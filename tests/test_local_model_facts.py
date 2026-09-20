"""Actual loopback HTTP with synthetic facts JSON; no model/GPU quality claim."""

from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread
import unittest
from uuid import uuid4

from neurobuild.application.requirement_generation import GenerationContract
from neurobuild.domain.errors import DomainError
from neurobuild.infrastructure.local_model import (
    LocalRequirementClient, SamplingProfile, StructuredOutputProtocol,
)
from tests.test_local_model import Handler, envelope


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "실험실 낮은 작업대를 X축 +12mm, Y축 음의 방향으로 7cm 이동해줘."
FACTS_FINAL = {
    "schema_version": "3.0",
    "facts": {
        "intent": "CURRENT_MOVE", "condition": "NONE", "condition_quote": None,
        "target_class": "FURNITURE", "target_count": "ONE",
        "motion": "ONE_RELATIVE_XY_VECTOR", "axis_completeness": "EXPLICIT",
        "authority": "NONE", "authority_quote": None,
        "selection_scope_quote": "실험실", "selection_exclusion_quote": None,
    },
    "target_selection_quote": "실험실 낮은 작업대", "current_instruction_quote": SOURCE,
    "dx_evidence": "X축 +12mm", "dy_evidence": "Y축 음의 방향으로 7cm",
    "reason": None, "decision": "READY",
}


class LocalModelFactsClientTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.server.requests = []
        self.server.request_bodies = []
        self.server.status = 200
        self.server.headers = {"Content-Type": "application/json"}
        self.server.delay = self.server.trickle = 0
        self.respond(FACTS_FINAL)
        self.thread = Thread(target=self.server.serve_forever,
                             kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.ids = {key: uuid4() for key in ("requirement_id", "project_id", "base_revision_id")}

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=1)

    def respond(self, value):
        self.server.body = json.dumps(envelope(json.dumps(value, ensure_ascii=False)),
                                      ensure_ascii=False).encode("utf-8")

    def client(self, protocol, **overrides):
        options = dict(generation_contract=GenerationContract.FACTS, protocol=protocol,
                       sampling_profile=SamplingProfile.LEGACY_GREEDY, max_tokens=1024, timeout=1)
        options.update(overrides)
        return LocalRequirementClient(self.base, "synthetic-test-model", **options)

    def extract(self, client, source=SOURCE):
        return client.extract(source, axis_convention="project_xy", **self.ids)

    def test_actual_extract_uses_facts_contract_and_one_request_in_both_protocols(self):
        prompt = (ROOT / "prompts/requirement_generation_v3_v1.txt").read_bytes()
        schema = (ROOT / "schemas/requirement_generation_v3.schema.json").read_bytes()
        results = []
        for protocol in StructuredOutputProtocol:
            for configured in (GenerationContract.FACTS, "3.0"):
                with self.subTest(protocol=protocol, configured=configured):
                    client = self.client(protocol, generation_contract=configured)
                    before = len(self.server.requests)
                    result = self.extract(client)
                    results.append(result)
                    self.assertEqual(len(self.server.requests), before + 1)
                    self.assertIs(client.generation_contract, GenerationContract.FACTS)
                    self.assertIs(client.protocol, protocol)
                    self.assertEqual(client.prompt_sha256, sha256(prompt).hexdigest())
                    self.assertEqual(client.schema_sha256, sha256(schema).hexdigest())
                    path, headers, request = self.server.requests[-1]
                    self.assertEqual(path, "/v1/chat/completions")
                    self.assertEqual(headers["Content-Type"], "application/json")
                    self.assertEqual(request["model"], "synthetic-test-model")
                    self.assertEqual(request["max_tokens"], 1024)
                    self.assertEqual(request["temperature"], 0)
                    self.assertEqual(request["seed"], 42)
                    self.assertIs(request["stream"], False)
                    self.assertEqual(request["chat_template_kwargs"], {"enable_thinking": False})
                    self.assertIs(client.enable_thinking, False)
                    self.assertEqual(request["messages"], [
                        {"role": "system", "content": prompt.decode()},
                        {"role": "user", "content": json.dumps(
                            {"source_text": SOURCE, "axis_convention": "project_xy"}, ensure_ascii=False)},
                    ])
                    if protocol is StructuredOutputProtocol.LEGACY_GUIDED_JSON:
                        self.assertEqual(request["guided_json"], json.loads(schema))
                        self.assertEqual(request["guided_decoding_backend"], "xgrammar:no-fallback")
                        self.assertNotIn("structured_outputs", request)
                    else:
                        self.assertEqual(request["structured_outputs"], {"json": json.loads(schema)})
                        self.assertNotIn("guided_json", request)
                        self.assertNotIn("guided_decoding_backend", request)
                    for absent in ("generation_contract", "response_format", "classified_decision",
                                   "top_p", "top_k", "presence_penalty", "repetition_penalty"):
                        self.assertNotIn(absent, request)
        self.assertEqual(len(results), 4)
        self.assertTrue(all(result == results[0] for result in results))
        result = results[0]
        self.assertEqual(result.status.value, "READY")
        self.assertEqual(result.source_text, SOURCE)
        self.assertEqual(result.target_description, "실험실 낮은 작업대")
        self.assertEqual(result.operation.dx.metres, Decimal("0.012"))
        self.assertEqual(result.operation.dy.metres, Decimal("-0.07"))
        self.assertEqual(result.operation.dx.value, Decimal("12"))
        for key, value in self.ids.items():
            self.assertEqual(getattr(result, key), value)
        self.assertFalse(hasattr(result, "approval"))
        self.assertFalse(hasattr(result, "global_id"))

    def test_actual_nonready_extract_preserves_condition_and_never_promotes(self):
        condition = "통로가 비어 있을 때만"
        source = condition + " " + SOURCE
        value = deepcopy(FACTS_FINAL)
        value["facts"].update(condition="UNRESOLVED", condition_quote=condition)
        value.update(decision="CLARIFICATION", current_instruction_quote=None,
                     dx_evidence=None, dy_evidence=None, reason="원문의 통로 조건을 확인해야 합니다.")
        self.respond(value)
        for protocol in StructuredOutputProtocol:
            with self.subTest(protocol=protocol):
                before = len(self.server.requests)
                result = self.extract(self.client(protocol), source)
                self.assertEqual(len(self.server.requests), before + 1)
                self.assertEqual(result.status.value, "CLARIFICATION")
                self.assertIsNone(result.operation)
                self.assertEqual(result.target_description, FACTS_FINAL["target_selection_quote"])
                self.assertEqual(result.source_text, source)

    def test_wrong_facts_reject_original_ready_after_one_http_call_without_retry(self):
        changes = (
            {"intent": "NEGATED_MOVE"},
            {"target_count": "MULTIPLE"},
            {"authority": "HISTORICAL_OR_QUOTED_ONLY", "authority_quote": None},
        )
        for protocol in StructuredOutputProtocol:
            for change in changes:
                with self.subTest(protocol=protocol, facts=change):
                    value = deepcopy(FACTS_FINAL)
                    value["facts"].update(change)
                    self.respond(value)
                    original_response = self.server.body
                    before = len(self.server.requests)
                    with self.assertRaises(DomainError) as caught:
                        self.extract(self.client(protocol))
                    self.assertEqual(caught.exception.code, "INVALID_MODEL_OUTPUT")
                    self.assertEqual(len(self.server.requests), before + 1)
                    self.assertEqual(self.server.body, original_response)
                    self.assertEqual(value["decision"], "READY")

    def test_source_grounding_failure_after_projection_does_not_retry_or_repair(self):
        value = deepcopy(FACTS_FINAL)
        value["dx_evidence"] = "X축 +13mm"
        self.respond(value)
        for protocol in StructuredOutputProtocol:
            with self.subTest(protocol=protocol):
                before = len(self.server.requests)
                with self.assertRaises(DomainError) as caught:
                    self.extract(self.client(protocol))
                self.assertEqual(caught.exception.code, "UNGROUNDED_REQUIREMENT")
                self.assertEqual(len(self.server.requests), before + 1)

    def test_mismatched_schema_version_rejects_configuration_before_http(self):
        for protocol in StructuredOutputProtocol:
            for schema in ("semantic_requirement.schema.json", "requirement_generation_v2.schema.json",
                           "requirement_generation_v2_decision_branches.schema.json"):
                with self.subTest(protocol=protocol, schema=schema):
                    with self.assertRaises(DomainError) as caught:
                        self.client(protocol, schema_path=ROOT / "schemas" / schema)
                    self.assertEqual(caught.exception.code, "LOCAL_MODEL_CONFIG_INVALID")
        self.assertEqual(self.server.requests, [])

    def test_version_two_response_is_not_automatically_accepted_in_facts_mode(self):
        value = {key: deepcopy(item) for key, item in FACTS_FINAL.items() if key != "facts"}
        value["schema_version"] = "2.0"
        self.respond(value)
        for protocol in StructuredOutputProtocol:
            with self.subTest(protocol=protocol):
                before = len(self.server.requests)
                with self.assertRaises(DomainError) as caught:
                    self.extract(self.client(protocol))
                self.assertEqual(caught.exception.code, "INVALID_MODEL_OUTPUT")
                self.assertEqual(len(self.server.requests), before + 1)


if __name__ == "__main__":
    unittest.main()
