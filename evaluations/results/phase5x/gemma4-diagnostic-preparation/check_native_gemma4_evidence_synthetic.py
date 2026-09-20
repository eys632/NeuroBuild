"""Only new Gemma saved-evidence metadata controls; no row/results/data replay."""
import ast
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[2]
path=ROOT/'var/review-tools/replay_native_gemma4_exposed.py'
spec=importlib.util.spec_from_file_location('gemma_evidence_replay',path)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)


def fixture():
    start='evaluations/results/phase5x/synthetic-gemma/'
    cpu_path='var/research/SYNTHETIC-gemma-cpu.json'
    archive='evaluations/results/phase5x/synthetic-gemma/cpu.json'
    public_path=start+'public.json';resource_path=start+'resource.json'
    values={};hashes={}
    def add(name,value,hashed=None):
        values[name]=value;hashes[name]=hashed or sha256(name.encode()).hexdigest()
    source={r.PATHS[k]:sha256(k.encode()).hexdigest() for k in ('client','parser','generation_adapter','prompt','schema')}
    hashes.update(source)
    refs={name:{'path':start+name+'.json','sha256':sha256(name.encode()).hexdigest()}
          for name in ('public_contract','vocab_context','tokenizer_fixture')}
    for ref in refs.values():hashes[ref['path']]=ref['sha256']
    parity={'status':'PASS','case_count':20,'id_match_count':20,'native_original_roundtrip_count':20}
    norm={'official_hf_literal_u2581_raw_roundtrip':False,'global_unicode_roundtrip_guarantee':False,
          'input_output_repair':False,'reference':'tokenizer_fixture.normalization_witness'}
    context={'kind':'GEMMA4_NATIVE_CONTRACT_CPU_PROOF','status':'PASS','model_id':r.MODEL,
        'revision':r.REVISION,'gguf_sha256':r.GGUF_SHA,'header_sha256':r.HEADER_SHA,'source_pin':r.SOURCE_PIN,
        'template_sha256':r.TEMPLATE_SHA,'tokenizer_json_sha256':r.TOKENIZER_SHA,
        'protocol':'llama_cpp_json_schema','sampling_profile':r.PROFILE,'enable_thinking':False,
        'application_input_output_nfc_repair':False,'model_inference_calls':0,'gpu_or_http_calls':0,
        'max_output_tokens':768,'max_context_tokens':4096,'official_tokenizer_parity':parity,
        'normalization_limitation':norm,'source_sha256':source,'proof_refs':refs,
        'splits':{name:{'input_count':count,'dataset_sha256':sha,'min_input_tokens':100,
             'max_input_tokens':200,'max_input_plus_output':968} for name,count,sha in (
             ('exposed120',120,'7e5b9a05932df7aafdbf683655b044b3e3b25cbffb4115d298e1490aecbc7a5b'),
             ('v2_length80',80,'7416f05613b1490358672f3926770dbd8653e676577eeee6ba65f863b27cec40'))}}
    add(cpu_path,context,r.CPU_SHA);add(archive,context,r.CPU_SHA)
    provenance={'model_id':r.MODEL,'model_revision':r.REVISION,'cpu_proof_sha256':r.CPU_SHA,
        'cpu_proof_kind':context['kind'],'chat_template_sha256':r.TEMPLATE_SHA,'tokenizer_json_sha256':r.TOKENIZER_SHA,
        'tokenizer_contract':'official_qat_metadata_native_public_parity_20_of_20',
        'official_tokenizer_parity':parity,'application_input_output_nfc_repair':False,
        'cpu_proof_refs':refs,'cpu_source_sha256':source,'cpu_checks_rerun':False}
    launch={'batch_size':64,'ubatch_size':64,'max_seconds':7200,'served_model_name':'synthetic',
        'binary_sha256':'a'*64,'source_report_sha256':'b'*64,'build_report_sha256':'c'*64,
        'source_commit':r.SOURCE_PIN,'model_sha256':r.GGUF_SHA,'model_revision':r.REVISION,
        'model_header_report_sha256':r.HEADER_SHA}
    add(start+'launch_config.json',launch)
    epoch={'pid':123,'start_ticks':456,'guard_started_at_utc':'2026-09-20T00:00:00+00:00'}
    fields={'pid':123,'process_start_ticks':456,'guard_started_at_utc':epoch['guard_started_at_utc'],
            'launch_config_sha256':hashes[start+'launch_config.json']}
    guard={'state':'RUNNING','native_identity_verified':True,'physical_gpu_index':3,'required_cuda_visible_devices':'3',
           'batch_size':64,'ubatch_size':64,'max_num_seqs':1,'native_output_policy':'DISCARD_STDOUT_STDERR',
           'native_core_dump_limit_bytes':0,'minimum_observed_free_mib':9000,'required_free_floor_mib':7275,
           'observed_baseline_relative_peak_mib':27373,'aggregate_increment_limit_mib':28672,
           'max_model_len':4096,'enable_reasoning':False,'reasoning_parser':'deepseek',
           'served_model_name':'synthetic','child_pid':123,'started_at_utc':epoch['guard_started_at_utc'],
           'elapsed_seconds':100,'native_artifacts':{k:launch[k] for k in (
             'binary_sha256','source_report_sha256','build_report_sha256','source_commit',
             'model_sha256','model_revision','model_header_report_sha256')}}
    add(start+'resource_report.json',guard)
    listeners={'verdict':'PASS','all_loopback':True,'snapshot_complete':True,'uid':os.getuid(),
               'pid':123,'process_start_ticks':456}
    add(start+'listeners.json',listeners)
    startup={**deepcopy(provenance),**fields,'kind':'GEMMA4_NATIVE_STARTUP_HTTP_PROOF','status':'PASS',
             'http_get_calls':3,'model_inference_calls':0,'raw_http_bodies_saved':False,
             'embedded_chat_template_sha256':r.TEMPLATE_SHA,'embedded_chat_template_bytes':18683,
             'props_reported_template_sha256':'6a1015c47ccfcfa67c3b772385bccee357a4d37c3cda37bd202e9047f391ab82',
             'props_reported_template_bytes':18682,
             'resource_report_sha256':hashes[start+'resource_report.json']}
    add(start+'startup.json',startup)
    runtime={'startup_report_sha256':hashes[start+'startup.json'],'listener_report_sha256':hashes[start+'listeners.json'],
             'launch_config_sha256':hashes[start+'launch_config.json'],'gguf_header_sha256':r.HEADER_SHA}
    public={**deepcopy(provenance),**fields,'status':'PASS','kind':'GEMMA4_NATIVE_PUBLIC_PRODUCTION_SMOKE',
        'sampling_profile':r.PROFILE,'http_calls_attempted':1,'quality_gate_pass':False,'generated_body_retained':False}
    resource={**deepcopy(provenance),**fields,'kind':'GEMMA4_NATIVE_PUBLIC_CONTEXT_RESOURCE_PROBE','status':'PASS',
        'http_post_calls':1,'tokens_evaluated':3328,'timings/prompt_n':3328,'tokens_predicted':768,
        'timings/predicted_n':768,'tokens_cached':4095,'stop':True,'truncated':True,'stop_type':'limit',
        'quality_evaluation':False,'grammar_enabled':False,'generated_body_retained':False}
    add(public_path,public);add(resource_path,resource)
    weights={'model_id':r.MODEL,'revision':r.REVISION,'files':[{'name':'x.gguf','sha256':r.GGUF_SHA,'bytes':r.GGUF_BYTES}]}
    add(r.PATHS['weight_manifest'],weights)
    receipt={'kind':'GEMMA_NATIVE_PROFILE_REGRESSION','status':'PASS','tests':395,'skipped':0,'headless':True,
         'actual_postgresql_ifcopenshell':True,'model_gpu_calls':0,'prior_125_diagnostic_repeated':False,
         'log_path':'var/SYNTHETIC-regression.log','log_sha256':'724865dd1d4dfae92c1e7a5860895317eebc675a39bbec894af3d002f65728d0',
         'source_sha256':source}
    add('evaluations/results/phase5x/gemma4-profile-preparation/regression.json',receipt)
    hashes[receipt['log_path']]=receipt['log_sha256'];hashes[r.V2_OUTPUT_EXPOSURE]=r.V2_OUTPUT_EXPOSURE_SHA
    freeze={'runtime_metadata':start+'runtime_metadata.json','public_smoke_report':public_path,
        'resource_probe_report':resource_path,'cpu_context_report':cpu_path,'cpu_context_archive':archive,
        'normalization_limitation':deepcopy(norm),'tokenizer_contract':deepcopy(provenance),
        'runtime_epoch_snapshot':epoch,'prior_v2_model_output_exposure_record':r.V2_OUTPUT_EXPOSURE,
        'regression':deepcopy(receipt),'guard_time_observation':{'guard_max_seconds':7200,
          'elapsed_seconds_at_freeze':200,'remaining_seconds_at_freeze':7000,
          'first_request_requires_fresh_root_time_decision':True}}
    return freeze,runtime,launch,values,hashes


def invoke(bundle):
    f,t,l,values,hashes=bundle
    r.validate_evidence(f,t,l,lambda name:deepcopy(values[name]),hashes)


bundle=fixture();invoke(bundle)
f,t,l,docs,hashes=bundle;start=f['runtime_metadata'].rsplit('/',1)[0]+'/'
cpu=f['cpu_context_report'];public=f['public_smoke_report'];resource=f['resource_probe_report']
tampering=[
 ('cpu_pin',lambda f,t,l,d,h:h.update({cpu:'0'*64})),
 ('archive_pin',lambda f,t,l,d,h:h.update({f['cpu_context_archive']:'0'*64})),
 ('cpu_wrong_profile',lambda f,t,l,d,h:d[cpu].update(sampling_profile='qwen38_nonthinking_llama_cpp')),
 ('cpu_calls_present',lambda f,t,l,d,h:d[cpu].update(model_inference_calls=1)),
 ('cpu_token_overflow',lambda f,t,l,d,h:d[cpu]['splits']['exposed120'].update(max_input_tokens=4000,max_input_plus_output=4768)),
 ('cpu_source_changed',lambda f,t,l,d,h:h.update({r.PATHS['client']:'0'*64})),
 ('erase_unicode_limit',lambda f,t,l,d,h:d[cpu]['normalization_limitation'].update(global_unicode_roundtrip_guarantee=True)),
 ('weaker_parity',lambda f,t,l,d,h:d[cpu]['official_tokenizer_parity'].update(id_match_count=19)),
 ('reference_unbound',lambda f,t,l,d,h:h.update({d[cpu]['proof_refs']['public_contract']['path']:'0'*64})),
 ('startup_extra_calls',lambda f,t,l,d,h:d[start+'startup.json'].update(http_get_calls=4)),
 ('props_raw_hash_confusion',lambda f,t,l,d,h:d[start+'startup.json'].update(props_reported_template_sha256=r.TEMPLATE_SHA)),
 ('props_arbitrary_trimming',lambda f,t,l,d,h:d[start+'startup.json'].update(props_reported_template_bytes=18681)),
 ('startup_wrong_epoch',lambda f,t,l,d,h:d[start+'startup.json'].update(pid=321)),
 ('startup_wrong_guard_time',lambda f,t,l,d,h:d[start+'startup.json'].update(guard_started_at_utc='OTHER_EPOCH')),
 ('listener_not_loopback',lambda f,t,l,d,h:d[start+'listeners.json'].update(all_loopback=False)),
 ('public_old_model_proof',lambda f,t,l,d,h:d[public].update(kind='NATIVE_PUBLIC_PRODUCTION_SMOKE')),
 ('public_extra_calls',lambda f,t,l,d,h:d[public].update(http_calls_attempted=2)),
 ('public_other_epoch',lambda f,t,l,d,h:d[public].update(process_start_ticks=999)),
 ('resource_short_output',lambda f,t,l,d,h:d[resource].update(tokens_predicted=767)),
 ('resource_retains_body',lambda f,t,l,d,h:d[resource].update(generated_body_retained=True)),
 ('guard_exceeded_peak',lambda f,t,l,d,h:d[start+'resource_report.json'].update(observed_baseline_relative_peak_mib=28673)),
 ('guard_wrong_model',lambda f,t,l,d,h:d[start+'resource_report.json']['native_artifacts'].update(model_revision='x')),
 ('wrong_header',lambda f,t,l,d,h:t.update(gguf_header_sha256='0'*64)),
 ('wrong_lifetime',lambda f,t,l,d,h:l.update(max_seconds=3600)),
 ('no_firstcall_time_recheck',lambda f,t,l,d,h:f['guard_time_observation'].update(first_request_requires_fresh_root_time_decision=False)),
 ('pretend_more_time',lambda f,t,l,d,h:f['guard_time_observation'].update(remaining_seconds_at_freeze=7100)),
 ('hide_v2_outputs',lambda f,t,l,d,h:h.update({r.V2_OUTPUT_EXPOSURE:'0'*64})),
 ('regression_not395',lambda f,t,l,d,h:d['evaluations/results/phase5x/gemma4-profile-preparation/regression.json'].update(tests=386)),
]
rejected=[]
for label,mutate in tampering:
    b=deepcopy(bundle);mutate(*b)
    try:invoke(b)
    except (AssertionError,KeyError):rejected.append(label)
    else:raise AssertionError('missed_'+label)
prior=ast.parse((ROOT/'var/review-tools/replay_native_qwen38_exposed.py').read_text());current=ast.parse(path.read_text())
for name in ('replay_row','replay_groups','load_snapshot'):
    a=next(x for x in prior.body if getattr(x,'name',None)==name)
    b=next(x for x in current.body if getattr(x,'name',None)==name)
    assert ast.dump(a)==ast.dump(b),name
assert r.PREPARATION_STATUS=='IMPLEMENTED_AWAITING_COMPLETED_GEMMA_RUN'
proof={'kind':'GEMMA4_REPLAY_SAVED_EVIDENCE_SYNTHETIC_PROOF','status':'PASS_SYNTHETIC_METADATA_ONLY',
 'helper_sha256':sha256(path.read_bytes()).hexdigest(),'selfcheck_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
 'tampering_rejected':rejected,'core_functions_ast_exact':3,'core_rows_or_metrics_replayed_this_check':0,
 'prior_core_proof':'var/research/gemma4-replay-core-selfcheck-f164b2a6cbcc46c2a4f51955bb5c6c82.json',
 'prior_core_proof_sha256':'16fc25e7d46761d236a6dc70beaaca83afb3dbeb9b6f8c13440bb40b0d9c7309',
 'real_results_read':False,'datasets_parsed':0,'model_calls':0,'gpu_calls':0,'http_calls':0,
 'runtime_process_queries':0,'meaning':'Final evidence checks exercised with newly constructed fake metadata, no actual run or adoption claim.'}
out=ROOT/'var/research'/('gemma4-replay-evidence-selfcheck-'+uuid4().hex+'.json')
with out.open('x') as f:json.dump(proof,f,indent=2);f.write('\n')
print(json.dumps({'status':proof['status'],'tampering_rejected':len(rejected),
 'helper_sha256':proof['helper_sha256'],'proof':str(out.relative_to(ROOT)),
 'proof_sha256':sha256(out.read_bytes()).hexdigest()}))
