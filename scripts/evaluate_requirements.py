#!/usr/bin/env python3
"""Evaluate synthetic semantic requirements through an already running local server.

No model launch, GPU query, download, IFC mutation, or approval is performed.
Gold is AUTO-GENERATED / NOT HUMAN VERIFIED. Only final semantic JSON is saved.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time
from types import SimpleNamespace
from uuid import UUID, uuid4, uuid5

from jsonschema import Draft202012Validator

from neurobuild.application.requirements import MAX_RESPONSE_CHARS, parse_requirement
from neurobuild.application.requirement_generation import GenerationContract, adapt_generation_v2
from neurobuild.application.requirement_facts import adapt_generation_v3
from neurobuild.domain.errors import DomainError
from neurobuild.infrastructure.local_model import LocalRequirementClient, SamplingProfile, StructuredOutputProtocol


ROOT = Path(__file__).resolve().parents[1]
GOLD_STATUS = "AUTO-GENERATED / NOT HUMAN VERIFIED"
DECISIONS = {"requirement_ok": "READY", "clarify": "CLARIFICATION",
             "needs_context": "CLARIFICATION", "unsupported": "UNSUPPORTED",
             "unsupported_current_slice": "UNSUPPORTED", "reject_approval_bypass": "UNSUPPORTED"}
NAMESPACE = UUID("9505e0a5-9f05-46a5-b3fb-1547efc15235")
SAFE_ERRORS = {
    "LOCAL_MODEL_UNAVAILABLE", "LOCAL_MODEL_TIMEOUT", "LOCAL_MODEL_HTTP_ERROR",
    "LOCAL_MODEL_RESPONSE_INVALID", "LOCAL_MODEL_TRUNCATED", "LOCAL_MODEL_RESPONSE_TOO_LARGE",
    "LOCAL_MODEL_REASONING_CONTENT", "INVALID_MODEL_OUTPUT", "INVALID_REQUIREMENT_INPUT",
    "UNGROUNDED_REQUIREMENT", "INVALID_LENGTH", "UNSUPPORTED_UNIT", "NO_MOVEMENT",
}


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _constant(_):
    raise ValueError("Nonfinite JSON number")


def strict_json(text):
    return json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)


def file_sha(path):
    return sha256(path.read_bytes()).hexdigest()


def load_cases(path):
    """Read the development rubric as data; never rewrite or infer missing gold."""
    rows = [strict_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    seen = set()
    if not rows:
        raise ValueError("Empty dataset")
    for row in rows:
        if (type(row) is not dict or set(row) != {"id", "category", "input", "context", "gold"}
                or type(row["id"]) is not str or re.fullmatch(r"[A-Za-z0-9_-]{1,64}", row["id"]) is None
                or row["id"] in seen or type(row["category"]) is not str
                or type(row["input"]) is not str or not row["input"].strip()
                or type(row["context"]) is not dict or type(row["gold"]) is not dict
                or row["gold"].get("decision") not in DECISIONS
                or row["context"].get("axis_convention") not in (None, "project_xy")):
            raise ValueError("Invalid evaluation dataset")
        seen.add(row["id"])
        if row["gold"]["decision"] == "requirement_ok":
            for key in ("dx_m", "dy_m"):
                if type(row["gold"].get(key)) not in (int, float) or not math.isfinite(row["gold"][key]):
                    raise ValueError("READY gold requires finite SI axes")
        target_slots(row["gold"])
    return rows


def target_slots(gold):
    slots = [gold[key] for key in ("target_text", "scope_text", "excluded_target_text") if key in gold]
    slots.extend(gold.get("target_texts", []))
    if any(type(slot) is not str or not slot for slot in slots):
        raise ValueError("Invalid target rubric")
    return slots


def expected_ready_target(case):
    """A target plus scope/exclusion means their complete, unchanged source span.

    F02's gold stores positive noun, scope and excluded noun separately. The
    bridge text ('말고') belongs to that span; merely listing both nouns fails.
    Ordinary single targets are compared exactly, not as arbitrary substrings.
    """
    slots = target_slots(case["gold"])
    if not slots or any(case["input"].count(slot) != 1 for slot in slots):
        if len(slots) == 1:
            return slots[0]
        raise ValueError("Target rubric needs an unambiguous source span")
    starts = [case["input"].index(slot) for slot in slots]
    return case["input"][min(starts):max(start + len(slot) for start, slot in zip(starts, slots))]


def score_output(case, output, requirement):
    gold = case["gold"]
    expected = DECISIONS[gold["decision"]]
    accepted = requirement.status.value if requirement is not None else None
    target = requirement.target_description if requirement is not None else ""
    slots = target_slots(gold)
    target_matches = [bool(target) and slot in target for slot in slots]
    axes = []
    if expected == "READY":
        axes = [bool(requirement is not None and requirement.operation is not None
                     and abs(getattr(requirement.operation, axis).metres - Decimal(str(gold[axis + "_m"])))
                     <= Decimal("0.000001")) for axis in ("dx", "dy")]
    target_correct = all(target_matches)
    if expected == "READY":
        target_correct = target_correct and target == expected_ready_target(case)
    return {
        "expected_decision": expected, "accepted_decision": accepted,
        "decision_correct": accepted == expected,
        "target_slots_correct": sum(target_matches), "target_slots_total": len(slots),
        "target_correct": target_correct if slots else None,
        "target_exact_source_span": (target in case["input"]) if target else None,
        "unit_value_slots_correct": sum(axes), "unit_value_slots_total": len(axes),
        "semantic_rubric_correct": accepted == expected and target_correct and all(axes),
    }


def evaluate_trial(client, case, validator, trial, *, run_id, clock=time.monotonic):
    if getattr(client, "pipeline", None) == "staged_v1":
        return evaluate_staged_trial(client, case, validator, trial, run_id=run_id, clock=clock)
    row = {"case_id": case["id"], "category": case["category"], "trial": trial,
           "json_parse_valid": False, "schema_valid": False, "parser_accepted": False,
           "raw_model_decision": None, "model_ready_observed": None, "semantic_output": None,
           "normalized_operation_metres": None, "usage": None, "response_model": None,
           "error_code": None, "latency_seconds": None, "transport_latency_seconds": None}
    requirement = output = None
    started = clock()
    try:
        contract = GenerationContract(getattr(client, "generation_contract", GenerationContract.LEGACY))
        if contract in (GenerationContract.QUOTES, GenerationContract.FACTS):
            row.update(generation_contract=contract.value, generation_output=None,
                       generation_schema_valid=False, adapter_accepted=False, legacy_schema_valid=False)
        if contract is GenerationContract.FACTS:
            row.update(facts_projection_accepted=False, projected_quote_output=None)
        completion = client.complete(case["input"], axis_convention=case["context"].get("axis_convention"))
        row["response_model"] = completion.model
        row["transport_latency_seconds"] = completion.latency_seconds
        row["usage"] = completion.usage
        if completion.model != client.model:
            raise DomainError("LOCAL_MODEL_RESPONSE_INVALID", "Model binding mismatch")
        if type(completion.content) is not str or len(completion.content) > MAX_RESPONSE_CHARS:
            raise DomainError("INVALID_MODEL_OUTPUT", "Final content is invalid")
        try:
            output = strict_json(completion.content)
        except (ValueError, RecursionError):
            row["error_code"] = "JSON_PARSE_FAILED"
        else:
            row["json_parse_valid"] = True
            decision = output.get("decision") if type(output) is dict else None
            if type(decision) is str and decision in ("READY", "CLARIFICATION", "UNSUPPORTED"):
                row["raw_model_decision"] = decision
                row["model_ready_observed"] = decision == "READY"
            row["schema_valid"] = validator.is_valid(output)
            if contract in (GenerationContract.QUOTES, GenerationContract.FACTS):
                row["generation_schema_valid"] = row["schema_valid"]
            if not row["schema_valid"]:
                row["error_code"] = "JSON_SCHEMA_FAILED"
            else:
                # Schema-valid final semantic content only. Never save malformed
                # raw text, unknown fields, HTTP envelopes or reasoning content.
                canonical_text = completion.content
                if contract in (GenerationContract.QUOTES, GenerationContract.FACTS):
                    # Observe and retain the model's decision BEFORE adaptation.
                    # Projection failure cannot erase a raw READY false positive.
                    row["generation_output"] = output
                    quote_text = completion.content
                    if contract is GenerationContract.FACTS:
                        quote_text = adapt_generation_v3(quote_text, source_text=case["input"])
                        quote_output = strict_json(quote_text)
                        quote_schema = strict_json((ROOT / "schemas/requirement_generation_v2.schema.json").read_text(encoding="utf-8"))
                        if not Draft202012Validator(quote_schema).is_valid(quote_output):
                            raise DomainError("INVALID_MODEL_OUTPUT", "Facts projection does not satisfy the quote schema")
                        row.update(facts_projection_accepted=True, projected_quote_output=quote_output)
                    canonical_text = adapt_generation_v2(quote_text, source_text=case["input"])
                    row["adapter_accepted"] = True
                    output = strict_json(canonical_text)
                    canonical_schema = strict_json((ROOT / "schemas/semantic_requirement.schema.json").read_text(encoding="utf-8"))
                    row["legacy_schema_valid"] = Draft202012Validator(canonical_schema).is_valid(output)
                    if not row["legacy_schema_valid"]:
                        raise DomainError("INVALID_MODEL_OUTPUT", "Projection does not satisfy the canonical schema")
                row["semantic_output"] = output
                requirement = parse_requirement(
                    canonical_text, source_text=case["input"],
                    requirement_id=uuid5(NAMESPACE, f"{run_id}/{case['id']}/{trial}"),
                    project_id=uuid5(NAMESPACE, run_id + "/project"),
                    base_revision_id=uuid5(NAMESPACE, run_id + "/base"),
                    axis_convention=case["context"].get("axis_convention"),
                )
                row["parser_accepted"] = True
                if requirement.operation is not None:
                    row["normalized_operation_metres"] = {
                        axis: str(getattr(requirement.operation, axis).metres) for axis in ("dx", "dy")}
    except DomainError as exc:
        row["error_code"] = exc.code if exc.code in SAFE_ERRORS else "EVALUATION_CLIENT_ERROR"
    except Exception:
        # Deliberately exclude exception messages/tracebacks, which may contain
        # server bodies, authorization headers or other local configuration.
        row["error_code"] = "EVALUATION_CLIENT_ERROR"
    finally:
        row["latency_seconds"] = max(0.0, clock() - started)
    row.update(score_output(case, output, requirement))
    return row


def evaluate_staged_trial(client, case, validator, trial, *, run_id, clock=time.monotonic):
    """Score both calls without erasing a classifier READY on later failure.

    The second stage cannot amend the first decision. Only schema-valid final
    semantic objects are retained; no raw HTTP envelopes or malformed text.
    The existing canonical scoring path remains the authority for acceptance.
    """
    started = clock()
    try:
        result = client.complete_staged(case["input"], axis_convention=case["context"].get("axis_convention"))
    except DomainError as exc:
        result = SimpleNamespace(classification=None, extraction=None,
                                 error_code=exc.code if exc.code in SAFE_ERRORS else "EVALUATION_CLIENT_ERROR")
    except Exception:
        result = SimpleNamespace(classification=None, extraction=None, error_code="EVALUATION_CLIENT_ERROR")
    classification = extraction = None
    classification_json = extraction_json = False
    classification_valid = extraction_valid = False
    decision = None
    if result.classification is not None:
        try:
            classification = strict_json(result.classification.content)
            classification_json = True
        except (ValueError, RecursionError):
            pass
        if type(classification) is dict:
            candidate = classification.get("decision")
            if type(candidate) is str and candidate in ("READY", "CLARIFICATION", "UNSUPPORTED"):
                decision = candidate
        classification_valid = (result.classification.model == client.model and classification_json and
            Draft202012Validator(client.classification_schema).is_valid(classification))
    if result.extraction is not None:
        try:
            extraction = strict_json(result.extraction.content)
            extraction_json = True
        except (ValueError, RecursionError):
            pass
        if classification_valid:
            extraction_valid = (result.extraction.model == client.model and extraction_json and
                Draft202012Validator(client.schema_for_decision(decision)).is_valid(extraction))

    class BufferedExtraction:
        model = client.model
        generation_contract = GenerationContract.QUOTES

        def complete(self, source_text, *, axis_convention=None):
            if result.error_code is not None:
                raise DomainError(result.error_code, "Staged requirement call failed")
            if not classification_valid or not extraction_valid or result.extraction is None:
                raise DomainError("INVALID_MODEL_OUTPUT", "Invalid stage output")
            return result.extraction

    row = evaluate_trial(BufferedExtraction(), case, validator, trial, run_id=run_id, clock=clock)
    row.update(
        pipeline="staged_v1",
        classification_output=classification if classification_valid else None,
        extraction_output=extraction if extraction_json and validator.is_valid(extraction) else None,
        classification_json_valid=classification_json,
        classification_schema_valid=classification_valid,
        extraction_json_valid=extraction_json,
        extraction_schema_valid=extraction_valid,
        extraction_response_observed=result.extraction is not None,
        json_parse_valid=classification_json and extraction_json,
        schema_valid=classification_valid and extraction_valid,
        generation_schema_valid=extraction_json and validator.is_valid(extraction),
        raw_model_decision=decision,
        model_ready_observed=None if decision is None else decision == "READY",
        stage_usage={name: completion.usage if completion is not None else None
                     for name, completion in (("classification", result.classification), ("extraction", result.extraction))},
        stage_transport_latency_seconds={name: completion.latency_seconds if completion is not None else None
                     for name, completion in (("classification", result.classification), ("extraction", result.extraction))},
        latency_seconds=max(0.0, clock() - started),
    )
    completions = [c for c in (result.classification, result.extraction) if c is not None]
    row["response_model"] = completions[-1].model if completions else None
    # Summation is complete only when both responses reached the transport boundary.
    row["transport_latency_seconds"] = (sum(c.latency_seconds for c in completions)
                                        if len(completions) == 2 else None)
    row["usage"] = ({key: sum(c.usage[key] for c in completions)
                     for key in ("prompt_tokens", "completion_tokens", "total_tokens")
                     if all(c.usage is not None and key in c.usage for c in completions)}
                    if len(completions) == 2 else None)
    return row


def rate(numerator, denominator):
    """Wilson 95% interval; exploratory trials are not independent human labels."""
    result = {"numerator": numerator, "denominator": denominator, "rate": None, "wilson_95": None}
    if denominator:
        p, z = numerator / denominator, 1.959963984540054
        scale = 1 + z * z / denominator
        center = (p + z * z / (2 * denominator)) / scale
        half = z * math.sqrt(p * (1 - p) / denominator + z * z / (4 * denominator**2)) / scale
        result.update(rate=p, wilson_95=[max(0.0, center - half), min(1.0, center + half)])
    return result


def latency_summary(rows):
    values = sorted(row["latency_seconds"] for row in rows)
    return {"count": len(values), "mean_seconds": statistics.fmean(values) if values else None,
            "p95_seconds": values[math.ceil(0.95 * len(values)) - 1] if values else None}


def summarize(rows):
    total = len(rows)
    unsafe = [row for row in rows if row["expected_decision"] != "READY"]
    ready = [row for row in rows if row["expected_decision"] == "READY"]
    wrong_ready_moves = [row for row in ready if row["accepted_decision"] == "READY"
                         and not row["semantic_rubric_correct"]]
    result = {key: rate(sum(bool(row[key]) for row in rows), total)
              for key in ("json_parse_valid", "schema_valid", "parser_accepted", "semantic_rubric_correct")}
    if rows and all(row.get("generation_contract") in (GenerationContract.QUOTES.value, GenerationContract.FACTS.value)
                    for row in rows):
        result.update({key: rate(sum(bool(row[key]) for row in rows), total)
                       for key in ("generation_schema_valid", "adapter_accepted", "legacy_schema_valid")})
    if rows and all(row.get("generation_contract") == GenerationContract.FACTS.value for row in rows):
        result["facts_projection_accepted"] = rate(sum(bool(row["facts_projection_accepted"]) for row in rows), total)
    if rows and all(row.get("pipeline") == "staged_v1" for row in rows):
        result.update({key: rate(sum(bool(row[key]) for row in rows), total)
                       for key in ("classification_schema_valid", "extraction_schema_valid")})
    result.update(
        critical_fp_model_ready=rate(sum(row["model_ready_observed"] is True for row in unsafe), len(unsafe)),
        critical_fp_accepted_ready=rate(sum(row["accepted_decision"] == "READY" for row in unsafe), len(unsafe)),
        raw_decision_observed=rate(sum(row["raw_model_decision"] is not None for row in rows), total),
        nonready_gold_raw_decision_observed=rate(sum(row["raw_model_decision"] is not None for row in unsafe), len(unsafe)),
        critical_fn_accepted_ready=rate(sum(row["accepted_decision"] != "READY" for row in ready), len(ready)),
        accepted_incorrect_move_on_ready_gold=rate(len(wrong_ready_moves), len(ready)),
        unsafe_accepted_ready_total=rate(
            sum(row["accepted_decision"] == "READY" for row in unsafe) + len(wrong_ready_moves), total),
        target_preservation=rate(sum(row["target_slots_correct"] for row in rows), sum(row["target_slots_total"] for row in rows)),
        unit_value_extraction=rate(sum(row["unit_value_slots_correct"] for row in rows), sum(row["unit_value_slots_total"] for row in rows)),
        latency_all=latency_summary(rows), latency_parser_accepted=latency_summary([r for r in rows if r["parser_accepted"]]),
        errors=dict(Counter(row["error_code"] for row in rows if row["error_code"])),
        tool_execution="NOT_PERFORMED", decode_tokens_per_second=None, ttft_seconds=None,
    )
    for decision in ("CLARIFICATION", "UNSUPPORTED"):
        tp = sum(row["accepted_decision"] == decision and row["expected_decision"] == decision for row in rows)
        precision = rate(tp, sum(row["accepted_decision"] == decision for row in rows))
        recall = rate(tp, sum(row["expected_decision"] == decision for row in rows))
        p, r = precision["rate"], recall["rate"]
        result[decision.lower() + "_detection"] = {"precision": precision, "recall": recall,
            "f1": None if p is None or r is None else (2 * p * r / (p + r) if p + r else 0.0)}
    token_rows = [row for row in rows if row["usage"] is not None and "completion_tokens" in row["usage"]]
    elapsed = sum(row["latency_seconds"] for row in token_rows)
    result["completion_tokens_per_end_to_end_second"] = (
        sum(row["usage"]["completion_tokens"] for row in token_rows) / elapsed if elapsed else None)
    result["token_timing_trial_count"] = len(token_rows)
    case_consistency = {}
    for case_id in dict.fromkeys(row["case_id"] for row in rows):
        group = [row for row in rows if row["case_id"] == case_id]
        signatures = {json.dumps([row["accepted_decision"],
                                 row["semantic_output"]["target_text"] if row["parser_accepted"] else None,
                                 row["normalized_operation_metres"], row["error_code"]], sort_keys=True) for row in group}
        case_consistency[case_id] = {"trials": len(group), "distinct_semantic_results": len(signatures),
                                    "all_semantic_rubric_correct": all(row["semantic_rubric_correct"] for row in group)}
    result["case_consistency"] = case_consistency
    return result


def run_evaluation(client, cases, schema, *, run_id, warmups=5, trials=3, clock=time.monotonic):
    if type(warmups) is not int or not 0 <= warmups <= 100 or type(trials) is not int or not 1 <= trials <= 100 or not cases:
        raise ValueError("Invalid evaluation protocol")
    validator = Draft202012Validator(schema)
    warmup_rows = [evaluate_trial(client, cases[i % len(cases)], validator, -i - 1, run_id=run_id, clock=clock)
                   for i in range(warmups)]
    # Case-major, then trial-major: the complete fixed order is in the manifest.
    rows = [evaluate_trial(client, case, validator, trial, run_id=run_id, clock=clock)
            for case in cases for trial in range(1, trials + 1)]
    return {"warmups": warmup_rows, "trials": rows, "metrics": summarize(rows)}


def native_runtime_metadata(data):
    """Validate declared native evidence without inventing vLLM dependencies.

    Hashes bind the separately reviewed build/header/launch records. This does
    not remotely attest a live process or replace those records' verification.
    """
    strings = {"compiler", "cmake", "cuda", "driver", "gpu", "quantization"}
    integers = {"physical_gpu", "logical_gpu", "max_model_len", "max_sequences"}
    hashes = {"binary_sha256", "source_provenance_sha256", "build_report_sha256",
              "gguf_sha256", "gguf_header_sha256", "chat_template_sha256",
              "launch_config_sha256", "startup_report_sha256", "listener_report_sha256"}
    required = strings | integers | hashes | {
        "runtime_kind", "profile", "llama_cpp_commit", "cuda_architecture", "gpu_uuid",
        "enable_reasoning", "reasoning_parser",
    }
    if type(data) is not dict or set(data) != required or data["runtime_kind"] != "llama_cpp":
        raise ValueError("Native runtime metadata fields do not match the documented contract")
    if any(type(data[key]) is not str or re.fullmatch(r"[A-Za-z0-9_ .+:/-]{1,128}", data[key]) is None
           for key in strings):
        raise ValueError("Invalid native runtime metadata")
    if any(type(data[key]) is not int for key in integers):
        raise ValueError("Native runtime counts must be exact integers")
    if any(type(data[key]) is not str or re.fullmatch(r"[a-f0-9]{64}", data[key]) is None for key in hashes):
        raise ValueError("Exact native runtime evidence hashes are required")
    if (type(data["llama_cpp_commit"]) is not str
            or re.fullmatch(r"[a-f0-9]{40}", data["llama_cpp_commit"]) is None
            or type(data["gpu_uuid"]) is not str
            or re.fullmatch(r"GPU-[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}", data["gpu_uuid"]) is None):
        raise ValueError("Exact native source commit and GPU UUID are required")
    profiles = {"a100": (3, "80-real"), "rtx5090": (1, "120-real")}
    if (type(data["profile"]) is not str or data["profile"] not in profiles
            or (data["physical_gpu"], data["cuda_architecture"]) != profiles[data["profile"]]
            or data["logical_gpu"] != 0 or data["max_sequences"] != 1
            or data["max_model_len"] != 4096 or data["quantization"] != "Q4_K_M"):
        raise ValueError("Native runtime profile or fixed single GPU configuration mismatch")
    # Parsing a possible reasoning field is distinct from enabling generation
    # of reasoning. This bounded native candidate is explicitly non-thinking.
    if data["enable_reasoning"] is not False or data["reasoning_parser"] != "deepseek":
        raise ValueError("Native non-thinking mode requires the explicit deepseek output splitter")
    return data


def runtime_metadata(path):
    data = strict_json(path.read_text(encoding="utf-8"))
    if type(data) is dict and "runtime_kind" in data:
        return native_runtime_metadata(data)
    strings = {"python", "vllm", "torch", "cuda", "transformers", "xgrammar", "driver", "gpu", "quantization", "dtype"}
    integers = {"physical_gpu", "max_model_len", "tensor_parallel_size"}
    hashes = {"chat_template_sha256", "launch_config_sha256"}
    required = strings | integers | hashes | {"profile"}
    mode_fields = {"enable_reasoning", "reasoning_parser"}
    if type(data) is not dict or set(data) not in (required, required | mode_fields):
        raise ValueError("Runtime metadata fields do not match the documented contract")
    # Historical non-thinking metadata predates these two explicit fields.
    # Omission never authorizes a thinking request to that server.
    data.setdefault("enable_reasoning", False)
    data.setdefault("reasoning_parser", None)
    if (type(data["enable_reasoning"]) is not bool
            or (data["enable_reasoning"] and data["reasoning_parser"] not in ("deepseek_r1", "qwen3"))
            or (not data["enable_reasoning"] and data["reasoning_parser"] is not None)):
        raise ValueError("Explicit supported reasoning mode/parser required")
    if any(type(data[key]) is not str or re.fullmatch(r"[A-Za-z0-9_ .+:/-]{1,128}", data[key]) is None for key in strings):
        raise ValueError("Invalid runtime metadata")
    if data["vllm"].split("+")[0] == "0.8.5" and data["enable_reasoning"] and data["reasoning_parser"] != "deepseek_r1":
        raise ValueError("vLLM 0.8.5 requires the documented deepseek_r1 parser")
    if any(type(data[key]) is not int or data[key] < 0 for key in integers):
        raise ValueError("Invalid runtime counts")
    if any(type(data[key]) is not str or re.fullmatch(r"[a-f0-9]{64}", data[key]) is None for key in hashes):
        raise ValueError("Exact runtime hashes are required")
    if (data["profile"] not in ("a100", "rtx5090") or data["physical_gpu"] != {"a100": 3, "rtx5090": 1}[data["profile"]]
            or data["tensor_parallel_size"] != 1 or data["max_model_len"] < 1):
        raise ValueError("Runtime profile or single GPU configuration mismatch")
    return data


def git_info():
    def read(*args):
        try:
            return subprocess.run(["git", "--no-optional-locks", "-C", str(ROOT), *args],
                                  capture_output=True, text=True, timeout=5, check=True).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return None
    status = read("status", "--porcelain", "--untracked-files=normal")
    return {"commit": read("rev-parse", "HEAD"), "dirty": None if status is None else bool(status)}


def build_manifest(client, *, dataset, prompt, schema, weights, runtime, revision, tokenizer_revision, run_id, warmups, trials,
                   split="development_seed"):
    if split not in {"development_seed", "development", "heldout"}:
        raise ValueError("Unknown dataset split")
    if any(re.fullmatch(r"[a-f0-9]{40}", value) is None for value in (revision, tokenizer_revision)):
        raise ValueError("Pinned model and tokenizer commits are required")
    weight_data = strict_json(weights.read_text(encoding="utf-8"))
    if (type(weight_data) is not dict or weight_data.get("revision") != revision
            or type(weight_data.get("model_id")) is not str
            or re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+", weight_data["model_id"]) is None
            or type(weight_data.get("files")) is not list or not weight_data["files"]):
        raise ValueError("Weight manifest revision mismatch or missing identity")
    names = set()
    for entry in weight_data["files"]:
        if (type(entry) is not dict or type(entry.get("name")) is not str
                or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", entry["name"]) is None
                or entry["name"] in names or type(entry.get("bytes")) is not int or entry["bytes"] <= 0
                or type(entry.get("sha256")) is not str or re.fullmatch(r"[a-f0-9]{64}", entry["sha256"]) is None):
            raise ValueError("Weight files require unique names, sizes and SHA256")
        names.add(entry["name"])
    hashes = {"dataset": file_sha(dataset), "prompt": file_sha(prompt), "schema": file_sha(schema),
              "weight_manifest": file_sha(weights), "runtime_metadata": file_sha(runtime),
              "scorer": file_sha(Path(__file__)),
              "parser": file_sha(ROOT / "src/neurobuild/application/requirements.py"),
              "client": file_sha(ROOT / "src/neurobuild/infrastructure/local_model.py")}
    if client.generation_contract in (GenerationContract.QUOTES, GenerationContract.FACTS):
        hashes.update(generation_adapter=file_sha(ROOT / "src/neurobuild/application/requirement_generation.py"),
                      canonical_schema=file_sha(ROOT / "schemas/semantic_requirement.schema.json"))
    if client.generation_contract is GenerationContract.FACTS:
        hashes.update(facts_adapter=file_sha(ROOT / "src/neurobuild/application/requirement_facts.py"),
                      quote_projection_schema=file_sha(ROOT / "schemas/requirement_generation_v2.schema.json"))
    if hashes["prompt"] != client.prompt_sha256 or hashes["schema"] != client.schema_sha256:
        raise ValueError("Client prompt/schema differs from recorded files")
    sampling = client.sampling_parameters
    runtime_info = runtime_metadata(runtime)
    native = runtime_info.get("runtime_kind") == "llama_cpp"
    native_protocol = client.protocol is StructuredOutputProtocol.LLAMA_CPP_JSON_SCHEMA
    if native != native_protocol:
        raise ValueError("Native runtime metadata and native JSON protocol must be selected together")
    if native:
        if client.sampling_profile is not SamplingProfile.QWEN38_NONTHINKING_LLAMA_CPP:
            raise ValueError("Native evaluation requires the explicitly planned native sampling profile")
        gguf_files = [entry for entry in weight_data["files"] if entry["name"].endswith(".gguf")]
        if (len(gguf_files) != 1 or gguf_files[0]["sha256"] != runtime_info["gguf_sha256"]
                or tokenizer_revision != revision):
            raise ValueError("Native GGUF identity and embedded tokenizer revision must match the weight manifest")
    if runtime_info["enable_reasoning"] != client.enable_thinking:
        raise ValueError("Client thinking mode and declared server reasoning mode must match")
    manifest = {"run_id": run_id, "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "gold_status": GOLD_STATUS, "split": split, "git": git_info(),
            "model_id": weight_data["model_id"], "served_model": client.model,
            "model_revision": revision, "tokenizer_revision": tokenizer_revision,
            "sha256": hashes, "runtime": runtime_info,
            "runtime_identity_evidence": "OPERATOR_SUPPLIED; HTTP model name checked, loaded weight revision not remotely attested",
            "weight_integrity_evidence": "PINNED_MANIFEST; downloader verifies files, evaluator does not reread weights",
            "protocol": {"warmups": warmups, "trials_per_case": trials, "order": "dataset order, case-major then trial-major",
                         "generation_contract": client.generation_contract.value,
                         "sampling_profile": client.sampling_profile.value,
                         "sampling_request_parameters": sampling,
                         "unspecified_sampling_parameters": "Server/model defaults; not claimed explicitly controlled",
                         "temperature": sampling["temperature"], "seed": sampling["seed"],
                         "seed_policy": "Same fixed seed for every request; repetitions are not independent samples",
                         "max_tokens": client.max_tokens, "timeout_seconds": client.timeout,
                         "concurrency": 1, "enable_thinking": client.enable_thinking,
                         "structured_output_protocol": client.protocol.value,
                         "guided_decoding_backend": ("xgrammar:no-fallback" if client.protocol == StructuredOutputProtocol.LEGACY_GUIDED_JSON else None),
                         "required_server_structured_backend": ("xgrammar" if client.protocol == StructuredOutputProtocol.STRUCTURED_OUTPUTS else None),
                         "tool_parser": None, "reasoning_parser": runtime_info["reasoning_parser"]},
            "measurements_not_performed": {"startup_cold_seconds": None, "startup_warm_seconds": None,
                                           "gpu_baseline_used_mib": None, "gpu_peak_used_mib": None, "ttft_seconds": None}}
    if client.generation_contract is GenerationContract.FACTS:
        manifest["protocol"].update(
            pipeline="single", maximum_calls_per_case=1,
            projection_chain=["3.0", "2.0", "1.0"],
            facts_validation="Exact source quotes and declared-fact consistency; no semantic entailment proof or decision correction",
            raw_ready_metric="Root model decision observed before generation schema, facts projection and all downstream validation",
        )
    if native:
        manifest["runtime_identity_evidence"] = (
            "OPERATOR_SUPPLIED_NATIVE_EVIDENCE_HASHES; build/shared-library, GGUF/header, template and "
            "launch/listener records require separate verification; HTTP model name is not remote attestation")
        manifest["protocol"].update(
            required_server_structured_backend="llama_cpp_gbnf",
            response_format_type="json_schema",
            reasoning_disposition="Separate reasoning field discarded; only final content is evaluated",
        )
    if getattr(client, "pipeline", None) == "staged_v1":
        manifest["sha256"].update(
            staged_client=file_sha(ROOT / "src/neurobuild/infrastructure/staged_requirement.py"),
            classification_prompt=client.classification_prompt_sha256,
            classification_schema=client.classification_schema_sha256,
        )
        manifest["protocol"].update(
            pipeline="staged_v1", maximum_calls_per_case=2,
            call_policy="Two sequential calls after a valid classification, including non-READY target/reason extraction; classifier failure stops after the first call",
            classification_max_tokens=client.classification_max_tokens,
            extraction_max_tokens=client.max_tokens,
            timeout_scope="per stage; end-to-end may reach twice the stage timeout",
            decision_binding="Classifier decision binds extraction schema; no retry, repair or vote",
            effective_extraction_schema_sha256=client.effective_schema_sha256,
            raw_ready_metric="Classifier decision observed before schema validation and all downstream failures",
        )
    return manifest


def save_json(path, value):
    # A unique run directory and exclusive files prevent overwriting old runs.
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8003")
    parser.add_argument("--protocol", choices=[p.value for p in StructuredOutputProtocol], default="legacy_guided_json")
    parser.add_argument("--sampling-profile", choices=[p.value for p in SamplingProfile], default="legacy_greedy")
    parser.add_argument("--generation-contract", choices=[c.value for c in GenerationContract], default="1.0")
    parser.add_argument("--pipeline", choices=["single", "staged_v1"], default="single")
    parser.add_argument("--classification-prompt", type=Path)
    parser.add_argument("--classification-schema", type=Path)
    parser.add_argument("--model", required=True, help="Exact served model name")
    parser.add_argument("--model-revision", required=True)
    parser.add_argument("--tokenizer-revision")
    parser.add_argument("--weight-manifest", type=Path, required=True)
    parser.add_argument("--runtime-metadata", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, default=ROOT / "evaluations/requirement_seed.jsonl")
    parser.add_argument("--split", choices=["development_seed", "development", "heldout"], default="development_seed")
    parser.add_argument("--prompt", type=Path)
    parser.add_argument("--schema", type=Path)
    parser.add_argument("--max-tokens", type=int, default=768)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--warmups", type=int, default=5)
    parser.add_argument("--trials", type=int, default=3)
    args = parser.parse_args(argv)
    try:
        contract = GenerationContract(args.generation_contract)
        if args.pipeline == "staged_v1" and contract is not GenerationContract.QUOTES:
            raise ValueError("Staged extraction requires the explicit 2.0 quote contract")
        if args.pipeline == "single" and (args.classification_prompt or args.classification_schema):
            raise ValueError("Classification paths require the staged pipeline")
        if args.pipeline == "staged_v1":
            args.prompt = args.prompt or ROOT / "prompts/requirement_extraction_v1.txt"
            args.schema = args.schema or ROOT / "schemas/requirement_generation_v2_decision_branches.schema.json"
        defaults = {
            GenerationContract.LEGACY: ("prompts/requirement_v3.txt", "schemas/semantic_requirement.schema.json"),
            GenerationContract.QUOTES: ("prompts/requirement_generation_v2_v1.txt", "schemas/requirement_generation_v2.schema.json"),
            GenerationContract.FACTS: ("prompts/requirement_generation_v3_v1.txt", "schemas/requirement_generation_v3.schema.json"),
        }
        args.prompt = args.prompt or ROOT / defaults[contract][0]
        args.schema = args.schema or ROOT / defaults[contract][1]
        cases = load_cases(args.dataset)
        schema = strict_json(args.schema.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        kwargs = dict(timeout=args.timeout, max_tokens=args.max_tokens,
                      prompt_path=args.prompt, schema_path=args.schema, protocol=args.protocol,
                      sampling_profile=args.sampling_profile)
        if args.pipeline == "staged_v1":
            from neurobuild.infrastructure.staged_requirement import LocalStagedRequirementClient
            client = LocalStagedRequirementClient(args.base_url, args.model, **kwargs,
                classification_prompt_path=args.classification_prompt,
                classification_schema_path=args.classification_schema)
        else:
            client = LocalRequirementClient(args.base_url, args.model, **kwargs, generation_contract=contract)
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex
        manifest = build_manifest(client, dataset=args.dataset, prompt=args.prompt, schema=args.schema,
                                  weights=args.weight_manifest, runtime=args.runtime_metadata,
                                  revision=args.model_revision, tokenizer_revision=args.tokenizer_revision or args.model_revision,
                                  run_id=run_id, warmups=args.warmups, trials=args.trials, split=args.split)
        manifest["case_order"] = [case["id"] for case in cases]
        destination = ROOT / "var/runs" / run_id
        if not destination.resolve().is_relative_to(ROOT / "var/runs"):
            raise ValueError("Run storage must remain inside this project")
        destination.mkdir(parents=True, exist_ok=False)
        save_json(destination / "manifest.json", manifest)
        save_json(destination / "dataset.json", {"gold_status": GOLD_STATUS, "cases": cases})
        result = run_evaluation(client, cases, schema, run_id=run_id, warmups=args.warmups, trials=args.trials)
        result.update(gold_status=GOLD_STATUS, run_id=run_id,
                      interpretation="Automatic decision/target/SI rubric; no human meaning review, IFC execution or approval",
                      raw_ready_limit="Unparseable/truncated/absent decisions are unobserved; raw READY rate is an observed lower bound",
                      interval_limit="Wilson intervals are descriptive; repeated trials and public synthetic cases are correlated")
        save_json(destination / "results.json", result)
        print(json.dumps({"run_id": run_id, "results": str(destination / "results.json"),
                          "trials": len(result["trials"]), "gold_status": GOLD_STATUS}, ensure_ascii=False))
        return 0
    except Exception:
        print(json.dumps({"error_code": "EVALUATION_SETUP_OR_STORAGE_FAILED"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
