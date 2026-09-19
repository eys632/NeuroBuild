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


def require(condition, code, message):
    if not condition:
        raise PreflightError(code, message)


def local_path(value, root, *, output=False):
    path = Path(value)
    path = (root / path).resolve() if not path.is_absolute() else path.resolve()
    boundary = (root / "var").resolve() if output else root.resolve()
    require(boundary.is_relative_to(root.resolve()) and path.is_relative_to(boundary) and path != boundary,
            "INVALID_PATH", "Models must be local to the checkout; output paths must be below its var directory")
    return path


def runtime_output_path(value, root, directory):
    """Keep mutable guard output separate from model and immutable artifact data."""
    root = root.resolve()
    boundary = root / "var" / directory
    path = Path(value)
    path = root / path if not path.is_absolute() else path
    require(boundary.resolve() == boundary and not path.is_symlink(),
            "INVALID_PATH", "Runtime output directories and files must not alias other storage")
    path = path.resolve()
    require(path.is_relative_to(boundary) and path != boundary,
            "INVALID_PATH", "Logs require var/logs and reports require var/reports")
    if path.exists():
        info = path.stat()
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and info.st_nlink == 1,
                "INVALID_PATH", "Existing runtime output must be an owned regular file without hardlink aliases")
    return path


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


def acquire_project_lock(root):
    """Serialize our project's model lifecycles before taking a GPU baseline."""
    run_root = local_path(root / "var/run", root, output=True)
    run_root.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(run_root / "model-server.lock", os.O_CREAT | os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(descriptor)
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid(),
                "INVALID_GUARD_LOCK", "Guard lock must be an owned regular file")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise PreflightError("OWN_MODEL_ALREADY_RUNNING", "This project's model guard is already active") from None
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def write_report(path, report):
    """Atomically replace only the explicitly selected project-var JSON report."""
    descriptor, name = tempfile.mkstemp(prefix=".model-report-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def peek_child_exit(child):
    """Observe only our child, retaining its PID/group identity until cleanup."""
    return os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None


def stop_owned_child(child, killpg, peek_exit, sleep, monotonic):
    """Signal only the group created by our own Popen(start_new_session=True)."""
    result = {"term_sent": False, "kill_sent": False, "child_reaped": False}
    if child.returncode is not None:
        result["child_reaped"] = True
        return result  # Do not signal a potentially reused group ID after reaping.
    try:
        killpg(child.pid, signal.SIGTERM)
        result["term_sent"] = True
    except ProcessLookupError:
        pass
    deadline = monotonic() + 10
    while not peek_exit(child) and monotonic() < deadline:
        sleep(0.1)
    # Even if the leader obeyed TERM, its helpers may have ignored it. The
    # unreaped leader prevents this process-group ID being reused by others.
    try:
        killpg(child.pid, signal.SIGKILL)
        result["kill_sent"] = True
    except ProcessLookupError:
        pass
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        return result
    result["child_reaped"] = True
    return result


def run_guard(config, *, root=ROOT, environ=None, query=None, popen=None, killpg=None,
              sleep=None, monotonic=None, stop_requested=None, peek_exit=None):
    """Foreground guard; dependency injection keeps tests entirely CPU/fake-only."""
    root = Path(root).resolve()
    environ = os.environ if environ is None else environ
    query = _query_gpu if query is None else query
    popen = subprocess.Popen if popen is None else popen
    killpg = os.killpg if killpg is None else killpg
    sleep = time.sleep if sleep is None else sleep
    monotonic = time.monotonic if monotonic is None else monotonic
    peek_exit = peek_child_exit if peek_exit is None else peek_exit
    stop_requested = (lambda: False) if stop_requested is None else stop_requested
    report = {"schema_version": 1, "profile": config.profile, "state": "BLOCKED",
              "enable_reasoning": config.enable_reasoning,
              "reasoning_parser": "deepseek_r1" if config.enable_reasoning else None,
              "started_at_utc": datetime.now(timezone.utc).isoformat(), "reason": None,
              "memory_fit_guaranteed": False, "inference_validation": "NOT_ESTABLISHED",
              "measurement_scope": "permitted_GPU_aggregate_only", "per_process_measurement": False,
              "peak_attribution_notice": "Aggregate baseline-relative increase is not a guaranteed per-process upper bound: other workloads may release memory between samples.",
              "poll_interval_seconds": POLL_SECONDS, "elapsed_seconds": 0,
              "observed_baseline_relative_peak_mib": 0, "watchdog_sample_count": 0}
    child = None
    report_path = None
    rendezvous_dir = None
    lock_fd = None
    started = monotonic()
    try:
        require(config.profile == "a100", "RUNTIME_PROFILE_NOT_VALIDATED",
                "The current cu118 runtime is validated for the A100 launch path only; RTX5090 requires its own runtime validation")
        model = local_path(config.model_path, root)
        log_path = runtime_output_path(config.log_file, root, "logs")
        candidate_report = runtime_output_path(config.report_file, root, "reports")
        require(log_path != candidate_report and not log_path.is_relative_to(model)
                and not candidate_report.is_relative_to(model), "INVALID_PATH", "Log/report paths must differ and must not overwrite model files")
        require(model.is_dir() and (model / "config.json").is_file(),
                "MODEL_NOT_LOCAL", "A downloaded local model directory with config.json is required")
        runtime = root / ".conda-vllm/bin/python"
        require(runtime.is_file() and runtime.resolve().is_relative_to((root / ".conda-vllm").resolve()),
                "RUNTIME_NOT_LOCAL", "The project .conda-vllm Python is required")
        lock_fd = acquire_project_lock(root)
        report_path = candidate_report
        log_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        child_env = child_environment(config, root, environ)
        report.update(log_file=str(log_path), model_path=str(model), dtype=config.dtype, served_model_name=config.served_model_name,
                      torch_allocator_fraction=config.torch_memory_fraction,
                      gpu_memory_utilization=config.gpu_memory_utilization,
                      max_model_len=config.max_model_len, physical_gpu_index=3,
                      required_cuda_visible_devices="3", peak_allowance_mib=config.peak_allowance_mib)
        preflight = run_preflight(Policy(config.profile, config.estimated_peak_mib),
                                  environ=environ, query=query, sleep=sleep)
        report["preflight"] = preflight
        require(preflight["allowed"], "PREFLIGHT_BLOCKED", "The current permitted-GPU budget does not allow launch")
        total = preflight["measured"]["total_mib"]
        budget = preflight["budget"]["available_model_budget_mib"]
        margin = preflight["budget"]["required_safety_margin_mib"]
        fractions = (config.gpu_memory_utilization, config.torch_memory_fraction)
        require(all(fraction is None or math.ceil(fraction * total) <= budget for fraction in fractions),
                "ALLOCATION_CAP_EXCEEDS_BUDGET", "Reduce configured runtime/allocator fractions to the measured model budget")
        baseline = min(row["used_mib"] for row in preflight["samples"])
        rise_limit = min(config.estimated_peak_mib + config.peak_allowance_mib, budget)
        report.update(state="STARTING", baseline_used_mib=baseline,
                      required_free_floor_mib=margin, aggregate_increment_limit_mib=rise_limit,
                      minimum_observed_free_mib=preflight["measured"]["minimum_free_mib"])
        rendezvous_root = local_path(root / "var/run/rendezvous", root, output=True)
        rendezvous_root.mkdir(parents=True, exist_ok=True)
        rendezvous_dir = Path(tempfile.mkdtemp(prefix="model-", dir=rendezvous_root))
        rendezvous_file = rendezvous_dir / "store"
        command = launch_command(config, root, rendezvous_file=rendezvous_file)
        report.update(rendezvous={"kind": "FILE_STORE", "path": str(rendezvous_file), "world_size": 1,
                                  "gloo_interface": "lo", "nccl_interface": "=lo", "cleaned": False})
        write_report(report_path, report)
        require(not stop_requested(), "STOP_REQUESTED", "Launch was cancelled before process creation")
        with log_path.open("ab", buffering=0) as log:
            child = popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                          cwd=str(root), env=child_env, start_new_session=True)
            started = monotonic()
            report.update(state="RUNNING", child_pid=child.pid, reason=None)
            write_report(report_path, report)
            while True:
                report["elapsed_seconds"] = round(monotonic() - started, 3)
                if stop_requested():
                    report["reason"] = "STOP_REQUESTED"
                    break
                if peek_exit(child):
                    report["reason"] = "CHILD_EXITED"
                    break
                if report["elapsed_seconds"] >= config.max_seconds:
                    report["reason"] = "TIME_LIMIT"
                    break
                reading = parse_reading(query(3))
                require(reading.total_mib == total, "GPU_TOTAL_CHANGED", "GPU total changed during execution")
                report["watchdog_sample_count"] += 1
                report["minimum_observed_free_mib"] = min(report["minimum_observed_free_mib"], reading.free_mib)
                rise = max(0, reading.used_mib - baseline)
                report["observed_baseline_relative_peak_mib"] = max(report["observed_baseline_relative_peak_mib"], rise)
                if reading.free_mib < margin:
                    report["reason"] = "FREE_MARGIN_BREACHED"
                    break
                if rise > rise_limit:
                    report["reason"] = "PEAK_BUDGET_EXCEEDED"
                    break
                write_report(report_path, report)
                sleep(POLL_SECONDS)
    except PreflightError as error:
        report.update(reason=error.code, error=str(error))
    except (OSError, subprocess.SubprocessError):
        report.update(reason="LAUNCH_OR_MONITOR_IO_FAILED", error="Local launch or monitoring I/O failed")
    finally:
        if child is not None:
            try:
                report["shutdown"] = stop_owned_child(child, killpg, peek_exit, sleep, monotonic)
                report["child_exit_code"] = child.returncode
            except OSError:
                report["shutdown"] = {"child_reaped": False, "error": "OWN_CHILD_SHUTDOWN_FAILED"}
            report["state"] = "STOPPED" if report["shutdown"]["child_reaped"] else "STOP_FAILED"
            report["elapsed_seconds"] = round(monotonic() - started, 3)
        if rendezvous_dir is not None and (child is None or report["shutdown"]["child_reaped"]):
            try:
                # Only this guard's unique file/directory; no recursive cleanup.
                (rendezvous_dir / "store").unlink(missing_ok=True)
                rendezvous_dir.rmdir()
                report["rendezvous"]["cleaned"] = True
            except OSError:
                report["rendezvous"]["cleanup_error"] = "RENDEZVOUS_CLEANUP_FAILED"
        report["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
        if report_path is not None and report_path.parent.is_dir():
            try:
                write_report(report_path, report)
            except OSError:
                report["report_write_failed"] = True
        if lock_fd is not None:
            os.close(lock_fd)  # Keep the regular lock file; never unlink a held-lock identity.
    return report


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
