"""Pure cache parser regressions. No helper main, subprocess, build or GPU."""
import ast
from hashlib import sha256
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def module(name, relative):
    path = ROOT / relative
    ast.parse(path.read_text())
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


verifier = module('postcompile_cache_subject', 'var/research/verify_llama_build.py')
cpu = module('cpu_cache_subject', 'var/research/build_native_contract_cpu.py')
parsers = [('postcompile', verifier.parse_cmake_cache),
           ('cpu', lambda text: cpu.validate_cache(text, {}))]
valid = '# CMake generated cache\n\n// explicit build number\nLLAMA_BUILD_NUMBER:UNINITIALIZED=0\n\n' \
        '  # comment containing FOO:STRING=ignored\n\t// another comment\n' \
        'CMAKE_INSTALL_RPATH:STRING=$ORIGIN\nEMPTY:STRING=\nBOOL:BOOL=OFF\n' \
        'F:FILEPATH=/usr/local/bin/g++\nP:PATH=/usr/local\nI:INTERNAL=1\nS:STATIC=x=y\n'
expected = {'LLAMA_BUILD_NUMBER': '0', 'CMAKE_INSTALL_RPATH': '$ORIGIN', 'EMPTY': '',
            'BOOL': 'OFF', 'F': '/usr/local/bin/g++', 'P': '/usr/local', 'I': '1', 'S': 'x=y'}
assert verifier.parse_cmake_cache(valid) == expected
assert cpu.validate_cache(valid, expected) == expected
checks = [{'case': 'blank_comments_uninitialized_all_types', 'status': 'PASS'}]
invalid = {
    'duplicate': 'X:BOOL=OFF\nX:BOOL=ON\n',
    'duplicate_across_type': 'X:BOOL=OFF\nX:INTERNAL=OFF\n',
    'multiline_key': 'SHOULD_NOT_JOIN\nX:STRING=value\n',
    'multiline_type': 'X:STR\nING=value\n',
    'bad_type': 'X:UNKNOWN=value\n',
    'leading_key_space': ' X:STRING=value\n',
}
for label, parser in parsers:
    for case, text in invalid.items():
        try:
            parser(text)
        except ValueError:
            checks.append({'parser': label, 'case': case, 'status': 'PASS'})
        else:
            raise AssertionError((label, case))
actual = ROOT / 'var/runtime-build/llama-f072-sm80-cu118/CMakeCache.txt'
parsed = verifier.parse_cmake_cache(actual.read_text())
assert parsed['LLAMA_BUILD_NUMBER'] == '0'
assert parsed['LLAMA_BUILD_COMMIT'] == verifier.PIN
assert parsed['CMAKE_BUILD_WITH_INSTALL_RPATH'] == 'ON'
assert parsed['CMAKE_INSTALL_RPATH'] == '$ORIGIN'
# CPU validator intentionally rejects the CUDA cache. Test that expected boundary
# independently from the fixed multiline parser regression.
try:
    cpu.validate_cache(actual.read_text(), {'LLAMA_BUILD_NUMBER': '0'})
except ValueError as error:
    assert str(error) == 'GPU_COMPILER_CONFIGURED'
else:
    raise AssertionError('CPU cache accepted a GPU compiler')
checks.append({'case': 'actual_cache_build_number_and_rpath_exact_cpu_rejects_gpu', 'status': 'PASS'})
for name, expected_hash in cpu.PINS.items():
    assert sha256((ROOT / name).read_bytes()).hexdigest() == expected_hash, name
proof = {'status': 'PASS', 'checks': checks, 'check_count': len(checks),
         'verifier_sha256': sha256((ROOT / 'var/research/verify_llama_build.py').read_bytes()).hexdigest(),
         'cpu_runner_sha256': sha256((ROOT / 'var/research/build_native_contract_cpu.py').read_bytes()).hexdigest(),
         'checker_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
         'actual_cache_sha256': sha256(actual.read_bytes()).hexdigest(),
         'main_executed': False, 'subprocesses_or_gpu_calls': 0}
output = ROOT / 'var/research/cmake-cache-parser-proof.json'
output.write_text(json.dumps(proof, indent=2) + '\n')
print(json.dumps({'status': 'PASS', 'checks': len(checks),
                  'verifier_sha256': proof['verifier_sha256'], 'cpu_runner_sha256': proof['cpu_runner_sha256'],
                  'proof_sha256': sha256(output.read_bytes()).hexdigest()}))
