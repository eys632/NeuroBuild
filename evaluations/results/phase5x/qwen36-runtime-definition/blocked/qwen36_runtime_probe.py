"""Qwen3.6 BLOCKED runtime definitions; no current candidate runtime eligibility.

Import checks the historical generic helper hash, but never contacts a server,
reads a process, loads a model, runs native code or creates a proof. No CLI/main.
Response text, reasoning, props template and token arrays are not persisted.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import resource
import time
from types import ModuleType
from uuid import UUID

ROOT = Path('/home/a202192020/NeuroBuild_v2')
BASE_PATH = ROOT / 'var/research/native_runtime_probe.py'
BASE_SHA = 'ac100df7949b2b14a517c4568fa66369bd98c599b39507ef19f873490a0f9f63'
_base_bytes = BASE_PATH.read_bytes()
if hashlib.sha256(_base_bytes).hexdigest() != BASE_SHA:
    raise ValueError('GENERIC_HELPER_HASH_MISMATCH')
base = ModuleType('qwen36_pinned_generic_probe')
base.__file__ = str(BASE_PATH)
exec(compile(_base_bytes, str(BASE_PATH), 'exec'), base.__dict__)
del _base_bytes
# Deliberately exclude all historical Qwen provenance/template/client helpers.
require, digest, encoded, read_json = base.require, base.digest, base.encoded, base.read_json
load_config, binding, validate_guard, epoch = base.load_config, base.binding, base.validate_guard, base.epoch
request_json, resource_payload, validate_resource = base.request_json, base.resource_payload, base.validate_resource
write_bundle = base.write_bundle

MODEL_ID = 'ggml-org/Qwen3.6-35B-A3B-GGUF'
REVISION = 'baec3ebee244827cda0f4557eafa8b28f7545fa6'
MODEL_SHA = '671e47e0ec53c665d048b98c3ecbfd5236b5ca9c3e02ed19fc8f81f7b85140c7'
MODEL_BYTES = 20419565568
TEMPLATE_SHA = 'e84f32a23fdda27689f868aa4a1a5621f41133e51a48d7f3efcbea2839574259'
# Saved source has zero CR and no terminal LF. Pinned jinja/lexer.cpp:42-58
# therefore preserves its bytes; the actual GGUF and live props remain pending.
PROPS_TEMPLATE_SHA = TEMPLATE_SHA
PROPS_TEMPLATE_BYTES = 7764
EMBEDDED_TEMPLATE_BYTES = 7764
TOKENIZER_SHA = '5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
PROFILE = 'qwen36_nonthinking_llama_cpp'
SAMPLING = {
    'temperature': 0.7, 'top_p': 0.8, 'top_k': 20, 'min_p': 0.0,
    'presence_penalty': 1.5, 'frequency_penalty': 0.0,
    'repeat_penalty': 1.0, 'repeat_last_n': 64, 'seed': 42,
    'samplers': ['penalties', 'top_k', 'top_p', 'min_p', 'temperature'],
}
HEADER_SHA = None
FINAL_CPU_SHA = None
CPU_REFS = None
TEMPLATE_INPUT_EQUIVALENCE = None
CANDIDATE_VARIANT = None  # Root must explicitly decide the raw-Unicode contract.
QUANTIZATION = 'Q4_K_M'  # Published-log expectation; actual header gate remains pending.
PREPARATION_STATUS = 'BLOCKED_HEADER_CPU_CONTRACT_AND_ROOT_ACTIVATION_PENDING'
CPU_KIND = 'QWEN36_NATIVE_CONTRACT_CPU_PROOF'
CPU_STATUS = 'PASS_CURRENT_PUBLIC_AND_CARRIED_EXPOSED120'
RUNTIME_LAUNCHER_SHA = '6a58ee1ea09636df182125da4a4a2711012e6c53f5f90c06548a63b9915369ed'
CPU_SOURCE_PINS = {
    'src/neurobuild/infrastructure/local_model.py': '0814c6a5a695c3abb3c4c6cf244990bd569ed372840b1786d2b488e72e0f3120',
    'src/neurobuild/application/requirement_generation.py': 'fcba16f6adc906923859f3bcf4ae2f680e76716863a759582167cd9326f03198',
    'src/neurobuild/application/requirements.py': 'a940f3952c0c4133ab51732f6abf76516d8ff66617470545222b52adfa49fb4a',
    'prompts/requirement_generation_v2_v2.txt': '99d737124372836ba5f985fa6e5570afef693e769798844931f000fb21403cf6',
    'schemas/requirement_generation_v2_decision_branches.schema.json': '36d42b9fa3d24f4a1bc1d14381110e36e8d89103b696bc83113be006b64934e2',
}
EVALUATOR_SHA = '1915ee707cb6dca4f9f6927b760b0bdce1c1c5d6929837be489dafc97fb0cbfd'
HISTORICAL_MODEL = 'ggml-org/Qwen3.8-27B-GGUF'
HISTORICAL_OFFICIAL = {'status': 'FAIL', 'case_count': 20, 'id_match_count': 19,
    'mismatch_indices': [11], 'native_original_roundtrip_count': 20}
HISTORICAL_RAW = {'status': 'PASS', 'case_count': 20, 'id_match_count': 20,
    'reference_kind': 'hf-tokenizer-json-with-nfc-normalizer-disabled'}
EXPOSED_SOURCE_SHA = '7e5b9a05932df7aafdbf683655b044b3e3b25cbffb4115d298e1490aecbc7a5b'
CPU_REF_KEYS = {'header', 'tokenizer_comparison', 'public_contract', 'public_build',
    'historical_header', 'historical_context', 'historical_official', 'historical_raw',
    'historical_raw_fixture', 'source_equivalence'}


def require_ready():
    raise ValueError('QWEN36_HEADER_CPU_CONTRACT_ROOT_ACTIVATION_PENDING')


PUBLIC_SOURCE = '검사실 책상을 X축 양의 방향으로 1m 옮겨줘.'
def qwen_binding(config):
    require_ready()
    require(config.model_revision == REVISION and config.model_sha256 == MODEL_SHA
            and config.source_commit == 'f072b103714dfa1eee531f80b24512faf38e3dd2'
            and config.enable_reasoning is False
            and (config.batch_size, config.ubatch_size) == (64, 64)
            and config.estimated_peak_mib == 28672 and config.peak_allowance_mib == 0
            and config.profile == 'a100' and config.port == 8003 and config.max_seconds == 7200
            and config.served_model_name == 'neurobuild-qwen36-35b-a3b-q4-k-m'
            and config.chat_template_path is None and config.chat_template_sha256 is None,
            'QWEN36_CONFIG_MISMATCH')
    artifacts = binding(config)
    header, raw = read_json(config.model_header_report)
    require(digest(raw) == config.model_header_report_sha256
            and digest(raw) == HEADER_SHA
            and header['file_bytes'] == MODEL_BYTES and header['model_id'] == MODEL_ID
            and header['bindings']['embedded_template_sha256'] == TEMPLATE_SHA
            and header['bindings']['quantization'] == QUANTIZATION, 'QWEN36_HEADER_MISMATCH')
    return artifacts


def cpu_provenance(config, proof_path, proof_sha):
    """Draft saved-only consumer for the exact typed-vocab/input-equivalent route.

    No old provenance helper or corpus validator is invoked. This route can be
    finalized only after actual new-header/comparison/public-template evidence;
    a token delta or non-equivalent template needs a separately reviewed route.
    """
    require_ready()
    require(type(FINAL_CPU_SHA) is str and proof_sha == FINAL_CPU_SHA, 'QWEN36_FINAL_CPU_HASH_MISMATCH')
    proof, raw = read_json(proof_path)
    require(digest(raw) == proof_sha and proof['kind'] == CPU_KIND and proof['status'] == CPU_STATUS
            and proof['model_id'] == MODEL_ID and proof['candidate_variant'] == CANDIDATE_VARIANT
            and proof['revision'] == REVISION and proof['gguf_sha256'] == MODEL_SHA == config.model_sha256
            and proof['header_sha256'] == HEADER_SHA == config.model_header_report_sha256
            and proof['template_sha256'] == TEMPLATE_SHA and proof['tokenizer_json_sha256'] == TOKENIZER_SHA
            and proof['source_pin'] == config.source_commit == 'f072b103714dfa1eee531f80b24512faf38e3dd2'
            and proof['protocol'] == 'llama_cpp_json_schema' and proof['sampling_profile'] == PROFILE
            and proof['sampling_request_parameters'] == SAMPLING
            and proof['sampling_equivalent'] is False
            and proof['application_input_output_nfc_repair'] is False
            and proof['template_override_used'] is False,
            'QWEN36_CPU_PROVENANCE_MISMATCH')
    require(type(proof['max_output_tokens']) is int and proof['max_output_tokens'] == 768
            and type(proof['max_context_tokens']) is int and proof['max_context_tokens'] == 4096,
            'QWEN36_CONTEXT_LIMIT_MISMATCH')
    require(proof['source_sha256'] == CPU_SOURCE_PINS, 'QWEN36_CPU_SOURCE_SET_MISMATCH')
    for path, expected in {**CPU_SOURCE_PINS, 'scripts/llama_server.py': RUNTIME_LAUNCHER_SHA,
                           'scripts/evaluate_requirements.py': EVALUATOR_SHA}.items():
        source_file = base.checked_file(ROOT / path, ROOT)
        require(source_file.stat().st_size <= 1024 * 1024 and digest(source_file.read_bytes()) == expected,
                'QWEN36_CURRENT_SOURCE_HASH_MISMATCH')
    require(proof['historical_hf_equivalence'] == HISTORICAL_OFFICIAL
            and proof['historical_raw_reference'] == HISTORICAL_RAW,
            'QWEN36_HISTORICAL_TOKENIZER_BOUNDARY_MISMATCH')
    require(type(TEMPLATE_INPUT_EQUIVALENCE) is dict
            and proof['template_input_equivalence'] == TEMPLATE_INPUT_EQUIVALENCE,
            'QWEN36_EFFECTIVE_INPUT_EQUIVALENCE_PENDING')
    require(set(proof['splits']) == {'exposed120'}, 'QWEN36_CONTEXT_SPLITS_MISMATCH')
    row = proof['splits']['exposed120']
    expected_row = {'dataset_sha256': EXPOSED_SOURCE_SHA, 'input_count': 120,
        'min_input_tokens': 2133, 'max_input_tokens': 2409, 'max_input_plus_output': 3177,
        'measurement_kind': 'CARRIED_FORWARD', 'measured_model_id': HISTORICAL_MODEL}
    require(row == expected_row and all(type(row[k]) is int for k in
            ('input_count', 'min_input_tokens', 'max_input_tokens', 'max_input_plus_output'))
            and row['max_input_tokens'] + 768 == row['max_input_plus_output'] <= 4096,
            'QWEN36_CARRIED_EXPOSED_COUNTS_MISMATCH')
    expected_executions = {'public_request_count': 1, 'native_compile_count': 1,
        'context_request_count': 0, 'public_parity_cases': 0, 'old_corpus_replays': 0,
        'model_inference': 0, 'http': 0, 'gpu': 0}
    require(proof['new_executions'] == expected_executions
            and all(type(v) is int for v in proof['new_executions'].values()),
            'QWEN36_CPU_EXECUTION_SCOPE_MISMATCH')
    require(type(CPU_REFS) is dict and set(CPU_REFS) == CPU_REF_KEYS
            and proof['proof_refs'] == CPU_REFS, 'QWEN36_CPU_REFERENCE_CLOSURE_PENDING')
    for ref in proof['proof_refs'].values():
        require(set(ref) == {'path', 'sha256'} and type(ref['path']) is str
                and not Path(ref['path']).is_absolute() and '..' not in Path(ref['path']).parts,
                'QWEN36_CPU_REFERENCE_PATH_INVALID')
        _, linked_raw = read_json(ROOT / ref['path'])
        require(digest(linked_raw) == ref['sha256'], 'QWEN36_CPU_REFERENCE_HASH_MISMATCH')
    token = proof['resource_probe_token']
    require(token == {'text': ' ', 'token_id': 220, 'native_token_count': 1,
            'native_roundtrip': True, 'measurement_kind': 'CARRIED_FORWARD_BY_TYPED_VOCAB_EQUALITY'}
            and type(token['token_id']) is int and type(token['native_token_count']) is int,
            'QWEN36_PUBLIC_TOKEN_INVALID')
    require(type(proof['normalization_limitation']) is str and 0 < len(proof['normalization_limitation']) <= 4096,
            'QWEN36_NORMALIZATION_LIMITATION_MISSING')
    return ({'candidate_variant': CANDIDATE_VARIANT, 'model_id': MODEL_ID, 'model_revision': REVISION,
             'cpu_proof_sha256': proof_sha, 'cpu_proof_kind': CPU_KIND, 'cpu_proof_status': CPU_STATUS,
             'chat_template_sha256': TEMPLATE_SHA, 'tokenizer_json_sha256': TOKENIZER_SHA,
             'tokenizer_contract': 'historical_raw_reference_by_exact_typed_metadata_and_restricted_input_equivalence',
             'historical_hf_equivalence': HISTORICAL_OFFICIAL, 'historical_raw_reference': HISTORICAL_RAW,
             'template_input_equivalence': proof['template_input_equivalence'], 'exposed_context': row,
             'application_input_output_nfc_repair': False, 'sampling_equivalent': False,
             'cpu_proof_refs': proof['proof_refs'], 'cpu_source_sha256': proof['source_sha256'],
             'normalization_limitation': proof['normalization_limitation'],
             'new_cpu_executions': proof['new_executions'], 'cpu_checks_rerun': False}, token['token_id'])


def validate_health_models_props(config, health, models, props):
    require(health == {'status': 'ok'}, 'HEALTH_FAILED')
    rows = models.get('data')
    require(type(rows) is list and len(rows) == 1 and rows[0]['id'] == config.served_model_name
            and type(rows[0]['meta']['n_ctx']) is int and rows[0]['meta']['n_ctx'] == 4096,
            'MODELS_MISMATCH')
    require(props['model_alias'] == config.served_model_name and type(props['total_slots']) is int
            and props['total_slots'] == 1 and props['model_path'] == str(base.checked_file(config.model_path, ROOT))
            and type(props['default_generation_settings']['n_ctx']) is int
            and props['default_generation_settings']['n_ctx'] == 4096
            and type(props['chat_template']) is str
            and len(props['chat_template'].encode()) == PROPS_TEMPLATE_BYTES
            and digest(props['chat_template'].encode()) == PROPS_TEMPLATE_SHA
            and props['is_sleeping'] is False, 'PROPS_MISMATCH')
    return {'health_http_status': 200, 'models_http_status': 200, 'props_http_status': 200,
            'served_model': config.served_model_name, 'model_path': props['model_path'],
            'max_model_len': 4096, 'max_sequences': 1, 'chat_template_sha256': TEMPLATE_SHA,
            'embedded_chat_template_sha256': TEMPLATE_SHA, 'embedded_chat_template_bytes': EMBEDDED_TEMPLATE_BYTES,
            'props_reported_template_sha256': PROPS_TEMPLATE_SHA,
            'props_reported_template_bytes': PROPS_TEMPLATE_BYTES,
            'props_template_derivation': 'Official source has no CR or terminal LF; expected raw embedded and props source bytes equal; no application input/output repair'}


def make_metadata(config, platform, config_sha, startup_sha, listener_sha):
    require(set(platform) == {'compiler', 'cmake', 'cuda', 'driver', 'gpu', 'gpu_uuid'}, 'PLATFORM_FIELDS_INVALID')
    return base.native_runtime_metadata({**platform, 'runtime_kind': 'llama_cpp', 'profile': 'a100',
        'llama_cpp_commit': config.source_commit, 'cuda_architecture': '80-real', 'physical_gpu': 3,
        'logical_gpu': 0, 'max_model_len': 4096, 'max_sequences': 1, 'quantization': QUANTIZATION,
        'enable_reasoning': False, 'reasoning_parser': 'deepseek', 'binary_sha256': config.binary_sha256,
        'source_provenance_sha256': config.source_report_sha256, 'build_report_sha256': config.build_report_sha256,
        'gguf_sha256': config.model_sha256, 'gguf_header_sha256': config.model_header_report_sha256,
        'chat_template_sha256': TEMPLATE_SHA, 'launch_config_sha256': config_sha,
        'startup_report_sha256': startup_sha, 'listener_report_sha256': listener_sha})


def begin(config_path, config_sha, cpu_proof_path, cpu_proof_sha, *, timeout=0):
    require_ready()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    config, config_raw = load_config(config_path, config_sha)
    provenance, token_id = cpu_provenance(config, cpu_proof_path, cpu_proof_sha)
    artifacts = qwen_binding(config)
    before, before_raw = read_json(config.report_file)
    validate_guard(config, before, artifacts)
    require(type(timeout) is int and 0 <= timeout <= 1800
            and config.max_seconds - before['elapsed_seconds'] >= timeout + 30, 'INSUFFICIENT_GUARD_TIME')
    listeners = epoch(config, before['child_pid'])
    return config, config_raw, provenance, token_id, artifacts, before, before_raw, listeners


def finish(config, config_sha, artifacts, before, before_raw, first):
    listeners = epoch(config, before['child_pid'], first['process_start_ticks'])
    after, after_raw = read_json(config.report_file)
    validate_guard(config, after, artifacts)
    require((before['started_at_utc'], before['child_pid']) == (after['started_at_utc'], after['child_pid'])
            and after['elapsed_seconds'] >= before['elapsed_seconds'], 'GUARD_EPOCH_CHANGED')
    fields = {'launch_config_sha256': config_sha, 'pid': before['child_pid'],
              'process_start_ticks': first['process_start_ticks'], 'guard_started_at_utc': before['started_at_utc'],
              'guard_before_sha256': digest(before_raw), 'guard_after_sha256': digest(after_raw),
              'listener_report_sha256': digest(encoded(listeners))}
    return fields, after, after_raw, listeners


def capture_startup(config_path, config_sha, platform, *, cpu_proof_path, cpu_proof_sha):
    config, config_raw, provenance, _, artifacts, before, before_raw, first = begin(
        config_path, config_sha, cpu_proof_path, cpu_proof_sha, timeout=30)
    health, _ = request_json(config.port, '/health')
    models, _ = request_json(config.port, '/v1/models')
    props, _ = request_json(config.port, '/props')
    summary = validate_health_models_props(config, health, models, props)
    fields, _, after_raw, listeners = finish(config, config_sha, artifacts, before, before_raw, first)
    startup = {**summary, **provenance, **fields, 'kind': 'QWEN36_NATIVE_STARTUP_HTTP_PROOF', 'status': 'PASS',
        'at_utc': datetime.now(timezone.utc).isoformat(), 'http_get_calls': 3, 'model_inference_calls': 0,
        'model_inference_calls_scope': 'Explicit HTTP generation calls; native startup warmup is enabled and not counted',
        'native_startup_warmup_enabled': True,
        'native_startup_warmup_evidence': 'Pinned source default: common/common.h:579 and common/common.cpp:1511-1545; not an observed decode counter',
        'resource_report_sha256': digest(after_raw), 'native_identity_verified': True,
        'raw_http_bodies_saved': False, 'installed_small_artifacts_rehashed': True,
        'gguf_binding': 'Live guard full hash + pinned header + current owned file size; no second full hash',
        'platform_facts_scope': 'Root-supplied measured platform facts; HTTP is not hardware attestation'}
    startup_raw, listener_raw = encoded(startup), encoded(listeners)
    metadata = make_metadata(config, platform, config_sha, digest(startup_raw), digest(listener_raw))
    return {'launch_config.json': config_raw, 'resource_report.json': after_raw,
            'listeners.json': listener_raw, 'startup.json': startup_raw, 'runtime_metadata.json': encoded(metadata)}


def public_smoke(config_path, config_sha, *, cpu_proof_path, cpu_proof_sha, timeout=120):
    from neurobuild.infrastructure.local_model import LocalRequirementClient
    from neurobuild.domain.errors import DomainError
    config, _, provenance, _, artifacts, before, before_raw, first = begin(
        config_path, config_sha, cpu_proof_path, cpu_proof_sha, timeout=timeout)
    client = LocalRequirementClient(f'http://127.0.0.1:{config.port}', config.served_model_name,
        prompt_path=ROOT / 'prompts/requirement_generation_v2_v2.txt',
        schema_path=ROOT / 'schemas/requirement_generation_v2_decision_branches.schema.json',
        generation_contract='2.0', protocol='llama_cpp_json_schema', sampling_profile=PROFILE,
        max_tokens=768, timeout=timeout)
    require(client.sampling_parameters == SAMPLING and client.enable_thinking is False, 'QWEN36_CLIENT_RECIPE_MISMATCH')
    started = time.monotonic()
    try:
        result = client.extract(PUBLIC_SOURCE, requirement_id=UUID(int=1), project_id=UUID(int=2),
                                base_revision_id=UUID(int=3), axis_convention='project_xy')
        ok = (result.status.value == 'READY' and result.operation.dx.metres == 1
              and result.operation.dy.metres == 0 and result.target_description == '검사실 책상')
        status, code = ('PASS', None) if ok else ('FAIL', 'PUBLIC_SEMANTIC_MISMATCH')
    except DomainError as error:
        status, code = 'FAIL', error.code
    elapsed = time.monotonic() - started
    fields, _, _, _ = finish(config, config_sha, artifacts, before, before_raw, first)
    return {**provenance, **fields, 'kind': 'QWEN36_NATIVE_PUBLIC_PRODUCTION_SMOKE',
            'status': status, 'error_code': code, 'http_calls_attempted': 1, 'elapsed_seconds': elapsed,
            'sampling_profile': PROFILE, 'source': 'PUBLIC_SYNTHETIC_CPU_FIXTURE',
            'generated_body_retained': False, 'quality_gate_pass': False}


def run_resource_smoke(config_path, config_sha, *, cpu_proof_path, cpu_proof_sha, timeout=900):
    config, _, provenance, token_id, artifacts, before, before_raw, first = begin(
        config_path, config_sha, cpu_proof_path, cpu_proof_sha, timeout=timeout)
    payload = resource_payload(token_id)
    value, elapsed = request_json(config.port, '/completion', payload, timeout=timeout, max_bytes=8192)
    summary = validate_resource(value)
    fields, after, _, _ = finish(config, config_sha, artifacts, before, before_raw, first)
    return {**summary, **provenance, **fields, 'kind': 'QWEN36_NATIVE_PUBLIC_CONTEXT_RESOURCE_PROBE', 'status': 'PASS',
            'http_post_calls': 1, 'elapsed_seconds': elapsed,
            'request_sha256': digest(json.dumps(payload, ensure_ascii=False, allow_nan=False).encode()),
            'guard_minimum_observed_free_mib': after['minimum_observed_free_mib'],
            'guard_aggregate_peak_mib': after['observed_baseline_relative_peak_mib'],
            'guard_required_free_floor_mib': after['required_free_floor_mib'],
            'guard_aggregate_increment_limit_mib': after['aggregate_increment_limit_mib'],
            'lifetime_aggregate_values_not_probe_isolated': True}
