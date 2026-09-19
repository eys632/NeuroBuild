"""Launcher watchdog tests with fake children and fake permitted-GPU readings only."""

from dataclasses import replace
import json
import fcntl
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import sys
import unittest
from unittest.mock import patch

from scripts.gpu_preflight import PreflightError
from scripts.model_server import (
    LaunchConfig, PARENT_DEATH_BOOTSTRAP, child_environment, launch_command, run_guard,
)


STABLE = "40960, 36373, 3965, 0"


class FakeChild:
    pid = 765432

    def __init__(self, *, stubborn=False, exited=False):
        self.returncode = 0 if exited else None
        self.stubborn = stubborn
        self.waits = []

    def poll(self):
        return self.returncode

    def wait(self, timeout):
        self.waits.append(timeout)
        self.returncode = -9 if self.stubborn else -15
        return self.returncode


class ModelServerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        model = self.root / "var/models/synthetic"
        model.mkdir(parents=True)
        (model / "config.json").write_text("{}")
        runtime = self.root / ".conda-vllm/bin/python"
        runtime.parent.mkdir(parents=True)
        runtime.write_text("synthetic executable; never run")
        self.config = LaunchConfig("a100", model, "half", 18432,
                                   Path("var/logs/launch.log"), Path("var/reports/launch.json"), max_seconds=1)
        # Fail loudly if a test accidentally escapes dependency injection.
        self.addCleanup(patch.stopall)
        patch("scripts.model_server.subprocess.Popen", side_effect=AssertionError("Real child forbidden")).start()
        patch("scripts.model_server.os.killpg", side_effect=AssertionError("Real signal forbidden")).start()
        patch("scripts.model_server._query_gpu", side_effect=AssertionError("Real GPU query forbidden")).start()

    def run_fake(self, *, config=None, rows=(), child=None, environ=None, stop=None):
        values = iter([STABLE] * 5 + list(rows))
        child = child or FakeChild()
        queried, launches, signals, sleeps = [], [], [], []
        now = [0.0]
        term_sent = [False]

        def query(index):
            queried.append(index)
            value = next(values, STABLE)
            if isinstance(value, BaseException):
                raise value
            return value

        def sleep(seconds):
            sleeps.append(seconds)
            now[0] += seconds

        def popen(command, **kwargs):
            launches.append((command, kwargs))
            return child

        def killpg(pid, sig):
            signals.append((pid, sig))
            if sig == signal.SIGTERM:
                term_sent[0] = True

        def peek_exit(process):
            return process.returncode is not None or (term_sent[0] and not process.stubborn)

        report = run_guard(config or self.config, root=self.root,
                           environ=environ or {"CUDA_VISIBLE_DEVICES": "3"}, query=query,
                           sleep=sleep, monotonic=lambda: now[0], popen=popen,
                           killpg=killpg, stop_requested=stop, peek_exit=peek_exit)
        return report, queried, launches, signals, child, sleeps

    def test_fits_then_bounded_timeout_stops_only_new_group(self):
        report, queried, launches, signals, child, sleeps = self.run_fake(rows=["40960, 24000, 16338, 100"] * 2)
        self.assertEqual(report["reason"], "TIME_LIMIT")
        self.assertEqual(report["state"], "STOPPED")
        self.assertTrue(report["shutdown"]["child_reaped"])
        self.assertEqual(signals, [(child.pid, signal.SIGTERM), (child.pid, signal.SIGKILL)])
        self.assertEqual(queried, [3] * 7)
        self.assertEqual(sleeps, [1.0] * 4 + [0.5] * 2)
        self.assertEqual(report["required_free_floor_mib"], 7275)
        self.assertEqual(report["aggregate_increment_limit_mib"], 19456)
        self.assertEqual(report["observed_baseline_relative_peak_mib"], 12373)
        self.assertFalse(report["per_process_measurement"])
        self.assertFalse(report["memory_fit_guaranteed"])
        command, kwargs = launches[0]
        self.assertTrue(kwargs["start_new_session"])
        self.assertEqual(kwargs["env"]["CUDA_VISIBLE_DEVICES"], "3")
        self.assertEqual(kwargs["env"]["CUDA_DEVICE_ORDER"], "PCI_BUS_ID")
        self.assertEqual(json.loads((self.root / self.config.report_file).read_text()), report)
        self.assertEqual(command[0], str(self.root / ".conda-vllm/bin/python"))
        self.assertEqual(report["rendezvous"]["kind"], "FILE_STORE")
        self.assertTrue(report["rendezvous"]["cleaned"])
        self.assertFalse(Path(report["rendezvous"]["path"]).parent.exists())

    def test_memory_floor_breach_stops_immediately_and_kills_stubborn_child(self):
        report, _, _, signals, child, _ = self.run_fake(rows=["40960, 7274, 33064, 50"], child=FakeChild(stubborn=True))
        self.assertEqual(report["reason"], "FREE_MARGIN_BREACHED")
        self.assertEqual(signals, [(child.pid, signal.SIGTERM), (child.pid, signal.SIGKILL)])
        self.assertEqual(child.waits, [5])
        self.assertEqual(report["watchdog_sample_count"], 1)

    def test_aggregate_growth_ceiling_without_free_floor_breach(self):
        report, _, _, signals, _, _ = self.run_fake(rows=["40960, 16916, 23422, 99"])
        self.assertEqual(report["reason"], "PEAK_BUDGET_EXCEEDED")
        self.assertGreater(report["minimum_observed_free_mib"], report["required_free_floor_mib"])
        self.assertEqual(len(signals), 2)

    def test_query_failure_unknown_values_or_device_change_shutdown(self):
        for value, reason in [(PreflightError("GPU_QUERY_FAILED", "synthetic"), "GPU_QUERY_FAILED"),
                              ("N/A, 30000, 10000, 1", "INVALID_READING"),
                              ("50000, 36373, 3965, 0", "GPU_TOTAL_CHANGED")]:
            with self.subTest(reason=reason):
                report, _, launches, signals, _, _ = self.run_fake(rows=[value])
                self.assertEqual(report["reason"], reason)
                self.assertEqual(len(launches), 1)
                self.assertEqual(len(signals), 2)

    def test_preflight_mask_mismatch_never_queries_or_spawns(self):
        report, queried, launches, signals, _, _ = self.run_fake(environ={"CUDA_VISIBLE_DEVICES": "0,3"})
        self.assertEqual(report["reason"], "PREFLIGHT_BLOCKED")
        self.assertEqual(report["preflight"]["reason_codes"], ["CUDA_MASK_MISMATCH"])
        self.assertEqual((queried, launches, signals), ([], [], []))

    def test_profile_rtx_reserved_until_runtime_validated(self):
        report, queried, launches, signals, _, _ = self.run_fake(config=replace(self.config, profile="rtx5090"))
        self.assertEqual(report["reason"], "RUNTIME_PROFILE_NOT_VALIDATED")
        self.assertEqual((queried, launches, signals), ([], [], []))

    def test_runtime_caps_above_measured_budget_reject_before_child(self):
        for key in ("torch_memory_fraction", "gpu_memory_utilization"):
            with self.subTest(key=key):
                report, _, launches, signals, _, _ = self.run_fake(config=replace(self.config, **{key: 0.8}))
                self.assertEqual(report["reason"], "ALLOCATION_CAP_EXCEEDS_BUDGET")
                self.assertEqual((launches, signals), ([], []))
        report, _, launches, _, _, _ = self.run_fake(config=replace(self.config, estimated_peak_mib=23552,
                                                                 gpu_memory_utilization=0.6, torch_memory_fraction=0.6))
        self.assertEqual(report["reason"], "TIME_LIMIT")
        self.assertEqual(len(launches), 1)

    def test_stop_request_cleans_up_without_waiting_for_time_limit(self):
        calls = [0]

        def stop():
            calls[0] += 1
            return calls[0] >= 2

        report, queried, _, signals, _, _ = self.run_fake(stop=stop)
        self.assertEqual(report["reason"], "STOP_REQUESTED")
        self.assertEqual(len(queried), 5)
        self.assertEqual(len(signals), 2)

    def test_already_exited_child_does_not_signal_reused_group(self):
        report, _, _, signals, _, _ = self.run_fake(child=FakeChild(exited=True))
        self.assertEqual(report["reason"], "CHILD_EXITED")
        self.assertEqual(report["child_exit_code"], 0)
        self.assertEqual(signals, [])

    def test_output_failure_after_spawn_still_stops_own_child(self):
        from scripts.model_server import write_report
        calls = [0]

        def broken(path, report):
            calls[0] += 1
            if calls[0] >= 2:
                raise OSError("synthetic report storage failure")
            write_report(path, report)

        with patch("scripts.model_server.write_report", side_effect=broken):
            report, _, launches, signals, _, _ = self.run_fake()
        self.assertEqual(report["reason"], "LAUNCH_OR_MONITOR_IO_FAILED")
        self.assertTrue(report["report_write_failed"])
        self.assertEqual(len(launches), 1)
        self.assertEqual(len(signals), 2)

    def test_failed_shutdown_is_not_reported_stopped(self):
        child = FakeChild()
        child.wait = lambda timeout: (_ for _ in ()).throw(subprocess.TimeoutExpired("synthetic", timeout))
        report, _, _, _, _, _ = self.run_fake(child=child)
        self.assertEqual(report["state"], "STOP_FAILED")
        self.assertFalse(report["shutdown"]["child_reaped"])
        self.assertFalse(report["rendezvous"]["cleaned"])
        self.assertTrue(Path(report["rendezvous"]["path"]).parent.is_dir())

    def test_each_launch_has_fresh_rendezvous_and_does_not_delete_old_files(self):
        old = self.root / "var/run/rendezvous/old-run/store"
        old.parent.mkdir(parents=True)
        old.write_text("unrelated prior run")
        first, *_ = self.run_fake()
        second, *_ = self.run_fake()
        self.assertNotEqual(first["rendezvous"]["path"], second["rendezvous"]["path"])
        self.assertEqual(old.read_text(), "unrelated prior run")

    def test_project_lock_blocks_second_guard_before_gpu_query_or_spawn(self):
        lock = self.root / "var/run/model-server.lock"
        lock.parent.mkdir(parents=True)
        active_report = self.root / self.config.report_file
        active_report.parent.mkdir(parents=True)
        active_report.write_text('existing active guard report')
        with lock.open("w") as owned:
            fcntl.flock(owned.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            report, queried, launched, signals, *_ = self.run_fake()
            self.assertEqual(report["reason"], "OWN_MODEL_ALREADY_RUNNING")
            self.assertEqual((queried, launched, signals), ([], [], []))
            self.assertEqual(active_report.read_text(), 'existing active guard report')
        report, *_ = self.run_fake()
        self.assertEqual(report["reason"], "TIME_LIMIT")
        self.assertTrue(lock.is_file())

    def test_project_lock_refuses_symlink_without_touching_target(self):
        target = self.root / "var/other-owned-file"
        target.write_text("unchanged")
        lock = self.root / "var/run/model-server.lock"
        lock.parent.mkdir(parents=True)
        lock.symlink_to(target)
        report, queried, launched, *_ = self.run_fake()
        self.assertEqual(report["reason"], "LAUNCH_OR_MONITOR_IO_FAILED")
        self.assertEqual((queried, launched), ([], []))
        self.assertEqual(target.read_text(), "unchanged")

    def test_outputs_cannot_escape_var_or_follow_external_directory(self):
        for config in (replace(self.config, log_file=Path("../outside.log")),
                       replace(self.config, report_file=self.config.log_file)):
            report, queried, launches, _, _, _ = self.run_fake(config=config)
            self.assertEqual(report["reason"], "INVALID_PATH")
            self.assertEqual((queried, launches), ([], []))
        (self.root / "var/external").symlink_to(self.root.parent, target_is_directory=True)
        report, queried, launches, _, _, _ = self.run_fake(config=replace(self.config, log_file=Path("var/external/outside.log")))
        self.assertEqual(report["reason"], "INVALID_PATH")
        self.assertEqual((queried, launches), ([], []))

    def test_command_uses_same_process_cap_and_known_pinned_flags(self):
        config = replace(self.config, served_model_name="neurobuild-candidate")
        command = launch_command(config, self.root, rendezvous_file=self.root / "var/run/rendezvous/test/store")
        self.assertIn("torch.cuda.set_per_process_memory_fraction", command[2])
        self.assertLess(command[2].index("set_per_process_memory_fraction"), command[2].index("runpy.run_module"))
        self.assertIn("GPU_IDENTITY_MISMATCH", command[2])
        self.assertIn("torch.distributed.FileStore(rendezvous_file, 1)", command[2])
        self.assertLess(command[2].index("set_per_process_memory_fraction"), command[2].index("init_process_group"))
        self.assertLess(command[2].index("init_process_group"), command[2].index("runpy.run_module"))
        self.assertLess(command[2].index("prctl("), command[2].index("import torch"))
        self.assertEqual(command[3], str(os.getpid()))
        self.assertIn("'-i', '3'", command[2])
        for flag in ("--disable-frontend-multiprocessing", "--enforce-eager", "--no-enable-prefix-caching",
                     "--disable-log-requests", "--disable-uvicorn-access-log"):
            self.assertIn(flag, command)
        for flag, value in (("--host", "127.0.0.1"), ("--distributed-executor-backend", "uni"),
                            ("--tensor-parallel-size", "1"), ("--served-model-name", "neurobuild-candidate")):
            self.assertEqual(command[command.index(flag) + 1], value)
        env = child_environment(config, self.root, {"PYTHONPATH": "/other", "CUDA_VISIBLE_DEVICES": "3",
                                                    "VLLM_DP_SIZE": "8", "RANK": "6", "MASTER_ADDR": "external"})
        self.assertNotIn("PYTHONPATH", env)
        self.assertEqual(env["VLLM_USE_V1"], "0")
        self.assertEqual(env["HF_HUB_OFFLINE"], "1")
        self.assertEqual(env["GLOO_SOCKET_IFNAME"], "lo")
        self.assertEqual(env["NCCL_SOCKET_IFNAME"], "=lo")
        self.assertEqual(env["NCCL_IB_DISABLE"], "1")
        self.assertEqual(env["VLLM_HOST_IP"], "127.0.0.1")
        self.assertEqual(env["PYTHONNOUSERSITE"], "1")
        self.assertEqual(env["VLLM_DP_SIZE"], "1")
        self.assertEqual(env["VLLM_DP_RANK"], "0")
        self.assertEqual(env["VLLM_DP_RANK_LOCAL"], "0")
        self.assertEqual(env["VLLM_DP_MASTER_PORT"], "0")
        self.assertNotIn("RANK", env)
        self.assertNotIn("MASTER_ADDR", env)
        for key in ("HF_HOME", "TORCH_HOME", "TRITON_CACHE_DIR", "VLLM_CACHE_ROOT", "XDG_CACHE_HOME", "TMPDIR"):
            self.assertTrue(Path(env[key]).is_relative_to(self.root / "var"))

    def test_invalid_configs_fail_before_io(self):
        for changes in ({"max_seconds": float("inf")}, {"dtype": "auto"}, {"estimated_peak_mib": True},
                        {"torch_memory_fraction": 1.0}, {"gpu_memory_utilization": None},
                        {"served_model_name": "../external"}, {"max_model_len": 8192}):
            with self.subTest(changes=changes), self.assertRaises(PreflightError):
                replace(self.config, **changes)


@unittest.skipUnless(sys.platform == "linux", "Linux PR_SET_PDEATHSIG and waitid contract")
class CpuProcessLifecycleTests(unittest.TestCase):
    """Real, tiny CPU children created by this test only; no torch or GPU calls."""

    def test_parent_death_kills_own_child_even_when_term_is_ignored(self):
        child_code = PARENT_DEATH_BOOTSTRAP + """
import time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
print('armed', flush=True)
time.sleep(20)
"""
        parent_code = f"""
import os, subprocess, sys, time
child = subprocess.Popen([sys.executable, '-c', {child_code!r}, str(os.getpid())], stdout=subprocess.PIPE, text=True)
assert child.stdout.readline().strip() == 'armed'
print(child.pid, flush=True)
time.sleep(20)
"""
        harness = f"""
import ctypes, os, signal, subprocess, sys, time
assert ctypes.CDLL(None).prctl(36, 1, 0, 0, 0) == 0  # adopt/reap only this harness's orphan
parent = subprocess.Popen([sys.executable, '-c', {parent_code!r}], stdout=subprocess.PIPE, text=True)
child_pid = int(parent.stdout.readline())
child_reaped = False
try:
    parent.kill()
    parent.wait(timeout=3)
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        found, status = os.waitpid(child_pid, os.WNOHANG)
        if found:
            child_reaped = True
            assert os.WIFSIGNALED(status) and os.WTERMSIG(status) == signal.SIGKILL
            print('PARENT_DEATH_PASS')
            break
        time.sleep(0.02)
    else:
        raise AssertionError('own child survived watchdog death')
finally:
    if parent.poll() is None:
        parent.kill()
        parent.wait(timeout=3)
    if not child_reaped:
        try:
            os.kill(child_pid, signal.SIGKILL)
            os.waitpid(child_pid, 0)
        except (ProcessLookupError, ChildProcessError):
            pass
"""
        result = subprocess.run([sys.executable, "-B", "-c", harness], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PARENT_DEATH_PASS", result.stdout)

    def test_unreaped_leader_allows_killing_term_ignoring_own_descendant(self):
        descendant = "import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); print('armed',flush=True); time.sleep(20)"
        leader = f"""
import subprocess, sys, time
child = subprocess.Popen([sys.executable, '-c', {descendant!r}], stdout=subprocess.PIPE, text=True)
assert child.stdout.readline().strip() == 'armed'
print(child.pid, flush=True)
time.sleep(20)
"""
        harness = f"""
import ctypes, os, signal, subprocess, sys, time
from scripts.model_server import stop_owned_child, peek_child_exit
assert ctypes.CDLL(None).prctl(36, 1, 0, 0, 0) == 0
leader = subprocess.Popen([sys.executable, '-c', {leader!r}], stdout=subprocess.PIPE, text=True, start_new_session=True)
descendant_pid = int(leader.stdout.readline())
descendant_reaped = False
try:
    result = stop_owned_child(leader, os.killpg, peek_child_exit, time.sleep, time.monotonic)
    assert result['term_sent'] and result['kill_sent'] and result['child_reaped']
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        found, status = os.waitpid(descendant_pid, os.WNOHANG)
        if found:
            descendant_reaped = True
            assert os.WIFSIGNALED(status) and os.WTERMSIG(status) == signal.SIGKILL
            print('OWN_GROUP_PASS')
            break
        time.sleep(0.02)
    else:
        raise AssertionError('own descendant survived group shutdown')
finally:
    if leader.returncode is None:
        os.killpg(leader.pid, signal.SIGKILL)
        leader.wait(timeout=3)
    if not descendant_reaped:
        try:
            os.kill(descendant_pid, signal.SIGKILL)
            os.waitpid(descendant_pid, 0)
        except (ProcessLookupError, ChildProcessError):
            pass
"""
        result = subprocess.run([sys.executable, "-B", "-c", harness], cwd=Path(__file__).resolve().parents[1],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("OWN_GROUP_PASS", result.stdout)


class CpuFileStoreTests(unittest.TestCase):
    """Optional installed model-runtime probe, with every CUDA device hidden."""

    def test_gloo_file_store_and_subgroups_listen_only_on_own_loopback_sockets(self):
        root = Path(__file__).resolve().parents[1]
        runtime = root / ".conda-vllm/bin/python"
        if not runtime.is_file():
            self.skipTest("Separate model runtime not installed; no backend torch dependency")
        probe = """
import errno, ipaddress, json, os, socket, sys
from datetime import timedelta
from pathlib import Path
import torch.distributed as dist
store = dist.FileStore(sys.argv[1], 1)
dist.init_process_group('gloo', store=store, rank=0, world_size=1, timeout=timedelta(seconds=15))
groups = [dist.new_group([0], backend='gloo', timeout=timedelta(seconds=15)) for _ in range(4)]
listeners = []
try:
    # Inspect only descriptors owned by THIS probe, never a global socket table.
    for entry in Path('/proc/self/fd').iterdir():
        try:
            if not os.readlink(entry).startswith('socket:['):
                continue
            with socket.socket(fileno=os.dup(int(entry.name))) as owned:
                if owned.family not in (socket.AF_INET, socket.AF_INET6):
                    continue
                if owned.getsockopt(socket.SOL_SOCKET, socket.SO_ACCEPTCONN):
                    address = owned.getsockname()[0]
                    assert ipaddress.ip_address(address).is_loopback, address
                    listeners.append(address)
        except OSError as error:
            if error.errno not in (errno.ENOENT, errno.EBADF, errno.ENOTSOCK):
                raise
    assert listeners, 'probe did not inspect any Gloo listeners'
    print(json.dumps({'event':'CPU_FILESTORE_LOOPBACK_PASS', 'listeners':listeners, 'world_size':dist.get_world_size()}))
finally:
    for group in reversed(groups):
        dist.destroy_process_group(group)
    dist.destroy_process_group()
"""
        with tempfile.TemporaryDirectory(prefix="cpu-filestore-", dir=root / "var/run") as directory:
            env = dict(os.environ, CUDA_VISIBLE_DEVICES="", GLOO_SOCKET_IFNAME="lo", NCCL_SOCKET_IFNAME="=lo",
                       NCCL_IB_DISABLE="1", VLLM_HOST_IP="127.0.0.1", PYTHONNOUSERSITE="1")
            result = subprocess.run([str(runtime), "-I", "-B", "-c", probe, str(Path(directory) / "store")],
                                    cwd=root, env=env, capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual(report["event"], "CPU_FILESTORE_LOOPBACK_PASS")
        self.assertEqual(report["world_size"], 1)
        self.assertTrue(set(report["listeners"]) <= {"127.0.0.1", "::1"})


if __name__ == "__main__":
    unittest.main()
