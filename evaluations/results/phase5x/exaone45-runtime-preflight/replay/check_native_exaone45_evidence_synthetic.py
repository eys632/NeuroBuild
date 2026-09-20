"""New EXAONE evidence wiring only; saved CPU metadata + synthetic runtime, zero row replay."""
import ast
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
path=ROOT/'var/review-tools/replay_native_exaone45_exposed_v3.py'
spec=importlib.util.spec_from_file_location('exaone_saved_evidence_tested',path)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
assert os.environ.get('CUDA_VISIBLE_DEVICES')==''
def actual(name):return json.loads((ROOT/name).read_bytes())
def digest(name):return sha256((ROOT/name).read_bytes()).hexdigest()
def fixture():
    values={};hashes={}
    def add(name,value,h=None):values[name]=value;hashes[name]=h or sha256(name.encode()).hexdigest()
    cpu=r.PROOF_DIR+'final-cpu-proof.json';context=actual(cpu)
    add(cpu,context,r.CPU_SHA);add(r.CPU_ARCHIVE,deepcopy(context),r.CPU_SHA)
    hashes.update(context['source_sha256'])
    refs=list(context['proof_refs'].values())+[context['official_hf_equivalence']['proof_ref'],
        context['raw_reference']['proof_ref'],context['official_reference_fixture_ref']]
    for ref in refs:add(ref['path'],actual(ref['path']),ref['sha256'])
    # Independent fixture uses the actual runtime consumer's earlier saved receipt.
    receipt=actual('var/research/exaone45-runtime-v4-cpu-consumer-proof.json')
    assert digest('var/research/exaone45-runtime-v4-cpu-consumer-proof.json')=='0cfc845948048df09224474aa9df42e7bbaa11d7e8961d700b904489c26f02e5'
    provenance=receipt['consumed_provenance']
    assert r.expected_cpu_provenance(context)==provenance
    launch=actual('var/research/exaone45-native-launch-epoch1.json')
    add(r.START+'launch_config.json',launch,digest('var/research/exaone45-native-launch-epoch1.json'))
    epoch={'pid':123,'start_ticks':456,'guard_started_at_utc':'2026-09-20T00:00:00+00:00'}
    fields={'pid':123,'process_start_ticks':456,'guard_started_at_utc':epoch['guard_started_at_utc'],
            'launch_config_sha256':hashes[r.START+'launch_config.json']}
    guard={'state':'RUNNING','native_identity_verified':True,'physical_gpu_index':3,'required_cuda_visible_devices':'3',
        'batch_size':64,'ubatch_size':64,'max_num_seqs':1,'native_output_policy':'DISCARD_STDOUT_STDERR',
        'native_core_dump_limit_bytes':0,'minimum_observed_free_mib':9000,'required_free_floor_mib':7275,
        'observed_baseline_relative_peak_mib':27373,'aggregate_increment_limit_mib':28672,
        'max_model_len':4096,'enable_reasoning':False,'reasoning_parser':'deepseek','served_model_name':launch['served_model_name'],
        'child_pid':123,'started_at_utc':epoch['guard_started_at_utc'],'elapsed_seconds':100,
        'native_artifacts':{k:launch[k] for k in ('binary_sha256','source_report_sha256','build_report_sha256',
            'source_commit','model_sha256','model_revision','model_header_report_sha256')}}
    guard['native_artifacts']['chat_template_override']={'path':r.OVERRIDE_PATH,'sha256':r.TEMPLATE_SHA}
    add(r.START+'resource_report.json',guard)
    listeners={'verdict':'PASS','all_loopback':True,'snapshot_complete':True,'uid':os.getuid(),'pid':123,'process_start_ticks':456}
    add(r.START+'listeners.json',listeners)
    startup={**deepcopy(provenance),**fields,'kind':'EXAONE45_NATIVE_STARTUP_HTTP_PROOF','status':'PASS',
        'http_get_calls':3,'model_inference_calls':0,'raw_http_bodies_saved':False,
        'embedded_chat_template_sha256':r.ORIGINAL_TEMPLATE_SHA,'embedded_chat_template_bytes':5930,
        'effective_chat_template_sha256':r.TEMPLATE_SHA,'effective_chat_template_bytes':5829,
        'props_reported_template_sha256':'b8bc1ef1b1fcd30cdd28fe7655bf79020aec666142107c01231b7b59f15cb1ef',
        'props_reported_template_bytes':5828,'resource_report_sha256':hashes[r.START+'resource_report.json']}
    add(r.START+'startup.json',startup)
    runtime={'startup_report_sha256':hashes[r.START+'startup.json'],'listener_report_sha256':hashes[r.START+'listeners.json'],
        'launch_config_sha256':hashes[r.START+'launch_config.json'],'gguf_header_sha256':r.HEADER_SHA}
    public={**deepcopy(provenance),**fields,'kind':'EXAONE45_NATIVE_PUBLIC_PRODUCTION_SMOKE','status':'PASS',
        'sampling_profile':r.PROFILE,'http_calls_attempted':1,'quality_gate_pass':False,'generated_body_retained':False}
    resource={**deepcopy(provenance),**fields,'kind':'EXAONE45_NATIVE_PUBLIC_CONTEXT_RESOURCE_PROBE','status':'PASS',
        'http_post_calls':1,'tokens_evaluated':3328,'timings/prompt_n':3328,'tokens_predicted':768,
        'timings/predicted_n':768,'tokens_cached':4095,'stop':True,'truncated':True,'stop_type':'limit',
        'quality_evaluation':False,'grammar_enabled':False,'generated_body_retained':False}
    add(r.PUBLIC,public);add(r.RESOURCE,resource)
    add(r.PATHS['weight_manifest'],actual(r.PATHS['weight_manifest']),r.MANIFEST_SHA)
    reg=actual(r.REGRESSION);add(r.REGRESSION,reg,digest(r.REGRESSION));hashes.update(reg['source_sha256'])
    hashes[reg['log_path']]=reg['log_sha256'];hashes[r.V2_OUTPUT_EXPOSURE]=r.V2_OUTPUT_EXPOSURE_SHA
    hashes[r.RUNTIME_HELPER]=r.RUNTIME_HELPER_SHA
    freeze={'runtime_metadata':r.START+'runtime_metadata.json','public_smoke_report':r.PUBLIC,'resource_probe_report':r.RESOURCE,
        'cpu_context_report':cpu,'cpu_context_archive':r.CPU_ARCHIVE,'normalization_limitation':deepcopy(context['normalization_limitation']),
        'official_hf_equivalence':deepcopy(context['official_hf_equivalence']),'raw_reference':deepcopy(context['raw_reference']),
        'chat_template_override':deepcopy(context['chat_template_override']),'context_tokenizer':context['context_tokenizer'],
        'tokenizer_contract':deepcopy(provenance),'runtime_epoch_snapshot':epoch,
        'prior_v2_model_output_exposure_record':r.V2_OUTPUT_EXPOSURE,'regression':deepcopy(reg),
        'guard_time_observation':{'guard_max_seconds':7200,'elapsed_seconds_at_freeze':200,
            'remaining_seconds_at_freeze':7000,'first_request_requires_fresh_root_time_decision':True}}
    return freeze,runtime,launch,values,hashes

def invoke(bundle):
    f,t,l,d,h=bundle;r.validate_evidence(f,t,l,lambda name:deepcopy(d[name]),h)
bundle=fixture();invoke(bundle);cpu=bundle[0]['cpu_context_report']
changes=[
 ('official_failure_erased',lambda f,t,l,d,h:f['official_hf_equivalence'].update(status='PASS')),
 ('raw_reference_as_official',lambda f,t,l,d,h:f['raw_reference'].update(official_hf_equivalence='PASS')),
 ('old_source_helper',lambda f,t,l,d,h:h.update({r.RUNTIME_HELPER:'0'*64})),
 ('wrong_cpu_pin',lambda f,t,l,d,h:h.update({cpu:'0'*64})),
 ('derived_public19',lambda f,t,l,d,h:d[r.PROOF_DIR+'raw-vocab-proof.json']['native'].update(tokenizer_id_match_count=19)),
 ('lost_policy',lambda f,t,l,d,h:d[r.PROOF_DIR+'vocab-context-raw-proof.json']['native_checks'][0].update(all_context_system_user_bytes_exact=False)),
 ('no_override_guard',lambda f,t,l,d,h:d[r.START+'resource_report.json']['native_artifacts'].pop('chat_template_override')),
 ('wrong_effective_template',lambda f,t,l,d,h:d[r.START+'startup.json'].update(effective_chat_template_sha256=r.ORIGINAL_TEMPLATE_SHA)),
 ('props_not_lexer_source',lambda f,t,l,d,h:d[r.START+'startup.json'].update(props_reported_template_sha256=r.TEMPLATE_SHA)),
 ('old_epoch_public',lambda f,t,l,d,h:d[r.PUBLIC].update(process_start_ticks=999)),
 ('unbound_launch',lambda f,t,l,d,h:d[r.RESOURCE].update(launch_config_sha256='0'*64)),
 ('not_loopback',lambda f,t,l,d,h:d[r.START+'listeners.json'].update(all_loopback=False)),
 ('body_retained',lambda f,t,l,d,h:d[r.RESOURCE].update(generated_body_retained=True)),
 ('short_context',lambda f,t,l,d,h:d[r.RESOURCE].update(tokens_predicted=767)),
 ('wrong_budget',lambda f,t,l,d,h:d[r.START+'resource_report.json'].update(aggregate_increment_limit_mib=30000)),
 ('old_regression',lambda f,t,l,d,h:d[r.REGRESSION].update(tests=403)),
 ('wrong_lifetime',lambda f,t,l,d,h:l.update(max_seconds=3600)),
 ('hidden_v2_exposure',lambda f,t,l,d,h:h.update({r.V2_OUTPUT_EXPOSURE:'0'*64})),
]
rejected=[]
for label,change in changes:
    b=deepcopy(bundle);change(*b)
    try:invoke(b)
    except (AssertionError,KeyError):rejected.append(label)
    else:raise AssertionError('missed_'+label)
prior=ast.parse((ROOT/'var/review-tools/replay_native_gemma4_exposed.py').read_text());current=ast.parse(path.read_text())
for name in ('load_snapshot','replay_row','replay_groups'):
    get=lambda tree:next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    assert ast.dump(get(prior),include_attributes=False)==ast.dump(get(current),include_attributes=False),name
main=next(n for n in current.body if isinstance(n,ast.FunctionDef) and n.name=='main')
text=ast.get_source_segment(path.read_text(),main)
assert text.index('validate_evidence(')<text.index('result = load(')<text.index('archived = load(')
assert 'torch' not in __import__('sys').modules
proof={'kind':'EXAONE45_REPLAY_SAVED_EVIDENCE_SYNTHETIC_PROOF','status':'PASS_NEW_METADATA_CONTROLS_ONLY',
    'helper_sha256':digest(path.relative_to(ROOT)),'selfcheck_sha256':digest(Path(__file__).relative_to(ROOT)),
    'tampering_rejected':rejected,'runtime_provenance_exact_existing_cpu_consumer_receipt':True,
    'core_functions_ast_exact':['load_snapshot','replay_row','replay_groups'],'core_functions_invoked':0,
    'original_gemma_helper_sha256':digest('var/review-tools/replay_native_gemma4_exposed.py'),
    'actual_cpu_proof_sha256':r.CPU_SHA,'launch_config_sha256':digest('var/research/exaone45-native-launch-epoch1.json'),
    'fake_runtime_fixture_only':True,'actual_run_results_read':False,'dataset_bodies_read':0,
    'live_process_queries':0,'http_calls':0,'gpu_calls':0,'native_calls':0,'model_calls':0,
    'meaning':'Only new saved-evidence boundaries tested. Main not executed; no candidate quality/actual runtime verdict.'}
out=ROOT/'var/research/exaone45-replay-final-evidence-cpu-proof.json'
with out.open('x') as f:json.dump(proof,f,indent=2);f.write('\n')
print(json.dumps({'status':proof['status'],'rejected':len(rejected),'helper_sha256':proof['helper_sha256'],
    'proof_path':str(out.relative_to(ROOT)),'proof_sha256':digest(out.relative_to(ROOT))}))
