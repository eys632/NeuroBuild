"""GLM first exposed120x1+5 freezer DRAFT, publication is blocked.

No HTTP, model, GPU, weight hashing, dataset parsing or old evaluation replay.
Actual CPU/runtime proof schemas and hashes must be finalized and independently
reviewed before this draft can publish anything. No command-line bypass exists.
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
PREPARATION_STATUS = 'DRAFT_BLOCKED_ACTUAL_CPU_RUNTIME_AND_FINAL_EVIDENCE_REVIEW'
CPU_SHA = '54ab0062c5d22112ed3349e0021391a4dd17f6d5f8698ac8a02cc096b08a1847'
CONFIG_SHA = None
PROBE_SHA = None
REGRESSION = 'evaluations/results/phase5x/glm47-flash-preparation/regression/regression.json'
CPU = 'var/research/native-glm47-contract/final-cpu-proof.json'
CPU_ARCHIVED_PROOF = None  # Final aggregate archive location must be supplied by its owner.
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
REPLAY = 'var/research/replay_native_glm47_exposed.py'
REPLAY_SHA = None
PREPARATION_RECEIPT = 'var/research/glm47-diagnostic-draft-static-proof.json'
FINAL_EVIDENCE_MANIFEST = None
LOG_SHA = 'c342132012c9d6192164b09ddf3c806b82faaaaec3cc8be99379f2cea2e0463d'
FIXED = {'scripts/gpu_preflight.py': '988d9493dd73d0e00b039f7d050f3ae52a4073833de23fc58eabc20ee58163fb', 'scripts/llama_server.py': '6a58ee1ea09636df182125da4a4a2711012e6c53f5f90c06548a63b9915369ed', 'scripts/model_guard.py': 'cc95f6cccf9ca5b749bea2fc8c82d2af9d56d55b94a6aee947379b3a2f4de528', 'scripts/native_model_bootstrap.py': '22e56159a6496aabf52dc6b567c800c54822c9def9713eb8a4ff0fac4183c2bf', 'scripts/verify_model_listeners.py': '2d7771d414a7faae4138ea555349d1f7f111d36498ad9815f64ac51910d758dd', 'src/neurobuild/application/requirement_generation.py': 'fcba16f6adc906923859f3bcf4ae2f680e76716863a759582167cd9326f03198', 'src/neurobuild/application/requirements.py': 'a940f3952c0c4133ab51732f6abf76516d8ff66617470545222b52adfa49fb4a', 'evaluations/requirement_hardening_v1_exposed_regression.jsonl': '7e5b9a05932df7aafdbf683655b044b3e3b25cbffb4115d298e1490aecbc7a5b', 'prompts/requirement_generation_v2_v2.txt': '99d737124372836ba5f985fa6e5570afef693e769798844931f000fb21403cf6', 'schemas/requirement_generation_v2.schema.json': '6ca6fed3e8666244cd4bd779d33c0dd647490d5f641134307930008ea440436c', 'schemas/requirement_generation_v2_decision_branches.schema.json': '36d42b9fa3d24f4a1bc1d14381110e36e8d89103b696bc83113be006b64934e2', 'schemas/semantic_requirement.schema.json': 'dd131db08fe9087e795059445b075f22876e44b42481201cc0ea70608a708f94', 'scripts/evaluate_requirements.py': '4fc1335e3372518c3534267613cbc4ad0d0cb0772a149ce286ce703f2b886048', 'src/neurobuild/infrastructure/local_model.py': '7dfc3f673ba6ab4e4970055c4cbee66ae440da2d42070af959a5fe415a9ab780', 'tests/test_local_model.py': 'd76731e5ee613ef664f76d078caf5b775c65b265c63913eaf527f40010e41510', 'tests/test_native_requirement_evaluation.py': 'f52d284fd62d78e8e41e8b32b883d6865f8978346257b2b0c8f3ed703fde4a04', 'runtime/models/glm47-flash-q4-k.json': '8f2c13b9fad51c6d65588a2b2b70ed966168259eaa42e2f997c59dd97be1814c', 'evaluations/results/phase5x/glm47-flash-preparation/regression/regression.json': '293bfc5b4f94e728af5eeb021a3aae2230376a74dae6e631d0c70a1c4e513fac'}
COPY_SOURCE_SHA = '268a3437cfe09494e6b39252c7c1a837ec3c099eba1e30b4c812f95b7aac6d82'

def require_ready():
    raise ValueError('GLM_FINAL_CPU_RUNTIME_FREEZE_EVIDENCE_PENDING')

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
    # Final archive/CPU/header/public-vocab/context exact refs are not invented.
    require(FINAL_EVIDENCE_MANIFEST is not None,'FINAL_EVIDENCE_MANIFEST_PENDING')
    return regression,v2


def import_probe():
    require_ready()
    require(digest(PROBE)==PROBE_SHA,'PROBE_CHANGED')
    spec=importlib.util.spec_from_file_location('glm_freeze_probe',ROOT/PROBE)
    probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
    return probe


def validate_saved(probe,cpu_sha):
    """Finalize against actual GLM collector APIs and complete seven saved proofs."""
    require_ready()


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
    require_ready()
    # Exact stable archives/config/collector/CPU refs added only after review;
    # no loose recursive future-file pickup and no candidate weight bytes.
    require(FINAL_EVIDENCE_MANIFEST is not None,'FINAL_EVIDENCE_MANIFEST_PENDING')
    files=set(FIXED)|set(v2['sha256'])|set(cpu_references(cpu))|set(FINAL_EVIDENCE_MANIFEST)|{
        CPU,CPU_ARCHIVED_PROOF,PUBLIC,RESOURCE,BASE,V2,V2_EXPOSURE,V2_OUTPUT_EXPOSURE,
        regression['log_path'],str(Path(__file__).relative_to(ROOT)),REPLAY,PREPARATION_RECEIPT}
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
        'normalization_limitation':{'official_normalizer':None,'global_unicode_roundtrip_guarantee':False},
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
