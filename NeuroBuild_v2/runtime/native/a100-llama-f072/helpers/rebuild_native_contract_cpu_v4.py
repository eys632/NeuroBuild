"""Rebuild only the reviewed CPU validator target for numeric diagnostics; no executable invocation."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import stat
import sys

ROOT = Path('/home/a202192020/NeuroBuild_v2')
ACTIVE = 'var/research/build_native_contract_cpu.py'
ACTIVE_SHA = '0f46ea1d2009d882077a5735aef17a62ad6cd9d327e5635c32081b7f82299510'
OLD_BUILDER_SHA = '054bee0e7442151ed5a62a804647d075b03b3b95d85a06e7531122bdacac77d2'
OLD_CPP_SHA = 'fb9c2873ee4040de3c63e621393c15cc8b88eb1358e288d3f6da8fd00f4e69ee'
ORIGINAL = ROOT / 'var/reports/llama-native-contract-cpu-build-v3.json'
ORIGINAL_LOG = ROOT / 'var/logs/llama-native-contract-cpu-build-v3.log'
IMMUTABLE = {
    'var/reports/llama-native-contract-cpu-build-v3.json': '8b1bb3639ef691ea0464965ead142743f743004f2fb7ac9200ad136752733b16',
    'var/logs/llama-native-contract-cpu-build-v3.log': 'f2945996844b9eb1748a6f7282d3523c792e0bbc7f7b798c7b36c7f940ce7cef',
    'var/reports/llama-native-contract-cpu-build-v2.json': 'ccb6a99305f9a62c1e2f9d1572380e428d20341a73f5dd65af4222f8b850aa36',
    'var/logs/llama-native-contract-cpu-build-v2.log': '86243521a8add3ff22fb1f2354d1aced4652a47ecb825a83e51e17e3cd2b8796',
    'var/reports/llama-native-contract-cpu-build.json': 'e85d4027ba0e01f14ff70e5a2b7325a916d46ef736a0401374b79801553910ad',
    'var/logs/llama-native-contract-cpu-build.log': 'bea58437fdb12008d805a174edd877d53fd7f0d58b2c6cfc6ffdbfece875c2bf',
    'var/runtime-build/llama-native-contract-cpu/CMakeCache.txt': 'f8c7d2c39cfa01c078b0eaeb618e6b0e91fa67f00771d4b1f9106f9b72909138',
    'var/runtime-build/llama-native-contract-cpu/compile_commands.json': '83051d57e1a71be7ebd18be8b97bd64e4d43bd4ff11e1cb532891b212a341aeb',
}
REPORT = ROOT / 'var/reports/llama-native-contract-cpu-build-v4.json'
LOG = ROOT / 'var/logs/llama-native-contract-cpu-build-v4.log'
TEMP = ROOT / 'var/tmp/llama-native-contract-cpu-v4'
STOP = False


def require(value, code):
    if not value:
        raise ValueError(code)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load_active():
    path = ROOT / ACTIVE
    require(not path.is_symlink() and digest(path) == ACTIVE_SHA, 'ACTIVE_CPU_BUILDER_CHANGED')
    spec = importlib.util.spec_from_file_location('fixed_cpu_builder', path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def validate_previous(original, cpu):
    require(original['kind'] == 'NATIVE_CONTRACT_CPU_BUILD' and original['status'] == 'COMPILE_PASS_NOT_EXECUTED'
            and original['source_pin'] == cpu.PIN and original['helper_sha256'] == OLD_BUILDER_SHA,
            'PREVIOUS_FAILURE_IDENTITY_MISMATCH')
    old_pins = dict(cpu.PINS)
    old_pins[ACTIVE] = '1e60456f429ea500657f2638a0ef525fc62823950fa7085ef891340785089506'
    old_pins['var/research/rebuild_native_contract_cpu.py'] = OLD_BUILDER_SHA
    old_pins['var/research/native-contract-validator/validator.cpp'] = OLD_CPP_SHA
    require(original['pinned_inputs'] == old_pins and original['settings'] == cpu.settings(),
            'PREVIOUS_FAILURE_INPUT_MISMATCH')
    require(original['build_path'] == str(cpu.BUILD.relative_to(ROOT))
            and original['cuda_visible_devices'] == '' and original['native_validator_executed'] is False
            and original['model_or_weights_loaded'] is False,
            'PREVIOUS_FAILURE_SCOPE_MISMATCH')
    phases = original['phases']
    require([p['name'] for p in phases] == ['rebuild-cpu-validator']
            and [p['exit_code'] for p in phases] == [0], 'PREVIOUS_FAILURE_PHASE_MISMATCH')
    require(all(p['native_cleanup']['cleanup_complete'] is True
                and p['native_cleanup']['native_reaped'] is True
                and p['guardian_shutdown']['child_reaped'] is True for p in phases),
            'PREVIOUS_FAILURE_CLEANUP_INCOMPLETE')


def check_immutable(builder):
    for relative, expected in IMMUTABLE.items():
        path = ROOT / relative
        builder.owned_path(path)
        require(path.is_file() and digest(path) == expected, 'FAILED_BUILD_EVIDENCE_CHANGED')


def object_inventory(builder, build):
    # Reuse only the unchanged upstream objects/static libraries; validator
    # object/binary may change and are outside this llama/ inventory.
    rows = []
    for path in sorted((build / 'llama').rglob('*')):
        if path.suffix not in ('.o', '.a'):
            continue
        builder.owned_path(path)
        info = path.lstat()
        require(stat.S_ISREG(info.st_mode), 'REUSED_OBJECT_NOT_REGULAR')
        rows.append([str(path.relative_to(build)), info.st_size, digest(path)])
    require(rows and any(row[0].endswith('.a') for row in rows), 'REUSED_STATIC_LIBRARIES_MISSING')
    return {'files': len(rows), 'bytes': sum(row[1] for row in rows),
            'inventory_sha256': hashlib.sha256(json.dumps(rows, separators=(',', ':')).encode()).hexdigest()}


def cancelled(*_):
    global STOP
    STOP = True


def main():
    require(len(sys.argv) == 1 and Path(sys.prefix) == ROOT / '.conda'
            and os.environ.get('CUDA_VISIBLE_DEVICES') == '', 'EXPLICIT_CPU_PROJECT_ENV_REQUIRED')
    cpu = load_active()
    builder = cpu.load_module('resume_guardian', 'var/research/run_llama_build.py')
    supervisor = cpu.load_module('resume_supervisor', 'var/research/relink_llama_rpath.py')
    verifier = cpu.load_module('resume_source_verifier', 'var/research/verify_llama_build.py')
    pinned = dict(cpu.PINS, **{ACTIVE: ACTIVE_SHA,
                             str(Path(__file__).absolute().relative_to(ROOT)): digest(Path(__file__))})
    for relative, expected in pinned.items():
        if relative.startswith('var/'):
            builder.owned_path(ROOT / relative)
        require(digest(ROOT / relative) == expected, 'CPU_INPUT_PIN_CHANGED')
    check_immutable(builder)
    original = json.loads(ORIGINAL.read_text())
    validate_previous(original, cpu)
    builder.owned_path(cpu.BUILD)
    require(cpu.BUILD.is_dir(), 'EXISTING_CPU_BUILD_MISSING')
    old_binary = cpu.BUILD / 'nb-native-contract-validator'
    builder.owned_path(old_binary)
    require(digest(old_binary) == original['binary_sha256'], 'PREVIOUS_CPU_BINARY_CHANGED')
    preserved = ROOT / 'var/research/native-contract-history/v3/nb-native-contract-validator'
    builder.owned_path(preserved)
    require(digest(preserved) == original['binary_sha256'], 'PREVIOUS_CPU_BINARY_NOT_PRESERVED')
    for path in (REPORT, LOG, TEMP):
        builder.owned_path(path, True)
        require(not path.exists() and not path.is_symlink(), 'RESUME_OUTPUT_EXISTS')
    options = cpu.settings()
    cache = cpu.validate_cache((cpu.BUILD / 'CMakeCache.txt').read_text(), options)
    commands = cpu.validate_commands(json.loads((cpu.BUILD / 'compile_commands.json').read_text()), builder.SOURCE)
    source_validator = verifier.load_bootstrap()
    verifier.ws_module = source_validator
    workspace = source_validator.Workspace()
    try:
        bootstrap_path = ROOT / source_validator.REPORT
        require(digest(bootstrap_path) == original['source_report_sha256'], 'BOOTSTRAP_REPORT_CHANGED')
        bootstrap = verifier.read_json(workspace, bootstrap_path)
        builder.verify_bootstrap(bootstrap)
        metadata = {}
        for name in ('commit.json', 'tree.json'):
            path = ROOT / source_validator.DOWNLOAD_DIR / name
            entry = next(row for row in bootstrap['downloads'] if row['path'] == str(path.relative_to(ROOT)))
            require(digest(path) == entry['sha256'], 'SOURCE_METADATA_CHANGED')
            metadata[name] = verifier.read_json(workspace, path)
        tree = source_validator.validate_tree(metadata['commit.json'], metadata['tree.json'])
        source_before = source_validator.verify_source(workspace, tree)
        require(source_before == bootstrap['source_verification'] == original['source_before_build'],
                'SOURCE_CHANGED_BEFORE_RESUME')
    finally:
        workspace.close()
    cmake = builder.TOOLS / 'bin/cmake'
    require(digest(cmake) == bootstrap['tool_identity']['sha256'] == original['cmake_binary_sha256'],
            'CMAKE_BINARY_CHANGED')
    reused_before = object_inventory(builder, cpu.BUILD)
    command = [str(cmake), '--build', str(cpu.BUILD), '--target', 'nb-native-contract-validator', '--parallel', '2']
    TEMP.mkdir(mode=0o700)
    builder.REPORT, builder.LOG, builder.TEMP = REPORT, LOG, TEMP
    builder.created_record = False
    env = builder.build_environment(os.environ)
    record = {'kind': 'NATIVE_CONTRACT_CPU_BUILD', 'status': 'RUNNING',
              'started_at_utc': datetime.now(timezone.utc).isoformat(), 'source_pin': cpu.PIN,
              'source_report_sha256': digest(bootstrap_path), 'source_before_build': source_before,
              'pinned_inputs': pinned, 'helper_sha256': digest(Path(__file__)),
              'cmake_binary_sha256': digest(cmake), 'settings': options,
              'cuda_visible_devices': '', 'gpu_queries_or_execution': 'NOT_REQUESTED',
              'native_validator_executed': False, 'model_or_weights_loaded': False,
              'build_path': str(cpu.BUILD.relative_to(ROOT)), 'phases': [],
              'disk_reserve_bytes': cpu.RESERVE, 'own_allocation_budget_bytes': cpu.BUDGET,
              'minimum_free_bytes': None, 'maximum_own_allocated_bytes': 0,
              'verified_cache_settings': cache, 'compile_verification': commands,
              'previous_build': {'immutable_inputs': IMMUTABLE, 'helper_sha256': OLD_BUILDER_SHA,
                                   'cpp_sha256': OLD_CPP_SHA,
                                   'cause': 'Retain exact parity failure; add only token counts and original-byte roundtrip booleans'},
              'resume_mode': 'same build directory; validator numeric diagnostics only; no reconfigure',
              'reused_upstream_objects_before': reused_before}
    builder.publish(record)
    builder.created_record = True
    previous = {sig: signal.signal(sig, cancelled) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        paths = [cpu.PROJECT, cpu.BUILD, TEMP, REPORT, LOG, builder.SOURCE, builder.TOOLS,
                 cpu.TEMP, ORIGINAL, ORIGINAL_LOG]
        with LOG.open('xb', buffering=0) as log:
            supervisor.run_phase(builder, name='rebuild-cpu-validator', command=command, env=env, log=log,
                                 record=record, phases=record['phases'], paths=paths,
                                 stop_requested=lambda: STOP, budget_bytes=cpu.BUDGET,
                                 reserve_bytes=cpu.RESERVE, max_seconds=1800)
        check_immutable(builder)
        require(object_inventory(builder, cpu.BUILD) == reused_before, 'REUSED_UPSTREAM_OBJECTS_CHANGED')
        workspace = source_validator.Workspace()
        try:
            source_after = source_validator.verify_source(workspace, tree)
        finally:
            workspace.close()
        require(source_after == source_before, 'SOURCE_CHANGED_DURING_RESUME')
        for relative, expected in pinned.items():
            require(digest(ROOT / relative) == expected, 'CPU_INPUT_CHANGED_DURING_RESUME')
        binary = cpu.BUILD / 'nb-native-contract-validator'
        builder.owned_path(binary)
        require(binary.is_file() and not binary.is_symlink(), 'CPU_VALIDATOR_BINARY_MISSING')
        record.update(status='COMPILE_PASS_NOT_EXECUTED', finished_at_utc=datetime.now(timezone.utc).isoformat(),
                      source_after_build=source_after, binary_path=str(binary.relative_to(ROOT)),
                      binary_bytes=binary.stat().st_size, binary_sha256=digest(binary),
                      compile_commands_sha256=digest(cpu.BUILD / 'compile_commands.json'),
                      cmake_cache_sha256=digest(cpu.BUILD / 'CMakeCache.txt'), log_sha256=digest(LOG),
                      reused_upstream_objects_after=reused_before, previous_build_unchanged=True,
                      next_gate='Static readelf dependency inspection before any CPU validator execution')
        builder.publish(record)
        print(json.dumps({'status': record['status'], 'report': str(REPORT.relative_to(ROOT)),
                          'binary_sha256': record['binary_sha256'], 'native_validator_executed': False}))
    except BaseException as error:
        record.update(status='FAILED', finished_at_utc=datetime.now(timezone.utc).isoformat(),
                      failure_type=type(error).__name__, failure=str(error),
                      previous_build_unchanged=all(digest(ROOT / path) == expected
                          for path, expected in IMMUTABLE.items()))
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
