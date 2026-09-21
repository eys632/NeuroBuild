"""Staged accounting must retain errors and early READY false positives."""

import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator

from neurobuild.application.requirement_generation import GenerationContract
from neurobuild.infrastructure.local_model import Completion
from scripts.evaluate_requirements import ROOT, build_manifest, evaluate_trial, summarize
from tests.test_requirement_generation_evaluation import CASES, quoted


CLASSIFICATION = json.loads((ROOT / "schemas/requirement_classification.schema.json").read_text())
EXTRACTION = json.loads((ROOT / "schemas/requirement_generation_v2_decision_branches.schema.json").read_text())


def completion(value, *, model="synthetic"):
    return Completion(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False),
                      {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}, 0.25, model)


def classifier(decision="READY"):
    return completion({"schema_version": "classification-1.0", "decision": decision})


class StagedFake:
    pipeline = "staged_v1"
    model = "synthetic"
    generation_contract = GenerationContract.QUOTES
    classification_schema = CLASSIFICATION

    def __init__(self, classification, extraction, error=None):
        self.result = SimpleNamespace(classification=classification, extraction=extraction, error_code=error)

    def complete_staged(self, source_text, *, axis_convention=None):
        return self.result

    def schema_for_decision(self, decision):
        return {"allOf": [EXTRACTION, {"properties": {"decision": {"const": decision}}}]}


def measured(client, case=None):
    return evaluate_trial(client, case or CASES["A01"], Draft202012Validator(EXTRACTION), 1, run_id="staged-test")


class StagedEvaluationTests(unittest.TestCase):
    def test_success_uses_canonical_parser_and_sums_both_calls(self):
        row = measured(StagedFake(classifier(), completion(quoted(CASES["A01"]))))
        self.assertTrue(row["semantic_rubric_correct"])
        self.assertEqual(row["normalized_operation_metres"], {"dx": "1", "dy": "0"})
        self.assertEqual(row["usage"]["total_tokens"], 30)
        self.assertEqual(row["transport_latency_seconds"], 0.5)
        self.assertEqual(row["classification_output"]["decision"], "READY")
        self.assertEqual(row["semantic_output"]["schema_version"], "1.0")

    def test_classifier_ready_survives_each_downstream_failure(self):
        for error in ("LOCAL_MODEL_TIMEOUT", "LOCAL_MODEL_TRUNCATED", "LOCAL_MODEL_HTTP_ERROR", "INVALID_MODEL_OUTPUT"):
            with self.subTest(error=error):
                row = measured(StagedFake(classifier(), None, error), CASES["B01"])
                self.assertEqual(row["raw_model_decision"], "READY")
                self.assertFalse(row["parser_accepted"])
                self.assertFalse(row["schema_valid"])
                self.assertIsNone(row["transport_latency_seconds"])
                self.assertEqual(row["error_code"], error)
                metrics = summarize([row])
                self.assertEqual(metrics["critical_fp_model_ready"]["numerator"], 1)
                self.assertEqual(metrics["critical_fp_model_ready"]["denominator"], 1)
                self.assertEqual(metrics["semantic_rubric_correct"]["denominator"], 1)

    def test_malformed_classifier_preserves_observed_decision_but_not_unknown_fields(self):
        raw = completion({"decision": "READY", "reasoning": "DO_NOT_SAVE"})
        row = measured(StagedFake(raw, None, "INVALID_MODEL_OUTPUT"), CASES["B01"])
        self.assertTrue(row["classification_json_valid"])
        self.assertFalse(row["classification_schema_valid"])
        self.assertIsNone(row["classification_output"])
        self.assertNotIn("DO_NOT_SAVE", json.dumps(row))
        self.assertEqual(summarize([row])["critical_fp_model_ready"]["numerator"], 1)

    def test_extractor_cannot_change_classifier_decision_even_with_valid_quotes(self):
        row = measured(StagedFake(classifier("UNSUPPORTED"), completion(quoted(CASES["A01"]))))
        self.assertEqual(row["raw_model_decision"], "UNSUPPORTED")
        self.assertTrue(row["generation_schema_valid"])
        self.assertFalse(row["extraction_schema_valid"])
        self.assertFalse(row["parser_accepted"])
        self.assertFalse(row["semantic_rubric_correct"])
        self.assertIsNotNone(row["extraction_output"])

    def test_valid_stages_do_not_bypass_unchanged_grounding(self):
        output = quoted(CASES["A01"], dx="X축 양의 방향으로 2m")
        row = measured(StagedFake(classifier(), completion(output)))
        self.assertTrue(row["schema_valid"])
        self.assertFalse(row["adapter_accepted"])
        self.assertFalse(row["parser_accepted"])
        self.assertEqual(row["error_code"], "UNGROUNDED_REQUIREMENT")

    def test_unknown_and_transport_errors_remain_in_denominator(self):
        rows = [measured(StagedFake(None, None, "LOCAL_MODEL_UNAVAILABLE")),
                measured(StagedFake(completion("not json"), None, "INVALID_MODEL_OUTPUT"))]
        for row in rows:
            self.assertIsNone(row["raw_model_decision"])
            self.assertIsNone(row["classification_output"])
        self.assertEqual(summarize(rows)["semantic_rubric_correct"]["denominator"], 2)
        self.assertEqual(summarize(rows)["raw_decision_observed"]["numerator"], 0)

    def test_model_binding_applies_to_each_stage(self):
        wrong = completion({"schema_version": "classification-1.0", "decision": "READY"}, model="wrong")
        row = measured(StagedFake(wrong, completion(quoted(CASES["A01"]))))
        self.assertFalse(row["classification_schema_valid"])
        self.assertFalse(row["parser_accepted"])
        self.assertEqual(row["raw_model_decision"], "READY")

    def test_interrupts_are_not_converted_into_completed_trials(self):
        client = StagedFake(None, None)
        with patch.object(client, "complete_staged", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                measured(client)

    def test_manifest_binds_both_stage_definitions_without_a_model_call(self):
        from neurobuild.infrastructure.staged_requirement import LocalStagedRequirementClient
        client = LocalStagedRequirementClient("http://127.0.0.1:8003", "neurobuild-local")
        revision = "31c69efc29464b6bb0aee1398b5a7b50a99340c3"
        with patch.object(client, "complete_staged") as call:
            manifest = build_manifest(client,
                dataset=ROOT / "evaluations/requirement_hardening_v1_exposed_regression.jsonl",
                prompt=ROOT / "prompts/requirement_extraction_v1.txt",
                schema=ROOT / "schemas/requirement_generation_v2_decision_branches.schema.json",
                weights=ROOT / "runtime/models/qwen3-14b-awq.json",
                runtime=ROOT / "evaluations/results/phase5x/14b-generation2-v2-launch/runtime_metadata.json",
                revision=revision, tokenizer_revision=revision,
                run_id="staged-manifest", warmups=5, trials=1, split="development")
            call.assert_not_called()
        self.assertEqual(manifest["protocol"]["pipeline"], "staged_v1")
        self.assertEqual(manifest["protocol"]["maximum_calls_per_case"], 2)
        self.assertEqual(manifest["protocol"]["classification_max_tokens"], 128)
        self.assertEqual(manifest["protocol"]["effective_extraction_schema_sha256"], client.effective_schema_sha256)
        self.assertEqual(manifest["sha256"]["classification_prompt"], client.classification_prompt_sha256)
        self.assertEqual(manifest["sha256"]["classification_schema"], client.classification_schema_sha256)
        self.assertEqual(len(manifest["sha256"]["staged_client"]), 64)


if __name__ == "__main__":
    unittest.main()
