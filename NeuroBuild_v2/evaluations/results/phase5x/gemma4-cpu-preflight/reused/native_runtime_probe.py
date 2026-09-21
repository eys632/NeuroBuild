"""Import-only native evidence helpers. No launch, retry, CLI execution or import-time I/O.

Call only after root confirms CPU/header/VRAM gates. Generated bodies are never
returned by public_smoke, and resource_probe requests only scalar response fields.
"""
from datetime import datetime, timezone
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import resource
import sys
import time
from uuid import UUID

ROOT = Path('/home/a202192020/NeuroBuild_v2')
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from scripts.llama_server import NativeLaunchConfig, checked_file, load_proof, native_arguments, verified_hash
from scripts.verify_model_listeners import ProcReader, verify_listeners, save_report
from scripts.evaluate_requirements import native_runtime_metadata

TEMPLATE_SHA = 'c3cf9e34abf4f9e36c2d72165aa9c132d3e2a725b6c2586aaa3a8af9d7a81041'
PARITY_SHA = '79c4448b7ee949add0a80e8a7f0fc0d73575aaf01ff6e52beb3cfae8434ea1bd'
RUNTIME_VARIANT = 'qwen38-gguf-raw-unicode-v1'
REFERENCE_KIND = 'hf-tokenizer-json-with-nfc-normalizer-disabled'
RAW_REFERENCE_PATH = 'var/research/native-tokenizer-public-parity-raw-diagnostic.json'
RAW_REFERENCE_SHA = '9658eb53fae81adee1b775b45f796f3484db69aea41e04a020765fa05d770514'
HF_PROOF_PATH = 'var/research/native-vocab-public-probe-v4.json'
HF_PROOF_SHA = 'b537545d26a876a1496c2f85ad979330eba938f2880aae49190640b2404c63e0'
RAW_PROOF_PATH = 'var/research/native-vocab-public-probe-v4-raw-diagnostic.json'
RAW_PROOF_SHA = '12a5ebeafc16969f36435d9bb9e933ba12197d01ba05e8f26df41114f4e01d2d'
CPU_BUILD_SHA = 'f149c7eda01dda9b36f4dba9327cb368bbdf2e3c591fa7db287b47787be7aea0'
CPU_BINARY_SHA = '49a57a9630bd89e03940c07621d896d51efa32d502cca3d0736de48366563e5e'
CPU_CPP_SHA = '92ed10acd9be33d02d4cc6ea446dc2bea93ffb60b7d17ffc3c0f0268aab6c6b2'
CONTEXT_SPLITS = {
    'exposed120': (120, '7e5b9a05932df7aafdbf683655b044b3e3b25cbffb4115d298e1490aecbc7a5b'),
    'v2_length80': (80, '7416f05613b1490358672f3926770dbd8653e676577eeee6ba65f863b27cec40'),
}
HF_EQUIVALENCE = {'status': 'FAIL', 'case_count': 20, 'id_match_count': 19, 'mismatch_indices': [11],
    'proof_path': HF_PROOF_PATH, 'proof_sha256': HF_PROOF_SHA, 'original_fixture_sha256': PARITY_SHA}
RAW_REFERENCE = {'kind': REFERENCE_KIND, 'fixture_path': RAW_REFERENCE_PATH, 'fixture_sha256': RAW_REFERENCE_SHA,
    'native_proof_path': RAW_PROOF_PATH, 'native_proof_sha256': RAW_PROOF_SHA,
    'case_count': 20, 'id_match_count': 20, 'native_original_roundtrip_count': 20}
RESOURCE_FIELDS = ['tokens_evaluated', 'tokens_predicted', 'tokens_cached', 'truncated', 'stop', 'stop_type',
                   'timings/prompt_n', 'timings/predicted_n', 'timings/prompt_ms', 'timings/predicted_ms']
PUBLIC_SOURCE = '검사실 책상을 X축 양의 방향으로 1m 옮겨줘.'


def require(condition, code):
    if not condition:
        raise ValueError(code)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def read_json(path):
    path = checked_file(Path(path), ROOT)
    require(path.stat().st_size <= 2 * 1024 * 1024, 'INPUT_TOO_LARGE')
    raw = path.read_bytes()
    return json.loads(raw), raw


def load_config(path, expected):
    data, raw = read_json(path)
    require(digest(raw) == expected, 'CONFIG_HASH_MISMATCH')
    for key in ('binary_path', 'build_report', 'source_report', 'model_path', 'model_header_report', 'log_file', 'report_file'):
        data[key] = Path(data[key])
    config = NativeLaunchConfig(**data)
    require(config.enable_reasoning is False, 'NONTHINKING_REQUIRED')
    return config, raw


def binding(config):
    """Rehash small evidence/binary/libraries; GGUF hash was checked by live guard.

    Header and current owned GGUF size are bound here, not a second 19 GB hash.
    Caller must keep this epoch's model files immutable after guard verification.
    """
    source = load_proof(config.source_report, config.source_report_sha256, ROOT)
    build = load_proof(config.build_report, config.build_report_sha256, ROOT)
    header = load_proof(config.model_header_report, config.model_header_report_sha256, ROOT)
    require(source['kind'] == 'LLAMA_SOURCE_TOOL_BOOTSTRAP' and source['status'] == 'PASS'
            and source['llama_commit'] == config.source_commit, 'SOURCE_MISMATCH')
    for name, count in {'verified_blobs': 3607, 'verified_blob_bytes': 172243701, 'extra_or_missing_paths': 0}.items():
        require(source['source_verification'][name] == count, 'SOURCE_MISMATCH')
    require(build['status'] == 'COMPILE_PASS_NOT_RUNTIME_VALIDATED'
            and build['source_pin'] == config.source_commit
            and build['bootstrap_report_sha256'] == config.source_report_sha256
            and build['binary_sha256'] == config.binary_sha256, 'BUILD_MISMATCH')
    binary = checked_file(config.binary_path, ROOT)
    model = checked_file(config.model_path, ROOT)
    verified_hash(binary, config.binary_sha256)
    require(header['kind'] == 'GGUF_HEADER_AUDIT' and header['status'] == 'PASS'
            and header['model_path'] == str(model.relative_to(ROOT))
            and header['revision'] == config.model_revision and header['file_sha256'] == config.model_sha256
            and header['file_bytes'] == model.stat().st_size, 'HEADER_MISMATCH')
    real_names = set()
    for item in build['runtime_dependencies']:
        path = checked_file(Path(item['path']), ROOT)
        require(path.parent == binary.parent and path.name not in real_names, 'LIBRARY_PATH_MISMATCH')
        real_names.add(path.name)
        verified_hash(path, item['sha256'], expected_bytes=item['bytes'])
    validate_aliases(binary, build, real_names)
    return {'binary_sha256': config.binary_sha256, 'source_report_sha256': config.source_report_sha256,
            'build_report_sha256': config.build_report_sha256, 'source_commit': config.source_commit,
            'model_sha256': config.model_sha256, 'model_revision': config.model_revision,
            'model_header_report_sha256': config.model_header_report_sha256,
            'project_library_count': len(real_names)}


def validate_aliases(binary, build, real_names):
    aliases = set()
    listed_names = {Path(item['path']).name for item in build['runtime_dependency_symlinks']}
    for item in build['runtime_dependency_symlinks']:
        path, real = ROOT / item['path'], ROOT / item['real_path']
        target = item['target']
        require(path.parent == binary.parent and real.parent == binary.parent and real.name in real_names
                and type(target) is str and Path(target).name == target and target in real_names | listed_names
                and path.is_symlink() and os.readlink(path) == target
                and path.resolve() == real and path.name not in aliases, 'LIBRARY_ALIAS_MISMATCH')
        aliases.add(path.name)
    require(real_names and {p.name for p in binary.parent.glob('*.so*')} == real_names | aliases,
            'LIBRARY_INVENTORY_MISMATCH')


def validate_guard(config, report, artifacts):
    require(report['state'] == 'RUNNING' and report['runtime_family'] == 'llama_cpp'
            and report['native_identity_verified'] is True and report['physical_gpu_index'] == 3
            and report['required_cuda_visible_devices'] == '3' and report['max_model_len'] == 4096
            and report['max_num_seqs'] == 1
            and type(config.batch_size) is int and type(config.ubatch_size) is int
            and type(report['batch_size']) is int and type(report['ubatch_size']) is int
            and (report['batch_size'], report['ubatch_size']) == (config.batch_size, config.ubatch_size)
            and (config.batch_size, config.ubatch_size) in ((2, 1), (64, 64))
            and ((config.batch_size, config.ubatch_size) != (64, 64) or config.estimated_peak_mib >= 28672)
            and report['served_model_name'] == config.served_model_name
            and report['model_path'] == str(checked_file(config.model_path, ROOT))
            and report['native_artifacts'] == artifacts, 'GUARD_BINDING_MISMATCH')
    require(report['enable_reasoning'] is False and report['reasoning_parser'] == 'deepseek'
            and report['native_output_policy'] == 'DISCARD_STDOUT_STDERR'
            and report['native_core_dump_limit_bytes'] == 0, 'BODY_POLICY_MISMATCH')
    require(report['preflight']['allowed'] is True
            and report['minimum_observed_free_mib'] >= report['required_free_floor_mib']
            and report['observed_baseline_relative_peak_mib'] <= report['aggregate_increment_limit_mib'],
            'RESOURCE_FLOOR_FAILED')
    budget = report['preflight']['budget']
    require(report['preflight']['policy']['estimated_peak_mib'] == config.estimated_peak_mib
            and budget['estimated_startup_or_inference_peak_mib'] == config.estimated_peak_mib
            and report['peak_allowance_mib'] == config.peak_allowance_mib == 0
            and report['aggregate_increment_limit_mib'] == min(config.estimated_peak_mib, budget['available_model_budget_mib'])
            and report['required_free_floor_mib'] == budget['required_safety_margin_mib'], 'GUARD_BUDGET_MISMATCH')
    require(type(report['child_pid']) is int and report['child_pid'] > 1, 'PID_INVALID')
    require(0 <= report['elapsed_seconds'] < config.max_seconds, 'GUARD_TIME_EXHAUSTED')


def epoch(config, pid, expected_ticks=None):
    """Own UID only, pinned proc FD; never scans other processes."""
    with ProcReader(pid, os.getuid()) as proc:
        ticks = proc.identity()
        require(expected_ticks is None or ticks == expected_ticks, 'PROCESS_CHANGED')
        require(os.readlink('exe', dir_fd=proc.descriptor) == str(checked_file(config.binary_path, ROOT)),
                'EXECUTABLE_MISMATCH')
        require(proc.read_text('cmdline').rstrip('\0').split('\0') == native_arguments(config, ROOT),
                'COMMAND_MISMATCH')
        listeners = verify_listeners(pid)
        require(listeners['verdict'] == 'PASS' and listeners['process_start_ticks'] == ticks
                and any(item['address'] == '127.0.0.1' and item['port'] == config.port
                        for item in listeners['listeners']), 'LISTENER_MISMATCH')
        require(proc.identity() == ticks, 'PROCESS_CHANGED')
    return listeners


def request_json(port, route, payload=None, *, timeout=10, max_bytes=131072, connection=http.client.HTTPConnection):
    require(type(port) is int and 1024 <= port <= 65535, 'INVALID_PORT')
    require(route in ('/health', '/v1/models', '/props', '/completion'), 'INVALID_ROUTE')
    require(0 < timeout <= 1800 and type(max_bytes) is int and 0 < max_bytes <= 131072, 'INVALID_LIMIT')
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    body = None if payload is None else json.dumps(payload, ensure_ascii=False, allow_nan=False).encode()
    client = connection('127.0.0.1', port, timeout=timeout)
    started = time.monotonic()
    try:
        client.request('GET' if payload is None else 'POST', route, body=body,
                       headers={'Content-Type': 'application/json', 'Connection': 'close'})
        response = client.getresponse()
        require(response.status == 200, 'HTTP_STATUS_FAILED')
        require(response.getheader('Content-Encoding') in (None, 'identity'), 'UNSUPPORTED_ENCODING')
        raw = response.read(max_bytes + 1)
        require(len(raw) <= max_bytes and time.monotonic() - started <= timeout, 'RESPONSE_LIMIT_FAILED')
        result = json.loads(raw)
        require(type(result) is dict, 'RESPONSE_SHAPE_FAILED')
        return result, time.monotonic() - started
    finally:
        client.close()


def validate_health_models_props(config, health, models, props):
    require(health == {'status': 'ok'}, 'HEALTH_FAILED')
    rows = models.get('data')
    require(type(rows) is list and len(rows) == 1 and rows[0]['id'] == config.served_model_name
            and rows[0]['meta']['n_ctx'] == 4096, 'MODELS_MISMATCH')
    require(props['model_alias'] == config.served_model_name and props['total_slots'] == 1
            and props['model_path'] == str(checked_file(config.model_path, ROOT))
            and props['default_generation_settings']['n_ctx'] == 4096
            and digest(props['chat_template'].encode()) == TEMPLATE_SHA
            and props['is_sleeping'] is False, 'PROPS_MISMATCH')
    return {'health_http_status': 200, 'models_http_status': 200, 'props_http_status': 200,
            'served_model': config.served_model_name, 'model_path': props['model_path'],
            'max_model_len': 4096, 'max_sequences': 1, 'chat_template_sha256': TEMPLATE_SHA}


def resource_payload(token_id):
    require(type(token_id) is int and token_id >= 0, 'TOKEN_INVALID')
    return {'prompt': [token_id] * 3328, 'n_predict': 768, 'ignore_eos': True, 'cache_prompt': False,
            'stream': False, 'return_tokens': False, 'verbose': False, 'stop': [], 'n_probs': 0,
            'temperature': 0, 'seed': 42, 'repeat_penalty': 1, 'repeat_last_n': 0,
            'presence_penalty': 0, 'frequency_penalty': 0, 'samplers': ['temperature'],
            'response_fields': list(RESOURCE_FIELDS)}


def raw_context_provenance(context_proof_path, context_proof_sha, *, runtime_variant, model_sha, header_sha):
    require(runtime_variant == RUNTIME_VARIANT, 'EXPLICIT_RAW_VARIANT_REQUIRED')
    proof, proof_raw = read_json(context_proof_path)
    require(digest(proof_raw) == context_proof_sha
            and proof['kind'] == 'NATIVE_CONTEXT_RAW_UNICODE_CPU_PROOF'
            and proof['status'] == 'PASS' and proof['gguf_sha256'] == model_sha
            and proof['header_sha256'] == header_sha and proof['model_inference_calls'] == 0
            and proof['runtime_variant'] == RUNTIME_VARIANT and proof['reference_kind'] == REFERENCE_KIND
            and proof['context_tokenizer'] == 'native_raw_unicode_no_nfc_repair'
            and proof['application_input_output_nfc_repair'] is False
            and proof['hf_equivalence'] == HF_EQUIVALENCE and proof['raw_reference'] == RAW_REFERENCE,
            'RAW_CONTEXT_PROVENANCE_MISMATCH')
    require(proof['cpu_build_report_sha256'] == CPU_BUILD_SHA and proof['binary_sha256'] == CPU_BINARY_SHA
            and proof['cpu_cpp_source_sha256'] == CPU_CPP_SHA, 'RAW_CONTEXT_BINARY_MISMATCH')
    require(type(proof['max_output_tokens']) is int and proof['max_output_tokens'] == 768
            and type(proof['max_context_tokens']) is int and proof['max_context_tokens'] == 4096,
            'CONTEXT_LIMIT_BINDING_MISMATCH')
    require(set(proof['splits']) == set(CONTEXT_SPLITS), 'NATIVE_PARITY_PROOF_MISMATCH')
    for name, (count, dataset_sha) in CONTEXT_SPLITS.items():
        split = proof['splits'][name]
        require(type(split['input_count']) is int and split['input_count'] == count
                and split['dataset_sha256'] == dataset_sha
                and type(split['max_input_tokens']) is int and type(split['max_input_plus_output']) is int
                and 0 < split['max_input_tokens']
                and split['max_input_plus_output'] == split['max_input_tokens'] + 768 <= 4096
                and split['native']['status'] == 'PASS'
                and split['native']['native_tokenization'] == 'PASS_VOCAB_ONLY'
                and split['native']['tokenizer_metadata_parity'] == 'PASS'
                and split['native']['tokenizer_metadata_parity_cases'] == 20, 'NATIVE_PARITY_PROOF_MISMATCH')
    original, original_raw = read_json(ROOT / 'var/research/native-tokenizer-public-parity.json')
    derived, derived_raw = read_json(ROOT / RAW_REFERENCE_PATH)
    hf, hf_raw = read_json(ROOT / HF_PROOF_PATH)
    raw, raw_raw = read_json(ROOT / RAW_PROOF_PATH)
    require(digest(original_raw) == PARITY_SHA and digest(derived_raw) == RAW_REFERENCE_SHA
            and digest(hf_raw) == HF_PROOF_SHA and digest(raw_raw) == RAW_PROOF_SHA, 'REFERENCE_HASH_MISMATCH')
    require(original['status'] == 'FIXTURE_ONLY_NATIVE_PARITY_NOT_RUN'
            and derived['status'] == 'DERIVED_REFERENCE_NOT_OFFICIAL_HF_PARITY'
            and derived['original_fixture_sha256'] == PARITY_SHA
            and derived['original_hf_vs_raw_differing_indices'] == [11]
            and derived['original_hf_roundtrip_original_cases'] == 19
            and derived['derived_raw_roundtrip_original_cases'] == 20
            and derived['application_source_or_quotes_changed'] is False
            and len(original['tokenizer_parity']) == len(derived['tokenizer_parity']) == 20
            and [r['text'] for r in original['tokenizer_parity']] == [r['text'] for r in derived['tokenizer_parity']],
            'REFERENCE_SCOPE_MISMATCH')
    require(hf['reference_kind'] == 'official-hf' and hf['exit_code'] == 1 and hf['native']['status'] == 'FAIL'
            and hf['actual_reference_sha256'] == PARITY_SHA and hf['native']['parity_cases_checked'] == 20
            and hf['native']['parity_id_matches'] == 19 and hf['native']['parity_id_mismatches'] == 1
            and hf['native']['parity_mismatch_mask'] == 2048
            and hf['native']['parity_native_roundtrip_cases'] == 20, 'HF_FAILURE_EVIDENCE_MISMATCH')
    require(raw['reference_kind'] == 'raw-diagnostic' and raw['exit_code'] == 0 and raw['native']['status'] == 'PASS'
            and raw['actual_reference_sha256'] == RAW_REFERENCE_SHA
            and raw['native']['tokenizer_metadata_parity'] == 'PASS'
            and raw['native']['tokenizer_metadata_parity_cases'] == 20, 'RAW_REFERENCE_PROOF_MISMATCH')
    for observation in (hf, raw):
        require(observation['binary_sha256'] == CPU_BINARY_SHA and observation['build_report_sha256'] == CPU_BUILD_SHA
                and observation['cpp_sha256'] == CPU_CPP_SHA and observation['header_proof_sha256'] == header_sha
                and observation['gpu_calls'] == observation['model_inference_calls'] == 0, 'CPU_PROOF_EPOCH_MISMATCH')
    return {'runtime_variant': RUNTIME_VARIANT, 'reference_kind': REFERENCE_KIND,
            'context_cpu_proof_sha256': context_proof_sha, 'hf_equivalence': dict(HF_EQUIVALENCE),
            'raw_reference': dict(RAW_REFERENCE), 'context_tokenizer': 'native_raw_unicode_no_nfc_repair',
            'application_input_output_nfc_repair': False}


def ordinary_token():
    # Called only after raw_context_provenance at the entrypoint. Never relabel
    # the original official HF fixture's known mismatch as an exact match.
    parity, raw = read_json(ROOT / RAW_REFERENCE_PATH)
    require(digest(raw) == RAW_REFERENCE_SHA, 'REFERENCE_HASH_MISMATCH')
    rows = [r for r in parity['tokenizer_parity'] if r['text'] == ' ']
    require(len(rows) == 1 and len(rows[0]['expected_token_ids']) == 1, 'PUBLIC_TOKEN_MISSING')
    return rows[0]['expected_token_ids'][0]


def validate_resource(value):
    require(set(value) == set(RESOURCE_FIELDS), 'RESOURCE_RESPONSE_FIELDS_FAILED')
    for key in ('tokens_evaluated', 'tokens_predicted', 'tokens_cached', 'timings/prompt_n', 'timings/predicted_n'):
        require(type(value[key]) is int, 'RESOURCE_COUNTS_INVALID')
    require(value['tokens_evaluated'] == value['timings/prompt_n'] == 3328
            and value['tokens_predicted'] == value['timings/predicted_n'] == 768
            and value['tokens_cached'] == 4095
            and value['stop'] is True and value['truncated'] is True and value['stop_type'] == 'limit',
            'RESOURCE_BOUNDARY_NOT_REACHED')
    for key in ('timings/prompt_ms', 'timings/predicted_ms'):
        require(type(value[key]) in (int, float) and math.isfinite(value[key]) and value[key] >= 0,
                'RESOURCE_TIMING_INVALID')
    return {**value, 'probe_scope': '3328 uncached prompt tokens + 768 sampled tokens; 4095 cached positions',
            'grammar_enabled': False, 'quality_evaluation': False, 'generated_body_retained': False,
            'not_a_per_process_peak_measurement': True}


def make_metadata(config, platform, config_sha, startup_sha, listener_sha):
    require(set(platform) == {'compiler', 'cmake', 'cuda', 'driver', 'gpu', 'gpu_uuid'}, 'PLATFORM_FIELDS_INVALID')
    return native_runtime_metadata({**platform, 'runtime_kind': 'llama_cpp', 'profile': 'a100',
        'llama_cpp_commit': config.source_commit, 'cuda_architecture': '80-real', 'physical_gpu': 3,
        'logical_gpu': 0, 'max_model_len': 4096, 'max_sequences': 1, 'quantization': 'Q4_K_M',
        'enable_reasoning': False, 'reasoning_parser': 'deepseek', 'binary_sha256': config.binary_sha256,
        'source_provenance_sha256': config.source_report_sha256, 'build_report_sha256': config.build_report_sha256,
        'gguf_sha256': config.model_sha256, 'gguf_header_sha256': config.model_header_report_sha256,
        'chat_template_sha256': TEMPLATE_SHA, 'launch_config_sha256': config_sha,
        'startup_report_sha256': startup_sha, 'listener_report_sha256': listener_sha})


def public_smoke(config, *, runtime_variant, context_proof_path, context_proof_sha, timeout=120):
    """Exactly one production extraction call; caller must verify epoch before/after.

    Return only status and safe error code. Public request body is the existing
    CPU fixture. Reasoning/final response strings are neither printed nor saved.
    """
    from neurobuild.infrastructure.local_model import LocalRequirementClient
    from neurobuild.domain.errors import DomainError
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    provenance = raw_context_provenance(context_proof_path, context_proof_sha, runtime_variant=runtime_variant,
        model_sha=config.model_sha256, header_sha=config.model_header_report_sha256)
    client = LocalRequirementClient(f'http://127.0.0.1:{config.port}', config.served_model_name,
        prompt_path=ROOT / 'prompts/requirement_generation_v2_v2.txt',
        schema_path=ROOT / 'schemas/requirement_generation_v2_decision_branches.schema.json',
        generation_contract='2.0', protocol='llama_cpp_json_schema',
        sampling_profile='qwen38_nonthinking_llama_cpp', max_tokens=768, timeout=timeout)
    started = time.monotonic()
    try:
        result = client.extract(PUBLIC_SOURCE, requirement_id=UUID(int=1), project_id=UUID(int=2),
            base_revision_id=UUID(int=3), axis_convention='project_xy')
        ok = (result.status.value == 'READY' and result.operation.dx.metres == 1
              and result.operation.dy.metres == 0 and result.target_description == '검사실 책상')
        status, code = ('PASS', None) if ok else ('FAIL', 'PUBLIC_SEMANTIC_MISMATCH')
    except DomainError as error:
        status, code = 'FAIL', error.code
    return {**provenance, 'status': status, 'error_code': code, 'http_calls_attempted': 1,
            'elapsed_seconds': time.monotonic() - started, 'source': 'PUBLIC_SYNTHETIC_CPU_FIXTURE',
            'generated_body_retained': False, 'quality_gate_pass': False}


def capture_startup(config_path, config_sha, platform, *, runtime_variant, context_proof_path, context_proof_sha):
    """Future root-triggered three-GET probe; return five exact-byte JSON artifacts."""
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    config, config_raw = load_config(config_path, config_sha)
    provenance = raw_context_provenance(context_proof_path, context_proof_sha, runtime_variant=runtime_variant,
        model_sha=config.model_sha256, header_sha=config.model_header_report_sha256)
    artifacts = binding(config)
    before, _ = read_json(config.report_file)
    validate_guard(config, before, artifacts)
    first = epoch(config, before['child_pid'])
    health, _ = request_json(config.port, '/health')
    models, _ = request_json(config.port, '/v1/models')
    props, _ = request_json(config.port, '/props')
    summary = validate_health_models_props(config, health, models, props)
    listeners = epoch(config, before['child_pid'], first['process_start_ticks'])
    after, report_raw = read_json(config.report_file)
    validate_guard(config, after, artifacts)
    require((before['started_at_utc'], before['child_pid']) ==
            (after['started_at_utc'], after['child_pid']), 'GUARD_EPOCH_CHANGED')
    listener_raw = encoded(listeners)
    startup = {**summary, **provenance, 'kind': 'NATIVE_STARTUP_HTTP_PROOF', 'status': 'PASS',
               'at_utc': datetime.now(timezone.utc).isoformat(), 'pid': before['child_pid'],
               'process_start_ticks': first['process_start_ticks'], 'http_get_calls': 3,
               'model_inference_calls': 0, 'resource_report_sha256': digest(report_raw),
               'native_identity_verified': True, 'raw_http_bodies_saved': False,
               'installed_small_artifacts_rehashed': True,
               'gguf_binding': 'Live guard full hash + pinned header + current owned file size; no second full hash',
               'platform_facts_scope': 'Root-supplied measured platform facts; HTTP is not hardware attestation'}
    startup_raw = encoded(startup)
    metadata = make_metadata(config, platform, config_sha, digest(startup_raw), digest(listener_raw))
    return {'launch_config.json': config_raw, 'resource_report.json': report_raw,
            'listeners.json': listener_raw, 'startup.json': startup_raw,
            'runtime_metadata.json': encoded(metadata)}


def run_resource_smoke(config_path, config_sha, *, runtime_variant, context_proof_path, context_proof_sha, timeout=900):
    """Future explicit single POST. No retries or automatic process termination."""
    config, _ = load_config(config_path, config_sha)
    provenance = raw_context_provenance(context_proof_path, context_proof_sha, runtime_variant=runtime_variant,
        model_sha=config.model_sha256, header_sha=config.model_header_report_sha256)
    artifacts = binding(config)
    before, before_raw = read_json(config.report_file)
    validate_guard(config, before, artifacts)
    require(type(timeout) is int and 1 <= timeout <= 1800
            and config.max_seconds - before['elapsed_seconds'] >= timeout + 30,
            'INSUFFICIENT_GUARD_TIME')
    listeners = epoch(config, before['child_pid'])
    payload = resource_payload(ordinary_token())
    value, elapsed = request_json(config.port, '/completion', payload, timeout=timeout, max_bytes=8192)
    summary = validate_resource(value)
    epoch(config, before['child_pid'], listeners['process_start_ticks'])
    after, after_raw = read_json(config.report_file)
    validate_guard(config, after, artifacts)
    require((before['started_at_utc'], before['child_pid']) ==
            (after['started_at_utc'], after['child_pid']), 'GUARD_EPOCH_CHANGED')
    return {'kind': 'NATIVE_PUBLIC_CONTEXT_RESOURCE_PROBE', 'status': 'PASS', **summary, **provenance,
            'http_post_calls': 1, 'elapsed_seconds': elapsed, 'context_cpu_proof_sha256': context_proof_sha,
            'launch_config_sha256': config_sha, 'pid': before['child_pid'],
            'process_start_ticks': listeners['process_start_ticks'],
            'guard_started_at_utc': before['started_at_utc'],
            'request_sha256': digest(json.dumps(payload, ensure_ascii=False, allow_nan=False).encode()),
            'guard_before_sha256': digest(before_raw), 'guard_after_sha256': digest(after_raw),
            'guard_minimum_observed_free_mib': after['minimum_observed_free_mib'],
            'guard_aggregate_peak_mib': after['observed_baseline_relative_peak_mib'],
            'guard_required_free_floor_mib': after['required_free_floor_mib'],
            'guard_aggregate_increment_limit_mib': after['aggregate_increment_limit_mib'],
            'lifetime_aggregate_values_not_probe_isolated': True}


def write_bundle(output_dir, bundle):
    """Create an immutable new proof directory. Never overwrite inputs or prior proofs."""
    output_dir = Path(output_dir)
    base = ROOT / 'var/reports'
    require(output_dir.is_absolute() and output_dir.is_relative_to(base)
            and output_dir != base and not output_dir.exists() and not output_dir.is_symlink(), 'OUTPUT_PATH_INVALID')
    require(base.resolve() == base and output_dir.parent.resolve() == output_dir.parent
            and output_dir.parent.is_dir(), 'OUTPUT_PARENT_INVALID')
    require(all(type(name) is str and Path(name).name == name and name.endswith('.json')
                and type(raw) is bytes for name, raw in bundle.items()), 'OUTPUT_BUNDLE_INVALID')
    os.mkdir(output_dir, 0o700)
    for name, raw in bundle.items():
        with (output_dir / name).open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    for path in (output_dir, output_dir.parent):
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    return {name: digest(raw) for name, raw in bundle.items()}
