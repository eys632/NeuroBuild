#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

LIVE_DIR = Path(
    os.environ.get(
        "NB_LIVE_DIR",
        str(Path(__file__).resolve().parents[1] / "results" / "live"),
    )
)

_STATUS: dict[str, Any] = {}
_RUN_START: float | None = None


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_live_dir() -> None:
    LIVE_DIR.mkdir(parents=True, exist_ok=True)


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    _atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2))


def _append_event(event: dict[str, Any]) -> None:
    _ensure_live_dir()
    path = LIVE_DIR / "events.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def _get_gpu_info(device: str | None) -> tuple[str | None, int | None, int | None]:
    try:
        import torch

        if not device:
            return None, None, None
        if not device.startswith("cuda"):
            return None, None, None
        if not torch.cuda.is_available():
            return None, None, None
        idx = torch.cuda.current_device()
        name = torch.cuda.get_device_name(idx)
        alloc = int(torch.cuda.memory_allocated(idx) / (1024 * 1024))
        reserved = int(torch.cuda.memory_reserved(idx) / (1024 * 1024))
        return name, alloc, reserved
    except Exception:
        return None, None, None


def _format_progress_text(status: dict[str, Any]) -> str:
    lines: list[str] = []
    run_type = status.get("run_type")
    lines.append(f"run_type: {run_type}")
    lines.append(f"stage: {status.get('stage')}")
    if status.get("progress_pct") is not None:
        lines.append(f"progress_pct: {status.get('progress_pct')}")

    if run_type == "train":
        lines.append(f"epoch: {status.get('epoch')}/{status.get('num_train_epochs')}")
        lines.append(f"step: {status.get('global_step')}/{status.get('max_steps')}")
        lines.append(f"loss: {status.get('loss')}")
        lines.append(f"elapsed_sec: {status.get('elapsed_sec')}")
        lines.append(f"eta_sec: {status.get('eta_sec')}")
        lines.append(f"device: {status.get('device')}")
        lines.append(f"gpu_name: {status.get('gpu_name')}")
        lines.append(f"gpu_mem_allocated_mb: {status.get('gpu_mem_allocated_mb')}")
        lines.append(f"gpu_mem_reserved_mb: {status.get('gpu_mem_reserved_mb')}")
    elif run_type == "eval":
        lines.append(f"current_example_idx: {status.get('current_example_idx')}")
        lines.append(f"total_examples: {status.get('total_examples')}")
        lines.append(f"parse_success_count: {status.get('parse_success_count')}")
        lines.append(f"schema_valid_count: {status.get('schema_valid_count')}")
        lines.append(f"op_exact_match_count: {status.get('op_exact_match_count')}")
        lines.append(f"slot_accuracy_running_avg: {status.get('slot_accuracy_running_avg')}")
        lines.append(f"elapsed_sec: {status.get('elapsed_sec')}")
        lines.append(f"eta_sec: {status.get('eta_sec')}")

    if status.get("error_message"):
        lines.append(f"error: {status.get('error_message')}")

    lines.append(f"timestamp: {status.get('timestamp')}")
    return "\n".join(lines) + "\n"


def _update_status(fields: dict[str, Any]) -> None:
    global _STATUS
    _ensure_live_dir()
    _STATUS.update(fields)
    _STATUS["timestamp"] = _now_iso()

    device = _STATUS.get("device")
    gpu_name, alloc_mb, reserved_mb = _get_gpu_info(device)
    if gpu_name:
        _STATUS["gpu_name"] = gpu_name
        _STATUS["gpu_mem_allocated_mb"] = alloc_mb
        _STATUS["gpu_mem_reserved_mb"] = reserved_mb

    _write_json(LIVE_DIR / "current_status.json", _STATUS)
    _atomic_write(LIVE_DIR / "progress.txt", _format_progress_text(_STATUS))


def start_run(*, run_type: str, stage: str, **fields: Any) -> None:
    global _RUN_START, _STATUS
    _RUN_START = time.time()
    _STATUS = {
        "run_type": run_type,
        "stage": stage,
    }
    _STATUS.update(fields)
    _STATUS["elapsed_sec"] = 0
    _STATUS["eta_sec"] = None
    _STATUS["progress_pct"] = 0.0
    _update_status({})
    log_event("start", message=f"run_type={run_type}", data={"stage": stage})


def update_stage(stage: str, **fields: Any) -> None:
    _update_status({"stage": stage, **fields})
    log_event("stage", message=stage)


def _compute_eta(progress_pct: float, elapsed: float) -> float | None:
    if progress_pct <= 0:
        return None
    frac = progress_pct / 100.0
    if frac <= 0:
        return None
    return max(0.0, elapsed * (1.0 / frac - 1.0))


def update_train(
    *,
    model_id: str | None,
    adapter_output_dir: str | None,
    device: str | None,
    epoch: float | None,
    num_train_epochs: float | None,
    global_step: int | None,
    max_steps: int | None,
    loss: float | None,
) -> None:
    elapsed = time.time() - _RUN_START if _RUN_START else 0.0
    progress_pct = None
    if global_step is not None and max_steps:
        progress_pct = round((global_step / max_steps) * 100.0, 2)
    eta = _compute_eta(progress_pct or 0.0, elapsed)

    _update_status(
        {
            "run_type": "train",
            "stage": "training",
            "model_id": model_id,
            "adapter_output_dir": adapter_output_dir,
            "device": device,
            "epoch": epoch,
            "num_train_epochs": num_train_epochs,
            "global_step": global_step,
            "max_steps": max_steps,
            "progress_pct": progress_pct,
            "loss": loss,
            "elapsed_sec": round(elapsed, 2),
            "eta_sec": round(eta, 2) if eta is not None else None,
        }
    )


def update_eval(
    *,
    model_id_or_path: str | None,
    adapter_path: str | None,
    dataset_path: str | None,
    current_example_idx: int,
    total_examples: int,
    parse_success_count: int,
    schema_valid_count: int,
    op_exact_match_count: int,
    slot_accuracy_running_avg: float,
) -> None:
    elapsed = time.time() - _RUN_START if _RUN_START else 0.0
    progress_pct = round((current_example_idx / max(1, total_examples)) * 100.0, 2)
    eta = _compute_eta(progress_pct, elapsed)

    _update_status(
        {
            "run_type": "eval",
            "stage": "evaluating",
            "model_id_or_path": model_id_or_path,
            "adapter_path": adapter_path,
            "dataset_path": dataset_path,
            "current_example_idx": current_example_idx,
            "total_examples": total_examples,
            "progress_pct": progress_pct,
            "parse_success_count": parse_success_count,
            "schema_valid_count": schema_valid_count,
            "op_exact_match_count": op_exact_match_count,
            "slot_accuracy_running_avg": round(slot_accuracy_running_avg, 4),
            "elapsed_sec": round(elapsed, 2),
            "eta_sec": round(eta, 2) if eta is not None else None,
        }
    )


def log_event(event_type: str, message: str | None = None, data: dict[str, Any] | None = None) -> None:
    payload = {
        "timestamp": _now_iso(),
        "event": event_type,
    }
    if message:
        payload["message"] = message
    if data:
        payload["data"] = data
    _append_event(payload)


def finish_run(**fields: Any) -> None:
    _update_status({"stage": "done", "progress_pct": 100.0, **fields})
    log_event("done")


def fail_run(error_message: str, **fields: Any) -> None:
    _update_status({"stage": "failed", "error_message": error_message, **fields})
    log_event("failed", message=error_message)
