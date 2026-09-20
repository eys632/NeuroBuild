"""Facts accounting tests using synthetic completions, without model calls."""

from contextlib import redirect_stderr
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator

from neurobuild.application.requirement_generation import GenerationContract
from neurobuild.domain.errors import DomainError
from neurobuild.infrastructure.local_model import LocalRequirementClient
from scripts.evaluate_requirements import ROOT, build_manifest, evaluate_trial, main, run_evaluation, summarize
from tests.test_requirement_evaluation import CASES, FakeClient, ready
from tests.test_requirement_facts import facts


SCHEMA = json.loads((ROOT / "schemas/requirement_generation_v3.schema.json").read_text())


class FakeFactsClient(FakeClient):
    generation_contract = GenerationContract.FACTS


def generated(case=None):
    case = CASES["A01"] if case is None else case
    return {"schema_version": "3.0", "facts": facts(), "decision": "READY",
            "target_selection_quote": "회의실 책상", "current_instruction_quote": case["input"],
            "dx_evidence": "X축 양의 방향으로 1m", "dy_evidence": None, "reason": None}


def measured(output, case=None):
    return evaluate_trial(FakeFactsClient([output]), CASES["A01"] if case is None else case,
                          Draft202012Validator(SCHEMA), 1, run_id="synthetic-facts")


class RequirementFactsEvaluationTests(unittest.TestCase):
    def test_single_completion_preserves_three_contract_boundaries(self):
        output = generated()
        row = measured(output)
        for key in ("schema_valid", "generation_schema_valid", "facts_projection_accepted",
                    "adapter_accepted", "legacy_schema_valid", "parser_accepted", "semantic_rubric_correct"):
            self.assertTrue(row[key], (key, row["error_code"]))
        self.assertEqual(row["generation_output"], output)
        self.assertEqual(row["projected_quote_output"],
                         {"schema_version": "2.0", **{k: v for k, v in output.items()
                                                       if k not in ("schema_version", "facts")}})
        self.assertEqual(row["semantic_output"], ready(CASES["A01"]))
        self.assertEqual(row["normalized_operation_metres"], {"dx": "1", "dy": "0"})
        self.assertEqual(summarize([row])["facts_projection_accepted"]["rate"], 1)

    def test_raw_ready_survives_schema_and_fact_rejections(self):
        contradictory = generated(CASES["B02"])
        contradictory["facts"]["authority_quote"] = CASES["B02"]["input"]
        structurally_wrong = generated(CASES["B02"])
        structurally_wrong["facts"]["intent"] = "NEGATED_MOVE"
        rows = [measured(output, CASES["B02"]) for output in (contradictory, structurally_wrong)]
        self.assertTrue(rows[0]["generation_schema_valid"])
        self.assertEqual(rows[0]["error_code"], "INVALID_MODEL_OUTPUT")
        self.assertFalse(rows[1]["generation_schema_valid"])
        for row in rows:
            self.assertEqual(row["raw_model_decision"], "READY")
            self.assertFalse(row["facts_projection_accepted"])
            self.assertFalse(row["parser_accepted"])
            self.assertIsNone(row["projected_quote_output"])
        metrics = summarize(rows)
        self.assertEqual(metrics["critical_fp_model_ready"]["numerator"], 2)
        self.assertEqual(metrics["critical_fp_model_ready"]["denominator"], 2)
        self.assertEqual(metrics["critical_fp_accepted_ready"]["numerator"], 0)

    def test_quote_adapter_failure_does_not_erase_facts_or_raw_ready(self):
        output = generated()
        output["dx_evidence"] = "X축 양의 방향으로 999m"
        row = measured(output)
        self.assertTrue(row["facts_projection_accepted"])
        self.assertFalse(row["adapter_accepted"])
        self.assertEqual(row["error_code"], "UNGROUNDED_REQUIREMENT")
        self.assertEqual(row["generation_output"], output)
        self.assertEqual(row["raw_model_decision"], "READY")

    def test_canonical_parser_is_mandatory_after_both_adapters(self):
        wrong = ready(CASES["A01"], target="원문에 없는 작업대")
        with patch("scripts.evaluate_requirements.adapt_generation_v2", return_value=json.dumps(wrong)):
            row = measured(generated())
        self.assertTrue(row["facts_projection_accepted"])
        self.assertTrue(row["adapter_accepted"])
        self.assertTrue(row["legacy_schema_valid"])
        self.assertFalse(row["parser_accepted"])
        self.assertEqual(row["error_code"], "UNGROUNDED_REQUIREMENT")

    def test_invalid_projection_is_not_saved_or_sent_to_quote_adapter(self):
        projected = {"schema_version": "2.0", **{k: v for k, v in generated().items()
                                                  if k not in ("schema_version", "facts")}}
        for faulty in (dict(projected, secret="DO_NOT_SAVE"), dict(projected, schema_version="1.0")):
            with patch("scripts.evaluate_requirements.adapt_generation_v3", return_value=json.dumps(faulty)), \
                 patch("scripts.evaluate_requirements.adapt_generation_v2") as downstream:
                row = measured(generated())
            downstream.assert_not_called()
            self.assertFalse(row["facts_projection_accepted"])
            self.assertIsNone(row["projected_quote_output"])
            self.assertEqual(row["error_code"], "INVALID_MODEL_OUTPUT")
            self.assertNotIn("DO_NOT_SAVE", json.dumps(row))

    def test_errors_keep_denominators_and_exclude_unsafe_raw_payloads(self):
        outputs = ["DO_NOT_SAVE", '{"decision":"READY","decision":"CLARIFICATION"}',
                   {"decision": "READY", "secret": "DO_NOT_SAVE"},
                   DomainError("LOCAL_MODEL_TIMEOUT", "DO_NOT_SAVE"),
                   DomainError("LOCAL_MODEL_TRUNCATED", "DO_NOT_SAVE")]
        rows = [measured(value, CASES["B01"]) for value in outputs]
        metrics = summarize(rows)
        for metric in ("schema_valid", "semantic_rubric_correct", "facts_projection_accepted"):
            self.assertEqual(metrics[metric]["denominator"], 5)
            self.assertEqual(metrics[metric]["numerator"], 0)
        self.assertEqual(metrics["critical_fp_model_ready"]["numerator"], 1)
        self.assertEqual(metrics["critical_fp_model_ready"]["denominator"], 5)
        self.assertEqual(metrics["raw_decision_observed"]["numerator"], 1)
        self.assertNotIn("DO_NOT_SAVE", json.dumps(rows))
        self.assertTrue(all(row["generation_output"] is None for row in rows))

    def test_warmup_and_one_call_per_trial_accounting(self):
        client = FakeFactsClient([DomainError("LOCAL_MODEL_TIMEOUT", "warmup")] * 5 + [generated()] * 3)
        result = run_evaluation(client, [CASES["A01"]], SCHEMA, run_id="facts-counts", warmups=5, trials=3)
        self.assertEqual(len(client.calls), 8)
        self.assertEqual(len(result["warmups"]), 5)
        self.assertEqual(result["metrics"]["semantic_rubric_correct"]["denominator"], 3)
        self.assertEqual(result["metrics"]["semantic_rubric_correct"]["rate"], 1)
        self.assertEqual(result["metrics"]["errors"], {})

    def test_manifest_records_explicit_projection_and_both_adapter_hashes(self):
        client = LocalRequirementClient("http://127.0.0.1:8003", "synthetic-model",
                                        generation_contract="3.0", max_tokens=1024)
        with TemporaryDirectory() as directory:
            base = Path(directory)
            weights = base / "weights.json"
            weights.write_text(json.dumps({"model_id": "Qwen/Qwen3-32B-AWQ", "revision": "a" * 40,
                "files": [{"name": "model.safetensors", "bytes": 1, "sha256": "b" * 64}]}))
            runtime = base / "runtime.json"
            runtime.write_text(json.dumps({"python": "3.12.14", "vllm": "0.8.5+cu118", "torch": "2.6.0+cu118",
                "cuda": "11.8", "transformers": "4.51.3", "xgrammar": "0.1.18", "driver": "535.183.01",
                "gpu": "NVIDIA A100-PCIE-40GB", "quantization": "awq", "dtype": "float16", "profile": "a100",
                "physical_gpu": 3, "max_model_len": 4096, "tensor_parallel_size": 1,
                "chat_template_sha256": "c" * 64, "launch_config_sha256": "d" * 64}))
            manifest = build_manifest(client, dataset=ROOT / "evaluations/requirement_seed.jsonl",
                prompt=ROOT / "prompts/requirement_generation_v3_v1.txt",
                schema=ROOT / "schemas/requirement_generation_v3.schema.json", weights=weights, runtime=runtime,
                revision="a" * 40, tokenizer_revision="a" * 40, run_id="facts-manifest", warmups=5, trials=3)
        self.assertEqual(manifest["protocol"]["projection_chain"], ["3.0", "2.0", "1.0"])
        self.assertEqual(manifest["protocol"]["pipeline"], "single")
        self.assertEqual(manifest["protocol"]["maximum_calls_per_case"], 1)
        self.assertEqual(manifest["protocol"]["max_tokens"], 1024)
        for key, relative in {
            "facts_adapter": "src/neurobuild/application/requirement_facts.py",
            "generation_adapter": "src/neurobuild/application/requirement_generation.py",
            "quote_projection_schema": "schemas/requirement_generation_v2.schema.json",
            "canonical_schema": "schemas/semantic_requirement.schema.json",
        }.items():
            self.assertEqual(manifest["sha256"][key], sha256((ROOT / relative).read_bytes()).hexdigest())

    def test_staged_generation_three_rejected_before_client_or_dataset(self):
        args = ["--pipeline", "staged_v1", "--generation-contract", "3.0", "--model", "test",
                "--model-revision", "a" * 40, "--weight-manifest", "/nonexistent/weights.json",
                "--runtime-metadata", "/nonexistent/runtime.json"]
        with patch("scripts.evaluate_requirements.LocalRequirementClient") as client, \
             patch("scripts.evaluate_requirements.load_cases") as dataset, redirect_stderr(StringIO()):
            self.assertEqual(main(args), 2)
        client.assert_not_called()
        dataset.assert_not_called()


if __name__ == "__main__":
    unittest.main()
