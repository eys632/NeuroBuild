#!/usr/bin/env python3
"""Read only the permitted GPU and assess an estimated runtime memory budget."""

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import math
import os
import re
import subprocess
import time


PROFILE_GPU = {"a100": 3, "rtx5090": 1}


class PreflightError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def _require(condition, code, message):
    if not condition:
        raise PreflightError(code, message)


@dataclass(frozen=True)
class Reading:
    total_mib: int
    free_mib: int
    used_mib: int
    utilization_percent: int

    def __post_init__(self):
        values = (self.total_mib, self.free_mib, self.used_mib, self.utilization_percent)
        _require(all(type(value) is int for value in values), "INVALID_READING", "GPU readings must be integer quantities")
        _require(self.total_mib > 0 and 0 <= self.free_mib <= self.total_mib
                 and 0 <= self.used_mib <= self.total_mib and 0 <= self.utilization_percent <= 100
                 and self.free_mib + self.used_mib <= self.total_mib + 2,
                 "INVALID_READING", "GPU readings are outside a consistent physical range")


@dataclass(frozen=True)
class Policy:
    profile: str
    estimated_peak_mib: int
    samples: int = 5
    interval_seconds: float = 1.0
    safety_margin_mib: int = 6144
    safety_margin_fraction: float = 0.20
    max_utilization_percent: int = 10
    max_free_change_mib: int = 256

    def __post_init__(self):
        _require(self.profile in PROFILE_GPU, "INVALID_PROFILE", "Choose the server's explicit a100 or rtx5090 profile")
        _require(type(self.estimated_peak_mib) is int and self.estimated_peak_mib > 0,
                 "INVALID_POLICY", "Estimated startup/inference peak must be a positive MiB integer")
        _require(type(self.samples) is int and 3 <= self.samples <= 20,
                 "INVALID_POLICY", "Use between three and twenty samples")
        _require(type(self.interval_seconds) in (int, float) and math.isfinite(self.interval_seconds)
                 and 0.1 <= self.interval_seconds <= 5 and (self.samples - 1) * self.interval_seconds <= 30,
                 "INVALID_POLICY", "Sampling intervals must be 0.1–5 seconds within a 30-second window")
        _require(type(self.safety_margin_mib) is int and self.safety_margin_mib >= 6144,
                 "INVALID_POLICY", "The fixed safety margin must be at least 6144 MiB")
        _require(type(self.safety_margin_fraction) in (int, float) and math.isfinite(self.safety_margin_fraction)
                 and 0.20 <= self.safety_margin_fraction < 1,
                 "INVALID_POLICY", "The free-memory safety fraction must be at least 0.20 and below 1")
        _require(type(self.max_utilization_percent) is int and 0 <= self.max_utilization_percent <= 25,
                 "INVALID_POLICY", "Maximum utilization must be between 0 and 25 percent")
        _require(type(self.max_free_change_mib) is int and 0 <= self.max_free_change_mib <= 1024,
                 "INVALID_POLICY", "Maximum free-memory swing must be between 0 and 1024 MiB")


def parse_reading(output):
    """Reject N/A, multiple devices, units, partial rows and malformed quantities."""
    _require(isinstance(output, str), "INVALID_READING", "Expected one GPU CSV reading")
    rows = output.strip().splitlines()
    _require(len(rows) == 1, "INVALID_READING", "Exactly one permitted GPU must be reported")
    fields = [field.strip() for field in rows[0].split(",")]
    _require(len(fields) == 4 and all(re.fullmatch(r"[0-9]{1,9}", field) for field in fields),
             "INVALID_READING", "GPU memory/utilization must be known numeric readings")
    return Reading(*(int(field) for field in fields))


def _query_gpu(physical_index):
    _require(type(physical_index) is int and physical_index in PROFILE_GPU.values(),
             "INVALID_PROFILE", "Only a profile's permitted GPU can be queried")
    command = [
        "nvidia-smi", "-i", str(physical_index),
        "--query-gpu=memory.total,memory.free,memory.used,utilization.gpu",
        "--format=csv,noheader,nounits",
    ]
    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        raise PreflightError("GPU_QUERY_FAILED", "The permitted GPU could not be measured") from None
    return result.stdout


def evaluate_budget(readings, policy):
    """Pure calculation; process presence is not a blocking condition."""
    _require(type(policy) is Policy and len(readings) == policy.samples
             and all(type(reading) is Reading for reading in readings),
             "INVALID_READING", "A complete sampling window is required")
    totals = {reading.total_mib for reading in readings}
    _require(len(totals) == 1, "UNSTABLE_TOTAL_MEMORY", "GPU total memory changed during sampling")
    total = readings[0].total_mib
    minimum = min(reading.free_mib for reading in readings)
    swing = max(reading.free_mib for reading in readings) - minimum
    utilization = max(reading.utilization_percent for reading in readings)
    margin = max(policy.safety_margin_mib, math.ceil(minimum * policy.safety_margin_fraction))
    budget = max(0, minimum - margin)
    reasons = []
    if utilization > policy.max_utilization_percent:
        reasons.append("GPU_UTILIZATION_HIGH")
    if swing > policy.max_free_change_mib:
        reasons.append("FREE_MEMORY_UNSTABLE")
    if policy.estimated_peak_mib > budget:
        reasons.append("INSUFFICIENT_MEMORY_BUDGET")
    allowed = not reasons
    return {
        "allowed": allowed,
        "decision": "BUDGET_FITS_ESTIMATE" if allowed else "BLOCKED",
        "reason_codes": reasons,
        "measured": {
            "total_mib": total,
            "minimum_free_mib": minimum,
            "maximum_used_mib": max(reading.used_mib for reading in readings),
            "maximum_utilization_percent": utilization,
            "free_memory_swing_mib": swing,
            "sample_count": len(readings),
        },
        "budget": {
            "estimated_startup_or_inference_peak_mib": policy.estimated_peak_mib,
            "estimate_must_include": ["weights", "KV_cache", "workspace", "CUDA_context", "allocator_overhead"],
            "required_safety_margin_mib": margin,
            "available_model_budget_mib": budget,
            "unallocated_budget_after_estimated_peak_mib": budget - policy.estimated_peak_mib,
            "estimate_is_measured_peak": False,
        },
        "required_launch_limit": {
            "maximum_total_runtime_peak_mib": budget if allowed else None,
            "maximum_fraction_of_total_vram": math.floor(budget / total * 1_000_000) / 1_000_000 if allowed else None,
            "tensor_parallel_size": 1,
            "process_device": "cuda:0",
            "recheck_immediately_before_launch": True,
            "runtime_must_enforce_its_own_memory_settings": True,
            "hard_gpu_isolation": False,
        },
    }


def run_preflight(policy, *, environ=None, query=None, sleep=None):
    """Collect only allowed-device aggregate readings; injected functions aid tests."""
    environ = os.environ if environ is None else environ
    query = _query_gpu if query is None else query
    sleep = time.sleep if sleep is None else sleep
    physical_index = PROFILE_GPU[policy.profile]
    report = {
        "schema_version": 1,
        "profile": policy.profile,
        "physical_gpu_index": physical_index,
        "required_cuda_visible_devices": str(physical_index),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "policy": asdict(policy),
        "samples": [],
        "runtime_validation": "NOT_TESTED",
        "memory_fit_guaranteed": False,
        "notice": "Read-only measurement and estimate; no reservation, runtime launch, process query or termination.",
    }
    try:
        _require(environ.get("CUDA_VISIBLE_DEVICES") == str(physical_index),
                 "CUDA_MASK_MISMATCH", "Set CUDA_VISIBLE_DEVICES to exactly the chosen profile's permitted GPU")
        readings = []
        for index in range(policy.samples):
            reading = parse_reading(query(physical_index))
            readings.append(reading)
            report["samples"].append(asdict(reading))
            if index + 1 < policy.samples:
                sleep(policy.interval_seconds)
        report.update(evaluate_budget(readings, policy))
    except PreflightError as error:
        report.update(allowed=False, decision="BLOCKED", reason_codes=[error.code], error=str(error))
    report["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, choices=tuple(PROFILE_GPU))
    parser.add_argument("--estimated-peak-mib", required=True, type=int,
                        help="Estimated max(startup, inference) peak including weights, KV, workspace and overhead")
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--interval-seconds", type=float, default=1.0)
    parser.add_argument("--safety-margin-mib", type=int, default=6144)
    parser.add_argument("--safety-margin-fraction", type=float, default=0.20)
    parser.add_argument("--max-utilization-percent", type=int, default=10)
    parser.add_argument("--max-free-change-mib", type=int, default=256)
    args = parser.parse_args(argv)
    try:
        policy = Policy(**vars(args))
        report = run_preflight(policy)
    except PreflightError as error:
        report = {"schema_version": 1, "allowed": False, "decision": "BLOCKED",
                  "reason_codes": [error.code], "error": str(error), "memory_fit_guaranteed": False}
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report["allowed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
