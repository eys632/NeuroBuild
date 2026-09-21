"""Qwen3.6 first-diagnostic proposal only. Missing observations are never wildcards.
No imports of runtime helpers or reads of artifacts/datasets occur in this module.
"""
from copy import deepcopy
from pathlib import Path
ROOT = Path('/home/a202192020/NeuroBuild_v2')
PREPARATION_STATUS = 'BLOCKED_ACTUAL_CPU_BOUND_PENDING_RUNTIME_SEVEN_AND_ROOT_ACTIVATION'
MODEL = 'ggml-org/Qwen3.6-35B-A3B-GGUF'
REVISION = 'baec3ebee244827cda0f4557eafa8b28f7545fa6'
UPSTREAM_MODEL = 'Qwen/Qwen3.6-35B-A3B'
UPSTREAM_REVISION = '995ad96eacd98c81ed38be0c5b274b04031597b0'
VARIANT = 'qwen36-gguf-raw-unicode-v1'
PROPOSED_VARIANT = 'qwen36-gguf-raw-unicode-v1'
SOURCE_PIN = 'f072b103714dfa1eee531f80b24512faf38e3dd2'
GGUF_SHA = '671e47e0ec53c665d048b98c3ecbfd5236b5ca9c3e02ed19fc8f81f7b85140c7'
GGUF_BYTES = 20419565568
GGUF_NAME = 'Qwen3.6-35B-A3B-Q4_K_M.gguf'
TEMPLATE_SHA = 'e84f32a23fdda27689f868aa4a1a5621f41133e51a48d7f3efcbea2839574259'
TEMPLATE_BYTES = 7764
PROPS_TEMPLATE_SHA = 'e84f32a23fdda27689f868aa4a1a5621f41133e51a48d7f3efcbea2839574259'
PROPS_TEMPLATE_BYTES = 7764
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
CPU_SHA = '747af5656057ebfbe0779a8931f95047f20e1812779097dfe35d8759a12120d1'
CPU_ARCHIVED_PROOF = 'evaluations/results/phase5x/qwen36-cpu-preflight/contract/final-cpu-proof.json'
CPU_SCHEMA_FINAL = True
CPU_EXPECTED_PROJECTION = {'splits': {'exposed120': {'dataset_sha256': '7e5b9a05932df7aafdbf683655b044b3e3b25cbffb4115d298e1490aecbc7a5b', 'input_count': 120, 'min_input_tokens': 2133, 'max_input_tokens': 2409, 'max_input_plus_output': 3177, 'measurement_kind': 'CARRIED_FORWARD', 'measured_model_id': 'ggml-org/Qwen3.8-27B-GGUF'}}, 'resource_probe_token': {'text': ' ', 'token_id': 220, 'native_token_count': 1, 'native_roundtrip': True, 'measurement_kind': 'CARRIED_FORWARD_BY_TYPED_VOCAB_EQUALITY'}, 'historical_hf_equivalence': {'status': 'FAIL', 'case_count': 20, 'id_match_count': 19, 'mismatch_indices': [11], 'native_original_roundtrip_count': 20}, 'historical_raw_reference': {'status': 'PASS', 'case_count': 20, 'id_match_count': 20, 'reference_kind': 'hf-tokenizer-json-with-nfc-normalizer-disabled'}, 'new_executions': {'public_request_count': 1, 'native_compile_count': 1, 'context_request_count': 0, 'public_parity_cases': 0, 'old_corpus_replays': 0, 'model_inference': 0, 'http': 0, 'gpu': 0}, 'normalization_limitation': 'Historical Qwen3.8 official HF NFC reference IDs matched 19/20 (index11 mismatch), while native raw original roundtrip and explicitly NFC-disabled reference matched 20/20. These measurements remain historical; actual typed native tokenizer equality and restricted effective-input equivalence support carry to the explicit Qwen3.6 raw-Unicode variant. Official HF equivalence is not newly measured or asserted; no application input/output normalization repair.', 'tokenizer_contract': 'historical_raw_reference_by_exact_typed_metadata_and_restricted_input_equivalence', 'template_input_equivalence': {'status': 'PASS', 'scope': 'nonempty_system_single_user_text_no_history_no_tools_nonthinking', 'byte_exact_public_native_render': True, 'proof_ref': 'source_equivalence'}, 'template_override_used': False, 'helper_sha256': 'ac904566519ccdf4d392dac17404ecf797286f5833963864a4c448d2eaa01301'}
CPU_REF_KEYS = ['header', 'tokenizer_comparison', 'public_contract', 'public_build', 'historical_header', 'historical_context', 'historical_official', 'historical_raw', 'historical_raw_fixture', 'source_equivalence']
CPU_REFS = {'header': {'path': 'var/reports/qwen36-gguf-header.json', 'sha256': '7434158edf19cfc7f178496b38655031abed3793ae4f3e994b171426af68fed9'}, 'tokenizer_comparison': {'path': 'var/reports/qwen36-qwen38-saved-tokenizer-comparison.json', 'sha256': '81f7496d8f484f82e7fdb6c01f566a543ef24ff6e7ac6b013dfcb59c77ceb82f'}, 'public_contract': {'path': 'var/research/native-qwen36-contract/public-proof.json', 'sha256': 'c87d48d3ce7a0621dfdbfcaa918e36664b88357a60e1dffb98e93c2dcdd0050c'}, 'public_build': {'path': 'var/research/native-qwen36-contract/build.json', 'sha256': '8d98d6d7e13e1fa597cc7e88b0c460ca7ebf6d713a94a99dc390f5798753e950'}, 'historical_header': {'path': 'var/reports/qwen38-gguf-header.json', 'sha256': 'ff168aeee125b2934b8b5204c14971915c7555c5dfc660d6fda46c2bf7fc810a'}, 'historical_context': {'path': 'var/reports/native-contract-raw-cpu-context.json', 'sha256': '5d37568d7b51d1b689b168f0e9fa6fb46ac487b70f451c82611c146f978e59be'}, 'historical_official': {'path': 'var/research/native-vocab-public-probe-v4.json', 'sha256': 'b537545d26a876a1496c2f85ad979330eba938f2880aae49190640b2404c63e0'}, 'historical_raw': {'path': 'var/research/native-vocab-public-probe-v4-raw-diagnostic.json', 'sha256': '12a5ebeafc16969f36435d9bb9e933ba12197d01ba05e8f26df41114f4e01d2d'}, 'historical_raw_fixture': {'path': 'var/research/native-tokenizer-public-parity-raw-diagnostic.json', 'sha256': '9658eb53fae81adee1b775b45f796f3484db69aea41e04a020765fa05d770514'}, 'source_equivalence': {'path': 'var/research/native-qwen36-contract/source-equivalence.json', 'sha256': 'efd6529f1f2db9e7cdd4bd5fc24e8f31e0b8e87189ee1a8865c595d4e1bb2d66'}}
HEADER = 'var/reports/qwen36-gguf-header.json'
HEADER_SHA = '7434158edf19cfc7f178496b38655031abed3793ae4f3e994b171426af68fed9'
HEADER_ARCHIVE = 'evaluations/results/phase5x/qwen36-cpu-preflight/header/header.json'
TOKENIZER_COMPARISON = 'var/reports/qwen36-qwen38-saved-tokenizer-comparison.json'
TOKENIZER_COMPARISON_SHA = '81f7496d8f484f82e7fdb6c01f566a543ef24ff6e7ac6b013dfcb59c77ceb82f'
COMPARISON_ARCHIVE = 'evaluations/results/phase5x/qwen36-cpu-preflight/header/tokenizer-comparison.json'
PROBE = 'var/research/qwen36_runtime_probe.py'
PROBE_SHA = 'ea121357ca95b34d9b7e0443dc0b5810128705ef9ca3cf87c333fbf5150b7572'
CONFIG = 'var/research/qwen36-native-launch-epoch1.json'
CONFIG_SHA = '91c651088a9cbdebb35b294ec5fa71df0cda451dff99fdab4fe7f463cd9e70bb'
CONTROLLER = 'var/research/run_native_qwen36_epoch1_probe.py'
CONTROLLER_SHA = 'ef13331c745ef78351c51bcf7bce4e5998cfce9768ad65c04472beb0bd1a9247'
SOURCE_COMMIT = 'fdd4f01d09033e0d037f1ad6cdd44307500a080f'
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
GUARD_MAX_SECONDS = 7200
RESOURCE_TOKEN_ID = 220
NEXT_EVALUATION_POLICY = {'clear_fail': 'STOP_CANDIDATE_NO_REPEAT_NO_V2_NO_UNUSED_HOLDOUT', 'pass': 'LATER_SEPARATE_MINIMUM_NEW_HOLDOUT_DECISION_ONLY', 'automatic_trials_or_retries': 0, 'first_diagnostic_calls': 125, 'future_holdout_execution_authorized': False}

def require_ready():
    # Deliberately unconditional: no hash-only dataset access, live check, freeze,
    # replay or publication until seven actual runtime pins and root activation review.
    raise ValueError('QWEN36_RUNTIME_SEVEN_AND_ROOT_ACTIVATION_PENDING')


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

# Actual saved consumer observation; no invocation is performed by this draft.
SAVED_CONSUMER = 'var/research/qwen36-runtime-saved-consumer-check.json'
SAVED_CONSUMER_SHA = '91125088b96840a73953e407072be9dbe9ba0723181cb80968280168fc768684'
RUNTIME_DEFINITION_PINS.update({'var/research/qwen36-runtime-saved-consumer-check.json': '91125088b96840a73953e407072be9dbe9ba0723181cb80968280168fc768684', 'var/research/inspect_qwen36_gguf.py': '6e19db06be126b95ec619d434b7230a88dc4542d10d506c026f9cebb71114d97', 'var/research/compare_qwen36_qwen38_saved_headers.py': 'e4325ae6f952f5aaf8b277b75af33da835b8e2fe01834c69cc0b5cf66042b756', 'var/research/native-qwen36-contract/validator.cpp': 'c55f66ab7909a921bdf8c429151cf71eb4cc17cc34a0578e65b709eae4c41ec8', 'var/research/native-qwen36-contract/build.py': '61760634036bd94e1922d6cb022ab6c2ffaf3cb30dc1c54d6bd2813a31196a0b', 'var/research/native-qwen36-contract/public_check.py': '7bb13bb7abd0fc596194d592d9f17b1ba5d5103d15dfae3193a0dd2c181f98fc', 'var/research/native-qwen36-contract/produce_final.py': 'ac904566519ccdf4d392dac17404ecf797286f5833963864a4c448d2eaa01301'})
