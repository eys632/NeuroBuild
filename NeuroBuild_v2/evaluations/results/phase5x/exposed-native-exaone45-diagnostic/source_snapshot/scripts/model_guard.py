"""Shared stdlib guard lifecycle; runtime-specific code cannot bypass its budget/cleanup."""
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import tempfile
import time

try:
    from .gpu_preflight import Policy, PreflightError, _query_gpu, parse_reading, run_preflight
except ImportError:
    from gpu_preflight import Policy, PreflightError, _query_gpu, parse_reading, run_preflight

ROOT = Path(__file__).resolve().parents[1]
POLL_SECONDS = 0.5

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


def run_lifecycle(config, runtime, *, root=ROOT, environ=None, query=None, popen=None, killpg=None,
              sleep=None, monotonic=None, stop_requested=None, peek_exit=None, report_writer=None):
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
    report_writer = write_report if report_writer is None else report_writer
    report = {"schema_version": 1, "profile": config.profile, "state": "BLOCKED",
              **runtime.initial_fields(config),
              "started_at_utc": datetime.now(timezone.utc).isoformat(), "reason": None,
              "memory_fit_guaranteed": False, "inference_validation": "NOT_ESTABLISHED",
              "measurement_scope": "permitted_GPU_aggregate_only", "per_process_measurement": False,
              "peak_attribution_notice": "Aggregate baseline-relative increase is not a guaranteed per-process upper bound: other workloads may release memory between samples.",
              "poll_interval_seconds": POLL_SECONDS, "elapsed_seconds": 0,
              "observed_baseline_relative_peak_mib": 0, "watchdog_sample_count": 0}
    child = None
    report_path = None
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
        runtime.validate(config, root, model)
        lock_fd = acquire_project_lock(root)
        report_path = candidate_report
        log_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        child_env = runtime.environment(config, root, environ)
        report.update(log_file=str(log_path), model_path=str(model),
                      served_model_name=config.served_model_name,
                      max_model_len=config.max_model_len, physical_gpu_index=3,
                      required_cuda_visible_devices="3", peak_allowance_mib=config.peak_allowance_mib,
                      **runtime.fields(config))
        preflight = run_preflight(Policy(config.profile, config.estimated_peak_mib),
                                  environ=environ, query=query, sleep=sleep)
        report["preflight"] = preflight
        require(preflight["allowed"], "PREFLIGHT_BLOCKED", "The current permitted-GPU budget does not allow launch")
        total = preflight["measured"]["total_mib"]
        budget = preflight["budget"]["available_model_budget_mib"]
        margin = preflight["budget"]["required_safety_margin_mib"]
        runtime.check_budget(config, total, budget)
        baseline = min(row["used_mib"] for row in preflight["samples"])
        rise_limit = min(config.estimated_peak_mib + config.peak_allowance_mib, budget)
        report.update(state="STARTING", baseline_used_mib=baseline,
                      required_free_floor_mib=margin, aggregate_increment_limit_mib=rise_limit,
                      minimum_observed_free_mib=preflight["measured"]["minimum_free_mib"])
        command = runtime.prepare(config, root, report)
        report_writer(report_path, report)
        require(not stop_requested(), "STOP_REQUESTED", "Launch was cancelled before process creation")
        with log_path.open("ab", buffering=0) as log:
            child = popen(command, stdin=subprocess.DEVNULL, **runtime.output_options(log),
                          cwd=str(root), env=child_env, start_new_session=True)
            runtime.after_spawn(child)
            started = monotonic()
            report.update(state="RUNNING", child_pid=child.pid, reason=None)
            report_writer(report_path, report)
            while True:
                report["elapsed_seconds"] = round(monotonic() - started, 3)
                if stop_requested():
                    report["reason"] = "STOP_REQUESTED"
                    break
                runtime.observe(child, report)
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
                report_writer(report_path, report)
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
        runtime.cleanup(report, child is None or report["shutdown"]["child_reaped"])
        report["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
        if report_path is not None and report_path.parent.is_dir():
            try:
                report_writer(report_path, report)
            except OSError:
                report["report_write_failed"] = True
        if lock_fd is not None:
            os.close(lock_fd)  # Keep the regular lock file; never unlink a held-lock identity.
    return report

