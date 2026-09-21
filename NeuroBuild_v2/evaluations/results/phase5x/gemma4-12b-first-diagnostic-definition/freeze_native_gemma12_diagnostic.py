"""Prospective complete Gemma12 single-epoch freezer, unconditionally blocked.

No model/HTTP/native calls. Once root reviews actual pins, the final operation is
an exclusive freeze write after saved hashes and current own-epoch checks.
"""
from datetime import datetime,timezone
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
from contract import *
from evidence import validate_carry,provenance_projection,validate_regression,validate_single_epoch,exact

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
    require(all(v is not None for v in (CPU_SHA,CPU_ARCHIVED_PROOF,PROBE_SHA,CONFIG_SHA,
            CONTROLLER,CONTROLLER_SHA,SOURCE_COMMIT)), 'MISSING_FINAL_PINS')
    for path,sha in {**FIXED_SOURCE,**RUNTIME_DEFINITION_PINS}.items():require(digest(path)==sha,'FIXED_SOURCE_CHANGED')
    require(digest(PATHS['dataset'])==DATASET_SHA and digest(V2_DATASET)==V2_DATASET_SHA,'DATASET_HASH_CHANGED')
    require(digest(REGRESSION)==REGRESSION_SHA and digest(REGRESSION_LOG)==REGRESSION_LOG_SHA,'REGRESSION_CHANGED')
    require(re.search(r'Ran 418 tests in 21\.412s\s+OK\s*$',checked(REGRESSION_LOG).read_text()),'REGRESSION_LOG_INVALID')
    regression=load(REGRESSION);v2=load(V2_FREEZE)
    require(len(v2['sha256'])==9,'V2_FREEZE_COUNT')
    for path,sha in v2['sha256'].items():require(digest(path)==sha,'V2_BYTES_CHANGED')
    require(digest(V2_OUTPUT_EXPOSURE)==V2_OUTPUT_EXPOSURE_SHA,'PRIOR_V2_OUTPUT_EXPOSURE_CHANGED')
    return regression,v2


def import_probe():
    require(digest(PROBE)==PROBE_SHA and digest(CONTROLLER)==CONTROLLER_SHA,'RUNTIME_DEFINITION_CHANGED')
    spec=importlib.util.spec_from_file_location('gemma12_freeze_probe',ROOT/PROBE)
    probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
    return probe


def collect_files(config,cpu,regression,v2):
    paths=set(FIXED_SOURCE)|set(RUNTIME_DEFINITION_PINS)|set(regression['source_sha256'])|set(v2['sha256'])|set(RUNTIME_SHA)|set(DEFINITION_PATHS)
    paths.update((CPU,CPU_ARCHIVED_PROOF,HEADER,HEADER_ARCHIVE,TOKENIZER_COMPARISON,COMPARISON_ARCHIVE,
                  CONFIG,PROBE,CONTROLLER,REGRESSION,REGRESSION_LOG,V2_FREEZE,V2_EXPOSURE,V2_OUTPUT_EXPOSURE,
                  PATHS['dataset'],V2_DATASET,str(config.source_report),str(config.build_report),str(config.model_header_report)))
    paths.update(ref['path'] for ref in cpu['proof_refs'].values())
    # Explicit current definition/referenced receipts only, not an old archive tree.
    return {str(checked(path).relative_to(ROOT)) for path in paths}


def validate_saved(probe,regression,v2):
    require(digest(CPU)==digest(CPU_ARCHIVED_PROOF)==CPU_SHA,'CARRY_OR_ARCHIVE_CHANGED')
    config,_=probe.load_config(ROOT/START/'launch_config.json',CONFIG_SHA)
    provenance,token=probe.cpu_provenance(config,ROOT/CPU,CPU_SHA)
    artifacts=probe.gemma_binding(config)
    cpu=load(CPU);paths=collect_files(config,cpu,regression,v2)
    hashes={path:digest(path) for path in sorted(paths)}
    require(all(v is not None and hashes[path]==v for path,v in RUNTIME_SHA.items()),'ACTUAL_RUNTIME_RECEIPT_PINS')
    require(hashes[HEADER_ARCHIVE]==HEADER_SHA and hashes[COMPARISON_ARCHIVE]==TOKENIZER_COMPARISON_SHA,'HEADER_ARCHIVES_CHANGED')
    validate_carry(cpu,load,hashes);validate_regression(regression,hashes)
    exact(provenance,provenance_projection(cpu),'COLLECTOR_PROJECTION_CHANGED')
    require(token==236743,'RESOURCE_TOKEN_CHANGED')
    startup=load(START+'startup.json');metadata=load(START+'runtime_metadata.json')
    guard=load(START+'resource_report.json');listeners=load(START+'listeners.json')
    public=load(PUBLIC);resource=load(RESOURCE)
    probe.validate_guard(config,guard,artifacts)
    probe.validate_resource({key:resource[key] for key in probe.base.RESOURCE_FIELDS})
    epoch=validate_single_epoch(cpu,provenance,startup,metadata,load(START+'launch_config.json'),
                                guard,listeners,public,resource,hashes)
    platform={k:metadata[k] for k in ('compiler','cmake','cuda','driver','gpu','gpu_uuid')}
    exact(metadata,probe.make_metadata(config,platform,CONFIG_SHA,hashes[START+'startup.json'],
                                       hashes[START+'listeners.json']),'RUNTIME_METADATA_PROJECTION_CHANGED')
    return config,cpu,provenance,startup,artifacts,guard,epoch,hashes


def validate_current(probe,config,startup,artifacts,guard):
    live,_=probe.read_json(config.report_file)
    probe.validate_guard(config,live,artifacts)
    require(live['child_pid']==startup['pid'] and live['started_at_utc']==guard['started_at_utc'],'GUARD_EPOCH_CHANGED')
    probe.epoch(config,live['child_pid'],startup['process_start_ticks'])
    elapsed=live['elapsed_seconds']
    require(type(elapsed) in (int,float) and math.isfinite(elapsed)
            and guard['elapsed_seconds']<=elapsed<config.max_seconds,'GUARD_TIME_INVALID')
    return {'guard_max_seconds':config.max_seconds,'elapsed_seconds_at_freeze':elapsed,
            'remaining_seconds_at_freeze':config.max_seconds-elapsed,
            'first_request_requires_fresh_root_time_decision':True,
            'meaning':'Own guard lifetime observation, not a promised125-call completion duration.'}


def main():
    require_ready()  # FIRST action: no files/processes/publication until root final review.
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cpu-proof-sha256',required=True)
    args=parser.parse_args()
    require(args.cpu_proof_sha256==CPU_SHA,'EXPLICIT_CARRY_PIN_CHANGED')
    output=ROOT/OUT
    require(not output.exists() and not output.is_symlink(),'FREEZE_ALREADY_EXISTS')
    require(os.environ.get('CUDA_VISIBLE_DEVICES')=='','EMPTY_CUDA_REQUIRED')
    regression,v2=validate_fixed();probe=import_probe()
    config,cpu,provenance,startup,artifacts,guard,epoch,hashes=validate_saved(probe,regression,v2)
    source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    require(re.fullmatch('[a-f0-9]{40}',SOURCE_COMMIT) is not None
            and subprocess.run(['git','merge-base','--is-ancestor',SOURCE_COMMIT,source_commit],
                               cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0,
            'SOURCE_ANCESTOR_CHANGED')
    # Local client construction validates explicit protocol only; no HTTP complete/extract call.
    sys.path.insert(0,str(ROOT/'src'))
    from neurobuild.infrastructure.local_model import LocalRequirementClient
    client=LocalRequirementClient('http://127.0.0.1:8003',config.served_model_name,
        prompt_path=ROOT/PATHS['prompt'],schema_path=ROOT/PATHS['schema'],generation_contract='2.0',
        protocol='llama_cpp_json_schema',sampling_profile=PROFILE,max_tokens=768,timeout=120)
    exact(client.sampling_parameters,SAMPLING,'CLIENT_PROFILE_CHANGED')
    require(client.enable_thinking is False,'CLIENT_THINKING_CHANGED')
    for path,sha in hashes.items():require(digest(path)==sha,'INPUT_CHANGED_DURING_FREEZE')
    time_observation=validate_current(probe,config,startup,artifacts,guard)
    frozen=planned_contract();frozen.pop('preparation_status')
    frozen.update({'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'source_ancestor_commit':SOURCE_COMMIT,
                   'freeze_worktree_head_commit':source_commit,
                   'runtime_epoch_snapshot':epoch,'guard_time_observation':time_observation,
                   'tokenizer_contract':provenance,'normalization_limitation':cpu['normalization_limitation'],
                   'historical_cpu_measurements':cpu['historical_measurements'],'new_cpu_executions':cpu['new_executions'],
                   'regression':regression,'prior_v2_model_output_exposure_record':V2_OUTPUT_EXPOSURE,
                   'sha256':hashes,'decision_policy':'Raw final decision before validation; no retry/repair/fallback; unknown preserves all denominators.',
                   'limits':['Exposed synthetic regression; auto-generated gold is not human verified.',
                             'Historical Gemma31 CPU observations carried forward; no new public/vocab/context execution.',
                             'Suppression2 changes full native sampling; official literalU+2581 limitation retained.',
                             'Only the new12 single-epoch GPU evidence applies to runtime; RTX5090 remains unverified.']})
    require('torch' not in sys.modules,'TORCH_IMPORT_FORBIDDEN')
    payload=(json.dumps(frozen,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
    fd=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(payload);stream.flush();os.fsync(stream.fileno())
    parent=os.open(output.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(parent)
    finally:os.close(parent)
    print(json.dumps({'status':'FROZEN_NOT_EVALUATED','path':OUT,'sha256':hashlib.sha256(payload).hexdigest(),
                      'candidate_variant':VARIANT,'bound_files':len(hashes)}))


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print(json.dumps({'status':'BLOCKED_OR_FAILED','code':str(exc) if isinstance(exc,(ValueError,AssertionError)) else type(exc).__name__}),file=sys.stderr)
        raise SystemExit(1)
