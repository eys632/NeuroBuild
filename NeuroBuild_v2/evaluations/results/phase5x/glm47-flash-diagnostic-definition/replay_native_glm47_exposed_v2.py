"""GLM first exposed120x1+5 offline replay, completed new run only.

Only a completed new run may be audited after exact frozen CPU/runtime evidence
passes. No historical result replay is performed as a prerequisite.
Source/evaluate_trial/score/summary formulas are copied unchanged from the final
EXAONE replay, including its finite numeric timeout120 fix. No historical replay
amendment applies to this new pre-run candidate.
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

ROOT = Path('/home/a202192020/NeuroBuild_v2')
MODEL = 'ggml-org/GLM-4.7-Flash-GGUF'
REVISION = '7559e96b7e324ab405897dc2b91492b0f376ad4a'
VARIANT = 'glm47-flash-gguf-nonthinking-v1'
SOURCE_PIN = 'f072b103714dfa1eee531f80b24512faf38e3dd2'
GGUF_SHA = 'b6019edc5fbe37d3660d2e994d16c839a7855a6f03362c5dcf8142ba479cd0d2'
GGUF_BYTES = 18244193920
TEMPLATE_SHA = 'd63ad536c3c81880043e22ec7fd08db42b4d8fb7c89c7138bc562bfa25281375'
TOKENIZER_SHA = '19e773648cb4e65de8660ea6365e10acca112d42a854923df93db4a6f333a82d'
HEADER_SHA = '595a7efd19914b65e91f1d92aaee141a0457472039c7278264cc1b5d314659ef'
PROFILE = 'glm47_flash_nonthinking_llama_cpp'
LIFECYCLE = 'FROZEN_BEFORE_NATIVE_GLM47_FLASH_EXPOSED_DIAGNOSTIC'
PREPARATION_STATUS = 'FINAL_DEFINITION_REQUIRES_ACTUAL_SAVED_RUNTIME_PASS'
CPU_SHA = '54ab0062c5d22112ed3349e0021391a4dd17f6d5f8698ac8a02cc096b08a1847'
REGRESSION = 'evaluations/results/phase5x/glm47-flash-preparation/regression/regression.json'
CPU = 'var/research/native-glm47-contract/final-cpu-proof.json'
START = 'evaluations/results/phase5x/glm47-flash-native-startup-epoch1/'
PUBLIC = 'evaluations/results/phase5x/glm47-flash-native-public-smoke-epoch1/report.json'
RESOURCE = 'evaluations/results/phase5x/glm47-flash-native-resource-epoch1/report.json'
PROBE = 'var/research/glm47_flash_runtime_probe_v2.py'
V2_FREEZE = 'evaluations/hardening_v2_dataset_freeze.json'
V2_EXPOSURE = 'evaluations/hardening_v2_input_exposure_addendum.json'
V2_OUTPUT_EXPOSURE = 'evaluations/hardening_v2_model_output_exposure_record.json'
GATES = {'schema_required': 120, 'schema_denominator': 120, 'semantic_required_at_least': 114, 'semantic_denominator': 120, 'critical_model_ready_fp_required': 0, 'critical_model_ready_fp_denominator': 58, 'unsafe_accepted_ready_total_required': 0, 'unsafe_accepted_ready_total_denominator': 120}
SAMPLING = {'temperature': 1.0, 'top_p': 0.95, 'top_k': 0, 'min_p': 0.0, 'presence_penalty': 0.0, 'frequency_penalty': 0.0, 'repeat_penalty': 1.0, 'repeat_last_n': 0, 'seed': 42, 'samplers': ['temperature', 'top_k', 'top_p', 'min_p']}
PATHS = {'dataset': 'evaluations/requirement_hardening_v1_exposed_regression.jsonl', 'prompt': 'prompts/requirement_generation_v2_v2.txt', 'schema': 'schemas/requirement_generation_v2_decision_branches.schema.json', 'canonical_schema': 'schemas/semantic_requirement.schema.json', 'generation_adapter': 'src/neurobuild/application/requirement_generation.py', 'parser': 'src/neurobuild/application/requirements.py', 'client': 'src/neurobuild/infrastructure/local_model.py', 'scorer': 'scripts/evaluate_requirements.py', 'weight_manifest': 'runtime/models/glm47-flash-q4-k.json'}
COPY_SOURCE_SHA = '177bc501c5be5bb9e240414ec49216b99d8621d9306250eb1446b73dc05dca3f'


CONFIG_SHA = '4824463fcabca13c2eaa07a9774c324b7980a2383915868f4f493b149dc245c4'
PROBE_SHA = '4399c90d32e0e472455bae5e907c8a479fdac550fed46978d8001c6d894d69ea'
CPU_ARCHIVED_PROOF = 'evaluations/results/phase5x/glm47-flash-runtime-definition/aggregate/final-cpu-proof.json'
RUNTIME_ARCHIVE = 'evaluations/results/phase5x/glm47-flash-runtime-definition'
CONTROLLER = 'var/research/run_native_glm47_epoch1_probe_v2.py'
CONTROLLER_SHA = '065f41afb9b5d55297f4e5114fba3642eeb3adaab18fcf21e6e0c5f42aeaba37'
RUNTIME_CPU_PROOF = 'var/research/glm47-runtime-v2-cpu-proof.json'
RUNTIME_CPU_PROOF_SHA = '0690eee68f5479927fb174243b4073cf26af433f8449a3ce9be124cbab15ac22'
REGRESSION_SHA = '293bfc5b4f94e728af5eeb021a3aae2230376a74dae6e631d0c70a1c4e513fac'
REGRESSION_LOG_SHA = 'c342132012c9d6192164b09ddf3c806b82faaaaec3cc8be99379f2cea2e0463d'
LAUNCHER_SHA = '6a58ee1ea09636df182125da4a4a2711012e6c53f5f90c06548a63b9915369ed'
CPU_REFS = {'header': {'path': 'var/reports/glm47-flash-gguf-header.json', 'sha256': '595a7efd19914b65e91f1d92aaee141a0457472039c7278264cc1b5d314659ef'}, 'public_contract': {'path': 'var/research/native-glm47-contract/public-proof-v3.json', 'sha256': 'd8f8fe1faf2ee73b06f6df35d16dba3a29cb78ad41af35a8a1be6cff888ac85c'}, 'public_vocab': {'path': 'var/research/native-glm47-contract/public-vocab-proof.json', 'sha256': 'f3e31a724dcec94f6d3b285a9dd793d6a8b6c91c3c8c475a63c25709c94d6cf7'}, 'tokenizer_fixture': {'path': 'var/research/native-glm47-contract/official-tokenizer-fixture.json', 'sha256': 'e67bd4d05462587e0466f092351ada8c8fa4efdd9a10da0b4cecb25a4d3dc8f3'}, 'vocab_context': {'path': 'var/research/native-glm47-contract/vocab-context-proof.json', 'sha256': '66e2ab245e0d7c2a2760d2b98e0a191fb8b27248be6fae6d61cf922c814bb607'}}
CPU_SOURCE = {'prompts/requirement_generation_v2_v2.txt': '99d737124372836ba5f985fa6e5570afef693e769798844931f000fb21403cf6', 'schemas/requirement_generation_v2_decision_branches.schema.json': '36d42b9fa3d24f4a1bc1d14381110e36e8d89103b696bc83113be006b64934e2', 'src/neurobuild/application/requirement_generation.py': 'fcba16f6adc906923859f3bcf4ae2f680e76716863a759582167cd9326f03198', 'src/neurobuild/application/requirements.py': 'a940f3952c0c4133ab51732f6abf76516d8ff66617470545222b52adfa49fb4a', 'src/neurobuild/infrastructure/local_model.py': '7dfc3f673ba6ab4e4970055c4cbee66ae440da2d42070af959a5fe415a9ab780'}
V2_OUTPUT_EXPOSURE_SHA = '25c080827a6d57aa6bc864495e537490dc7fa48b3ccf91df297a47b9815d447b'

def require_ready():
    # Exact saved receipts are still required by validation; no missing-proof bypass.
    assert CPU_SHA and CONFIG_SHA and PROBE_SHA, 'FINAL_EVIDENCE_PINS_PENDING'

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
    check(freeze['chat_template_override'] is None
          and freeze['original_embedded_template_sha256'] == TEMPLATE_SHA
          and freeze['effective_chat_template_sha256'] == TEMPLATE_SHA,
          'official_template_without_override')
    check(launch.get('chat_template_path') is None and launch.get('chat_template_sha256') is None,
          'no_launch_template_override')
    check(freeze['application_input_output_nfc_repair'] is False,
          'no_application_input_output_repair')
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
    check(p["temperature"] == 1.0 and p["seed"] == 42, "sampling_mirrors")
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

def validate_cpu_metadata(context, hashes):
    for key, expected in {'kind':'GLM47_FLASH_NATIVE_CONTRACT_CPU_PROOF','status':'PASS',
            'candidate_variant':VARIANT,'model_id':MODEL,'revision':REVISION,'gguf_sha256':GGUF_SHA,
            'header_sha256':HEADER_SHA,'source_pin':SOURCE_PIN,'template_sha256':TEMPLATE_SHA,
            'tokenizer_json_sha256':TOKENIZER_SHA,'protocol':'llama_cpp_json_schema',
            'sampling_profile':PROFILE,'model_inference_calls':0,'gpu_calls':0,'http_calls':0,
            'max_output_tokens':768,'max_context_tokens':4096,'application_input_output_nfc_repair':False,
            'official_tokenizer_normalizer':None,'template_override_used':False}.items():
        check(type(context[key]) is type(expected) and context[key]==expected,'cpu_'+key)
    check(context['sampling_request_parameters']==SAMPLING
          and all(type(context['sampling_request_parameters'][k]) is type(v) for k,v in SAMPLING.items()), 'cpu_sampling')
    check(context['official_tokenizer_parity']=={'status':'PASS','case_count':20,'id_match_count':20,
          'native_original_roundtrip_count':20},'cpu_official_parity')
    check(context['source_sha256']==CPU_SOURCE and context['proof_refs']==CPU_REFS,'cpu_exact_sources_refs')
    for name,value in CPU_SOURCE.items():check(hashes[name]==value,'cpu_frozen_source')
    for ref in CPU_REFS.values():check(hashes[ref['path']]==ref['sha256'],'cpu_frozen_reference')
    check(set(context['splits'])=={'exposed120','v2_length80'},'cpu_split_set')
    for name,count,data_sha in [('exposed120',120,'7e5b9a05932df7aafdbf683655b044b3e3b25cbffb4115d298e1490aecbc7a5b'),
            ('v2_length80',80,'7416f05613b1490358672f3926770dbd8653e676577eeee6ba65f863b27cec40')]:
        r=context['splits'][name]
        check(type(r['input_count']) is int and r['input_count']==count and r['dataset_sha256']==data_sha
              and all(type(r[k]) is int for k in ('min_input_tokens','max_input_tokens','max_input_plus_output'))
              and 0<r['min_input_tokens']<=r['max_input_tokens']
              and r['max_input_plus_output']==r['max_input_tokens']+768<=4096,'cpu_context_count')
    check(context['resource_probe_token']=={'text':' ','token_id':220,'native_token_count':1,'native_roundtrip':True},'cpu_resource_token')
    return {'candidate_variant':VARIANT,'model_id':MODEL,'model_revision':REVISION,'cpu_proof_sha256':CPU_SHA,
        'cpu_proof_kind':context['kind'],'chat_template_sha256':TEMPLATE_SHA,'tokenizer_json_sha256':TOKENIZER_SHA,
        'tokenizer_contract':'official_glm_metadata_native_public_parity_20_of_20',
        'official_tokenizer_parity':context['official_tokenizer_parity'],'application_input_output_nfc_repair':False,
        'cpu_proof_refs':context['proof_refs'],'cpu_source_sha256':context['source_sha256'],
        'normalization_limitation':context['normalization_limitation'],'reasoning_boundary':context['reasoning_boundary'],
        'cpu_checks_rerun':False}

def validate_evidence(freeze,runtime,launch,load,hashes):
    """Only frozen saved metadata; no process, HTTP, native or weight access."""
    start=START
    check(freeze['runtime_metadata']==start+'runtime_metadata.json' and freeze['public_smoke_report']==PUBLIC
          and freeze['resource_probe_report']==RESOURCE and freeze['cpu_context_report']==CPU
          and freeze['cpu_context_archive']==CPU_ARCHIVED_PROOF,'exact_evidence_paths')
    startup,guard,listeners=(load(start+n) for n in ('startup.json','resource_report.json','listeners.json'))
    context,public,resource=load(CPU),load(PUBLIC),load(RESOURCE)
    check(hashes[CPU]==hashes[CPU_ARCHIVED_PROOF]==CPU_SHA,'cpu_exact_pin_and_archive')
    provenance=validate_cpu_metadata(context,hashes)
    check(freeze['tokenizer_contract']==provenance and freeze['official_tokenizer_parity']==context['official_tokenizer_parity']
          and freeze['normalization_limitation']==context['normalization_limitation'],'cpu_frozen_provenance')
    for proof in (startup,public,resource):
        check(all(proof[k]==v for k,v in provenance.items()),'runtime_cpu_provenance_edges')
    check(startup['embedded_chat_template_sha256']==startup['chat_template_sha256']
          ==startup['props_reported_template_sha256']==TEMPLATE_SHA
          and startup['embedded_chat_template_bytes']==startup['props_reported_template_bytes']==3120,'template_representation')
    check(runtime['startup_report_sha256']==hashes[start+'startup.json']
          and runtime['listener_report_sha256']==hashes[start+'listeners.json']
          and runtime['launch_config_sha256']==hashes[start+'launch_config.json']==CONFIG_SHA
          and startup['resource_report_sha256']==hashes[start+'resource_report.json'],'startup_hash_edges')
    check(startup['native_startup_warmup_enabled'] is True
          and startup['model_inference_calls_scope']=='Explicit HTTP generation calls; native startup warmup is enabled and not counted',
          'startup_internal_warmup_scope')
    epoch = freeze["runtime_epoch_snapshot"]
    check(startup["kind"] == "GLM47_FLASH_NATIVE_STARTUP_HTTP_PROOF" and startup["status"] == "PASS"
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
    check('chat_template_override' not in artifacts, 'guard_no_override')
    check(guard["max_model_len"] == 4096 and guard["enable_reasoning"] is False
          and guard["reasoning_parser"] == "deepseek" and guard["served_model_name"] == launch["served_model_name"],
          "guard_generation_scope")
    check(public["status"] == "PASS" and public["kind"] == "GLM47_FLASH_NATIVE_PUBLIC_PRODUCTION_SMOKE"
          and public["sampling_profile"] == PROFILE and public["http_calls_attempted"] == 1
          and public["quality_gate_pass"] is False and public["generated_body_retained"] is False,
          "public_smoke_scope")
    check(resource["kind"] == "GLM47_FLASH_NATIVE_PUBLIC_CONTEXT_RESOURCE_PROBE" and resource["status"] == "PASS"
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
    receipt=load(REGRESSION)
    check(hashes[REGRESSION]==REGRESSION_SHA and receipt==freeze['regression']
          and receipt['kind']=='GLM47_EXPLICIT_NATIVE_PROFILE_REGRESSION' and receipt['status']=='PASS'
          and receipt['tests_run']==416 and receipt['skipped']==0 and receipt['duration_seconds']==19.398
          and receipt['real_postgresql'] is True and receipt['real_ifcopenshell'] is True
          and receipt['headless'] is True and receipt['cuda_visible_devices']==''
          and receipt['quality_model_calls']==receipt['old_evaluation_replay']==0,'regression_receipt')
    check(hashes[receipt['log_path']]==receipt['log_sha256']==REGRESSION_LOG_SHA,'regression_log_pin')
    for name,value in receipt['source_sha256'].items():check(hashes[name]==value,'regression_source_pin')
    check(hashes['scripts/llama_server.py']==LAUNCHER_SHA and hashes[PROBE]==PROBE_SHA
          and hashes[CONTROLLER]==CONTROLLER_SHA and hashes[RUNTIME_CPU_PROOF]==RUNTIME_CPU_PROOF_SHA,
          'runtime_definition_pins')

def main():
    require_ready()  # Before source snapshot, manifest, dataset or result access.
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
    check(freeze['sha256'].get(str(Path(__file__).relative_to(ROOT))) == digest(Path(__file__)), 'pre_run_frozen_replay_identity')
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
            "limitation": "Prior V2 model outputs already exposed; no V2 result replay or input parsing in this GLM exposed120 replay"},
        "replay_helper_sha256": digest(Path(__file__)),
        "replay_origin": {"pre_run_frozen": True, "source_copy_sha256": COPY_SOURCE_SHA,
            "core_functions_ast_unchanged": ["load_snapshot", "replay_row", "replay_groups"],
            "timeout_representation": "Finite numeric120 int/float accepted; bool/nonfinite rejected"},
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
