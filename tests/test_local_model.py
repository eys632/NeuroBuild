"""Real loopback HTTP tests with a fake model; no GPU or LLM accuracy claim."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import StringIO
import json
import os
from pathlib import Path
import socket
from tempfile import TemporaryDirectory
from threading import Thread
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

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
                    else:
                        self.assertEqual(request["structured_outputs"], {"json": expected_schema})
                        self.assertNotIn("guided_json", request)
                        self.assertNotIn("guided_decoding_backend", request)
                    self.assertNotIn("response_format", request)
                    self.assertEqual(request["chat_template_kwargs"], {"enable_thinking": False})
                    self.assertEqual(request["temperature"], 0)
        self.assertEqual(len(self.server.requests), 4)
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
        for client in clients:
            with self.subTest(profile=client.sampling_profile):
                client.complete(SOURCE, axis_convention="project_xy")
                self.assertIs(client.sampling_profile, SamplingProfile.LEGACY_GREEDY)
                self.assertEqual(client.sampling_parameters, {"temperature": 0, "seed": 42})
                self.assertEqual(self.server.request_bodies[-1], json.dumps(expected, ensure_ascii=False).encode("utf-8"))
        self.assertEqual(len(self.server.requests), 3)

    def test_qwen_sampling_sends_all_eight_values_with_each_explicit_schema_protocol(self):
        expected = {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0.0,
                    "presence_penalty": 1.5, "frequency_penalty": 0.0,
                    "repetition_penalty": 1.0, "seed": 42}
        schema = json.loads((Path(__file__).resolve().parents[1] / "schemas/semantic_requirement.schema.json").read_text())
        for protocol in StructuredOutputProtocol:
            for profile in (SamplingProfile.QWEN3_NONTHINKING_AWQ, "qwen3_nonthinking_awq"):
                with self.subTest(protocol=protocol, profile_type=type(profile).__name__):
                    client = LocalRequirementClient(self.base, "synthetic-test-model", protocol=protocol,
                                                    sampling_profile=profile)
                    result = client.extract(SOURCE, axis_convention="project_xy", requirement_id=uuid4(),
                                            project_id=uuid4(), base_revision_id=uuid4())
                    self.assertEqual(result.operation.dx.metres, 1)
                    self.assertIs(client.sampling_profile, SamplingProfile.QWEN3_NONTHINKING_AWQ)
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
                   "QWEN3_NONTHINKING_AWQ", "qwen3_nonthinking_awq ", StructuredOutputProtocol.LEGACY_GUIDED_JSON)
        for profile in invalid:
            with self.subTest(profile=profile), self.assertRaises(DomainError) as caught:
                LocalRequirementClient(self.base, "synthetic-test-model", sampling_profile=profile)
            self.assertEqual(caught.exception.code, "LOCAL_MODEL_CONFIG_INVALID")
        self.assertEqual(self.server.requests, [])

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
            for protocol in StructuredOutputProtocol:
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
                selected = "guided_json" if protocol is StructuredOutputProtocol.LEGACY_GUIDED_JSON else "structured_outputs"
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


if __name__ == "__main__":
    unittest.main()
