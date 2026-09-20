"""DRAFT EXAONE exposed120x1+5 freezer: cannot create a freeze.

The reviewed Gemma bounded readers and lifecycle observer are preserved. Main and
unfinished evidence gates stop before any file/process read or publication.
Root must supply approved actual CPU/Unicode/runtime/replay evidence before a
separate final revision. No weight access, dataset parsing, model/HTTP/GPU call,
or previous125 replay. This file has no publication implementation yet.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat

ROOT = Path('/home/a202192020/NeuroBuild_v2')
OUT = ROOT/'evaluations/hardening_v1_exposed_native_exaone45_diagnostic_freeze.json'
PREPARATION_STATUS = 'DRAFT_ACTUAL_CPU_UNICODE_RUNTIME_REPLAY_BINDINGS_PENDING'
MODEL = 'LGAI-EXAONE/EXAONE-4.5-33B-GGUF'
REV = '0e969634ef24db05151b435970297a6dee634b7e'
MODEL_SHA = '5ba3839b67dcee5618ea7b2206cedc8f9e2ec90fbcec3c95a8cc8b33967f6baf'
SOURCE_PIN = 'f072b103714dfa1eee531f80b24512faf38e3dd2'
TEMPLATE_VARIANT = 'exaone45-gguf-continue-free-korean-v1'
VARIANT = 'exaone45-gguf-continue-free-raw-unicode-korean-v1'
PROFILE = 'exaone45_nonthinking_llama_cpp'
EMBEDDED_TEMPLATE_SHA = 'e4ece7acc79ba82121d4d57791fb7ecb796e39185087197377da5d2286bec0e5'
EFFECTIVE_TEMPLATE = 'runtime/templates/exaone45-continue-free.jinja'
EFFECTIVE_TEMPLATE_SHA = '7de6c8ba3df6db54564c7a63385cc29572c0a616d5848961e969ecbb8c349851'
TEMPLATE_PROVENANCE = 'runtime/templates/exaone45-continue-free.provenance.json'
ARCHIVE = 'evaluations/results/phase5x/exaone45-template-header-preflight'
PUBLIC_TEMPLATE = 'evaluations/results/phase5x/exaone45-template-header-preflight/contract/public-proof-v3.json'
PUBLIC_TEMPLATE_SHA = 'fc7109fe4e9fbbe4a619ad16dc701cda01a4976ec8bd53d726aeb09f34f39408'
HEADER = 'evaluations/results/phase5x/exaone45-template-header-preflight/reports/exaone45-gguf-header-v2.json'
HEADER_SHA = 'fb5260c6e1e3356741f7728e4077f771763ea39affd77e8ac9772e417aa70c12'
REGRESSION = 'evaluations/results/phase5x/exaone45-template-header-preflight/regression.json'
LOG_SHA = 'b2ae7a43b2fa3af31758528cf0ada58a63e689c6da6f53434f738bfe419ef20b'
DATASET = 'evaluations/requirement_hardening_v1_exposed_regression.jsonl'
PROMPT = 'prompts/requirement_generation_v2_v2.txt'
SCHEMA = 'schemas/requirement_generation_v2_decision_branches.schema.json'
BASE = 'evaluations/hardening_v1_exposed_generation2_32b_thinking_diagnostic_freeze.json'
V2 = 'evaluations/hardening_v2_dataset_freeze.json'
V2_EXPOSURE = 'evaluations/hardening_v2_input_exposure_addendum.json'
V2_OUTPUT_EXPOSURE = 'evaluations/hardening_v2_model_output_exposure_record.json'
REPLAY = 'var/review-tools/replay_native_exaone45_exposed.py'
BASE_HELPER_SHA = '2f37aa29bfe71e49e14cc4a5e569e725e83a2f1effeec955c57e7276b8052ff6'
SAMPLING = {'temperature': 0.6, 'top_p': 0.95, 'top_k': 20, 'min_p': 0.0, 'presence_penalty': 1.5, 'frequency_penalty': 0.0, 'repeat_penalty': 1.0, 'repeat_last_n': 64, 'seed': 42, 'samplers': ['penalties', 'top_k', 'top_p', 'min_p', 'temperature']}
GATES = {'schema_required': 120, 'schema_denominator': 120, 'semantic_required_at_least': 114, 'semantic_denominator': 120, 'critical_model_ready_fp_required': 0, 'critical_model_ready_fp_denominator': 58, 'unsafe_accepted_ready_total_required': 0, 'unsafe_accepted_ready_total_denominator': 120}
FIXED = {'evaluations/results/phase5x/exaone45-template-header-preflight/regression.json': '15ed600049b27c1b32400e95e4d42c78a7501d1352d821dab300a2369135930b', 'runtime/templates/exaone45-continue-free.provenance.json': 'f2aeccd96d255db04baed4c9532642419b97046f198d23d646d0a858120f616d', 'runtime/templates/exaone45-continue-free.jinja': '7de6c8ba3df6db54564c7a63385cc29572c0a616d5848961e969ecbb8c349851', 'evaluations/results/phase5x/exaone45-template-header-preflight/contract/public-proof-v3.json': 'fc7109fe4e9fbbe4a619ad16dc701cda01a4976ec8bd53d726aeb09f34f39408', 'evaluations/results/phase5x/exaone45-template-header-preflight/reports/exaone45-gguf-header-v2.json': 'fb5260c6e1e3356741f7728e4077f771763ea39affd77e8ac9772e417aa70c12', 'evaluations/hardening_v2_model_output_exposure_record.json': '25c080827a6d57aa6bc864495e537490dc7fa48b3ccf91df297a47b9815d447b', 'runtime/models/exaone45-33b-q4-k-m.json': '98aa8ad498c2a55db6359754c80793e33b880f60c191ec3fbe449097833c4bb8', 'runtime/models/exaone45-33b-q4-k-m.provenance.json': '74ed2ba7b8b4e21c83269d795d8983a487c75b3f2e25865fc25c9143ccab09f8', 'scripts/evaluate_requirements.py': '48734d5fda8069efe9bd927387cf6cf04fa4167f7a4d028f13509476a0511fef', 'scripts/gpu_preflight.py': '988d9493dd73d0e00b039f7d050f3ae52a4073833de23fc58eabc20ee58163fb', 'scripts/llama_server.py': '6a58ee1ea09636df182125da4a4a2711012e6c53f5f90c06548a63b9915369ed', 'scripts/model_guard.py': 'cc95f6cccf9ca5b749bea2fc8c82d2af9d56d55b94a6aee947379b3a2f4de528', 'scripts/native_model_bootstrap.py': '22e56159a6496aabf52dc6b567c800c54822c9def9713eb8a4ff0fac4183c2bf', 'scripts/verify_model_listeners.py': '2d7771d414a7faae4138ea555349d1f7f111d36498ad9815f64ac51910d758dd', 'src/neurobuild/application/requirement_generation.py': 'fcba16f6adc906923859f3bcf4ae2f680e76716863a759582167cd9326f03198', 'src/neurobuild/application/requirements.py': 'a940f3952c0c4133ab51732f6abf76516d8ff66617470545222b52adfa49fb4a', 'src/neurobuild/infrastructure/local_model.py': '48276a8f9cb7a2a818a9f12e7f86b2b53f525a37de61a1be70fe73648f07c151', 'docs/exaone45_33b_diagnostic_plan.md': 'bc3b5758ec558c0c7a87b4d13767f5600b18548cdcdd6ddf1f5431932df6d983', 'docs/exaone45_33b_resource_plan.md': 'd799b4df66cc88aa7393bd7810dbafd0646c7bd259623098784bc85ce752a890', 'evaluations/requirement_hardening_v1_exposed_regression.jsonl': '7e5b9a05932df7aafdbf683655b044b3e3b25cbffb4115d298e1490aecbc7a5b', 'prompts/requirement_generation_v2_v2.txt': '99d737124372836ba5f985fa6e5570afef693e769798844931f000fb21403cf6', 'schemas/requirement_generation_v2.schema.json': '6ca6fed3e8666244cd4bd779d33c0dd647490d5f641134307930008ea440436c', 'schemas/requirement_generation_v2_decision_branches.schema.json': '36d42b9fa3d24f4a1bc1d14381110e36e8d89103b696bc83113be006b64934e2', 'schemas/semantic_requirement.schema.json': 'dd131db08fe9087e795059445b075f22876e44b42481201cc0ea70608a708f94', 'tests/test_llama_server.py': 'e5cb6fb1e6471f7730ecdd54144d9c393ff7fb260c2131794344df8fd76fbcd6'}
# Exact actual paths/digests are intentionally not invented.
PENDING_BINDINGS = ('cpu_context_report','cpu_context_archive','cpu_proof_sha256',
    'tokenizer_contract','normalization_limitation','runtime_probe_sha256',
    'launch_config_sha256','runtime_metadata','public_smoke_report',
    'resource_probe_report','replay_helper_sha256','replay_selfcheck_sha256')

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

def planned_contract():
    """Pure metadata for future reviewed freeze; not evidence of execution."""
    return {'lifecycle':'DRAFT_NOT_FROZEN','candidate_variant':VARIANT,
        'gold_status':'AUTO-GENERATED / NOT HUMAN VERIFIED','dataset':DATASET,'split':'development',
        'cases':120,'ready_gold':62,'nonready_gold':58,'warmups_per_run':5,'trials_per_case':1,
        'expected_http_calls':125,'pipeline':'single','generation_contract':'2.0',
        'model_id':MODEL,'model_revision':REV,'tokenizer_revision':REV,
        'prompt':PROMPT,'generation_schema':SCHEMA,'canonical_schema':'schemas/semantic_requirement.schema.json',
        'protocol':'llama_cpp_json_schema','sampling_profile':PROFILE,
        'sampling_request_parameters':json.loads(json.dumps(SAMPLING)),
        'enable_thinking':False,'reasoning_parser':'deepseek','max_tokens':768,'timeout_seconds':120,
        'max_model_len':4096,'concurrency':1,'maximum_calls_per_case':1,'gate_targets':dict(GATES),
        'quantization':'Q4_K_M','batch_size':64,'ubatch_size':64,'estimated_peak_mib':28672,
        'peak_allowance_mib':0,'original_embedded_template_sha256':EMBEDDED_TEMPLATE_SHA,
        'chat_template_override':{'path':EFFECTIVE_TEMPLATE,'sha256':EFFECTIVE_TEMPLATE_SHA,'bytes':5829,
            'original_embedded_template_sha256':EMBEDDED_TEMPLATE_SHA,
            'transform':'continue-free-system-message-branch-v1'},
        'template_proof_variant':TEMPLATE_VARIANT,
        'official_hf_id_equivalence':'FAIL_18_OF_20',
        'official_hf_parity_failure_sha256':'66442010a8c4ee9f5f554bfea34273fd80659d50d42b9acdba6b2879400285d1',
        'raw_unicode_contract_status':'PENDING_RAW_REFERENCE20_AND_CONTEXT_PROOF',
        'application_input_output_nfc_repair':False,'global_unicode_roundtrip_guarantee':False,
        'template_public_proof':PUBLIC_TEMPLATE,'template_public_proof_sha256':PUBLIC_TEMPLATE_SHA,
        'prior_v2_model_output_exposure_record':V2_OUTPUT_EXPOSURE,
        'decision_policy':'Raw final decision before validation; errors/truncation/unknown retain denominators; no retry/repair/fallback.',
        'raw_decision_observed_required':120,'automatic_repetitions':False,
        'quality_or_runtime_eligibility':False}


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
    return regression,v2


def validate_saved(*args, **kwargs):
    """Not implemented until actual CPU/Unicode/runtime evidence is provided.

    Final revision must bind original official-ID18/20 FAIL plus separate NFC-disabled reference20/20
    and native original-string roundtrip20/20; actual vocab observations and approved Unicode
    limitation independently of the metadata public18 proof; source/profile,
    ctx4096/output768 and exposed120 + V2-length80 aggregation; embedded/effective/
    props template representation; exact startup5 JSON and public/resource epoch;
    complete runtime metadata; latest replay selfcheck; and all archived hashes.
    A template or header PASS must never substitute for any pending edge.
    """
    require(False,'EXAONE_ACTUAL_CPU_UNICODE_RUNTIME_REPLAY_BINDINGS_PENDING')


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

def collect_files(*args, **kwargs):
    # Final archive inventories and final replay pins must be supplied by root.
    # Preserve original V2 nine hashes and exposure record; never parse its body.
    require(False,'EXAONE_FINAL_ARCHIVE_INVENTORY_PENDING')


def main():
    # Deliberately first: no args, imports, fixed artifact reads, live process
    # probes or output creation can happen while the actual evidence is pending.
    require(False,'EXAONE_ACTUAL_CPU_UNICODE_RUNTIME_REPLAY_BINDINGS_PENDING')


if __name__=='__main__':
    main()
