"""Public GLM vocabulary-only CPU wrapper; blocked until reviewed public/build pins.

No evaluation inputs, tokenizer re-encoding, tensor/context/backend/decode or HTTP.
Original and v2 failures remain required inputs through the fixed public helper.
"""
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager
import hashlib, importlib.util, json, os, re, resource, signal, stat, subprocess, sys

ROOT = Path('/home/a202192020/NeuroBuild_v2')
BASE = ROOT / 'var/research/native-glm47-contract'
MODEL_ID = 'ggml-org/GLM-4.7-Flash-GGUF'
REVISION = '7559e96b7e324ab405897dc2b91492b0f376ad4a'
MODEL = ROOT / 'var/models/ggml-org--GLM-4.7-Flash-GGUF' / REVISION / 'GLM-4.7-Flash-Q4_K.gguf'
MODEL_SHA = 'b6019edc5fbe37d3660d2e994d16c839a7855a6f03362c5dcf8142ba479cd0d2'
MODEL_BYTES = 18244193920
HEADER = ROOT / 'var/reports/glm47-flash-gguf-header.json'
HEADER_SHA = '595a7efd19914b65e91f1d92aaee141a0457472039c7278264cc1b5d314659ef'
TEMPLATE_SHA = 'd63ad536c3c81880043e22ec7fd08db42b4d8fb7c89c7138bc562bfa25281375'
TOKENIZER_SHA = '19e773648cb4e65de8660ea6365e10acca112d42a854923df93db4a6f333a82d'
PUBLIC_HELPER_SHA = '06dc94dc5211e84c91fedde470ea5aebbc11bd93f1bd83e6a3b3aae85f8ffc45'
FIXTURE_SHA = 'e67bd4d05462587e0466f092351ada8c8fa4efdd9a10da0b4cecb25a4d3dc8f3'
# No CLI/environment bypass. Fill only from separately reviewed actual receipts.
PUBLIC_PROOF_SHA = 'd8f8fe1faf2ee73b06f6df35d16dba3a29cb78ad41af35a8a1be6cff888ac85c'
BUILD_REPORT_SHA = 'befeeb0c258f9c570b6c148e78e426979811a1b628090bf0ad1bc25ceac2cbef'
BINARY_SHA = '19e5641f0e6051348a96f06fe6986cb40c5228e83bb352a2c21ea9317fcad3cb'
REPORT = BASE / 'public-vocab-proof.json'
SOURCE_PATHS = (
    'src/neurobuild/infrastructure/local_model.py',
    'src/neurobuild/application/requirement_generation.py',
    'src/neurobuild/application/requirements.py',
    'prompts/requirement_generation_v2_v2.txt',
    'schemas/requirement_generation_v2_decision_branches.schema.json',
)
SAFE_ENV = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8',
            'CUDA_VISIBLE_DEVICES': '', 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1',
            'PYTHONNOUSERSITE': '1'}
BOOTSTRAP = '''import ctypes,os,resource,signal,sys
parent=int(sys.argv[1])
if os.getppid()!=parent:raise SystemExit(91)
if ctypes.CDLL(None,use_errno=True).prctl(1,signal.SIGKILL,0,0,0)!=0:raise SystemExit(91)
if os.getppid()!=parent:os.kill(os.getpid(),signal.SIGKILL)
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
os.execve(sys.argv[2],sys.argv[2:],dict(os.environ))
'''

def require(value, code):
    if not value: raise ValueError(code)

def ready():
    require(all(type(x) is str and re.fullmatch('[0-9a-f]{64}', x)
                for x in (PUBLIC_PROOF_SHA, BUILD_REPORT_SHA, BINARY_SHA)),
            'ACTUAL_PUBLIC_BUILD_PINS_PENDING')

def stat_key(s):
    return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns

@contextmanager
def safe_open(path, write=False):
    require(path.is_relative_to(ROOT) and '..' not in path.parts, 'OUTSIDE_PROJECT')
    parts = path.relative_to(ROOT).parts
    require(bool(parts), 'INVALID_FILE_PATH')
    fd = os.open(ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        require(os.fstat(fd).st_uid == os.getuid(), 'PATH_NOT_OWNED')
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = child
            require(os.fstat(fd).st_uid == os.getuid(), 'PATH_NOT_OWNED')
        flags = os.O_NOFOLLOW | (os.O_WRONLY | os.O_CREAT | os.O_EXCL if write else os.O_RDONLY | os.O_NONBLOCK)
        leaf = os.open(parts[-1], flags, 0o600, dir_fd=fd)
        with os.fdopen(leaf, 'wb' if write else 'rb') as stream:
            info = os.fstat(stream.fileno())
            require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                    and info.st_nlink == 1, 'UNSAFE_FILE')
            yield stream
            if write: stream.flush(); os.fsync(stream.fileno())
        if write: os.fsync(fd)
    finally: os.close(fd)

def sha(path):
    with safe_open(path) as f: return hashlib.file_digest(f, 'sha256').hexdigest()

def read_bound(path, digest, cap):
    with safe_open(path) as f:
        before = os.fstat(f.fileno())
        require(before.st_size <= cap, 'INPUT_TOO_LARGE')
        data = f.read(cap + 1)
        require(len(data) == before.st_size and stat_key(before) == stat_key(os.fstat(f.fileno())), 'INPUT_CHANGED')
    require(hashlib.sha256(data).hexdigest() == digest, 'INPUT_HASH_CHANGED')
    return data

def model_stat_matches(expected):
    with safe_open(MODEL) as f:
        require(stat_key(os.fstat(f.fileno())) == expected, 'MODEL_PATH_CHANGED')

def prepare():
    ready()
    header = json.loads(read_bound(HEADER, HEADER_SHA, 2 * 1024**2))
    require(header['kind'] == 'GGUF_HEADER_AUDIT' and header['status'] == 'PASS'
            and header['model_id'] == MODEL_ID and header['revision'] == REVISION
            and header['file_sha256'] == MODEL_SHA and header['file_bytes'] == MODEL_BYTES
            and header['model_path'] == str(MODEL.relative_to(ROOT))
            and header['full_file_sha256_verified'] is True
            and header['gpu_or_native_execution'] is False
            and header['header']['tensor_count'] == 844
            and header['bindings']['embedded_template_sha256'] == TEMPLATE_SHA
            and header['bindings']['quantization'] == 'Q4_K_M'
            and header['bindings']['main_layer_count'] == 47
            and header['bindings']['nextn_layer_count'] == 0, 'HEADER_REQUIRED')
    read_bound(BASE / 'public_check_v3.py', PUBLIC_HELPER_SHA, 128 * 1024)
    proof = json.loads(read_bound(BASE / 'public-proof-v3.json', PUBLIC_PROOF_SHA, 2 * 1024**2))
    build = json.loads(read_bound(BASE / 'build-v3.json', BUILD_REPORT_SHA, 2 * 1024**2))
    fixture = json.loads(read_bound(BASE / 'official-tokenizer-fixture.json', FIXTURE_SHA, 128 * 1024))
    require(proof['kind'] == 'GLM47_FLASH_NATIVE_PUBLIC_TEMPLATE_CPU_PROOF' and proof['status'] == 'PASS'
            and proof['helper_sha256'] == PUBLIC_HELPER_SHA and proof['build_report_sha256'] == BUILD_REPORT_SHA
            and proof['binary_sha256'] == build['binary_sha256'] == BINARY_SHA
            and proof['model_id'] == MODEL_ID and proof['model_revision'] == REVISION
            and proof['sampling_profile'] == 'glm47_flash_nonthinking_llama_cpp'
            and proof['protocol'] == 'llama_cpp_json_schema' and proof['enable_thinking'] is False
            and proof['template_override_used'] is False
            and proof['official_template_sha256'] == TEMPLATE_SHA, 'PUBLIC_CONTRACT_REQUIRED')
    require(fixture['kind'] == 'GLM47_FLASH_PUBLIC_OFFICIAL_TOKENIZER_FIXTURE'
            and fixture['reference_kind'] == 'official_pinned_tokenizer_no_normalizer_change'
            and fixture['normalizer'] is None and fixture['tokenizer_sha256'] == TOKENIZER_SHA
            and fixture['case_count'] == 20 and len(fixture['tokenizer_parity']) == 20
            and fixture['official_raw_roundtrip_count'] == 20 and fixture['official_raw_mismatch_indices'] == []
            and fixture['added_literal_single_id_count'] == 36
            and fixture['added_literal_raw_roundtrip_count'] == 36
            and fixture['application_input_output_nfc_repair'] is False, 'OFFICIAL_REFERENCE_REQUIRED')
    spec = importlib.util.spec_from_file_location('glm_public_v3', BASE / 'public_check_v3.py')
    public = importlib.util.module_from_spec(spec); spec.loader.exec_module(public)
    # Some preserved pins are CPU binaries, so verify by streaming hash rather
    # than applying a metadata-size cap to them or loading them into memory.
    for path, digest in public.PINS.items(): require(sha(path) == digest, 'PUBLIC_SOURCE_CHANGED')
    binary, checked_build = public.inspect_cpu_binary()
    require(checked_build == build and sha(binary) == BINARY_SHA, 'CPU_BINARY_CHANGED')
    source = {path: public.PINS[ROOT / path] for path in SOURCE_PATHS}
    # One bounded streaming full hash binds this exact invocation to the model
    # file. This does not decode tensor values or create a model context.
    with safe_open(MODEL) as f:
        before = os.fstat(f.fileno())
        require(before.st_size == MODEL_BYTES, 'MODEL_SIZE_CHANGED')
        require(hashlib.file_digest(f, 'sha256').hexdigest() == MODEL_SHA, 'MODEL_HASH_CHANGED')
        require(stat_key(before) == stat_key(os.fstat(f.fileno())), 'MODEL_CHANGED_DURING_HASH')
    model_stat_matches(stat_key(before))
    return public, binary, build, proof, fixture, source, stat_key(before)

def invoke(public, binary, bundle, before, public_native):
    model_stat_matches(before)
    payload = json.dumps(bundle, ensure_ascii=False).encode()
    require(len(payload) <= 2 * 1024**2, 'BUNDLE_TOO_LARGE')
    args = [str(ROOT / '.conda/bin/python'), '-I', '-B', '-c', BOOTSTRAP, str(os.getpid()),
            str(binary), str(public.TEMPLATE), str(public.SCHEMA), str(MODEL)]
    child = subprocess.Popen(args, cwd=ROOT, env=SAFE_ENV, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try: stdout, stderr = child.communicate(payload, timeout=180)
    except BaseException:
        try: os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError: pass
        child.wait(); raise
    require(not stderr and len(stdout) < 65536, 'UNSAFE_CPU_OUTPUT')
    native = json.loads(stdout)
    allowed = set(public_native) | {
        'code', 'stage', 'check_line', 'native_vocab_grammar_cases_accepted',
        'native_vocab_grammar_cases_rejected', 'native_vocab_grammar_eog_checked',
        'embedded_template_exact_match', 'vocab_backed_official_prompt_exact',
        'tokenizer_cases_checked', 'tokenizer_id_match_count', 'tokenizer_native_raw_roundtrip_count',
        'tokenizer_reference_ids_raw_roundtrip_count', 'tokenizer_id_mismatch_mask', 'tokenizer_raw_mismatch_mask',
        'official_hf_equivalence', 'resource_probe_token_id', 'resource_probe_token_count',
        'resource_probe_raw_roundtrip', 'public_input_tokens', 'public_input_plus_output',
    }
    require(type(native) is dict and set(native) <= allowed
            and native.get('kind') == 'GLM47_FLASH_NATIVE_PUBLIC_CONTRACT_CPU_PREFLIGHT'
            and all(type(value) in (str, int, bool) for value in native.values()), 'CPU_BODY_OUTPUT_FORBIDDEN')
    model_stat_matches(before); require(sha(binary) == BINARY_SHA, 'CPU_BINARY_CHANGED')
    return child.returncode, native, hashlib.sha256(payload).hexdigest()

def validate_native(code, native, public_native):
    require(code == 0 and native.get('status') == 'PASS', 'NATIVE_CPU_FAILED')
    for key, value in public_native.items():
        if key == 'native_tokenization': continue
        require(type(native.get(key)) is type(value) and native[key] == value, 'PUBLIC_CONTRACT_CHANGED')
    for key, value in {'native_vocab_grammar_cases_accepted': 20, 'native_vocab_grammar_cases_rejected': 40,
                       'tokenizer_cases_checked': 20, 'tokenizer_id_match_count': 20,
                       'tokenizer_native_raw_roundtrip_count': 20, 'tokenizer_reference_ids_raw_roundtrip_count': 20,
                       'tokenizer_id_mismatch_mask': 0, 'tokenizer_raw_mismatch_mask': 0,
                       'resource_probe_token_count': 1}.items():
        require(type(native.get(key)) is int and native[key] == value, 'NATIVE_VOCAB_COUNT_MISMATCH')
    for key in ('native_vocab_grammar_eog_checked', 'embedded_template_exact_match',
                'vocab_backed_official_prompt_exact', 'resource_probe_raw_roundtrip'):
        require(native.get(key) is True, 'NATIVE_VOCAB_INVARIANT')
    require(native.get('native_tokenization') == 'OBSERVED_VOCAB_ONLY'
            and native.get('official_hf_equivalence') == 'PASS', 'OFFICIAL_EQUIVALENCE_FAILED')
    require(type(native.get('resource_probe_token_id')) is int
            and 0 <= native['resource_probe_token_id'] < 154880, 'RESOURCE_TOKEN_INVALID')
    require(type(native.get('public_input_tokens')) is int and native['public_input_tokens'] > 0
            and native['public_input_tokens'] + 768 == native.get('public_input_plus_output') <= 4096, 'PUBLIC_CONTEXT_LIMIT')

def main():
    ready()  # Before any proof creation, helper import, model or input access.
    require(len(sys.argv) == 1 and Path(sys.prefix) == ROOT / '.conda'
            and os.environ.get('CUDA_VISIBLE_DEVICES') == '', 'CPU_ENV_REQUIRED')
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    require(not REPORT.exists() and not REPORT.is_symlink(), 'OUTPUT_EXISTS')
    record = {'kind': 'GLM47_FLASH_NATIVE_PUBLIC_VOCAB_CPU_PROOF', 'status': 'FAIL',
              'at_utc': datetime.now(timezone.utc).isoformat(), 'phase': 'PREPARE',
              'helper_sha256': sha(Path(__file__)), 'model_id': MODEL_ID, 'revision': REVISION,
              'gguf_sha256': MODEL_SHA, 'header_sha256': HEADER_SHA, 'template_sha256': TEMPLATE_SHA,
              'public_contract_sha256': PUBLIC_PROOF_SHA, 'tokenizer_fixture_sha256': FIXTURE_SHA,
              'build_report_sha256': BUILD_REPORT_SHA, 'binary_sha256': BINARY_SHA,
              'model_inference_calls': 0, 'http_calls': 0, 'gpu_calls': 0,
              'evaluation_inputs_read': 0, 'official_tokenizer_reencoded': False,
              'application_input_output_nfc_repair': False, 'official_reference_observed_all20': False,
              'eligibility': 'VOCAB_ONLY_CONTEXT_AND_RUNTIME_PENDING'}
    try:
        public, binary, build, proof, fixture, source, before = prepare()
        record['phase'] = 'PUBLIC_NATIVE_VOCAB'
        request = public.capture_request(); templates, jinja_version = public.official_reference(request)
        bundle = {'request': request, 'cases': public.corpus(), 'template_cases': templates,
                  'reference_kind': 'official_pinned_tokenizer_no_normalizer_change',
                  'audited_vocab_only': True, 'tokenizer_parity': fixture['tokenizer_parity']}
        code, native, bundle_sha = invoke(public, binary, bundle, before, proof['native'])
        record.update(native=native, exit_code=code, bundle_sha256=bundle_sha)
        observed = type(native.get('tokenizer_cases_checked')) is int and native['tokenizer_cases_checked'] == 20
        masks = {key: native.get(key) for key in ('tokenizer_id_mismatch_mask', 'tokenizer_raw_mismatch_mask')}
        for mask in masks.values():
            require(mask is None or type(mask) is int and 0 <= mask < 2**20, 'INVALID_MISMATCH_MASK')
        require(not observed or all(type(mask) is int for mask in masks.values()), 'MISSING_OBSERVED_MASK')
        record.update(                      source_pin=build['source_pin'], source_sha256=source, jinja2_reference_version=jinja_version,
                      official_reference_observed_all20=observed,
                      official_reference_native_id_mismatch_indices=None if not observed else [i for i in range(20) if masks['tokenizer_id_mismatch_mask'] & (1 << i)],
                      native_raw_roundtrip_mismatch_indices=None if not observed else [i for i in range(20) if masks['tokenizer_raw_mismatch_mask'] & (1 << i)],
                      model_stat_before_and_after_equal=True,
                      gguf_load_mode='VOCAB_ONLY_NO_ALLOC_NO_TENSORS_NO_CONTEXT_EMPTY_DEVICES')
        validate_native(code, native, proof['native'])
        for path, digest in public.PINS.items(): require(sha(path) == digest, 'PUBLIC_SOURCE_CHANGED')
        for path, digest in ((HEADER, HEADER_SHA), (BASE / 'official-tokenizer-fixture.json', FIXTURE_SHA),
                             (BASE / 'public-proof-v3.json', PUBLIC_PROOF_SHA), (BASE / 'build-v3.json', BUILD_REPORT_SHA)):
            require(sha(path) == digest, 'PROOF_CHANGED')
        record.update(status='PASS', phase='FINISHED')
    except Exception as error:
        record.update(error_type=type(error).__name__, error_code=str(error)
                      if isinstance(error, ValueError) and re.fullmatch('[A-Z0-9_]+', str(error)) else 'INPUT_OR_IO_ERROR')
    finally:
        with safe_open(REPORT, write=True) as f:
            f.write((json.dumps(record, indent=2) + '\n').encode())
    print(json.dumps({'status': record['status'], 'phase': record['phase'],
                      'observed_all20': record['official_reference_observed_all20'],
                      'report': str(REPORT.relative_to(ROOT)), 'sha256': sha(REPORT)}))
    return 0 if record['status'] == 'PASS' else 1

if __name__ == '__main__':
    try: raise SystemExit(main())
    except Exception as error:
        print(json.dumps({'status': 'FAIL', 'error_type': type(error).__name__,
                          'code': str(error) if isinstance(error, ValueError) and re.fullmatch('[A-Z0-9_]+', str(error)) else 'INPUT_OR_IO_ERROR'}))
        raise SystemExit(1)
