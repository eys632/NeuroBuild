"""Synthetic scorer/runner tests; no GPU or model server is used."""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator

from neurobuild.domain.errors import DomainError
from neurobuild.infrastructure.local_model import Completion, LocalRequirementClient
from scripts.evaluate_requirements import (
    GOLD_STATUS, ROOT, build_manifest, evaluate_trial, expected_ready_target,
    load_cases, rate, run_evaluation, runtime_metadata, save_json, summarize,
)


SCHEMA = json.loads((ROOT / "schemas/semantic_requirement.schema.json").read_text())
CASES = {row["id"]: row for row in load_cases(ROOT / "evaluations/requirement_seed.jsonl")}


def ready(case, *, target=None, value="1", unit="m", evidence="X축 양의 방향으로 1m", axis="dx", instruction=None):
    return {"schema_version": "1.0", "decision": "READY",
            "target_text": target or case["gold"].get("target_text", "회의실 책상"),
            "operation": {"kind": "MOVE_FURNITURE", "coordinate_frame": "PROJECT_WORLD_XY",
                          "instruction_text": instruction or case["input"],
                          "dx": None, "dy": None, axis: {"value": value, "unit": unit, "evidence": evidence}},
            "reason": None}


def refusal(decision="CLARIFICATION", target=""):
    return {"schema_version": "1.0", "decision": decision, "target_text": target,
            "operation": None, "reason": "명확한 지원 범위의 요청이 필요합니다."}


class FakeClient:
    model = "synthetic-model"

    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.calls = []

    def complete(self, source_text, *, axis_convention=None):
        self.calls.append((source_text, axis_convention))
        value = next(self.outputs)
        if isinstance(value, Exception):
            raise value
        if not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False)
        return Completion(value, {"completion_tokens": 30}, 0.25, self.model)


def measured(case, output):
    ticks = iter([5.0, 5.5])
    return evaluate_trial(FakeClient([output]), case, Draft202012Validator(SCHEMA), 1,
                          run_id="synthetic-test", clock=lambda: next(ticks))


class RequirementEvaluationTests(unittest.TestCase):
    def test_seed_is_unchanged_twenty_development_cases(self):
        self.assertEqual(len(CASES), 20)
        self.assertEqual(sum(row["gold"]["decision"] == "requirement_ok" for row in CASES.values()), 9)
        self.assertEqual(GOLD_STATUS, "AUTO-GENERATED / NOT HUMAN VERIFIED")

    def test_raw_ready_rejected_by_parser_still_counts_model_false_positive(self):
        case = CASES["B02"]
        result = measured(case, ready(case))  # Model invented missing distance.
        self.assertTrue(result["schema_valid"])
        self.assertTrue(result["model_ready_observed"])
        self.assertFalse(result["parser_accepted"])
        self.assertEqual(result["error_code"], "UNGROUNDED_REQUIREMENT")
        metrics = summarize([result])
        self.assertEqual(metrics["critical_fp_model_ready"]["numerator"], 1)
        self.assertEqual(metrics["critical_fp_accepted_ready"]["numerator"], 0)
        self.assertEqual(metrics["critical_fp_model_ready"]["denominator"], 1)

    def test_grounded_but_approval_bypass_ready_is_accepted_critical_false_positive(self):
        case = CASES["G02"]
        result = measured(case, ready(case))
        self.assertTrue(result["parser_accepted"])
        self.assertFalse(result["semantic_rubric_correct"])
        metrics = summarize([result])
        self.assertEqual(metrics["critical_fp_model_ready"]["rate"], 1)
        self.assertEqual(metrics["critical_fp_accepted_ready"]["rate"], 1)

    def test_parse_schema_timeout_and_truncation_keep_full_denominator(self):
        outputs = ["not JSON", {"decision": "READY", "chain_of_thought": "DO_NOT_SAVE"},
                   DomainError("LOCAL_MODEL_TIMEOUT", "DO_NOT_SAVE"),
                   DomainError("LOCAL_MODEL_TRUNCATED", "DO_NOT_SAVE")]
        results = [measured(CASES["B01"], output) for output in outputs]
        metrics = summarize(results)
        self.assertEqual(metrics["schema_valid"]["denominator"], 4)
        self.assertEqual(metrics["schema_valid"]["numerator"], 0)
        self.assertEqual(metrics["semantic_rubric_correct"]["denominator"], 4)
        self.assertEqual(metrics["critical_fp_model_ready"]["numerator"], 1)
        self.assertEqual(metrics["critical_fp_model_ready"]["denominator"], 4)
        self.assertEqual(metrics["raw_decision_observed"]["numerator"], 1)
        self.assertTrue(all(row["semantic_output"] is None for row in results))
        self.assertNotIn("DO_NOT_SAVE", json.dumps(results))
        self.assertEqual(metrics["latency_all"]["count"], 4)

    def test_duplicate_keys_and_nonfinite_numbers_are_parse_failure(self):
        for text in ('{"decision":"READY","decision":"CLARIFICATION"}', '{"value":NaN}'):
            result = measured(CASES["A01"], text)
            self.assertFalse(result["json_parse_valid"])
            self.assertIsNone(result["model_ready_observed"])

    def test_source_numeric_units_are_converted_exactly_for_scoring(self):
        case = CASES["A02"]
        result = measured(case, ready(case, value="-250", unit="mm", axis="dy", evidence="Y축 음의 방향으로 250mm"))
        self.assertTrue(result["semantic_rubric_correct"])
        self.assertEqual(result["normalized_operation_metres"], {"dx": "0", "dy": "-0.250"})
        self.assertEqual(result["unit_value_slots_correct"], 2)
        invalid = measured(case, ready(case, value="-0.25", unit="m", axis="dy", evidence="Y축 음의 방향으로 250mm"))
        self.assertFalse(invalid["parser_accepted"])
        self.assertEqual(invalid["unit_value_slots_correct"], 0)

    def test_f02_requires_scope_exclusion_and_bridge_without_changing_gold(self):
        case = CASES["F02"]
        original = deepcopy(case)
        full_target = "회의실 입구 쪽 책상 말고 창가 쪽 책상"
        self.assertEqual(expected_ready_target(case), full_target)
        complete = measured(case, ready(case, target=full_target, axis="dy", value="30", unit="cm",
                                        evidence="Y축 양의 방향으로 30cm"))
        dropped = measured(case, ready(case, target="창가 쪽 책상", axis="dy", value="30", unit="cm",
                                       evidence="Y축 양의 방향으로 30cm"))
        self.assertTrue(complete["semantic_rubric_correct"])
        self.assertEqual(complete["target_slots_correct"], 3)
        self.assertTrue(dropped["parser_accepted"])
        self.assertFalse(dropped["semantic_rubric_correct"])
        self.assertEqual(dropped["target_slots_correct"], 1)
        self.assertEqual(summarize([dropped])["critical_fp_accepted_ready"]["denominator"], 0)
        self.assertEqual(summarize([dropped])["accepted_incorrect_move_on_ready_gold"]["numerator"], 1)
        self.assertEqual(summarize([dropped])["unsafe_accepted_ready_total"]["numerator"], 1)
        self.assertEqual(case, original)

    def test_single_target_cannot_pass_by_copying_the_entire_instruction(self):
        case = CASES["A01"]
        result = measured(case, ready(case, target=case["input"]))
        self.assertTrue(result["parser_accepted"])
        self.assertEqual(result["target_slots_correct"], 1)
        self.assertFalse(result["target_correct"])
        self.assertFalse(result["semantic_rubric_correct"])

    def test_wrong_supported_axis_distance_fails_semantic_not_readiness(self):
        case = deepcopy(CASES["A01"])
        case["input"] += " 이전 요청은 회의실 책상을 X축 양의 방향으로 2m 옮겨줘."
        result = measured(case, ready(case, value="2", evidence="X축 양의 방향으로 2m",
                                     instruction="회의실 책상을 X축 양의 방향으로 2m 옮겨줘."))
        self.assertTrue(result["parser_accepted"])
        self.assertFalse(result["semantic_rubric_correct"])
        self.assertEqual(summarize([result])["critical_fn_accepted_ready"]["numerator"], 0)
        self.assertEqual(summarize([result])["accepted_incorrect_move_on_ready_gold"]["rate"], 1)

    def test_warmups_are_excluded_from_trials_and_latency(self):
        cases = [CASES["A01"], CASES["B01"]]
        warm = [DomainError("LOCAL_MODEL_TIMEOUT", "ignored warmup") for _ in range(5)]
        trial = [ready(cases[0])] * 3 + [refusal(target="책상")] * 3
        fake = FakeClient(warm + trial)
        ticks = iter(range(22))
        result = run_evaluation(fake, cases, SCHEMA, run_id="test", clock=lambda: next(ticks))
        self.assertEqual(len(fake.calls), 11)
        self.assertEqual(len(result["warmups"]), 5)
        self.assertEqual(len(result["trials"]), 6)
        self.assertEqual(result["metrics"]["semantic_rubric_correct"]["rate"], 1)
        self.assertEqual(result["metrics"]["latency_all"], {"count": 6, "mean_seconds": 1.0, "p95_seconds": 1})
        self.assertEqual(result["metrics"]["errors"], {})
        self.assertEqual([row["case_id"] for row in result["trials"]], ["A01"] * 3 + ["B01"] * 3)
        self.assertEqual(fake.calls[-1], (cases[1]["input"], None))
        self.assertEqual(result["metrics"]["completion_tokens_per_end_to_end_second"], 30)
        self.assertIsNone(result["metrics"]["decode_tokens_per_second"])

    def test_unexpected_errors_and_mismatched_server_model_are_sanitized(self):
        result = measured(CASES["A01"], RuntimeError("SECRET /private/location"))
        self.assertEqual(result["error_code"], "EVALUATION_CLIENT_ERROR")
        self.assertNotIn("SECRET", json.dumps(result))
        fake = FakeClient([])
        with patch.object(fake, "complete", return_value=Completion(json.dumps(ready(CASES["A01"])), None, 0.1, "another")):
            result = evaluate_trial(fake, CASES["A01"], Draft202012Validator(SCHEMA), 1, run_id="test")
        self.assertEqual(result["error_code"], "LOCAL_MODEL_RESPONSE_INVALID")
        self.assertFalse(result["parser_accepted"])

    def test_rates_have_null_undefined_denominators_and_nonzero_zero_event_uncertainty(self):
        self.assertEqual(rate(0, 0), {"numerator": 0, "denominator": 0, "rate": None, "wilson_95": None})
        self.assertGreater(rate(0, 33)["wilson_95"][1], 0.1)
        rows = [measured(CASES["A01"], ready(CASES["A01"]))]
        metrics = summarize(rows)
        self.assertIsNone(metrics["critical_fp_model_ready"]["rate"])

    def test_manifest_pins_exact_inputs_and_rejects_mismatches(self):
        client = LocalRequirementClient("http://127.0.0.1:8003", "synthetic-model", max_tokens=768)
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            weight = base / "weights.json"
            weight.write_text(json.dumps({"model_id": "Qwen/Qwen3-14B-AWQ", "revision": "a" * 40,
                                         "files": [{"name": "model.safetensors", "bytes": 1, "sha256": "b" * 64}]}))
            runtime = base / "runtime.json"
            runtime.write_text(json.dumps({"python": "3.12.14", "vllm": "0.8.5+cu118", "torch": "2.6.0+cu118",
                "cuda": "11.8", "transformers": "4.51.3", "xgrammar": "0.1.18", "driver": "535.183.01",
                "gpu": "NVIDIA A100-PCIE-40GB", "quantization": "awq", "dtype": "float16", "profile": "a100",
                "physical_gpu": 3, "max_model_len": 4096, "tensor_parallel_size": 1,
                "chat_template_sha256": "c" * 64, "launch_config_sha256": "d" * 64}))
            kwargs = dict(dataset=ROOT / "evaluations/requirement_seed.jsonl", prompt=ROOT / "prompts/requirement_v3.txt",
                          schema=ROOT / "schemas/semantic_requirement.schema.json", weights=weight, runtime=runtime,
                          revision="a" * 40, tokenizer_revision="a" * 40, run_id="test", warmups=5, trials=3)
            manifest = build_manifest(client, **kwargs)
            self.assertEqual(manifest["model_revision"], "a" * 40)
            self.assertEqual(manifest["sha256"]["dataset"], sha256(kwargs["dataset"].read_bytes()).hexdigest())
            self.assertEqual(manifest["protocol"]["max_tokens"], 768)
            self.assertEqual(manifest["protocol"]["structured_output_protocol"], "legacy_guided_json")
            self.assertEqual(manifest["protocol"]["guided_decoding_backend"], "xgrammar:no-fallback")
            modern = LocalRequirementClient("http://127.0.0.1:8003", "synthetic-model", protocol="structured_outputs")
            modern_manifest = build_manifest(modern, **dict(kwargs, split="heldout"))
            self.assertEqual(modern_manifest["split"], "heldout")
            self.assertEqual(modern_manifest["protocol"]["structured_output_protocol"], "structured_outputs")
            self.assertIsNone(modern_manifest["protocol"]["guided_decoding_backend"])
            self.assertEqual(modern_manifest["protocol"]["required_server_structured_backend"], "xgrammar")
            with self.assertRaises(ValueError):
                build_manifest(client, **dict(kwargs, split="human_verified"))
            self.assertEqual(manifest["gold_status"], GOLD_STATUS)
            self.assertIsNone(manifest["measurements_not_performed"]["gpu_peak_used_mib"])
            with self.assertRaises(ValueError):
                build_manifest(client, **dict(kwargs, revision="main"))
            with self.assertRaises(ValueError):
                build_manifest(client, **dict(kwargs, revision="f" * 40))
            bad = json.loads(runtime.read_text())
            bad["api_key"] = "DO_NOT_SAVE"
            runtime.write_text(json.dumps(bad))
            with self.assertRaises(ValueError):
                runtime_metadata(runtime)

    def test_result_files_are_exclusive_and_never_replace_previous_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            save_json(path, {"version": 1})
            with self.assertRaises(FileExistsError):
                save_json(path, {"version": 2})
            self.assertEqual(json.loads(path.read_text()), {"version": 1})


if __name__ == "__main__":
    unittest.main()
