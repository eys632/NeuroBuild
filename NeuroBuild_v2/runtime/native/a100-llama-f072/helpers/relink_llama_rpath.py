"""Prepared, explicitly invoked CPU-only RPATH relink; never run during compilation.

Source and original build report/log are immutable. Reuses the reviewed native
guardian and shared own-child shutdown implementation; no native binary runs.
"""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys
import subprocess
import time

ROOT = Path('/home/a202192020/NeuroBuild_v2')
BUILDER_SHA = 'e901372cc4f39dbee1e0574baf318fd2ae6edca167963f8bfe66274c06b8d52f'
REPORT = ROOT / 'var/reports/llama-rpath-relink.json'
LOG = ROOT / 'var/logs/llama-rpath-relink.log'
TEMP = ROOT / 'var/tmp/llama-rpath-relink'
STOP = False


def require(value, code):
    if not value:
        raise ValueError(code)


def module(name, relative, expected=None):
    path = ROOT / relative
    if expected is not None:
        require(hashlib.sha256(path.read_bytes()).hexdigest() == expected, 'HELPER_HASH_CHANGED')
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def now():
    return datetime.now(timezone.utc).isoformat()


def cancelled(*_):
    global STOP
    STOP = True


def object_identity(builder):
    rows = []
    for path in sorted(builder.BUILD.rglob('*.o')):
        builder.owned_path(path)
        require(path.is_file() and not path.is_symlink(), 'UNSAFE_OBJECT_FILE')
        rows.append([str(path.relative_to(builder.BUILD)), path.stat().st_size, builder.digest(path)])
    require(bool(rows), 'NO_COMPILED_OBJECTS')
    return {'count': len(rows), 'inventory_sha256': hashlib.sha256(
        json.dumps(rows, separators=(',', ':')).encode()).hexdigest()}


def choose_rpath(verifier, inventory):
    cache = verifier.loader_cache()
    records, missing_cuda = [], []
    for path in [verifier.BIN / 'llama-server', *(ROOT / row['path'] for row in inventory)]:
        info = verifier.elf(path)
        records.append({'path': str(path.relative_to(ROOT)), **info})
        for needed in info['needed']:
            if needed.startswith(('libcudart.', 'libcublas.', 'libcublasLt.')):
                if needed in cache:
                    verifier.system_path(cache[needed][0])
                else:
                    missing_cuda.append(needed)
            elif needed == 'libcuda.so.1':
                require(needed in cache, 'SYSTEM_DRIVER_NOT_IN_LOADER_CACHE')
                provider = verifier.system_path(cache[needed][0])
                require(provider.is_file(), 'REAL_SYSTEM_DRIVER_MISSING')
    require(any('' in value.split(':') for row in records for key in ('rpath', 'runpath') for value in row[key]),
            'ACTUAL_EMPTY_RPATH_NOT_PRESENT')
    rpath, fallback = '$ORIGIN', None
    if missing_cuda:
        directory = verifier.system_path(Path('/usr/local/cuda/targets/x86_64-linux/lib'))
        for name in set(missing_cuda):
            provider = verifier.system_path(directory / name)
            require(provider.is_file(), 'TOOLKIT_RUNTIME_PROVIDER_MISSING')
        fallback = str(directory)
        rpath += ';' + fallback
    return rpath, {'original_elf_objects': records, 'missing_cuda_cache_names': sorted(set(missing_cuda)),
                   'explicit_toolkit_fallback_directory': fallback,
                   'selection': 'Literal $ORIGIN; append only verified existing system toolkit directory if cache lacks a toolkit SONAME'}


def run_phase(builder, *, name, command, env, log, record, phases, paths, stop_requested,
              max_seconds=1800, reserve_bytes=None, budget_bytes=None, temp_dir=None):
    """Reusable CPU compiler supervision using already reviewed cleanup code.

    The caller pins the builder module, supplies explicit commands/output and
    publishes its own outer result. No native runtime executable is allowed by
    the callers' reviewed plans; this generic supervisor does not infer commands.
    """
    sys.path.insert(0, str(ROOT))
    from scripts.model_guard import peek_child_exit, stop_owned_child
    require(env.get('CUDA_VISIBLE_DEVICES') == '', 'CPU_PHASE_REQUIRES_EMPTY_CUDA_MASK')
    require(type(name) is str and name and all(c.isalnum() or c == '-' for c in name), 'INVALID_PHASE_NAME')
    require(type(command) is list and command and all(type(s) is str and s for s in command), 'INVALID_PHASE_COMMAND')
    reserve = builder.RESERVE if reserve_bytes is None else reserve_bytes
    budget = builder.BUDGET if budget_bytes is None else budget_bytes
    temporary = builder.TEMP if temp_dir is None else temp_dir
    require(type(reserve) is int and reserve >= 20 * 1024**3
            and type(budget) is int and budget > 0 and type(max_seconds) is int and 1 <= max_seconds <= 1800,
            'INVALID_CPU_PHASE_LIMITS')
    disk = os.statvfs(ROOT)
    free = disk.f_bavail * disk.f_frsize
    allocated = builder.allocation(paths)
    require(not stop_requested() and allocated <= budget
            and free >= reserve + max(0, budget - allocated), 'CPU_PHASE_INITIAL_DISK_OR_STOP')
    phase = {'name': name, 'command': command, 'started_at_utc': now(),
             'max_seconds': max_seconds, 'budget_bytes': budget, 'reserve_bytes': reserve}
    phases.append(phase)
    cleanup_path = temporary / ('guardian-' + name + '.json')
    child = subprocess.Popen([str(ROOT / '.conda/bin/python'), '-c', builder.BOOTSTRAP,
                              str(os.getpid()), str(cleanup_path), *command], cwd=ROOT, env=env,
                             stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                             start_new_session=True)
    phase['own_child_pid'] = child.pid
    started = time.monotonic()
    try:
        while not peek_child_exit(child):
            disk = os.statvfs(ROOT)
            free = disk.f_bavail * disk.f_frsize
            allocated = builder.allocation(paths)
            previous_min = record.get('minimum_free_bytes')
            record['minimum_free_bytes'] = free if previous_min is None else min(previous_min, free)
            record['maximum_own_allocated_bytes'] = max(record.get('maximum_own_allocated_bytes', 0), allocated)
            require(not stop_requested() and free >= reserve + 512 * 1024**2
                    and allocated <= budget and time.monotonic() - started <= max_seconds,
                    'CPU_PHASE_DISK_TIME_OR_STOP_LIMIT')
            builder.publish(record)
            time.sleep(2)
    finally:
        phase['guardian_shutdown'] = stop_owned_child(child, os.killpg, peek_child_exit, time.sleep, time.monotonic)
        phase['exit_code'] = child.returncode
        phase['finished_at_utc'] = now()
        cleanup = json.loads(cleanup_path.read_text())
        require(cleanup['guardian_pid'] == child.pid and cleanup['cleanup_complete'] is True
                and cleanup['native_reaped'] is True and phase['guardian_shutdown']['child_reaped'] is True,
                'CPU_PHASE_NATIVE_CLEANUP_UNCONFIRMED')
        phase['native_cleanup'] = cleanup
        builder.publish(record)
    require(child.returncode == 0, 'CPU_PHASE_FAILED')
    return phase


def main():
    global STOP
    require(len(sys.argv) == 1 and Path(sys.prefix) == ROOT / '.conda'
            and os.environ.get('CUDA_VISIBLE_DEVICES') == '', 'EXPLICIT_CPU_PROJECT_ENV_REQUIRED')
    builder = module('reviewed_native_builder', 'var/research/run_llama_build.py', BUILDER_SHA)
    verifier = module('postbuild_verifier', 'var/research/verify_llama_build.py')
    original_path = builder.REPORT
    builder.owned_path(original_path)
    original = json.loads(original_path.read_text())
    original_sha = builder.digest(original_path)
    require(original['status'] == 'COMPILE_PASS_NOT_RUNTIME_VALIDATED' and original['source_pin'] == builder.PIN,
            'ORIGINAL_COMPILE_INCOMPLETE')
    require([phase['name'] for phase in original['phases']] == ['configure', 'ggml-cuda', 'llama-server'],
            'ORIGINAL_PHASES_INCOMPLETE')
    require(all(phase['exit_code'] == 0 and phase['native_cleanup']['cleanup_complete'] is True
                and phase['native_cleanup']['native_reaped'] is True for phase in original['phases']),
            'ORIGINAL_CLEANUP_INCOMPLETE')
    require(original['helper_sha256'] == BUILDER_SHA and original['cuda_visible_devices'] == ''
            and original['gpu_queries_or_execution'] == 'NOT_REQUESTED', 'ORIGINAL_IDENTITY_MISMATCH')
    require(builder.digest(builder.BUILD / 'bin/llama-server') == original['binary_sha256'], 'ORIGINAL_BINARY_CHANGED')
    require(builder.digest(builder.BUILD / 'compile_commands.json') == original['compile_commands_sha256'],
            'ORIGINAL_COMPILE_COMMANDS_CHANGED')
    require(builder.digest(builder.LOG) == original['log_sha256'], 'ORIGINAL_LOG_CHANGED')
    for path in (REPORT, LOG, TEMP):
        builder.owned_path(path, True)
        require(not path.exists() and not path.is_symlink(), 'RELINK_OUTPUT_ALREADY_EXISTS')

    # Pure source verification before mutation; no network/bootstrap main runs.
    source_validator = verifier.load_bootstrap()
    verifier.ws_module = source_validator
    workspace = source_validator.Workspace()
    try:
        bootstrap = verifier.read_json(workspace, ROOT / source_validator.REPORT)
        require(builder.digest(ROOT / source_validator.REPORT) == original['bootstrap_report_sha256'],
                'BOOTSTRAP_REPORT_CHANGED')
        builder.verify_bootstrap(bootstrap)
        metadata = {}
        for name in ('commit.json', 'tree.json'):
            path = ROOT / source_validator.DOWNLOAD_DIR / name
            entry = next(row for row in bootstrap['downloads'] if row['path'] == str(path.relative_to(ROOT)))
            require(builder.digest(path) == entry['sha256'], 'SOURCE_METADATA_CHANGED')
            metadata[name] = verifier.read_json(workspace, path)
        tree = source_validator.validate_tree(metadata['commit.json'], metadata['tree.json'])
        source_before = source_validator.verify_source(workspace, tree)
        require(source_before == bootstrap['source_verification'], 'SOURCE_CHANGED_BEFORE_RELINK')
        inventory, aliases, _ = verifier.library_inventory(workspace)
        rpath, selection = choose_rpath(verifier, inventory)
    finally:
        workspace.close()
    objects_before = object_identity(builder)

    settings = dict(original['settings'], CMAKE_BUILD_WITH_INSTALL_RPATH='ON',
                    CMAKE_INSTALL_RPATH=rpath, CMAKE_INSTALL_RPATH_USE_LINK_PATH='OFF')
    cmake = builder.TOOLS / 'bin/cmake'
    require(builder.digest(cmake) == original['cmake_binary_sha256'], 'CMAKE_BINARY_CHANGED')
    configure = [str(cmake), '-S', str(builder.SOURCE), '-B', str(builder.BUILD), '-G', 'Unix Makefiles']
    configure += ['-D' + key + '=' + value for key, value in settings.items()]
    commands = [('reconfigure-rpath', configure),
                ('relink-server', [str(cmake), '--build', str(builder.BUILD), '--target', 'llama-server', '--parallel', '2'])]
    # Only in-memory output/temp bindings change; original module/source bytes do not.
    builder.REPORT, builder.LOG, builder.TEMP = REPORT, LOG, TEMP
    builder.created_record = False
    TEMP.mkdir(mode=0o700)
    paths = [builder.SOURCE, builder.TOOLS, builder.BUILD, TEMP, REPORT, LOG,
             ROOT / 'var/tmp/llama-f072-sm80-cu118', original_path, ROOT / 'var/logs/llama-cuda-build.log',
             ROOT / 'var/runtime-downloads' / ('llama-' + builder.PIN)]
    env = builder.build_environment(os.environ)
    record = dict(original)
    record.update(status='RPATH_RELINK_RUNNING', kind='LLAMA_SOURCE_IMMUTABLE_RPATH_RELINK',
                  original_compile_report_sha256=original_sha,
                  relink_started_at_utc=now(), relink_helper_sha256=builder.digest(Path(__file__).absolute()),
                  reused_guardian_helper_sha256=BUILDER_SHA,
                  shared_shutdown_module_sha256=builder.digest(ROOT / 'scripts/model_guard.py'),
                  verifier_helper_sha256=builder.digest(ROOT / 'var/research/verify_llama_build.py'),
                  original_runtime_dependencies=inventory, original_runtime_dependency_symlinks=aliases,
                  source_before_relink=source_before, object_inventory_before=objects_before,
                  settings=settings, rpath_selection=selection, relink_phases=[])
    builder.publish(record)
    builder.created_record = True
    previous = {sig: signal.signal(sig, cancelled) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        with LOG.open('xb', buffering=0) as log:
            for name, command in commands:
                run_phase(builder, name=name, command=command, env=env, log=log, record=record,
                          phases=record['relink_phases'], paths=paths, stop_requested=lambda: STOP)
        require(builder.digest(original_path) == original_sha, 'ORIGINAL_REPORT_CHANGED')
        require(builder.digest(ROOT / 'var/logs/llama-cuda-build.log') == original['log_sha256'], 'ORIGINAL_LOG_CHANGED')
        require(builder.digest(builder.BUILD / 'compile_commands.json') == original['compile_commands_sha256'],
                'RELINK_CHANGED_COMPILATION_COMMANDS')
        objects_after = object_identity(builder)
        require(objects_after == objects_before, 'RELINK_CHANGED_OBJECT_BYTES')
        record.update(status='COMPILE_PASS_NOT_RUNTIME_VALIDATED', relink_finished_at_utc=now(),
                      object_inventory_after=objects_after, log_sha256=builder.digest(LOG),
                      binary_sha256=builder.digest(builder.BUILD / 'bin/llama-server'))
        builder.publish(record)
        print(json.dumps({'status': record['status'], 'report': str(REPORT.relative_to(ROOT)),
                          'rpath': rpath, 'native_binary_executed': False}))
    except BaseException as error:
        record.update(status='FAILED', relink_finished_at_utc=now(), relink_failure_type=type(error).__name__)
        builder.publish(record)
        raise
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'status': 'FAILED', 'error_type': type(error).__name__, 'error': str(error)}))
        raise SystemExit(1)
