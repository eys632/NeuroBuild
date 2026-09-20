"""Offline audit of a completed native single2 exposed 120x1 + 5 diagnostic.

Run only after root confirms results completion. Required independent CLI pins
bind the clean run checkpoint, freeze and exact git source snapshot. No HTTP,
model/GPU calls or weight reads. Only retained final quote JSON can be replayed;
rejected/unretained bodies retain recorded unknown/READY and full denominators.
Never interprets unused v2 input/gold, except byte hashing for preservation.
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
import re
import socket
import sys
from types import SimpleNamespace
from uuid import uuid5

ROOT = Path(__file__).resolve().parents[2]
MODEL = "ggml-org/Qwen3.8-27B-GGUF"
REVISION = "efbb3b1f70a21d97fd4495240648405f7228554f"
VARIANT = "qwen38-gguf-raw-unicode-v1"
SOURCE_PIN = "f072b103714dfa1eee531f80b24512faf38e3dd2"
GGUF_SHA = "c600de0300ae8a0eb3a6c0b8b5561b8b96f16bd2c863c2a66c42de29d391a747"
TEMPLATE_SHA = "c3cf9e34abf4f9e36c2d72165aa9c132d3e2a725b6c2586aaa3a8af9d7a81041"
PATHS = {
    "dataset": "evaluations/requirement_hardening_v1_exposed_regression.jsonl",
    "prompt": "prompts/requirement_generation_v2_v2.txt",
    "schema": "schemas/requirement_generation_v2_decision_branches.schema.json",
    "canonical_schema": "schemas/semantic_requirement.schema.json",
    "generation_adapter": "src/neurobuild/application/requirement_generation.py",
    "parser": "src/neurobuild/application/requirements.py",
    "client": "src/neurobuild/infrastructure/local_model.py",
    "scorer": "scripts/evaluate_requirements.py",
    "weight_manifest": "runtime/models/qwen38-27b-q4-k-m.json",
}
V2_FREEZE = "evaluations/hardening_v2_dataset_freeze.json"
V2_EXPOSURE = "evaluations/hardening_v2_input_exposure_addendum.json"
CPU = "var/reports/native-contract-raw-cpu-context.json"
SAMPLING = {"temperature": .7, "top_p": .8, "top_k": 20, "min_p": 0.,
            "presence_penalty": 0., "frequency_penalty": 0., "repeat_penalty": 1.,
            "repeat_last_n": 0, "seed": 42,
            "samplers": ["temperature", "top_k", "top_p", "min_p"]}
GATES = {"schema_required": 120, "schema_denominator": 120,
         "semantic_required_at_least": 114, "semantic_denominator": 120,
         "critical_model_ready_fp_required": 0, "critical_model_ready_fp_denominator": 58,
         "unsafe_accepted_ready_total_required": 0, "unsafe_accepted_ready_total_denominator": 120}

def check(ok, label):
    if not ok:
        raise AssertionError(label)

def digest(path):
    check(path.suffix not in (".gguf", ".safetensors"), "weight_payload_read_forbidden")
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()

def project_path(value):
    path = Path(value)
    path = ROOT / path if not path.is_absolute() else path
    check(not path.is_symlink() and path.resolve().is_relative_to(ROOT), "path_scope")
    return path.resolve()

def read_json(path, strict_json):
    check(path.is_file() and path.stat().st_size <= 64*1024*1024, "artifact_size")
    raw = path.read_bytes()
    return strict_json(raw.decode("utf-8")), sha256(raw).hexdigest()

def deny_network(*_args, **_kwargs):
    raise AssertionError("network_forbidden")

def load_snapshot(path, expected, commit):
    check(os.environ.get("CUDA_VISIBLE_DEVICES") == "", "empty_cuda_required")
    check(re.fullmatch(r"[a-f0-9]{40}", commit) is not None, "checkpoint_format")
    check(not any(n == "neurobuild" or n.startswith("neurobuild.")
                  or n == "scripts.evaluate_requirements" for n in sys.modules), "fresh_process_required")
    socket.create_connection = socket.getaddrinfo = deny_network
    check(digest(path / "snapshot.json") == expected, "snapshot_record_hash")
    record = json.loads((path / "snapshot.json").read_bytes())
    check(record["source_snapshot_commit"] == commit, "snapshot_commit")
    for name, value in record["sha256"].items():
        item = (path / name).resolve()
        check(item.is_relative_to(path), "snapshot_path_scope")
        check(digest(item) == value, "snapshot_hash")
    sys.path[:0] = [str(path / "src"), str(path)]
    core = importlib.import_module("scripts.evaluate_requirements")
    generation = importlib.import_module("neurobuild.application.requirement_generation")
    for name, module in tuple(sys.modules.items()):
        if name == "scripts.evaluate_requirements" or name == "neurobuild" or name.startswith("neurobuild."):
            origin = Path(module.__file__).resolve()
            check(origin.is_relative_to(path), "frozen_import_scope")
            check(str(origin.relative_to(path)) in record["sha256"], "unrecorded_import")
    check("torch" not in sys.modules, "torch_forbidden")
    return core, generation, record

def validate_identity(manifest, freeze, runtime, launch, commit):
    """Must finish before opening result or archived dataset bodies."""
    check(manifest["git"] == {"commit": commit, "dirty": False}, "clean_checkpoint")
    check(manifest["sha256"]["dataset"] == "7e5b9a05932df7aafdbf683655b044b3e3b25cbffb4115d298e1490aecbc7a5b"
          and manifest["split"] == freeze["split"] == "development"
          and freeze["dataset"] == PATHS["dataset"], "exposed_v1_only")
    check(freeze["lifecycle"] == "FROZEN_BEFORE_NATIVE_QWEN38_EXPOSED_DIAGNOSTIC"
          and freeze["candidate_variant"] == VARIANT, "native_freeze")
    check(manifest["model_id"] == freeze["model_id"] == MODEL
          and manifest["model_revision"] == manifest["tokenizer_revision"] == REVISION
          and freeze["model_revision"] == freeze["tokenizer_revision"] == REVISION, "model_revision")
    check(manifest["served_model"] == freeze["served_model"] == launch["served_model_name"], "served_model")
    check(manifest["runtime"] == runtime, "runtime_manifest")
    p = manifest["protocol"]
    check(p.get("pipeline", "single") == freeze["pipeline"] == "single"
          and freeze["maximum_calls_per_case"] == 1 and freeze["expected_http_calls"] == 125,
          "single_calls")
    for key, expected in {"generation_contract": "2.0", "sampling_profile": "qwen38_nonthinking_llama_cpp",
                          "sampling_request_parameters": SAMPLING, "max_tokens": 768,
                          "timeout_seconds": 120, "concurrency": 1, "enable_thinking": False,
                          "reasoning_parser": "deepseek"}.items():
        check(p[key] == freeze[key] == expected, "protocol_" + key)
    check(p["structured_output_protocol"] == freeze["protocol"] == "llama_cpp_json_schema"
          and p["guided_decoding_backend"] is None
          and p["required_server_structured_backend"] == "llama_cpp_gbnf"
          and p["response_format_type"] == "json_schema" and p["tool_parser"] is None, "native_wire_only")
    check(p["temperature"] == .7 and p["seed"] == 42, "sampling_mirrors")
    check(p["warmups"] == freeze["warmups_per_run"] == 5
          and p["trials_per_case"] == freeze["trials_per_case"] == 1
          and freeze["cases"] == 120 and freeze["ready_gold"] == 62 and freeze["nonready_gold"] == 58,
          "complete_protocol_counts")
    check(freeze["gate_targets"] == GATES, "fixed_gate")
    check(freeze["prompt"] == PATHS["prompt"] and freeze["generation_schema"] == PATHS["schema"], "fixed_generation_paths")
    check(datetime.fromisoformat(freeze["frozen_at_utc"]) <
          datetime.fromisoformat(manifest["created_at_utc"].replace("Z", "+00:00")), "freeze_before_run")
    for key, expected in {"runtime_kind": "llama_cpp", "profile": "a100", "physical_gpu": 3,
                          "logical_gpu": 0, "cuda_architecture": "80-real", "max_sequences": 1,
                          "max_model_len": 4096, "enable_reasoning": False, "reasoning_parser": "deepseek",
                          "quantization": "Q4_K_M", "llama_cpp_commit": SOURCE_PIN,
                          "gguf_sha256": GGUF_SHA, "chat_template_sha256": TEMPLATE_SHA}.items():
        check(runtime[key] == expected, "native_runtime_" + key)
    for key, expected in {"profile": "a100", "max_model_len": 4096,
                          "enable_reasoning": False, "estimated_peak_mib": 28672, "peak_allowance_mib": 0,
                          "source_commit": SOURCE_PIN, "model_sha256": GGUF_SHA,
                          "model_revision": REVISION}.items():
        check(launch[key] == expected and type(launch[key]) is type(expected), "native_launch_" + key)
    check(type(launch["batch_size"]) is int and type(launch["ubatch_size"]) is int
          and (launch["batch_size"], launch["ubatch_size"]) in ((2, 1), (64, 64)), "explicit_reviewed_batch_pair")
    for key, other in {"binary_sha256": "binary_sha256", "source_provenance_sha256": "source_report_sha256",
                       "build_report_sha256": "build_report_sha256", "gguf_header_sha256": "model_header_report_sha256"}.items():
        check(runtime[key] == launch[other], "native_artifact_binding")
    provenance = freeze["tokenizer_contract"]
    check(provenance["runtime_variant"] == VARIANT
          and provenance["reference_kind"] == "hf-tokenizer-json-with-nfc-normalizer-disabled"
          and provenance["context_tokenizer"] == "native_raw_unicode_no_nfc_repair"
          and provenance["application_input_output_nfc_repair"] is False, "raw_variant")
    hf = provenance["hf_equivalence"]
    raw = provenance["raw_reference"]
    check(hf["status"] == "FAIL" and hf["case_count"] == 20 and hf["id_match_count"] == 19
          and hf["mismatch_indices"] == [11]
          and hf["proof_sha256"] == "b537545d26a876a1496c2f85ad979330eba938f2880aae49190640b2404c63e0"
          and hf["original_fixture_sha256"] == "79c4448b7ee949add0a80e8a7f0fc0d73575aaf01ff6e52beb3cfae8434ea1bd",
          "official_hf_failure_retained")
    check(raw["case_count"] == raw["id_match_count"] == raw["native_original_roundtrip_count"] == 20
          and raw["fixture_sha256"] == "9658eb53fae81adee1b775b45f796f3484db69aea41e04a020765fa05d770514"
          and raw["native_proof_sha256"] == "12a5ebeafc16969f36435d9bb9e933ba12197d01ba05e8f26df41114f4e01d2d",
          "raw_reference_retained")

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


def validate_evidence(freeze, runtime, launch, load, hashes):
    """Read pinned small archives only; never query a live process or rehash weights."""
    runtime_path = project_path(freeze["runtime_metadata"])
    check(runtime_path.name == "runtime_metadata.json"
          and runtime_path.is_relative_to(ROOT / "evaluations/results/phase5x"), "runtime_archive_scope")
    start = str(runtime_path.parent.relative_to(ROOT)) + "/"
    public_path = freeze["public_smoke_report"]
    resource_path = freeze["resource_probe_report"]
    for name in (public_path, resource_path):
        check(project_path(name).is_relative_to(ROOT / "evaluations/results/phase5x")
              and name in hashes, "smoke_archive_scope")
    startup = load(start + "startup.json")
    guard = load(start + "resource_report.json")
    listeners = load(start + "listeners.json")
    context = load(CPU)
    public, resource = load(public_path), load(resource_path)
    check(runtime["startup_report_sha256"] == hashes[start + "startup.json"]
          and runtime["listener_report_sha256"] == hashes[start + "listeners.json"]
          and runtime["launch_config_sha256"] == hashes[start + "launch_config.json"]
          and startup["resource_report_sha256"] == hashes[start + "resource_report.json"], "startup_hash_edges")
    provenance = freeze["tokenizer_contract"]
    check(provenance["context_cpu_proof_sha256"] == hashes[CPU], "context_hash_edge")
    for proof in (startup, public, resource):
        check(all(proof[key] == value for key, value in provenance.items()), "tokenizer_provenance_edges")
    check(all(context[key] == value for key, value in provenance.items() if key != "context_cpu_proof_sha256"),
          "context_provenance_fields")
    check(context["kind"] == "NATIVE_CONTEXT_RAW_UNICODE_CPU_PROOF" and context["status"] == "PASS"
          and context["gguf_sha256"] == GGUF_SHA and context["model_inference_calls"] == 0
          and context["max_output_tokens"] == 768 and context["max_context_tokens"] == 4096, "cpu_context_scope")
    for split, count in (("exposed120", 120), ("v2_length80", 80)):
        row = context["splits"][split]
        check(row["input_count"] == count and 0 < row["max_input_tokens"]
              and row["max_input_plus_output"] == row["max_input_tokens"] + 768 <= 4096
              and row["native"]["status"] == "PASS"
              and row["native"]["tokenizer_metadata_parity_cases"] == 20, "cpu_context_counts")
    epoch = freeze["runtime_epoch_snapshot"]
    check(startup["kind"] == "NATIVE_STARTUP_HTTP_PROOF" and startup["status"] == "PASS"
          and startup["pid"] == guard["child_pid"] == listeners["pid"] == epoch["pid"]
          and startup["process_start_ticks"] == listeners["process_start_ticks"] == epoch["start_ticks"]
          and guard["started_at_utc"] == epoch["guard_started_at_utc"]
          and startup["http_get_calls"] == 3 and startup["model_inference_calls"] == 0
          and startup["raw_http_bodies_saved"] is False, "startup_epoch")
    check(listeners["verdict"] == "PASS" and listeners["all_loopback"] is True
          and listeners["snapshot_complete"] is True and listeners["uid"] == os.getuid(), "listeners_scope")
    check(guard["state"] == "RUNNING" and guard["native_identity_verified"] is True
          and guard["physical_gpu_index"] == 3 and guard["required_cuda_visible_devices"] == "3"
          and type(guard["batch_size"]) is int and type(guard["ubatch_size"]) is int
          and (guard["batch_size"], guard["ubatch_size"], guard["max_num_seqs"])
              == (launch["batch_size"], launch["ubatch_size"], 1)
          and guard["native_output_policy"] == "DISCARD_STDOUT_STDERR"
          and guard["native_core_dump_limit_bytes"] == 0
          and guard["minimum_observed_free_mib"] >= guard["required_free_floor_mib"]
          and guard["observed_baseline_relative_peak_mib"] <= guard["aggregate_increment_limit_mib"] == 28672,
          "startup_guard_scope")
    artifacts = guard["native_artifacts"]
    for key in ("binary_sha256", "source_report_sha256", "build_report_sha256", "source_commit",
                "model_sha256", "model_revision", "model_header_report_sha256"):
        check(artifacts[key] == launch[key], "guard_artifact_identity")
    check(guard["max_model_len"] == 4096 and guard["enable_reasoning"] is False
          and guard["reasoning_parser"] == "deepseek" and guard["served_model_name"] == launch["served_model_name"],
          "guard_generation_scope")
    check(public["status"] == "PASS" and public["http_calls_attempted"] == 1
          and public["quality_gate_pass"] is False and public["generated_body_retained"] is False,
          "public_smoke_scope")
    check(resource["kind"] == "NATIVE_PUBLIC_CONTEXT_RESOURCE_PROBE" and resource["status"] == "PASS"
          and resource["http_post_calls"] == 1, "resource_smoke_scope")
    check(resource["tokens_evaluated"] == resource["timings/prompt_n"] == 3328
          and resource["tokens_predicted"] == resource["timings/predicted_n"] == 768
          and resource["tokens_cached"] == 4095 and resource["stop"] is True
          and resource["truncated"] is True and resource["stop_type"] == "limit"
          and resource["quality_evaluation"] is False and resource["grammar_enabled"] is False
          and resource["generated_body_retained"] is False, "resource_full_context_boundary")
    for proof in (public, resource):
        check(proof["pid"] == epoch["pid"] and proof["process_start_ticks"] == epoch["start_ticks"]
              and proof["guard_started_at_utc"] == epoch["guard_started_at_utc"]
              and proof["launch_config_sha256"] == hashes[start + "launch_config.json"], "smoke_epoch")
    weights = load(PATHS["weight_manifest"])
    check(weights["model_id"] == MODEL and weights["revision"] == REVISION, "weight_manifest_identity")
    ggufs = [entry for entry in weights["files"] if entry["name"].endswith(".gguf")]
    check(len(ggufs) == 1 and ggufs[0]["sha256"] == GGUF_SHA and ggufs[0]["bytes"] == 18973870528,
          "weight_manifest_exact_quant")


def replay_groups(result, cases, manifest, validators, core, generation):
    check(len(cases) == 120 and sum(c["gold"]["decision"] == "requirement_ok" for c in cases) == 62,
          "gold_strata")
    check(manifest["case_order"] == [c["id"] for c in cases], "case_order")
    check([(r["case_id"], r["trial"]) for r in result["trials"]] == [(c["id"], 1) for c in cases],
          "complete_120_trial_order")
    check([(r["case_id"], r["trial"]) for r in result["warmups"]]
          == [(cases[i]["id"], -i-1) for i in range(5)], "complete_5_warmup_order")
    by_id = {c["id"]: c for c in cases}
    check(len(by_id) == 120, "unique_cases")
    replayed, retained, limitations = {}, {}, []
    for group in ("warmups", "trials"):
        replayed[group], retained[group] = [], 0
        for row in result[group]:
            item, present = replay_row(row, by_id[row["case_id"]], result["run_id"], manifest["served_model"],
                                       validators, core, generation)
            if not present:
                limitations.append({"group": group, "case_id": row["case_id"], "trial": row["trial"],
                    "raw_decision_recorded_not_reobserved": row["raw_model_decision"] is not None,
                    "reason": "Rejected body unretained; raw decision/error cannot be independently reobserved"})
            replayed[group].append(item)
            retained[group] += int(present)
    metrics = core.summarize(replayed["trials"])
    check(metrics == result["metrics"], "all_metrics_exact")
    rows = replayed["trials"]
    counts = {"schema": sum(r["schema_valid"] for r in rows),
              "quote_adapter": sum(r["adapter_accepted"] for r in rows),
              "canonical_schema": sum(r["legacy_schema_valid"] for r in rows),
              "parser": sum(r["parser_accepted"] for r in rows),
              "semantic": sum(r["semantic_rubric_correct"] for r in rows),
              "raw_fp": sum(r["expected_decision"] != "READY" and r["model_ready_observed"] is True for r in rows),
              "unsafe": sum(r["accepted_decision"] == "READY" and
                            (r["expected_decision"] != "READY" or not r["semantic_rubric_correct"]) for r in rows),
              "false_negative": sum(r["expected_decision"] == "READY" and r["accepted_decision"] != "READY" for r in rows),
              "raw_observed": sum(r["raw_model_decision"] is not None for r in rows)}
    for count, metric in (("schema", "schema_valid"), ("quote_adapter", "adapter_accepted"),
                          ("canonical_schema", "legacy_schema_valid"), ("parser", "parser_accepted"),
                          ("semantic", "semantic_rubric_correct"), ("raw_fp", "critical_fp_model_ready"),
                          ("unsafe", "unsafe_accepted_ready_total"), ("false_negative", "critical_fn_accepted_ready"),
                          ("raw_observed", "raw_decision_observed")):
        check(counts[count] == metrics[metric]["numerator"], "independent_count_" + count)
    for key, denominator in (("schema_valid", 120), ("semantic_rubric_correct", 120),
                              ("critical_fp_model_ready", 58), ("critical_fn_accepted_ready", 62),
                              ("unsafe_accepted_ready_total", 120), ("nonready_gold_raw_decision_observed", 58)):
        check(metrics[key]["denominator"] == denominator, "denominator_" + key)
    check(dict(Counter(r["error_code"] for r in rows if r["error_code"])) == metrics["errors"], "error_counts")
    gate = counts["schema"] == 120 and counts["semantic"] >= 114 and counts["raw_fp"] == counts["unsafe"] == 0 and counts["raw_observed"] == 120
    return {"diagnostic_gate": "PASS" if gate else "FAIL", "diagnostic_gate_counts": counts,
        "trials": 120, "warmups": 5, "retained_generation_json_replayed": retained,
        "unretained_response_rows": {g: len(result[g])-retained[g] for g in retained},
        "retained_stages_and_trial_metrics_exact": True, "frozen_evaluate_trial_exact_on_retained_rows": True,
        "metrics": metrics, "warmup_metrics_separate": core.summarize(replayed["warmups"]),
        "raw_ready_observation_coverage": {"all_trials": metrics["raw_decision_observed"],
            "nonready_gold_trials": metrics["nonready_gold_raw_decision_observed"],
            "meaning": "Unknown is not safe non-READY; full denominators remain and unknown prevents gate PASS"},
        "unobserved_decisions_by_error": {g: dict(Counter(r["error_code"] for r in replayed[g]
            if r["raw_model_decision"] is None)) for g in replayed}, "limitations": limitations}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run")
    parser.add_argument("--freeze", required=True)
    parser.add_argument("--freeze-sha256", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--snapshot-sha256", required=True)
    args = parser.parse_args()
    for value in (args.freeze_sha256, args.snapshot_sha256):
        check(re.fullmatch(r"[a-f0-9]{64}", value) is not None, "sha256_argument")
    snapshot_path = project_path(args.snapshot)
    core, generation, snapshot = load_snapshot(snapshot_path, args.snapshot_sha256, args.source_commit)
    directory, freeze_path = project_path(args.run), project_path(args.freeze)
    check(digest(freeze_path) == args.freeze_sha256, "independent_freeze_pin")
    artifact_hashes = {}
    def load(name):
        path = project_path(name)
        value, hashed = read_json(path, core.strict_json)
        if name in artifact_hashes:
            check(artifact_hashes[name] == hashed, "artifact_changed_while_reading")
        artifact_hashes[name] = hashed
        return value
    manifest = load(str(directory / "manifest.json"))
    freeze = load(str(freeze_path))
    runtime_path = project_path(freeze["runtime_metadata"])
    check(runtime_path.name == "runtime_metadata.json"
          and runtime_path.is_relative_to(ROOT / "evaluations/results/phase5x"), "runtime_archive_scope")
    start = str(runtime_path.parent.relative_to(ROOT)) + "/"
    runtime = load(start + "runtime_metadata.json")
    launch = load(start + "launch_config.json")
    validate_identity(manifest, freeze, runtime, launch, args.source_commit)
    core.native_runtime_metadata(runtime)
    check(freeze["runtime_metadata"] == start + "runtime_metadata.json", "runtime_archive_path")
    check(manifest["sha256"]["runtime_metadata"] == artifact_hashes[start + "runtime_metadata.json"], "runtime_hash")
    for key, name in PATHS.items():
        check(snapshot["sha256"][name] == manifest["sha256"][key] == freeze["sha256"][name], "source_binding_" + key)
    for name, expected in freeze["sha256"].items():
        check(digest(project_path(name)) == expected, "frozen_evidence_hash")
    validate_evidence(freeze, runtime, launch, load, freeze["sha256"])
    for name, hashed in artifact_hashes.items():
        relative = str(project_path(name).relative_to(ROOT))
        if relative in freeze["sha256"]:
            check(hashed == freeze["sha256"][relative], "read_evidence_exact_freeze")
    v2 = load(V2_FREEZE)
    check(len(v2["sha256"]) == 9, "v2_hash_count")
    for name, expected in v2["sha256"].items():
        check(digest(project_path(name)) == expected, "v2_hash_only")
    # Only after all identities/protocols/evidence pass may exposed outputs be read.
    result = load(str(directory / "results.json"))
    archived = load(str(directory / "dataset.json"))
    check(result["run_id"] == manifest["run_id"], "run_id")
    check(result["gold_status"] == manifest["gold_status"] == archived["gold_status"]
          == freeze["gold_status"] == "AUTO-GENERATED / NOT HUMAN VERIFIED", "gold_status")
    cases = core.load_cases(snapshot_path / PATHS["dataset"])
    check(cases == archived["cases"], "exact_archived_exposed_cases")
    validators = {key: core.Draft202012Validator(core.strict_json((snapshot_path / PATHS[key]).read_text()))
                  for key in ("schema", "canonical_schema")}
    audit = replay_groups(result, cases, manifest, validators, core, generation)
    for name, expected in artifact_hashes.items():
        check(digest(project_path(name)) == expected, "read_artifact_changed")
    for name, expected in snapshot["sha256"].items():
        check(digest(snapshot_path / name) == expected, "snapshot_changed")
    for name, expected in freeze["sha256"].items():
        check(digest(project_path(name)) == expected, "frozen_evidence_changed")
    for name, expected in v2["sha256"].items():
        check(digest(project_path(name)) == expected, "v2_hash_only_changed")
    check("torch" not in sys.modules, "torch_forbidden")
    print(json.dumps({"status": "PASS", "meaning": "Saved-result replay/accounting consistency, not adoption",
        **audit, "run_id": result["run_id"], "runtime_variant": VARIANT,
        "tokenizer_contract": freeze["tokenizer_contract"], "native_protocol": "llama_cpp_json_schema",
        "source_snapshot_commit": args.source_commit, "source_snapshot_sha256": args.snapshot_sha256,
        "source_hashes_verified": {key: manifest["sha256"][key] for key in PATHS},
        "original_artifact_sha256": artifact_hashes, "native_freeze_sha256": args.freeze_sha256,
        "v2_preservation": {"artifacts_hashed_without_parsing": 9,
            "freeze_sha256": freeze["sha256"][V2_FREEZE], "input_exposure_addendum_sha256": freeze["sha256"][V2_EXPOSURE],
            "limitation": "Prior root input exposure recorded; no v2 model results used or read here"},
        "replay_helper_sha256": digest(Path(__file__)),
        "latencies_and_token_usage": "Recorded observations only; no remeasurement",
        "runtime_limit": "Archive hash/epoch binding, not new process/weight attestation or per-process VRAM",
        "quality_limit": "Exposed synthetic regression, not human reviewed or independent unseen evaluation",
        "model_calls": 0, "network_calls": 0, "gpu_calls": 0, "weight_payload_reads": 0}, ensure_ascii=False, indent=2, allow_nan=False))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        label = str(exc) if isinstance(exc, AssertionError) else type(exc).__name__
        print(json.dumps({"status": "FAIL", "check": label}), file=sys.stderr)
        raise SystemExit(1)
