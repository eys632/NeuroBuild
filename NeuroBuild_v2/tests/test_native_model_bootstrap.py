"""Metadata calls are faked. Own CPU exec/parent-death probe never loads CUDA."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts import native_model_bootstrap as bootstrap

GPU_UUID = "12345678-1234-5678-9abc-123456789abc"
ENV = {"CUDA_VISIBLE_DEVICES": "3", "CUDA_DEVICE_ORDER": "PCI_BUS_ID"}


class NativeBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.limit_patch = patch.object(bootstrap.resource, "setrlimit")
        self.limit = self.limit_patch.start()
        self.addCleanup(self.limit_patch.stop)

    def test_only_single_visible_device_matching_permitted_uuid_is_accepted(self):
        driver = Mock()
        driver.count.return_value = 1
        driver.uuid.return_value = GPU_UUID
        query = Mock(return_value="GPU-" + GPU_UUID + "\n")
        factory = Mock(return_value=driver)
        bootstrap.verify_gpu_identity(ENV, driver_factory=factory, query=query)
        query.assert_called_once_with()
        driver.uuid.assert_called_once_with()
        for count, value in ((0, GPU_UUID), (2, GPU_UUID), (1, "0" * 36)):
            driver.count.return_value, driver.uuid.return_value = count, value
            with self.subTest(count=count), self.assertRaisesRegex(bootstrap.BootstrapError, "GPU_IDENTITY_MISMATCH"):
                bootstrap.verify_gpu_identity(ENV, driver_factory=factory, query=query)

    def test_mask_rejects_before_driver_or_uuid_query_and_unknown_reading_blocks(self):
        factory, query = Mock(), Mock()
        for env in ({}, {"CUDA_VISIBLE_DEVICES": "1", "CUDA_DEVICE_ORDER": "PCI_BUS_ID"},
                    {"CUDA_VISIBLE_DEVICES": "3", "CUDA_DEVICE_ORDER": "FASTEST_FIRST"}):
            with self.assertRaisesRegex(bootstrap.BootstrapError, "CUDA_MASK_MISMATCH"):
                bootstrap.verify_gpu_identity(env, driver_factory=factory, query=query)
        factory.assert_not_called()
        query.assert_not_called()
        for value in ("N/A", "GPU-" + GPU_UUID + "\nGPU-" + GPU_UUID, ""):
            with self.subTest(value=value), self.assertRaises(bootstrap.BootstrapError):
                bootstrap.verify_gpu_identity(ENV, driver_factory=factory, query=lambda: value)
        factory.assert_not_called()

    def test_uuid_query_targets_only_gpu3_and_never_reads_process_metadata(self):
        with patch.object(bootstrap.subprocess, "run", return_value=Mock(stdout="safe")) as run:
            self.assertEqual(bootstrap.query_permitted_uuid(), "safe")
        self.assertEqual(run.call_args.args[0], ["/usr/bin/nvidia-smi", "-i", "3", "--query-gpu=uuid", "--format=csv,noheader,nounits"])
        self.assertEqual(run.call_args.kwargs["timeout"], 5)

    def test_driver_failure_is_sanitized_and_exec_cannot_follow_failed_identity(self):
        factory = Mock(side_effect=OSError("PRIVATE_DIAGNOSTIC"))
        with self.assertRaisesRegex(bootstrap.BootstrapError, "^GPU_IDENTITY_FAILED$"):
            bootstrap.verify_gpu_identity(ENV, driver_factory=factory, query=lambda: "GPU-" + GPU_UUID)
        read_fd, write_fd = os.pipe()
        execute = Mock()
        try:
            result = bootstrap.run_native(123, write_fd, ["never"], environ=ENV, arm=lambda _: None,
                                          probe=Mock(side_effect=bootstrap.BootstrapError("GPU_IDENTITY_MISMATCH")), execute=execute)
            self.assertEqual(result, 2)
            self.assertEqual(json.loads(os.read(read_fd, 4096)),
                             {"event": "BOOTSTRAP_FAILED", "pid": os.getpid(), "code": "GPU_IDENTITY_MISMATCH"})
            execute.assert_not_called()
        finally:
            os.close(read_fd)

    def test_identity_pipe_is_closed_before_same_pid_exec_and_contains_no_body(self):
        read_fd, write_fd = os.pipe()
        observed = []

        class Executed(BaseException):
            pass

        def execute(path, args, env):
            observed.append((path, args, env, os.getpid()))
            with self.assertRaises(OSError):
                os.fstat(write_fd)
            raise Executed()

        def probe(env):
            self.limit.assert_called_once_with(bootstrap.resource.RLIMIT_CORE, (0, 0))

        try:
            with self.assertRaises(Executed):
                bootstrap.run_native(os.getppid(), write_fd, ["fixed", "--model", "local"], environ=ENV,
                                     arm=lambda _: None, probe=probe, execute=execute)
            record = json.loads(os.read(read_fd, 4096))
            self.assertEqual(record, {"event": "GPU_IDENTITY_VERIFIED", "pid": os.getpid(),
                                      "physical_gpu_index": 3, "logical_device": 0})
            self.assertEqual(observed, [("fixed", ["fixed", "--model", "local"], ENV, os.getpid())])
        finally:
            os.close(read_fd)

    def test_parent_changed_is_rejected_before_prctl_or_driver(self):
        with patch.object(bootstrap.os, "getppid", return_value=123), patch.object(bootstrap.ctypes, "CDLL") as library:
            with self.assertRaisesRegex(bootstrap.BootstrapError, "WATCHDOG_PARENT_CHANGED"):
                bootstrap.arm_parent_death(456)
            library.assert_not_called()

    def test_cpu_same_pid_exec_keeps_parent_death_sigkill(self):
        # A dedicated subreaper owns every process in this probe; no other process is inspected or signalled.
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix="native-death-", dir=root / "var/run") as directory:
            marker = str(Path(directory) / "exec-pid")
            payload = f"import os,resource,signal,time; from pathlib import Path; assert resource.getrlimit(resource.RLIMIT_CORE)==(0,0); signal.signal(signal.SIGTERM,signal.SIG_IGN); Path({marker!r}).write_text(str(os.getpid())); time.sleep(20)"
            child = f"""
import os,sys
from scripts.native_model_bootstrap import run_native
raise SystemExit(run_native(int(sys.argv[1]), int(sys.argv[2]), [sys.executable,'-B','-c',{payload!r}],
                            environ=dict(os.environ), probe=lambda _: None))
"""
            parent = f"""
import json,os,subprocess,sys,time
read_fd, write_fd = os.pipe()
p = subprocess.Popen([sys.executable,'-B','-c',{child!r},str(os.getpid()),str(write_fd)], pass_fds=(write_fd,), start_new_session=True)
os.close(write_fd)
status = json.loads(os.read(read_fd,4096)); os.close(read_fd)
assert status['pid'] == p.pid and status['event'] == 'GPU_IDENTITY_VERIFIED'
print(p.pid,flush=True)
time.sleep(20)
"""
            harness = f"""
import ctypes,os,signal,subprocess,sys,time
from pathlib import Path
assert ctypes.CDLL(None).prctl(36,1,0,0,0) == 0
parent = subprocess.Popen([sys.executable,'-B','-c',{parent!r}], stdout=subprocess.PIPE,text=True,start_new_session=True)
child_pid = int(parent.stdout.readline())
reaped = False
try:
    deadline = time.monotonic()+3
    while not Path({marker!r}).exists() and time.monotonic()<deadline:
        time.sleep(.01)
    assert Path({marker!r}).read_text() == str(child_pid), 'exec changed identity or did not complete'
    parent.kill(); parent.wait(timeout=3)
    deadline = time.monotonic()+3
    while time.monotonic()<deadline:
        pid,status = os.waitpid(child_pid,os.WNOHANG)
        if pid:
            reaped = True
            assert os.WIFSIGNALED(status) and os.WTERMSIG(status)==signal.SIGKILL
            print('NATIVE_SAME_PID_PARENT_DEATH_PASS')
            break
        time.sleep(.01)
    else:
        raise AssertionError('own exec child survived parent death')
finally:
    if parent.poll() is None:
        parent.kill(); parent.wait(timeout=3)
    parent.stdout.close()
    if not reaped:
        try:
            os.kill(child_pid,signal.SIGKILL); os.waitpid(child_pid,0)
        except (ProcessLookupError,ChildProcessError):
            pass
"""
            result = subprocess.run([sys.executable, "-B", "-c", harness], cwd=root,
                                    capture_output=True, text=True, timeout=10,
                                    env=dict(os.environ, CUDA_VISIBLE_DEVICES=""))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("NATIVE_SAME_PID_PARENT_DEATH_PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
