"""Public-only CPU vocab diagnostic; no evaluation input, HTTP or inference."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import re
import resource
import subprocess
import sys

ROOT = Path('/home/a202192020/NeuroBuild_v2')
HEADER = ROOT / 'var/reports/qwen38-gguf-header.json'
HEADER_SHA = 'ff168aeee125b2934b8b5204c14971915c7555c5dfc660d6fda46c2bf7fc810a'
PUBLIC = ROOT / 'var/research/run_native_contract_cpu.py'
PUBLIC_SHA = 'bc441dbcb6f86106d47f7a87364f0008d793d78ae0d04795e57f7ec441f193df'
PARITY = ROOT / 'var/research/native-tokenizer-public-parity.json'
PARITY_SHA = '79c4448b7ee949add0a80e8a7f0fc0d73575aaf01ff6e52beb3cfae8434ea1bd'
BOOTSTRAP = '''import ctypes,os,resource,signal,sys
p=int(sys.argv[1])
if ctypes.CDLL(None,use_errno=True).prctl(1,signal.SIGKILL,0,0,0)!=0:raise SystemExit(2)
if os.getppid()!=p:os.kill(os.getpid(),signal.SIGKILL)
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
os.execve(sys.argv[2],sys.argv[2:],dict(os.environ))
'''


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', type=int, required=True)
    parser.add_argument('--reference', choices=('official-hf', 'raw-diagnostic'), default='official-hf')
    args = parser.parse_args()
    assert 3 <= args.version <= 9
    assert Path(sys.prefix) == ROOT / '.conda' and os.environ.get('CUDA_VISIBLE_DEVICES') == ''
    for path, expected in ((HEADER, HEADER_SHA), (PUBLIC, PUBLIC_SHA), (PARITY, PARITY_SHA)):
        assert path.is_file() and not path.is_symlink() and sha(path) == expected
    build_path = ROOT / f'var/reports/llama-native-contract-cpu-build-v{args.version}.json'
    suffix = '' if args.reference == 'official-hf' else '-raw-diagnostic'
    output = ROOT / f'var/research/native-vocab-public-probe-v{args.version}{suffix}.json'
    assert not output.exists() and not output.is_symlink()
    spec = importlib.util.spec_from_file_location('pinned_public_probe', PUBLIC)
    public = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(public)
    for path, expected in public.PINS.items():
        assert sha(path) == expected
    build = json.loads(build_path.read_text())
    binary, needed = public.inspect_cpu_binary(build)
    header = json.loads(HEADER.read_text())
    assert header['kind'] == 'GGUF_HEADER_AUDIT' and header['status'] == 'PASS'
    assert header['file_sha256'] == 'c600de0300ae8a0eb3a6c0b8b5561b8b96f16bd2c863c2a66c42de29d391a747'
    assert header['model_path'] == 'var/models/ggml-org--Qwen3.8-27B-GGUF/efbb3b1f70a21d97fd4495240648405f7228554f/Qwen3.8-27B-Q4_K_M.gguf'
    model = ROOT / header['model_path']
    assert not model.is_symlink() and model.is_file()
    before = model.stat()
    assert before.st_uid == os.getuid() and before.st_nlink == 1 and before.st_size == 18973870528
    request = public.capture_request()
    cases = public.corpus()
    parity = json.loads(PARITY.read_text())['tokenizer_parity']
    fixture_sha = PARITY_SHA
    if args.reference == 'raw-diagnostic':
        derived_path = ROOT / 'var/research/native-tokenizer-public-parity-raw-diagnostic.json'
        fixture_sha = '9658eb53fae81adee1b775b45f796f3484db69aea41e04a020765fa05d770514'
        assert sha(derived_path) == fixture_sha
        derived = json.loads(derived_path.read_text())
        assert derived['original_fixture_sha256'] == PARITY_SHA
        assert [row['text'] for row in derived['tokenizer_parity']] == [row['text'] for row in parity]
        parity = derived['tokenizer_parity']
    assert len(parity) == 20 and len(cases) == 30
    bundle = {'request': request, 'cases': cases, 'context_requests': [request],
              'max_output_tokens': 768, 'tokenizer_parity': parity}
    payload = json.dumps(bundle, ensure_ascii=False).encode()
    child = subprocess.run([str(ROOT / '.conda/bin/python'), '-I', '-B', '-c', BOOTSTRAP,
                            str(os.getpid()), str(binary), str(public.TEMPLATE), str(public.SCHEMA), str(model)],
                           input=payload, cwd=ROOT, env=public.SAFE_ENV, capture_output=True,
                           timeout=180, check=False)
    assert model.stat() == before and len(child.stdout) <= 65536
    native = json.loads(child.stdout)
    # No string values except the fixed protocol labels below may be persisted.
    assert type(native) is dict
    strings = {'status': {'PASS', 'FAIL'}, 'kind': {'NATIVE_CONTRACT_CPU_PREFLIGHT'},
               'code': {'CHECK_FAILED'}, 'native_tokenization': {'PASS_VOCAB_ONLY', 'NOT_RUN'},
               'tokenizer_metadata_parity': {'PASS', 'NOT_RUN'}}
    for key, value in native.items():
        assert re.fullmatch('[a-z_]+', key)
        if type(value) is str:
            assert value in strings.get(key, set())
        else:
            assert type(value) in (int, bool) and value >= 0
    record = {'kind': 'PUBLIC_SYNTHETIC_OPTIONAL_VOCAB_DIAGNOSTIC', 'native': native,
              'exit_code': child.returncode, 'stderr_bytes': len(child.stderr),
              'binary_sha256': build['binary_sha256'], 'build_report_sha256': sha(build_path),
              'cpp_sha256': build['pinned_inputs']['var/research/native-contract-validator/validator.cpp'],
              'header_proof_sha256': HEADER_SHA, 'public_helper_sha256': PUBLIC_SHA,
              'parity_fixture_sha256': PARITY_SHA, 'helper_sha256': sha(Path(__file__)),
              'reference_kind': args.reference, 'actual_reference_sha256': fixture_sha,
              'public_cases': 30, 'tokenizer_parity_cases': 20, 'context_requests': 1,
              'elf_needed': needed, 'public_bundle_sha256': hashlib.sha256(payload).hexdigest(),
              'gpu_calls': 0, 'model_inference_calls': 0, 'v2_or_exposed_inputs_read': False,
              'stderr_text_saved': False}
    with output.open('x') as stream:
        json.dump(record, stream, indent=2); stream.write('\n')
    print(json.dumps({'report': str(output.relative_to(ROOT)), 'native': native,
                      'exit_code': child.returncode, 'stderr_bytes': len(child.stderr)}))
    return 0 if child.returncode == 0 and native['status'] == 'PASS' and not child.stderr else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({'status': 'FAIL', 'error_type': type(error).__name__}))
        raise SystemExit(1)
