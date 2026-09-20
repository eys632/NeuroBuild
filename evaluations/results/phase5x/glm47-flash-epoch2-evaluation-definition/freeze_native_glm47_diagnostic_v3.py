"""GLM epoch2 first quality freezer; epoch1 prerequisites and fresh epoch2 startup required.

No HTTP, model, GPU, weight hashing, dataset parsing or old evaluation replay.
No quality request is made. Root runs dry-check/publication only after review.
Missing or inconsistent actual CPU/runtime evidence prevents publication.
"""
from datetime import datetime, timezone
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

ROOT = Path('/home/a202192020/NeuroBuild_v2')
MODEL = 'ggml-org/GLM-4.7-Flash-GGUF'
REVISION = '7559e96b7e324ab405897dc2b91492b0f376ad4a'
VARIANT = 'glm47-flash-gguf-nonthinking-v1'
SOURCE_PIN = 'f072b103714dfa1eee531f80b24512faf38e3dd2'
GGUF_SHA = 'b6019edc5fbe37d3660d2e994d16c839a7855a6f03362c5dcf8142ba479cd0d2'
GGUF_BYTES = 18244193920
TEMPLATE_SHA = 'd63ad536c3c81880043e22ec7fd08db42b4d8fb7c89c7138bc562bfa25281375'
TOKENIZER_SHA = '19e773648cb4e65de8660ea6365e10acca112d42a854923df93db4a6f333a82d'
HEADER_SHA = '595a7efd19914b65e91f1d92aaee141a0457472039c7278264cc1b5d314659ef'
PROFILE = 'glm47_flash_nonthinking_llama_cpp'
LIFECYCLE = 'FROZEN_BEFORE_NATIVE_GLM47_FLASH_EXPOSED_DIAGNOSTIC'
PREPARATION_STATUS = 'FINAL_DEFINITION_REQUIRES_ACTUAL_SAVED_RUNTIME_PASS'
CPU_SHA = '54ab0062c5d22112ed3349e0021391a4dd17f6d5f8698ac8a02cc096b08a1847'
REGRESSION = 'evaluations/results/phase5x/glm47-flash-preparation/regression/regression.json'
CPU = 'var/research/native-glm47-contract/final-cpu-proof.json'
START = 'evaluations/results/phase5x/glm47-flash-native-startup-epoch1/'
PUBLIC = 'evaluations/results/phase5x/glm47-flash-native-public-smoke-epoch1/report.json'
RESOURCE = 'evaluations/results/phase5x/glm47-flash-native-resource-epoch1/report.json'
PROBE = 'var/research/glm47_flash_runtime_probe_v2.py'
V2_FREEZE = 'evaluations/hardening_v2_dataset_freeze.json'
V2_EXPOSURE = 'evaluations/hardening_v2_input_exposure_addendum.json'
V2_OUTPUT_EXPOSURE = 'evaluations/hardening_v2_model_output_exposure_record.json'
GATES = {'schema_required': 120, 'schema_denominator': 120, 'semantic_required_at_least': 114, 'semantic_denominator': 120, 'critical_model_ready_fp_required': 0, 'critical_model_ready_fp_denominator': 58, 'unsafe_accepted_ready_total_required': 0, 'unsafe_accepted_ready_total_denominator': 120}
SAMPLING = {'temperature': 1.0, 'top_p': 0.95, 'top_k': 0, 'min_p': 0.0, 'presence_penalty': 0.0, 'frequency_penalty': 0.0, 'repeat_penalty': 1.0, 'repeat_last_n': 0, 'seed': 42, 'samplers': ['temperature', 'top_k', 'top_p', 'min_p']}
OUT = ROOT/'evaluations/hardening_v1_exposed_native_glm47_diagnostic_freeze.json'
REV = REVISION
MODEL_SHA = GGUF_SHA
DATASET = 'evaluations/requirement_hardening_v1_exposed_regression.jsonl'
PROMPT = 'prompts/requirement_generation_v2_v2.txt'
SCHEMA = 'schemas/requirement_generation_v2_decision_branches.schema.json'
BASE = 'evaluations/hardening_v1_exposed_generation2_32b_thinking_diagnostic_freeze.json'
V2 = V2_FREEZE
CPU_ARCHIVE = 'evaluations/results/phase5x/glm47-flash-native-cpu'
PLAN = 'docs/glm47_flash_diagnostic_plan.md'
ARCHIVE = 'evaluations/results/phase5x/glm47-flash-preparation'
REPLAY = 'var/research/replay_native_glm47_exposed_v3.py'
REPLAY_SHA = '386ba1d07bcba38c8d88509da5743443fb1330c3c866d39117f71195549f2576'
PREPARATION_RECEIPT = 'var/research/glm47-diagnostic-draft-static-proof.json'
SELFTEST = 'var/research/glm47-epoch-transition-v3-proof.json'
SELFTEST_SOURCE = 'var/research/check_glm47_epoch_transition_v3.py'
LOG_SHA = 'c342132012c9d6192164b09ddf3c806b82faaaaec3cc8be99379f2cea2e0463d'
FIXED = {'scripts/gpu_preflight.py': '988d9493dd73d0e00b039f7d050f3ae52a4073833de23fc58eabc20ee58163fb', 'scripts/llama_server.py': '6a58ee1ea09636df182125da4a4a2711012e6c53f5f90c06548a63b9915369ed', 'scripts/model_guard.py': 'cc95f6cccf9ca5b749bea2fc8c82d2af9d56d55b94a6aee947379b3a2f4de528', 'scripts/native_model_bootstrap.py': '22e56159a6496aabf52dc6b567c800c54822c9def9713eb8a4ff0fac4183c2bf', 'scripts/verify_model_listeners.py': '2d7771d414a7faae4138ea555349d1f7f111d36498ad9815f64ac51910d758dd', 'src/neurobuild/application/requirement_generation.py': 'fcba16f6adc906923859f3bcf4ae2f680e76716863a759582167cd9326f03198', 'src/neurobuild/application/requirements.py': 'a940f3952c0c4133ab51732f6abf76516d8ff66617470545222b52adfa49fb4a', 'evaluations/requirement_hardening_v1_exposed_regression.jsonl': '7e5b9a05932df7aafdbf683655b044b3e3b25cbffb4115d298e1490aecbc7a5b', 'prompts/requirement_generation_v2_v2.txt': '99d737124372836ba5f985fa6e5570afef693e769798844931f000fb21403cf6', 'schemas/requirement_generation_v2.schema.json': '6ca6fed3e8666244cd4bd779d33c0dd647490d5f641134307930008ea440436c', 'schemas/requirement_generation_v2_decision_branches.schema.json': '36d42b9fa3d24f4a1bc1d14381110e36e8d89103b696bc83113be006b64934e2', 'schemas/semantic_requirement.schema.json': 'dd131db08fe9087e795059445b075f22876e44b42481201cc0ea70608a708f94', 'scripts/evaluate_requirements.py': '4fc1335e3372518c3534267613cbc4ad0d0cb0772a149ce286ce703f2b886048', 'src/neurobuild/infrastructure/local_model.py': '7dfc3f673ba6ab4e4970055c4cbee66ae440da2d42070af959a5fe415a9ab780', 'tests/test_local_model.py': 'd76731e5ee613ef664f76d078caf5b775c65b265c63913eaf527f40010e41510', 'tests/test_native_requirement_evaluation.py': 'f52d284fd62d78e8e41e8b32b883d6865f8978346257b2b0c8f3ed703fde4a04', 'runtime/models/glm47-flash-q4-k.json': '8f2c13b9fad51c6d65588a2b2b70ed966168259eaa42e2f997c59dd97be1814c', 'evaluations/results/phase5x/glm47-flash-preparation/regression/regression.json': '293bfc5b4f94e728af5eeb021a3aae2230376a74dae6e631d0c70a1c4e513fac'}
COPY_SOURCE_SHA = '268a3437cfe09494e6b39252c7c1a837ec3c099eba1e30b4c812f95b7aac6d82'


CONFIG_SHA = '4824463fcabca13c2eaa07a9774c324b7980a2383915868f4f493b149dc245c4'
PROBE_SHA = '4399c90d32e0e472455bae5e907c8a479fdac550fed46978d8001c6d894d69ea'
CPU_ARCHIVED_PROOF = 'evaluations/results/phase5x/glm47-flash-runtime-definition/aggregate/final-cpu-proof.json'
RUNTIME_ARCHIVE = 'evaluations/results/phase5x/glm47-flash-runtime-definition'
CONTROLLER = 'var/research/run_native_glm47_epoch1_probe_v2.py'
CONTROLLER_SHA = '065f41afb9b5d55297f4e5114fba3642eeb3adaab18fcf21e6e0c5f42aeaba37'
RUNTIME_CPU_PROOF = 'var/research/glm47-runtime-v2-cpu-proof.json'
RUNTIME_CPU_PROOF_SHA = '0690eee68f5479927fb174243b4073cf26af433f8449a3ce9be124cbab15ac22'
REGRESSION_SHA = '293bfc5b4f94e728af5eeb021a3aae2230376a74dae6e631d0c70a1c4e513fac'
REGRESSION_LOG_SHA = 'c342132012c9d6192164b09ddf3c806b82faaaaec3cc8be99379f2cea2e0463d'
LAUNCHER_SHA = '6a58ee1ea09636df182125da4a4a2711012e6c53f5f90c06548a63b9915369ed'
CPU_REFS = {'header': {'path': 'var/reports/glm47-flash-gguf-header.json', 'sha256': '595a7efd19914b65e91f1d92aaee141a0457472039c7278264cc1b5d314659ef'}, 'public_contract': {'path': 'var/research/native-glm47-contract/public-proof-v3.json', 'sha256': 'd8f8fe1faf2ee73b06f6df35d16dba3a29cb78ad41af35a8a1be6cff888ac85c'}, 'public_vocab': {'path': 'var/research/native-glm47-contract/public-vocab-proof.json', 'sha256': 'f3e31a724dcec94f6d3b285a9dd793d6a8b6c91c3c8c475a63c25709c94d6cf7'}, 'tokenizer_fixture': {'path': 'var/research/native-glm47-contract/official-tokenizer-fixture.json', 'sha256': 'e67bd4d05462587e0466f092351ada8c8fa4efdd9a10da0b4cecb25a4d3dc8f3'}, 'vocab_context': {'path': 'var/research/native-glm47-contract/vocab-context-proof.json', 'sha256': '66e2ab245e0d7c2a2760d2b98e0a191fb8b27248be6fae6d61cf922c814bb607'}}
CPU_SOURCE = {'prompts/requirement_generation_v2_v2.txt': '99d737124372836ba5f985fa6e5570afef693e769798844931f000fb21403cf6', 'schemas/requirement_generation_v2_decision_branches.schema.json': '36d42b9fa3d24f4a1bc1d14381110e36e8d89103b696bc83113be006b64934e2', 'src/neurobuild/application/requirement_generation.py': 'fcba16f6adc906923859f3bcf4ae2f680e76716863a759582167cd9326f03198', 'src/neurobuild/application/requirements.py': 'a940f3952c0c4133ab51732f6abf76516d8ff66617470545222b52adfa49fb4a', 'src/neurobuild/infrastructure/local_model.py': '7dfc3f673ba6ab4e4970055c4cbee66ae440da2d42070af959a5fe415a9ab780'}
V2_OUTPUT_EXPOSURE_SHA = '25c080827a6d57aa6bc864495e537490dc7fa48b3ccf91df297a47b9815d447b'


EVALUATION_START = 'evaluations/results/phase5x/glm47-flash-native-startup-epoch2/'
EVALUATION_CONFIG_SHA = 'd0a5ae9663d9caf4420651a018ce687325b0e8fc7fb154963e948b4251e56994'
EVALUATION_CONTROLLER = 'var/research/run_native_glm47_epoch2_startup.py'
EVALUATION_CONTROLLER_SHA = 'c4fa474512ae41aa107c8564b278397886deb2682e16c6663ae055a4aa1be8e4'
EVALUATION_STARTUP_SHA = '29f5443a8e2b9d1936801860d5776dc3014ba69ba6f73bc6a3407fb4ca9b098c'
FINAL_GUARD = 'evaluations/results/phase5x/glm47-flash-epoch1-time-limit-stop/final_guard.json'
FINAL_GUARD_SHA = '792b8585672b82d6a702ef3600149fc19d4250fe5f48c795eb441de1eb3d1e86'
EPOCH_CARRY_POLICY = 'Same inference configuration; epoch1 public/resource carried forward; epoch2 startup GET-only; no repeated quality or public/resource calls'

def require_ready():
    # Both actual epochs and exact saved proof hashes are validated before use.
    require(EVALUATION_STARTUP_SHA == '29f5443a8e2b9d1936801860d5776dc3014ba69ba6f73bc6a3407fb4ca9b098c',
            'EPOCH2_ACTUAL_STARTUP_PIN_CHANGED')

def require(ok, code):
    if not ok:
        raise ValueError(code)

def checked(name):
    path = ROOT / name
    require(not path.is_symlink() and path.resolve().is_relative_to(ROOT), 'PATH_INVALID')
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and info.st_nlink == 1,
            'ARTIFACT_NOT_OWNED_REGULAR')
    require(path.suffix not in ('.gguf','.safetensors') and info.st_size <= 64*1024**2,
            'PAYLOAD_OR_LARGE_ARTIFACT_FORBIDDEN')
    return path

def digest(name):
    with checked(name).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

def load(name):
    def pairs(items):
        out={}
        for key,value in items:
            require(key not in out,'JSON_DUPLICATE_KEY')
            out[key]=value
        return out
    return json.loads(checked(name).read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda _: require(False,'JSON_NONFINITE'))

def validate_current(probe,config,startup,artifacts,guard):
    live,_=probe.read_json(config.report_file)
    probe.validate_guard(config,live,artifacts)
    require(live['child_pid']==startup['pid'] and live['started_at_utc']==guard['started_at_utc'],
            'GUARD_EPOCH_CHANGED')
    probe.epoch(config,live['child_pid'],startup['process_start_ticks'])
    elapsed=live['elapsed_seconds']
    require(type(elapsed) in (int,float) and math.isfinite(elapsed) and 0<=elapsed<config.max_seconds,
            'GUARD_TIME_INVALID')
    return live,{'guard_max_seconds':config.max_seconds,'elapsed_seconds_at_freeze':elapsed,
                 'remaining_seconds_at_freeze':config.max_seconds-elapsed,
                 'first_request_requires_fresh_root_time_decision':True,
                 'meaning':'Guard lifetime only; not a promised125-call completion time or timeout budget.'}

def validate_regression(regression):
    require(regression['kind']=='GLM47_EXPLICIT_NATIVE_PROFILE_REGRESSION'
            and regression['status']=='PASS' and regression['tests_run']==416
            and regression['skipped']==0 and regression['duration_seconds']==19.398
            and regression['real_postgresql'] is True and regression['real_ifcopenshell'] is True
            and regression['headless'] is True and regression['cuda_visible_devices']==''
            and regression['quality_model_calls']==regression['old_evaluation_replay']==0
            and regression['log_sha256']==LOG_SHA,'REGRESSION_REQUIRED')
    for name,value in regression['source_sha256'].items():
        require(FIXED.get(name)==value,'REGRESSION_SOURCE_PIN_MISMATCH')


def validate_fixed():
    require_ready()
    for name,expected in FIXED.items(): require(digest(name)==expected,'FIXED_INPUT_CHANGED')
    baseline=load(BASE);require(baseline['gate_targets']==GATES,'QUALITY_GATE_CHANGED')
    for name in ('schemas/semantic_requirement.schema.json','schemas/requirement_generation_v2.schema.json',V2,V2_EXPOSURE):
        require(digest(name)==baseline['sha256'][name],'BASELINE_CONTRACT_CHANGED')
    v2=load(V2);require(len(v2['sha256'])==9,'V2_FREEZE_CHANGED')
    for name,expected in v2['sha256'].items():require(digest(name)==expected,'V2_ARTIFACT_CHANGED')
    regression=load(REGRESSION);validate_regression(regression)
    require(digest(regression['log_path'])==LOG_SHA,'REGRESSION_LOG_CHANGED')
    require(digest(PROBE)==PROBE_SHA and digest(CONTROLLER)==CONTROLLER_SHA
            and digest(RUNTIME_CPU_PROOF)==RUNTIME_CPU_PROOF_SHA,'RUNTIME_DEFINITION_CHANGED')
    require(digest(V2_OUTPUT_EXPOSURE)==V2_OUTPUT_EXPOSURE_SHA,'V2_EXPOSURE_CHANGED')
    for folder,filename,pin in (
        (CPU_ARCHIVE,'archive_integrity.json','a13577bc11c450ad4abfc2ee6d674cec507a239f5f183f230f25fef49c8ff996'),
        (RUNTIME_ARCHIVE,'integrity.json','368f53421a45e8ab99f1e0f44a37045cd2f47258797fbf84677aa27854a49bc3')):
        require(digest(folder+'/'+filename)==pin,'ARCHIVE_INTEGRITY_CHANGED')
    header=load('var/reports/glm47-flash-gguf-header.json')
    require(digest('var/reports/glm47-flash-gguf-header.json')==HEADER_SHA and header['status']=='PASS'
            and header['kind']=='GGUF_HEADER_AUDIT' and header['full_file_sha256_verified'] is True
            and header['file_sha256']==GGUF_SHA and header['file_bytes']==GGUF_BYTES
            and header['bindings']['quantization']=='Q4_K_M','ACTUAL_HEADER_REQUIRED')
    return regression,v2


def import_probe():
    require_ready()
    require(digest(PROBE)==PROBE_SHA,'PROBE_CHANGED')
    spec=importlib.util.spec_from_file_location('glm_freeze_probe',ROOT/PROBE)
    probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
    return probe


def validate_prerequisite_saved(probe, cpu_sha):
    require(cpu_sha==CPU_SHA and digest(CPU)==CPU_SHA,'CPU_PIN_MISMATCH')
    require(type(CONFIG_SHA) is str and re.fullmatch('[a-f0-9]{64}',CONFIG_SHA),'FINAL_CONFIG_PIN_PENDING')
    require(digest(CPU_ARCHIVED_PROOF)==cpu_sha,'CPU_ARCHIVE_LINK_MISMATCH')
    config,_=probe.load_config(ROOT/START/'launch_config.json',CONFIG_SHA)
    require(config.max_seconds==7200 and config.port==8003 and config.estimated_peak_mib==28672
            and config.peak_allowance_mib==0 and (config.batch_size,config.ubatch_size)==(64,64),
            'CONFIG_PLAN_CHANGED')
    provenance,_=probe.cpu_provenance(config,ROOT/CPU,cpu_sha)
    cpu=load(CPU)
    require(cpu['model_inference_calls']==cpu['gpu_calls']==cpu['http_calls']==0
            and cpu['candidate_variant']==VARIANT and cpu['template_override_used'] is False,'CPU_SCOPE_CHANGED')
    startup,metadata=load(START+'startup.json'),load(START+'runtime_metadata.json')
    require(startup['status']=='PASS' and startup['kind']=='GLM47_FLASH_NATIVE_STARTUP_HTTP_PROOF'
            and startup['http_get_calls']==3 and startup['model_inference_calls']==0
            and startup['raw_http_bodies_saved'] is False,'STARTUP_REQUIRED')
    require(startup['embedded_chat_template_sha256']==startup['chat_template_sha256']
            ==startup['props_reported_template_sha256']==cpu['template_sha256']==metadata['chat_template_sha256']==TEMPLATE_SHA
            and startup['embedded_chat_template_bytes']==startup['props_reported_template_bytes']==3120,'TEMPLATE_REPRESENTATION_MISMATCH')
    require(startup['native_startup_warmup_enabled'] is True
            and startup['model_inference_calls_scope']=='Explicit HTTP generation calls; native startup warmup is enabled and not counted',
            'STARTUP_INTERNAL_WARMUP_SCOPE')
    require(metadata['startup_report_sha256']==digest(START+'startup.json')
            and metadata['listener_report_sha256']==digest(START+'listeners.json')
            and metadata['launch_config_sha256']==digest(START+'launch_config.json')==CONFIG_SHA
            and startup['resource_report_sha256']==digest(START+'resource_report.json'),
            'STARTUP_HASH_BINDING_FAILED')
    platform={key:metadata[key] for key in ('compiler','cmake','cuda','driver','gpu','gpu_uuid')}
    require(probe.make_metadata(config,platform,CONFIG_SHA,digest(START+'startup.json'),
                               digest(START+'listeners.json'))==metadata,'RUNTIME_METADATA_MISMATCH')
    public,resource=load(PUBLIC),load(RESOURCE)
    require(public['status']=='PASS' and public['kind']=='GLM47_FLASH_NATIVE_PUBLIC_PRODUCTION_SMOKE'
            and public['http_calls_attempted']==1 and public['quality_gate_pass'] is False
            and public['generated_body_retained'] is False and public['sampling_profile']==PROFILE,
            'PUBLIC_SMOKE_REQUIRED')
    require(resource['status']=='PASS' and resource['kind']=='GLM47_FLASH_NATIVE_PUBLIC_CONTEXT_RESOURCE_PROBE'
            and resource['http_post_calls']==1,'RESOURCE_SMOKE_REQUIRED')
    probe.validate_resource({key:resource[key] for key in probe.base.RESOURCE_FIELDS})
    for proof in (startup,public,resource):
        for key,value in provenance.items():
            require(proof[key]==value,'CPU_PROVENANCE_EDGE_FAILED')
    artifacts=probe.glm_binding(config)
    guard=load(START+'resource_report.json');probe.validate_guard(config,guard,artifacts)
    require('chat_template_override' not in guard['native_artifacts'],'NO_TEMPLATE_OVERRIDE')
    listeners=load(START+'listeners.json')
    require(listeners['verdict']=='PASS' and listeners['all_loopback'] is True
            and listeners['snapshot_complete'] is True and listeners['uid']==os.getuid()
            and listeners['pid']==startup['pid']==guard['child_pid']
            and listeners['process_start_ticks']==startup['process_start_ticks'],'STARTUP_EPOCH_FAILED')
    for proof in (startup,public,resource):
        require(proof['launch_config_sha256']==CONFIG_SHA and proof['pid']==startup['pid']
                and proof['process_start_ticks']==startup['process_start_ticks']
                and proof['guard_started_at_utc']==guard['started_at_utc'],'PROOF_EPOCH_CHANGED')
    require(resource['guard_required_free_floor_mib']==guard['required_free_floor_mib']
            and resource['guard_aggregate_increment_limit_mib']==guard['aggregate_increment_limit_mib']==28672
            and resource['guard_minimum_observed_free_mib']>=resource['guard_required_free_floor_mib']
            and resource['guard_aggregate_peak_mib']<=28672,'RESOURCE_BUDGET_CHANGED')
    return config,provenance,cpu,startup,artifacts,guard


def validate_epoch_transition(old_launch,new_launch,old_metadata,new_metadata,old_startup,new_startup,old_guard,new_guard,listeners,final):
    require(set(old_launch)==set(new_launch),'EPOCH_CONFIG_KEYS_CHANGED')
    require({k:v for k,v in old_launch.items() if k not in ('report_file','log_file')}
            =={k:v for k,v in new_launch.items() if k not in ('report_file','log_file')},'EPOCH_INFERENCE_CONFIG_CHANGED')
    require(all(old_launch[k]!=new_launch[k] for k in ('report_file','log_file')),'EPOCH_OUTPUT_PATH_REUSED')
    require(set(old_metadata)==set(new_metadata)
            and {k:v for k,v in old_metadata.items() if k not in ('launch_config_sha256','startup_report_sha256','listener_report_sha256')}
            =={k:v for k,v in new_metadata.items() if k not in ('launch_config_sha256','startup_report_sha256','listener_report_sha256')},
            'EPOCH_RUNTIME_ARTIFACTS_OR_PLATFORM_CHANGED')
    require(final['state']=='STOPPED' and final['reason']=='TIME_LIMIT' and final['child_exit_code']==0
            and final['shutdown']['child_reaped'] is True and final['elapsed_seconds']>=7200
            and final['child_pid']==old_startup['pid']==old_guard['child_pid']
            and final['started_at_utc']==old_startup['guard_started_at_utc']==old_guard['started_at_utc']
            and final['native_artifacts']==old_guard['native_artifacts'],'PREREQUISITE_EPOCH_FINAL_STOP_REQUIRED')
    require(new_guard['state']=='RUNNING' and new_startup['status']=='PASS'
            and new_startup['kind']=='GLM47_FLASH_NATIVE_STARTUP_HTTP_PROOF'
            and new_startup['http_get_calls']==3 and new_startup['model_inference_calls']==0
            and new_startup['raw_http_bodies_saved'] is False,'NEW_EPOCH_STARTUP_REQUIRED')
    require(datetime.fromisoformat(final['completed_at_utc'])<datetime.fromisoformat(new_guard['started_at_utc'])
            and new_guard['started_at_utc']!=old_guard['started_at_utc']
            and (new_startup['pid'],new_startup['process_start_ticks'])!=(old_startup['pid'],old_startup['process_start_ticks']),
            'NEW_EPOCH_REQUIRED')
    require(new_startup['pid']==new_guard['child_pid']==listeners['pid']
            and new_startup['process_start_ticks']==listeners['process_start_ticks']
            and new_startup['guard_started_at_utc']==new_guard['started_at_utc']
            and new_startup['launch_config_sha256']==EVALUATION_CONFIG_SHA
            and listeners['verdict']=='PASS' and listeners['all_loopback'] is True
            and listeners['snapshot_complete'] is True and listeners['uid']==os.getuid(),'NEW_EPOCH_IDENTITY_FAILED')
    for key in ('candidate_variant','model_id','model_revision','cpu_proof_sha256','cpu_proof_kind','cpu_proof_refs',
                'cpu_source_sha256','cpu_checks_rerun','chat_template_sha256','embedded_chat_template_sha256',
                'embedded_chat_template_bytes','props_reported_template_sha256','props_reported_template_bytes',
                'tokenizer_contract','tokenizer_json_sha256','official_tokenizer_parity','application_input_output_nfc_repair',
                'normalization_limitation','reasoning_boundary','native_startup_warmup_enabled','model_inference_calls_scope'):
        require(new_startup[key]==old_startup[key],'NEW_EPOCH_PROVENANCE_CHANGED')
    require(new_guard['native_artifacts']==old_guard['native_artifacts']
            and new_guard['native_identity_verified'] is True and new_guard['physical_gpu_index']==3
            and new_guard['required_cuda_visible_devices']=='3' and new_guard['max_num_seqs']==1
            and (new_guard['batch_size'],new_guard['ubatch_size'])==(64,64)
            and new_guard['max_model_len']==4096 and new_guard['enable_reasoning'] is False
            and new_guard['reasoning_parser']=='deepseek' and new_guard['native_output_policy']=='DISCARD_STDOUT_STDERR'
            and new_guard['native_core_dump_limit_bytes']==0
            and new_guard['aggregate_increment_limit_mib']==28672
            and new_guard['minimum_observed_free_mib']>=new_guard['required_free_floor_mib']
            and new_guard['observed_baseline_relative_peak_mib']<=28672,'NEW_EPOCH_GUARD_SCOPE')

def validate_saved(probe,cpu_sha):
    old_config,provenance,cpu,old_startup,old_artifacts,old_guard=validate_prerequisite_saved(probe,cpu_sha)
    require(digest(FINAL_GUARD)==FINAL_GUARD_SHA,'FINAL_STOP_HASH_CHANGED')
    require(digest(EVALUATION_CONTROLLER)==EVALUATION_CONTROLLER_SHA,'NEW_STARTUP_CONTROLLER_CHANGED')
    require(digest(EVALUATION_START+'startup.json')==EVALUATION_STARTUP_SHA,'NEW_STARTUP_PIN_PENDING_OR_CHANGED')
    config,_=probe.load_config(ROOT/EVALUATION_START/'launch_config.json',EVALUATION_CONFIG_SHA)
    artifacts=probe.glm_binding(config)
    startup=load(EVALUATION_START+'startup.json');metadata=load(EVALUATION_START+'runtime_metadata.json')
    guard=load(EVALUATION_START+'resource_report.json');listeners=load(EVALUATION_START+'listeners.json')
    probe.validate_guard(config,guard,artifacts)
    validate_epoch_transition(load(START+'launch_config.json'),load(EVALUATION_START+'launch_config.json'),
        load(START+'runtime_metadata.json'),metadata,old_startup,startup,old_guard,guard,listeners,load(FINAL_GUARD))
    require(metadata['startup_report_sha256']==digest(EVALUATION_START+'startup.json')
            and metadata['listener_report_sha256']==digest(EVALUATION_START+'listeners.json')
            and metadata['launch_config_sha256']==digest(EVALUATION_START+'launch_config.json')==EVALUATION_CONFIG_SHA
            and startup['resource_report_sha256']==digest(EVALUATION_START+'resource_report.json'),'NEW_STARTUP_HASH_EDGES')
    platform={key:metadata[key] for key in ('compiler','cmake','cuda','driver','gpu','gpu_uuid')}
    require(probe.make_metadata(config,platform,EVALUATION_CONFIG_SHA,digest(EVALUATION_START+'startup.json'),
            digest(EVALUATION_START+'listeners.json'))==metadata,'NEW_RUNTIME_METADATA_MISMATCH')
    return config,provenance,cpu,startup,artifacts,guard


def cpu_references(cpu):
    out={}
    for ref in cpu['proof_refs'].values():
        require(set(ref)=={'path','sha256'} and type(ref['path']) is str
                and not Path(ref['path']).is_absolute() and '..' not in Path(ref['path']).parts,
                'CPU_REF_PATH_INVALID')
        require(ref['path'] not in out or out[ref['path']]==ref['sha256'],'CPU_REF_COLLISION')
        require(digest(ref['path'])==ref['sha256'],'CPU_REF_CHANGED');out[ref['path']]=ref['sha256']
    return out


def collect_files(config,cpu,regression,v2):
    files=set(FIXED)|set(v2['sha256'])|set(cpu_references(cpu))|{
        CPU,CPU_ARCHIVED_PROOF,PUBLIC,RESOURCE,BASE,V2,V2_EXPOSURE,V2_OUTPUT_EXPOSURE,PLAN,
        PROBE,CONTROLLER,RUNTIME_CPU_PROOF,regression['log_path'],REPLAY,SELFTEST,SELFTEST_SOURCE,
        FINAL_GUARD,EVALUATION_CONTROLLER,'var/research/freeze_native_glm47_diagnostic_v2.py',
        'var/research/replay_native_glm47_exposed_v2.py','var/research/glm47-diagnostic-v2-metadata-proof.json',
        str(Path(__file__).relative_to(ROOT)),str(config.source_report),str(config.build_report),str(config.model_header_report),
        'var/research/freeze_native_glm47_diagnostic.py','var/research/replay_native_glm47_exposed.py',
        PREPARATION_RECEIPT,'var/research/glm47-diagnostic-draft-evidence-plan.md',
        'docs/reports/phase5x_glm47_flash_preparation_report.md',
        'docs/reports/phase5x_glm47_flash_native_cpu_report.md'}
    for folder in (ARCHIVE,CPU_ARCHIVE,RUNTIME_ARCHIVE,START,EVALUATION_START,
                   'evaluations/results/phase5x/glm47-flash-runtime-review',
                   'evaluations/results/phase5x/glm47-flash-epoch1-time-limit-stop',
                   'evaluations/results/phase5x/glm47-flash-runtime-observation-epoch1'):
        path=ROOT/folder;require(path.is_dir() and not path.is_symlink(),'ARCHIVE_MISSING')
        members=[p for p in path.rglob('*') if p.is_file()]
        require(0<len(members)<=160,'ARCHIVE_COUNT_INVALID')
        files.update(str(p.relative_to(ROOT)) for p in members)
    return {str(checked(name).relative_to(ROOT)) for name in files}

def main():
    require_ready()  # Before argument processing, artifacts, process checks or publication.
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cpu-proof-sha256',required=True)
    parser.add_argument('--dry-check',action='store_true',help='Validate actual evidence and own epoch, without publishing')
    args=parser.parse_args()
    require(not OUT.exists() and not OUT.is_symlink(),'FREEZE_ALREADY_EXISTS')
    require(os.environ.get('CUDA_VISIBLE_DEVICES')=='','CPU_ENV_REQUIRED')
    require(digest(REPLAY)==REPLAY_SHA,'REPLAY_PIN_MISMATCH')
    prepared=load(SELFTEST)
    require(prepared['status']=='PASS_NEW_EPOCH_TRANSITION_CONTROLS_ONLY'
            and prepared['helper_sha256']==digest(str(Path(__file__).relative_to(ROOT)))
            and prepared['replay_sha256']==REPLAY_SHA and prepared['core_functions_invoked']==0
            and prepared['selfcheck_sha256']==digest(SELFTEST_SOURCE),'NEW_METADATA_PREPARATION_REQUIRED')
    regression,v2=validate_fixed()
    probe=import_probe()
    config,provenance,cpu,startup,artifacts,guard=validate_saved(probe,args.cpu_proof_sha256)
    live,time_observation=validate_current(probe,config,startup,artifacts,guard)
    sys.path.insert(0,str(ROOT/'src'))
    from neurobuild.infrastructure.local_model import LocalRequirementClient
    client=LocalRequirementClient('http://127.0.0.1:8003',config.served_model_name,
        prompt_path=ROOT/PROMPT,schema_path=ROOT/SCHEMA,generation_contract='2.0',
        protocol='llama_cpp_json_schema',sampling_profile=PROFILE,max_tokens=768,timeout=120)
    require(client.sampling_parameters==SAMPLING and client.enable_thinking is False,'CLIENT_PROFILE_CHANGED')
    files=collect_files(config,cpu,regression,v2)
    hashes={name:digest(name) for name in sorted(files)}
    require(all(hashes[name]==expected for name,expected in FIXED.items()),'FIXED_INPUT_CHANGED_DURING_FREEZE')
    require(hashes[CPU]==args.cpu_proof_sha256,'CPU_CHANGED_DURING_FREEZE')
    require(hashes[CPU_ARCHIVED_PROOF]==args.cpu_proof_sha256,'CPU_ARCHIVE_CHANGED_DURING_FREEZE')
    require(all(hashes[name]==expected for name,expected in v2['sha256'].items()),'V2_CHANGED_DURING_FREEZE')
    require(all(hashes[name]==expected for name,expected in regression['source_sha256'].items()),
            'REGRESSION_SOURCE_CHANGED_DURING_FREEZE')
    require(all(hashes[ref['path']]==ref['sha256'] for ref in cpu['proof_refs'].values()),
            'CPU_REF_CHANGED_DURING_FREEZE')
    frozen={'lifecycle':LIFECYCLE,
        'frozen_at_utc':datetime.now(timezone.utc).isoformat(),
        'source_ancestor_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'candidate_variant':VARIANT,'tokenizer_contract':provenance,
        'original_embedded_template_sha256':TEMPLATE_SHA,
        'effective_chat_template_sha256':TEMPLATE_SHA,'chat_template_override':None,
        'official_tokenizer_parity':cpu['official_tokenizer_parity'],
        'application_input_output_nfc_repair':False,
        'normalization_limitation':cpu['normalization_limitation'],
        'gold_status':'AUTO-GENERATED / NOT HUMAN VERIFIED','dataset':DATASET,'split':'development',
        'cases':120,'ready_gold':62,'nonready_gold':58,'warmups_per_run':5,'trials_per_case':1,
        'expected_http_calls':125,'pipeline':'single','generation_contract':'2.0',
        'model_id':MODEL,'model_revision':REV,'tokenizer_revision':REV,'served_model':config.served_model_name,
        'prompt':PROMPT,'generation_schema':SCHEMA,'canonical_schema':'schemas/semantic_requirement.schema.json',
        'protocol':'llama_cpp_json_schema','sampling_profile':PROFILE,'sampling_request_parameters':SAMPLING,
        'enable_thinking':False,'reasoning_parser':'deepseek','max_tokens':768,'timeout_seconds':120,
        'max_model_len':4096,'concurrency':1,'maximum_calls_per_case':1,'gate_targets':GATES,
        'raw_decision_observed_required':120,'automatic_repetitions':False,
        'runtime_metadata':EVALUATION_START+'runtime_metadata.json','cpu_context_report':CPU,
        'prerequisite_epoch1':{'runtime_metadata':START+'runtime_metadata.json',
            'public_smoke_report':PUBLIC,'resource_probe_report':RESOURCE,'final_guard_report':FINAL_GUARD,
            'runtime_epoch_snapshot':{key:load(START+'startup.json')[other] for key,other in
                (('pid','pid'),('start_ticks','process_start_ticks'),('guard_started_at_utc','guard_started_at_utc'))}},
        'epoch_carryforward_policy':EPOCH_CARRY_POLICY,
        'cpu_context_archive':CPU_ARCHIVED_PROOF,'prior_v2_model_output_exposure_record':V2_OUTPUT_EXPOSURE,
        'public_smoke_report':PUBLIC,'resource_probe_report':RESOURCE,
        'runtime_epoch_snapshot':{'pid':startup['pid'],'start_ticks':startup['process_start_ticks'],
                                  'guard_started_at_utc':live['started_at_utc']},
        'guard_time_observation':time_observation,
        'decision_policy':'Raw final decision beforevalidation; errors/truncation/unknown retain denominators; no retry/repair/fallback.',
        'limits':['Exposed synthetic regression only; previousV2 outputs are also exposed. No unseen or human verification claim.',
                  'Model/quantization/template/sampling differ; no isolated causal attribution.',
                  'Official metadata/native public20 parity and raw roundtrip are bounded observations; no universalUnicode guarantee.',
                  'No application input/output repair; original quote/parser/gold/gates unchanged; RTX5090 unverified.'],
        'regression':regression,'sha256':hashes}
    require(digest(REPLAY)==REPLAY_SHA,'REPLAY_CHANGED_DURING_FREEZE')
    validate_current(probe,config,startup,artifacts,guard)
    require('torch' not in sys.modules,'TORCH_IMPORT_FORBIDDEN')
    if args.dry_check:
        print(json.dumps({'status':'ACTUAL_PREREQUISITES_PASS_NOT_FROZEN','candidate_variant':VARIANT,'bound_files':len(hashes)}))
        return
    with OUT.open('x') as stream:
        json.dump(frozen,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
        stream.flush();os.fsync(stream.fileno())
    print(json.dumps({'status':'FROZEN_NOT_EVALUATED','path':str(OUT.relative_to(ROOT)),
                      'sha256':digest(OUT),'candidate_variant':VARIANT,'bound_files':len(hashes)}))

if __name__=="__main__":
    main()
