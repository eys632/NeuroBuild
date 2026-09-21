"""GLM native context counts only; actual official vocab PASS must precede input reads.

No model inference, evaluation scoring/replay, tokenizer-reference re-encoding,
or unused holdout paths. New context TU, immutable public/vocab definitions.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, importlib.util, json, os, re, resource, signal, subprocess, sys

ROOT = Path('/home/a202192020/NeuroBuild_v2')
BASE = ROOT / 'var/research/native-glm47-contract'
VOCAB_HELPER_SHA = 'aafeaa2d9bf6ef7b5ceccfac1d4e4b0e1f70ef34cd17c2d34e8df4035e124d70'
CONTEXT_CPP_SHA = 'fe5f71fdce897d4138b77f670d5931ea685715b29b2795d50219f80b25510410'
CONTEXT_BUILDER_SHA = '6049c61c7dfba476034e975894ee8cebbaf3b274c78afcea11374d661f46e9b3'
# Fill only after actual reviewed receipts; no CLI/environment override.
VOCAB_PROOF_SHA = 'f3e31a724dcec94f6d3b285a9dd793d6a8b6c91c3c8c475a63c25709c94d6cf7'
CONTEXT_BUILD_SHA = '737234c286864486c57721007b6858fae61bb7613eee02eb007ab5be0e5795bd'
CONTEXT_BINARY_SHA = '3da5aa2debc3307277eab2794194541858e384c0fcfc0cfbe79e0f5b973f3017'
REPORT = BASE / 'vocab-context-proof.json'
SPLITS = {
    'exposed120': ('evaluations/requirement_hardening_v1_exposed_regression.jsonl', 120,
                   '7e5b9a05932df7aafdbf683655b044b3e3b25cbffb4115d298e1490aecbc7a5b'),
    'v2_length80': ('evaluations/requirement_hardening_v2_holdout.jsonl', 80,
                   '7416f05613b1490358672f3926770dbd8653e676577eeee6ba65f863b27cec40'),
}

def require(value, code):
    if not value: raise ValueError(code)

def ready():
    require(all(type(x) is str and re.fullmatch('[0-9a-f]{64}', x)
                for x in (VOCAB_PROOF_SHA, CONTEXT_BUILD_SHA, CONTEXT_BINARY_SHA)),
            'ACTUAL_VOCAB_PASS_AND_CONTEXT_BUILD_PENDING')

def load_vocab():
    ready()
    path = BASE / 'vocab_check.py'
    require(not path.is_symlink() and hashlib.sha256(path.read_bytes()).hexdigest() == VOCAB_HELPER_SHA,
            'VOCAB_HELPER_CHANGED')
    spec = importlib.util.spec_from_file_location('glm_context_pinned_vocab', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

def verify_saved_vocab(vocab):
    proof = json.loads(vocab.read_bound(BASE / 'public-vocab-proof.json', VOCAB_PROOF_SHA, 2 * 1024**2))
    public = json.loads(vocab.read_bound(BASE / 'public-proof-v3.json', vocab.PUBLIC_PROOF_SHA, 2 * 1024**2))
    require(proof['kind'] == 'GLM47_FLASH_NATIVE_PUBLIC_VOCAB_CPU_PROOF' and proof['status'] == 'PASS'
            and proof['helper_sha256'] == VOCAB_HELPER_SHA
            and proof['gguf_sha256'] == vocab.MODEL_SHA and proof['header_sha256'] == vocab.HEADER_SHA
            and proof['model_id'] == vocab.MODEL_ID and proof['revision'] == vocab.REVISION
            and proof['public_contract_sha256'] == vocab.PUBLIC_PROOF_SHA
            and proof['tokenizer_fixture_sha256'] == vocab.FIXTURE_SHA
            and proof['build_report_sha256'] == vocab.BUILD_REPORT_SHA
            and proof['binary_sha256'] == vocab.BINARY_SHA
            and proof['official_reference_observed_all20'] is True
            and proof['official_reference_native_id_mismatch_indices'] == []
            and proof['native_raw_roundtrip_mismatch_indices'] == []
            and proof['model_inference_calls'] == proof['gpu_calls'] == proof['http_calls'] == 0
            and proof['evaluation_inputs_read'] == 0 and proof['application_input_output_nfc_repair'] is False,
            'ACTUAL_OFFICIAL_VOCAB_PASS_REQUIRED')
    vocab.validate_native(proof['exit_code'], proof['native'], public['native'])
    return proof

def validate_counts(code, native, count):
    require(type(native) is dict and native.get('kind') == 'GLM47_FLASH_NATIVE_CONTEXT_CPU_COUNTS', 'CONTEXT_KIND')
    allowed = {'kind', 'status', 'input_count', 'min_input_tokens', 'max_input_tokens', 'max_input_plus_output',
               'all_context_system_user_bytes_exact', 'all_context_prompt_raw_roundtrips_exact',
               'embedded_template_exact_match', 'native_generation_prompt_exact', 'native_schema_grammar_fixed',
               'native_sampling_schema_binding', 'grammar_lazy', 'core_dump_limit_zero', 'model_context_created',
               'backend_init_called', 'weight_tensors_loaded', 'public_tokenizer_cases_repeated', 'discarded_stderr_bytes',
               'code', 'stage', 'check_line'}
    require(set(native) <= allowed and all(type(v) in (str, int, bool) for v in native.values()), 'CONTEXT_BODY_FORBIDDEN')
    require(code == 0 and native.get('status') == 'PASS', 'CONTEXT_NATIVE_FAILED')
    for key in ('all_context_system_user_bytes_exact', 'all_context_prompt_raw_roundtrips_exact',
                'embedded_template_exact_match', 'native_generation_prompt_exact', 'native_schema_grammar_fixed',
                'native_sampling_schema_binding', 'core_dump_limit_zero'):
        require(native.get(key) is True, 'CONTEXT_INVARIANT')
    for key in ('grammar_lazy', 'model_context_created', 'backend_init_called', 'weight_tensors_loaded'):
        require(native.get(key) is False, 'CONTEXT_SCOPE')
    require(type(native.get('input_count')) is int and native['input_count'] == count
            and type(native.get('public_tokenizer_cases_repeated')) is int and native['public_tokenizer_cases_repeated'] == 0
            and type(native.get('discarded_stderr_bytes')) is int and native['discarded_stderr_bytes'] == 0, 'CONTEXT_COUNT')
    require(type(native.get('min_input_tokens')) is int and type(native.get('max_input_tokens')) is int
            and type(native.get('max_input_plus_output')) is int
            and 0 < native['min_input_tokens'] <= native['max_input_tokens']
            and native['max_input_plus_output'] == native['max_input_tokens'] + 768 <= 4096, 'CONTEXT_LIMIT')

def invoke(vocab, public, binary, requests, before):
    vocab.model_stat_matches(before)
    bundle = {'reference_kind': 'official_pinned_tokenizer_no_normalizer_change',
              'audited_official_vocab_pass': True, 'max_output_tokens': 768,
              'expected_count': len(requests), 'context_requests': requests}
    payload = json.dumps(bundle, ensure_ascii=False).encode()
    require(len(payload) <= 16 * 1024**2, 'CONTEXT_BUNDLE_TOO_LARGE')
    args = [str(ROOT / '.conda/bin/python'), '-I', '-B', '-c', vocab.BOOTSTRAP, str(os.getpid()),
            str(binary), str(public.TEMPLATE), str(public.SCHEMA), str(vocab.MODEL)]
    child = subprocess.Popen(args, cwd=ROOT, env=vocab.SAFE_ENV, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try: stdout, stderr = child.communicate(payload, timeout=240)
    except BaseException:
        try: os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError: pass
        child.wait(); raise
    require(not stderr and len(stdout) < 65536, 'CONTEXT_UNSAFE_CPU_OUTPUT')
    native = json.loads(stdout)
    # Validate the scalar-only envelope before a caller can save any values.
    require(type(native) is dict and all(type(v) in (str, int, bool) for v in native.values()), 'CONTEXT_BODY_FORBIDDEN')
    vocab.model_stat_matches(before); require(vocab.sha(binary) == CONTEXT_BINARY_SHA, 'CONTEXT_BINARY_CHANGED')
    return child.returncode, native, hashlib.sha256(payload).hexdigest()

def main():
    ready()  # No dataset access or helper import before actual fixed PASS pins.
    require(len(sys.argv) == 1 and Path(sys.prefix) == ROOT / '.conda'
            and os.environ.get('CUDA_VISIBLE_DEVICES') == '', 'CPU_ENV_REQUIRED')
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    require(not REPORT.exists() and not REPORT.is_symlink(), 'OUTPUT_EXISTS')
    vocab = load_vocab()
    record = {'kind': 'GLM47_FLASH_NATIVE_VOCAB_CONTEXT_CPU_PROOF', 'status': 'FAIL',
              'phase': 'SAVED_OFFICIAL_VOCAB_GATE', 'at_utc': datetime.now(timezone.utc).isoformat(),
              'helper_sha256': vocab.sha(Path(__file__)), 'official_vocab_proof_sha256': VOCAB_PROOF_SHA,
              'model_inference_calls': 0, 'gpu_calls': 0, 'http_calls': 0, 'public_tokenizer_cases_repeated': 0,
              'application_input_output_nfc_repair': False, 'input_bodies_gold_token_ids_saved': False,
              'gold_fields_scored': False, 'splits': {}, 'native_checks': []}
    try:
        passed_vocab = verify_saved_vocab(vocab)
        record['phase'] = 'SOURCE_HEADER_MODEL_BINDING'
        public, _, _, _, _, source, before = vocab.prepare()
        require(source == passed_vocab['source_sha256'], 'VOCAB_SOURCE_BINDING_CHANGED')
        vocab.read_bound(BASE / 'context_validator.cpp', CONTEXT_CPP_SHA, 128 * 1024)
        vocab.read_bound(BASE / 'build_context.py', CONTEXT_BUILDER_SHA, 128 * 1024)
        saved_build = json.loads(vocab.read_bound(BASE / 'context-build.json', CONTEXT_BUILD_SHA, 2 * 1024**2))
        public.BUILD_REPORT = BASE / 'context-build.json'  # In-memory module setting only.
        binary, build = public.inspect_cpu_binary()
        require(saved_build == build and build['binary_sha256'] == CONTEXT_BINARY_SHA
                and vocab.sha(binary) == CONTEXT_BINARY_SHA, 'CONTEXT_BUILD_CHANGED')
        baseline = public.capture_request()
        controls = {key: value for key, value in baseline.items() if key != 'messages'}
        record.update(source_sha256=source, source_pin=build['source_pin'], gguf_sha256=vocab.MODEL_SHA,
                      header_sha256=vocab.HEADER_SHA, model_id=vocab.MODEL_ID, revision=vocab.REVISION,
                      template_sha256=vocab.TEMPLATE_SHA, context_build_sha256=CONTEXT_BUILD_SHA,
                      context_binary_sha256=CONTEXT_BINARY_SHA, max_output_tokens=768, max_context_tokens=4096,
                      resource_probe_token={'text': ' ', 'token_id': passed_vocab['native']['resource_probe_token_id'],
                                            'native_token_count': 1, 'native_roundtrip': True})
        for name, (relative, count, digest) in SPLITS.items():
            # First input read occurs only after the actual saved official20
            # PASS, current source/header/full SHA, and new CPU ELF validation.
            record['phase'] = 'INPUT_LENGTH_' + name
            raw = vocab.read_bound(ROOT / relative, digest, 2 * 1024**2)
            rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
            require(len(rows) == count, 'SPLIT_COUNT')
            requests = []
            for row in rows:
                require(type(row.get('input')) is str and type(row.get('context')) is dict, 'SPLIT_INPUT')
                request = public.capture_request(row['input'], row['context'].get('axis_convention'))
                require({key: value for key, value in request.items() if key != 'messages'} == controls,
                        'CONTEXT_TRANSPORT_CONTROLS_CHANGED')
                require(request['messages'][0] == baseline['messages'][0], 'CONTEXT_SYSTEM_CHANGED')
                requests.append(request)
            del rows, raw
            code, native, bundle_sha = invoke(vocab, public, binary, requests, before)
            # Fixed fields only; do not persist a malformed helper envelope.
            try: validate_counts(code, native, count)
            except ValueError:
                allowed_error = {k: v for k, v in native.items() if k in {'kind', 'status', 'code', 'stage', 'check_line', 'discarded_stderr_bytes'}}
                record['failed_native'] = allowed_error; record['failed_exit_code'] = code
                raise
            record['native_checks'].append(native)
            record['splits'][name] = {'dataset_sha256': digest, 'input_count': count,
                                     'min_input_tokens': native['min_input_tokens'],
                                     'max_input_tokens': native['max_input_tokens'],
                                     'max_input_plus_output': native['max_input_plus_output'], 'bundle_sha256': bundle_sha}
            del requests
        for path, digest in source.items(): require(vocab.sha(ROOT / path) == digest, 'SOURCE_CHANGED')
        require(vocab.sha(BASE / 'public-vocab-proof.json') == VOCAB_PROOF_SHA, 'VOCAB_PROOF_CHANGED')
        require(vocab.sha(BASE / 'context-build.json') == CONTEXT_BUILD_SHA, 'CONTEXT_BUILD_CHANGED')
        vocab.model_stat_matches(before)
        record.update(status='PASS', phase='FINISHED', input_count=200, vocab_only_model_open_count=2,
                      full_model_hash_count=1, model_context_created=False, weight_tensors_loaded=False)
    except Exception as error:
        record.update(error_type=type(error).__name__, error_code=str(error)
                      if isinstance(error, ValueError) and re.fullmatch('[A-Z0-9_]+', str(error)) else 'INPUT_OR_IO_ERROR')
    finally:
        with vocab.safe_open(REPORT, write=True) as f:
            f.write((json.dumps(record, indent=2) + '\n').encode())
    print(json.dumps({'status': record['status'], 'phase': record['phase'],
                      'report': str(REPORT.relative_to(ROOT)), 'sha256': vocab.sha(REPORT)}))
    return 0 if record['status'] == 'PASS' else 1

if __name__ == '__main__':
    try: raise SystemExit(main())
    except Exception as error:
        print(json.dumps({'status': 'FAIL', 'error_type': type(error).__name__,
                          'code': str(error) if isinstance(error, ValueError) and re.fullmatch('[A-Z0-9_]+', str(error)) else 'INPUT_OR_IO_ERROR'}))
        raise SystemExit(1)
