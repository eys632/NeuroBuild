"""Offline completed EXAONE45 override/raw-Unicode exposed120 x1 +5 replay, never a model invocation.

Core row replay and all metric/denominator formulas are exact AST copies of the
reviewed native Qwen replay. New model/wire/runtime bindings are separate.
Main requires independent frozen evidence pins and explicit completed-run input.
No completed historical result, private dataset, GGUF or native call is needed to
exercise the synthetic preparation controls. Never import this as adoption proof.
Post-freeze offline amendment: accept timeout120 as finite int or float only.
The original v3 file and frozen v3 hash remain required. This v4 was not pre-run frozen.
Main requires the completed new run and all exact frozen saved evidence; no live probes.
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
PREPARATION_STATUS = "POST_FREEZE_OFFLINE_TIMEOUT_REPRESENTATION_FIX"
FROZEN_PARENT_PATH = "var/review-tools/replay_native_exaone45_exposed_v3.py"
FROZEN_PARENT_SHA = "47981646b4efe96ba7b7f85c991fad526b287f5c64407102aefcd2d8bbee30e4"
VARIANT = "exaone45-gguf-continue-free-raw-unicode-korean-v1"
CPU_SHA = "2a937a8adeca827f4724c9b65947291005aa34dc8ca4af823739fd09ca248209"
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

MANIFEST_SHA = "98aa8ad498c2a55db6359754c80793e33b880f60c191ec3fbe449097833c4bb8"
LAUNCHER_SHA = "6a58ee1ea09636df182125da4a4a2711012e6c53f5f90c06548a63b9915369ed"
RUNTIME_HELPER = "var/research/exaone45_runtime_probe_v4.py"
RUNTIME_HELPER_SHA = "7e2ff0e719304df4667baa988c416307405c61b5bca090f6609b8715eb024ee2"
PROOF_DIR = "var/research/native-exaone45-contract/"
PUBLIC_SHA = "fc7109fe4e9fbbe4a619ad16dc701cda01a4976ec8bd53d726aeb09f34f39408"
RAW_SHA = "2ce12c5e4d93f7d3baff40da67b1f2c3b5575e117dff081c84d03835e07e8c9d"
CONTEXT_SHA = "f450e9f0bf3a206204474ed860bc6d191597cbe6cc31a7349efe894b5d3775bb"
RAW_FIXTURE_SHA = "9a379ccf7cab7c85c23582c45f77c6b4ec481a9bb1469009564dba0fe894bf2c"
OFFICIAL_FIXTURE_SHA = "49b40b3390cba92f3088c22606632348ba261e69ea0b385b74aa9126be8c46cb"
START = "evaluations/results/phase5x/exaone45-native-startup-epoch1/"
PUBLIC = "evaluations/results/phase5x/exaone45-native-public-smoke-epoch1/report.json"
RESOURCE = "evaluations/results/phase5x/exaone45-native-resource-epoch1/report.json"
CPU_ARCHIVE = "evaluations/results/phase5x/exaone45-cpu-preflight/contract/final-cpu-proof.json"
REGRESSION = "evaluations/results/phase5x/exaone45-template-header-preflight/regression.json"
REGRESSION_SHA = "15ed600049b27c1b32400e95e4d42c78a7501d1352d821dab300a2369135930b"
REGRESSION_LOG_SHA = "b2ae7a43b2fa3af31758528cf0ada58a63e689c6da6f53434f738bfe419ef20b"

def override_contract():
    return {'path':OVERRIDE_PATH,'sha256':TEMPLATE_SHA,'bytes':5829,
            'original_embedded_template_sha256':ORIGINAL_TEMPLATE_SHA,
            'transform':'continue-free-system-message-branch-v1'}

def expected_cpu_provenance(context):
    """Reconstruct receipt fields from exact frozen CPU metadata, without importing runtime code."""
    return {'runtime_variant':VARIANT,'model_id':MODEL,'model_revision':REVISION,
        'manifest_sha256':MANIFEST_SHA,'cpu_proof_sha256':CPU_SHA,'cpu_proof_kind':context['kind'],
        'chat_template_sha256':TEMPLATE_SHA,'original_embedded_template_sha256':ORIGINAL_TEMPLATE_SHA,
        'effective_chat_template_sha256':TEMPLATE_SHA,'runtime_launcher_sha256':LAUNCHER_SHA,
        'chat_template_override':override_contract(),'template_render_parity':context['template_render_parity'],
        'tokenizer_json_sha256':TOKENIZER_SHA,
        'official_reference_limitation':{'case_count':20,'raw_original_roundtrip_count':18,
            'raw_original_mismatch_indices':[11,12],'nfc_source_roundtrip_count':20,
            'normalizer':'NFC','native_parity_observed':False},
        'template_proof_variant':TEMPLATE_VARIANT,'official_hf_equivalence':context['official_hf_equivalence'],
        'context_tokenizer':'native_raw_unicode_no_nfc_repair','official_fixture_sha256':OFFICIAL_FIXTURE_SHA,
        'application_input_output_nfc_repair':False,'cpu_proof_refs':context['proof_refs'],
        'cpu_source_sha256':context['source_sha256'],'cpu_checks_rerun':False,
        'tokenizer_contract_status':'EXPLICIT_RAW_REFERENCE_CPU_PASS_OFFICIAL_HF_FAIL',
        'raw_reference':context['raw_reference'],'normalization_limitation':context['normalization_limitation'],
        'tokenizer_contract':'native_raw_unicode_no_nfc_repair',
        'official_reference_fixture_ref':context['official_reference_fixture_ref']}

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
          and freeze['chat_template_override'] == override_contract(),
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
        if key == "timeout_seconds":
            check(all(type(value) in (int, float) and value == expected and math.isfinite(value)
                      for value in (p[key], freeze[key])), "protocol_" + key)
        else:
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
    """Read pinned small archives only; never query a live process or rehash weights."""
    runtime_path = project_path(freeze["runtime_metadata"])
    check(runtime_path.name == "runtime_metadata.json"
          and runtime_path.is_relative_to(ROOT / "evaluations/results/phase5x"), "runtime_archive_scope")
    start = str(runtime_path.parent.relative_to(ROOT)) + "/"
    check(start == START and freeze["runtime_metadata"] == START+"runtime_metadata.json"
          and freeze["public_smoke_report"] == PUBLIC and freeze["resource_probe_report"] == RESOURCE, "exact_epoch_archive_paths")
    public_path = freeze["public_smoke_report"]
    resource_path = freeze["resource_probe_report"]
    for name in (public_path, resource_path):
        check(project_path(name).is_relative_to(ROOT / "evaluations/results/phase5x")
              and name in hashes, "smoke_archive_scope")
    startup = load(start + "startup.json")
    guard = load(start + "resource_report.json")
    listeners = load(start + "listeners.json")
    cpu_path = freeze["cpu_context_report"]
    check(cpu_path == PROOF_DIR+"final-cpu-proof.json" and freeze["cpu_context_archive"] == CPU_ARCHIVE, "exact_cpu_paths")
    context = load(cpu_path)
    public, resource = load(public_path), load(resource_path)
    check(startup["embedded_chat_template_sha256"] == ORIGINAL_TEMPLATE_SHA
          and startup["chat_template_sha256"] == startup["effective_chat_template_sha256"] == TEMPLATE_SHA
          and startup["effective_chat_template_bytes"] == 5829
          and startup["embedded_chat_template_bytes"] == 5930
          and startup["props_reported_template_sha256"] == "b8bc1ef1b1fcd30cdd28fe7655bf79020aec666142107c01231b7b59f15cb1ef"
          and startup["props_reported_template_bytes"] == 5828, "template_representation_exact")
    check(runtime["startup_report_sha256"] == hashes[start + "startup.json"]
          and runtime["listener_report_sha256"] == hashes[start + "listeners.json"]
          and runtime["launch_config_sha256"] == hashes[start + "launch_config.json"]
          and startup["resource_report_sha256"] == hashes[start + "resource_report.json"], "startup_hash_edges")
    check(hashes[cpu_path] == hashes[freeze["cpu_context_archive"]] == CPU_SHA, "cpu_exact_pin_and_archive")
    for key, expected in {"kind":"EXAONE45_NATIVE_CONTRACT_CPU_PROOF", "status":"PASS",
            "model_id":MODEL, "revision":REVISION, "gguf_sha256":GGUF_SHA, "header_sha256":HEADER_SHA,
            "source_pin":SOURCE_PIN, "template_sha256":TEMPLATE_SHA, "tokenizer_json_sha256":TOKENIZER_SHA,
            "protocol":"llama_cpp_json_schema", "sampling_profile":PROFILE, "enable_thinking":False,
            "application_input_output_nfc_repair":False, "model_inference_calls":0, "gpu_or_http_calls":0,
            "max_output_tokens":768, "max_context_tokens":4096}.items():
        check(type(context[key]) is type(expected) and context[key] == expected, "cpu_"+key)
    check(context['runtime_variant'] == VARIANT and context['template_proof_variant'] == TEMPLATE_VARIANT
          and context['original_embedded_template_sha256'] == ORIGINAL_TEMPLATE_SHA
          and context['runtime_launcher_sha256'] == LAUNCHER_SHA
          and context['chat_template_override'] == freeze['chat_template_override'] == override_contract(),
          'cpu_override_variant')
    official={'status':'FAIL','case_count':20,'id_match_count':18,'mismatch_indices':[11,12],
        'native_raw_roundtrip_count':20,'official_ids_raw_roundtrip_count':18,
        'proof_ref':{'path':PROOF_DIR+'public-vocab-proof.json','sha256':OFFICIAL_VOCAB_SHA}}
    raw_reference={'reference_kind':'official_metadata_with_only_NFC_normalizer_disabled',
        'fixture_ref':{'path':PROOF_DIR+'raw-reference-diagnostic.json','sha256':RAW_FIXTURE_SHA},
        'proof_ref':{'path':PROOF_DIR+'raw-vocab-proof.json','sha256':RAW_SHA},
        'case_count':20,'id_match_count':20,'native_raw_roundtrip_count':20,
        'official_hf_equivalence':'NOT_ASSERTED_BY_DERIVED_REFERENCE'}
    check(context['official_hf_equivalence'] == freeze['official_hf_equivalence'] == official
          and context['raw_reference'] == freeze['raw_reference'] == raw_reference,
          'official_failure_derived_success_distinct')
    normalization={'official_normalizer':'NFC','official_public_raw_roundtrip_count':18,
        'native_public_raw_roundtrip_count':20,'public_case_count':20,'global_unicode_roundtrip_guarantee':False}
    check(context['normalization_limitation'] == freeze['normalization_limitation'] == normalization
          and context['context_tokenizer'] == freeze['context_tokenizer'] == 'native_raw_unicode_no_nfc_repair',
          'unicode_limitation_retained')
    linked={PROOF_DIR+'public-proof-v3.json':PUBLIC_SHA,
            PROOF_DIR+'public-vocab-proof.json':OFFICIAL_VOCAB_SHA,
            PROOF_DIR+'raw-vocab-proof.json':RAW_SHA,
            PROOF_DIR+'vocab-context-raw-proof.json':CONTEXT_SHA,
            PROOF_DIR+'raw-reference-diagnostic.json':RAW_FIXTURE_SHA,
            PROOF_DIR+'official-tokenizer-fixture.json':OFFICIAL_FIXTURE_SHA}
    for name,value in linked.items():check(hashes[name] == value,'cpu_component_pin')
    orig=load(PROOF_DIR+'public-vocab-proof.json');raw=load(PROOF_DIR+'raw-vocab-proof.json')
    actual_context=load(PROOF_DIR+'vocab-context-raw-proof.json')
    check(orig['status']=='FAIL' and orig['native']['tokenizer_id_match_count']==18
          and orig['native']['tokenizer_id_mismatch_mask']==6144
          and orig['native']['tokenizer_reference_parity']=='FAIL', 'actual_official_failure')
    for proof in (raw,actual_context):
        check(proof['status']=='PASS' and proof['runtime_variant']==VARIANT
              and proof['official_native_failure_sha256']==OFFICIAL_VOCAB_SHA
              and proof['raw_reference_sha256']==RAW_FIXTURE_SHA
              and proof['effective_template_sha256']==TEMPLATE_SHA
              and proof['original_embedded_template_sha256']==ORIGINAL_TEMPLATE_SHA
              and proof['application_input_output_nfc_repair'] is False,
              'actual_raw_reference_binding')
    for n in [raw['native'], *actual_context['native_checks']]:
        check(n['reference_kind']=='derived_hf_nfc_disabled' and n['reference_gate_pass'] is True
              and n['official_hf_equivalence']=='NOT_ASSERTED_BY_DERIVED_REFERENCE'
              and n['tokenizer_id_match_count']==n['tokenizer_native_raw_roundtrip_count']==20
              and n['all_context_system_user_bytes_exact'] is True
              and n['native_request_prompt_bytes']==9176 and n['native_vocab_grammar_eog_checked'] is True,
              'actual_raw_native_observation')
    check(actual_context['splits']==context['splits'] and len(actual_context['native_checks'])==2
          and actual_context['max_output_tokens']==768 and actual_context['max_context_tokens']==4096
          and actual_context['resource_probe_token']==context['resource_probe_token']=={
              'text':' ','token_id':582,'native_token_count':1,'native_roundtrip':True}, 'actual_context_cpu_binding')
    check(set(context["splits"]) == {"exposed120", "v2_length80"}, "cpu_context_split_set")
    for split,count,dataset_sha in (("exposed120",120,"7e5b9a05932df7aafdbf683655b044b3e3b25cbffb4115d298e1490aecbc7a5b"),
            ("v2_length80",80,"7416f05613b1490358672f3926770dbd8653e676577eeee6ba65f863b27cec40")):
        row=context["splits"][split]
        check(row["input_count"] == count and row["dataset_sha256"] == dataset_sha
              and type(row["min_input_tokens"]) is int and type(row["max_input_tokens"]) is int
              and 0 < row["min_input_tokens"] <= row["max_input_tokens"]
              and row["max_input_plus_output"] == row["max_input_tokens"]+768 <= 4096, "cpu_context_counts")
    check(set(context["source_sha256"]) == {PATHS[k] for k in ("client","parser","generation_adapter","prompt","schema")},
          "cpu_source_set")
    for name,value in context["source_sha256"].items():
        check(hashes[name] == value, "cpu_frozen_source_hash")
    check(set(context["proof_refs"]) == {"public_contract","vocab_context","tokenizer_fixture"}, "cpu_proof_reference_set")
    for ref in context["proof_refs"].values():
        check(set(ref) == {"path","sha256"} and hashes[ref["path"]] == ref["sha256"], "cpu_reference_hash")
    provenance = expected_cpu_provenance(context)
    check(freeze["tokenizer_contract"] == provenance, "tokenizer_provenance_exact")
    for proof in (startup, public, resource):
        check(all(proof[key] == value for key,value in provenance.items()), "runtime_cpu_provenance_edges")
    epoch = freeze["runtime_epoch_snapshot"]
    check(startup["kind"] == "EXAONE45_NATIVE_STARTUP_HTTP_PROOF" and startup["status"] == "PASS"
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
    check(artifacts['chat_template_override']=={'path':OVERRIDE_PATH,'sha256':TEMPLATE_SHA}, 'guard_override_identity')
    check(guard["max_model_len"] == 4096 and guard["enable_reasoning"] is False
          and guard["reasoning_parser"] == "deepseek" and guard["served_model_name"] == launch["served_model_name"],
          "guard_generation_scope")
    check(public["status"] == "PASS" and public["kind"] == "EXAONE45_NATIVE_PUBLIC_PRODUCTION_SMOKE"
          and public["sampling_profile"] == PROFILE and public["http_calls_attempted"] == 1
          and public["quality_gate_pass"] is False and public["generated_body_retained"] is False,
          "public_smoke_scope")
    check(resource["kind"] == "EXAONE45_NATIVE_PUBLIC_CONTEXT_RESOURCE_PROBE" and resource["status"] == "PASS"
          and resource["http_post_calls"] == 1, "resource_smoke_scope")
    check(resource["tokens_evaluated"] == resource["timings/prompt_n"] == 3328
          and resource["tokens_predicted"] == resource["timings/predicted_n"] == 768
          and resource["tokens_cached"] == 4095 and resource["stop"] is True
          and resource["truncated"] is True and resource["stop_type"] == "limit"
          and resource["quality_evaluation"] is False and resource["grammar_enabled"] is False
          and resource["generated_body_retained"] is False, "resource_full_context_boundary")
    for proof in (startup, public, resource):
        check(proof["pid"] == epoch["pid"] and proof["process_start_ticks"] == epoch["start_ticks"]
              and proof["guard_started_at_utc"] == epoch["guard_started_at_utc"]
              and proof["launch_config_sha256"] == hashes[start + "launch_config.json"], "smoke_epoch")
    weights = load(PATHS["weight_manifest"])
    check(weights["model_id"] == MODEL and weights["revision"] == REVISION, "weight_manifest_identity")
    ggufs = [entry for entry in weights["files"] if entry["name"].endswith(".gguf")]
    check(len(ggufs) == 1 and ggufs[0]["sha256"] == GGUF_SHA and ggufs[0]["bytes"] == GGUF_BYTES,
          "weight_manifest_exact_quant")
    check(launch["max_seconds"] == 7200 and runtime["gguf_header_sha256"] == HEADER_SHA, "launch_known_header_lifetime")
    clock = freeze["guard_time_observation"]
    check(clock["guard_max_seconds"] == 7200
          and type(clock["elapsed_seconds_at_freeze"]) in (int,float)
          and math.isfinite(clock["elapsed_seconds_at_freeze"])
          and 0 <= guard["elapsed_seconds"] <= clock["elapsed_seconds_at_freeze"] < 7200
          and clock["remaining_seconds_at_freeze"] == 7200-clock["elapsed_seconds_at_freeze"]
          and clock["first_request_requires_fresh_root_time_decision"] is True, "guard_time_observation")
    check(freeze["prior_v2_model_output_exposure_record"] == V2_OUTPUT_EXPOSURE
          and hashes[V2_OUTPUT_EXPOSURE] == V2_OUTPUT_EXPOSURE_SHA, "prior_v2_outputs_exposed")
    receipt = load(REGRESSION)
    check(hashes[REGRESSION] == REGRESSION_SHA and receipt == freeze['regression']
          and receipt['kind'] == 'OPTIONAL_NATIVE_TEMPLATE_OVERRIDE_REGRESSION'
          and receipt['status'] == 'PASS' and receipt['tests'] == 408 and receipt['skipped'] == 0
          and receipt['headless'] is True and receipt['actual_postgresql_and_ifcopenshell'] is True
          and receipt['cuda_visible_devices'] == '' and receipt['model_gpu_calls'] == 0, 'regression_receipt')
    check(hashes[receipt['log_path']] == receipt['log_sha256'] == REGRESSION_LOG_SHA, 'regression_log_pin')
    for name,value in receipt['source_sha256'].items():check(hashes[name] == value, 'regression_source_pin')
    check(hashes['scripts/llama_server.py'] == LAUNCHER_SHA
          and hashes[RUNTIME_HELPER] == RUNTIME_HELPER_SHA, 'runtime_source_helper_pins')


def validate_frozen_parent(freeze):
    """v4 is an explicit post-freeze amendment, never a substituted frozen helper."""
    check(freeze['sha256'].get(FROZEN_PARENT_PATH) == FROZEN_PARENT_SHA
          and digest(project_path(FROZEN_PARENT_PATH)) == FROZEN_PARENT_SHA,
          'original_frozen_replay_parent_changed')


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
    validate_frozen_parent(freeze)
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
        "offline_validator_amendment": {"pre_run_frozen": False,
            "frozen_parent_path": FROZEN_PARENT_PATH, "frozen_parent_sha256": FROZEN_PARENT_SHA,
            "change": "Only timeout_seconds accepts finite numeric120 as int or float; boolean/nonfinite/other values rejected.",
            "core_functions_ast_unchanged": ["load_snapshot", "replay_row", "replay_groups"]},
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
