"""Prepare one Gemma exposed120x1+5 freeze after real completed prerequisites.

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
OUT = ROOT / 'evaluations/hardening_v1_exposed_native_gemma4_diagnostic_freeze.json'
CPU = 'var/research/native-gemma4-contract/final-cpu-proof.json'
CPU_ARCHIVE = 'evaluations/results/phase5x/gemma4-cpu-preflight'
CPU_ARCHIVED_PROOF = CPU_ARCHIVE + '/contract/final-cpu-proof.json'
START = 'evaluations/results/phase5x/gemma4-native-startup-epoch1/'
PUBLIC = 'evaluations/results/phase5x/gemma4-native-public-smoke-epoch1/report.json'
RESOURCE = 'evaluations/results/phase5x/gemma4-native-resource-epoch1/report.json'
CONFIG_SHA = '14cb239f83d6997d01490bf3889aa1605d53a06aa8a9b2d63491dc25430b40dc'
PROBE = 'var/research/gemma4_runtime_probe_v3.py'
REGRESSION = 'evaluations/results/phase5x/gemma4-profile-preparation/regression.json'
LOG_SHA = '724865dd1d4dfae92c1e7a5860895317eebc675a39bbec894af3d002f65728d0'
MODEL = 'google/gemma-4-31B-it-qat-q4_0-gguf'
REV = '59dde24573e7e61570dba08b18a2e1fe246955ed'
VARIANT = 'gemma4-31b-qat-q4_0-official-native-v1'
PROFILE = 'gemma4_nonthinking_llama_cpp'
DATASET = 'evaluations/requirement_hardening_v1_exposed_regression.jsonl'
PROMPT = 'prompts/requirement_generation_v2_v2.txt'
SCHEMA = 'schemas/requirement_generation_v2_decision_branches.schema.json'
BASE = 'evaluations/hardening_v1_exposed_generation2_32b_thinking_diagnostic_freeze.json'
V2 = 'evaluations/hardening_v2_dataset_freeze.json'
V2_EXPOSURE = 'evaluations/hardening_v2_input_exposure_addendum.json'
V2_OUTPUT_EXPOSURE = 'evaluations/hardening_v2_model_output_exposure_record.json'
GATES = {'schema_required':120,'schema_denominator':120,'semantic_required_at_least':114,
         'semantic_denominator':120,'critical_model_ready_fp_required':0,
         'critical_model_ready_fp_denominator':58,'unsafe_accepted_ready_total_required':0,
         'unsafe_accepted_ready_total_denominator':120}
SAMPLING = {'temperature':1.0,'top_p':.95,'top_k':64,'min_p':0.0,
            'presence_penalty':0.0,'frequency_penalty':0.0,'repeat_penalty':1.0,
            'repeat_last_n':0,'seed':42,'samplers':['temperature','top_k','top_p','min_p']}
FIXED = {'evaluations/hardening_v2_model_output_exposure_record.json': '25c080827a6d57aa6bc864495e537490dc7fa48b3ccf91df297a47b9815d447b',
 'var/research/gemma4_runtime_probe_v3.py': '14fdc596eea3a15a2a343c961e9080b05d876eac34d34b6f893a2c2cedd97a37',
 'var/research/run_native_gemma4_epoch1_probe_v2.py': '352efcf270e0ab894c35ad54b5bb2461257f8ffecd5af4b771ed3ba768f383b0',
 'evaluations/requirement_hardening_v1_exposed_regression.jsonl': '7e5b9a05932df7aafdbf683655b044b3e3b25cbffb4115d298e1490aecbc7a5b',
 'evaluations/results/phase5x/gemma4-profile-preparation/regression.json': 'dd685fcccd979e73500d9d25f09fff5dfea67c7dca8de26009d9637c7b8ce7fd',
 'prompts/requirement_generation_v2_v2.txt': '99d737124372836ba5f985fa6e5570afef693e769798844931f000fb21403cf6',
 'runtime/models/gemma4-31b-qat-q4-0.json': '16d471fc5bb8ae266015d73b0a648e2b576dab6e6e453de8c28fdc0f1a8a6e3c',
 'runtime/models/gemma4-31b-qat-q4-0.provenance.json': 'dedec756118f0aae8eb7908e0ffaa77746c60cfafcd8c40cab80d8bd2dd95bbc',
 'schemas/requirement_generation_v2.schema.json': '6ca6fed3e8666244cd4bd779d33c0dd647490d5f641134307930008ea440436c',
 'schemas/requirement_generation_v2_decision_branches.schema.json': '36d42b9fa3d24f4a1bc1d14381110e36e8d89103b696bc83113be006b64934e2',
 'schemas/semantic_requirement.schema.json': 'dd131db08fe9087e795059445b075f22876e44b42481201cc0ea70608a708f94',
 'scripts/evaluate_requirements.py': '4f9da8c7cd430625fbe0226ae8201d7bcb934834cef435740822b2df948c69e7',
 'scripts/gpu_preflight.py': '988d9493dd73d0e00b039f7d050f3ae52a4073833de23fc58eabc20ee58163fb',
 'scripts/llama_server.py': '163e6a27ec6675e17da5dfcd7c6beaa6f70b22f6db6cead0cf52d42e6bff9077',
 'scripts/model_guard.py': 'cc95f6cccf9ca5b749bea2fc8c82d2af9d56d55b94a6aee947379b3a2f4de528',
 'scripts/native_model_bootstrap.py': '22e56159a6496aabf52dc6b567c800c54822c9def9713eb8a4ff0fac4183c2bf',
 'scripts/verify_model_listeners.py': '2d7771d414a7faae4138ea555349d1f7f111d36498ad9815f64ac51910d758dd',
 'src/neurobuild/application/requirement_generation.py': 'fcba16f6adc906923859f3bcf4ae2f680e76716863a759582167cd9326f03198',
 'src/neurobuild/application/requirements.py': 'a940f3952c0c4133ab51732f6abf76516d8ff66617470545222b52adfa49fb4a',
 'src/neurobuild/infrastructure/local_model.py': '68c086f08bf2c3f5d6464f689baa8e628c8c33664397db06868c26cb6dd0d763',
 'var/research/gemma4-native-launch-epoch1.json': '14cb239f83d6997d01490bf3889aa1605d53a06aa8a9b2d63491dc25430b40dc',
 'var/research/gemma4_runtime_probe.py': 'e2b7fdc53b37e51af2d358bafdf30e051c377a3e2b3e1a2207736079df6695e0',
 'var/research/inspect_gemma4_gguf_v2.py': 'eec3e66ef68e6d09a1c8f9c85247d149ffe4b66d57383ca29468d9af2c384ef5',
 'var/research/native_runtime_probe.py': 'ac100df7949b2b14a517c4568fa66369bd98c599b39507ef19f873490a0f9f63',
 'var/research/run_native_gemma4_epoch1_probe.py': '8afbbea59dae9fbc13cc4bd0d13e06eafa03e8685697bd7b88d552052db9ab71'}


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


def validate_fixed():
    for name,expected in FIXED.items():
        require(digest(name)==expected,'FIXED_INPUT_CHANGED')
    base=load(BASE)
    for name in ('schemas/semantic_requirement.schema.json','schemas/requirement_generation_v2.schema.json',V2,V2_EXPOSURE):
        require(digest(name)==base['sha256'][name],'BASELINE_CONTRACT_CHANGED')
    require(base['gate_targets']==GATES,'QUALITY_GATE_CHANGED')
    v2=load(V2)
    require(len(v2['sha256'])==9,'V2_FREEZE_CHANGED')
    for name,expected in v2['sha256'].items():
        require(digest(name)==expected,'V2_ARTIFACT_CHANGED')
    regression=load(REGRESSION)
    require(regression['kind']=='GEMMA_NATIVE_PROFILE_REGRESSION' and regression['status']=='PASS'
            and type(regression['tests']) is int and regression['tests']==395
            and type(regression['skipped']) is int and regression['skipped']==0
            and regression['headless'] is True and regression['actual_postgresql_ifcopenshell'] is True
            and regression['model_gpu_calls']==0 and regression['prior_125_diagnostic_repeated'] is False,
            'REGRESSION_REQUIRED')
    require(regression['log_sha256']==LOG_SHA and digest(regression['log_path'])==LOG_SHA,
            'REGRESSION_LOG_CHANGED')
    require(re.search(r'Ran 395 tests in 19\.339s\s+OK\s*$',checked(regression['log_path']).read_text()),
            'REGRESSION_LOG_INVALID')
    for name,expected in regression['source_sha256'].items():
        require(digest(name)==expected,'REGRESSION_SOURCE_CHANGED')
    return regression,v2


def import_probe():
    require(digest(PROBE)==FIXED[PROBE],'PROBE_CHANGED')
    spec=importlib.util.spec_from_file_location('gemma_freeze_probe',ROOT/PROBE)
    probe=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    return probe


def validate_saved(probe, cpu_sha):
    require(re.fullmatch('[a-f0-9]{64}',cpu_sha) is not None and digest(CPU)==cpu_sha,'CPU_PIN_MISMATCH')
    require(digest(CPU_ARCHIVED_PROOF)==cpu_sha,'CPU_ARCHIVE_LINK_MISMATCH')
    config,_=probe.load_config(ROOT/START/'launch_config.json',CONFIG_SHA)
    require(config.max_seconds==7200 and config.port==8003 and config.estimated_peak_mib==28672
            and config.peak_allowance_mib==0 and (config.batch_size,config.ubatch_size)==(64,64),
            'CONFIG_PLAN_CHANGED')
    provenance,_=probe.cpu_provenance(config,ROOT/CPU,cpu_sha)
    cpu=load(CPU)
    require(cpu['enable_thinking'] is False and cpu['gpu_or_http_calls']==0,'CPU_SCOPE_CHANGED')
    norm=cpu['normalization_limitation']
    require(norm['official_hf_literal_u2581_raw_roundtrip'] is False
            and norm['global_unicode_roundtrip_guarantee'] is False and norm['input_output_repair'] is False,
            'NORMALIZATION_LIMITATION_MISSING')
    startup,metadata=load(START+'startup.json'),load(START+'runtime_metadata.json')
    require(startup['status']=='PASS' and startup['kind']=='GEMMA4_NATIVE_STARTUP_HTTP_PROOF'
            and startup['http_get_calls']==3 and startup['model_inference_calls']==0
            and startup['raw_http_bodies_saved'] is False,'STARTUP_REQUIRED')
    require(startup['embedded_chat_template_sha256']==startup['chat_template_sha256']
            ==cpu['template_sha256']=='ae53464bf3be25802b3a5b37def7fd89667067d7577049b3b2d74c4d8de4c6d4'
            and startup['embedded_chat_template_bytes']==18683
            and startup['props_reported_template_sha256']=='6a1015c47ccfcfa67c3b772385bccee357a4d37c3cda37bd202e9047f391ab82'
            and startup['props_reported_template_bytes']==18682,'TEMPLATE_REPRESENTATION_MISMATCH')
    require(metadata['startup_report_sha256']==digest(START+'startup.json')
            and metadata['listener_report_sha256']==digest(START+'listeners.json')
            and metadata['launch_config_sha256']==digest(START+'launch_config.json')==CONFIG_SHA
            and startup['resource_report_sha256']==digest(START+'resource_report.json'),
            'STARTUP_HASH_BINDING_FAILED')
    platform={key:metadata[key] for key in ('compiler','cmake','cuda','driver','gpu','gpu_uuid')}
    require(probe.make_metadata(config,platform,CONFIG_SHA,digest(START+'startup.json'),
                               digest(START+'listeners.json'))==metadata,'RUNTIME_METADATA_MISMATCH')
    public,resource=load(PUBLIC),load(RESOURCE)
    require(public['status']=='PASS' and public['kind']=='GEMMA4_NATIVE_PUBLIC_PRODUCTION_SMOKE'
            and public['http_calls_attempted']==1 and public['quality_gate_pass'] is False
            and public['generated_body_retained'] is False and public['sampling_profile']==PROFILE,
            'PUBLIC_SMOKE_REQUIRED')
    require(resource['status']=='PASS' and resource['kind']=='GEMMA4_NATIVE_PUBLIC_CONTEXT_RESOURCE_PROBE'
            and resource['http_post_calls']==1,'RESOURCE_SMOKE_REQUIRED')
    probe.validate_resource({key:resource[key] for key in probe.base.RESOURCE_FIELDS})
    for proof in (startup,public,resource):
        for key,value in provenance.items():
            require(proof[key]==value,'CPU_PROVENANCE_EDGE_FAILED')
    artifacts=probe.gemma_binding(config)
    guard=load(START+'resource_report.json');probe.validate_guard(config,guard,artifacts)
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


def collect_files(config,cpu,regression,v2):
    files=set(FIXED)|set(v2['sha256'])|set(regression['source_sha256'])|{
        CPU,CPU_ARCHIVED_PROOF,PUBLIC,RESOURCE,BASE,V2,V2_EXPOSURE,V2_OUTPUT_EXPOSURE,regression['log_path'],
        'docs/gemma4_31b_diagnostic_plan.md','docs/gemma4_31b_resource_plan.md',
        'var/research/freeze_native_gemma4_diagnostic.py',
        'var/review-tools/replay_native_gemma4_exposed.py',
        str(config.source_report),str(config.build_report),str(config.model_header_report)}
    for ref in cpu['proof_refs'].values():
        require(digest(ref['path'])==ref['sha256'],'CPU_REF_CHANGED')
        files.add(ref['path'])
    # Only this candidate's small archived sources/reports. No old build trees.
    for folder in (CPU_ARCHIVE,'evaluations/results/phase5x/gemma4-profile-preparation',START):
        root=ROOT/folder
        require(root.is_dir() and not root.is_symlink(),'ARCHIVE_MISSING')
        members=[p for p in root.rglob('*') if p.is_file()]
        require(0<len(members)<=160,'ARCHIVE_COUNT_INVALID')
        files.update(str(p.relative_to(ROOT)) for p in members)
    normalized=set()
    for name in files:
        path=checked(name)
        normalized.add(str(path.relative_to(ROOT)))
    return normalized


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cpu-proof-sha256',required=True)
    args=parser.parse_args()
    require(not OUT.exists() and not OUT.is_symlink(),'FREEZE_ALREADY_EXISTS')
    require(os.environ.get('CUDA_VISIBLE_DEVICES')=='','CPU_ENV_REQUIRED')
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
    frozen={'lifecycle':'FROZEN_BEFORE_NATIVE_GEMMA4_EXPOSED_DIAGNOSTIC',
        'frozen_at_utc':datetime.now(timezone.utc).isoformat(),
        'source_ancestor_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'candidate_variant':VARIANT,'tokenizer_contract':provenance,
        'normalization_limitation':cpu['normalization_limitation'],
        'gold_status':'AUTO-GENERATED / NOT HUMAN VERIFIED','dataset':DATASET,'split':'development',
        'cases':120,'ready_gold':62,'nonready_gold':58,'warmups_per_run':5,'trials_per_case':1,
        'expected_http_calls':125,'pipeline':'single','generation_contract':'2.0',
        'model_id':MODEL,'model_revision':REV,'tokenizer_revision':REV,'served_model':config.served_model_name,
        'prompt':PROMPT,'generation_schema':SCHEMA,'canonical_schema':'schemas/semantic_requirement.schema.json',
        'protocol':'llama_cpp_json_schema','sampling_profile':PROFILE,'sampling_request_parameters':SAMPLING,
        'enable_thinking':False,'reasoning_parser':'deepseek','max_tokens':768,'timeout_seconds':120,
        'max_model_len':4096,'concurrency':1,'maximum_calls_per_case':1,'gate_targets':GATES,
        'runtime_metadata':START+'runtime_metadata.json','cpu_context_report':CPU,
        'cpu_context_archive':CPU_ARCHIVED_PROOF,'prior_v2_model_output_exposure_record':V2_OUTPUT_EXPOSURE,
        'public_smoke_report':PUBLIC,'resource_probe_report':RESOURCE,
        'runtime_epoch_snapshot':{'pid':startup['pid'],'start_ticks':startup['process_start_ticks'],
                                  'guard_started_at_utc':live['started_at_utc']},
        'guard_time_observation':time_observation,
        'decision_policy':'Raw final decision beforevalidation; errors/truncation/unknown retain denominators; no retry/repair/fallback.',
        'limits':['Exposed synthetic regression only; previousV2 outputs are also exposed. No unseen or human verification claim.',
                  'Model/quantization/template/sampling differ; no isolated causal attribution.',
                  'Public tokenizer20 probes do not prove allUnicode. Official literalU+2581 normalization witness retained.',
                  'No application input/output repair; original quote/parser/gold/gates unchanged; RTX5090 unverified.'],
        'regression':regression,'sha256':hashes}
    require('torch' not in sys.modules,'TORCH_IMPORT_FORBIDDEN')
    with OUT.open('x') as stream:
        json.dump(frozen,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
        stream.flush();os.fsync(stream.fileno())
    print(json.dumps({'status':'FROZEN_NOT_EVALUATED','path':str(OUT.relative_to(ROOT)),
                      'sha256':digest(OUT),'candidate_variant':VARIANT,'bound_files':len(hashes)}))

if __name__=='__main__':
    main()
