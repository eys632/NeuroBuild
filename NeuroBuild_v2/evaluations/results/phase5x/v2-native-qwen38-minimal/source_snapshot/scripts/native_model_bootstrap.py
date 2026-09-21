#!/usr/bin/env python3
"""Same-PID native exec after permitted-device identity; no Torch or body logging."""
import ctypes
import json
import os
import re
import resource
import signal
import subprocess
import sys
import uuid

DRIVER_LIBRARY = "/usr/lib/x86_64-linux-gnu/libcuda.so.1"


class BootstrapError(Exception):
    pass


def require(ok, code):
    if not ok:
        raise BootstrapError(code)


def arm_parent_death(expected_parent):
    require(os.getppid() == expected_parent, "WATCHDOG_PARENT_CHANGED")
    require(ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGKILL, 0, 0, 0) == 0,
            "WATCHDOG_DEATH_SIGNAL_FAILED")
    if os.getppid() != expected_parent:
        os.kill(os.getpid(), signal.SIGKILL)


class DriverAPI:
    """Only driver metadata calls for the one CUDA-visible device; no context creation."""
    def __init__(self):
        self.library = ctypes.CDLL(DRIVER_LIBRARY)
        for name, arguments in (
            ("cuInit", [ctypes.c_uint]),
            ("cuDeviceGetCount", [ctypes.POINTER(ctypes.c_int)]),
            ("cuDeviceGet", [ctypes.POINTER(ctypes.c_int), ctypes.c_int]),
            ("cuDeviceGetUuid_v2", [ctypes.c_void_p, ctypes.c_int]),
        ):
            function = getattr(self.library, name)
            function.argtypes, function.restype = arguments, ctypes.c_int
        require(self.library.cuInit(0) == 0, "GPU_IDENTITY_FAILED")

    def count(self):
        value = ctypes.c_int()
        require(self.library.cuDeviceGetCount(ctypes.byref(value)) == 0, "GPU_IDENTITY_FAILED")
        return value.value

    def uuid(self):
        device = ctypes.c_int()
        require(self.library.cuDeviceGet(ctypes.byref(device), 0) == 0, "GPU_IDENTITY_FAILED")
        value = (ctypes.c_ubyte * 16)()
        require(self.library.cuDeviceGetUuid_v2(ctypes.byref(value), device.value) == 0, "GPU_IDENTITY_FAILED")
        return str(uuid.UUID(bytes=bytes(value)))


def query_permitted_uuid():
    result = subprocess.run(
        ["/usr/bin/nvidia-smi", "-i", "3", "--query-gpu=uuid", "--format=csv,noheader,nounits"],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
    return result.stdout


def verify_gpu_identity(environ, *, driver_factory=DriverAPI, query=query_permitted_uuid):
    require(environ.get("CUDA_VISIBLE_DEVICES") == "3" and environ.get("CUDA_DEVICE_ORDER") == "PCI_BUS_ID",
            "CUDA_MASK_MISMATCH")
    try:
        expected = query().strip()
        require(re.fullmatch(r"GPU-[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", expected) is not None,
                "GPU_IDENTITY_MISMATCH")
        driver = driver_factory()
        require(driver.count() == 1, "GPU_IDENTITY_MISMATCH")
        require(driver.uuid().lower() == expected[4:].lower(), "GPU_IDENTITY_MISMATCH")
    except BootstrapError:
        raise
    except (OSError, AttributeError, ValueError, subprocess.SubprocessError):
        raise BootstrapError("GPU_IDENTITY_FAILED") from None


def run_native(expected_parent, status_fd, command, *, environ=None, probe=None, arm=None, execute=None):
    """Injected functions are for CPU tests; CLI has no option to bypass any check."""
    environ = os.environ if environ is None else environ
    probe = verify_gpu_identity if probe is None else probe
    arm = arm_parent_death if arm is None else arm
    execute = os.execve if execute is None else execute
    open_fd = True
    try:
        arm(expected_parent)
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        probe(environ)
        value = {"event": "GPU_IDENTITY_VERIFIED", "pid": os.getpid(),
                 "physical_gpu_index": 3, "logical_device": 0}
        data = (json.dumps(value, separators=(",", ":")) + "\n").encode()
        require(os.write(status_fd, data) == len(data), "BOOTSTRAP_STATUS_FAILED")
        os.close(status_fd)
        open_fd = False
        execute(command[0], command, environ)
        raise BootstrapError("NATIVE_EXEC_FAILED")  # successful exec never returns
    except Exception as error:
        if open_fd:
            code = str(error) if isinstance(error, BootstrapError) else "BOOTSTRAP_FAILED"
            data = (json.dumps({"event": "BOOTSTRAP_FAILED", "pid": os.getpid(), "code": code}) + "\n").encode()
            try:
                os.write(status_fd, data)
            except OSError:
                pass
        return 2
    finally:
        if open_fd:
            os.close(status_fd)


def main():
    # Arguments originate only from the fixed native launcher, never an HTTP body.
    if len(sys.argv) < 4:
        return 2
    try:
        return run_native(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3:])
    except Exception:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
