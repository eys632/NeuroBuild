"""Offline completed EXAONE45 override/raw-Unicode exposed120 x1 +5 replay, never a model invocation.

Core row replay and all metric/denominator formulas are exact AST copies of the
reviewed native Qwen replay. New model/wire/runtime bindings are separate.
Main requires independent frozen evidence pins and explicit completed-run input.
No completed historical result, private dataset, GGUF or native call is needed to
exercise the synthetic preparation controls. Never import this as adoption proof.
Current evidence validation is intentionally fail-closed; main is NOT ready.
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
MODEL = "LGAI-EXAONE/EXAONE-4.5-33B-GGUF"
REVISION = "0e969634ef24db05151b435970297a6dee634b7e"
SOURCE_PIN = "f072b103714dfa1eee531f80b24512faf38e3dd2"
GGUF_SHA = "5ba3839b67dcee5618ea7b2206cedc8f9e2ec90fbcec3c95a8cc8b33967f6baf"
GGUF_BYTES = 20047839424
ORIGINAL_TEMPLATE_SHA = "e4ece7acc79ba82121d4d57791fb7ecb796e39185087197377da5d2286bec0e5"
TEMPLATE_SHA = "7de6c8ba3df6db54564c7a63385cc29572c0a616d5848961e969ecbb8c349851"
TEMPLATE_VARIANT = "exaone45-gguf-continue-free-korean-v1"
OVERRIDE_PATH = "runtime/templates/exaone45-continue-free.jinja"
OFFICIAL_VOCAB_SHA = "66442010a8c4ee9f5f554bfea34273fd80659d50d42b9acdba6b2879400285d1"
PROFILE = "exaone45_nonthinking_llama_cpp"
LIFECYCLE = "FROZEN_BEFORE_NATIVE_EXAONE45_EXPOSED_DIAGNOSTIC"
ORIGINAL_REPLAY_SHA = "c1f063fe4a6ea14c9eaa57bb6e10467460f6765d9a3b4fce67a6fca0f69ac592"
PREPARATION_STATUS = "DRAFT_RUNTIME_FREEZE_BINDING_PENDING"
VARIANT = "exaone45-gguf-continue-free-raw-unicode-korean-v1"
CPU_SHA = None  # Actual GGUF aggregate is not available; never borrow another model proof.
HEADER_SHA = "fb5260c6e1e3356741f7728e4077f771763ea39affd77e8ac9772e417aa70c12"
TOKENIZER_SHA = "0bd798efa30739e209d51f36cfc2f0a636711e37ad9d69b77e4e5c8ca5f09fab"
V2_FREEZE = "evaluations/hardening_v2_dataset_freeze.json"
V2_EXPOSURE = "evaluations/hardening_v2_input_exposure_addendum.json"
V2_OUTPUT_EXPOSURE = "evaluations/hardening_v2_model_output_exposure_record.json"
V2_OUTPUT_EXPOSURE_SHA = "25c080827a6d57aa6bc864495e537490dc7fa48b3ccf91df297a47b9815d447b"
PATHS = {
    "dataset": "evaluations/requirement_hardening_v1_exposed_regression.jsonl",
    "prompt": "prompts/requirement_generation_v2_v2.txt",
    "schema": "schemas/requirement_generation_v2_decision_branches.schema.json",
    "canonical_schema": "schemas/semantic_requirement.schema.json",
    "generation_adapter": "src/neurobuild/application/requirement_generation.py",
    "parser": "src/neurobuild/application/requirements.py",
    "client": "src/neurobuild/infrastructure/local_model.py",
    "scorer": "scripts/evaluate_requirements.py",
    "weight_manifest": "runtime/models/exaone45-33b-q4-k-m.json",
}
SAMPLING = {"temperature": .6, "top_p": .95, "top_k": 20, "min_p": 0.,
            "presence_penalty": 1.5, "frequency_penalty": 0., "repeat_penalty": 1.,
            "repeat_last_n": 64, "seed": 42,
            "samplers": ["penalties", "top_k", "top_p", "min_p", "temperature"]}
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

def validate_identity(manifest, freeze, runtime, launch, commit, *, expected_variant):
    """Must finish before opening result or archived dataset bodies."""
    check(manifest["git"] == {"commit": commit, "dirty": False}, "clean_checkpoint")
    check(manifest["sha256"]["dataset"] == "7e5b9a05932df7aafdbf683655b044b3e3b25cbffb4115d298e1490aecbc7a5b"
          and manifest["split"] == freeze["split"] == "development"
          and freeze["dataset"] == PATHS["dataset"], "exposed_v1_only")
    check(freeze["lifecycle"] == LIFECYCLE
          and freeze["candidate_variant"] == expected_variant == VARIANT, "native_freeze")
    check(freeze['template_proof_variant'] == TEMPLATE_VARIANT
          and freeze['original_embedded_template_sha256'] == ORIGINAL_TEMPLATE_SHA
          and freeze['chat_template_override'] == {'path':OVERRIDE_PATH,'sha256':TEMPLATE_SHA},
          'explicit_effective_template_override')
    override_path = Path(launch['chat_template_path'])
    if not override_path.is_absolute(): override_path = ROOT / override_path
    check(override_path == ROOT / OVERRIDE_PATH
          and launch['chat_template_sha256'] == TEMPLATE_SHA, 'launch_template_override')
    check(freeze['official_hf_equivalence'] == {
        'status':'FAIL','case_count':20,'id_match_count':18,'mismatch_indices':[11,12],
        'native_raw_roundtrip_count':20,'official_ids_raw_roundtrip_count':18,
        'proof_ref':{'path':'var/research/native-exaone45-contract/public-vocab-proof.json',
                     'sha256':OFFICIAL_VOCAB_SHA}}, 'official_hf_failure_preserved')
    check(freeze['application_input_output_nfc_repair'] is False
          and freeze['context_tokenizer'] == 'native_raw_unicode_no_nfc_repair',
          'explicit_raw_unicode_contract')
    check(manifest["model_id"] == freeze["model_id"] == MODEL
          and manifest["model_revision"] == manifest["tokenizer_revision"] == REVISION
          and freeze["model_revision"] == freeze["tokenizer_revision"] == REVISION, "model_revision")
    check(manifest["served_model"] == freeze["served_model"] == launch["served_model_name"], "served_model")
    check(manifest["runtime"] == runtime, "runtime_manifest")
    p = manifest["protocol"]
    check(p.get("pipeline", "single") == freeze["pipeline"] == "single"
          and freeze["maximum_calls_per_case"] == 1 and freeze["expected_http_calls"] == 125,
          "single_calls")
    for key, expected in {"generation_contract": "2.0", "sampling_profile": PROFILE,
                          "sampling_request_parameters": SAMPLING, "max_tokens": 768,
                          "timeout_seconds": 120, "concurrency": 1, "enable_thinking": False,
                          "reasoning_parser": "deepseek"}.items():
        check(type(p[key]) is type(expected) and type(freeze[key]) is type(expected)
              and p[key] == freeze[key] == expected, "protocol_" + key)
    check(all(type(p["sampling_request_parameters"][key]) is type(value)
              and type(freeze["sampling_request_parameters"][key]) is type(value)
              for key,value in SAMPLING.items()), "sampling_value_types")
    check(p["structured_output_protocol"] == freeze["protocol"] == "llama_cpp_json_schema"
          and p["guided_decoding_backend"] is None
          and p["required_server_structured_backend"] == "llama_cpp_gbnf"
          and p["response_format_type"] == "json_schema" and p["tool_parser"] is None, "native_wire_only")
    check(p["temperature"] == .6 and p["seed"] == 42, "sampling_mirrors")
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
          and (launch["batch_size"], launch["ubatch_size"]) == (64, 64), "explicit_reviewed_batch_pair")
    for key, other in {"binary_sha256": "binary_sha256", "source_provenance_sha256": "source_report_sha256",
                       "build_report_sha256": "build_report_sha256", "gguf_header_sha256": "model_header_report_sha256"}.items():
        check(runtime[key] == launch[other], "native_artifact_binding")


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

def validate_evidence(freeze, runtime, launch, load, hashes):
    """Intentional hard stop until actual EXAONE evidence is separately reviewed.

    Full aggregate, header, startup/public/resource epoch, tokenizer/NFC contract,
    source-matched408-regression receipt and final freeze do not yet all exist.
    The official reference raw roundtrip18/20 must never be relabeled20/20 or
    inherit another model's Unicode variant. Add exact archived proof edges only
    after root provides the completed candidate freeze. Do not alter replay core.
    Main invokes this before reading saved results or dataset bodies.
    """
    check(False, "exaone_actual_evidence_binding_pending")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run")
    parser.add_argument("--freeze", required=True)
    parser.add_argument("--freeze-sha256", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--snapshot-sha256", required=True)
    parser.add_argument("--candidate-variant", required=True)
    parser.add_argument("--completed-run", action="store_true", required=True)
    args = parser.parse_args()
    check(args.candidate_variant == VARIANT, "candidate_variant_pin")
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
    validate_identity(manifest, freeze, runtime, launch, args.source_commit, expected_variant=args.candidate_variant)
    core.native_runtime_metadata(runtime)
    check(freeze["runtime_metadata"] == start + "runtime_metadata.json", "runtime_archive_path")
    check(freeze["sha256"].get("var/review-tools/replay_native_exaone45_exposed.py") == digest(Path(__file__)), "replay_helper_frozen")
    check(manifest["sha256"]["runtime_metadata"] == artifact_hashes[start + "runtime_metadata.json"], "runtime_hash")
    for key, name in PATHS.items():
        check(snapshot["sha256"][name] == manifest["sha256"][key] == freeze["sha256"][name], "source_binding_" + key)
    for name, expected in freeze["sha256"].items():
        check(digest(project_path(name)) == expected, "frozen_evidence_hash")
    def load_evidence(name):
        check(name in freeze["sha256"], "evidence_not_frozen")
        return load(name)
    validate_evidence(freeze, runtime, launch, load_evidence, freeze["sha256"])
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
        "cpu_context_proof_sha256": CPU_SHA, "normalization_limitation": freeze["normalization_limitation"],
        "v2_preservation": {"artifacts_hashed_without_parsing": 9,
            "freeze_sha256": freeze["sha256"][V2_FREEZE], "input_exposure_addendum_sha256": freeze["sha256"][V2_EXPOSURE],
            "model_output_exposure_record_sha256": freeze["sha256"][V2_OUTPUT_EXPOSURE],
            "limitation": "Prior V2 model outputs already exposed; no V2 result replay or input parsing in this EXAONE exposed120 replay"},
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
        print(json.dumps({"status":"FAIL", "check":label}), file=sys.stderr)
        raise SystemExit(1)
