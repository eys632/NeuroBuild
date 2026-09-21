"""Pure Gemma12 first-diagnostic draft constants; no artifact reads or activation."""
from copy import deepcopy
from pathlib import Path
import re

ROOT = Path('/home/a202192020/NeuroBuild_v2')
PREPARATION_STATUS = 'FINAL_DEFINITION_READY_FOR_ROOT_SINGLE_FREEZE'
MODEL = 'google/gemma-4-12B-it-qat-q4_0-gguf'
REVISION = '29d097773436b69ff9feafd636ab4cf873786537'
VARIANT = 'gemma4-12b-qat-q4_0-carried-contract-v1'
SOURCE_PIN = 'f072b103714dfa1eee531f80b24512faf38e3dd2'
GGUF_SHA = '93567e57a8fe10b23569b9d9ec38cd005deedf71e29477c421a4b83f418a538b'
GGUF_BYTES = 6975879296
TEMPLATE_SHA = 'ae53464bf3be25802b3a5b37def7fd89667067d7577049b3b2d74c4d8de4c6d4'
PROPS_TEMPLATE_SHA = '6a1015c47ccfcfa67c3b772385bccee357a4d37c3cda37bd202e9047f391ab82'
TOKENIZER_SHA = 'cc8d3a0ce36466ccc1278bf987df5f71db1719b9ca6b4118264f45cb627bfe0f'
PROFILE = 'gemma4_nonthinking_llama_cpp'
LIFECYCLE = 'FROZEN_BEFORE_NATIVE_GEMMA4_12B_EXPOSED_DIAGNOSTIC'
OUT = 'evaluations/hardening_v1_exposed_native_gemma4_12b_diagnostic_freeze.json'
START = 'evaluations/results/phase5x/gemma4-12b-native-startup-epoch1/'
PUBLIC = 'evaluations/results/phase5x/gemma4-12b-native-public-smoke-epoch1/report.json'
RESOURCE = 'evaluations/results/phase5x/gemma4-12b-native-resource-epoch1/report.json'
CPU = 'var/research/native-gemma4-12b-contract/cpu-carry-forward.json'
CPU_KIND = 'GEMMA4_12B_CPU_CONTRACT_CARRY_FORWARD'
CPU_STATUS = 'CARRIED_FORWARD_BY_EXACT_INPUT_EQUIVALENCE'
HEADER = 'var/reports/gemma4-12b-gguf-header.json'
HEADER_SHA = '97a9bd3cb854c446edd7b534011eaceac389f76f8f6c49b1dd0ec5e06be4eac0'
TOKENIZER_COMPARISON = 'var/reports/gemma4-12b-saved-tokenizer-comparison.json'
TOKENIZER_COMPARISON_SHA = 'a6d70d937b44a9743735b7843b59d9ba85dca2f9db300cf13c61d108a8c5f481'
PROBE = 'var/research/gemma4_12b_runtime_probe.py'
CONFIG = 'var/research/gemma4-12b-native-launch-epoch1.json'
# None is a missing requirement, not a wildcard. Filling these cannot activate main.
SOURCE_COMMIT = 'fa3d337871f2d8078a6145b3a3632a0ddeab7ce6'
CPU_SHA = 'cb2370d7a012b40fe62dae039551d9f8d37f4961aaaccc7a9845dd8bfdee0a2f'
PROBE_SHA = '69c90fbbab9ee2a5f9db45723be6be7ebc544f44622b191bba76f3a7afc62d4d'
CONFIG_SHA = '03bef49517deff1a8410625569fa7566433db31b20b381d989e275814a71b812'
CPU_ARCHIVED_PROOF = 'evaluations/results/phase5x/gemma4-12b-cpu-preflight/contract/cpu-carry-forward.json'
CONTROLLER = 'var/research/run_native_gemma4_12b_epoch1_probe.py'
CONTROLLER_SHA = '10ca99d2f7e70b3cd5d1e0019afaea1a87cf9c9aaa66845aa62cfef0077ad2b4'
REGRESSION = 'evaluations/results/phase5x/gemma4-12b-preparation/regression/result.json'
REGRESSION_SHA = 'f2b00ee159ab4f723f72af18d41413e54f8580a6e5af3f56a193e3f44e1c0988'
REGRESSION_LOG = 'evaluations/results/phase5x/gemma4-12b-preparation/regression/backend.log.txt'
REGRESSION_LOG_SHA = '2652a0b4cc990b9e97cfbe1a9840c00232b2c5036e1c1783a964d209b6d73916'
RUNTIME_SHA = {'evaluations/results/phase5x/gemma4-12b-native-startup-epoch1/launch_config.json': '03bef49517deff1a8410625569fa7566433db31b20b381d989e275814a71b812', 'evaluations/results/phase5x/gemma4-12b-native-startup-epoch1/runtime_metadata.json': '6efd2f49f7601ac80de0e0816d2cc5e2ed91c04ed7a211ea4d40bab87f2e5cd4', 'evaluations/results/phase5x/gemma4-12b-native-startup-epoch1/resource_report.json': 'cb35db98aae6b5bfcfd3c725f541418109f32e3824da03a2ce84226f8597604a', 'evaluations/results/phase5x/gemma4-12b-native-startup-epoch1/listeners.json': '056f5a0ae82d83502edf76b83835092fa53fca7623f5f105f31c67bdb6604076', 'evaluations/results/phase5x/gemma4-12b-native-startup-epoch1/startup.json': '9949a39bb15dff4aa3d195f72f354b2055fb92407ab0a19b040f0f4842993213', 'evaluations/results/phase5x/gemma4-12b-native-public-smoke-epoch1/report.json': '042ed74b7c23ebcd084c36579fd39f4e5ca0680960a2b49da7d45f2e8b2d5e5f', 'evaluations/results/phase5x/gemma4-12b-native-resource-epoch1/report.json': 'b2edfb4c0fc73615a456b97547690b75138f01310a042fb8141767d3388666c5'}

GATES = {'schema_required':120,'schema_denominator':120,'semantic_required_at_least':114,
         'semantic_denominator':120,'critical_model_ready_fp_required':0,
         'critical_model_ready_fp_denominator':58,'unsafe_accepted_ready_total_required':0,
         'unsafe_accepted_ready_total_denominator':120}
SAMPLING = {'temperature':1.0,'top_p':0.95,'top_k':64,'min_p':0.0,
            'presence_penalty':0.0,'frequency_penalty':0.0,'repeat_penalty':1.0,
            'repeat_last_n':0,'seed':42,'samplers':['temperature','top_k','top_p','min_p']}
PATHS = {'dataset':'evaluations/requirement_hardening_v1_exposed_regression.jsonl',
         'prompt':'prompts/requirement_generation_v2_v2.txt',
         'schema':'schemas/requirement_generation_v2_decision_branches.schema.json',
         'canonical_schema':'schemas/semantic_requirement.schema.json',
         'generation_adapter':'src/neurobuild/application/requirement_generation.py',
         'parser':'src/neurobuild/application/requirements.py',
         'client':'src/neurobuild/infrastructure/local_model.py',
         'scorer':'scripts/evaluate_requirements.py',
         'weight_manifest':'runtime/models/gemma4-12b-qat-q4-0.json'}
CPU_REF_KEYS = {'public_contract','vocab','vocab_context','tokenizer_fixture','historical_aggregate',
                'normalization_witness','old_header','new_header','tokenizer_comparison','source_equivalence',
                'historical_cpu_build','historical_cpp'}
EPOCH_FIELDS = ('launch_config_sha256','pid','process_start_ticks','guard_started_at_utc')
SUPPRESSION = {'http_recipe_equal':True,'full_sampling_equivalent':False,
               'additional_suppressed_ids':[258883,258882],'suppression_eog_disjoint':True,
               'native_effect':'Model-owned negative-infinity logit bias before the unchanged HTTP sampling recipe'}


def require_ready():
    """Root-reviewed explicit release; missing or mismatched pins fail closed."""
    pins = (CPU_SHA, PROBE_SHA, CONFIG_SHA, CONTROLLER_SHA, REGRESSION_SHA,
            REGRESSION_LOG_SHA, HEADER_SHA, TOKENIZER_COMPARISON_SHA, *RUNTIME_SHA.values())
    expected_paths = {START+n for n in ('launch_config.json','runtime_metadata.json',
                                       'resource_report.json','listeners.json','startup.json')} | {PUBLIC,RESOURCE}
    expected_gates = {'schema_required':120,'schema_denominator':120,'semantic_required_at_least':114,
                     'semantic_denominator':120,'critical_model_ready_fp_required':0,
                     'critical_model_ready_fp_denominator':58,'unsafe_accepted_ready_total_required':0,
                     'unsafe_accepted_ready_total_denominator':120}
    valid = (all(type(pin) is str and re.fullmatch('[a-f0-9]{64}',pin) is not None for pin in pins)
             and set(RUNTIME_SHA)==expected_paths and len(RUNTIME_SHA)==7
             and RUNTIME_SHA[START+'launch_config.json']==CONFIG_SHA
             and VARIANT=='gemma4-12b-qat-q4_0-carried-contract-v1'
             and MODEL=='google/gemma-4-12B-it-qat-q4_0-gguf'
             and SOURCE_COMMIT=='fa3d337871f2d8078a6145b3a3632a0ddeab7ce6'
             and CPU_SHA=='cb2370d7a012b40fe62dae039551d9f8d37f4961aaaccc7a9845dd8bfdee0a2f'
             and PROBE_SHA=='69c90fbbab9ee2a5f9db45723be6be7ebc544f44622b191bba76f3a7afc62d4d'
             and CONTROLLER_SHA=='10ca99d2f7e70b3cd5d1e0019afaea1a87cf9c9aaa66845aa62cfef0077ad2b4'
             and CONFIG_SHA=='03bef49517deff1a8410625569fa7566433db31b20b381d989e275814a71b812'
             and CPU_ARCHIVED_PROOF=='evaluations/results/phase5x/gemma4-12b-cpu-preflight/contract/cpu-carry-forward.json'
             and CPU_STATUS=='CARRIED_FORWARD_BY_EXACT_INPUT_EQUIVALENCE'
             and set(CPU_REFS)==CPU_REF_KEYS and len(CPU_REFS)==12
             and GATES==expected_gates and all(type(v) is int for v in GATES.values()))
    if not valid:
        raise ValueError('GEMMA12_FINAL_PIN_OR_CONTRACT_MISMATCH')


def planned_contract():
    """Schema proposal only; no timestamps, actual epoch, SHA closure or PASS."""
    return {'preparation_status':PREPARATION_STATUS,'lifecycle':LIFECYCLE,
            'candidate_variant':VARIANT,'model_id':MODEL,'model_revision':REVISION,
            'tokenizer_revision':REVISION,'served_model':'neurobuild-gemma4-12b-qat-q4-0',
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
            'sampling_behavior':deepcopy(SUPPRESSION),'runtime_epoch_snapshot':None,
            'tokenizer_contract':None,'normalization_limitation':None,
            'source_ancestor_commit':None,'frozen_at_utc':None,'sha256':None}

CPU_SOURCE = {'src/neurobuild/infrastructure/local_model.py': '7dfc3f673ba6ab4e4970055c4cbee66ae440da2d42070af959a5fe415a9ab780', 'src/neurobuild/application/requirement_generation.py': 'fcba16f6adc906923859f3bcf4ae2f680e76716863a759582167cd9326f03198', 'src/neurobuild/application/requirements.py': 'a940f3952c0c4133ab51732f6abf76516d8ff66617470545222b52adfa49fb4a', 'prompts/requirement_generation_v2_v2.txt': '99d737124372836ba5f985fa6e5570afef693e769798844931f000fb21403cf6', 'schemas/requirement_generation_v2_decision_branches.schema.json': '36d42b9fa3d24f4a1bc1d14381110e36e8d89103b696bc83113be006b64934e2'}
CPU_REFS = {'old_header': {'path': 'evaluations/results/phase5x/gemma4-cpu-preflight/header-v2.json', 'sha256': 'd867a3300b2a93534fb1b480e8e42b30321c894aaec05b5729a529e848817756'}, 'new_header': {'path': 'var/reports/gemma4-12b-gguf-header.json', 'sha256': '97a9bd3cb854c446edd7b534011eaceac389f76f8f6c49b1dd0ec5e06be4eac0'}, 'tokenizer_comparison': {'path': 'var/reports/gemma4-12b-saved-tokenizer-comparison.json', 'sha256': 'a6d70d937b44a9743735b7843b59d9ba85dca2f9db300cf13c61d108a8c5f481'}, 'source_equivalence': {'path': 'var/research/gemma12-gemma-branch-source-equivalence.json', 'sha256': 'c21cbd6102933e1511f51625a88471b85caf8d9192dd3fe01fcd4ac644a37f20'}, 'historical_aggregate': {'path': 'evaluations/results/phase5x/gemma4-cpu-preflight/contract/final-cpu-proof.json', 'sha256': 'a27cd1f7a37899873aac346404e1cea8d0805c8db899f03eba6e3d7d7340029d'}, 'public_contract': {'path': 'evaluations/results/phase5x/gemma4-cpu-preflight/contract/public-proof.json', 'sha256': 'd7cd7032f019af566e2d7484afed85f9dab95fcbc0da06fc2a602cf5b7a76334'}, 'vocab': {'path': 'evaluations/results/phase5x/gemma4-cpu-preflight/contract/public-vocab-v2-proof.json', 'sha256': '70886f2ad74ef3758fe839f13b4b6740e22cb749f8f0989a98ea376382cc09c6'}, 'vocab_context': {'path': 'evaluations/results/phase5x/gemma4-cpu-preflight/contract/vocab-context-v2-proof.json', 'sha256': '06ef550b4ea48b3c3c65d631dafca06c85bd3d350311888b9bc5c86630caf64a'}, 'tokenizer_fixture': {'path': 'evaluations/results/phase5x/gemma4-cpu-preflight/contract/tokenizer-fixture.json', 'sha256': '42b2a10fdc4ebc066acb878a5a9e0c9e407affe0b91bc7d32145d8d360dc13e5'}, 'normalization_witness': {'path': 'evaluations/results/phase5x/gemma4-cpu-preflight/contract/normalization-witness-proof.json', 'sha256': 'bbb9ed28cdae06bb07a3f66949c2e23e59728324f74440be82b567f0a8662e73'}, 'historical_cpu_build': {'path': 'evaluations/results/phase5x/gemma4-cpu-preflight/contract/build-v2.json', 'sha256': '1b6dce0e85790b267ec2514da8c81158c76b9d01a27aa6c2e584787a160e67ee'}, 'historical_cpp': {'path': 'evaluations/results/phase5x/gemma4-cpu-preflight/contract/validator_v2.cpp', 'sha256': 'fecf647d431a3af0137f5e9459ddd8afece4e571d4a6a240dc2f4929acf9f20d'}}
FIXED_SOURCE = {'src/neurobuild/infrastructure/local_model.py': '7dfc3f673ba6ab4e4970055c4cbee66ae440da2d42070af959a5fe415a9ab780', 'src/neurobuild/application/requirement_generation.py': 'fcba16f6adc906923859f3bcf4ae2f680e76716863a759582167cd9326f03198', 'src/neurobuild/application/requirements.py': 'a940f3952c0c4133ab51732f6abf76516d8ff66617470545222b52adfa49fb4a', 'prompts/requirement_generation_v2_v2.txt': '99d737124372836ba5f985fa6e5570afef693e769798844931f000fb21403cf6', 'schemas/requirement_generation_v2_decision_branches.schema.json': '36d42b9fa3d24f4a1bc1d14381110e36e8d89103b696bc83113be006b64934e2', 'scripts/evaluate_requirements.py': '48b919e8ef9ec41ee2765c66fd5d752202248f53502616ec01d687be87f42f24', 'scripts/gpu_preflight.py': '988d9493dd73d0e00b039f7d050f3ae52a4073833de23fc58eabc20ee58163fb', 'scripts/llama_server.py': '6a58ee1ea09636df182125da4a4a2711012e6c53f5f90c06548a63b9915369ed', 'scripts/model_guard.py': 'cc95f6cccf9ca5b749bea2fc8c82d2af9d56d55b94a6aee947379b3a2f4de528', 'scripts/native_model_bootstrap.py': '22e56159a6496aabf52dc6b567c800c54822c9def9713eb8a4ff0fac4183c2bf', 'scripts/verify_model_listeners.py': '2d7771d414a7faae4138ea555349d1f7f111d36498ad9815f64ac51910d758dd', 'runtime/models/gemma4-12b-qat-q4-0.json': '7c14b3edaa691341c8759300e81825a8b0c9bf4924dec240df35be648c7b3990', 'schemas/semantic_requirement.schema.json': 'dd131db08fe9087e795059445b075f22876e44b42481201cc0ea70608a708f94', 'schemas/requirement_generation_v2.schema.json': '6ca6fed3e8666244cd4bd779d33c0dd647490d5f641134307930008ea440436c'}
DRAFT_DIR = 'var/research/gemma12-first-diagnostic-draft/'
REPLAY_PATH = DRAFT_DIR+'replay_native_gemma12_exposed.py'
FREEZER_PATH = DRAFT_DIR+'freeze_native_gemma12_diagnostic.py'
DEFINITION_PATHS = [DRAFT_DIR+x for x in ('contract.py','evidence.py','freeze_native_gemma12_diagnostic.py','replay_native_gemma12_exposed.py')]
V2_FREEZE='evaluations/hardening_v2_dataset_freeze.json'
V2_EXPOSURE='evaluations/hardening_v2_input_exposure_addendum.json'
V2_OUTPUT_EXPOSURE='evaluations/hardening_v2_model_output_exposure_record.json'
V2_OUTPUT_EXPOSURE_SHA='25c080827a6d57aa6bc864495e537490dc7fa48b3ccf91df297a47b9815d447b'
DATASET_SHA='7e5b9a05932df7aafdbf683655b044b3e3b25cbffb4115d298e1490aecbc7a5b'
V2_DATASET='evaluations/requirement_hardening_v2_holdout.jsonl'
V2_DATASET_SHA='7416f05613b1490358672f3926770dbd8653e676577eeee6ba65f863b27cec40'
HEADER_ARCHIVE='evaluations/results/phase5x/gemma4-12b-cpu-preflight/header.json'
COMPARISON_ARCHIVE='evaluations/results/phase5x/gemma4-12b-cpu-preflight/tokenizer-comparison.json'

RUNTIME_DEFINITION_PINS = {'var/research/native_runtime_probe.py': 'ac100df7949b2b14a517c4568fa66369bd98c599b39507ef19f873490a0f9f63', 'var/research/gemma12-runtime-carry-consumer-controls.json': '836f1421ca51f75d1db5a9fdd1732662e3c57d0dcf9f941dafd2f5a21b32677d', 'var/research/test_gemma12_runtime_carry_consumer.py': 'dbd47e2ee642f3cc31c49827aeeed122a1b3a38441afe572da94d0db307e99fc', 'var/research/gemma12-runtime-activation-binding.json': '9e0db49c46bbd30d81fcb6001f749fc42124e87b6b160bdd75fa23d31b626f31', 'var/research/gemma12-runtime-activation.patch': 'df845651f0fbfb00a8a8bc837db33f30468073e892c3b02896e25c567a18278f'}
