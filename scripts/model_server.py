#!/usr/bin/env python3
"""Run the local model server with a permitted-GPU budget and own-child watchdog."""

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import json
import math
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import tempfile
import threading
import time

try:
    from .gpu_preflight import Policy, PreflightError, _query_gpu, parse_reading, run_preflight
except ImportError:  # direct script execution, including from outside the checkout
    from gpu_preflight import Policy, PreflightError, _query_gpu, parse_reading, run_preflight


ROOT = Path(__file__).resolve().parents[1]
POLL_SECONDS = 0.5
PARENT_DEATH_BOOTSTRAP = """import ctypes, os, signal, sys
expected_parent = int(sys.argv.pop(1))
if os.getppid() != expected_parent:
    raise SystemExit('WATCHDOG_PARENT_CHANGED')
if ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGKILL, 0, 0, 0) != 0:
    raise SystemExit('WATCHDOG_DEATH_SIGNAL_FAILED')
if os.getppid() != expected_parent:
    os.kill(os.getpid(), signal.SIGKILL)
"""
# V0 + uni + disabled frontend multiprocessing keep the engine in this process.
# The cap covers PyTorch allocator allocations, not every CUDA/native allocation.
CHILD_BOOTSTRAP = PARENT_DEATH_BOOTSTRAP + """import json, runpy, subprocess, sys
cap = sys.argv.pop(1)
rendezvous_file = sys.argv.pop(1)
import torch
expected = subprocess.run(['nvidia-smi', '-i', '3', '--query-gpu=uuid', '--format=csv,noheader,nounits'],
                          check=True, capture_output=True, text=True, timeout=5).stdout.strip()
if '\\n' in expected or not expected.startswith('GPU-') or torch.cuda.device_count() != 1:
    raise SystemExit('GPU_IDENTITY_MISMATCH')
actual = str(torch.cuda.get_device_properties(0).uuid)
if actual.lower().removeprefix('gpu-') != expected.lower().removeprefix('gpu-'):
    raise SystemExit('GPU_IDENTITY_MISMATCH')
print(json.dumps({'event': 'GPU_IDENTITY_VERIFIED', 'physical_gpu_index': 3, 'logical_device': 0}), flush=True)
if cap != 'none':
    torch.cuda.set_device(0)
    torch.cuda.set_per_process_memory_fraction(float(cap), 0)
from datetime import timedelta
if torch.distributed.is_initialized():
    raise SystemExit('UNEXPECTED_DISTRIBUTED_GROUP')
store = torch.distributed.FileStore(rendezvous_file, 1)
torch.distributed.init_process_group(backend='nccl', store=store, rank=0, world_size=1,
                                     timeout=timedelta(seconds=30))
if torch.distributed.get_rank() != 0 or torch.distributed.get_world_size() != 1:
    raise SystemExit('DISTRIBUTED_GROUP_MISMATCH')
print(json.dumps({'event': 'LOCAL_FILE_RENDEZVOUS_READY', 'world_size': 1}), flush=True)
sys.argv[0] = 'vllm.entrypoints.openai.api_server'
runpy.run_module('vllm.entrypoints.openai.api_server', run_name='__main__')
"""


try:
    from .model_guard import (require, local_path, runtime_output_path, acquire_project_lock,
                              write_report, peek_child_exit, stop_owned_child, run_lifecycle)
except ImportError:
    from model_guard import (require, local_path, runtime_output_path, acquire_project_lock,
                             write_report, peek_child_exit, stop_owned_child, run_lifecycle)

@dataclass(frozen=True)
class LaunchConfig:
    profile: str
    model_path: Path
    dtype: str
    estimated_peak_mib: int
    log_file: Path
    report_file: Path
    port: int = 8003
    max_seconds: float = 1800
    max_model_len: int = 4096
    gpu_memory_utilization: float = 0.50
    torch_memory_fraction: float | None = 0.50
    peak_allowance_mib: int = 1024
    served_model_name: str = "neurobuild-local"
    enable_reasoning: bool = False

    def __post_init__(self):
        Policy(self.profile, self.estimated_peak_mib)
        require(type(self.enable_reasoning) is bool, "INVALID_CONFIG", "Reasoning mode must be an explicit boolean")
        require(self.dtype in ("half", "bfloat16"), "INVALID_CONFIG", "Choose explicit half or bfloat16 precision")
        require(type(self.port) is int and 1024 <= self.port <= 65535,
                "INVALID_CONFIG", "Use an unprivileged localhost port")
        require(type(self.max_seconds) in (int, float) and math.isfinite(self.max_seconds)
                and 1 <= self.max_seconds <= 43200, "INVALID_CONFIG", "Execution must be bounded to 1–43200 seconds")
        require(type(self.max_model_len) is int and 256 <= self.max_model_len <= 4096,
                "INVALID_CONFIG", "Initial context must be between 256 and 4096 tokens")
        for fraction in (self.gpu_memory_utilization, self.torch_memory_fraction):
            require(fraction is None or (type(fraction) in (int, float) and math.isfinite(fraction)
                    and 0 < fraction < 1), "INVALID_CONFIG", "Memory fractions must be above zero and below one")
        require(self.gpu_memory_utilization is not None, "INVALID_CONFIG", "Runtime memory utilization is required")
        require(type(self.peak_allowance_mib) is int and 0 <= self.peak_allowance_mib <= 1024,
                "INVALID_CONFIG", "Peak allowance must be between zero and 1024 MiB")
        require(isinstance(self.served_model_name, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}", self.served_model_name),
                "INVALID_CONFIG", "Use a short explicit model alias without paths or whitespace")


def launch_command(config, root=ROOT, *, rendezvous_file):
    """Construct pinned vLLM 0.8.5 arguments without a shell or implicit download."""
    command = [str(root / ".conda-vllm/bin/python"), "-c", CHILD_BOOTSTRAP,
            str(os.getpid()),
            "none" if config.torch_memory_fraction is None else str(config.torch_memory_fraction),
            str(local_path(rendezvous_file, root, output=True)),
            "--model", str(local_path(config.model_path, root)),
            "--served-model-name", config.served_model_name, "--host", "127.0.0.1", "--port", str(config.port),
            "--tensor-parallel-size", "1", "--distributed-executor-backend", "uni",
            "--disable-frontend-multiprocessing", "--enforce-eager", "--dtype", config.dtype,
            "--max-model-len", str(config.max_model_len), "--max-num-seqs", "1",
            "--max-num-batched-tokens", str(config.max_model_len), "--block-size", "16",
            "--num-gpu-blocks-override", str(math.ceil(config.max_model_len / 16)),
            "--gpu-memory-utilization", str(config.gpu_memory_utilization), "--swap-space", "0",
            "--no-enable-prefix-caching", "--guided-decoding-backend", "xgrammar",
            "--disable-log-requests", "--disable-uvicorn-access-log"]
    if config.enable_reasoning:
        command.extend(["--enable-reasoning", "--reasoning-parser", "deepseek_r1"])
    return command


def child_environment(config, root, environ):
    child = dict(environ)
    child.pop("PYTHONHOME", None)
    child.pop("PYTHONPATH", None)
    for variable in ("MASTER_ADDR", "MASTER_PORT", "RANK", "LOCAL_RANK", "WORLD_SIZE"):
        child.pop(variable, None)
    child.update(CUDA_VISIBLE_DEVICES="3", CUDA_DEVICE_ORDER="PCI_BUS_ID", VLLM_USE_V1="0", VLLM_ATTENTION_BACKEND="FLASH_ATTN",
                 VLLM_FLASH_ATTN_VERSION="2", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                 DO_NOT_TRACK="1", VLLM_NO_USAGE_STATS="1", TOKENIZERS_PARALLELISM="false",
                 GLOO_SOCKET_IFNAME="lo", NCCL_SOCKET_IFNAME="=lo", NCCL_IB_DISABLE="1",
                 VLLM_HOST_IP="127.0.0.1", PYTHONNOUSERSITE="1",
                 VLLM_DP_SIZE="1", VLLM_DP_RANK="0", VLLM_DP_RANK_LOCAL="0",
                 VLLM_DP_MASTER_IP="127.0.0.1", VLLM_DP_MASTER_PORT="0",
                 TORCH_NCCL_AVOID_RECORD_STREAMS="1",
                 CONDA_PREFIX=str(root / ".conda-vllm"))
    child["PATH"] = str(root / ".conda-vllm/bin") + os.pathsep + child.get("PATH", "")
    for variable, directory in {"HF_HOME": "huggingface", "TORCH_HOME": "torch",
                                "TRITON_CACHE_DIR": "triton", "CUDA_CACHE_PATH": "cuda",
                                "VLLM_CACHE_ROOT": "vllm", "XDG_CACHE_HOME": "xdg", "TMPDIR": "tmp"}.items():
        path = local_path(root / "var/cache" / directory, root, output=True)
        path.mkdir(parents=True, exist_ok=True)
        child[variable] = str(path)
    return child


class _VllmRuntime:
    def __init__(self):
        self.rendezvous_dir = None

    def initial_fields(self, config):
        return {"enable_reasoning": config.enable_reasoning,
                "reasoning_parser": "deepseek_r1" if config.enable_reasoning else None}

    def validate(self, config, root, model):
        require(model.is_dir() and (model / "config.json").is_file(),
                "MODEL_NOT_LOCAL", "A downloaded local model directory with config.json is required")
        runtime = root / ".conda-vllm/bin/python"
        require(runtime.is_file() and runtime.resolve().is_relative_to((root / ".conda-vllm").resolve()),
                "RUNTIME_NOT_LOCAL", "The project .conda-vllm Python is required")

    def environment(self, config, root, environ):
        return child_environment(config, root, environ)

    def fields(self, config):
        return {"dtype": config.dtype, "torch_allocator_fraction": config.torch_memory_fraction,
                "gpu_memory_utilization": config.gpu_memory_utilization}

    def check_budget(self, config, total, budget):
        fractions = (config.gpu_memory_utilization, config.torch_memory_fraction)
        require(all(fraction is None or math.ceil(fraction * total) <= budget for fraction in fractions),
                "ALLOCATION_CAP_EXCEEDS_BUDGET", "Reduce configured runtime/allocator fractions to the measured model budget")

    def prepare(self, config, root, report):
        rendezvous_root = local_path(root / "var/run/rendezvous", root, output=True)
        rendezvous_root.mkdir(parents=True, exist_ok=True)
        self.rendezvous_dir = Path(tempfile.mkdtemp(prefix="model-", dir=rendezvous_root))
        rendezvous_file = self.rendezvous_dir / "store"
        report.update(rendezvous={"kind": "FILE_STORE", "path": str(rendezvous_file), "world_size": 1,
                                  "gloo_interface": "lo", "nccl_interface": "=lo", "cleaned": False})
        return launch_command(config, root, rendezvous_file=rendezvous_file)

    def output_options(self, log):
        return {"stdout": log, "stderr": subprocess.STDOUT}

    def after_spawn(self, child):
        pass

    def observe(self, child, report):
        pass

    def cleanup(self, report, safe_to_release):
        if self.rendezvous_dir is not None and safe_to_release:
            try:
                (self.rendezvous_dir / "store").unlink(missing_ok=True)
                self.rendezvous_dir.rmdir()
                report["rendezvous"]["cleaned"] = True
            except OSError:
                report["rendezvous"]["cleanup_error"] = "RENDEZVOUS_CLEANUP_FAILED"


def run_guard(config, *, root=ROOT, environ=None, query=None, popen=None, killpg=None,
              sleep=None, monotonic=None, stop_requested=None, peek_exit=None):
    """Preserve the vLLM public API and its injection points."""
    return run_lifecycle(config, _VllmRuntime(), root=root, environ=environ,
                         query=_query_gpu if query is None else query,
                         popen=subprocess.Popen if popen is None else popen,
                         killpg=os.killpg if killpg is None else killpg,
                         sleep=sleep, monotonic=monotonic, stop_requested=stop_requested,
                         peek_exit=peek_exit, report_writer=write_report)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, choices=("a100", "rtx5090"))
    parser.add_argument("--model-path", required=True, type=Path)
    parser.add_argument("--dtype", required=True, choices=("half", "bfloat16"))
    parser.add_argument("--estimated-peak-mib", required=True, type=int)
    parser.add_argument("--log-file", required=True, type=Path)
    parser.add_argument("--report-file", required=True, type=Path)
    parser.add_argument("--port", type=int, default=8003)
    parser.add_argument("--max-seconds", type=float, default=1800)
    parser.add_argument("--max-model-len", type=int, default=4096)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.50)
    parser.add_argument("--torch-memory-fraction", type=float, default=0.50)
    parser.add_argument("--no-torch-cap", action="store_true")
    parser.add_argument("--peak-allowance-mib", type=int, default=1024)
    parser.add_argument("--served-model-name", default="neurobuild-local")
    parser.add_argument("--enable-reasoning", action="store_true",
                        help="Explicit A100 V0 experiment using deepseek_r1; requests must enable thinking")
    arguments = vars(parser.parse_args(argv))
    if arguments.pop("no_torch_cap"):
        arguments["torch_memory_fraction"] = None
    stop = threading.Event()
    previous = {sig: signal.signal(sig, lambda *_: stop.set()) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        try:
            report = run_guard(LaunchConfig(**arguments), stop_requested=stop.is_set)
        except PreflightError as error:
            report = {"schema_version": 1, "state": "BLOCKED", "reason": error.code, "error": str(error)}
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    print(json.dumps(report, indent=2, allow_nan=False))
    expected_stop = report["reason"] in ("TIME_LIMIT", "STOP_REQUESTED")
    clean_exit = report["reason"] == "CHILD_EXITED" and report.get("child_exit_code") == 0
    return 0 if (expected_stop or clean_exit) and report.get("shutdown", {}).get("child_reaped") else 2


if __name__ == "__main__":
    raise SystemExit(main())
