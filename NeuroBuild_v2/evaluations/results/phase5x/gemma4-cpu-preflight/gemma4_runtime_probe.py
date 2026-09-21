"""Import-only Gemma4 evidence helpers; root explicitly calls after CPU/VRAM gates.

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
base = ModuleType('gemma4_pinned_generic_probe')
base.__file__ = str(BASE_PATH)
exec(compile(_base_bytes, str(BASE_PATH), 'exec'), base.__dict__)
del _base_bytes
# Deliberately exclude all historical Qwen provenance/template/client helpers.
require, digest, encoded, read_json = base.require, base.digest, base.encoded, base.read_json
load_config, binding, validate_guard, epoch = base.load_config, base.binding, base.validate_guard, base.epoch
request_json, resource_payload, validate_resource = base.request_json, base.resource_payload, base.validate_resource
write_bundle = base.write_bundle

MODEL_ID = 'google/gemma-4-31B-it-qat-q4_0-gguf'
REVISION = '59dde24573e7e61570dba08b18a2e1fe246955ed'
MODEL_SHA = '179cfb99212709597eae5929112cfca677e1bbf566178b479ae1da0c4772874b'
MODEL_BYTES = 17651001568
TEMPLATE_SHA = 'ae53464bf3be25802b3a5b37def7fd89667067d7577049b3b2d74c4d8de4c6d4'
TOKENIZER_SHA = 'cc8d3a0ce36466ccc1278bf987df5f71db1719b9ca6b4118264f45cb627bfe0f'
PROFILE = 'gemma4_nonthinking_llama_cpp'
CPU_SOURCE_PATHS = {
    'src/neurobuild/infrastructure/local_model.py',
    'src/neurobuild/application/requirement_generation.py',
    'src/neurobuild/application/requirements.py',
    'prompts/requirement_generation_v2_v2.txt',
    'schemas/requirement_generation_v2_decision_branches.schema.json',
}
PUBLIC_SOURCE = '검사실 책상을 X축 양의 방향으로 1m 옮겨줘.'
CONTEXT_SPLITS = {
    'exposed120': (120, '7e5b9a05932df7aafdbf683655b044b3e3b25cbffb4115d298e1490aecbc7a5b'),
    'v2_length80': (80, '7416f05613b1490358672f3926770dbd8653e676577eeee6ba65f863b27cec40'),
}


def gemma_binding(config):
    require(config.model_revision == REVISION and config.model_sha256 == MODEL_SHA
            and config.source_commit == 'f072b103714dfa1eee531f80b24512faf38e3dd2'
            and config.enable_reasoning is False
            and (config.batch_size, config.ubatch_size) == (64, 64), 'GEMMA_CONFIG_MISMATCH')
    artifacts = binding(config)
    header, raw = read_json(config.model_header_report)
    require(digest(raw) == config.model_header_report_sha256
            and header['file_bytes'] == MODEL_BYTES, 'GEMMA_HEADER_MISMATCH')
    return artifacts


def cpu_provenance(config, proof_path, proof_sha):
    """Final public-template + official-vocab/context CPU gate; never run it here.

    The caller supplies the reviewed aggregate proof's exact hash. Linked small
    evidence hashes are checked again; datasets/tensors are never opened here.
    """
    proof, raw = read_json(proof_path)
    require(digest(raw) == proof_sha and proof['kind'] == 'GEMMA4_NATIVE_CONTRACT_CPU_PROOF'
            and proof['status'] == 'PASS' and proof['model_id'] == MODEL_ID
            and proof['protocol'] == 'llama_cpp_json_schema' and proof['sampling_profile'] == PROFILE
            and proof['source_pin'] == config.source_commit == 'f072b103714dfa1eee531f80b24512faf38e3dd2'
            and proof['revision'] == REVISION and proof['gguf_sha256'] == MODEL_SHA == config.model_sha256
            and proof['header_sha256'] == config.model_header_report_sha256
            and proof['template_sha256'] == TEMPLATE_SHA and proof['tokenizer_json_sha256'] == TOKENIZER_SHA
            and type(proof['model_inference_calls']) is int and proof['model_inference_calls'] == 0
            and proof['application_input_output_nfc_repair'] is False, 'GEMMA_CPU_PROVENANCE_MISMATCH')
    require(type(proof['max_output_tokens']) is int and proof['max_output_tokens'] == 768
            and type(proof['max_context_tokens']) is int and proof['max_context_tokens'] == 4096,
            'GEMMA_CONTEXT_LIMIT_MISMATCH')
    require(proof['official_tokenizer_parity'] == {'status': 'PASS', 'case_count': 20,
            'id_match_count': 20, 'native_original_roundtrip_count': 20}, 'GEMMA_OFFICIAL_PARITY_REQUIRED')
    require(set(proof['splits']) == set(CONTEXT_SPLITS), 'GEMMA_CONTEXT_SPLITS_MISMATCH')
    for name, (count, sha) in CONTEXT_SPLITS.items():
        row = proof['splits'][name]
        require(type(row['input_count']) is int and row['input_count'] == count
                and row['dataset_sha256'] == sha
                and type(row['min_input_tokens']) is int and type(row['max_input_tokens']) is int
                and 0 < row['min_input_tokens'] <= row['max_input_tokens']
                and type(row['max_input_plus_output']) is int
                and row['max_input_plus_output'] == row['max_input_tokens'] + 768 <= 4096,
                'GEMMA_CONTEXT_SPLIT_MISMATCH')
    require(set(proof['source_sha256']) == CPU_SOURCE_PATHS, 'GEMMA_CPU_SOURCE_SET_MISMATCH')
    for path, expected in proof['source_sha256'].items():
        source_file = base.checked_file(ROOT / path, ROOT)
        require(source_file.stat().st_size <= 1024 * 1024
                and digest(source_file.read_bytes()) == expected, 'GEMMA_CPU_SOURCE_HASH_MISMATCH')
    require(set(proof['proof_refs']) == {'public_contract', 'vocab_context', 'tokenizer_fixture'},
            'GEMMA_CPU_REFERENCES_MISMATCH')
    for ref in proof['proof_refs'].values():
        require(set(ref) == {'path', 'sha256'} and type(ref['path']) is str
                and not Path(ref['path']).is_absolute() and '..' not in Path(ref['path']).parts,
                'GEMMA_CPU_REFERENCE_PATH_INVALID')
        _, linked_raw = read_json(ROOT / ref['path'])
        require(digest(linked_raw) == ref['sha256'], 'GEMMA_CPU_REFERENCE_HASH_MISMATCH')
    token = proof['resource_probe_token']
    require(set(token) == {'text', 'token_id', 'native_token_count', 'native_roundtrip'}
            and token['text'] == ' ' and type(token['token_id']) is int and 0 <= token['token_id'] < 262144
            and type(token['native_token_count']) is int and token['native_token_count'] == 1
            and token['native_roundtrip'] is True, 'GEMMA_PUBLIC_TOKEN_INVALID')
    return ({'model_id': MODEL_ID, 'model_revision': REVISION, 'cpu_proof_sha256': proof_sha,
             'cpu_proof_kind': proof['kind'], 'chat_template_sha256': TEMPLATE_SHA,
             'tokenizer_json_sha256': TOKENIZER_SHA,
             'tokenizer_contract': 'official_qat_metadata_native_public_parity_20_of_20',
             'official_tokenizer_parity': dict(proof['official_tokenizer_parity']),
             'application_input_output_nfc_repair': False,
             'cpu_proof_refs': proof['proof_refs'], 'cpu_source_sha256': proof['source_sha256'],
             'cpu_checks_rerun': False}, token['token_id'])


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
            and type(props['chat_template']) is str and digest(props['chat_template'].encode()) == TEMPLATE_SHA
            and props['is_sleeping'] is False, 'PROPS_MISMATCH')
    return {'health_http_status': 200, 'models_http_status': 200, 'props_http_status': 200,
            'served_model': config.served_model_name, 'model_path': props['model_path'],
            'max_model_len': 4096, 'max_sequences': 1, 'chat_template_sha256': TEMPLATE_SHA}


def make_metadata(config, platform, config_sha, startup_sha, listener_sha):
    require(set(platform) == {'compiler', 'cmake', 'cuda', 'driver', 'gpu', 'gpu_uuid'}, 'PLATFORM_FIELDS_INVALID')
    return base.native_runtime_metadata({**platform, 'runtime_kind': 'llama_cpp', 'profile': 'a100',
        'llama_cpp_commit': config.source_commit, 'cuda_architecture': '80-real', 'physical_gpu': 3,
        'logical_gpu': 0, 'max_model_len': 4096, 'max_sequences': 1, 'quantization': 'Q4_0',
        'enable_reasoning': False, 'reasoning_parser': 'deepseek', 'binary_sha256': config.binary_sha256,
        'source_provenance_sha256': config.source_report_sha256, 'build_report_sha256': config.build_report_sha256,
        'gguf_sha256': config.model_sha256, 'gguf_header_sha256': config.model_header_report_sha256,
        'chat_template_sha256': TEMPLATE_SHA, 'launch_config_sha256': config_sha,
        'startup_report_sha256': startup_sha, 'listener_report_sha256': listener_sha})


def begin(config_path, config_sha, cpu_proof_path, cpu_proof_sha, *, timeout=0):
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    config, config_raw = load_config(config_path, config_sha)
    provenance, token_id = cpu_provenance(config, cpu_proof_path, cpu_proof_sha)
    artifacts = gemma_binding(config)
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
    startup = {**summary, **provenance, **fields, 'kind': 'GEMMA4_NATIVE_STARTUP_HTTP_PROOF', 'status': 'PASS',
        'at_utc': datetime.now(timezone.utc).isoformat(), 'http_get_calls': 3, 'model_inference_calls': 0,
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
    return {**provenance, **fields, 'kind': 'GEMMA4_NATIVE_PUBLIC_PRODUCTION_SMOKE',
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
    return {**summary, **provenance, **fields, 'kind': 'GEMMA4_NATIVE_PUBLIC_CONTEXT_RESOURCE_PROBE', 'status': 'PASS',
            'http_post_calls': 1, 'elapsed_seconds': elapsed,
            'request_sha256': digest(json.dumps(payload, ensure_ascii=False, allow_nan=False).encode()),
            'guard_minimum_observed_free_mib': after['minimum_observed_free_mib'],
            'guard_aggregate_peak_mib': after['observed_baseline_relative_peak_mib'],
            'guard_required_free_floor_mib': after['required_free_floor_mib'],
            'guard_aggregate_increment_limit_mib': after['aggregate_increment_limit_mib'],
            'lifetime_aggregate_values_not_probe_isolated': True}
