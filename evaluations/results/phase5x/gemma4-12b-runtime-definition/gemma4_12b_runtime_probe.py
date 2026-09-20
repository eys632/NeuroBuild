"""Gemma4 12B evidence collector definition; no import-time runtime actions.

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
base = ModuleType('gemma4_12b_pinned_generic_probe')
base.__file__ = str(BASE_PATH)
exec(compile(_base_bytes, str(BASE_PATH), 'exec'), base.__dict__)
del _base_bytes
# Deliberately exclude all historical Qwen provenance/template/client helpers.
require, digest, encoded, read_json = base.require, base.digest, base.encoded, base.read_json
load_config, binding, validate_guard, epoch = base.load_config, base.binding, base.validate_guard, base.epoch
request_json, resource_payload, validate_resource = base.request_json, base.resource_payload, base.validate_resource
write_bundle = base.write_bundle

MODEL_ID = 'google/gemma-4-12B-it-qat-q4_0-gguf'
REVISION = '29d097773436b69ff9feafd636ab4cf873786537'
MODEL_SHA = '93567e57a8fe10b23569b9d9ec38cd005deedf71e29477c421a4b83f418a538b'
MODEL_BYTES = 6975879296
TEMPLATE_SHA = 'ae53464bf3be25802b3a5b37def7fd89667067d7577049b3b2d74c4d8de4c6d4'
# f072 common/jinja/lexer.cpp:54-57 strips exactly one terminal LF.
# This official source has no CR bytes; no user text normalization is performed.
PROPS_TEMPLATE_SHA = '6a1015c47ccfcfa67c3b772385bccee357a4d37c3cda37bd202e9047f391ab82'
PROPS_TEMPLATE_BYTES = 18682
EMBEDDED_TEMPLATE_BYTES = 18683
TOKENIZER_SHA = 'cc8d3a0ce36466ccc1278bf987df5f71db1719b9ca6b4118264f45cb627bfe0f'
PROFILE = 'gemma4_nonthinking_llama_cpp'
MODEL_PATH = Path('var/models/google--gemma-4-12B-it-qat-q4_0-gguf/29d097773436b69ff9feafd636ab4cf873786537/gemma-4-12b-it-qat-q4_0.gguf')
HEADER_PATH = Path('var/reports/gemma4-12b-gguf-header.json')
HEADER_SHA = '97a9bd3cb854c446edd7b534011eaceac389f76f8f6c49b1dd0ec5e06be4eac0'
CPU_CARRYFORWARD_PATH = Path('var/research/native-gemma4-12b-contract/cpu-carry-forward.json')
CPU_CARRYFORWARD_SHA = 'cb2370d7a012b40fe62dae039551d9f8d37f4961aaaccc7a9845dd8bfdee0a2f'
TOKENIZER_METADATA_COMPARISON_SHA = 'a6d70d937b44a9743735b7843b59d9ba85dca2f9db300cf13c61d108a8c5f481'
CANDIDATE_VARIANT = 'gemma4-12b-qat-q4_0-carried-contract-v1'
PREPARATION_STATUS = 'FINALIZED_DEFINITION_RUNTIME_NOT_RUN'
CONDITIONAL_MODEL_ESTIMATE_MIB = 18432
OPERATIONAL_BUDGET_MIB = 28672
ADDITIONAL_CONSERVATIVE_ALLOWANCE_MIB = 10240
SAMPLING = {
    'temperature': 1.0, 'top_p': 0.95, 'top_k': 64, 'min_p': 0.0,
    'presence_penalty': 0.0, 'frequency_penalty': 0.0,
    'repeat_penalty': 1.0, 'repeat_last_n': 0, 'seed': 42,
    'samplers': ['temperature', 'top_k', 'top_p', 'min_p'],
}
# Expected official generation metadata, not an observed new GGUF assertion.
# The same client recipe does NOT imply the same complete effective sampler.
SUPPRESS_TOKENS = [258883, 258882]
COMPLETE_EFFECTIVE_SAMPLING_EQUIVALENT_TO_31B = False
EXPECTED_NATIVE_CONSTRAINTS = {
    'physical_gpu': 3, 'logical_gpu': 0, 'visible_gpu_count': 1,
    'max_model_len': 4096, 'max_sequences': 1, 'batch_size': 64, 'ubatch_size': 64,
    'cache_type_k': 'f16', 'cache_type_v': 'f16', 'flash_attn': 'off',
    'cuda_graphs': False, 'fit': 'off', 'gpu_layers': 'all',
    'host': '127.0.0.1', 'estimated_peak_mib': OPERATIONAL_BUDGET_MIB, 'peak_allowance_mib': 0,
}
# Exact receipts are bound without relabeling prior 31B checks as 12B runs.
CARRYFORWARD_REQUIREMENTS = (
    'Exact new full-SHA/header PASS and saved typed tokenizer.* equality, with only the declared suppression difference.',
    'Historical 31B CPU/public/vocab/context proof hashes and their original model identity remain explicit.',
    'Unchanged pinned native binary/source and model-aware tokenizer/template/BOS/EOG path; no inference of equality from file names.',
    'Current production request/profile/prompt/schema/parser source and original input-file hashes bound to historical observations without reading inputs here.',
    'Same official template/tokenizer bytes; preserve literal U+2581 normalization witness and no input/output repair.',
    'Carry historical public30/tokenizer20/context200 counts as historical only; max input plus 768 <= 4096; no claim of new model quality or GPU compatibility.',
    'New I32 suppression [258883,258882], EOG disjointness and negative-infinity native bias recorded separately from client recipe.',
    'Resource token proof and suppression noncollision remain explicit before any resource request.',
    'Use the existing 28672 MiB operational budget plus fresh GPU3 safety margin; the conditional 18432 MiB model estimate leaves 10240 MiB additional conservative allowance, not a strict allocation cap.',
)


def require_ready():
    require(PREPARATION_STATUS == 'FINALIZED_DEFINITION_RUNTIME_NOT_RUN'
            and CPU_CARRYFORWARD_SHA == 'cb2370d7a012b40fe62dae039551d9f8d37f4961aaaccc7a9845dd8bfdee0a2f'
            and HEADER_SHA == '97a9bd3cb854c446edd7b534011eaceac389f76f8f6c49b1dd0ec5e06be4eac0'
            and TOKENIZER_METADATA_COMPARISON_SHA == 'a6d70d937b44a9743735b7843b59d9ba85dca2f9db300cf13c61d108a8c5f481'
            and PRODUCER_SHA == '4653f4e09a6d52bb9d04a6d3d2579bdd6d3d12c1588289d0465e7717ad227281'
            and CANDIDATE_VARIANT == 'gemma4-12b-qat-q4_0-carried-contract-v1'
            and PROFILE == 'gemma4_nonthinking_llama_cpp'
            and OPERATIONAL_BUDGET_MIB == 28672
            and CONDITIONAL_MODEL_ESTIMATE_MIB + ADDITIONAL_CONSERVATIVE_ALLOWANCE_MIB == OPERATIONAL_BUDGET_MIB
            and SUPPRESS_TOKENS == [258883, 258882]
            and COMPLETE_EFFECTIVE_SAMPLING_EQUIVALENT_TO_31B is False,
            'GEMMA12_FINALIZED_DEFINITION_MISMATCH')

PRODUCER_PATH = Path('var/research/produce_gemma12_cpu_carry_forward.py')
PRODUCER_SHA = '4653f4e09a6d52bb9d04a6d3d2579bdd6d3d12c1588289d0465e7717ad227281'
CPU_KIND = 'GEMMA4_12B_CPU_CONTRACT_CARRY_FORWARD'
CPU_STATUS = 'CARRIED_FORWARD_BY_EXACT_INPUT_EQUIVALENCE'
CURRENT_SOURCE_SHA256 = {'src/neurobuild/infrastructure/local_model.py': '7dfc3f673ba6ab4e4970055c4cbee66ae440da2d42070af959a5fe415a9ab780',
 'src/neurobuild/application/requirement_generation.py': 'fcba16f6adc906923859f3bcf4ae2f680e76716863a759582167cd9326f03198',
 'src/neurobuild/application/requirements.py': 'a940f3952c0c4133ab51732f6abf76516d8ff66617470545222b52adfa49fb4a',
 'prompts/requirement_generation_v2_v2.txt': '99d737124372836ba5f985fa6e5570afef693e769798844931f000fb21403cf6',
 'schemas/requirement_generation_v2_decision_branches.schema.json': '36d42b9fa3d24f4a1bc1d14381110e36e8d89103b696bc83113be006b64934e2'}
CARRY_REFS = {'old_header': {'path': 'evaluations/results/phase5x/gemma4-cpu-preflight/header-v2.json',
                'sha256': 'd867a3300b2a93534fb1b480e8e42b30321c894aaec05b5729a529e848817756'},
 'new_header': {'path': 'var/reports/gemma4-12b-gguf-header.json',
                'sha256': '97a9bd3cb854c446edd7b534011eaceac389f76f8f6c49b1dd0ec5e06be4eac0'},
 'tokenizer_comparison': {'path': 'var/reports/gemma4-12b-saved-tokenizer-comparison.json',
                          'sha256': 'a6d70d937b44a9743735b7843b59d9ba85dca2f9db300cf13c61d108a8c5f481'},
 'source_equivalence': {'path': 'var/research/gemma12-gemma-branch-source-equivalence.json',
                        'sha256': 'c21cbd6102933e1511f51625a88471b85caf8d9192dd3fe01fcd4ac644a37f20'},
 'historical_aggregate': {'path': 'evaluations/results/phase5x/gemma4-cpu-preflight/contract/final-cpu-proof.json',
                          'sha256': 'a27cd1f7a37899873aac346404e1cea8d0805c8db899f03eba6e3d7d7340029d'},
 'public_contract': {'path': 'evaluations/results/phase5x/gemma4-cpu-preflight/contract/public-proof.json',
                     'sha256': 'd7cd7032f019af566e2d7484afed85f9dab95fcbc0da06fc2a602cf5b7a76334'},
 'vocab': {'path': 'evaluations/results/phase5x/gemma4-cpu-preflight/contract/public-vocab-v2-proof.json',
           'sha256': '70886f2ad74ef3758fe839f13b4b6740e22cb749f8f0989a98ea376382cc09c6'},
 'vocab_context': {'path': 'evaluations/results/phase5x/gemma4-cpu-preflight/contract/vocab-context-v2-proof.json',
                   'sha256': '06ef550b4ea48b3c3c65d631dafca06c85bd3d350311888b9bc5c86630caf64a'},
 'tokenizer_fixture': {'path': 'evaluations/results/phase5x/gemma4-cpu-preflight/contract/tokenizer-fixture.json',
                       'sha256': '42b2a10fdc4ebc066acb878a5a9e0c9e407affe0b91bc7d32145d8d360dc13e5'},
 'normalization_witness': {'path': 'evaluations/results/phase5x/gemma4-cpu-preflight/contract/normalization-witness-proof.json',
                           'sha256': 'bbb9ed28cdae06bb07a3f66949c2e23e59728324f74440be82b567f0a8662e73'},
 'historical_cpu_build': {'path': 'evaluations/results/phase5x/gemma4-cpu-preflight/contract/build-v2.json',
                          'sha256': '1b6dce0e85790b267ec2514da8c81158c76b9d01a27aa6c2e584787a160e67ee'},
 'historical_cpp': {'path': 'evaluations/results/phase5x/gemma4-cpu-preflight/contract/validator_v2.cpp',
                    'sha256': 'fecf647d431a3af0137f5e9459ddd8afece4e571d4a6a240dc2f4929acf9f20d'}}

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
    require_ready()
    require(config.model_revision == REVISION and config.model_sha256 == MODEL_SHA
            and config.source_commit == 'f072b103714dfa1eee531f80b24512faf38e3dd2'
            and config.enable_reasoning is False
            and type(config.batch_size) is int and type(config.ubatch_size) is int
            and (config.batch_size, config.ubatch_size) == (64, 64)
            and config.estimated_peak_mib == OPERATIONAL_BUDGET_MIB and config.peak_allowance_mib == 0
            and config.profile == 'a100' and config.port == 8003 and config.max_seconds == 7200
            and config.max_model_len == 4096
            and config.served_model_name == 'neurobuild-gemma4-12b-qat-q4-0'
            and config.model_path == MODEL_PATH and config.model_header_report == HEADER_PATH
            and config.model_header_report_sha256 == HEADER_SHA
            and config.chat_template_path is None and config.chat_template_sha256 is None,
            'GEMMA12_CONFIG_MISMATCH')
    artifacts = binding(config)
    header, raw = read_json(config.model_header_report)
    require(digest(raw) == config.model_header_report_sha256
            and digest(raw) == HEADER_SHA and header['file_bytes'] == MODEL_BYTES
            and header['model_id'] == MODEL_ID and header['revision'] == REVISION
            and header['bindings']['embedded_template_sha256'] == TEMPLATE_SHA
            and header['bindings']['suppress_tokens'] == SUPPRESS_TOKENS
            and header['bindings']['suppression_wire_type'] == 'INT32(5)'
            and header['bindings']['suppression_eog_disjoint'] is True,
            'GEMMA12_HEADER_MISMATCH')
    return artifacts


def exact_json(actual, expected, code):
    """Typed equality of saved metadata; booleans never substitute for numbers."""
    require(encoded(actual) == encoded(expected), code)


def bound_small_bytes(relative, expected):
    require(type(relative) is str and not Path(relative).is_absolute()
            and '..' not in Path(relative).parts, 'GEMMA12_REFERENCE_PATH_INVALID')
    path = base.checked_file(ROOT / relative, ROOT)
    require(path.stat().st_size <= 2 * 1024 * 1024, 'GEMMA12_REFERENCE_TOO_LARGE')
    raw = path.read_bytes()
    require(digest(raw) == expected, 'GEMMA12_REFERENCE_HASH_MISMATCH')
    return raw


def cpu_provenance(config, proof_path, proof_sha):
    """Consume exact saved carry evidence; never execute prior CPU tests/corpora.

    Historical public30/tokenizer20/context200 are not relabeled as measurements on 12B.
    The final evaluation freeze separately hashes current dataset bytes.
    """
    require_ready()
    require(type(CPU_CARRYFORWARD_SHA) is str and len(CPU_CARRYFORWARD_SHA) == 64
            and proof_sha == CPU_CARRYFORWARD_SHA, 'GEMMA12_CARRY_HASH_NOT_PINNED')
    require(Path(proof_path) in (CPU_CARRYFORWARD_PATH, ROOT / CPU_CARRYFORWARD_PATH),
            'GEMMA12_CARRY_PATH_MISMATCH')
    proof, raw = read_json(proof_path)
    require(digest(raw) == proof_sha, 'GEMMA12_CARRY_HASH_MISMATCH')
    exact_json({key: proof[key] for key in (
        'kind', 'status', 'candidate_variant', 'model_id', 'revision', 'gguf_sha256',
        'header_sha256', 'template_sha256', 'tokenizer_json_sha256', 'source_pin',
        'protocol', 'sampling_profile', 'source_sha256', 'sampling_request_parameters',
        'enable_reasoning', 'enable_thinking', 'max_output_tokens', 'max_context_tokens',
        'application_input_output_nfc_repair', 'producer_sha256')}, {
        'kind': CPU_KIND, 'status': CPU_STATUS, 'candidate_variant': CANDIDATE_VARIANT,
        'model_id': MODEL_ID, 'revision': REVISION, 'gguf_sha256': MODEL_SHA,
        'header_sha256': HEADER_SHA, 'template_sha256': TEMPLATE_SHA,
        'tokenizer_json_sha256': TOKENIZER_SHA, 'source_pin': config.source_commit,
        'protocol': 'llama_cpp_json_schema', 'sampling_profile': PROFILE,
        'source_sha256': CURRENT_SOURCE_SHA256, 'sampling_request_parameters': SAMPLING,
        'enable_reasoning': False, 'enable_thinking': False, 'max_output_tokens': 768,
        'max_context_tokens': 4096, 'application_input_output_nfc_repair': False,
        'producer_sha256': PRODUCER_SHA}, 'GEMMA12_CARRY_IDENTITY_MISMATCH')
    require(config.source_commit == 'f072b103714dfa1eee531f80b24512faf38e3dd2'
            and config.model_sha256 == MODEL_SHA and config.model_revision == REVISION
            and config.model_header_report_sha256 == HEADER_SHA, 'GEMMA12_CARRY_CONFIG_MISMATCH')
    exact_json(proof['proof_refs'], CARRY_REFS, 'GEMMA12_CARRY_REFERENCES_MISMATCH')
    bound_small_bytes(PRODUCER_PATH.as_posix(), PRODUCER_SHA)
    documents = {}
    for key, ref in CARRY_REFS.items():
        linked = bound_small_bytes(ref['path'], ref['sha256'])
        # Public fixture and historical C++ are hashed only, never parsed/executed.
        if key not in ('tokenizer_fixture', 'historical_cpp'):
            documents[key] = json.loads(linked)
    for relative, pin in CURRENT_SOURCE_SHA256.items():
        bound_small_bytes(relative, pin)
    old = documents['historical_aggregate']
    exact_json(proof['historical_measurements'], {
        'measured_model_id': 'google/gemma-4-31B-it-qat-q4_0-gguf',
        'measured_revision': '59dde24573e7e61570dba08b18a2e1fe246955ed',
        'measured_gguf_sha256': '179cfb99212709597eae5929112cfca677e1bbf566178b479ae1da0c4772874b',
        'original_status': 'PASS', 'measurement_status_for_new_candidate': CPU_STATUS,
        'public_contract': documents['public_contract']['native'],
        'official_tokenizer_parity': old['official_tokenizer_parity'],
        'splits': old['splits']}, 'GEMMA12_HISTORICAL_MEASUREMENT_MISMATCH')
    exact_json(proof['new_executions'], {'native_public': 0, 'vocab': 0, 'context': 0,
        'model_inference': 0, 'http': 0, 'gpu': 0}, 'GEMMA12_NEW_EXECUTION_CLAIM_INVALID')
    exact_json(proof['sampling_behavior'], {
        'http_recipe_equal': True, 'full_sampling_equivalent': False,
        'additional_suppressed_ids': SUPPRESS_TOKENS, 'suppression_eog_disjoint': True,
        'native_effect': 'Model-owned negative-infinity logit bias before the unchanged HTTP sampling recipe'},
        'GEMMA12_SAMPLING_DIFFERENCE_LOST')
    require(proof['current_dataset_hash_verified_by_producer'] is False
            and proof['future_freeze_must_bind_current_dataset_bytes_to_historical_split_hashes'] is True
            and proof['new_model_runtime_status'] == proof['new_model_quality_status'] == 'NOT_RUN',
            'GEMMA12_CARRY_SCOPE_INVALID')
    exact_json(proof['normalization_limitation'], old['normalization_limitation'],
               'GEMMA12_NORMALIZATION_LIMITATION_MISMATCH')
    require(proof['literal_u2581_witness_status'] == documents['normalization_witness']['status']
            == 'FAIL_NATIVE_ORIGINAL_ROUNDTRIP', 'GEMMA12_NORMALIZATION_WITNESS_LOST')
    require(set(proof['historical_measurements']['splits']) == set(CONTEXT_SPLITS),
            'GEMMA12_CONTEXT_SPLITS_MISMATCH')
    for key, (count, sha) in CONTEXT_SPLITS.items():
        row = proof['historical_measurements']['splits'][key]
        require(type(row['input_count']) is int and row['input_count'] == count
                and row['dataset_sha256'] == sha
                and type(row['min_input_tokens']) is int and type(row['max_input_tokens']) is int
                and 0 < row['min_input_tokens'] <= row['max_input_tokens']
                and type(row['max_input_plus_output']) is int
                and row['max_input_plus_output'] == row['max_input_tokens'] + 768 <= 4096,
                'GEMMA12_CONTEXT_BOUND_INVALID')
    token = proof['resource_probe_token']
    exact_json(token, old['resource_probe_token'], 'GEMMA12_RESOURCE_TOKEN_HISTORY_MISMATCH')
    exact_json(token, {'text': ' ', 'token_id': 236743, 'native_token_count': 1,
                      'native_roundtrip': True}, 'GEMMA12_RESOURCE_TOKEN_INVALID')
    require(proof['resource_probe_token_suppression_disjoint'] is True
            and token['token_id'] not in SUPPRESS_TOKENS, 'GEMMA12_RESOURCE_TOKEN_SUPPRESSED')
    return ({'model_id': MODEL_ID, 'model_revision': REVISION,
             'candidate_variant': CANDIDATE_VARIANT,
             'cpu_proof_sha256': proof_sha, 'cpu_proof_kind': CPU_KIND, 'cpu_proof_status': CPU_STATUS,
             'chat_template_sha256': TEMPLATE_SHA, 'tokenizer_json_sha256': TOKENIZER_SHA,
             'tokenizer_contract': 'carried_forward_by_exact_typed_tokenizer_and_effective_input_equivalence',
             'historical_measurements': proof['historical_measurements'],
             'new_cpu_executions': proof['new_executions'],
             'sampling_behavior': proof['sampling_behavior'],
             'normalization_limitation': proof['normalization_limitation'],
             'literal_u2581_witness_status': proof['literal_u2581_witness_status'],
             'application_input_output_nfc_repair': False,
             'cpu_proof_refs': proof['proof_refs'], 'cpu_source_sha256': proof['source_sha256'],
             'cpu_checks_rerun': False}, token['token_id'])


def validate_health_models_props(config, health, models, props):
    require_ready()
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
            'props_template_derivation': 'Pinned f072 Jinja lexer removes exactly one terminal LF from this no-CR template; no application input/output repair'}


def make_metadata(config, platform, config_sha, startup_sha, listener_sha):
    require_ready()
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
    require_ready()
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
    require_ready()
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
    require_ready()
    config, config_raw, provenance, _, artifacts, before, before_raw, first = begin(
        config_path, config_sha, cpu_proof_path, cpu_proof_sha, timeout=30)
    health, _ = request_json(config.port, '/health')
    models, _ = request_json(config.port, '/v1/models')
    props, _ = request_json(config.port, '/props')
    summary = validate_health_models_props(config, health, models, props)
    fields, _, after_raw, listeners = finish(config, config_sha, artifacts, before, before_raw, first)
    startup = {**summary, **provenance, **fields, 'kind': 'GEMMA4_12B_NATIVE_STARTUP_HTTP_PROOF', 'status': 'PASS',
        'at_utc': datetime.now(timezone.utc).isoformat(), 'http_get_calls': 3, 'model_inference_calls': 0,
        'model_inference_calls_scope': 'Explicit HTTP generation calls only; native startup warmup is enabled',
        'native_startup_warmup_enabled': True,
        'resource_report_sha256': digest(after_raw), 'native_identity_verified': True,
        'raw_http_bodies_saved': False, 'installed_small_artifacts_rehashed': True,
        'gguf_binding': 'Live guard full hash + pinned header + current owned file size; no second full hash',
        'platform_facts_scope': 'Root-supplied measured platform facts; HTTP is not hardware attestation'}
    startup_raw, listener_raw = encoded(startup), encoded(listeners)
    metadata = make_metadata(config, platform, config_sha, digest(startup_raw), digest(listener_raw))
    return {'launch_config.json': config_raw, 'resource_report.json': after_raw,
            'listeners.json': listener_raw, 'startup.json': startup_raw, 'runtime_metadata.json': encoded(metadata)}


def public_smoke(config_path, config_sha, *, cpu_proof_path, cpu_proof_sha, timeout=120):
    require_ready()
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
    return {**provenance, **fields, 'kind': 'GEMMA4_12B_NATIVE_PUBLIC_PRODUCTION_SMOKE',
            'status': status, 'error_code': code, 'http_calls_attempted': 1, 'elapsed_seconds': elapsed,
            'sampling_profile': PROFILE, 'source': 'PUBLIC_SYNTHETIC_CPU_FIXTURE',
            'generated_body_retained': False, 'quality_gate_pass': False}


def run_resource_smoke(config_path, config_sha, *, cpu_proof_path, cpu_proof_sha, timeout=900):
    require_ready()
    config, _, provenance, token_id, artifacts, before, before_raw, first = begin(
        config_path, config_sha, cpu_proof_path, cpu_proof_sha, timeout=timeout)
    payload = resource_payload(token_id)
    value, elapsed = request_json(config.port, '/completion', payload, timeout=timeout, max_bytes=8192)
    summary = validate_resource(value)
    fields, after, _, _ = finish(config, config_sha, artifacts, before, before_raw, first)
    return {**summary, **provenance, **fields, 'kind': 'GEMMA4_12B_NATIVE_PUBLIC_CONTEXT_RESOURCE_PROBE', 'status': 'PASS',
            'http_post_calls': 1, 'elapsed_seconds': elapsed,
            'request_sha256': digest(json.dumps(payload, ensure_ascii=False, allow_nan=False).encode()),
            'guard_minimum_observed_free_mib': after['minimum_observed_free_mib'],
            'guard_aggregate_peak_mib': after['observed_baseline_relative_peak_mib'],
            'guard_required_free_floor_mib': after['required_free_floor_mib'],
            'guard_aggregate_increment_limit_mib': after['aggregate_increment_limit_mib'],
            'lifetime_aggregate_values_not_probe_isolated': True}
