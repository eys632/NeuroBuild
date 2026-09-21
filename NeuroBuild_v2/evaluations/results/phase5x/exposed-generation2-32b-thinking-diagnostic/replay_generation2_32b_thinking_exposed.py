"""Offline frozen replay of the official 32B single2 thinking diagnostic.

Invoke only after all 120 trials plus five separate warmups finish:
  CUDA_VISIBLE_DEVICES='' .conda/bin/python -B \
    var/review-tools/replay_generation2_32b_thinking_exposed.py RUN_DIRECTORY \
    --freeze evaluations/hardening_v1_exposed_generation2_32b_thinking_diagnostic_freeze.json \
    --runtime-dir evaluations/results/phase5x/32b-generation2-thinking-v1-launch

Uses the exact 59e9b64 snapshot. Retained final 2.0 JSON is independently
projected to canonical1 and compared with frozen evaluate_trial. Truncation,
missing final JSON and malformed/unretained responses keep original unknowns,
raw observations and denominators. No response repair or fabricated raw replay.
No model/client/network/GPU calls, weights, actual reasoning-body reads/writes.
Future v2 data is hashed only, never parsed. PASS concerns faithful accounting;
quality gate and replay coverage are reported separately.
"""

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import importlib
import json
import math
import os
from pathlib import Path
import socket
import sys
from types import SimpleNamespace
from uuid import uuid5


ROOT = Path(__file__).resolve().parents[2]
COMMIT = "59e9b64312e32582371553a3a243bd566a72c845"
SNAPSHOT = ROOT / "var/review-snapshots" / COMMIT
SNAPSHOT_SHA256 = "3d73a64ce97ef67149e03add34faf2497cbe05e26c315de4d6e73a77fc41c8b5"
FREEZE_SHA256 = "e0bf7d237fdbfa61d3e4fe09aefa6d706872a4a3db100fec5541ec0eebc0c19d"
MODEL = "Qwen/Qwen3-32B-AWQ"
REVISION = "0499c3ac83fdef8810b907a23894ba91e95eddd8"
PATHS = {
    "dataset": "evaluations/requirement_hardening_v1_exposed_regression.jsonl",
    "prompt": "prompts/requirement_generation_v2_thinking_v1.txt",
    "schema": "schemas/requirement_generation_v2_decision_branches.schema.json",
    "canonical_schema": "schemas/semantic_requirement.schema.json",
    "generation_adapter": "src/neurobuild/application/requirement_generation.py",
    "parser": "src/neurobuild/application/requirements.py",
    "client": "src/neurobuild/infrastructure/local_model.py",
    "scorer": "scripts/evaluate_requirements.py",
    "weight_manifest": "runtime/models/qwen3-32b-awq.json",
}
V2_FREEZE = "evaluations/hardening_v2_dataset_freeze.json"
V2_EXPOSURE = "evaluations/hardening_v2_input_exposure_addendum.json"


def check(condition, label):
    if not condition:
        raise AssertionError(label)


def digest(path):
    """Hash bytes without interpreting or exposing possibly unused v2 inputs."""
    result = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def project_path(value):
    path = Path(value).resolve()
    check(path.is_relative_to(ROOT), "path_outside_project")
    return path


def read_json(path, strict_json):
    check(path.is_file() and path.stat().st_size <= 64 * 1024 * 1024,
          "artifact_size_or_type")
    raw = path.read_bytes()
    return strict_json(raw.decode("utf-8")), sha256(raw).hexdigest()


def deny_network(*_args, **_kwargs):
    raise AssertionError("network_forbidden_in_offline_replay")


def load_snapshot():
    check(os.environ.get("CUDA_VISIBLE_DEVICES") == "", "explicit_cpu_mask_required")
    check(not any(name == "neurobuild" or name.startswith("neurobuild.")
                  or name == "scripts.evaluate_requirements" for name in sys.modules),
          "fresh_process_required_for_frozen_imports")
    socket.create_connection = deny_network
    socket.getaddrinfo = deny_network
    check(digest(SNAPSHOT / "snapshot.json") == SNAPSHOT_SHA256, "snapshot_record_hash")
    record = json.loads((SNAPSHOT / "snapshot.json").read_text())
    check(record["source_snapshot_commit"] == COMMIT, "snapshot_commit")
    for name, expected in record["sha256"].items():
        path = (SNAPSHOT / name).resolve()
        check(path.is_relative_to(SNAPSHOT), "snapshot_path_scope")
        check(digest(path) == expected, "snapshot_hash:" + name)
    sys.path[:0] = [str(SNAPSHOT / "src"), str(SNAPSHOT)]
    core = importlib.import_module("scripts.evaluate_requirements")
    generation = importlib.import_module("neurobuild.application.requirement_generation")
    for name, module in tuple(sys.modules.items()):
        if name == "scripts.evaluate_requirements" or name == "neurobuild" or name.startswith("neurobuild."):
            origin = Path(module.__file__).resolve()
            check(origin.is_relative_to(SNAPSHOT), "import_outside_snapshot")
            check(str(origin.relative_to(SNAPSHOT)) in record["sha256"], "unrecorded_frozen_import")
    check("torch" not in sys.modules, "tensor_import_forbidden")
    return core, generation, record


def replay_row(row, case, run_id, served_model, validators, core, generation):
    """Recompute recorded quote/canonical stages without editing decisions."""
    tag = case["id"] + "/" + str(row["trial"])
    check(row.get("generation_contract") == "2.0", tag + ":contract")
    check(row.get("pipeline", "single") == "single", tag + ":single_pipeline")
    check(row["category"] == case["category"], tag + ":category")
    for key in ("json_parse_valid", "schema_valid", "generation_schema_valid",
                "adapter_accepted", "legacy_schema_valid", "parser_accepted"):
        check(type(row[key]) is bool, tag + ":boolean_" + key)
    check(type(row["latency_seconds"]) in (int, float)
          and math.isfinite(row["latency_seconds"]) and row["latency_seconds"] >= 0,
          tag + ":recorded_latency")
    check(row["error_code"] in core.SAFE_ERRORS | {
        None, "JSON_PARSE_FAILED", "JSON_SCHEMA_FAILED", "EVALUATION_CLIENT_ERROR"}, tag + ":safe_error")
    decision = row["raw_model_decision"]
    check(decision in (None, "READY", "CLARIFICATION", "UNSUPPORTED"), tag + ":raw_decision")
    observed = row["model_ready_observed"]
    check(observed is (None if decision is None else decision == "READY"), tag + ":raw_ready")
    original = row["generation_output"]
    canonical = requirement = None
    expected = dict(adapter_accepted=False, legacy_schema_valid=False, parser_accepted=False,
                    semantic_output=None, normalized_operation_metres=None)
    if original is None:
        # Neither invented response text nor a sanitized error is a reobservation.
        # Preserve a recorded READY even on schema rejection; preserve unknowns.
        check(not row["schema_valid"] and not row["generation_schema_valid"], tag + ":absent_generation")
        check(row["error_code"] is not None, tag + ":absent_generation_error")
        if not row["json_parse_valid"]:
            check(decision is None, tag + ":unparseable_decision")
    else:
        check(row["json_parse_valid"] and row["schema_valid"] and row["generation_schema_valid"],
              tag + ":generation_flags")
        check(validators["schema"].is_valid(original), tag + ":generation_schema")
        check(row["response_model"] == served_model, tag + ":served_model")
        check(decision == original["decision"], tag + ":original_root_decision")
        error = None
        try:
            canonical_text = generation.adapt_generation_v2(
                json.dumps(original, ensure_ascii=False), source_text=case["input"])
            expected["adapter_accepted"] = True
            canonical = core.strict_json(canonical_text)
            expected["legacy_schema_valid"] = validators["canonical_schema"].is_valid(canonical)
            if not expected["legacy_schema_valid"]:
                raise core.DomainError("INVALID_MODEL_OUTPUT", "Canonical schema mismatch")
            expected["semantic_output"] = canonical
            requirement = core.parse_requirement(
                canonical_text, source_text=case["input"],
                requirement_id=uuid5(core.NAMESPACE, f"{run_id}/{case['id']}/{row['trial']}"),
                project_id=uuid5(core.NAMESPACE, run_id + "/project"),
                base_revision_id=uuid5(core.NAMESPACE, run_id + "/base"),
                axis_convention=case["context"].get("axis_convention"),
            )
            expected["parser_accepted"] = True
            if requirement.operation is not None:
                expected["normalized_operation_metres"] = {
                    axis: str(getattr(requirement.operation, axis).metres) for axis in ("dx", "dy")}
        except core.DomainError as exc:
            error = exc.code if exc.code in core.SAFE_ERRORS else "EVALUATION_CLIENT_ERROR"
        check(error == row["error_code"], tag + ":replayed_error")
    for key, value in expected.items():
        check(row[key] == value, tag + ":" + key)
    rubric = core.score_output(case, canonical, requirement)
    for key, value in rubric.items():
        check(row[key] == value, tag + ":rubric_" + key)
    replayed = deepcopy(row)
    replayed.update(expected)
    replayed.update(rubric)
    if original is not None:
        completion = SimpleNamespace(content=json.dumps(original, ensure_ascii=False),
                                     model=row["response_model"], usage=row["usage"],
                                     latency_seconds=row["transport_latency_seconds"])

        class BufferedClient:
            model = served_model
            generation_contract = generation.GenerationContract.QUOTES

            def complete(self, source_text, *, axis_convention=None):
                check(source_text == case["input"] and axis_convention == case["context"].get("axis_convention"),
                      "buffered_source_binding")
                return completion

        ticks = iter((0.0, row["latency_seconds"]))
        reproduced = core.evaluate_trial(BufferedClient(), case, validators["schema"], row["trial"],
                                         run_id=run_id, clock=lambda: next(ticks))
        check(reproduced == row, tag + ":frozen_evaluate_trial_exact")
    return replayed, original is not None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", help="Completed 120x1 diagnostic directory; no partial-run support")
    parser.add_argument("--freeze", required=True)
    parser.add_argument("--runtime-dir", required=True)
    args = parser.parse_args()
    core, generation, snapshot = load_snapshot()
    directory, freeze_path, runtime_dir = map(project_path, (args.run, args.freeze, args.runtime_dir))
    check(digest(freeze_path) == FREEZE_SHA256, "pinned_generation2_thinking_freeze")
    paths = {name: directory / name for name in ("results.json", "manifest.json", "dataset.json")}
    paths.update(freeze=freeze_path, runtime=runtime_dir / "runtime_metadata.json",
                 launch=runtime_dir / "launch_config.json")
    values, original_hashes = {}, {}
    # Check manifest identity before opening archived cases or model outputs.
    # An accidentally supplied future-v2 run must fail without reading its body.
    for name in ("manifest.json", "freeze", "runtime", "launch"):
        path = paths[name]
        values[name], original_hashes[name] = read_json(path, core.strict_json)
    check(values["manifest.json"]["sha256"]["dataset"] == snapshot["sha256"][PATHS["dataset"]]
          and values["manifest.json"]["split"] == "development"
          and values["manifest.json"]["protocol"]["generation_contract"] == "2.0"
          and values["manifest.json"]["protocol"]["enable_thinking"] is True
          and values["manifest.json"]["git"] == {"commit": COMMIT, "dirty": False},
          "exposed_generation2_thinking_manifest_before_payload_read")
    for name in ("results.json", "dataset.json"):
        values[name], original_hashes[name] = read_json(paths[name], core.strict_json)
    result, manifest, archived = (values[name] for name in ("results.json", "manifest.json", "dataset.json"))
    freeze, runtime, launch = (values[name] for name in ("freeze", "runtime", "launch"))
    check(freeze["dataset"] == PATHS["dataset"], "only_exposed_v1_dataset_allowed")
    check(manifest["model_id"] == freeze["model_id"] == MODEL, "model_identity")
    check(manifest["model_revision"] == manifest["tokenizer_revision"] == freeze["model_revision"] == REVISION,
          "model_and_tokenizer_revision")
    check(manifest["served_model"] == freeze["served_model"], "served_alias")
    check(manifest["git"] == {"commit": COMMIT, "dirty": False}, "exact_clean_run_checkpoint")
    check(manifest["split"] == freeze["split"] == "development", "exposed_split")
    check(result["run_id"] == manifest["run_id"], "run_id")
    check(result["gold_status"] == manifest["gold_status"] == archived["gold_status"]
          == freeze["gold_status"] == "AUTO-GENERATED / NOT HUMAN VERIFIED", "gold_status")
    check(datetime.fromisoformat(freeze["frozen_at_utc"]) <
          datetime.fromisoformat(manifest["created_at_utc"].replace("Z", "+00:00")), "freeze_precedes_run")
    protocol = manifest["protocol"]
    check(protocol.get("pipeline", "single") == freeze["pipeline"] == "single", "single_pipeline_only")
    # Current 2.0 manifest predates explicit projection-chain/max-call fields;
    # freeze plus exact frozen single-client/evaluator source supplies that binding.
    check(freeze["projection_chain"] == ["2.0", "1.0"] and freeze["maximum_calls_per_case"] == 1
          and freeze["expected_http_calls"] == 125, "single_projection_call_contract")
    for key, expected in {
        "generation_contract": "2.0", "sampling_profile": "qwen3_thinking_awq",
        "sampling_request_parameters": {"temperature": 0.6, "top_p": 0.95, "top_k": 20, "min_p": 0.0,
            "presence_penalty": 1.5, "frequency_penalty": 0.0, "repetition_penalty": 1.0, "seed": 42},
        "max_tokens": 1024, "timeout_seconds": 120, "concurrency": 1,
        "enable_thinking": True, "reasoning_parser": "deepseek_r1",
        "guided_decoding_backend": "xgrammar:no-fallback",
    }.items():
        check(protocol[key] == freeze[key] == expected, "protocol:" + key)
    check(protocol["structured_output_protocol"] == freeze["protocol"] == "legacy_guided_json", "wire_protocol")
    check(protocol["warmups"] == freeze["warmups_per_run"] == 5, "warmup_count")
    check(protocol["trials_per_case"] == freeze["trials_per_case"] == 1, "trial_count")
    check(freeze["cases"] == 120 and freeze["ready_gold"] == 62 and freeze["nonready_gold"] == 58, "frozen_case_counts")
    check(freeze["prompt"] == PATHS["prompt"] and freeze["generation_schema"] == PATHS["schema"], "generation2_thinking_paths")
    for key, name in PATHS.items():
        check(snapshot["sha256"][name] == manifest["sha256"][key] == freeze["sha256"][name], "bound_source:" + key)
    # Evidence hashes cover all preregistered files, with v2 payloads hashed only.
    for name, expected in freeze["sha256"].items():
        check(digest(project_path(ROOT / name)) == expected, "frozen_evidence_hash:" + name)
    v2, _ = read_json(ROOT / V2_FREEZE, core.strict_json)
    check(len(v2["sha256"]) == freeze["v2_holdout_preservation"]["frozen_artifacts_verified"] == 9,
          "v2_preserved_artifact_count")
    for name, expected in v2["sha256"].items():
        check(digest(project_path(ROOT / name)) == expected, "v2_hash_only_preservation")
    check(runtime == manifest["runtime"] == freeze["runtime_metadata"]
          and original_hashes["runtime"] == manifest["sha256"]["runtime_metadata"], "runtime_metadata_binding")
    for key in ("runtime", "launch"):
        check(original_hashes[key] == freeze["sha256"][str(paths[key].relative_to(ROOT))], "frozen_runtime:" + key)
    check(original_hashes["launch"] == runtime["launch_config_sha256"], "launch_config_binding")
    check(launch["launcher_sha256"] == snapshot["sha256"]["scripts/model_server.py"]
          == freeze["sha256"]["scripts/model_server.py"], "launcher_binding")
    check(runtime["chat_template_sha256"] == freeze["template_sha256"], "template_binding")
    check(runtime["profile"] == "a100" and runtime["physical_gpu"] == 3
          and runtime["tensor_parallel_size"] == 1 and runtime["max_model_len"] == 4096
          and runtime["enable_reasoning"] is True and runtime["reasoning_parser"] == "deepseek_r1"
          and runtime["quantization"] == "awq_marlin" and runtime["dtype"] == "float16", "runtime_scope")
    for key, expected in {"max_num_seqs": 1, "num_gpu_blocks_override": 256,
                          "gpu_memory_utilization": 0.6, "torch_memory_fraction": 0.6,
                          "estimated_peak_mib": 25600, "peak_allowance_mib": 0,
                          "enforce_eager": True, "VLLM_USE_V1": "0", "enable_reasoning": True,
                          "reasoning_parser": "deepseek_r1"}.items():
        check(launch[key] == expected, "launch_limit:" + key)
    cases = core.load_cases(SNAPSHOT / PATHS["dataset"])
    check(len(cases) == 120 and cases == archived["cases"], "archived_exposed_dataset")
    check(sum(c["gold"]["decision"] == "requirement_ok" for c in cases) == 62, "ready_gold_count")
    check(manifest["case_order"] == [c["id"] for c in cases], "case_order")
    check([(r["case_id"], r["trial"]) for r in result["trials"]]
          == [(c["id"], 1) for c in cases], "complete_120_trial_order")
    check([(r["case_id"], r["trial"]) for r in result["warmups"]]
          == [(cases[i]["id"], -i - 1) for i in range(5)], "complete_5_warmup_order")
    validators = {key: core.Draft202012Validator(core.strict_json((SNAPSHOT / PATHS[key]).read_text()))
                  for key in ("schema", "canonical_schema")}
    by_id = {c["id"]: c for c in cases}
    replayed, retained_counts, limitations = {}, {}, []
    for group in ("warmups", "trials"):
        replayed[group], retained_counts[group] = [], 0
        for row in result[group]:
            replay, retained = replay_row(row, by_id[row["case_id"]], result["run_id"], manifest["served_model"],
                                          validators, core, generation)
            if not retained:
                limitations.append({"group": group, "case_id": row["case_id"], "trial": row["trial"],
                    "raw_decision_is_recorded_not_reobserved": row["raw_model_decision"] is not None,
                    "reason": "Rejected body was not retained; its raw decision/error cannot be independently reobserved"})
            replayed[group].append(replay)
            retained_counts[group] += int(retained)
    metrics = core.summarize(replayed["trials"])
    check(metrics == result["metrics"], "all_metrics_exact_including_recorded_latencies")
    rows = replayed["trials"]
    counts = {
        "schema": sum(r["schema_valid"] for r in rows),
        "quote_adapter": sum(r["adapter_accepted"] for r in rows),
        "canonical_schema": sum(r["legacy_schema_valid"] for r in rows),
        "parser": sum(r["parser_accepted"] for r in rows),
        "semantic": sum(r["semantic_rubric_correct"] for r in rows),
        "raw_fp": sum(r["expected_decision"] != "READY" and r["model_ready_observed"] is True for r in rows),
        "unsafe": sum(r["accepted_decision"] == "READY" and
                      (r["expected_decision"] != "READY" or not r["semantic_rubric_correct"]) for r in rows),
        "false_negative": sum(r["expected_decision"] == "READY" and r["accepted_decision"] != "READY" for r in rows),
        "raw_observed": sum(r["raw_model_decision"] is not None for r in rows),
    }
    for key, metric in (("schema", "schema_valid"),
                        ("quote_adapter", "adapter_accepted"), ("canonical_schema", "legacy_schema_valid"),
                        ("parser", "parser_accepted"), ("semantic", "semantic_rubric_correct"),
                        ("raw_fp", "critical_fp_model_ready"), ("unsafe", "unsafe_accepted_ready_total"),
                        ("false_negative", "critical_fn_accepted_ready"), ("raw_observed", "raw_decision_observed")):
        check(counts[key] == metrics[metric]["numerator"], "independent_count:" + key)
    check(dict(Counter(r["error_code"] for r in rows if r["error_code"])) == metrics["errors"], "error_counts")
    check(freeze["gate_targets"] == {
        "schema_required": 120, "schema_denominator": 120,
        "semantic_required_at_least": 114, "semantic_denominator": 120,
        "critical_model_ready_fp_required": 0, "critical_model_ready_fp_denominator": 58,
        "unsafe_accepted_ready_total_required": 0, "unsafe_accepted_ready_total_denominator": 120,
    }, "unchanged_gate_targets")
    gate = (counts["schema"] == 120 and counts["semantic"] >= 114 and counts["raw_fp"] == counts["unsafe"] == 0
            and counts["raw_observed"] == 120)
    for name, path in paths.items():
        check(digest(path) == original_hashes[name], "input_changed:" + name)
    for name, expected in snapshot["sha256"].items():
        check(digest(SNAPSHOT / name) == expected, "snapshot_changed:" + name)
    for name, expected in freeze["sha256"].items():
        check(digest(project_path(ROOT / name)) == expected, "frozen_evidence_changed:" + name)
    for name, expected in v2["sha256"].items():
        check(digest(project_path(ROOT / name)) == expected, "v2_hash_only_changed")
    check("torch" not in sys.modules, "tensor_import_forbidden")
    print(json.dumps({
        "status": "PASS", "meaning": "Independent replay/accounting consistency, not quality adoption",
        "diagnostic_gate": "PASS" if gate else "FAIL", "diagnostic_gate_counts": counts,
        "run_id": result["run_id"], "trials": 120, "warmups": 5,
        "retained_generation_json_replayed": retained_counts,
        "unretained_response_rows": {g: len(result[g]) - retained_counts[g] for g in retained_counts},
        "retained_stage_replay_unretained_flag_consistency_and_trial_metrics_exact": True,
        "frozen_evaluate_trial_exact_on_all_retained_rows": True,
        "metrics": metrics, "warmup_metrics_separate": core.summarize(replayed["warmups"]),
        "raw_ready_observation_coverage": {
            "all_trials": metrics["raw_decision_observed"],
            "nonready_gold_trials": metrics["nonready_gold_raw_decision_observed"],
            "interpretation": "Recorded FP numerator keeps the full non-READY denominator; unknown decisions are not safe non-READY and prevent a gate PASS",
        },
        "unobserved_decisions_by_error": {
            group: dict(Counter(row["error_code"] for row in replayed[group]
                                if row["raw_model_decision"] is None)) for group in ("warmups", "trials")
        },
        "limitations": limitations,
        "source_snapshot_commit": COMMIT, "source_snapshot_sha256": SNAPSHOT_SHA256,
        "source_hashes_verified": {key: manifest["sha256"][key] for key in PATHS},
        "original_artifact_sha256": original_hashes,
        "generation2_thinking_freeze_sha256": FREEZE_SHA256,
        "v2_preservation": {"artifacts_hashed_without_parsing": 9,
                            "freeze_sha256": freeze["sha256"][V2_FREEZE],
                            "input_exposure_addendum_sha256": freeze["sha256"][V2_EXPOSURE],
                            "limitation": freeze["v2_holdout_preservation"]["limitation"]},
        "replay_helper_sha256": digest(Path(__file__)),
        "latencies_and_token_usage": "Stored observations preserved; no remeasurement",
        "runtime_limit": "Archive/manifest binding only, not new process/loaded-weight attestation or per-process VRAM measurement",
        "quality_limit": "Synthetic, not human verified; exposed regression and fixed-seed trials are not independent unseen evidence",
        "model_calls": 0, "gpu_calls": 0, "network_calls": 0, "weight_payload_reads": 0,
    }, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        # Avoid bodies, source inputs, credentials and raw tracebacks in errors.
        label = str(exc) if isinstance(exc, AssertionError) else type(exc).__name__
        print(json.dumps({"status": "FAIL", "check": label}), file=sys.stderr)
        raise SystemExit(1)
