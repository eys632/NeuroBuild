"""Prepared CPU-only validator compilation. No validator/native/model execution."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import signal
import sys

ROOT = Path('/home/a202192020/NeuroBuild_v2')
PIN = 'f072b103714dfa1eee531f80b24512faf38e3dd2'
PROJECT = ROOT / 'var/research/native-contract-validator'
BUILD = ROOT / 'var/runtime-build/llama-native-contract-cpu'
TEMP = ROOT / 'var/tmp/llama-native-contract-cpu'
REPORT = ROOT / 'var/reports/llama-native-contract-cpu-build.json'
LOG = ROOT / 'var/logs/llama-native-contract-cpu-build.log'
RESERVE, BUDGET = 20 * 1024**3, 3 * 1024**3
PINS = {
    'var/research/run_llama_build.py': 'e901372cc4f39dbee1e0574baf318fd2ae6edca167963f8bfe66274c06b8d52f',
    'var/research/relink_llama_rpath.py': '52ab2e85128c1ff8fff978017aa7225268615d31ba653cdf20bb1c7f202333e0',
    'var/research/verify_llama_build.py': '81285c40d1ee3862f747bbbc32fc9868d7a0604b4ea402dc8a8b5e9a1a06573e',
    'scripts/model_guard.py': 'cc95f6cccf9ca5b749bea2fc8c82d2af9d56d55b94a6aee947379b3a2f4de528',
    'var/research/native-contract-validator/CMakeLists.txt': '9dede1e5ac9ee2f9b46f81e655e801e1b3ac2a57132dece6291cd9bb5f9860b5',
    'var/research/native-contract-validator/validator.cpp': '92ed10acd9be33d02d4cc6ea446dc2bea93ffb60b7d17ffc3c0f0268aab6c6b2',
}
BACKENDS_OFF = ('BLAS', 'CANN', 'CUDA', 'ET', 'ET_SYSEMU', 'HIP', 'METAL', 'MUSA', 'RPC',
                'VIRTGPU', 'VIRTGPU_BACKEND', 'SYCL', 'VULKAN', 'WEBGPU', 'ZDNN', 'OPENCL',
                'HEXAGON', 'ZENDNN', 'OPENVINO', 'ACCELERATE', 'CPU_KLEIDIAI', 'CPU_HBM',
                'OPENMP', 'OPENMP_FETCH', 'CPU_ALL_VARIANTS', 'NATIVE', 'CCACHE', 'LTO', 'LLAMAFILE')
STOP = False


def require(condition, code):
    if not condition:
        raise ValueError(code)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load_module(name, relative):
    path = ROOT / relative
    require(digest(path) == PINS[relative], 'PINNED_HELPER_CHANGED')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def settings():
    result = {'CMAKE_BUILD_TYPE': 'Release', 'CMAKE_EXPORT_COMPILE_COMMANDS': 'ON',
              'CMAKE_C_COMPILER': '/usr/local/bin/gcc', 'CMAKE_CXX_COMPILER': '/usr/local/bin/g++',
              'BUILD_SHARED_LIBS': 'OFF', 'GGML_BACKEND_DL': 'OFF', 'GGML_CPU': 'ON',
              'LLAMA_BUILD_COMMIT': PIN, 'LLAMA_BUILD_NUMBER': '0',
              'LLAMA_BUILD_COMMON': 'ON', 'LLAMA_BUILD_TOOLS': 'ON', 'LLAMA_BUILD_SERVER': 'ON',
              'FETCHCONTENT_FULLY_DISCONNECTED': 'ON', 'FETCHCONTENT_UPDATES_DISCONNECTED': 'ON'}
    result.update({'GGML_' + name: 'OFF' for name in BACKENDS_OFF})
    result.update({'LLAMA_' + name: 'OFF' for name in (
        'BUILD_TESTS', 'BUILD_EXAMPLES', 'BUILD_APP', 'BUILD_UI', 'USE_PREBUILT_UI',
        'OPENSSL', 'SUBPROCESS', 'LLGUIDANCE', 'TOOLS_INSTALL', 'TESTS_INSTALL')})
    return result


def validate_cache(text, expected):
    cache = {}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith(('#', '//')):
            continue
        match = re.fullmatch(r'([^:=\r\n]+):(BOOL|FILEPATH|PATH|STRING|INTERNAL|STATIC|UNINITIALIZED)=(.*)', line)
        require(match is not None and match[1] == match[1].strip(), 'MALFORMED_CMAKE_CACHE_LINE')
        key, _, value = match.groups()
        require(key not in cache, 'DUPLICATE_CMAKE_CACHE_KEY')
        cache[key] = value
    for key, value in expected.items():
        require(cache.get(key) == value, 'CPU_CACHE_MISMATCH:' + key)
    require('CMAKE_CUDA_COMPILER' not in cache and 'CMAKE_HIP_COMPILER' not in cache,
            'GPU_COMPILER_CONFIGURED')
    return {key: cache[key] for key in expected}


def validate_commands(commands, source):
    require(type(commands) is list and 0 < len(commands) <= 10000, 'INVALID_CPU_COMPILE_COMMANDS')
    for entry in commands:
        path = Path(entry['file'])
        require(path.is_relative_to(source) or path.is_relative_to(PROJECT) or path.is_relative_to(BUILD),
                'CPU_COMPILE_SOURCE_ESCAPE')
        require(path.suffix in ('.c', '.cpp', '.cc', '.cxx', '.S', '.s'), 'NON_CPU_COMPILE_SOURCE')
        args = shlex.split(entry['command'])
        require(args[0] in ('/usr/local/bin/gcc', '/usr/local/bin/g++')
                and not any(arg.startswith('@') for arg in args), 'CPU_COMPILER_MISMATCH')
        require(not any(arg.startswith(('--generate-code', '-gencode', '--cuda', '-DGGML_USE_CUDA',
                                        '-DGGML_USE_HIP', '-DGGML_USE_VULKAN', '-DGGML_USE_SYCL'))
                        for arg in args), 'GPU_COMPILER_FLAG_PRESENT')
        require(Path(entry['directory']).is_relative_to(BUILD), 'CPU_COMPILE_WORKDIR_ESCAPE')
    return {'total_compile_commands': len(commands), 'cuda_compile_commands': 0,
            'allowed_compilers': ['/usr/local/bin/gcc', '/usr/local/bin/g++']}


def cancelled(*_):
    global STOP
    STOP = True


def main():
    require(len(sys.argv) == 1 and Path(sys.prefix) == ROOT / '.conda'
            and os.environ.get('CUDA_VISIBLE_DEVICES') == '', 'EXPLICIT_CPU_PROJECT_ENV_REQUIRED')
    builder = load_module('pinned_compiler_guardian', 'var/research/run_llama_build.py')
    supervisor = load_module('pinned_cpu_supervision', 'var/research/relink_llama_rpath.py')
    verifier = load_module('pinned_source_verification', 'var/research/verify_llama_build.py')
    for name, expected in PINS.items():
        builder.owned_path(ROOT / name) if name.startswith('var/') else None
        require(digest(ROOT / name) == expected, 'CPU_INPUT_PIN_CHANGED')
    for path in (BUILD, TEMP, REPORT, LOG):
        builder.owned_path(path, True)
        require(not path.exists() and not path.is_symlink(), 'CPU_BUILD_OUTPUT_EXISTS')
    source_validator = verifier.load_bootstrap()
    verifier.ws_module = source_validator
    workspace = source_validator.Workspace()
    try:
        bootstrap_path = ROOT / source_validator.REPORT
        bootstrap = verifier.read_json(workspace, bootstrap_path)
        builder.verify_bootstrap(bootstrap)
        metadata = {}
        for name in ('commit.json', 'tree.json'):
            path = ROOT / source_validator.DOWNLOAD_DIR / name
            evidence = next(row for row in bootstrap['downloads'] if row['path'] == str(path.relative_to(ROOT)))
            require(digest(path) == evidence['sha256'], 'SOURCE_METADATA_CHANGED')
            metadata[name] = verifier.read_json(workspace, path)
        tree = source_validator.validate_tree(metadata['commit.json'], metadata['tree.json'])
        source_before = source_validator.verify_source(workspace, tree)
        require(source_before == bootstrap['source_verification'], 'CPU_SOURCE_CHANGED_BEFORE_BUILD')
    finally:
        workspace.close()
    cmake = builder.TOOLS / 'bin/cmake'
    require(digest(cmake) == bootstrap['tool_identity']['sha256'], 'CPU_CMAKE_BINARY_CHANGED')
    BUILD.mkdir(mode=0o700)
    TEMP.mkdir(mode=0o700)
    builder.REPORT, builder.LOG, builder.TEMP = REPORT, LOG, TEMP
    builder.created_record = False
    env = builder.build_environment(os.environ)
    options = settings()
    configure = [str(cmake), '-S', str(PROJECT), '-B', str(BUILD), '-G', 'Unix Makefiles']
    configure += ['-D' + key + '=' + value for key, value in options.items()]
    target = [str(cmake), '--build', str(BUILD), '--target', 'nb-native-contract-validator', '--parallel', '2']
    paths = [PROJECT, BUILD, TEMP, REPORT, LOG, builder.SOURCE, builder.TOOLS]
    record = {'kind': 'NATIVE_CONTRACT_CPU_BUILD', 'status': 'RUNNING',
              'started_at_utc': datetime.now(timezone.utc).isoformat(), 'source_pin': PIN,
              'source_report_sha256': digest(bootstrap_path), 'source_before_build': source_before,
              'pinned_inputs': PINS, 'helper_sha256': digest(Path(__file__).absolute()),
              'cmake_binary_sha256': digest(cmake), 'settings': options,
              'cuda_visible_devices': '', 'gpu_queries_or_execution': 'NOT_REQUESTED',
              'native_validator_executed': False, 'model_or_weights_loaded': False,
              'build_path': str(BUILD.relative_to(ROOT)), 'phases': [],
              'disk_reserve_bytes': RESERVE, 'own_allocation_budget_bytes': BUDGET,
              'minimum_free_bytes': None, 'maximum_own_allocated_bytes': 0}
    builder.publish(record)
    builder.created_record = True
    previous = {sig: signal.signal(sig, cancelled) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        with LOG.open('xb', buffering=0) as log:
            for name, command in [('configure-cpu', configure), ('build-cpu-validator', target)]:
                supervisor.run_phase(builder, name=name, command=command, env=env, log=log, record=record,
                                     phases=record['phases'], paths=paths, stop_requested=lambda: STOP,
                                     budget_bytes=BUDGET, reserve_bytes=RESERVE, max_seconds=1800)
                record['verified_cache_settings'] = validate_cache((BUILD / 'CMakeCache.txt').read_text(), options)
                record['compile_verification'] = validate_commands(
                    json.loads((BUILD / 'compile_commands.json').read_text()), builder.SOURCE)
                builder.publish(record)
        workspace = source_validator.Workspace()
        try:
            source_after = source_validator.verify_source(workspace, tree)
        finally:
            workspace.close()
        require(source_after == source_before, 'CPU_SOURCE_CHANGED_DURING_BUILD')
        for name, expected in PINS.items():
            require(digest(ROOT / name) == expected, 'CPU_INPUT_CHANGED_DURING_BUILD')
        binary = BUILD / 'nb-native-contract-validator'
        builder.owned_path(binary)
        require(binary.is_file() and not binary.is_symlink(), 'CPU_VALIDATOR_BINARY_MISSING')
        record.update(status='COMPILE_PASS_NOT_EXECUTED', finished_at_utc=datetime.now(timezone.utc).isoformat(),
                      source_after_build=source_after, binary_path=str(binary.relative_to(ROOT)),
                      binary_bytes=binary.stat().st_size, binary_sha256=digest(binary),
                      compile_commands_sha256=digest(BUILD / 'compile_commands.json'),
                      cmake_cache_sha256=digest(BUILD / 'CMakeCache.txt'), log_sha256=digest(LOG),
                      next_gate='Parent readelf dependency/CPU-only verification before any validator execution')
        builder.publish(record)
        print(json.dumps({'status': record['status'], 'report': str(REPORT.relative_to(ROOT)),
                          'binary_sha256': record['binary_sha256'], 'native_validator_executed': False}))
    except BaseException as error:
        record.update(status='FAILED', finished_at_utc=datetime.now(timezone.utc).isoformat(),
                      failure_type=type(error).__name__, failure=str(error))
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
