"""GLM47 Flash reviewed CPU evidence; actual GPU actions remain root-owned.

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
base = ModuleType('glm47_flash_pinned_generic_probe')
base.__file__ = str(BASE_PATH)
exec(compile(_base_bytes, str(BASE_PATH), 'exec'), base.__dict__)
del _base_bytes
# Deliberately exclude all historical Qwen provenance/template/client helpers.
require, digest, encoded, read_json = base.require, base.digest, base.encoded, base.read_json
load_config, binding, validate_guard, epoch = base.load_config, base.binding, base.validate_guard, base.epoch
request_json, resource_payload, validate_resource = base.request_json, base.resource_payload, base.validate_resource
write_bundle = base.write_bundle

MODEL_ID = 'ggml-org/GLM-4.7-Flash-GGUF'
REVISION = '7559e96b7e324ab405897dc2b91492b0f376ad4a'
MODEL_SHA = 'b6019edc5fbe37d3660d2e994d16c839a7855a6f03362c5dcf8142ba479cd0d2'
MODEL_BYTES = 18244193920
TEMPLATE_SHA = 'd63ad536c3c81880043e22ec7fd08db42b4d8fb7c89c7138bc562bfa25281375'
# Actual audited embedded bytes match the official source; live props not observed.
# This source template has no CR or terminal LF; no string normalization here.
PROPS_TEMPLATE_SHA = TEMPLATE_SHA
PROPS_TEMPLATE_BYTES = 3120
EMBEDDED_TEMPLATE_BYTES = 3120
TOKENIZER_SHA = '19e773648cb4e65de8660ea6365e10acca112d42a854923df93db4a6f333a82d'
PROFILE = 'glm47_flash_nonthinking_llama_cpp'
SAMPLING = {
    'temperature': 1.0, 'top_p': 0.95, 'top_k': 0, 'min_p': 0.0,
    'presence_penalty': 0.0, 'frequency_penalty': 0.0,
    'repeat_penalty': 1.0, 'repeat_last_n': 0, 'seed': 42,
    'samplers': ['temperature', 'top_k', 'top_p', 'min_p'],
}
# Deliberately not booleans that a response/config may enable. Finalizing needs
# a separate reviewed revision after actual header and full CPU receipts exist.
HEADER_SHA = '595a7efd19914b65e91f1d92aaee141a0457472039c7278264cc1b5d314659ef'
FINAL_CPU_SHA = '54ab0062c5d22112ed3349e0021391a4dd17f6d5f8698ac8a02cc096b08a1847'
QUANTIZATION = 'Q4_K_M'  # Actual audited ftype15; artifact filename remains Q4_K.
CANDIDATE_VARIANT = 'glm47-flash-gguf-nonthinking-v1'
PREPARATION_STATUS = 'REVIEWED_CPU_BINDING_READY_FOR_ROOT_GPU_DECISION'
RUNTIME_LAUNCHER_SHA = '6a58ee1ea09636df182125da4a4a2711012e6c53f5f90c06548a63b9915369ed'
CPU_REFS = {'public_contract': {'path': 'var/research/native-glm47-contract/public-proof-v3.json', 'sha256': 'd8f8fe1faf2ee73b06f6df35d16dba3a29cb78ad41af35a8a1be6cff888ac85c'}, 'public_vocab': {'path': 'var/research/native-glm47-contract/public-vocab-proof.json', 'sha256': 'f3e31a724dcec94f6d3b285a9dd793d6a8b6c91c3c8c475a63c25709c94d6cf7'}, 'vocab_context': {'path': 'var/research/native-glm47-contract/vocab-context-proof.json', 'sha256': '66e2ab245e0d7c2a2760d2b98e0a191fb8b27248be6fae6d61cf922c814bb607'}, 'header': {'path': 'var/reports/glm47-flash-gguf-header.json', 'sha256': '595a7efd19914b65e91f1d92aaee141a0457472039c7278264cc1b5d314659ef'}, 'tokenizer_fixture': {'path': 'var/research/native-glm47-contract/official-tokenizer-fixture.json', 'sha256': 'e67bd4d05462587e0466f092351ada8c8fa4efdd9a10da0b4cecb25a4d3dc8f3'}}


def require_ready():
    require(FINAL_CPU_SHA == '54ab0062c5d22112ed3349e0021391a4dd17f6d5f8698ac8a02cc096b08a1847',
            'GLM_ROOT_FINAL_RUNTIME_REVIEW_PENDING')


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


def glm_binding(config):
    require(config.model_revision == REVISION and config.model_sha256 == MODEL_SHA
            and config.source_commit == 'f072b103714dfa1eee531f80b24512faf38e3dd2'
            and config.enable_reasoning is False
            and (config.batch_size, config.ubatch_size) == (64, 64)
            and config.estimated_peak_mib == 28672 and config.peak_allowance_mib == 0
            and config.profile == 'a100' and config.port == 8003 and config.max_seconds == 7200
            and config.served_model_name == 'neurobuild-glm47-flash-q4-k'
            and config.chat_template_path is None and config.chat_template_sha256 is None,
            'GLM_CONFIG_MISMATCH')
    artifacts = binding(config)
    header, raw = read_json(config.model_header_report)
    require(digest(raw) == config.model_header_report_sha256
            and digest(raw) == HEADER_SHA
            and header['file_bytes'] == MODEL_BYTES and header['model_id'] == MODEL_ID
            and header['bindings']['embedded_template_sha256'] == TEMPLATE_SHA
            and header['bindings']['quantization'] == QUANTIZATION, 'GLM_HEADER_MISMATCH')
    return artifacts


def cpu_provenance(config, proof_path, proof_sha):
    """Saved public-template + official-vocab/context proof validation only.

    The caller supplies the reviewed aggregate proof's exact hash. Linked small
    evidence hashes are checked again; datasets/tensors are never opened here.
    """
    require(type(FINAL_CPU_SHA) is str and proof_sha == FINAL_CPU_SHA, 'GLM_FINAL_CPU_HASH_MISMATCH')
    proof, raw = read_json(proof_path)
    require(digest(raw) == proof_sha and proof['kind'] == 'GLM47_FLASH_NATIVE_CONTRACT_CPU_PROOF'
            and proof['status'] == 'PASS' and proof['model_id'] == MODEL_ID
            and proof['candidate_variant'] == CANDIDATE_VARIANT
            and proof['sampling_request_parameters'] == SAMPLING
            and proof['protocol'] == 'llama_cpp_json_schema' and proof['sampling_profile'] == PROFILE
            and proof['source_pin'] == config.source_commit == 'f072b103714dfa1eee531f80b24512faf38e3dd2'
            and proof['revision'] == REVISION and proof['gguf_sha256'] == MODEL_SHA == config.model_sha256
            and proof['header_sha256'] == HEADER_SHA == config.model_header_report_sha256
            and proof['template_sha256'] == TEMPLATE_SHA and proof['tokenizer_json_sha256'] == TOKENIZER_SHA
            and type(proof['model_inference_calls']) is int and proof['model_inference_calls'] == 0
            and proof['application_input_output_nfc_repair'] is False
            and proof['official_tokenizer_normalizer'] is None
            and proof['template_override_used'] is False
            and digest((ROOT / 'scripts/llama_server.py').read_bytes()) == RUNTIME_LAUNCHER_SHA,
            'GLM_CPU_PROVENANCE_MISMATCH')
    require(type(proof['max_output_tokens']) is int and proof['max_output_tokens'] == 768
            and type(proof['max_context_tokens']) is int and proof['max_context_tokens'] == 4096,
            'GLM_CONTEXT_LIMIT_MISMATCH')
    require(proof['official_tokenizer_parity'] == {'status': 'PASS', 'case_count': 20,
            'id_match_count': 20, 'native_original_roundtrip_count': 20}, 'GLM_OFFICIAL_PARITY_REQUIRED')
    require(set(proof['splits']) == set(CONTEXT_SPLITS), 'GLM_CONTEXT_SPLITS_MISMATCH')
    for name, (count, sha) in CONTEXT_SPLITS.items():
        row = proof['splits'][name]
        require(type(row['input_count']) is int and row['input_count'] == count
                and row['dataset_sha256'] == sha
                and type(row['min_input_tokens']) is int and type(row['max_input_tokens']) is int
                and 0 < row['min_input_tokens'] <= row['max_input_tokens']
                and type(row['max_input_plus_output']) is int
                and row['max_input_plus_output'] == row['max_input_tokens'] + 768 <= 4096,
                'GLM_CONTEXT_SPLIT_MISMATCH')
    require(set(proof['source_sha256']) == CPU_SOURCE_PATHS, 'GLM_CPU_SOURCE_SET_MISMATCH')
    for path, expected in proof['source_sha256'].items():
        source_file = base.checked_file(ROOT / path, ROOT)
        require(source_file.stat().st_size <= 1024 * 1024
                and digest(source_file.read_bytes()) == expected, 'GLM_CPU_SOURCE_HASH_MISMATCH')
    require(proof['proof_refs'] == CPU_REFS,
            'GLM_CPU_REFERENCES_MISMATCH')
    for ref in proof['proof_refs'].values():
        require(set(ref) == {'path', 'sha256'} and type(ref['path']) is str
                and not Path(ref['path']).is_absolute() and '..' not in Path(ref['path']).parts,
                'GLM_CPU_REFERENCE_PATH_INVALID')
        _, linked_raw = read_json(ROOT / ref['path'])
        require(digest(linked_raw) == ref['sha256'], 'GLM_CPU_REFERENCE_HASH_MISMATCH')
    token = proof['resource_probe_token']
    require(set(token) == {'text', 'token_id', 'native_token_count', 'native_roundtrip'}
            and token['text'] == ' ' and type(token['token_id']) is int and token['token_id'] == 220
            and type(token['native_token_count']) is int and token['native_token_count'] == 1
            and token['native_roundtrip'] is True, 'GLM_PUBLIC_TOKEN_INVALID')
    return ({'candidate_variant': CANDIDATE_VARIANT, 'model_id': MODEL_ID, 'model_revision': REVISION, 'cpu_proof_sha256': proof_sha,
             'cpu_proof_kind': proof['kind'], 'chat_template_sha256': TEMPLATE_SHA,
             'tokenizer_json_sha256': TOKENIZER_SHA,
             'tokenizer_contract': 'official_glm_metadata_native_public_parity_20_of_20',
             'official_tokenizer_parity': dict(proof['official_tokenizer_parity']),
             'application_input_output_nfc_repair': False,
             'cpu_proof_refs': proof['proof_refs'], 'cpu_source_sha256': proof['source_sha256'],
             'normalization_limitation': proof['normalization_limitation'],
             'reasoning_boundary': proof['reasoning_boundary'],
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
    artifacts = glm_binding(config)
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
    startup = {**summary, **provenance, **fields, 'kind': 'GLM47_FLASH_NATIVE_STARTUP_HTTP_PROOF', 'status': 'PASS',
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
    require(client.sampling_parameters == SAMPLING and client.enable_thinking is False, 'GLM_CLIENT_RECIPE_MISMATCH')
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
    return {**provenance, **fields, 'kind': 'GLM47_FLASH_NATIVE_PUBLIC_PRODUCTION_SMOKE',
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
    return {**summary, **provenance, **fields, 'kind': 'GLM47_FLASH_NATIVE_PUBLIC_CONTEXT_RESOURCE_PROBE', 'status': 'PASS',
            'http_post_calls': 1, 'elapsed_seconds': elapsed,
            'request_sha256': digest(json.dumps(payload, ensure_ascii=False, allow_nan=False).encode()),
            'guard_minimum_observed_free_mib': after['minimum_observed_free_mib'],
            'guard_aggregate_peak_mib': after['observed_baseline_relative_peak_mib'],
            'guard_required_free_floor_mib': after['required_free_floor_mib'],
            'guard_aggregate_increment_limit_mib': after['aggregate_increment_limit_mib'],
            'lifetime_aggregate_values_not_probe_isolated': True}
