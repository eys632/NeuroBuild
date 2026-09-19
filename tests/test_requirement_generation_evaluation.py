"""Quote generation accounting: model mistakes must survive adapter rejection."""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator

from neurobuild.application.requirement_generation import GenerationContract
from neurobuild.domain.errors import DomainError
from neurobuild.infrastructure.local_model import LocalRequirementClient
from scripts.evaluate_requirements import (
    ROOT, build_manifest, evaluate_trial, load_cases, run_evaluation, summarize,
)
from tests.test_requirement_evaluation import FakeClient


SCHEMA = json.loads((ROOT / "schemas/requirement_generation_v2.schema.json").read_text())
CASES = {row["id"]: row for row in load_cases(ROOT / "evaluations/requirement_seed.jsonl")}


class QuoteClient(FakeClient):
    generation_contract = GenerationContract.QUOTES


def quoted(case, *, target=None, dx="X축 양의 방향으로 1m", dy=None):
    return {"schema_version": "2.0", "decision": "READY",
            "target_selection_quote": target or case["gold"].get("target_text", "회의실 책상"),
            "current_instruction_quote": case["input"], "dx_evidence": dx, "dy_evidence": dy,
            "reason": None}


def measured(case, output):
    return evaluate_trial(QuoteClient([output]), case, Draft202012Validator(SCHEMA), 1,
                          run_id="synthetic-quotes")


class GenerationEvaluationTests(unittest.TestCase):
    def test_raw_ready_survives_adapter_rejection(self):
        row = measured(CASES["B02"], quoted(CASES["B02"]))
        self.assertTrue(row["generation_schema_valid"])
        self.assertEqual(row["raw_model_decision"], "READY")
        self.assertFalse(row["adapter_accepted"])
        self.assertFalse(row["parser_accepted"])
        self.assertIsNotNone(row["generation_output"])
        self.assertIsNone(row["semantic_output"])
        metrics = summarize([row])
        self.assertEqual(metrics["critical_fp_model_ready"]["numerator"], 1)
        self.assertEqual(metrics["critical_fp_model_ready"]["denominator"], 1)
        self.assertEqual(metrics["critical_fp_accepted_ready"]["numerator"], 0)

    def test_both_original_quotes_and_canonical_projection_are_retained(self):
        case = CASES["A02"]
        output = quoted(case, dx=None, dy="Y축 음의 방향으로 250mm")
        row = measured(case, output)
        self.assertTrue(row["semantic_rubric_correct"])
        self.assertTrue(row["adapter_accepted"])
        self.assertTrue(row["legacy_schema_valid"])
        self.assertEqual(row["generation_output"], output)
        self.assertEqual(row["semantic_output"]["schema_version"], "1.0")
        self.assertEqual(row["semantic_output"]["operation"]["dy"]["value"], "-250")
        self.assertEqual(row["normalized_operation_metres"], {"dx": "0", "dy": "-0.250"})
        self.assertEqual(summarize([row])["case_consistency"][case["id"]]["distinct_semantic_results"], 1)

    def test_scope_loss_is_not_repaired_or_rescored(self):
        case = CASES["F02"]
        output = quoted(case, target="창가 쪽 책상", dx=None, dy="Y축 양의 방향으로 30cm")
        row = measured(case, output)
        self.assertTrue(row["parser_accepted"])
        self.assertFalse(row["semantic_rubric_correct"])
        self.assertEqual(row["semantic_output"]["target_text"], "창가 쪽 책상")
        self.assertEqual(summarize([row])["unsafe_accepted_ready_total"]["numerator"], 1)

    def test_nonready_crossfield_rejection_does_not_become_success(self):
        output = quoted(CASES["B02"])
        output.update(decision="CLARIFICATION", reason="거리를 확인해야 합니다.")
        row = measured(CASES["B02"], output)
        self.assertFalse(row["parser_accepted"])
        self.assertFalse(row["semantic_rubric_correct"])
        self.assertEqual(row["raw_model_decision"], "CLARIFICATION")

    def test_schema_errors_and_transport_failures_keep_denominators_and_sanitize(self):
        outputs = [{"decision": "READY", "reasoning": "DO_NOT_SAVE"},
                   DomainError("LOCAL_MODEL_TIMEOUT", "DO_NOT_SAVE"),
                   DomainError("LOCAL_MODEL_TRUNCATED", "DO_NOT_SAVE"), "not json"]
        rows = [measured(CASES["B01"], value) for value in outputs]
        metrics = summarize(rows)
        self.assertEqual(metrics["generation_schema_valid"]["denominator"], 4)
        self.assertEqual(metrics["generation_schema_valid"]["numerator"], 0)
        self.assertEqual(metrics["semantic_rubric_correct"]["denominator"], 4)
        self.assertEqual(metrics["critical_fp_model_ready"]["numerator"], 1)
        self.assertEqual(metrics["raw_decision_observed"]["numerator"], 1)
        self.assertNotIn("DO_NOT_SAVE", json.dumps(rows))
        self.assertTrue(all(row["generation_output"] is None for row in rows))

    def test_projection_cannot_bypass_the_final_parser(self):
        case = deepcopy(CASES["A01"])
        case["input"] = "회의실 책상을 X축 양의 방향으로 1m, Y축 음의 방향으로 2m 옮겨줘."
        row = measured(case, quoted(case))
        self.assertTrue(row["generation_schema_valid"])
        self.assertFalse(row["parser_accepted"])
        self.assertEqual(row["error_code"], "UNGROUNDED_REQUIREMENT")

    def test_schema_valid_but_ungrounded_adapter_result_still_reaches_parser(self):
        from tests.test_requirement_evaluation import ready
        case = CASES["A01"]
        projection = ready(case, value="2")  # Shape is valid; source says 1m.
        with patch("scripts.evaluate_requirements.adapt_generation_v2",
                   return_value=json.dumps(projection, ensure_ascii=False)):
            row = measured(case, quoted(case))
        self.assertTrue(row["generation_schema_valid"])
        self.assertTrue(row["adapter_accepted"])
        self.assertTrue(row["legacy_schema_valid"])
        self.assertFalse(row["parser_accepted"])
        self.assertEqual(row["raw_model_decision"], "READY")
        self.assertEqual(row["error_code"], "UNGROUNDED_REQUIREMENT")
        self.assertFalse(row["semantic_rubric_correct"])

    def test_quote_warmups_are_excluded_and_legacy_shape_is_unchanged(self):
        case = CASES["A01"]
        client = QuoteClient([DomainError("LOCAL_MODEL_TIMEOUT", "warmup"), quoted(case), quoted(case)])
        result = run_evaluation(client, [case], SCHEMA, run_id="quotes-test", warmups=1, trials=2)
        self.assertEqual(len(result["warmups"]), 1)
        self.assertEqual(result["metrics"]["generation_schema_valid"]["numerator"], 2)
        self.assertEqual(result["metrics"]["latency_all"]["count"], 2)
        from tests.test_requirement_evaluation import measured as legacy_measured, ready
        legacy = legacy_measured(case, ready(case))
        self.assertNotIn("generation_output", legacy)
        self.assertNotIn("generation_schema_valid", summarize([legacy]))
        self.assertTrue(legacy["semantic_rubric_correct"])

    def test_manifest_records_explicit_contract_adapter_and_canonical_schema(self):
        client = LocalRequirementClient("http://127.0.0.1:8003", "synthetic", generation_contract="2.0")
        with tempfile.TemporaryDirectory(dir=ROOT / "var") as directory:
            weights = Path(directory) / "weights.json"
            weights.write_text(json.dumps({"model_id": "test/model", "revision": "a" * 40,
                "files": [{"name": "model.safetensors", "bytes": 1, "sha256": "b" * 64}]}))
            runtime = {"python": "3.12.14", "vllm": "0.8.5+cu118", "torch": "2.6.0+cu118",
                       "cuda": "11.8", "transformers": "4.51.3", "xgrammar": "0.1.18", "driver": "535.183.01",
                       "gpu": "NVIDIA A100-PCIE-40GB", "quantization": "awq", "dtype": "float16", "profile": "a100",
                       "physical_gpu": 3, "max_model_len": 4096, "tensor_parallel_size": 1,
                       "chat_template_sha256": "c" * 64, "launch_config_sha256": "d" * 64}
            runtime_path = Path(directory) / "runtime.json"
            runtime_path.write_text(json.dumps(runtime))
            with patch.object(client, "complete") as transport:
                result = build_manifest(client, dataset=ROOT / "evaluations/requirement_seed.jsonl",
                    prompt=ROOT / "prompts/requirement_generation_v2_v1.txt",
                    schema=ROOT / "schemas/requirement_generation_v2.schema.json", weights=weights,
                    runtime=runtime_path, revision="a" * 40, tokenizer_revision="a" * 40,
                    run_id="test", warmups=5, trials=3)
                transport.assert_not_called()
            self.assertEqual(result["protocol"]["generation_contract"], "2.0")
            for key, path in (("generation_adapter", "src/neurobuild/application/requirement_generation.py"),
                              ("canonical_schema", "schemas/semantic_requirement.schema.json")):
                self.assertEqual(result["sha256"][key], sha256((ROOT / path).read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
