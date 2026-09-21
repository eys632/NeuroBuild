"""CPU-only actual native contract check; public examples and synthetic cases only."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json
import os
import re
import resource
import subprocess
import sys
from urllib.error import URLError

ROOT = Path('/home/a202192020/NeuroBuild_v2')
sys.path.insert(0, str(ROOT / 'src'))
from neurobuild.infrastructure.local_model import LocalRequirementClient
from neurobuild.domain.errors import DomainError
from jsonschema import Draft202012Validator

TEMPLATE = ROOT / 'var/research/qwen38-candidate-metadata/upstream/chat_template.jinja'
SCHEMA = ROOT / 'schemas/requirement_generation_v2_decision_branches.schema.json'
PROMPT = ROOT / 'prompts/requirement_generation_v2_v2.txt'
REPORT = ROOT / 'var/reports/native-contract-cpu-public.json'
BUILD_REPORT = ROOT / 'var/reports/llama-native-contract-cpu-build-v2.json'
PINS = {
    TEMPLATE: 'c3cf9e34abf4f9e36c2d72165aa9c132d3e2a725b6c2586aaa3a8af9d7a81041',
    SCHEMA: '36d42b9fa3d24f4a1bc1d14381110e36e8d89103b696bc83113be006b64934e2',
    PROMPT: '99d737124372836ba5f985fa6e5570afef693e769798844931f000fb21403cf6',
}
SAFE_ENV = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8',
            'CUDA_VISIBLE_DEVICES': '', 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def capture_request():
    class Capture:
        def open(self, request, **kwargs):
            self.body = request.data
            raise URLError('CPU capture')
    capture = Capture()
    client = LocalRequirementClient('http://127.0.0.1:8003', 'neurobuild-qwen38-27b-q4-k-m',
        prompt_path=PROMPT, schema_path=SCHEMA, generation_contract='2.0',
        protocol='llama_cpp_json_schema', sampling_profile='qwen38_nonthinking_llama_cpp')
    client._opener = capture
    try:
        client.complete('검사실 책상을 X축 양의 방향으로 1m 옮겨줘.', axis_convention='project_xy')
    except DomainError as error:
        assert error.code == 'LOCAL_MODEL_UNAVAILABLE'
    return json.loads(capture.body)


def corpus():
    examples = [json.loads(line.removeprefix('출력: ')) for line in PROMPT.read_text().splitlines()
                if line.startswith('출력: ')]
    assert len(examples) == 7
    ready, nonready = copy.deepcopy(examples[0]), copy.deepcopy(examples[2])
    xy = dict(ready, dy_evidence='Y축 -2cm')
    escaped = dict(ready, target_selection_quote='"인용"\\경로\n한국어 😀')
    accepts = examples + [xy, escaped, dict(ready, target_selection_quote='')]
    rejects = []
    for key in ready:
        case = copy.deepcopy(ready)
        del case[key]
        rejects.append(case)
    rejects += [dict(ready, extra=True), dict(ready, schema_version='1.0'),
                dict(ready, decision='UNKNOWN'), dict(ready, dx_evidence=None),
                dict(ready, reason='null'), dict(ready, current_instruction_quote=None),
                dict(nonready, current_instruction_quote='지원되지 않은 지시'),
                dict(nonready, dx_evidence='X축 +1m'), dict(nonready, reason=None), [ready]]
    validator = Draft202012Validator(json.loads(SCHEMA.read_text()))
    assert all(validator.is_valid(case) for case in accepts)
    assert all(not validator.is_valid(case) for case in rejects)
    encode = lambda case: json.dumps(case, ensure_ascii=False, separators=(',', ':'))
    cases = [{'text': encode(case), 'accept': True} for case in accepts]
    cases += [{'text': encode(case), 'accept': False} for case in rejects]
    cases += [{'text': text, 'accept': False} for text in
              (encode(ready)[:-1], encode(ready) + 'x', encode(ready) + encode(ready))]
    return cases


def inspect_cpu_binary(build):
    assert build['status'] == 'COMPILE_PASS_NOT_EXECUTED'
    assert build['cuda_visible_devices'] == '' and build['native_validator_executed'] is False
    assert build['settings']['GGML_CUDA'] == 'OFF'
    assert build['settings']['GGML_BACKEND_DL'] == 'OFF'
    assert build['settings']['BUILD_SHARED_LIBS'] == 'OFF'
    binary = ROOT / build['binary_path']
    assert not binary.is_symlink() and binary.is_file() and sha(binary) == build['binary_sha256']
    for relative, expected in build['pinned_inputs'].items():
        assert sha(ROOT / relative) == expected
    dynamic = subprocess.run(['/usr/bin/readelf', '--wide', '--dynamic', str(binary)],
        cwd=ROOT, env=SAFE_ENV, capture_output=True, check=True, text=True, timeout=30)
    assert not dynamic.stderr
    needed = re.findall(r'\(NEEDED\).*\[([^\]]+)\]', dynamic.stdout)
    assert needed and set(needed) <= {'libstdc++.so.6', 'libm.so.6', 'libgcc_s.so.1',
        'libc.so.6', 'libpthread.so.0', 'libdl.so.2', 'librt.so.1', 'ld-linux-x86-64.so.2'}
    assert not re.search(r'\((?:RPATH|RUNPATH)\)', dynamic.stdout)
    assert all(phase['native_cleanup']['cleanup_complete'] and
               phase['native_cleanup']['native_reaped'] for phase in build['phases'])
    return binary, needed


def main():
    assert len(sys.argv) == 1 and Path(sys.prefix) == ROOT / '.conda'
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == ''
    assert not REPORT.exists() and not REPORT.is_symlink()
    for path, expected in PINS.items():
        assert sha(path) == expected
    build = json.loads(BUILD_REPORT.read_text())
    binary, needed = inspect_cpu_binary(build)
    bundle = {'request': capture_request(), 'cases': corpus()}
    payload = json.dumps(bundle, ensure_ascii=False).encode()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    result = subprocess.run([str(binary), str(TEMPLATE), str(SCHEMA)], input=payload,
        cwd=ROOT, env=SAFE_ENV, capture_output=True, timeout=180, check=False)
    assert len(result.stdout) < 65536 and not result.stderr
    native = json.loads(result.stdout)
    assert native.get('kind') == 'NATIVE_CONTRACT_CPU_PREFLIGHT'
    # The helper emits only a fixed status code/counts; no exception text or input.
    report = {'status': 'PASS' if result.returncode == 0 and native['status'] == 'PASS' else 'FAIL',
        'kind': 'NATIVE_CONTRACT_PUBLIC_CPU_PROOF', 'at_utc': datetime.now(timezone.utc).isoformat(),
        'native': native, 'exit_code': result.returncode, 'elf_needed': needed,
        'binary_sha256': sha(binary), 'build_report_sha256': sha(BUILD_REPORT),
        'helper_sha256': sha(Path(__file__)), 'request_sha256': hashlib.sha256(
            json.dumps(bundle['request'], ensure_ascii=False).encode()).hexdigest(),
        'corpus_sha256': hashlib.sha256(payload).hexdigest(),
        'inputs': {str(path.relative_to(ROOT)): expected for path, expected in PINS.items()},
        'scope': 'Public prompt examples and synthetic controls only; no v2 input/gold, GPU, model or network calls'}
    with REPORT.open('x') as stream:
        json.dump(report, stream, indent=2); stream.write('\n')
    print(json.dumps({'status': report['status'], 'native': native, 'report': str(REPORT.relative_to(ROOT))}))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({'status': 'FAIL', 'error_type': type(error).__name__}))
        raise SystemExit(1)
