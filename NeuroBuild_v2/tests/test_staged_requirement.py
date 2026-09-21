"""Two-stage acceptance tests over real loopback HTTP, without model/GPU calls."""

from copy import deepcopy
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

from jsonschema import Draft202012Validator

from neurobuild.application.requirement_generation import GenerationContract
from neurobuild.domain.contracts import RequirementStatus
from neurobuild.domain.errors import DomainError
from neurobuild.infrastructure.local_model import SamplingProfile, StructuredOutputProtocol
from neurobuild.infrastructure.staged_requirement import LocalStagedRequirementClient, bind_extraction_schema
from tests.test_local_model import SOURCE, QUOTE_FINAL, envelope


ROOT = Path(__file__).resolve().parents[1]


def classification(decision="READY"):
    return {"schema_version": "classification-1.0", "decision": decision}


def response(value, **kwargs):
    content = value if type(value) is str else json.dumps(value, ensure_ascii=False)
    return {"body": json.dumps(envelope(content), ensure_ascii=False).encode("utf-8"), **kwargs}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        data = self.rfile.read(int(self.headers["Content-Length"]))
        self.server.requests.append(json.loads(data))
        item = self.server.responses.pop(0) if self.server.responses else {"status": 500, "body": b"UNPLANNED_REQUEST"}
        try:
            time.sleep(item.get("delay", 0))
            self.send_response(item.get("status", 200))
            self.send_header("Content-Type", "application/json")
            for key, value in item.get("headers", {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(item["body"])
        except (BrokenPipeError, ConnectionResetError):
            pass


class StagedRequirementTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.server.requests = []
        self.server.responses = []
        self.thread = Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.client = LocalStagedRequirementClient(self.base, "synthetic-test-model", timeout=1)
        self.ids = {key: uuid4() for key in ("requirement_id", "project_id", "base_revision_id")}

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=1)

    def queue(self, decision="READY", final=None):
        self.server.responses = [response(classification(decision)), response(final or QUOTE_FINAL)]

    def test_ready_uses_original_source_twice_and_only_code_owned_ids(self):
        for protocol in StructuredOutputProtocol:
            with self.subTest(protocol=protocol):
                self.queue()
                client = LocalStagedRequirementClient(self.base, "synthetic-test-model", protocol=protocol)
                requirement = client.extract(SOURCE, axis_convention="project_xy", **self.ids)
                self.assertIs(requirement.status, RequirementStatus.READY)
                self.assertEqual(requirement.requirement_id, self.ids["requirement_id"])
                self.assertEqual(requirement.operation.dx.metres, 1)
                self.assertEqual(requirement.source_text, SOURCE)
                first, second = self.server.requests[-2:]
                self.assertEqual(first["max_tokens"], 128)
                self.assertEqual(second["max_tokens"], 768)
                self.assertEqual(first["messages"][1]["content"], json.dumps(
                    {"source_text": SOURCE, "axis_convention": "project_xy"}, ensure_ascii=False))
                self.assertEqual(second["messages"][1]["content"], json.dumps(
                    {"source_text": SOURCE, "axis_convention": "project_xy", "classified_decision": "READY"},
                    ensure_ascii=False))
                for request in (first, second):
                    self.assertEqual(request["chat_template_kwargs"], {"enable_thinking": False})
                    self.assertNotIn("tools", request)
                    self.assertEqual(request["temperature"], 0)
                    self.assertEqual(request["seed"], 42)
                if protocol is StructuredOutputProtocol.LEGACY_GUIDED_JSON:
                    self.assertEqual(first["guided_json"], client.classification_schema)
                    self.assertEqual(second["guided_json"], client.schema_for_decision("READY"))
                    self.assertNotIn("structured_outputs", second)
                elif protocol is StructuredOutputProtocol.STRUCTURED_OUTPUTS:
                    self.assertEqual(second["structured_outputs"]["json"], client.schema_for_decision("READY"))
                    self.assertNotIn("guided_json", second)
                    self.assertNotIn("guided_decoding_backend", second)
                else:
                    self.assertEqual(first["response_format"], {
                        "type": "json_schema", "json_schema": {"schema": client.classification_schema}})
                    self.assertEqual(second["response_format"], {
                        "type": "json_schema", "json_schema": {"schema": client.schema_for_decision("READY")}})
                    for request in (first, second):
                        for absent in ("guided_json", "guided_decoding_backend", "structured_outputs"):
                            self.assertNotIn(absent, request)
        self.assertEqual(len(self.server.requests), 6)

    def test_both_nonready_decisions_remain_bound_and_have_no_operation(self):
        for decision, status in (("CLARIFICATION", RequirementStatus.CLARIFICATION),
                                 ("UNSUPPORTED", RequirementStatus.UNSUPPORTED)):
            with self.subTest(decision=decision):
                final = dict(QUOTE_FINAL, decision=decision, current_instruction_quote=None,
                             dx_evidence=None, dy_evidence=None, reason="추가 확인 또는 지원 밖 요청")
                self.queue(decision, final)
                requirement = self.client.extract(SOURCE, axis_convention="project_xy", **self.ids)
                self.assertIs(requirement.status, status)
                self.assertIsNone(requirement.operation)
                schema = self.server.requests[-1]["guided_json"]
                self.assertEqual(len(schema["anyOf"]), 1)
                self.assertEqual(schema["anyOf"][0]["properties"]["decision"]["enum"], [decision])
                self.assertFalse(Draft202012Validator(schema).is_valid(QUOTE_FINAL))

    def test_invalid_classifier_never_requests_extraction_and_retains_observed_content(self):
        invalid = ["{", "[]", "null", '{"schema_version":"classification-1.0","decision":"READY","decision":"UNSUPPORTED"}',
                   '{"schema_version":"classification-1.0","decision":NaN}',
                   classification("UNKNOWN"), {"schema_version": "2.0", "decision": "READY"},
                   dict(classification(), approved=True), {"decision": "READY"}]
        for value in invalid:
            with self.subTest(value=value):
                self.server.responses = [response(value)]
                count = len(self.server.requests)
                result = self.client.complete_staged(SOURCE)
                self.assertEqual(result.error_code, "INVALID_MODEL_OUTPUT")
                self.assertIsNotNone(result.classification)
                self.assertIsNone(result.extraction)
                self.assertEqual(len(self.server.requests), count + 1)

    def test_second_stage_cannot_reclassify_or_add_authority(self):
        invalid = [dict(QUOTE_FINAL, decision="CLARIFICATION", current_instruction_quote=None, dx_evidence=None, reason="확인"),
                   dict(QUOTE_FINAL, approved=True), dict(QUOTE_FINAL, GlobalId="0" * 22),
                   dict(QUOTE_FINAL, schema_version="1.0"), dict(QUOTE_FINAL, dx_evidence=None),
                   '{"schema_version":"2.0","decision":"READY","decision":"UNSUPPORTED"}', "NaN", "not JSON"]
        for final in invalid:
            with self.subTest(final=final):
                self.queue(final=final)
                count = len(self.server.requests)
                result = self.client.complete_staged(SOURCE)
                self.assertEqual(result.error_code, "INVALID_MODEL_OUTPUT")
                self.assertEqual(json.loads(result.classification.content)["decision"], "READY")
                self.assertIsNotNone(result.extraction)
                self.assertEqual(len(self.server.requests), count + 2)
        self.queue("UNSUPPORTED", QUOTE_FINAL)
        result = self.client.complete_staged(SOURCE)
        self.assertEqual(result.error_code, "INVALID_MODEL_OUTPUT")
        self.assertEqual(json.loads(result.classification.content)["decision"], "UNSUPPORTED")

    def test_schema_success_is_not_grounding_success(self):
        final = dict(QUOTE_FINAL, dx_evidence="X축 양의 방향으로 9m")
        self.queue(final=final)
        self.assertIsNone(self.client.complete_staged(SOURCE, axis_convention="project_xy").error_code)
        self.queue(final=final)
        with self.assertRaises(DomainError) as caught:
            self.client.extract(SOURCE, axis_convention="project_xy", **self.ids)
        self.assertEqual(caught.exception.code, "UNGROUNDED_REQUIREMENT")
        self.assertEqual(len(self.server.requests), 4)

    def test_later_transport_failure_retains_classifier_without_retry_or_secret_echo(self):
        cases = [(500, {}, "LOCAL_MODEL_HTTP_ERROR"),
                 (302, {"Location": self.base + "/redirect"}, "LOCAL_MODEL_HTTP_ERROR")]
        for status, headers, expected in cases:
            with self.subTest(status=status):
                self.server.responses = [response(classification()),
                    {"status": status, "headers": headers, "body": b"DO_NOT_ECHO_SECRET"}]
                count = len(self.server.requests)
                result = self.client.complete_staged(SOURCE)
                self.assertEqual(result.error_code, expected)
                self.assertIsNone(result.extraction)
                self.assertEqual(json.loads(result.classification.content)["decision"], "READY")
                self.assertNotIn("DO_NOT_ECHO_SECRET", repr(result))
                self.assertEqual(len(self.server.requests), count + 2)

    def test_first_stage_failure_never_requests_second(self):
        self.server.responses = [{"status": 400, "body": b"DO_NOT_ECHO_SECRET"}]
        result = self.client.complete_staged(SOURCE)
        self.assertEqual(result.error_code, "LOCAL_MODEL_HTTP_ERROR")
        self.assertIsNone(result.classification)
        self.assertIsNone(result.extraction)
        self.assertEqual(len(self.server.requests), 1)

    def test_second_stage_timeout_preserves_first_and_each_call_is_bounded(self):
        self.server.responses = [response(classification()), response(QUOTE_FINAL, delay=0.15)]
        client = LocalStagedRequirementClient(self.base, "synthetic-test-model", timeout=0.04)
        started = time.monotonic()
        result = client.complete_staged(SOURCE)
        self.assertEqual(result.error_code, "LOCAL_MODEL_TIMEOUT")
        self.assertIsNotNone(result.classification)
        self.assertIsNone(result.extraction)
        self.assertLess(time.monotonic() - started, 0.5)
        self.assertEqual(len(self.server.requests), 2)

    def test_truncation_reasoning_and_oversize_do_not_erase_first_stage(self):
        truncated = envelope(json.dumps(QUOTE_FINAL))
        truncated["choices"][0]["finish_reason"] = "length"
        cases = [(json.dumps(truncated).encode(), "LOCAL_MODEL_TRUNCATED"),
                 (response("<think>DO_NOT_ECHO_SECRET</think>")["body"], "LOCAL_MODEL_REASONING_CONTENT"),
                 (b" " * 262145, "LOCAL_MODEL_RESPONSE_TOO_LARGE")]
        for body, expected in cases:
            with self.subTest(expected=expected):
                self.server.responses = [response(classification()), {"body": body}]
                result = self.client.complete_staged(SOURCE)
                self.assertEqual(result.error_code, expected)
                self.assertIsNotNone(result.classification)
                self.assertIsNone(result.extraction)
                self.assertNotIn("DO_NOT_ECHO_SECRET", repr(result))

    def test_metadata_is_detached_and_actual_schemas_match_recorded_hashes(self):
        self.assertEqual(self.client.pipeline, "staged_v1")
        self.assertIs(self.client.generation_contract, GenerationContract.QUOTES)
        with self.assertRaises(AttributeError):
            self.client.pipeline = "single"
        schema = self.client.schema_for_decision("READY")
        expected = sha256(json.dumps(schema, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(self.client.effective_schema_sha256["READY"], expected)
        schema["anyOf"].clear()
        self.client.classification_schema["properties"].clear()
        self.client.effective_schema_sha256.clear()
        self.client.sampling_parameters["temperature"] = 99
        self.queue()
        self.assertIsNone(self.client.complete_staged(SOURCE).error_code)
        self.assertEqual(len(self.server.requests[-1]["guided_json"]["anyOf"]), 3)
        self.assertEqual(self.server.requests[-1]["temperature"], 0)
        self.assertEqual(len(self.server.requests[-2]["guided_json"]["properties"]), 2)

    def test_explicit_sampling_and_thinking_are_shared_not_inferred_per_stage(self):
        for profile in (SamplingProfile.QWEN3_NONTHINKING, SamplingProfile.QWEN3_THINKING_AWQ):
            with self.subTest(profile=profile):
                self.queue()
                client = LocalStagedRequirementClient(self.base, "synthetic-test-model", sampling_profile=profile)
                self.assertIsNone(client.complete_staged(SOURCE).error_code)
                for request in self.server.requests[-2:]:
                    for key, value in client.sampling_parameters.items():
                        self.assertEqual(request[key], value)
                    self.assertEqual(request["chat_template_kwargs"]["enable_thinking"], client.enable_thinking)

    def test_input_configuration_and_ids_fail_before_http(self):
        for cap in (True, 0, 129, "128"):
            with self.subTest(cap=cap), self.assertRaises(DomainError) as caught:
                LocalStagedRequirementClient(self.base, "synthetic-test-model", classification_max_tokens=cap)
            self.assertEqual(caught.exception.code, "LOCAL_MODEL_CONFIG_INVALID")
        for source, axis in (("", None), (SOURCE, "camera")):
            result = self.client.complete_staged(source, axis_convention=axis)
            self.assertEqual(result.error_code, "LOCAL_MODEL_INPUT_INVALID")
            self.assertIsNone(result.classification)
        with self.assertRaises(DomainError) as caught:
            self.client.extract(SOURCE, **dict(self.ids, requirement_id="user-controlled"))
        self.assertEqual(caught.exception.code, "LOCAL_MODEL_INPUT_INVALID")
        self.assertEqual(self.server.requests, [])

    def test_weakened_template_wrong_version_and_classifier_schema_are_rejected(self):
        template = self.client._extractor.schema
        changed = []
        value = deepcopy(template); value["anyOf"][0]["additionalProperties"] = True; changed.append(value)
        value = deepcopy(template); value["anyOf"][0]["properties"]["decision"]["enum"] = ["READY", "UNSUPPORTED"]; changed.append(value)
        value = deepcopy(template); value["properties"]["schema_version"]["enum"] = ["1.0"]; changed.append(value)
        value = deepcopy(template); value["anyOf"][1] = deepcopy(value["anyOf"][0]); changed.append(value)
        for value in changed:
            with self.subTest(schema=value), self.assertRaises(DomainError) as caught:
                bind_extraction_schema(value, "READY")
            self.assertEqual(caught.exception.code, "LOCAL_MODEL_CONFIG_INVALID")
        with TemporaryDirectory() as directory:
            path = Path(directory) / "schema.json"
            schema = self.client.classification_schema
            schema["additionalProperties"] = True
            path.write_text(json.dumps(schema))
            with self.assertRaises(DomainError) as caught:
                LocalStagedRequirementClient(self.base, "synthetic-test-model", classification_schema_path=path)
            self.assertEqual(caught.exception.code, "LOCAL_MODEL_CONFIG_INVALID")
        self.assertEqual(self.server.requests, [])

    def test_interrupts_are_never_swallowed_in_either_stage(self):
        for error in (KeyboardInterrupt, SystemExit):
            with self.subTest(error=error):
                with patch.object(self.client._classifier, "complete", side_effect=error):
                    with self.assertRaises(error):
                        self.client.complete_staged(SOURCE)
                self.server.responses = [response(classification())]
                with patch.object(self.client._extractor, "_complete", side_effect=error):
                    with self.assertRaises(error):
                        self.client.complete_staged(SOURCE)

    def test_unexpected_downstream_error_preserves_ready_without_exposing_exception(self):
        self.server.responses = [response(classification())]
        with patch.object(self.client._extractor, "_complete", side_effect=RuntimeError("DO_NOT_ECHO_SECRET")):
            result = self.client.complete_staged(SOURCE)
        self.assertEqual(result.error_code, "LOCAL_MODEL_RESPONSE_INVALID")
        self.assertEqual(json.loads(result.classification.content)["decision"], "READY")
        self.assertIsNone(result.extraction)
        self.assertNotIn("DO_NOT_ECHO_SECRET", repr(result))
        self.assertEqual(len(self.server.requests), 1)


if __name__ == "__main__":
    unittest.main()
