"""Qwen3.6 first-diagnostic proposal only. Missing observations are never wildcards.
No imports of runtime helpers or reads of artifacts/datasets occur in this module.
"""
from copy import deepcopy
from pathlib import Path
ROOT = Path('/home/a202192020/NeuroBuild_v2')
PREPARATION_STATUS = 'BLOCKED_PENDING_QWEN36_ACTUAL_CPU_HEADER_RUNTIME_AND_ROOT_VARIANT'
MODEL = 'ggml-org/Qwen3.6-35B-A3B-GGUF'
REVISION = 'baec3ebee244827cda0f4557eafa8b28f7545fa6'
UPSTREAM_MODEL = 'Qwen/Qwen3.6-35B-A3B'
UPSTREAM_REVISION = '995ad96eacd98c81ed38be0c5b274b04031597b0'
VARIANT = None
PROPOSED_VARIANT = 'qwen36-gguf-raw-unicode-v1'
SOURCE_PIN = 'f072b103714dfa1eee531f80b24512faf38e3dd2'
GGUF_SHA = '671e47e0ec53c665d048b98c3ecbfd5236b5ca9c3e02ed19fc8f81f7b85140c7'
GGUF_BYTES = 20419565568
GGUF_NAME = 'Qwen3.6-35B-A3B-Q4_K_M.gguf'
TEMPLATE_SHA = 'e84f32a23fdda27689f868aa4a1a5621f41133e51a48d7f3efcbea2839574259'
TEMPLATE_BYTES = 7764
PROPS_TEMPLATE_SHA = None
PROPS_TEMPLATE_BYTES = None
TOKENIZER_SHA = '5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
PROFILE = 'qwen36_nonthinking_llama_cpp'
SERVED_MODEL = 'neurobuild-qwen36-35b-a3b-q4-k-m'
LIFECYCLE = 'FROZEN_BEFORE_NATIVE_QWEN36_EXPOSED_DIAGNOSTIC'
OUT = 'evaluations/hardening_v1_exposed_native_qwen36_diagnostic_freeze.json'
START = 'evaluations/results/phase5x/qwen36-native-startup-epoch1/'
PUBLIC = 'evaluations/results/phase5x/qwen36-native-public-smoke-epoch1/report.json'
RESOURCE = 'evaluations/results/phase5x/qwen36-native-resource-epoch1/report.json'
CPU = 'var/research/native-qwen36-contract/final-cpu-proof.json'
CPU_KIND = 'QWEN36_NATIVE_CONTRACT_CPU_PROOF'
CPU_STATUS = 'PASS_CURRENT_PUBLIC_AND_CARRIED_EXPOSED120'
CPU_SHA = None
CPU_ARCHIVED_PROOF = None
CPU_SCHEMA_FINAL = False
CPU_EXPECTED_PROJECTION = None
CPU_REF_KEYS = ['header', 'tokenizer_comparison', 'public_contract', 'public_build', 'historical_header', 'historical_context', 'historical_official', 'historical_raw', 'historical_raw_fixture', 'source_equivalence']
CPU_REFS = None
HEADER = 'var/reports/qwen36-gguf-header.json'
HEADER_SHA = None
HEADER_ARCHIVE = None
TOKENIZER_COMPARISON = None
TOKENIZER_COMPARISON_SHA = None
COMPARISON_ARCHIVE = None
PROBE = 'var/research/qwen36_runtime_probe.py'
PROBE_SHA = None
CONFIG = 'var/research/qwen36-native-launch-epoch1.json'
CONFIG_SHA = None
CONTROLLER = 'var/research/run_native_qwen36_epoch1_probe.py'
CONTROLLER_SHA = None
SOURCE_COMMIT = '424abd8d976fcc3936c3376863a5a69469f44dc7'
REGRESSION = 'evaluations/results/phase5x/qwen36-preparation/regression_final.json'
REGRESSION_SHA = '5b75b7f81c147691b82fefa1032f0d28ee345b331bd3f92688d414859259ea30'
REGRESSION_LOG = 'evaluations/results/phase5x/qwen36-preparation/regression_final.log.txt'
REGRESSION_LOG_SHA = '9d58d99b1a14b13072f819aa6588483e577248c022431031c289f5409823e68b'
REGRESSION_TEST_COUNT = 422
REGRESSION_TEST_SECONDS = 20.758
RUNTIME_SHA = {'evaluations/results/phase5x/qwen36-native-startup-epoch1/launch_config.json': None, 'evaluations/results/phase5x/qwen36-native-startup-epoch1/runtime_metadata.json': None, 'evaluations/results/phase5x/qwen36-native-startup-epoch1/resource_report.json': None, 'evaluations/results/phase5x/qwen36-native-startup-epoch1/listeners.json': None, 'evaluations/results/phase5x/qwen36-native-startup-epoch1/startup.json': None, 'evaluations/results/phase5x/qwen36-native-public-smoke-epoch1/report.json': None, 'evaluations/results/phase5x/qwen36-native-resource-epoch1/report.json': None}
GATES = {'schema_required': 120, 'schema_denominator': 120, 'semantic_required_at_least': 114, 'semantic_denominator': 120, 'critical_model_ready_fp_required': 0, 'critical_model_ready_fp_denominator': 58, 'unsafe_accepted_ready_total_required': 0, 'unsafe_accepted_ready_total_denominator': 120}
SAMPLING = {'temperature': 0.7, 'top_p': 0.8, 'top_k': 20, 'min_p': 0.0, 'presence_penalty': 1.5, 'frequency_penalty': 0.0, 'repeat_penalty': 1.0, 'repeat_last_n': 64, 'seed': 42, 'samplers': ['penalties', 'top_k', 'top_p', 'min_p', 'temperature']}
PATHS = {'dataset': 'evaluations/requirement_hardening_v1_exposed_regression.jsonl', 'prompt': 'prompts/requirement_generation_v2_v2.txt', 'schema': 'schemas/requirement_generation_v2_decision_branches.schema.json', 'canonical_schema': 'schemas/semantic_requirement.schema.json', 'generation_adapter': 'src/neurobuild/application/requirement_generation.py', 'parser': 'src/neurobuild/application/requirements.py', 'client': 'src/neurobuild/infrastructure/local_model.py', 'scorer': 'scripts/evaluate_requirements.py', 'weight_manifest': 'runtime/models/qwen36-35b-a3b-q4-k-m.json'}
EPOCH_FIELDS = ('launch_config_sha256', 'pid', 'process_start_ticks', 'guard_started_at_utc')
CPU_SOURCE = {'src/neurobuild/infrastructure/local_model.py': '0814c6a5a695c3abb3c4c6cf244990bd569ed372840b1786d2b488e72e0f3120', 'src/neurobuild/application/requirement_generation.py': 'fcba16f6adc906923859f3bcf4ae2f680e76716863a759582167cd9326f03198', 'src/neurobuild/application/requirements.py': 'a940f3952c0c4133ab51732f6abf76516d8ff66617470545222b52adfa49fb4a', 'prompts/requirement_generation_v2_v2.txt': '99d737124372836ba5f985fa6e5570afef693e769798844931f000fb21403cf6', 'schemas/requirement_generation_v2_decision_branches.schema.json': '36d42b9fa3d24f4a1bc1d14381110e36e8d89103b696bc83113be006b64934e2'}
FIXED_SOURCE = {'src/neurobuild/infrastructure/local_model.py': '0814c6a5a695c3abb3c4c6cf244990bd569ed372840b1786d2b488e72e0f3120', 'src/neurobuild/application/requirement_generation.py': 'fcba16f6adc906923859f3bcf4ae2f680e76716863a759582167cd9326f03198', 'src/neurobuild/application/requirements.py': 'a940f3952c0c4133ab51732f6abf76516d8ff66617470545222b52adfa49fb4a', 'prompts/requirement_generation_v2_v2.txt': '99d737124372836ba5f985fa6e5570afef693e769798844931f000fb21403cf6', 'schemas/requirement_generation_v2_decision_branches.schema.json': '36d42b9fa3d24f4a1bc1d14381110e36e8d89103b696bc83113be006b64934e2', 'scripts/evaluate_requirements.py': '1915ee707cb6dca4f9f6927b760b0bdce1c1c5d6929837be489dafc97fb0cbfd', 'scripts/gpu_preflight.py': '988d9493dd73d0e00b039f7d050f3ae52a4073833de23fc58eabc20ee58163fb', 'scripts/llama_server.py': '6a58ee1ea09636df182125da4a4a2711012e6c53f5f90c06548a63b9915369ed', 'scripts/model_guard.py': 'cc95f6cccf9ca5b749bea2fc8c82d2af9d56d55b94a6aee947379b3a2f4de528', 'scripts/native_model_bootstrap.py': '22e56159a6496aabf52dc6b567c800c54822c9def9713eb8a4ff0fac4183c2bf', 'scripts/verify_model_listeners.py': '2d7771d414a7faae4138ea555349d1f7f111d36498ad9815f64ac51910d758dd', 'schemas/semantic_requirement.schema.json': 'dd131db08fe9087e795059445b075f22876e44b42481201cc0ea70608a708f94', 'schemas/requirement_generation_v2.schema.json': '6ca6fed3e8666244cd4bd779d33c0dd647490d5f641134307930008ea440436c', 'runtime/models/qwen36-35b-a3b-q4-k-m.json': '70d4c0f73f763e10d17b0bad75acda2079dff6d49a9e2ed25575a86cff62b76c'}
DRAFT_DIR = 'var/research/qwen36-first-diagnostic-draft/'
REPLAY_PATH = 'var/research/qwen36-first-diagnostic-draft/replay_native_qwen36_exposed.py'
FREEZER_PATH = 'var/research/qwen36-first-diagnostic-draft/freeze_native_qwen36_diagnostic.py'
DEFINITION_PATHS = ['var/research/qwen36-first-diagnostic-draft/contract.py', 'var/research/qwen36-first-diagnostic-draft/evidence.py', 'var/research/qwen36-first-diagnostic-draft/freeze_native_qwen36_diagnostic.py', 'var/research/qwen36-first-diagnostic-draft/replay_native_qwen36_exposed.py']
V2_FREEZE = 'evaluations/hardening_v2_dataset_freeze.json'
V2_EXPOSURE = 'evaluations/hardening_v2_input_exposure_addendum.json'
V2_OUTPUT_EXPOSURE = 'evaluations/hardening_v2_model_output_exposure_record.json'
V2_OUTPUT_EXPOSURE_SHA = '25c080827a6d57aa6bc864495e537490dc7fa48b3ccf91df297a47b9815d447b'
DATASET_SHA = '7e5b9a05932df7aafdbf683655b044b3e3b25cbffb4115d298e1490aecbc7a5b'
V2_DATASET = 'evaluations/requirement_hardening_v2_holdout.jsonl'
V2_DATASET_SHA = '7416f05613b1490358672f3926770dbd8653e676577eeee6ba65f863b27cec40'
RUNTIME_DEFINITION_PINS = {'var/research/native_runtime_probe.py': 'ac100df7949b2b14a517c4568fa66369bd98c599b39507ef19f873490a0f9f63'}
GUARD_MAX_SECONDS = None
RESOURCE_TOKEN_ID = None
NEXT_EVALUATION_POLICY = {'clear_fail': 'STOP_CANDIDATE_NO_REPEAT_NO_V2_NO_UNUSED_HOLDOUT', 'pass': 'LATER_SEPARATE_MINIMUM_NEW_HOLDOUT_DECISION_ONLY', 'automatic_trials_or_retries': 0, 'first_diagnostic_calls': 125, 'future_holdout_execution_authorized': False}

def require_ready():
    # Deliberately unconditional: no hash-only dataset access, live check, freeze,
    # replay or publication until actual pins/schema and root activation review.
    raise ValueError('QWEN36_ACTUAL_CPU_HEADER_RUNTIME_VARIANT_PENDING')


def planned_contract():
    """Future schema, never a freeze or evidence of candidate PASS."""
    return {'preparation_status':PREPARATION_STATUS,'lifecycle':LIFECYCLE,
            'candidate_variant':VARIANT,'model_id':MODEL,'model_revision':REVISION,
            'tokenizer_revision':REVISION,'served_model':SERVED_MODEL,
            'gold_status':'AUTO-GENERATED / NOT HUMAN VERIFIED',
            'dataset':PATHS['dataset'],'split':'development','cases':120,'ready_gold':62,
            'nonready_gold':58,'warmups_per_run':5,'trials_per_case':1,'expected_http_calls':125,
            'pipeline':'single','generation_contract':'2.0','protocol':'llama_cpp_json_schema',
            'sampling_profile':PROFILE,'sampling_request_parameters':deepcopy(SAMPLING),
            'enable_thinking':False,'reasoning_parser':'deepseek','max_tokens':768,
            'timeout_seconds':120,'max_model_len':4096,'concurrency':1,'maximum_calls_per_case':1,
            'gate_targets':deepcopy(GATES),'prompt':PATHS['prompt'],'generation_schema':PATHS['schema'],
            'canonical_schema':PATHS['canonical_schema'],'chat_template_override':None,
            'original_embedded_template_sha256':TEMPLATE_SHA,'effective_chat_template_sha256':TEMPLATE_SHA,
            'application_input_output_nfc_repair':False,'cpu_context_report':CPU,
            'cpu_context_archive':CPU_ARCHIVED_PROOF,'runtime_metadata':START+'runtime_metadata.json',
            'public_smoke_report':PUBLIC,'resource_probe_report':RESOURCE,
            'runtime_epoch_snapshot':None,'tokenizer_contract':None,'normalization_limitation':None,
            'source_ancestor_commit':None,'frozen_at_utc':None,'sha256':None,
            'next_evaluation_policy':deepcopy(NEXT_EVALUATION_POLICY)}
