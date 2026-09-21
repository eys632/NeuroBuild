#!/usr/bin/env python3
"""Bounded, CPU-only compilation of the verified native runtime source."""
from pathlib import Path
import hashlib
import json
import os
import signal
import stat
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path('/home/a202192020/NeuroBuild_v2')
PIN = 'f072b103714dfa1eee531f80b24512faf38e3dd2'
SOURCE = ROOT / 'var/runtime-src' / ('llama.cpp-' + PIN)
TOOLS = ROOT / 'var/tools/cmake-3.23.5-linux-x86_64'
BUILD = ROOT / 'var/runtime-build/llama-f072-sm80-cu118'
TEMP = ROOT / 'var/tmp/llama-f072-sm80-cu118'
REPORT = ROOT / 'var/reports/llama-cuda-build.json'
LOG = ROOT / 'var/logs/llama-cuda-build.log'
RESERVE = 20 * 1024**3
BUDGET = 6 * 1024**3
stop = False
created_record = False

def now():
    return datetime.now(timezone.utc).isoformat()

def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def owned_path(path, allow_missing=False):
    assert path.is_relative_to(ROOT / 'var')
    for part in (path, *path.parents):
        if part == ROOT:
            break
        if allow_missing and not part.exists() and not part.is_symlink():
            continue
        info = part.lstat()
        assert info.st_uid == os.getuid() and not stat.S_ISLNK(info.st_mode), str(part)

def allocation(paths):
    total, seen = 0, set()
    for base in paths:
        if not base.exists():
            continue
        for p in (base, *base.rglob('*')):
            s = p.lstat()
            k = (s.st_dev, s.st_ino)
            if k not in seen:
                total += s.st_blocks * 512
                seen.add(k)
    return total

def publish(record):
    tmp = REPORT.with_suffix('.json.tmp')
    with tmp.open('x') as f:
        json.dump(record, f, indent=2, allow_nan=False)
        f.write('\n')
    try:
        if created_record:
            os.replace(tmp, REPORT)
        else:
            os.link(tmp, REPORT)  # Initial publication never overwrites a raced-in report.
    finally:
        tmp.unlink(missing_ok=True)

def cancelled(*_):
    global stop
    stop = True

BOOTSTRAP = r'''import ctypes,json,os,signal,subprocess,sys,time
expected_parent=int(sys.argv[1])
report_path=sys.argv[2]
command=sys.argv[3:]
stopping=False
native=None
record={'guardian_pid':os.getpid(),'native_pid':None,'term_sent':False,
        'kill_sent':False,'native_reaped':False,'cleanup_complete':False}
def request_stop(*_):
    global stopping
    stopping=True
def exited(child):
    return os.waitid(os.P_PID,child.pid,os.WEXITED|os.WNOHANG|os.WNOWAIT) is not None
signal.signal(signal.SIGTERM,request_stop)
signal.signal(signal.SIGINT,request_stop)
fd=os.open(report_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
exit_code=1
try:
    if ctypes.CDLL(None,use_errno=True).prctl(1,signal.SIGTERM,0,0,0)!=0:
        raise RuntimeError('PDEATH_FAILED')
    if os.getppid()!=expected_parent:
        stopping=True
    if not stopping:
        native=subprocess.Popen(command,stdin=subprocess.DEVNULL,start_new_session=True)
        record['native_pid']=native.pid
        while not stopping and not exited(native):
            time.sleep(.05)
    exit_code=143 if stopping else 0
except Exception as error:
    record['failure_type']=type(error).__name__
    exit_code=1
finally:
    try:
        if native is not None:
            # Native leader remains unreaped, so its own PG identity is anchored.
            try:
                os.killpg(native.pid,signal.SIGTERM);record['term_sent']=True
            except ProcessLookupError:
                pass
            deadline=time.monotonic()+.5
            while not exited(native) and time.monotonic()<deadline:
                time.sleep(.05)
            try:
                os.killpg(native.pid,signal.SIGKILL);record['kill_sent']=True
            except ProcessLookupError:
                pass
            record['native_exit_code']=native.wait(timeout=1)
            record['native_reaped']=True
            if not stopping:
                code=record['native_exit_code']
                exit_code=code if code>=0 else 128-code
        record['cleanup_complete']=True
    except Exception as error:
        record['cleanup_failure_type']=type(error).__name__
        exit_code=1
    record['stop_requested']=stopping
    with os.fdopen(fd,'w') as stream:
        json.dump(record,stream,allow_nan=False);stream.write('\n');stream.flush();os.fsync(stream.fileno())
raise SystemExit(exit_code)
'''

def verify_bootstrap(evidence):
    assert evidence['kind'] == 'LLAMA_SOURCE_TOOL_BOOTSTRAP'
    assert evidence['status'] == 'PASS' and evidence['llama_commit'] == PIN
    assert evidence['source_path'] == str(SOURCE.relative_to(ROOT))
    assert evidence['tool_path'] == str(TOOLS.relative_to(ROOT))
    source = evidence['source_verification']
    for key, value in {'verified_blobs': 3607, 'verified_blob_bytes': 172243701,
                       'extra_or_missing_paths': 0}.items():
        assert type(source[key]) is int and source[key] == value
    assert all(evidence[key] is True for key in ('no_build', 'no_weights', 'no_gpu_calls', 'no_tool_execution'))
    expected_path = 'var/runtime-downloads/llama-' + PIN + '/cmake-3.23.5-linux-x86_64.tar.gz'
    downloads = [item for item in evidence['downloads'] if item['path'] == expected_path]
    assert len(downloads) == 1
    assert downloads[0]['bytes'] == 46031464
    assert downloads[0]['sha256'] == 'bbd7ad93d2a14ed3608021a9466ae63db76a24efd1fae7a5f7798c1de7ab9344'
    assert downloads[0]['url'] == 'https://github.com/Kitware/CMake/releases/download/v3.23.5/cmake-3.23.5-linux-x86_64.tar.gz'


def build_environment(environ):
    env = dict(environ)
    for key in tuple(env):
        if key.startswith(('CMAKE_', 'GGML_', 'LLAMA_', 'VLLM_', 'TORCH_', 'NCCL_', 'NVCC_', 'GIT_')) or key in (
            'LD_PRELOAD', 'LD_LIBRARY_PATH', 'PYTHONHOME', 'PYTHONPATH', 'CUDACXX',
            'CUDAHOSTCXX', 'CC', 'CXX', 'CFLAGS', 'CXXFLAGS', 'CPPFLAGS', 'LDFLAGS',
            'MAKEFLAGS', 'MFLAGS', 'GNUMAKEFLAGS', 'CUDAARCHS', 'CPATH', 'C_INCLUDE_PATH',
            'CPLUS_INCLUDE_PATH', 'LIBRARY_PATH', 'GCC_EXEC_PREFIX', 'COMPILER_PATH',
            'ENV', 'BASH_ENV'):
            env.pop(key, None)
    env.update(CUDA_VISIBLE_DEVICES='', CUDA_DEVICE_ORDER='PCI_BUS_ID',
               TMPDIR=str(TEMP), PYTHONNOUSERSITE='1',
               GIT_CEILING_DIRECTORIES=str(SOURCE.parent),
               PATH=str(TOOLS / 'bin') + ':/usr/local/bin:/usr/bin:/bin')
    return env


def main():
    global created_record
    assert Path(sys.executable).resolve().is_relative_to(ROOT / '.conda')
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == ''
    bootstrap = ROOT / 'var/reports/llama-source-bootstrap.json'
    owned_path(bootstrap)
    evidence = json.loads(bootstrap.read_text())
    # Root verifies the source tree once; this stage binds that exact evidence.
    verify_bootstrap(evidence)
    assert SOURCE.is_dir()
    for path in (SOURCE, TOOLS, REPORT.parent, LOG.parent):
        owned_path(path)
    for path in (BUILD, TEMP, REPORT, LOG):
        owned_path(path, True)
        assert not path.exists() and not path.is_symlink(), str(path)
    BUILD.mkdir(parents=True)
    TEMP.mkdir(parents=True)
    cmake = TOOLS / 'bin/cmake'
    assert digest(cmake) == '055306bf4b381456c172226eed0f6f3392e863293d471a71fcdafe211cd7384e'
    env = build_environment(os.environ)
    settings = {
        # The verified source archive has no upstream Git history. Number zero
        # is explicit; the exact pin must never become the enclosing app HEAD.
        'LLAMA_BUILD_NUMBER': '0', 'LLAMA_BUILD_COMMIT': PIN,
        'CMAKE_BUILD_TYPE': 'Release', 'CMAKE_EXPORT_COMPILE_COMMANDS': 'ON',
        'CMAKE_C_COMPILER': '/usr/local/bin/gcc',
        'CMAKE_CXX_COMPILER': '/usr/local/bin/g++',
        'CMAKE_CUDA_COMPILER': '/usr/local/cuda/bin/nvcc',
        'CMAKE_CUDA_HOST_COMPILER': '/usr/local/bin/g++',
        'CUDAToolkit_ROOT': '/usr/local/cuda', 'CMAKE_CUDA_ARCHITECTURES': '80-real',
        'GGML_CUDA': 'ON', 'GGML_NATIVE': 'OFF', 'GGML_CCACHE': 'OFF', 'GGML_LTO': 'OFF',
        'GGML_CUDA_CUB_3DOT2': 'OFF', 'GGML_CUDA_NCCL': 'OFF', 'GGML_CUDA_GRAPHS': 'OFF',
        'GGML_CUDA_FORCE_CUBLAS': 'OFF', 'GGML_CUDA_FORCE_MMQ': 'OFF',
        'GGML_BLAS': 'OFF', 'GGML_OPENMP': 'OFF', 'GGML_OPENMP_FETCH': 'OFF',
        'GGML_CPU_KLEIDIAI': 'OFF', 'GGML_LLAMAFILE': 'OFF', 'GGML_BACKEND_DL': 'OFF',
        'LLAMA_BUILD_COMMON': 'ON', 'LLAMA_BUILD_TOOLS': 'ON', 'LLAMA_BUILD_SERVER': 'ON',
        'LLAMA_BUILD_TESTS': 'OFF', 'LLAMA_BUILD_EXAMPLES': 'OFF', 'LLAMA_BUILD_APP': 'OFF',
        'LLAMA_BUILD_UI': 'OFF', 'LLAMA_USE_PREBUILT_UI': 'OFF',
        'LLAMA_OPENSSL': 'OFF', 'LLAMA_BUILD_BORINGSSL': 'OFF', 'LLAMA_BUILD_LIBRESSL': 'OFF',
        'LLAMA_LLGUIDANCE': 'OFF', 'LLAMA_SUBPROCESS': 'OFF',
        'FETCHCONTENT_FULLY_DISCONNECTED': 'ON', 'FETCHCONTENT_UPDATES_DISCONNECTED': 'ON',
    }
    configure = [str(cmake), '-S', str(SOURCE), '-B', str(BUILD), '-G', 'Unix Makefiles']
    configure.extend('-D' + k + '=' + v for k, v in settings.items())
    commands = [('configure', configure)]
    for target in ('ggml-cuda', 'llama-server'):
        commands.append((target, [str(cmake), '--build', str(BUILD), '--target', target, '--parallel', '2']))
    paths = [SOURCE, TOOLS, BUILD, TEMP, LOG, REPORT, ROOT / 'var/runtime-downloads' / ('llama-' + PIN)]
    record = {'status': 'RUNNING', 'started_at_utc': now(), 'source_pin': PIN,
              'bootstrap_report_sha256': digest(bootstrap), 'cmake_binary_sha256': digest(cmake),
              'helper_sha256': digest(Path(__file__)), 'cuda_visible_devices': '', 'settings': settings,
              'disk_reserve_bytes': RESERVE, 'own_allocation_budget_bytes': BUDGET,
              'gpu_queries_or_execution': 'NOT_REQUESTED', 'model_weights_downloaded': False,
              'phases': [], 'minimum_free_bytes': None, 'maximum_own_allocated_bytes': 0}
    publish(record)
    created_record = True
    signal.signal(signal.SIGTERM, cancelled)
    signal.signal(signal.SIGINT, cancelled)
    with LOG.open('xb', buffering=0) as log:
        for name, command in commands:
            initial = os.statvfs(ROOT)
            initial_free = initial.f_bavail * initial.f_frsize
            initial_used = allocation(paths)
            if stop or initial_used > BUDGET or initial_free < RESERVE + max(0, BUDGET - initial_used):
                raise RuntimeError('PRE_PHASE_DISK_OR_STOP_BUDGET')
            phase = {'name': name, 'command': command, 'started_at_utc': now()}
            record['phases'].append(phase)
            guardian_report = TEMP / ('guardian-' + name + '.json')
            child = subprocess.Popen([str(ROOT / '.conda/bin/python'), '-c', BOOTSTRAP, str(os.getpid()), str(guardian_report), *command],
                                     cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                     stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            phase['own_child_pid'] = child.pid
            phase['own_child_role'] = 'build_guardian'
            phase['guardian_report'] = str(guardian_report)
            started = time.monotonic()
            try:
                while True:
                    s = os.statvfs(ROOT)
                    free = s.f_bavail * s.f_frsize
                    used = allocation(paths)
                    record['minimum_free_bytes'] = free if record['minimum_free_bytes'] is None else min(record['minimum_free_bytes'], free)
                    record['maximum_own_allocated_bytes'] = max(record['maximum_own_allocated_bytes'], used)
                    reason = ('STOP_REQUESTED' if stop else 'DISK_RESERVE' if free < RESERVE + 512 * 1024**2
                              else 'BUILD_ALLOCATION_BUDGET' if used > BUDGET else 'TIME_LIMIT'
                              if time.monotonic() - started > 10800 else None)
                    if reason:
                        phase['failure_reason'] = reason
                        raise RuntimeError(reason)
                    exited = os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
                    if exited is not None:
                        break
                    publish(record)
                    time.sleep(2)
            finally:
                # Guardian owns a separate native process group and needs time
                # to terminate/reap it before we escalate against the guardian.
                # Retain this direct leader too until all group signals finish.
                phase['guardian_shutdown'] = {'term_sent': False, 'kill_sent': False, 'reaped': False}
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                    phase['guardian_shutdown']['term_sent'] = True
                except ProcessLookupError:
                    pass
                deadline = time.monotonic() + 3
                while (os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is None
                       and time.monotonic() < deadline):
                    time.sleep(.05)
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                    phase['guardian_shutdown']['kill_sent'] = True
                except ProcessLookupError:
                    pass
                phase['exit_code'] = child.wait(timeout=10)
                phase['guardian_shutdown']['reaped'] = True
                phase['finished_at_utc'] = now()
                try:
                    cleanup = json.loads(guardian_report.read_text())
                    assert cleanup['guardian_pid'] == child.pid
                    assert cleanup['cleanup_complete'] is True
                    assert cleanup['native_pid'] is None or cleanup['native_reaped'] is True
                    phase['native_cleanup'] = cleanup
                except (OSError, ValueError, KeyError, AssertionError):
                    phase['failure_reason'] = 'NATIVE_CLEANUP_UNCONFIRMED'
                    publish(record)
                    raise RuntimeError('NATIVE_CLEANUP_UNCONFIRMED') from None
                publish(record)
            if phase['exit_code'] != 0:
                raise RuntimeError('BUILD_PHASE_FAILED:' + name)
    record.update(status='COMPILE_PASS_NOT_RUNTIME_VALIDATED', finished_at_utc=now(),
                  log_sha256=digest(LOG), binary_sha256=digest(BUILD / 'bin/llama-server'),
                  compile_commands_sha256=digest(BUILD / 'compile_commands.json'))
    publish(record)
    print(json.dumps({'status': record['status'], 'report': str(REPORT)}), flush=True)

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        if created_record and REPORT.exists():
            r = json.loads(REPORT.read_text())
            r.update(status='FAILED', finished_at_utc=now(), failure=type(error).__name__ + ':' + str(error))
            publish(r)
        print(json.dumps({'status': 'FAILED', 'error': type(error).__name__ + ':' + str(error)}), flush=True)
        raise SystemExit(1)
