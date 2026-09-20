"""New candidate metadata controls only. No replay/core/native/process/HTTP calls."""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import runpy
R=Path.cwd()
F='var/research/freeze_native_glm47_diagnostic_v2.py'
P='var/research/replay_native_glm47_exposed_v2.py'
old='var/review-tools/replay_native_exaone45_exposed_v4.py'
def digest(p):return hashlib.sha256((R/p).read_bytes()).hexdigest()
def functions(p):return {n.name:n for n in ast.parse((R/p).read_bytes()).body if isinstance(n,ast.FunctionDef)}
core=['load_snapshot','replay_row','replay_groups']
for name in core:assert ast.dump(functions(P)[name],include_attributes=False)==ast.dump(functions(old)[name],include_attributes=False)
for p in (F,P):compile((R/p).read_bytes(),p,'exec')
ns=runpy.run_path(str(R/P),run_name='new_metadata_controls_only')
cpu=json.loads((R/ns['CPU']).read_bytes())
start=ns['START']
names=[ns['CPU'],ns['CPU_ARCHIVED_PROOF'],ns['PUBLIC'],ns['RESOURCE'],ns['REGRESSION'],ns['PATHS']['weight_manifest']]
names += [start+n for n in ('startup.json','runtime_metadata.json','launch_config.json','resource_report.json','listeners.json')]
bundle={p:json.loads((R/p).read_bytes()) for p in names}
hashes={p:digest(p) for p in names}
hashes.update(cpu['source_sha256']);hashes.update({v['path']:v['sha256'] for v in cpu['proof_refs'].values()})
for p in [ns['PROBE'],ns['CONTROLLER'],ns['RUNTIME_CPU_PROOF'],'scripts/llama_server.py',ns['V2_OUTPUT_EXPOSURE']]:hashes[p]=digest(p)
reg=bundle[ns['REGRESSION']];hashes.update(reg['source_sha256']);hashes[reg['log_path']]=reg['log_sha256']
startup=bundle[start+'startup.json'];guard=bundle[start+'resource_report.json']
runtime=bundle[start+'runtime_metadata.json'];launch=bundle[start+'launch_config.json']
provenance=ns['validate_cpu_metadata'](cpu,hashes)
freeze={'runtime_metadata':start+'runtime_metadata.json','public_smoke_report':ns['PUBLIC'],'resource_probe_report':ns['RESOURCE'],
    'cpu_context_report':ns['CPU'],'cpu_context_archive':ns['CPU_ARCHIVED_PROOF'],'tokenizer_contract':provenance,
    'official_tokenizer_parity':cpu['official_tokenizer_parity'],'normalization_limitation':cpu['normalization_limitation'],
    'runtime_epoch_snapshot':{'pid':startup['pid'],'start_ticks':startup['process_start_ticks'],'guard_started_at_utc':guard['started_at_utc']},
    'guard_time_observation':{'guard_max_seconds':7200,'elapsed_seconds_at_freeze':guard['elapsed_seconds'],
        'remaining_seconds_at_freeze':7200-guard['elapsed_seconds'],'first_request_requires_fresh_root_time_decision':True},
    'prior_v2_model_output_exposure_record':ns['V2_OUTPUT_EXPOSURE'],'regression':reg}
ns['validate_evidence'](freeze,runtime,launch,bundle.__getitem__,hashes)
mutations=[]
for label,change in [
 ('wrong_variant',lambda c:c.update(candidate_variant='wrong')),
 ('official_parity19',lambda c:c['official_tokenizer_parity'].update(id_match_count=19)),
 ('cpu_source_changed',lambda c:c['source_sha256'].update({next(iter(c['source_sha256'])):'0'*64})),
 ('public_vocab_missing',lambda c:c['proof_refs'].pop('public_vocab')),
 ('input_repair',lambda c:c.update(application_input_output_nfc_repair=True)),
 ('context_overflow',lambda c:c['splits']['exposed120'].update(max_input_tokens=3400,max_input_plus_output=4168)),
 ('wrong_resource_token',lambda c:c['resource_probe_token'].update(token_id=582)),
 ('sampler_order',lambda c:c['sampling_request_parameters'].update(samplers=['top_k','temperature']))]:
 c=deepcopy(cpu);change(c)
 try:ns['validate_cpu_metadata'](c,hashes)
 except (AssertionError,KeyError):mutations.append(label)
 else:raise AssertionError('accepted_mutation:'+label)
for label,path,key,value in [
 ('wrong_epoch',ns['PUBLIC'],'pid',-1),
 ('wrong_props_template',start+'startup.json','props_reported_template_sha256','0'*64),
 ('missing_internal_warmup_scope',start+'startup.json','native_startup_warmup_enabled',False),
 ('resource_wrong_count',ns['RESOURCE'],'tokens_predicted',767)]:
 b=deepcopy(bundle);b[path][key]=value
 try:ns['validate_evidence'](freeze,runtime,launch,b.__getitem__,hashes)
 except (AssertionError,KeyError):mutations.append(label)
 else:raise AssertionError('accepted_mutation:'+label)
report={'kind':'GLM47_DIAGNOSTIC_METADATA_CONTROLS','status':'PASS_NEW_METADATA_CONTROLS_ONLY',
    'helper_sha256':digest(F),'replay_sha256':digest(P),'selfcheck_sha256':digest('var/research/check_glm47_diagnostic_v2.py'),
    'core_ast_exact':core,'core_functions_invoked':0,'saved_new_runtime_metadata_validation':'PASS',
    'tampering_rejected':mutations,'dataset_result_body_reads':0,'public20_reruns':0,'test_suite_reruns':0,
    'native_gpu_http_model_calls':0,'freeze_created':False,'scope':'Passed maps and saved small CPU/runtime metadata only; no live guard, no result replay, no candidate quality claim.'}
path=R/'var/research/glm47-diagnostic-v2-metadata-proof.json'
with path.open('x') as s:json.dump(report,s,indent=2);s.write('\n')
print(json.dumps({'status':report['status'],'controls':len(mutations),'proof_sha256':digest(str(path.relative_to(R))),'helper_sha256':report['helper_sha256'],'replay_sha256':report['replay_sha256']}))
