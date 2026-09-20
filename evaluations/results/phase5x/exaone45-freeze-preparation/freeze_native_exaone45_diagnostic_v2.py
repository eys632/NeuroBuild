"""Prepare one EXAONE raw-Unicode exposed120x1+5 freeze after real completed prerequisites.

Root runs only after independently reviewing the final CPU proof and runtime
archives. No model/HTTP/GPU calls, weight hashing, dataset parsing, old125 replay,
or old regression/runtime re-execution. Own live PID/listener identity is checked.
Output is exclusive-create and never overwrites a previous freeze.
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
OUT = ROOT / 'evaluations/hardening_v1_exposed_native_exaone45_diagnostic_freeze.json'
MODEL = 'LGAI-EXAONE/EXAONE-4.5-33B-GGUF'
MODEL_SHA = '5ba3839b67dcee5618ea7b2206cedc8f9e2ec90fbcec3c95a8cc8b33967f6baf'
REV = '0e969634ef24db05151b435970297a6dee634b7e'
VARIANT = 'exaone45-gguf-continue-free-raw-unicode-korean-v1'
TEMPLATE_VARIANT = 'exaone45-gguf-continue-free-korean-v1'
SOURCE_PIN = 'f072b103714dfa1eee531f80b24512faf38e3dd2'
PROFILE = 'exaone45_nonthinking_llama_cpp'
DATASET = 'evaluations/requirement_hardening_v1_exposed_regression.jsonl'
PROMPT = 'prompts/requirement_generation_v2_v2.txt'
SCHEMA = 'schemas/requirement_generation_v2_decision_branches.schema.json'
BASE = 'evaluations/hardening_v1_exposed_generation2_32b_thinking_diagnostic_freeze.json'
V2 = 'evaluations/hardening_v2_dataset_freeze.json'
V2_EXPOSURE = 'evaluations/hardening_v2_input_exposure_addendum.json'
V2_OUTPUT_EXPOSURE = 'evaluations/hardening_v2_model_output_exposure_record.json'
EMBEDDED_TEMPLATE_SHA = 'e4ece7acc79ba82121d4d57791fb7ecb796e39185087197377da5d2286bec0e5'
EFFECTIVE_TEMPLATE = 'runtime/templates/exaone45-continue-free.jinja'
EFFECTIVE_TEMPLATE_SHA = '7de6c8ba3df6db54564c7a63385cc29572c0a616d5848961e969ecbb8c349851'
TEMPLATE_PROVENANCE = 'runtime/templates/exaone45-continue-free.provenance.json'
PUBLIC_TEMPLATE = 'evaluations/results/phase5x/exaone45-template-header-preflight/contract/public-proof-v3.json'
PUBLIC_TEMPLATE_SHA = 'fc7109fe4e9fbbe4a619ad16dc701cda01a4976ec8bd53d726aeb09f34f39408'
HEADER = 'evaluations/results/phase5x/exaone45-template-header-preflight/reports/exaone45-gguf-header-v2.json'
HEADER_SHA = 'fb5260c6e1e3356741f7728e4077f771763ea39affd77e8ac9772e417aa70c12'
REGRESSION = 'evaluations/results/phase5x/exaone45-template-header-preflight/regression.json'
LOG_SHA = 'b2ae7a43b2fa3af31758528cf0ada58a63e689c6da6f53434f738bfe419ef20b'
CPU = 'var/research/native-exaone45-contract/final-cpu-proof.json'
CPU_SHA = '2a937a8adeca827f4724c9b65947291005aa34dc8ca4af823739fd09ca248209'
CPU_ARCHIVE = 'evaluations/results/phase5x/exaone45-cpu-preflight'
CPU_ARCHIVED_PROOF = 'evaluations/results/phase5x/exaone45-cpu-preflight/contract/final-cpu-proof.json'
START = 'evaluations/results/phase5x/exaone45-native-startup-epoch1/'
PUBLIC = 'evaluations/results/phase5x/exaone45-native-public-smoke-epoch1/report.json'
RESOURCE = 'evaluations/results/phase5x/exaone45-native-resource-epoch1/report.json'
PROBE = 'var/research/exaone45_runtime_probe_v4.py'
REPLAY = 'var/review-tools/replay_native_exaone45_exposed_v3.py'
CONFIG_SHA = '1e872da88b6d00750447dd7c39213d7a4ce19b161fa64cb4c51cab1f7b8b7761'
REPLAY_SHA = '47981646b4efe96ba7b7f85c991fad526b287f5c64407102aefcd2d8bbee30e4'
REPLAY_PROOF = 'var/research/exaone45-replay-final-evidence-cpu-proof.json'
REPLAY_PROOF_SHA = 'c4a4619841901af87068465e0c0138a8d14f3833f0f41ba6e477919c8ae9fc9f'
SELFTEST = 'var/research/exaone45-freezer-v2-cpu-proof.json'
SELFTEST_SOURCE = 'var/research/test_freeze_native_exaone45_diagnostic_v2.py'
ARCHIVE = 'evaluations/results/phase5x/exaone45-template-header-preflight'
GATES = {'schema_required': 120, 'schema_denominator': 120, 'semantic_required_at_least': 114, 'semantic_denominator': 120, 'critical_model_ready_fp_required': 0, 'critical_model_ready_fp_denominator': 58, 'unsafe_accepted_ready_total_required': 0, 'unsafe_accepted_ready_total_denominator': 120}
SAMPLING = {'temperature': 0.6, 'top_p': 0.95, 'top_k': 20, 'min_p': 0.0, 'presence_penalty': 1.5, 'frequency_penalty': 0.0, 'repeat_penalty': 1.0, 'repeat_last_n': 64, 'seed': 42, 'samplers': ['penalties', 'top_k', 'top_p', 'min_p', 'temperature']}
FIXED = {'evaluations/results/phase5x/exaone45-template-header-preflight/regression.json': '15ed600049b27c1b32400e95e4d42c78a7501d1352d821dab300a2369135930b', 'runtime/templates/exaone45-continue-free.provenance.json': 'f2aeccd96d255db04baed4c9532642419b97046f198d23d646d0a858120f616d', 'runtime/templates/exaone45-continue-free.jinja': '7de6c8ba3df6db54564c7a63385cc29572c0a616d5848961e969ecbb8c349851', 'evaluations/results/phase5x/exaone45-template-header-preflight/contract/public-proof-v3.json': 'fc7109fe4e9fbbe4a619ad16dc701cda01a4976ec8bd53d726aeb09f34f39408', 'evaluations/results/phase5x/exaone45-template-header-preflight/reports/exaone45-gguf-header-v2.json': 'fb5260c6e1e3356741f7728e4077f771763ea39affd77e8ac9772e417aa70c12', 'evaluations/hardening_v2_model_output_exposure_record.json': '25c080827a6d57aa6bc864495e537490dc7fa48b3ccf91df297a47b9815d447b', 'runtime/models/exaone45-33b-q4-k-m.json': '98aa8ad498c2a55db6359754c80793e33b880f60c191ec3fbe449097833c4bb8', 'runtime/models/exaone45-33b-q4-k-m.provenance.json': '74ed2ba7b8b4e21c83269d795d8983a487c75b3f2e25865fc25c9143ccab09f8', 'scripts/evaluate_requirements.py': '48734d5fda8069efe9bd927387cf6cf04fa4167f7a4d028f13509476a0511fef', 'scripts/gpu_preflight.py': '988d9493dd73d0e00b039f7d050f3ae52a4073833de23fc58eabc20ee58163fb', 'scripts/llama_server.py': '6a58ee1ea09636df182125da4a4a2711012e6c53f5f90c06548a63b9915369ed', 'scripts/model_guard.py': 'cc95f6cccf9ca5b749bea2fc8c82d2af9d56d55b94a6aee947379b3a2f4de528', 'scripts/native_model_bootstrap.py': '22e56159a6496aabf52dc6b567c800c54822c9def9713eb8a4ff0fac4183c2bf', 'scripts/verify_model_listeners.py': '2d7771d414a7faae4138ea555349d1f7f111d36498ad9815f64ac51910d758dd', 'src/neurobuild/application/requirement_generation.py': 'fcba16f6adc906923859f3bcf4ae2f680e76716863a759582167cd9326f03198', 'src/neurobuild/application/requirements.py': 'a940f3952c0c4133ab51732f6abf76516d8ff66617470545222b52adfa49fb4a', 'src/neurobuild/infrastructure/local_model.py': '48276a8f9cb7a2a818a9f12e7f86b2b53f525a37de61a1be70fe73648f07c151', 'evaluations/requirement_hardening_v1_exposed_regression.jsonl': '7e5b9a05932df7aafdbf683655b044b3e3b25cbffb4115d298e1490aecbc7a5b', 'prompts/requirement_generation_v2_v2.txt': '99d737124372836ba5f985fa6e5570afef693e769798844931f000fb21403cf6', 'schemas/requirement_generation_v2.schema.json': '6ca6fed3e8666244cd4bd779d33c0dd647490d5f641134307930008ea440436c', 'schemas/requirement_generation_v2_decision_branches.schema.json': '36d42b9fa3d24f4a1bc1d14381110e36e8d89103b696bc83113be006b64934e2', 'schemas/semantic_requirement.schema.json': 'dd131db08fe9087e795059445b075f22876e44b42481201cc0ea70608a708f94', 'tests/test_llama_server.py': 'e5cb6fb1e6471f7730ecdd54144d9c393ff7fb260c2131794344df8fd76fbcd6', 'var/research/exaone45_runtime_probe_v4.py': '7e2ff0e719304df4667baa988c416307405c61b5bca090f6609b8715eb024ee2', 'var/research/exaone45-runtime-v4-cpu-consumer-proof.json': '0cfc845948048df09224474aa9df42e7bbaa11d7e8961d700b904489c26f02e5', 'var/research/native-exaone45-contract/final-cpu-proof.json': '2a937a8adeca827f4724c9b65947291005aa34dc8ca4af823739fd09ca248209', 'var/research/native-exaone45-contract/public-vocab-proof.json': '66442010a8c4ee9f5f554bfea34273fd80659d50d42b9acdba6b2879400285d1', 'var/research/native-exaone45-contract/raw-vocab-proof.json': '2ce12c5e4d93f7d3baff40da67b1f2c3b5575e117dff081c84d03835e07e8c9d', 'var/research/native-exaone45-contract/vocab-context-raw-proof.json': 'f450e9f0bf3a206204474ed860bc6d191597cbe6cc31a7349efe894b5d3775bb', 'var/research/native-exaone45-contract/raw-reference-diagnostic.json': '9a379ccf7cab7c85c23582c45f77c6b4ec481a9bb1469009564dba0fe894bf2c', 'var/research/native-exaone45-contract/official-tokenizer-fixture.json': '49b40b3390cba92f3088c22606632348ba261e69ea0b385b74aa9126be8c46cb', 'var/research/exaone45-native-launch-epoch1.json': '1e872da88b6d00750447dd7c39213d7a4ce19b161fa64cb4c51cab1f7b8b7761', 'var/research/run_native_exaone45_epoch1_probe.py': '970985e1ba5935862915744403810b5c0698127eb3aec1af341af7cb1a4a353b', 'var/review-tools/check_native_exaone45_evidence_synthetic.py': '568265440ff639d86532dc60eebc1029a927ad3ac96c10e087047e262bc663b8'}

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


def validate_regression(regression):
    require(regression['kind']=='OPTIONAL_NATIVE_TEMPLATE_OVERRIDE_REGRESSION'
        and regression['status']=='PASS' and type(regression['tests']) is int and regression['tests']==408
        and type(regression['skipped']) is int and regression['skipped']==0
        and regression['headless'] is True and regression['actual_postgresql_and_ifcopenshell'] is True
        and regression['cuda_visible_devices']=='' and type(regression['model_gpu_calls']) is int
        and regression['model_gpu_calls']==0 and regression['log_sha256']==LOG_SHA,'REGRESSION_REQUIRED')
    for name,value in regression['source_sha256'].items():
        require(name in FIXED and value==FIXED[name],'REGRESSION_SOURCE_PIN_MISMATCH')
    require(set(regression['source_sha256'])=={
        'scripts/llama_server.py','tests/test_llama_server.py','src/neurobuild/infrastructure/local_model.py',
        'scripts/evaluate_requirements.py','scripts/model_guard.py','scripts/native_model_bootstrap.py'},
        'REGRESSION_SOURCE_SET_MISMATCH')

def validate_public_template(proof, provenance):
    require(proof['kind']=='EXAONE45_NATIVE_PUBLIC_TEMPLATE_CPU_PROOF' and proof['status']=='PASS'
        and proof['exit_code']==0 and proof['model_id']==MODEL and proof['model_revision']==REV
        and proof['source_pin']==SOURCE_PIN and proof['runtime_variant']==TEMPLATE_VARIANT
        and proof['protocol']=='llama_cpp_json_schema' and proof['sampling_profile']==PROFILE
        and proof['enable_thinking'] is False and proof['template_reference_cases']==18
        and proof['official_original_derived_reference_byte_equal'] is True
        and proof['official_embedded_template_sha256']==EMBEDDED_TEMPLATE_SHA
        and proof['candidate_template_sha256']==EFFECTIVE_TEMPLATE_SHA
        and proof['original_native_template_eligibility']=='FAIL_SYSTEM_POLICY_LOSS',
        'PUBLIC_TEMPLATE_PROOF_REQUIRED')
    n=proof['native']
    require(n['status']=='PASS' and n['public_template_reference_cases']==18
        and n['original_template_native_mismatches']==7 and n['original_native_system_present'] is False
        and n['original_native_prompt_bytes']==177 and n['native_request_prompt_bytes']==9176
        and n['derived_native_system_and_user_exact'] is True
        and n['derived_native_prompt_equals_official_reference'] is True
        and n['nested_continue_witness_reproduced'] is True
        and n['schema_cases_accepted']==10 and n['schema_cases_rejected']==20
        and n['native_final_content_exact_cases']==20 and n['native_protocol_rejection_cases']==4
        and n['native_tokenization']=='NOT_RUN' and n['model_context_created'] is False
        and proof['gguf_loaded'] is False and proof['model_calls']==proof['gpu_calls']==proof['http_calls']==0,
        'PUBLIC_TEMPLATE_SCOPE_MISMATCH')
    require(provenance['candidate_variant']==TEMPLATE_VARIANT and provenance['model_id']==MODEL
        and provenance['model_revision']==REV and provenance['native_source_commit']==SOURCE_PIN
        and provenance['official_embedded_template_sha256']==EMBEDDED_TEMPLATE_SHA
        and provenance['effective_template_sha256']==EFFECTIVE_TEMPLATE_SHA
        and provenance['effective_template_path']==EFFECTIVE_TEMPLATE and provenance['effective_template_bytes']==5829
        and provenance['public_proof_sha256']==PUBLIC_TEMPLATE_SHA
        and provenance['launcher_sha256']==FIXED['scripts/llama_server.py'], 'TEMPLATE_PROVENANCE_MISMATCH')

def validate_fixed():
    """Hash-only dataset preservation; may be called only after separate review."""
    for name,expected in FIXED.items():
        require(digest(name)==expected,'FIXED_INPUT_CHANGED')
    baseline=load(BASE)
    require(baseline['gate_targets']==GATES,'QUALITY_GATE_CHANGED')
    for name in ('schemas/semantic_requirement.schema.json','schemas/requirement_generation_v2.schema.json',V2,V2_EXPOSURE):
        require(digest(name)==baseline['sha256'][name],'BASELINE_CONTRACT_CHANGED')
    v2=load(V2);require(len(v2['sha256'])==9,'V2_FREEZE_CHANGED')
    for name,expected in v2['sha256'].items():require(digest(name)==expected,'V2_ARTIFACT_CHANGED')
    regression=load(REGRESSION);validate_regression(regression)
    require(digest(regression['log_path'])==LOG_SHA,'REGRESSION_LOG_CHANGED')
    require(re.search(r'Ran 408 tests in 21\.330s\s+OK\s*$',checked(regression['log_path']).read_text()),'REGRESSION_LOG_INVALID')
    archive=load(ARCHIVE+'/integrity.json')
    require(len(archive['source_paths'])==35 and len(archive['sha256'])==37,'ARCHIVE_INVENTORY_CHANGED')
    for name,expected in archive['sha256'].items():require(digest(ARCHIVE+'/'+name)==expected,'ARCHIVE_CHANGED')
    validate_public_template(load(PUBLIC_TEMPLATE),load(TEMPLATE_PROVENANCE))
    header=load(HEADER)
    require(header['kind']=='GGUF_HEADER_AUDIT' and header['status']=='PASS'
        and header['model_id']==MODEL and header['revision']==REV and header['file_sha256']==MODEL_SHA
        and header['full_file_sha256_verified'] is True
        and header['bindings']['embedded_template_sha256']==EMBEDDED_TEMPLATE_SHA,'ACTUAL_HEADER_REQUIRED')
    integrity_name=CPU_ARCHIVE+'/contract/integrity.json'
    require(digest(integrity_name)=='dae203190ca60be0752981163c79851baec31bbdd6129ffa8fb09ba67ad746e9',
            'CPU_ARCHIVE_INTEGRITY_CHANGED')
    integrity=load(integrity_name)
    require(len(integrity['files'])==21 and integrity['exact_original_copies']==19,
            'CPU_ARCHIVE_INVENTORY_CHANGED')
    for name,entry in integrity['files'].items():
        require(digest(CPU_ARCHIVE+'/contract/'+name)==entry['sha256'],'CPU_ARCHIVE_FILE_CHANGED')
        if 'original_path' in entry:
            require(digest(entry['original_path'])==entry['sha256'],'CPU_ARCHIVE_ORIGINAL_CHANGED')
    return regression,v2


def import_probe():
    require(digest(PROBE)==FIXED[PROBE],'PROBE_CHANGED')
    spec=importlib.util.spec_from_file_location('exaone_freeze_probe',ROOT/PROBE)
    probe=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    return probe


def validate_saved(probe, cpu_sha):
    require(cpu_sha==CPU_SHA and digest(CPU)==CPU_SHA,'CPU_PIN_MISMATCH')
    require(type(CONFIG_SHA) is str and re.fullmatch('[a-f0-9]{64}',CONFIG_SHA),'FINAL_CONFIG_PIN_PENDING')
    require(digest(CPU_ARCHIVED_PROOF)==cpu_sha,'CPU_ARCHIVE_LINK_MISMATCH')
    config,_=probe.load_config(ROOT/START/'launch_config.json',CONFIG_SHA)
    require(config.max_seconds==7200 and config.port==8003 and config.estimated_peak_mib==28672
            and config.peak_allowance_mib==0 and (config.batch_size,config.ubatch_size)==(64,64),
            'CONFIG_PLAN_CHANGED')
    provenance,_=probe.cpu_provenance(config,ROOT/CPU,cpu_sha)
    cpu=load(CPU)
    require(cpu['enable_thinking'] is False and cpu['gpu_or_http_calls']==0,'CPU_SCOPE_CHANGED')
    require(cpu['runtime_variant']==VARIANT and cpu['template_proof_variant']==TEMPLATE_VARIANT
            and cpu['application_input_output_nfc_repair'] is False,'CPU_VARIANT_MISMATCH')
    require(cpu['official_hf_equivalence']['status']=='FAIL'
            and cpu['official_hf_equivalence']['id_match_count']==18
            and cpu['raw_reference']['id_match_count']==cpu['raw_reference']['native_raw_roundtrip_count']==20
            and cpu['normalization_limitation']['global_unicode_roundtrip_guarantee'] is False,
            'ORIGINAL_FAILURE_OR_RAW_SCOPE_MISSING')
    startup,metadata=load(START+'startup.json'),load(START+'runtime_metadata.json')
    require(startup['status']=='PASS' and startup['kind']=='EXAONE45_NATIVE_STARTUP_HTTP_PROOF'
            and startup['http_get_calls']==3 and startup['model_inference_calls']==0
            and startup['raw_http_bodies_saved'] is False,'STARTUP_REQUIRED')
    require(startup['embedded_chat_template_sha256']==EMBEDDED_TEMPLATE_SHA
            and startup['embedded_chat_template_bytes']==5930
            and startup['effective_chat_template_sha256']==startup['chat_template_sha256']
            ==cpu['template_sha256']==metadata['chat_template_sha256']==EFFECTIVE_TEMPLATE_SHA
            and startup['effective_chat_template_bytes']==5829
            and startup['props_reported_template_sha256']=='b8bc1ef1b1fcd30cdd28fe7655bf79020aec666142107c01231b7b59f15cb1ef'
            and startup['props_reported_template_bytes']==5828,'TEMPLATE_REPRESENTATION_MISMATCH')
    require(metadata['startup_report_sha256']==digest(START+'startup.json')
            and metadata['listener_report_sha256']==digest(START+'listeners.json')
            and metadata['launch_config_sha256']==digest(START+'launch_config.json')==CONFIG_SHA
            and startup['resource_report_sha256']==digest(START+'resource_report.json'),
            'STARTUP_HASH_BINDING_FAILED')
    platform={key:metadata[key] for key in ('compiler','cmake','cuda','driver','gpu','gpu_uuid')}
    require(probe.make_metadata(config,platform,CONFIG_SHA,digest(START+'startup.json'),
                               digest(START+'listeners.json'))==metadata,'RUNTIME_METADATA_MISMATCH')
    public,resource=load(PUBLIC),load(RESOURCE)
    require(public['status']=='PASS' and public['kind']=='EXAONE45_NATIVE_PUBLIC_PRODUCTION_SMOKE'
            and public['http_calls_attempted']==1 and public['quality_gate_pass'] is False
            and public['generated_body_retained'] is False and public['sampling_profile']==PROFILE,
            'PUBLIC_SMOKE_REQUIRED')
    require(resource['status']=='PASS' and resource['kind']=='EXAONE45_NATIVE_PUBLIC_CONTEXT_RESOURCE_PROBE'
            and resource['http_post_calls']==1,'RESOURCE_SMOKE_REQUIRED')
    probe.validate_resource({key:resource[key] for key in probe.base.RESOURCE_FIELDS})
    for proof in (startup,public,resource):
        for key,value in provenance.items():
            require(proof[key]==value,'CPU_PROVENANCE_EDGE_FAILED')
    artifacts=probe.exaone_binding(config)
    guard=load(START+'resource_report.json');probe.validate_guard(config,guard,artifacts)
    require(guard['native_artifacts']['chat_template_override']=={
        'path':EFFECTIVE_TEMPLATE,'sha256':EFFECTIVE_TEMPLATE_SHA},'GUARD_OVERRIDE_MISMATCH')
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


def cpu_references(cpu):
    refs=list(cpu['proof_refs'].values())+[cpu['template_render_parity']['proof_ref'],
        cpu['official_hf_equivalence']['proof_ref'],cpu['raw_reference']['proof_ref'],
        cpu['raw_reference']['fixture_ref'],cpu['official_reference_fixture_ref']]
    out={}
    for ref in refs:
        require(set(ref)=={'path','sha256'} and type(ref['path']) is str
                and not Path(ref['path']).is_absolute() and '..' not in Path(ref['path']).parts,
                'CPU_REF_PATH_INVALID')
        require(ref['path'] not in out or out[ref['path']]==ref['sha256'],'CPU_REF_COLLISION')
        require(digest(ref['path'])==ref['sha256'],'CPU_REF_CHANGED');out[ref['path']]=ref['sha256']
    return out


def collect_files(config,cpu,regression,v2):
    refs=cpu_references(cpu)
    files=set(FIXED)|set(v2['sha256'])|set(regression['source_sha256'])|set(refs)|{
        CPU,CPU_ARCHIVED_PROOF,PUBLIC,RESOURCE,BASE,V2,V2_EXPOSURE,V2_OUTPUT_EXPOSURE,regression['log_path'],
        'docs/exaone45_33b_diagnostic_plan.md','docs/exaone45_33b_resource_plan.md','docs/DECISIONS.md',
        'var/research/freeze_native_exaone45_diagnostic.py','var/research/exaone45-freezer-draft-cpu-proof.json',
        'var/research/freeze_native_exaone45_diagnostic_v2.py',REPLAY,REPLAY_PROOF,SELFTEST,SELFTEST_SOURCE,
        'var/review-tools/check_native_exaone45_evidence_synthetic.py',
        'docs/reports/phase5x_exaone45_cpu_preflight_report.md',
        'docs/reports/phase5x_exaone45_runtime_preflight_report.md',
        str(config.source_report),str(config.build_report),str(config.model_header_report),str(config.chat_template_path)}
    for folder in (CPU_ARCHIVE,ARCHIVE,'evaluations/results/phase5x/exaone45-preparation',
                   'evaluations/results/phase5x/exaone45-runtime-preflight',START):
        root=ROOT/folder;require(root.is_dir() and not root.is_symlink(),'ARCHIVE_MISSING')
        members=[p for p in root.rglob('*') if p.is_file()]
        require(0<len(members)<=160,'ARCHIVE_COUNT_INVALID')
        files.update(str(p.relative_to(ROOT)) for p in members)
    return {str(checked(name).relative_to(ROOT)) for name in files}



def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cpu-proof-sha256',required=True)
    parser.add_argument('--dry-check',action='store_true',help='Validate actual evidence and own epoch, without publishing')
    args=parser.parse_args()
    require(not OUT.exists() and not OUT.is_symlink(),'FREEZE_ALREADY_EXISTS')
    require(os.environ.get('CUDA_VISIBLE_DEVICES')=='','CPU_ENV_REQUIRED')
    require(type(REPLAY_SHA) is str and type(REPLAY_PROOF_SHA) is str
            and re.fullmatch('[a-f0-9]{64}',REPLAY_SHA) and re.fullmatch('[a-f0-9]{64}',REPLAY_PROOF_SHA),
            'FINAL_REPLAY_PINS_PENDING')
    require(digest(REPLAY)==REPLAY_SHA and digest(REPLAY_PROOF)==REPLAY_PROOF_SHA,'REPLAY_PIN_MISMATCH')
    replay_proof=load(REPLAY_PROOF)
    require(replay_proof['kind']=='EXAONE45_REPLAY_SAVED_EVIDENCE_SYNTHETIC_PROOF'
            and replay_proof['status']=='PASS_NEW_METADATA_CONTROLS_ONLY'
            and replay_proof['helper_sha256']==REPLAY_SHA and replay_proof['core_functions_invoked']==0
            and len(replay_proof['tampering_rejected'])==18
            and digest('var/review-tools/check_native_exaone45_evidence_synthetic.py')==replay_proof['selfcheck_sha256'],
            'REPLAY_PREPARATION_INVALID')
    selftest=load(SELFTEST)
    require(selftest['status']=='PASS' and selftest['helper_sha256']==digest(str(Path(__file__).relative_to(ROOT)))
            and selftest['test_source_sha256']==digest(SELFTEST_SOURCE), 'FREEZER_SELFTEST_MISMATCH')
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
    frozen={'lifecycle':'FROZEN_BEFORE_NATIVE_EXAONE45_EXPOSED_DIAGNOSTIC',
        'frozen_at_utc':datetime.now(timezone.utc).isoformat(),
        'source_ancestor_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'candidate_variant':VARIANT,'template_proof_variant':TEMPLATE_VARIANT,'tokenizer_contract':provenance,
        'original_embedded_template_sha256':EMBEDDED_TEMPLATE_SHA,
        'effective_chat_template_sha256':EFFECTIVE_TEMPLATE_SHA,'chat_template_override':cpu['chat_template_override'],
        'official_hf_equivalence':cpu['official_hf_equivalence'],'raw_reference':cpu['raw_reference'],
        'context_tokenizer':cpu['context_tokenizer'],'application_input_output_nfc_repair':False,
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
        'runtime_metadata':START+'runtime_metadata.json','cpu_context_report':CPU,
        'cpu_context_archive':CPU_ARCHIVED_PROOF,'prior_v2_model_output_exposure_record':V2_OUTPUT_EXPOSURE,
        'public_smoke_report':PUBLIC,'resource_probe_report':RESOURCE,
        'runtime_epoch_snapshot':{'pid':startup['pid'],'start_ticks':startup['process_start_ticks'],
                                  'guard_started_at_utc':live['started_at_utc']},
        'guard_time_observation':time_observation,
        'decision_policy':'Raw final decision beforevalidation; errors/truncation/unknown retain denominators; no retry/repair/fallback.',
        'limits':['Exposed synthetic regression only; previousV2 outputs are also exposed. No unseen or human verification claim.',
                  'Model/quantization/template/sampling differ; no isolated causal attribution.',
                  'Official HF token-ID equivalence remains FAIL18/20; derived no-NFC reference20/20 is separate and not an allUnicode guarantee.',
                  'No application input/output repair; original quote/parser/gold/gates unchanged; RTX5090 unverified.'],
        'regression':regression,'sha256':hashes}
    require(digest(REPLAY)==REPLAY_SHA and digest(REPLAY_PROOF)==REPLAY_PROOF_SHA,'REPLAY_CHANGED_DURING_FREEZE')
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

if __name__=='__main__':
    main()
