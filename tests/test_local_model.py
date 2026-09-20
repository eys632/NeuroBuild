"""Real loopback HTTP tests with a fake model; no GPU or LLM accuracy claim."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from email.message import Message
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO, StringIO
import json
import os
from pathlib import Path
import socket
from tempfile import TemporaryDirectory
from threading import Thread
import time
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from neurobuild.application.requirement_generation import GenerationContract
from neurobuild.domain.errors import DomainError
from neurobuild.infrastructure.local_model import (
    LocalRequirementClient, MAX_HTTP_RESPONSE_BYTES, SamplingProfile, StructuredOutputProtocol,
)


SOURCE = "회의실 책상을 X축 양의 방향으로 1m 옮겨줘."
FINAL = {
    "schema_version": "1.0", "decision": "READY", "target_text": "회의실 책상",
    "operation": {"kind": "MOVE_FURNITURE", "coordinate_frame": "PROJECT_WORLD_XY", "instruction_text": SOURCE,
                  "dx": {"value": "1", "unit": "m", "evidence": "X축 양의 방향으로 1m"}, "dy": None},
    "reason": None,
}
QUOTE_FINAL = {
    "schema_version": "2.0", "target_selection_quote": "회의실 책상",
    "current_instruction_quote": SOURCE, "dx_evidence": "X축 양의 방향으로 1m",
    "dy_evidence": None, "decision": "READY", "reason": None,
}


def envelope(content=None):
    return {"model": "synthetic-test-model", "choices": [{"index": 0, "finish_reason": "stop",
            "message": {"role": "assistant", "content": json.dumps(FINAL, ensure_ascii=False) if content is None else content}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        size = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(size)
        self.server.request_bodies.append(body)
        self.server.requests.append((self.path, dict(self.headers), json.loads(body)))
        try:
            if self.server.delay:
                time.sleep(self.server.delay)
            self.send_response(self.server.status)
            for key, value in self.server.headers.items():
                self.send_header(key, value)
            self.end_headers()
            if self.server.trickle:
                for chunk in self.server.body:
                    self.wfile.write(bytes([chunk]))
                    self.wfile.flush()
                    time.sleep(self.server.trickle)
            else:
                self.wfile.write(self.server.body)
        except (BrokenPipeError, ConnectionResetError):
            pass


class LocalModelClientTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.server.requests = []
        self.server.request_bodies = []
        self.server.status = 200
        self.server.headers = {"Content-Type": "application/json"}
        self.server.delay = 0
        self.server.trickle = 0
        self.respond(envelope())
        self.thread = Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.client = LocalRequirementClient(self.base, "synthetic-test-model", timeout=1)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=1)

    def respond(self, value):
        self.server.body = json.dumps(value, ensure_ascii=False).encode("utf-8")

    def reject(self, code, client=None):
        with self.assertRaises(DomainError) as caught:
            (client or self.client).complete(SOURCE, axis_convention="project_xy")
        self.assertEqual(caught.exception.code, code)
        self.assertNotIn("DO_NOT_ECHO_SECRET", str(caught.exception))

    def test_actual_request_uses_shared_contract_and_disabled_thinking(self):
        completion = self.client.complete(SOURCE, axis_convention="project_xy")
        self.assertEqual(json.loads(completion.content), FINAL)
        self.assertEqual(completion.usage, {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30})
        self.assertGreaterEqual(completion.latency_seconds, 0)
        self.assertEqual(completion.model, "synthetic-test-model")
        path, headers, request = self.server.requests[0]
        self.assertEqual(path, "/v1/chat/completions")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(request["guided_decoding_backend"], "xgrammar:no-fallback")
        self.assertNotIn("structured_outputs", request)
        self.assertIs(self.client.protocol, StructuredOutputProtocol.LEGACY_GUIDED_JSON)
        self.assertIs(self.client.enable_thinking, False)
        self.assertEqual(request["chat_template_kwargs"], {"enable_thinking": False})
        self.assertEqual(request["temperature"], 0)
        self.assertEqual(request["seed"], 42)
        self.assertEqual(request["max_tokens"], 768)
        self.assertIs(request["stream"], False)
        self.assertEqual(json.loads(request["messages"][1]["content"]), {"source_text": SOURCE, "axis_convention": "project_xy"})
        self.assertEqual(request["messages"][0]["role"], "system")
        selected_prompt = (Path(__file__).resolve().parents[1] / "prompts/requirement_v3.txt").read_text()
        self.assertEqual(request["messages"][0]["content"], selected_prompt)
        self.assertEqual(request["guided_json"]["properties"]["schema_version"]["enum"], ["1.0"])
        for forbidden in ("minLength", "maxLength", "pattern"):
            self.assertNotIn('"' + forbidden + '"', json.dumps(request["guided_json"]))
        self.assertEqual(len(self.client.prompt_sha256), 64)
        self.assertEqual(len(self.client.schema_sha256), 64)

    def test_explicit_protocols_use_the_same_schema_and_domain_conversion(self):
        ids = {"requirement_id": uuid4(), "project_id": uuid4(), "base_revision_id": uuid4()}
        expected_schema = json.loads((Path(__file__).resolve().parents[1] / "schemas/semantic_requirement.schema.json").read_text())
        results = []
        for protocol in StructuredOutputProtocol:
            for configured in (protocol, protocol.value):
                with self.subTest(protocol=protocol, configured_type=type(configured).__name__):
                    client = LocalRequirementClient(self.base, "synthetic-test-model", protocol=configured)
                    results.append(client.extract(SOURCE, axis_convention="project_xy", **ids))
                    self.assertIs(client.protocol, protocol)
                    request = self.server.requests[-1][2]
                    if protocol is StructuredOutputProtocol.LEGACY_GUIDED_JSON:
                        self.assertEqual(request["guided_json"], expected_schema)
                        self.assertEqual(request["guided_decoding_backend"], "xgrammar:no-fallback")
                        self.assertNotIn("structured_outputs", request)
                    elif protocol is StructuredOutputProtocol.STRUCTURED_OUTPUTS:
                        self.assertEqual(request["structured_outputs"], {"json": expected_schema})
                        self.assertNotIn("guided_json", request)
                        self.assertNotIn("guided_decoding_backend", request)
                    else:
                        self.assertEqual(request["response_format"], {
                            "type": "json_schema", "json_schema": {"schema": expected_schema}})
                        self.assertNotIn("guided_json", request)
                        self.assertNotIn("guided_decoding_backend", request)
                        self.assertNotIn("structured_outputs", request)
                    if protocol is not StructuredOutputProtocol.LLAMA_CPP_JSON_SCHEMA:
                        self.assertNotIn("response_format", request)
                    self.assertEqual(request["chat_template_kwargs"], {"enable_thinking": False})
                    self.assertEqual(request["temperature"], 0)
        self.assertEqual(len(self.server.requests), 6)
        self.assertTrue(all(result == results[0] for result in results))

    def test_unknown_protocol_never_reaches_http(self):
        for protocol in (None, True, 0, [], {}, "auto", "json", "LEGACY_GUIDED_JSON", "structured_outputs "):
            with self.subTest(protocol=protocol):
                with self.assertRaises(DomainError) as caught:
                    LocalRequirementClient(self.base, "synthetic-test-model", protocol=protocol)
                self.assertEqual(caught.exception.code, "LOCAL_MODEL_CONFIG_INVALID")
        self.assertEqual(self.server.requests, [])

    def test_default_and_explicit_legacy_sampling_preserve_the_original_request_bytes(self):
        root = Path(__file__).resolve().parents[1]
        expected = {
            "model": "synthetic-test-model",
            "messages": [{"role": "system", "content": (root / "prompts/requirement_v3.txt").read_text()},
                         {"role": "user", "content": json.dumps({"source_text": SOURCE, "axis_convention": "project_xy"},
                                                                ensure_ascii=False)}],
            "temperature": 0, "seed": 42, "max_tokens": 768, "stream": False,
            "chat_template_kwargs": {"enable_thinking": False},
            "guided_json": json.loads((root / "schemas/semantic_requirement.schema.json").read_text()),
            "guided_decoding_backend": "xgrammar:no-fallback",
        }
        clients = [self.client] + [LocalRequirementClient(self.base, "synthetic-test-model", sampling_profile=value)
                                  for value in (SamplingProfile.LEGACY_GREEDY, "legacy_greedy")]
        clients.extend(LocalRequirementClient(self.base, "synthetic-test-model", generation_contract=value)
                       for value in (GenerationContract.LEGACY, "1.0"))
        for client in clients:
            with self.subTest(profile=client.sampling_profile):
                client.complete(SOURCE, axis_convention="project_xy")
                self.assertIs(client.sampling_profile, SamplingProfile.LEGACY_GREEDY)
                self.assertIs(client.generation_contract, GenerationContract.LEGACY)
                self.assertEqual(client.sampling_parameters, {"temperature": 0, "seed": 42})
                self.assertEqual(self.server.request_bodies[-1], json.dumps(expected, ensure_ascii=False).encode("utf-8"))
        self.assertEqual(len(self.server.requests), 5)

    def test_generation_contract_defaults_and_domain_conversion_are_explicit_in_all_protocols(self):
        root = Path(__file__).resolve().parents[1]
        ids = {"requirement_id": uuid4(), "project_id": uuid4(), "base_revision_id": uuid4()}
        results = []
        configurations = (
            (GenerationContract.LEGACY, FINAL, "requirement_v3.txt", "semantic_requirement.schema.json"),
            (GenerationContract.QUOTES, QUOTE_FINAL, "requirement_generation_v2_v1.txt",
             "requirement_generation_v2.schema.json"),
        )
        for contract, output, prompt_name, schema_name in configurations:
            prompt_bytes = (root / "prompts" / prompt_name).read_bytes()
            schema_bytes = (root / "schemas" / schema_name).read_bytes()
            for protocol in StructuredOutputProtocol:
                for configured in (contract, contract.value):
                    with self.subTest(contract=contract, protocol=protocol, configured_type=type(configured).__name__):
                        self.respond(envelope(json.dumps(output, ensure_ascii=False)))
                        client = LocalRequirementClient(self.base, "synthetic-test-model", protocol=protocol,
                                                        generation_contract=configured)
                        with self.assertRaises(AttributeError):
                            client.generation_contract = GenerationContract.LEGACY
                        results.append(client.extract(SOURCE, axis_convention="project_xy", **ids))
                        self.assertIs(client.generation_contract, contract)
                        self.assertEqual(client.prompt_sha256, sha256(prompt_bytes).hexdigest())
                        self.assertEqual(client.schema_sha256, sha256(schema_bytes).hexdigest())
                        request = self.server.requests[-1][2]
                        self.assertEqual(request["messages"][0]["content"], prompt_bytes.decode())
                        sent_schema = (request["guided_json"] if protocol is StructuredOutputProtocol.LEGACY_GUIDED_JSON
                                       else request["structured_outputs"]["json"] if protocol is StructuredOutputProtocol.STRUCTURED_OUTPUTS
                                       else request["response_format"]["json_schema"]["schema"])
                        self.assertEqual(sent_schema, json.loads(schema_bytes))
                        self.assertNotIn("generation_contract", request)
                        self.assertEqual(request["chat_template_kwargs"], {"enable_thinking": False})
        self.assertEqual(len(self.server.requests), 12)
        self.assertTrue(all(result == results[0] for result in results))
        self.assertEqual(results[0].base_revision_id, ids["base_revision_id"])
        self.assertEqual(results[0].operation.dx.metres, 1)

    def test_unknown_generation_contract_never_reaches_http(self):
        for contract in (None, True, 1, 2.0, [], {}, "auto", "2", "QUOTES", "2.0 "):
            with self.subTest(contract=contract):
                with self.assertRaises(DomainError) as caught:
                    LocalRequirementClient(self.base, "synthetic-test-model", generation_contract=contract)
                self.assertEqual(caught.exception.code, "LOCAL_MODEL_CONFIG_INVALID")
        self.assertEqual(self.server.requests, [])

    def test_custom_schema_must_bind_the_explicit_generation_before_http(self):
        root = Path(__file__).resolve().parents[1]
        schemas = {
            GenerationContract.LEGACY: root / "schemas/semantic_requirement.schema.json",
            GenerationContract.QUOTES: root / "schemas/requirement_generation_v2.schema.json",
        }
        for contract, other in ((GenerationContract.LEGACY, GenerationContract.QUOTES),
                                (GenerationContract.QUOTES, GenerationContract.LEGACY)):
            with self.subTest(contract=contract):
                client = LocalRequirementClient(self.base, "synthetic-test-model", generation_contract=contract,
                                                schema_path=schemas[contract])
                self.assertIs(client.generation_contract, contract)
                with self.assertRaises(DomainError) as caught:
                    LocalRequirementClient(self.base, "synthetic-test-model", generation_contract=contract,
                                           schema_path=schemas[other])
                self.assertEqual(caught.exception.code, "LOCAL_MODEL_CONFIG_INVALID")
        with TemporaryDirectory(prefix="nb_model_version_") as directory:
            path = Path(directory) / "schema.json"
            for invalid in ({"type": "object"}, {"properties": None},
                            {"properties": {"schema_version": {"enum": ["1.0", "2.0"]}}}):
                path.write_text(json.dumps(invalid))
                with self.subTest(schema=invalid), self.assertRaises(DomainError) as caught:
                    LocalRequirementClient(self.base, "synthetic-test-model", generation_contract="2.0",
                                           schema_path=path)
                self.assertEqual(caught.exception.code, "LOCAL_MODEL_CONFIG_INVALID")
        self.assertEqual(self.server.requests, [])

    def test_wrong_generation_contract_response_is_not_detected_or_retried(self):
        ids = {"requirement_id": uuid4(), "project_id": uuid4(), "base_revision_id": uuid4()}
        for contract, wrong_output in ((GenerationContract.LEGACY, QUOTE_FINAL),
                                       (GenerationContract.QUOTES, FINAL)):
            for protocol in StructuredOutputProtocol:
                with self.subTest(contract=contract, protocol=protocol):
                    self.respond(envelope(json.dumps(wrong_output, ensure_ascii=False)))
                    client = LocalRequirementClient(self.base, "synthetic-test-model", protocol=protocol,
                                                    generation_contract=contract)
                    before = len(self.server.requests)
                    with self.assertRaises(DomainError) as caught:
                        client.extract(SOURCE, axis_convention="project_xy", **ids)
                    self.assertEqual(caught.exception.code, "INVALID_MODEL_OUTPUT")
                    self.assertEqual(len(self.server.requests), before + 1)
                    self.assertIs(client.generation_contract, contract)

    def test_quote_generation_keeps_ungrounded_and_unsigned_ready_out_of_domain(self):
        ids = {"requirement_id": uuid4(), "project_id": uuid4(), "base_revision_id": uuid4()}
        client = LocalRequirementClient(self.base, "synthetic-test-model", generation_contract="2.0")
        invalid = deepcopy(QUOTE_FINAL)
        invalid["dx_evidence"] = "X축 양의 방향으로 2m"
        unsigned_source = "회의실 책상을 X축으로 1m 옮겨줘."
        unsigned = dict(QUOTE_FINAL, current_instruction_quote=unsigned_source, dx_evidence="X축으로 1m")
        for source, output in ((SOURCE, invalid), (unsigned_source, unsigned)):
            with self.subTest(source=source):
                self.respond(envelope(json.dumps(output, ensure_ascii=False)))
                before = len(self.server.requests)
                with self.assertRaises(DomainError) as caught:
                    client.extract(source, axis_convention="project_xy", **ids)
                self.assertEqual(caught.exception.code, "UNGROUNDED_REQUIREMENT")
                self.assertEqual(len(self.server.requests), before + 1)

    def test_quote_nonready_keeps_null_motion_and_code_owned_identity(self):
        output = dict(QUOTE_FINAL, decision="CLARIFICATION", current_instruction_quote=None,
                      dx_evidence=None, dy_evidence=None, reason="이동 방향을 확인해야 합니다.")
        self.respond(envelope(json.dumps(output, ensure_ascii=False)))
        ids = {"requirement_id": uuid4(), "project_id": uuid4(), "base_revision_id": uuid4()}
        client = LocalRequirementClient(self.base, "synthetic-test-model", generation_contract="2.0")
        result = client.extract("회의실 책상을 X축으로 1m 옮겨줘.", axis_convention="project_xy", **ids)
        self.assertEqual(result.status.value, "CLARIFICATION")
        self.assertEqual(result.target_description, "회의실 책상")
        self.assertIsNone(result.operation)
        self.assertEqual(result.requirement_id, ids["requirement_id"])
        self.assertEqual(result.project_id, ids["project_id"])
        self.assertEqual(result.base_revision_id, ids["base_revision_id"])

    def test_qwen_sampling_sends_all_eight_values_with_each_explicit_schema_protocol(self):
        expected = {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0.0,
                    "presence_penalty": 1.5, "frequency_penalty": 0.0,
                    "repetition_penalty": 1.0, "seed": 42}
        schema = json.loads((Path(__file__).resolve().parents[1] / "schemas/semantic_requirement.schema.json").read_text())
        for protocol in (StructuredOutputProtocol.LEGACY_GUIDED_JSON, StructuredOutputProtocol.STRUCTURED_OUTPUTS):
            for profile in (SamplingProfile.QWEN3_NONTHINKING_AWQ, "qwen3_nonthinking_awq"):
                with self.subTest(protocol=protocol, profile_type=type(profile).__name__):
                    client = LocalRequirementClient(self.base, "synthetic-test-model", protocol=protocol,
                                                    sampling_profile=profile)
                    result = client.extract(SOURCE, axis_convention="project_xy", requirement_id=uuid4(),
                                            project_id=uuid4(), base_revision_id=uuid4())
                    self.assertEqual(result.operation.dx.metres, 1)
                    self.assertIs(client.sampling_profile, SamplingProfile.QWEN3_NONTHINKING_AWQ)
                    self.assertIs(client.enable_thinking, False)
                    self.assertEqual(client.sampling_parameters, expected)
                    request = self.server.requests[-1][2]
                    self.assertEqual({key: request[key] for key in expected}, expected)
                    self.assertIs(type(request["top_k"]), int)
                    self.assertIs(type(request["seed"]), int)
                    self.assertEqual(request["chat_template_kwargs"], {"enable_thinking": False})
                    self.assertEqual(request["max_tokens"], 768)
                    self.assertIs(request["stream"], False)
                    if protocol is StructuredOutputProtocol.LEGACY_GUIDED_JSON:
                        self.assertEqual(request["guided_json"], schema)
                        self.assertEqual(request["guided_decoding_backend"], "xgrammar:no-fallback")
                        self.assertNotIn("structured_outputs", request)
                    else:
                        self.assertEqual(request["structured_outputs"], {"json": schema})
                        self.assertNotIn("guided_json", request)
                        self.assertNotIn("guided_decoding_backend", request)

    def test_unknown_sampling_profile_fails_before_any_http_request(self):
        invalid = (None, True, False, 0, 0.7, float("nan"), [], {}, b"legacy_greedy", "auto", "",
                   "QWEN3_NONTHINKING_AWQ", "qwen3_nonthinking_awq ", "QWEN3_NONTHINKING",
                   "qwen3_nonthinking ", StructuredOutputProtocol.LEGACY_GUIDED_JSON)
        for profile in invalid:
            with self.subTest(profile=profile), self.assertRaises(DomainError) as caught:
                LocalRequirementClient(self.base, "synthetic-test-model", sampling_profile=profile)
            self.assertEqual(caught.exception.code, "LOCAL_MODEL_CONFIG_INVALID")
        self.assertEqual(self.server.requests, [])

    def test_native_profile_sends_native_sampling_and_branch_schema_without_changing_conversion(self):
        root = Path(__file__).resolve().parents[1]
        schema_path = root / "schemas/requirement_generation_v2_decision_branches.schema.json"
        expected_sampling = {
            "temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0.0,
            "presence_penalty": 0.0, "frequency_penalty": 0.0,
            "repeat_penalty": 1.0, "repeat_last_n": 0, "seed": 42,
            "samplers": ["temperature", "top_k", "top_p", "min_p"],
        }
        for profile in (SamplingProfile.QWEN38_NONTHINKING_LLAMA_CPP, "qwen38_nonthinking_llama_cpp"):
            self.respond(envelope(json.dumps(QUOTE_FINAL, ensure_ascii=False)))
            client = LocalRequirementClient(
                self.base, "synthetic-test-model", protocol="llama_cpp_json_schema",
                sampling_profile=profile, generation_contract="2.0", schema_path=schema_path,
            )
            result = client.extract(SOURCE, axis_convention="project_xy", requirement_id=uuid4(),
                                    project_id=uuid4(), base_revision_id=uuid4())
            self.assertEqual(result.operation.dx.metres, 1)
            self.assertEqual(client.sampling_parameters, expected_sampling)
            request = self.server.requests[-1][2]
            self.assertEqual({key: request[key] for key in expected_sampling}, expected_sampling)
            self.assertEqual(request["response_format"], {
                "type": "json_schema", "json_schema": {"schema": json.loads(schema_path.read_text())}})
            self.assertEqual(request["chat_template_kwargs"], {"enable_thinking": False})
            self.assertIs(client.enable_thinking, False)
            for absent in ("guided_json", "guided_decoding_backend", "structured_outputs",
                           "repetition_penalty", "tools", "reasoning_parser"):
                self.assertNotIn(absent, request)
        self.assertEqual(len(self.server.requests), 2)

    def test_native_and_vllm_sampling_profiles_cannot_be_mixed(self):
        for protocol in StructuredOutputProtocol:
            for profile in SamplingProfile:
                invalid = ((protocol is StructuredOutputProtocol.LLAMA_CPP_JSON_SCHEMA
                            and profile not in (SamplingProfile.LEGACY_GREEDY,
                                                SamplingProfile.QWEN38_NONTHINKING_LLAMA_CPP,
                                                SamplingProfile.QWEN36_NONTHINKING_LLAMA_CPP,
                                                SamplingProfile.GEMMA4_NONTHINKING_LLAMA_CPP,
                                                SamplingProfile.EXAONE45_NONTHINKING_LLAMA_CPP,
                                                SamplingProfile.GLM47_FLASH_NONTHINKING_LLAMA_CPP))
                           or (protocol is not StructuredOutputProtocol.LLAMA_CPP_JSON_SCHEMA
                               and profile in (SamplingProfile.QWEN38_NONTHINKING_LLAMA_CPP,
                                               SamplingProfile.QWEN36_NONTHINKING_LLAMA_CPP,
                                               SamplingProfile.GEMMA4_NONTHINKING_LLAMA_CPP,
                                               SamplingProfile.EXAONE45_NONTHINKING_LLAMA_CPP,
                                               SamplingProfile.GLM47_FLASH_NONTHINKING_LLAMA_CPP)))
                if invalid:
                    with self.subTest(protocol=protocol, profile=profile):
                        with self.assertRaises(DomainError) as caught:
                            LocalRequirementClient(self.base, "synthetic-test-model", protocol=protocol,
                                                   sampling_profile=profile)
                        self.assertEqual(caught.exception.code, "LOCAL_MODEL_CONFIG_INVALID")
        self.assertEqual(self.server.requests, [])

    def test_native_sampler_list_copy_cannot_mutate_next_request(self):
        client = LocalRequirementClient(self.base, "synthetic-test-model", protocol="llama_cpp_json_schema",
                                        sampling_profile="qwen38_nonthinking_llama_cpp")
        saved = client.sampling_parameters
        saved["samplers"].clear()
        saved["repeat_last_n"] = 4096
        client.complete(SOURCE)
        request = self.server.requests[-1][2]
        self.assertEqual(request["samplers"], ["temperature", "top_k", "top_p", "min_p"])
        self.assertEqual(request["repeat_last_n"], 0)

    def test_native_transport_discards_reasoning_even_with_nonthinking_requested(self):
        response = envelope()
        response["choices"][0]["message"]["reasoning_content"] = "DO_NOT_ECHO_SECRET_REASONING"
        self.respond(response)
        client = LocalRequirementClient(self.base, "synthetic-test-model", protocol="llama_cpp_json_schema",
                                        sampling_profile="qwen38_nonthinking_llama_cpp")
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            completion = client.complete(SOURCE)
        self.assertEqual(json.loads(completion.content), FINAL)
        self.assertNotIn("DO_NOT_ECHO_SECRET", repr(completion))
        self.assertFalse(hasattr(completion, "reasoning_content"))
        self.assertEqual(out.getvalue() + err.getvalue(), "")

    def test_native_rejection_and_truncation_never_retry_or_switch_protocol(self):
        client = LocalRequirementClient(self.base, "synthetic-test-model", protocol="llama_cpp_json_schema",
                                        sampling_profile="qwen38_nonthinking_llama_cpp")
        invalid = envelope()
        invalid["choices"][0]["finish_reason"] = "length"
        for status, body, code in (
            (400, {"error": "DO_NOT_ECHO_SECRET"}, "LOCAL_MODEL_HTTP_ERROR"),
            (200, invalid, "LOCAL_MODEL_TRUNCATED"),
            (200, envelope("<think>DO_NOT_ECHO_SECRET</think>" + json.dumps(FINAL)), "LOCAL_MODEL_REASONING_CONTENT"),
        ):
            with self.subTest(status=status, code=code):
                self.server.status = status
                self.respond(body)
                before = len(self.server.requests)
                self.reject(code, client)
                self.assertEqual(len(self.server.requests), before + 1)
                request = self.server.requests[-1][2]
                self.assertIn("response_format", request)
                self.assertNotIn("guided_json", request)
                self.assertNotIn("structured_outputs", request)

    def test_neutral_nonthinking_profile_sends_explicit_values_without_awq_penalty(self):
        expected = {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0.0,
                    "presence_penalty": 0.0, "frequency_penalty": 0.0,
                    "repetition_penalty": 1.0, "seed": 42}
        for protocol in (StructuredOutputProtocol.LEGACY_GUIDED_JSON, StructuredOutputProtocol.STRUCTURED_OUTPUTS):
            for profile in (SamplingProfile.QWEN3_NONTHINKING, "qwen3_nonthinking"):
                with self.subTest(protocol=protocol, profile_type=type(profile).__name__):
                    client = LocalRequirementClient(self.base, "synthetic-test-model", protocol=protocol,
                                                    sampling_profile=profile)
                    metadata = client.sampling_parameters
                    self.assertEqual(metadata, expected)
                    metadata["presence_penalty"] = 1.5
                    with self.assertRaises(AttributeError):
                        client.sampling_profile = SamplingProfile.QWEN3_NONTHINKING_AWQ
                    with self.assertRaises(AttributeError):
                        client.enable_thinking = True
                    result = client.extract(SOURCE, axis_convention="project_xy", requirement_id=uuid4(),
                                            project_id=uuid4(), base_revision_id=uuid4())
                    self.assertEqual(result.operation.dx.metres, 1)
                    self.assertIs(client.sampling_profile, SamplingProfile.QWEN3_NONTHINKING)
                    self.assertIs(client.enable_thinking, False)
                    request = self.server.requests[-1][2]
                    self.assertEqual({key: request[key] for key in expected}, expected)
                    self.assertEqual(client.sampling_parameters, expected)
                    self.assertIsNot(client.sampling_parameters, client.sampling_parameters)
                    self.assertEqual(request["chat_template_kwargs"], {"enable_thinking": False})
                    self.assertEqual(request["max_tokens"], 768)
                    self.assertEqual(client.timeout, 60)
                    self.assertNotIn("reasoning_parser", request)
                    self.assertIs(request["stream"], False)
                    schema_field = ("guided_json" if protocol is StructuredOutputProtocol.LEGACY_GUIDED_JSON
                                    else "structured_outputs")
                    self.assertIn(schema_field, request)
                    self.assertNotIn("structured_outputs" if schema_field == "guided_json" else "guided_json", request)

    def test_model_name_never_selects_a_sampling_profile_and_neutral_failure_never_retries(self):
        self.server.status = 400
        self.server.body = b'{"error":"sampling rejected DO_NOT_ECHO_SECRET"}'
        for model in ("Qwen/Qwen3-4B-Instruct-2507", "Qwen/Qwen3-14B-AWQ", "synthetic-test-model"):
            for profile, expected_penalty in ((None, None), (SamplingProfile.QWEN3_NONTHINKING, 0.0),
                                              (SamplingProfile.QWEN3_NONTHINKING_AWQ, 1.5)):
                with self.subTest(model=model, profile=profile):
                    kwargs = {} if profile is None else {"sampling_profile": profile}
                    client = LocalRequirementClient(self.base, model, **kwargs)
                    before = len(self.server.requests)
                    self.reject("LOCAL_MODEL_HTTP_ERROR", client)
                    self.assertEqual(len(self.server.requests), before + 1)
                    request = self.server.requests[-1][2]
                    self.assertEqual(request["model"], model)
                    self.assertIs(client.sampling_profile, SamplingProfile.LEGACY_GREEDY if profile is None else profile)
                    self.assertEqual(request.get("presence_penalty"), expected_penalty)
                    self.assertEqual(request["temperature"], 0 if profile is None else 0.7)
                    self.assertEqual(request["chat_template_kwargs"], {"enable_thinking": False})
                    self.assertIn("guided_json", request)

    def test_thinking_profile_sets_explicit_request_mode_and_sampling_without_selecting_server_parser(self):
        expected = {"temperature": 0.6, "top_p": 0.95, "top_k": 20, "min_p": 0.0,
                    "presence_penalty": 1.5, "frequency_penalty": 0.0,
                    "repetition_penalty": 1.0, "seed": 42}
        for protocol in (StructuredOutputProtocol.LEGACY_GUIDED_JSON, StructuredOutputProtocol.STRUCTURED_OUTPUTS):
            for profile in (SamplingProfile.QWEN3_THINKING_AWQ, "qwen3_thinking_awq"):
                with self.subTest(protocol=protocol, profile_type=type(profile).__name__):
                    client = LocalRequirementClient(self.base, "synthetic-test-model", protocol=protocol,
                                                    sampling_profile=profile, max_tokens=2048, timeout=120)
                    self.assertIs(client.enable_thinking, True)
                    self.assertEqual(client.sampling_parameters, expected)
                    with self.assertRaises(AttributeError):
                        client.enable_thinking = False
                    client.complete(SOURCE, axis_convention="project_xy")
                    request = self.server.requests[-1][2]
                    self.assertEqual({key: request[key] for key in expected}, expected)
                    self.assertEqual(request["chat_template_kwargs"], {"enable_thinking": True})
                    self.assertEqual(request["max_tokens"], 2048)
                    self.assertEqual(client.timeout, 120)
                    self.assertNotIn("reasoning_parser", request)
                    self.assertNotIn("enable_reasoning", request)
                    self.assertNotIn("thinking_budget", request)
                    self.assertIs(request["stream"], False)
                    if protocol is StructuredOutputProtocol.LEGACY_GUIDED_JSON:
                        self.assertEqual(request["guided_decoding_backend"], "xgrammar:no-fallback")
                        self.assertIn("guided_json", request)
                        self.assertNotIn("structured_outputs", request)
                    else:
                        self.assertIn("structured_outputs", request)
                        self.assertNotIn("guided_decoding_backend", request)
                        self.assertNotIn("guided_json", request)

    def test_thinking_success_returns_only_final_content_and_numeric_usage(self):
        response = envelope()
        response["choices"][0]["message"]["reasoning_content"] = "DO_NOT_ECHO_SECRET_REASONING"
        response["usage"]["completion_tokens_details"] = {"reasoning_tokens": 7}
        self.respond(response)
        client = LocalRequirementClient(self.base, "synthetic-test-model", sampling_profile="qwen3_thinking_awq",
                                        max_tokens=2048, timeout=120)
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            completion = client.complete(SOURCE, axis_convention="project_xy")
            requirement = client.extract(SOURCE, axis_convention="project_xy", requirement_id=uuid4(),
                                         project_id=uuid4(), base_revision_id=uuid4())
        self.assertEqual(json.loads(completion.content), FINAL)
        self.assertEqual(completion.usage["reasoning_tokens"], 7)
        self.assertEqual(requirement.operation.dx.metres, 1)
        self.assertFalse(hasattr(completion, "reasoning_content"))
        self.assertNotIn("DO_NOT_ECHO_SECRET", repr(completion) + repr(requirement))
        self.assertEqual(out.getvalue() + err.getvalue(), "")

    def test_thinking_truncation_absent_final_leak_and_oversized_body_fail_without_retry(self):
        cases = []
        response = envelope()
        response["choices"][0]["finish_reason"] = "length"
        cases.append((response, "LOCAL_MODEL_TRUNCATED"))
        for final in (None, ""):
            response = envelope()
            response["choices"][0]["message"].update(content=final, reasoning_content="DO_NOT_ECHO_SECRET_REASONING")
            cases.append((response, "LOCAL_MODEL_RESPONSE_INVALID"))
        cases.append((envelope("<think>DO_NOT_ECHO_SECRET</think>" + json.dumps(FINAL)), "LOCAL_MODEL_REASONING_CONTENT"))
        response = envelope()
        response["choices"][0]["message"]["reasoning_content"] = "x" * MAX_HTTP_RESPONSE_BYTES
        cases.append((response, "LOCAL_MODEL_RESPONSE_TOO_LARGE"))
        for protocol in (StructuredOutputProtocol.LEGACY_GUIDED_JSON, StructuredOutputProtocol.STRUCTURED_OUTPUTS):
            client = LocalRequirementClient(self.base, "synthetic-test-model", protocol=protocol,
                                            sampling_profile="qwen3_thinking_awq", max_tokens=2048, timeout=120)
            for response, code in cases:
                with self.subTest(protocol=protocol, error=code):
                    before = len(self.server.requests)
                    self.respond(response)
                    self.reject(code, client)
                    self.assertEqual(len(self.server.requests), before + 1)
                    self.assertEqual(self.server.requests[-1][2]["chat_template_kwargs"], {"enable_thinking": True})

    def test_sampling_metadata_copies_cannot_change_requests_or_the_selected_profile(self):
        client = LocalRequirementClient(self.base, "synthetic-test-model", sampling_profile="qwen3_nonthinking_awq")
        saved = client.sampling_parameters
        saved["temperature"] = 0
        saved["approval"] = True
        with self.assertRaises(AttributeError):
            client.sampling_profile = SamplingProfile.LEGACY_GREEDY
        with self.assertRaises(AttributeError):
            client.sampling_parameters = saved
        client.complete(SOURCE, axis_convention="project_xy")
        request = self.server.requests[-1][2]
        self.assertEqual(request["temperature"], 0.7)
        self.assertNotIn("approval", request)
        self.assertEqual(client.sampling_parameters["temperature"], 0.7)
        self.assertIsNot(client.sampling_parameters, client.sampling_parameters)

    def test_rejected_sampling_never_retries_with_greedy_or_without_schema(self):
        for status, error in ((400, "LOCAL_MODEL_HTTP_ERROR"), (200, "LOCAL_MODEL_RESPONSE_INVALID")):
            self.server.status = status
            self.server.body = b'{"error":"sampling rejected DO_NOT_ECHO_SECRET"}'
            for protocol in (StructuredOutputProtocol.LEGACY_GUIDED_JSON, StructuredOutputProtocol.STRUCTURED_OUTPUTS):
                with self.subTest(status=status, protocol=protocol):
                    before = len(self.server.requests)
                    client = LocalRequirementClient(self.base, "synthetic-test-model", protocol=protocol,
                                                    sampling_profile="qwen3_nonthinking_awq")
                    self.reject(error, client)
                    self.assertEqual(len(self.server.requests), before + 1)
                    self.assertIs(client.sampling_profile, SamplingProfile.QWEN3_NONTHINKING_AWQ)
                    request = self.server.requests[-1][2]
                    self.assertEqual(request["temperature"], 0.7)
                    self.assertIn("guided_json" if protocol is StructuredOutputProtocol.LEGACY_GUIDED_JSON
                                  else "structured_outputs", request)

    def test_protocol_rejection_never_retries_or_removes_grammar_constraints(self):
        self.server.status = 400
        self.server.body = b'{"error":"unsupported grammar field DO_NOT_ECHO_SECRET"}'
        for protocol in StructuredOutputProtocol:
            with self.subTest(protocol=protocol):
                before = len(self.server.requests)
                client = LocalRequirementClient(self.base, "synthetic-test-model", protocol=protocol)
                self.reject("LOCAL_MODEL_HTTP_ERROR", client)
                self.assertEqual(len(self.server.requests), before + 1)
                self.assertIs(client.protocol, protocol)
                request = self.server.requests[-1][2]
                selected = {StructuredOutputProtocol.LEGACY_GUIDED_JSON: "guided_json",
                            StructuredOutputProtocol.STRUCTURED_OUTPUTS: "structured_outputs",
                            StructuredOutputProtocol.LLAMA_CPP_JSON_SCHEMA: "response_format"}[protocol]
                self.assertIn(selected, request)

    def test_invalid_success_response_does_not_trigger_dialect_detection_or_retry(self):
        self.server.body = b'{"unexpected":"DO_NOT_ECHO_SECRET"}'
        for protocol in StructuredOutputProtocol:
            with self.subTest(protocol=protocol):
                before = len(self.server.requests)
                client = LocalRequirementClient(self.base, "synthetic-test-model", protocol=protocol)
                self.reject("LOCAL_MODEL_RESPONSE_INVALID", client)
                self.assertEqual(len(self.server.requests), before + 1)
                self.assertIs(client.protocol, protocol)

    def test_extract_binds_application_ids_and_runs_grounding(self):
        ids = {"requirement_id": uuid4(), "project_id": uuid4(), "base_revision_id": uuid4()}
        result = self.client.extract(SOURCE, axis_convention="project_xy", **ids)
        self.assertEqual(result.requirement_id, ids["requirement_id"])
        self.assertEqual(result.project_id, ids["project_id"])
        self.assertEqual(result.source_text, SOURCE)
        self.assertEqual(result.operation.dx.metres, 1)
        invalid = deepcopy(FINAL)
        invalid["operation"]["dx"]["value"] = "2"
        self.respond(envelope(json.dumps(invalid)))
        with self.assertRaises(DomainError) as caught:
            self.client.extract(SOURCE, axis_convention="project_xy", **ids)
        self.assertEqual(caught.exception.code, "UNGROUNDED_REQUIREMENT")

    def test_final_content_for_evaluation_need_not_be_schema_valid(self):
        self.respond(envelope("{invalid json"))
        result = self.client.complete(SOURCE)
        self.assertEqual(result.content, "{invalid json")

    def test_loopback_url_policy_rejects_external_credentials_and_ambiguous_paths(self):
        denied = ["https://127.0.0.1:8000", "http://example.com", "http://0.0.0.0:8000",
                  "http://192.168.1.2:8000", "http://127.0.0.1.evil.test", "http://user:secret@127.0.0.1",
                  "http://127.0.0.1?token=secret", "http://127.0.0.1/#fragment", "http://127.0.0.1/other",
                  "http://2130706433", "http://127.1", "http://127.0.0.1:0", "http://127.0.0.1:65536",
                  "http://[::ffff:127.0.0.1]", "http://[::1%eth0]", "http://localHOST.evil", "http://localhost\n"]
        for url in denied:
            with self.subTest(url=url):
                with self.assertRaises(DomainError) as caught:
                    LocalRequirementClient(url, "test")
                self.assertEqual(caught.exception.code, "LOCAL_MODEL_CONFIG_INVALID")
        for url in ("http://[::1]:8000/v1", "http://127.0.0.2:8000/v1/", "http://localhost:8000/"):
            self.assertTrue(LocalRequirementClient(url, "test").endpoint.endswith("/v1/chat/completions"))
        self.assertEqual(LocalRequirementClient("http://localhost:8000", "test").endpoint,
                         "http://127.0.0.1:8000/v1/chat/completions")
        self.assertEqual(self.server.requests, [])

    def test_environment_proxy_is_not_used(self):
        with patch.dict(os.environ, {"HTTP_PROXY": "http://127.0.0.1:1", "http_proxy": "http://127.0.0.1:1",
                                     "ALL_PROXY": "http://127.0.0.1:1", "NO_PROXY": "", "no_proxy": ""}):
            client = LocalRequirementClient(self.base + "/v1", "synthetic-test-model")
            self.assertEqual(client.complete(SOURCE).model, "synthetic-test-model")
        self.assertEqual(len(self.server.requests), 1)

    def test_redirect_is_rejected_before_any_second_request(self):
        self.server.status = 307
        self.server.headers["Location"] = self.base + "/must-not-follow"
        self.reject("LOCAL_MODEL_HTTP_ERROR")
        self.assertEqual(len(self.server.requests), 1)

    def test_error_status_does_not_echo_server_response_or_log_reasoning(self):
        self.server.status = 500
        self.server.body = b"DO_NOT_ECHO_SECRET"
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.reject("LOCAL_MODEL_HTTP_ERROR")
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(err.getvalue(), "")

    def test_timeout_and_slow_body_are_bounded(self):
        short = LocalRequirementClient(self.base, "synthetic-test-model", timeout=0.05)
        self.server.delay = 0.2
        self.reject("LOCAL_MODEL_TIMEOUT", short)
        self.server.delay = 0
        self.server.trickle = 0.02
        started = time.monotonic()
        self.reject("LOCAL_MODEL_TIMEOUT", short)
        self.assertLess(time.monotonic() - started, 0.5)

    def test_unavailable_service_is_safe_error(self):
        with socket.socket() as reserved:
            reserved.bind(("127.0.0.1", 0))
            client = LocalRequirementClient(f"http://127.0.0.1:{reserved.getsockname()[1]}", "synthetic-test-model", timeout=0.1)
            self.reject("LOCAL_MODEL_UNAVAILABLE", client)

    def test_response_byte_limit_applies_with_and_without_content_length(self):
        self.server.body = b"{}"
        self.server.headers["Content-Length"] = str(MAX_HTTP_RESPONSE_BYTES + 1)
        self.reject("LOCAL_MODEL_RESPONSE_TOO_LARGE")
        del self.server.headers["Content-Length"]
        self.server.body = b" " * (MAX_HTTP_RESPONSE_BYTES + 1)
        self.reject("LOCAL_MODEL_RESPONSE_TOO_LARGE")

    def test_truncated_or_invalid_http_envelope_never_becomes_ready(self):
        self.server.headers["Content-Length"] = "9999"
        self.reject("LOCAL_MODEL_RESPONSE_INVALID")
        del self.server.headers["Content-Length"]
        for body in (b"not json DO_NOT_ECHO_SECRET", b"\xff", b'{"model":NaN}',
                     b'{"model":"x","model":"y"}', b"[]"):
            with self.subTest(body=body):
                self.server.body = body
                self.reject("LOCAL_MODEL_RESPONSE_INVALID")
        self.respond(envelope())
        self.server.headers["Content-Type"] = "text/html"
        self.reject("LOCAL_MODEL_RESPONSE_INVALID")

    def test_only_one_completed_assistant_choice_is_accepted(self):
        cases = []
        for reason in (None, "length", "tool_calls", "content_filter"):
            item = envelope()
            item["choices"][0]["finish_reason"] = reason
            cases.append((item, "LOCAL_MODEL_TRUNCATED"))
        for value in ([], [envelope()["choices"][0]] * 2, [None]):
            item = envelope()
            item["choices"] = value
            cases.append((item, "LOCAL_MODEL_RESPONSE_INVALID"))
        for key, value in (("role", "user"), ("content", None), ("content", "x" * 16385),
                           ("tool_calls", [{"function": "apply"}]), ("function_call", {})):
            item = envelope()
            item["choices"][0]["message"][key] = value
            cases.append((item, "LOCAL_MODEL_RESPONSE_INVALID"))
        item = envelope()
        item["choices"][0]["index"] = False
        cases.append((item, "LOCAL_MODEL_RESPONSE_INVALID"))
        item = envelope()
        item["model"] = "different-model"
        cases.append((item, "LOCAL_MODEL_RESPONSE_INVALID"))
        for item, code in cases:
            with self.subTest(item=item):
                self.respond(item)
                self.reject(code)

    def test_reasoning_fields_are_discarded_and_think_content_is_rejected(self):
        item = envelope()
        item["choices"][0]["message"]["reasoning_content"] = "DO_NOT_ECHO_SECRET"
        item["usage"]["completion_tokens_details"] = {"reasoning_tokens": 7, "reasoning": "DO_NOT_ECHO_SECRET"}
        item["usage"]["private"] = "DO_NOT_ECHO_SECRET"
        self.respond(item)
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            result = self.client.complete(SOURCE)
        self.assertEqual(result.usage["reasoning_tokens"], 7)
        self.assertNotIn("DO_NOT_ECHO_SECRET", repr(result))
        self.assertEqual(out.getvalue() + err.getvalue(), "")
        self.respond(envelope("<think>DO_NOT_ECHO_SECRET</think>{}"))
        self.reject("LOCAL_MODEL_REASONING_CONTENT")

    def test_missing_usage_is_not_fabricated_and_malformed_counts_rejected(self):
        item = envelope()
        del item["usage"]
        self.respond(item)
        self.assertIsNone(self.client.complete(SOURCE).usage)
        for usage in ([], {"prompt_tokens": True}, {"completion_tokens": -1},
                      {"total_tokens": "30"}, {"completion_tokens_details": {"reasoning_tokens": 1.5}}):
            self.respond(dict(envelope(), usage=usage))
            self.reject("LOCAL_MODEL_RESPONSE_INVALID")

    def test_invalid_inputs_and_ids_are_rejected_before_http(self):
        for source in (None, "", " ", "x" * 16001, "text\x00", "text\ud800"):
            with self.subTest(source=repr(source)[:20]), self.assertRaises(DomainError) as caught:
                self.client.complete(source)
            self.assertEqual(caught.exception.code, "LOCAL_MODEL_INPUT_INVALID")
        with self.assertRaises(DomainError):
            self.client.complete(SOURCE, axis_convention="screen")
        with self.assertRaises(DomainError):
            self.client.extract(SOURCE, requirement_id="from-model", project_id=uuid4(), base_revision_id=uuid4())
        self.assertEqual(self.server.requests, [])

    def test_invalid_limits_or_contract_files_are_safe_configuration_errors(self):
        for options in ({"timeout": 0}, {"timeout": True}, {"timeout": float("inf")}, {"timeout": 301},
                        {"max_tokens": True}, {"max_tokens": 0}, {"max_tokens": 2049}):
            with self.subTest(options=options), self.assertRaises(DomainError) as caught:
                LocalRequirementClient(self.base, "model", **options)
            self.assertEqual(caught.exception.code, "LOCAL_MODEL_CONFIG_INVALID")
        with TemporaryDirectory(prefix="nb_model_contract_") as directory:
            broken = Path(directory) / "schema.json"
            broken.write_text("DO_NOT_ECHO_SECRET")
            with self.assertRaises(DomainError) as caught:
                LocalRequirementClient(self.base, "model", schema_path=broken)
            self.assertEqual(caught.exception.code, "LOCAL_MODEL_CONFIG_INVALID")
            self.assertNotIn("DO_NOT_ECHO_SECRET", str(caught.exception))
        self.assertEqual(self.server.requests, [])


class GemmaNativeProfileTests(unittest.TestCase):
    """Fake opener only: no server, sockets, GPU or model calls."""
    root = Path(__file__).resolve().parents[1]
    sampling = {
        "temperature": 1.0, "top_p": 0.95, "top_k": 64, "min_p": 0.0,
        "presence_penalty": 0.0, "frequency_penalty": 0.0,
        "repeat_penalty": 1.0, "repeat_last_n": 0, "seed": 42,
        "samplers": ["temperature", "top_k", "top_p", "min_p"],
    }

    def client(self, profile=SamplingProfile.GEMMA4_NONTHINKING_LLAMA_CPP):
        return LocalRequirementClient(
            "http://127.0.0.1:8003", "synthetic-test-model", protocol="llama_cpp_json_schema",
            sampling_profile=profile, generation_contract="2.0",
            prompt_path=self.root / "prompts/requirement_generation_v2_v2.txt",
            schema_path=self.root / "schemas/requirement_generation_v2_decision_branches.schema.json")

    def fake_response(self, client, response=None, status=200):
        value = envelope(json.dumps(QUOTE_FINAL, ensure_ascii=False)) if response is None else response
        body = json.dumps(value, ensure_ascii=False).encode()
        stream = BytesIO(body)
        stream.status = status
        stream.headers = Message()
        stream.headers["Content-Type"] = "application/json"
        stream.headers["Content-Length"] = str(len(body))
        client._opener = Mock()
        client._opener.open.return_value = stream
        return client._opener.open

    def test_gemma_wire_recipe_and_domain_extraction_are_explicit(self):
        for profile in (SamplingProfile.GEMMA4_NONTHINKING_LLAMA_CPP, "gemma4_nonthinking_llama_cpp"):
            with self.subTest(profile=profile):
                client = self.client(profile)
                transport = self.fake_response(client)
                result = client.extract(SOURCE, axis_convention="project_xy", requirement_id=uuid4(),
                                        project_id=uuid4(), base_revision_id=uuid4())
                transport.assert_called_once()
                request = json.loads(transport.call_args.args[0].data)
                self.assertEqual({key: request[key] for key in self.sampling}, self.sampling)
                self.assertEqual(request["chat_template_kwargs"], {"enable_thinking": False})
                self.assertEqual(request["response_format"]["json_schema"]["schema"], client.schema)
                self.assertEqual(request["max_tokens"], 768)
                self.assertFalse(client.enable_thinking)
                self.assertEqual(result.operation.dx.metres, 1)
                self.assertEqual(result.target_description, "회의실 책상")
                for absent in ("guided_json", "structured_outputs", "repetition_penalty", "reasoning_parser"):
                    self.assertNotIn(absent, request)

    def test_gemma_profile_is_native_only_and_never_selected_by_model_name(self):
        with patch("neurobuild.infrastructure.local_model.build_opener") as opener:
            for protocol in ("legacy_guided_json", "structured_outputs"):
                with self.subTest(protocol=protocol), self.assertRaises(DomainError):
                    LocalRequirementClient("http://127.0.0.1:8003", "model", protocol=protocol,
                                           sampling_profile="gemma4_nonthinking_llama_cpp")
            for profile in ("GEMMA4_NONTHINKING_LLAMA_CPP", "gemma4_nonthinking_llama_cpp ", True):
                with self.subTest(profile=profile), self.assertRaises(DomainError):
                    self.client(profile)
            opener.assert_not_called()
        default = LocalRequirementClient("http://127.0.0.1:8003", "google/gemma-4-31B-it-qat-q4_0-gguf")
        self.assertIs(default.sampling_profile, SamplingProfile.LEGACY_GREEDY)

    def test_gemma_sampler_copy_cannot_change_next_request(self):
        client = self.client()
        copied = client.sampling_parameters
        copied["samplers"].clear()
        copied["temperature"] = 0
        transport = self.fake_response(client)
        client.complete(SOURCE)
        request = json.loads(transport.call_args.args[0].data)
        self.assertEqual({key: request[key] for key in self.sampling}, self.sampling)

    def test_gemma_separate_reasoning_is_discarded_without_logging(self):
        client = self.client()
        response = envelope(json.dumps(QUOTE_FINAL))
        response["choices"][0]["message"]["reasoning_content"] = "<|channel>thought DO_NOT_ECHO_SECRET"
        self.fake_response(client, response)
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            completion = client.complete(SOURCE)
        self.assertEqual(json.loads(completion.content), QUOTE_FINAL)
        self.assertNotIn("DO_NOT_ECHO_SECRET", repr(completion))
        self.assertEqual(out.getvalue() + err.getvalue(), "")

    def test_inline_thought_or_channel_markers_are_rejected_without_retry(self):
        for marker in ("<|channel>thought", "<|channel>final", "<channel|>", "<|think|>",
                       "<|CHANNEL>thought", "<think>"):
            with self.subTest(marker=marker):
                client = self.client()
                transport = self.fake_response(client, envelope(marker + "DO_NOT_ECHO_SECRET" + json.dumps(QUOTE_FINAL)))
                with self.assertRaises(DomainError) as caught:
                    client.complete(SOURCE)
                self.assertEqual(caught.exception.code, "LOCAL_MODEL_REASONING_CONTENT")
                self.assertNotIn("DO_NOT_ECHO_SECRET", str(caught.exception))
                transport.assert_called_once()

    def test_http_rejection_truncation_and_fenced_content_are_not_repaired(self):
        truncated = envelope(json.dumps(QUOTE_FINAL))
        truncated["choices"][0]["finish_reason"] = "length"
        for response, status in (({"error": "DO_NOT_ECHO_SECRET"}, 400), (truncated, 200),
                                 (envelope('```json\n' + json.dumps(QUOTE_FINAL) + '\n```'), 200)):
            with self.subTest(status=status):
                client = self.client()
                transport = self.fake_response(client, response, status)
                with self.assertRaises(DomainError):
                    client.extract(SOURCE, requirement_id=uuid4(), project_id=uuid4(), base_revision_id=uuid4())
                transport.assert_called_once()

    def test_existing_qwen_native_wire_remains_byte_exact(self):
        client = self.client(SamplingProfile.QWEN38_NONTHINKING_LLAMA_CPP)
        transport = self.fake_response(client)
        client.complete(SOURCE, axis_convention="project_xy")
        old_sampling = dict(self.sampling, temperature=0.7, top_p=0.8, top_k=20)
        expected = {
            "model": "synthetic-test-model",
            "messages": [
                {"role": "system", "content": (self.root / "prompts/requirement_generation_v2_v2.txt").read_text()},
                {"role": "user", "content": json.dumps({"source_text": SOURCE, "axis_convention": "project_xy"}, ensure_ascii=False)},
            ],
            **old_sampling, "max_tokens": 768, "stream": False,
            "chat_template_kwargs": {"enable_thinking": False},
            "response_format": {"type": "json_schema", "json_schema": {"schema": client.schema}},
        }
        self.assertEqual(transport.call_args.args[0].data, json.dumps(expected, ensure_ascii=False).encode())


class ExaoneNativeProfileTests(unittest.TestCase):
    """Fake transport only; native sampler execution is a separate CPU gate."""
    root = Path(__file__).resolve().parents[1]
    sampling = {
        "temperature": 0.6, "top_p": 0.95, "top_k": 20, "min_p": 0.0,
        "presence_penalty": 1.5, "frequency_penalty": 0.0,
        "repeat_penalty": 1.0, "repeat_last_n": 64, "seed": 42,
        "samplers": ["penalties", "top_k", "top_p", "min_p", "temperature"],
    }
    # Reuse the response fixture without inheriting another TestCase's tests.
    fake_response = GemmaNativeProfileTests.fake_response

    def client(self, profile=SamplingProfile.EXAONE45_NONTHINKING_LLAMA_CPP):
        return LocalRequirementClient(
            "http://127.0.0.1:8003", "synthetic-test-model", protocol="llama_cpp_json_schema",
            sampling_profile=profile, generation_contract="2.0",
            prompt_path=self.root / "prompts/requirement_generation_v2_v2.txt",
            schema_path=self.root / "schemas/requirement_generation_v2_decision_branches.schema.json")

    def test_exaone_wire_activates_presence_penalty_and_preserves_quote_conversion(self):
        for profile in (SamplingProfile.EXAONE45_NONTHINKING_LLAMA_CPP, "exaone45_nonthinking_llama_cpp"):
            with self.subTest(profile=profile):
                client = self.client(profile)
                transport = self.fake_response(client)
                result = client.extract(SOURCE, axis_convention="project_xy", requirement_id=uuid4(),
                                        project_id=uuid4(), base_revision_id=uuid4())
                transport.assert_called_once()
                request = json.loads(transport.call_args.args[0].data)
                self.assertEqual({key: request[key] for key in self.sampling}, self.sampling)
                self.assertEqual(request["chat_template_kwargs"], {"enable_thinking": False})
                self.assertEqual(request["response_format"]["json_schema"]["schema"], client.schema)
                self.assertEqual(request["max_tokens"], 768)
                self.assertFalse(request["stream"])
                self.assertFalse(client.enable_thinking)
                self.assertEqual(result.operation.dx.metres, 1)
                self.assertEqual(result.target_description, "회의실 책상")
                for absent in ("guided_json", "structured_outputs", "repetition_penalty", "reasoning_parser"):
                    self.assertNotIn(absent, request)

    def test_exaone_profile_is_native_only_and_never_selected_by_model_name(self):
        with patch("neurobuild.infrastructure.local_model.build_opener") as opener:
            for protocol in ("legacy_guided_json", "structured_outputs"):
                with self.subTest(protocol=protocol), self.assertRaises(DomainError) as caught:
                    LocalRequirementClient("http://127.0.0.1:8003", "model", protocol=protocol,
                                           sampling_profile="exaone45_nonthinking_llama_cpp")
                self.assertEqual(caught.exception.code, "LOCAL_MODEL_CONFIG_INVALID")
            for profile in ("EXAONE45_NONTHINKING_LLAMA_CPP", "exaone45_nonthinking_llama_cpp ", True):
                with self.subTest(profile=profile), self.assertRaises(DomainError):
                    self.client(profile)
            opener.assert_not_called()
        default = LocalRequirementClient("http://127.0.0.1:8003", "LGAI-EXAONE/EXAONE-4.5-33B-GGUF")
        self.assertIs(default.sampling_profile, SamplingProfile.LEGACY_GREEDY)

    def test_exaone_sampler_metadata_cannot_disable_penalties_in_next_request(self):
        client = self.client()
        copied = client.sampling_parameters
        copied["samplers"].clear()
        copied["repeat_last_n"] = 0
        copied["presence_penalty"] = 0
        with self.assertRaises(AttributeError):
            client.sampling_profile = SamplingProfile.LEGACY_GREEDY
        transport = self.fake_response(client)
        client.complete(SOURCE)
        request = json.loads(transport.call_args.args[0].data)
        self.assertEqual({key: request[key] for key in self.sampling}, self.sampling)

    def test_exaone_separate_reasoning_is_discarded_without_logging(self):
        client = self.client()
        response = envelope(json.dumps(QUOTE_FINAL))
        response["choices"][0]["message"]["reasoning_content"] = "<think>DO_NOT_ECHO_SECRET</think>"
        transport = self.fake_response(client, response)
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            completion = client.complete(SOURCE)
        transport.assert_called_once()
        self.assertEqual(json.loads(completion.content), QUOTE_FINAL)
        self.assertFalse(hasattr(completion, "reasoning_content"))
        self.assertNotIn("DO_NOT_ECHO_SECRET", repr(completion))
        self.assertEqual(out.getvalue() + err.getvalue(), "")

    def test_exaone_inline_thinking_is_rejected_without_repair_or_retry(self):
        for marker in ("<think>", "</think>", "<THINK>", "</THINK>"):
            with self.subTest(marker=marker):
                client = self.client()
                transport = self.fake_response(client, envelope(marker + "DO_NOT_ECHO_SECRET" + json.dumps(QUOTE_FINAL)))
                with self.assertRaises(DomainError) as caught:
                    client.complete(SOURCE)
                self.assertEqual(caught.exception.code, "LOCAL_MODEL_REASONING_CONTENT")
                self.assertNotIn("DO_NOT_ECHO_SECRET", str(caught.exception))
                transport.assert_called_once()

    def test_exaone_transport_failure_or_nonfinal_output_never_retries(self):
        truncated = envelope(json.dumps(QUOTE_FINAL))
        truncated["choices"][0]["finish_reason"] = "length"
        no_final = envelope()
        no_final["choices"][0]["message"] = {"role": "assistant", "content": None,
                                               "reasoning_content": "DO_NOT_ECHO_SECRET"}
        for response, status in (({"error": "DO_NOT_ECHO_SECRET"}, 400), (truncated, 200), (no_final, 200),
                                 (envelope('```json\n' + json.dumps(QUOTE_FINAL) + '\n```'), 200)):
            with self.subTest(status=status, response=response):
                client = self.client()
                transport = self.fake_response(client, response, status)
                with self.assertRaises(DomainError):
                    client.extract(SOURCE, requirement_id=uuid4(), project_id=uuid4(), base_revision_id=uuid4())
                transport.assert_called_once()


class Qwen36NativeProfileTests(unittest.TestCase):
    root = Path(__file__).resolve().parents[1]
    fake_response = GemmaNativeProfileTests.fake_response

    def client(self, profile=SamplingProfile.QWEN36_NONTHINKING_LLAMA_CPP):
        return LocalRequirementClient(
            "http://127.0.0.1:8003", "synthetic-test-model", protocol="llama_cpp_json_schema",
            sampling_profile=profile, generation_contract="2.0",
            prompt_path=self.root / "prompts/requirement_generation_v2_v2.txt",
            schema_path=self.root / "schemas/requirement_generation_v2_decision_branches.schema.json")

    def test_qwen36_wire_keeps_presence_active_and_extracts_exact_quotes(self):
        for profile in (SamplingProfile.QWEN36_NONTHINKING_LLAMA_CPP, "qwen36_nonthinking_llama_cpp"):
            with self.subTest(profile=profile):
                client = self.client(profile)
                # Mutating returned metadata must not silently disable penalties.
                copied = client.sampling_parameters
                copied["samplers"].clear()
                copied["repeat_last_n"] = 0
                transport = self.fake_response(client)
                result = client.extract(SOURCE, axis_convention="project_xy", requirement_id=uuid4(),
                                        project_id=uuid4(), base_revision_id=uuid4())
                transport.assert_called_once()
                request = json.loads(transport.call_args.args[0].data)
                self.assertEqual(request["temperature"], 0.7)
                self.assertEqual(request["top_p"], 0.8)
                self.assertEqual(request["top_k"], 20)
                self.assertEqual(request["min_p"], 0.0)
                self.assertEqual(request["presence_penalty"], 1.5)
                self.assertEqual(request["frequency_penalty"], 0.0)
                self.assertEqual(request["repeat_penalty"], 1.0)
                self.assertEqual(request["repeat_last_n"], 64)
                self.assertEqual(request["seed"], 42)
                self.assertEqual(request["samplers"], ["penalties", "top_k", "top_p", "min_p", "temperature"])
                self.assertEqual(request["chat_template_kwargs"], {"enable_thinking": False})
                self.assertEqual(request["response_format"]["json_schema"]["schema"], client.schema)
                self.assertFalse(client.enable_thinking)
                self.assertEqual(result.operation.dx.metres, 1)
                self.assertEqual(result.target_description, "회의실 책상")
                self.assertNotIn("repetition_penalty", request)

    def test_qwen36_profile_requires_native_protocol_and_explicit_selection(self):
        with patch("neurobuild.infrastructure.local_model.build_opener") as opener:
            for protocol in ("legacy_guided_json", "structured_outputs"):
                with self.subTest(protocol=protocol), self.assertRaises(DomainError) as caught:
                    LocalRequirementClient("http://127.0.0.1:8003", "model", protocol=protocol,
                                           sampling_profile="qwen36_nonthinking_llama_cpp")
                self.assertEqual(caught.exception.code, "LOCAL_MODEL_CONFIG_INVALID")
            opener.assert_not_called()
        default = LocalRequirementClient("http://127.0.0.1:8003", "ggml-org/Qwen3.6-35B-A3B-GGUF")
        self.assertIs(default.sampling_profile, SamplingProfile.LEGACY_GREEDY)
        previous = self.client(SamplingProfile.QWEN38_NONTHINKING_LLAMA_CPP)
        self.assertEqual(previous.sampling_parameters["presence_penalty"], 0.0)
        self.assertEqual(previous.sampling_parameters["repeat_last_n"], 0)


class GlmFlashNativeProfileTests(unittest.TestCase):
    """New profile's fake transport contract; no native sampler execution."""
    root = Path(__file__).resolve().parents[1]
    sampling = {
        "temperature": 1.0, "top_p": 0.95, "top_k": 0, "min_p": 0.0,
        "presence_penalty": 0.0, "frequency_penalty": 0.0,
        "repeat_penalty": 1.0, "repeat_last_n": 0, "seed": 42,
        "samplers": ["temperature", "top_k", "top_p", "min_p"],
    }
    fake_response = GemmaNativeProfileTests.fake_response

    def client(self, profile=SamplingProfile.GLM47_FLASH_NONTHINKING_LLAMA_CPP):
        return LocalRequirementClient(
            "http://127.0.0.1:8003", "synthetic-test-model", protocol="llama_cpp_json_schema",
            sampling_profile=profile, generation_contract="2.0",
            prompt_path=self.root / "prompts/requirement_generation_v2_v2.txt",
            schema_path=self.root / "schemas/requirement_generation_v2_decision_branches.schema.json")

    def test_glm_wire_and_quote_conversion_are_explicit(self):
        for profile in (SamplingProfile.GLM47_FLASH_NONTHINKING_LLAMA_CPP, "glm47_flash_nonthinking_llama_cpp"):
            with self.subTest(profile=profile):
                client = self.client(profile)
                transport = self.fake_response(client)
                result = client.extract(SOURCE, axis_convention="project_xy", requirement_id=uuid4(),
                                        project_id=uuid4(), base_revision_id=uuid4())
                transport.assert_called_once()
                expected = {
                    "model": "synthetic-test-model",
                    "messages": [
                        {"role": "system", "content": (self.root / "prompts/requirement_generation_v2_v2.txt").read_text()},
                        {"role": "user", "content": json.dumps(
                            {"source_text": SOURCE, "axis_convention": "project_xy"}, ensure_ascii=False)},
                    ],
                    **self.sampling, "max_tokens": 768, "stream": False,
                    "chat_template_kwargs": {"enable_thinking": False},
                    "response_format": {"type": "json_schema", "json_schema": {"schema": client.schema}},
                }
                self.assertEqual(transport.call_args.args[0].data, json.dumps(expected, ensure_ascii=False).encode())
                self.assertIs(client.sampling_profile, SamplingProfile.GLM47_FLASH_NONTHINKING_LLAMA_CPP)
                self.assertFalse(client.enable_thinking)
                self.assertEqual(result.operation.dx.metres, 1)
                self.assertEqual(result.target_description, "회의실 책상")

    def test_glm_profile_is_native_only_and_never_selected_by_name(self):
        with patch("neurobuild.infrastructure.local_model.build_opener") as opener:
            for protocol in ("legacy_guided_json", "structured_outputs"):
                with self.subTest(protocol=protocol):
                    with self.assertRaises(DomainError) as caught:
                        LocalRequirementClient("http://127.0.0.1:8003", "model", protocol=protocol,
                                               sampling_profile="glm47_flash_nonthinking_llama_cpp")
                    self.assertEqual(caught.exception.code, "LOCAL_MODEL_CONFIG_INVALID")
            for profile in ("GLM47_FLASH_NONTHINKING_LLAMA_CPP", "glm47_flash_nonthinking_llama_cpp ", True):
                with self.subTest(profile=profile):
                    with self.assertRaises(DomainError) as caught:
                        self.client(profile)
                    self.assertEqual(caught.exception.code, "LOCAL_MODEL_CONFIG_INVALID")
            opener.assert_not_called()
        default = LocalRequirementClient("http://127.0.0.1:8003", "ggml-org/GLM-4.7-Flash-GGUF")
        self.assertIs(default.sampling_profile, SamplingProfile.LEGACY_GREEDY)

    def test_glm_sampler_copy_cannot_change_next_request(self):
        client = self.client()
        copied = client.sampling_parameters
        copied["samplers"].clear()
        copied["top_k"] = 40
        copied["repeat_last_n"] = 64
        with self.assertRaises(AttributeError):
            client.sampling_profile = SamplingProfile.LEGACY_GREEDY
        transport = self.fake_response(client)
        client.complete(SOURCE)
        request = json.loads(transport.call_args.args[0].data)
        self.assertEqual({key: request[key] for key in self.sampling}, self.sampling)

    def test_glm_separate_reasoning_is_discarded_without_logging(self):
        client = self.client()
        response = envelope(json.dumps(QUOTE_FINAL))
        response["choices"][0]["message"]["reasoning_content"] = "<think>DO_NOT_ECHO_SECRET</think>"
        transport = self.fake_response(client, response)
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            completion = client.complete(SOURCE)
        transport.assert_called_once()
        self.assertEqual(json.loads(completion.content), QUOTE_FINAL)
        self.assertFalse(hasattr(completion, "reasoning_content"))
        self.assertNotIn("DO_NOT_ECHO_SECRET", repr(completion))
        self.assertEqual(out.getvalue() + err.getvalue(), "")

    def test_glm_inline_thinking_is_rejected_without_repair_or_retry(self):
        for marker in ("<think>", "</think>", "<THINK>", "</THINK>"):
            with self.subTest(marker=marker):
                client = self.client()
                transport = self.fake_response(client, envelope(marker + "DO_NOT_ECHO_SECRET" + json.dumps(QUOTE_FINAL)))
                with self.assertRaises(DomainError) as caught:
                    client.complete(SOURCE)
                self.assertEqual(caught.exception.code, "LOCAL_MODEL_REASONING_CONTENT")
                self.assertNotIn("DO_NOT_ECHO_SECRET", str(caught.exception))
                transport.assert_called_once()

    def test_glm_failure_and_nonfinal_content_never_retry(self):
        truncated = envelope(json.dumps(QUOTE_FINAL))
        truncated["choices"][0]["finish_reason"] = "length"
        no_final = envelope()
        no_final["choices"][0]["message"] = {"role": "assistant", "content": None,
                                               "reasoning_content": "DO_NOT_ECHO_SECRET"}
        for response, status in (({"error": "DO_NOT_ECHO_SECRET"}, 400), (truncated, 200), (no_final, 200),
                                 (envelope('```json\n' + json.dumps(QUOTE_FINAL) + '\n```'), 200)):
            with self.subTest(status=status, response=response):
                client = self.client()
                transport = self.fake_response(client, response, status)
                with self.assertRaises(DomainError) as caught:
                    client.extract(SOURCE, requirement_id=uuid4(), project_id=uuid4(), base_revision_id=uuid4())
                self.assertNotIn("DO_NOT_ECHO_SECRET", str(caught.exception))
                transport.assert_called_once()


if __name__ == "__main__":
    unittest.main()
