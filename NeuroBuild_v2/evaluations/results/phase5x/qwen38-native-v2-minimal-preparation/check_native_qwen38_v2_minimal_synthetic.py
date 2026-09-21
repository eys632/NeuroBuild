"""Public/synthetic replay controls; no actual run, private dataset or native calls."""
import ast
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
from types import SimpleNamespace
from uuid import uuid4

root = Path(__file__).resolve().parents[2]
assert os.environ.get('CUDA_VISIBLE_DEVICES') == ''
path = root / 'var/review-tools/replay_native_qwen38_v2_minimal.py'
ast.parse(path.read_text())
spec = importlib.util.spec_from_file_location('native_replay_preparation', path)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
socket.create_connection = socket.getaddrinfo = r.deny_network
sys.path[:0] = [str(root / 'src'), str(root)]
from scripts import evaluate_requirements as core
from neurobuild.application import requirement_generation as generation
validators = {k: core.Draft202012Validator(core.strict_json((root/r.PATHS[k]).read_text()))
              for k in ('schema', 'canonical_schema')}
source = '문 옆 안내 데스크를 X축 양의 방향으로 2cm 이동해.'
case = {'id': 'SYNTHETIC_NATIVE_REPLAY', 'category': 'synthetic', 'input': source,
        'context': {'axis_convention': 'project_xy'}, 'gold': {'decision': 'clarify', 'target_text': '안내 데스크'}}
base = {'schema_version': '2.0', 'decision': 'READY', 'target_selection_quote': '안내 데스크',
        'current_instruction_quote': source, 'dx_evidence': 'X축 양의 방향으로 2cm', 'dy_evidence': None, 'reason': None}
nonready = dict(base, decision='CLARIFICATION', current_instruction_quote=None, dx_evidence=None, reason='추가 확인 필요')

def evaluate(case, output, *, error=None, trial=1):
    class Fake:
        model = 'synthetic'
        generation_contract = generation.GenerationContract.QUOTES
        def complete(self, source_text, *, axis_convention=None):
            assert source_text == case['input'] and axis_convention == 'project_xy'
            if error:
                raise core.DomainError(error, 'synthetic_safe_error')
            content = output if isinstance(output, str) else json.dumps(output, ensure_ascii=False)
            return SimpleNamespace(content=content, model=self.model, usage={'completion_tokens': 7}, latency_seconds=.1)
    ticks = iter([0., .25])
    return core.evaluate_trial(Fake(), case, validators['schema'], trial, run_id='native-synthetic', clock=lambda:next(ticks))

fixtures = [('retained_ready_on_nonready', base, None),
            ('retained_bad_axis', dict(base, dx_evidence='2cm'), None),
            ('retained_ungrounded_target', dict(base, target_selection_quote='없는 대상'), None),
            ('unretained_schema_rawready', dict(base, extra='discard'), None),
            ('unretained_malformed_unknown', '{', None),
            ('unretained_array_unknown', [], None),
            ('unretained_timeout_unknown', None, 'LOCAL_MODEL_TIMEOUT'),
            ('unretained_truncated_unknown', None, 'LOCAL_MODEL_TRUNCATED'),
            ('unretained_missing_final_unknown', None, 'LOCAL_MODEL_RESPONSE_INVALID'),
            ('retained_nonready', nonready, None)]
rows, observations = [], []
for label, output, error in fixtures:
    row = evaluate(case, output, error=error)
    replay, retained = r.replay_row(row, case, 'native-synthetic', 'synthetic', validators, core, generation)
    assert replay == row
    rows.append(row)
    observations.append({'fixture':label, 'retained':retained, 'error_code':row['error_code']})
row_tampering = []
for label, row, key, value in [
    ('erase_rawready', rows[1], 'raw_model_decision', None),
    ('erase_schema_failed_ready', rows[3], 'model_ready_observed', False),
    ('invent_timeout_ready', rows[6], 'raw_model_decision', 'READY'),
    ('unknown_as_safe_false', rows[8], 'model_ready_observed', False),
    ('invent_adapter_success', rows[1], 'adapter_accepted', True),
    ('erase_canonical', rows[0], 'semantic_output', None),
    ('inflate_semantic', rows[0], 'semantic_rubric_correct', True),
    ('wrong_contract', rows[0], 'generation_contract', '3.0')]:
    bad=deepcopy(row);bad[key]=value
    try:r.replay_row(bad,case,'native-synthetic','synthetic',validators,core,generation)
    except AssertionError:row_tampering.append(label)
    else:raise AssertionError('missed_row_tamper')
metrics=core.summarize(rows)
assert metrics['critical_fp_model_ready']['numerator']==4
assert metrics['critical_fp_model_ready']['denominator']==10
assert metrics['unsafe_accepted_ready_total']['numerator']==1
assert metrics['raw_decision_observed']['numerator']==5

# Whole synthetic 80/5 protocol and unknown coverage; no real evaluation file.
cases=[]
for i in range(80):
    c=deepcopy(case);c['id']=f'SYNTHETIC_{i:03}'
    if i<40:c['gold'].update(decision='requirement_ok',dx_m=.02,dy_m=0)
    cases.append(c)
def complete_result(timeout=False):
    trials=[evaluate(c,base if i<40 else nonready,error='LOCAL_MODEL_TIMEOUT' if timeout and i==79 else None)
            for i,c in enumerate(cases)]
    warmups=[evaluate(cases[i],base,trial=-i-1) for i in range(5)]
    return {'run_id':'native-synthetic','trials':trials,'warmups':warmups,'metrics':core.summarize(trials)}
manifest={'case_order':[c['id'] for c in cases],'served_model':'synthetic'}
perfect=complete_result(); audit=r.replay_groups(perfect,cases,manifest,validators,core,generation)
assert audit['holdout_gate']=='PASS' and audit['retained_generation_json_replayed']=={'warmups':5,'trials':80}
unknown=complete_result(True); a=r.replay_groups(unknown,cases,manifest,validators,core,generation)
assert a['holdout_gate']=='FAIL'
assert {k:a['metrics']['critical_fp_model_ready'][k] for k in ('numerator','denominator','rate')}=={'numerator':0,'denominator':40,'rate':0.0}
assert a['metrics']['nonready_gold_raw_decision_observed']['numerator']==39
assert a['unretained_response_rows']=={'warmups':0,'trials':1}
count_tampering=[]
for label, mutate in [('missing_trial',lambda d:d['trials'].pop()),('missing_warmup',lambda d:d['warmups'].pop()),
                      ('trial_order',lambda d:d['trials'].reverse()),
                      ('duplicate_case',lambda d:d['trials'].__setitem__(79,deepcopy(d['trials'][0]))),
                      ('wrong_trial_index',lambda d:d['trials'][0].update(trial=2)),('metric_denominator',lambda d:d['metrics']['critical_fp_model_ready'].update(denominator=39))]:
    bad=deepcopy(perfect);mutate(bad)
    try:r.replay_groups(bad,cases,manifest,validators,core,generation)
    except AssertionError:count_tampering.append(label)
    else:raise AssertionError('missed_count_tamper')

# Synthetic identity/protocol metadata, checked before future output reads.
commit='a'*40
launch={'served_model_name':'synthetic','profile':'a100','batch_size':64,'ubatch_size':64,'max_model_len':4096,
        'enable_reasoning':False,'estimated_peak_mib':28672,'peak_allowance_mib':0,'source_commit':r.SOURCE_PIN,
        'model_sha256':r.GGUF_SHA,'model_revision':r.REVISION,
        'binary_sha256':'b'*64,'source_report_sha256':'c'*64,'build_report_sha256':'d'*64,'model_header_report_sha256':'e'*64}
runtime={'runtime_kind':'llama_cpp','profile':'a100','physical_gpu':3,'logical_gpu':0,'cuda_architecture':'80-real',
         'max_sequences':1,'max_model_len':4096,'enable_reasoning':False,'reasoning_parser':'deepseek','quantization':'Q4_K_M',
         'llama_cpp_commit':r.SOURCE_PIN,'gguf_sha256':r.GGUF_SHA,'chat_template_sha256':r.TEMPLATE_SHA,
         'binary_sha256':'b'*64,'source_provenance_sha256':'c'*64,'build_report_sha256':'d'*64,'gguf_header_sha256':'e'*64}
provenance={'runtime_variant':r.VARIANT,'reference_kind':'hf-tokenizer-json-with-nfc-normalizer-disabled',
            'context_tokenizer':'native_raw_unicode_no_nfc_repair','application_input_output_nfc_repair':False,
            'hf_equivalence':{'status':'FAIL','case_count':20,'id_match_count':19,'mismatch_indices':[11],
              'proof_sha256':'b537545d26a876a1496c2f85ad979330eba938f2880aae49190640b2404c63e0',
              'original_fixture_sha256':'79c4448b7ee949add0a80e8a7f0fc0d73575aaf01ff6e52beb3cfae8434ea1bd'},
            'raw_reference':{'case_count':20,'id_match_count':20,'native_original_roundtrip_count':20,
              'fixture_sha256':'9658eb53fae81adee1b775b45f796f3484db69aea41e04a020765fa05d770514',
              'native_proof_sha256':'12a5ebeafc16969f36435d9bb9e933ba12197d01ba05e8f26df41114f4e01d2d'}}
protocol={'generation_contract':'2.0','sampling_profile':'qwen38_nonthinking_llama_cpp','sampling_request_parameters':deepcopy(r.SAMPLING),
          'max_tokens':768,'timeout_seconds':120,'concurrency':1,'enable_thinking':False,'reasoning_parser':'deepseek',
          'structured_output_protocol':'llama_cpp_json_schema','guided_decoding_backend':None,
          'required_server_structured_backend':'llama_cpp_gbnf','response_format_type':'json_schema','tool_parser':None,
          'temperature':.7,'seed':42,'warmups':5,'trials_per_case':1}
freeze={**{k:protocol[k] for k in ('generation_contract','sampling_profile','sampling_request_parameters','max_tokens',
        'timeout_seconds','concurrency','enable_thinking','reasoning_parser')},
        'dataset':r.PATHS['dataset'],'split':'heldout','lifecycle':'FROZEN_BEFORE_NATIVE_QWEN38_V2_MINIMAL_HOLDOUT',
        'candidate_variant':r.VARIANT,'model_id':r.MODEL,'model_revision':r.REVISION,'tokenizer_revision':r.REVISION,
        'served_model':'synthetic','pipeline':'single','maximum_calls_per_case':1,'expected_http_calls':85,
        'protocol':'llama_cpp_json_schema','warmups_per_run':5,'trials_per_case':1,'cases':80,'ready_gold':40,'nonready_gold':40,
        'gate_targets':r.GATES,'prompt':r.PATHS['prompt'],'generation_schema':r.PATHS['schema'],
        'frozen_at_utc':'2026-09-20T00:00:00+00:00','tokenizer_contract':provenance}
meta={'git':{'commit':commit,'dirty':False},'sha256':{'dataset':'7416f05613b1490358672f3926770dbd8653e676577eeee6ba65f863b27cec40'},
      'split':'heldout','model_id':r.MODEL,'model_revision':r.REVISION,'tokenizer_revision':r.REVISION,
      'served_model':'synthetic','runtime':runtime,'protocol':protocol,'created_at_utc':'2026-09-20T00:01:00+00:00'}
r.validate_identity(meta,freeze,runtime,launch,commit)
fast_launch=dict(launch,batch_size=64,ubatch_size=64)
r.validate_identity(meta,freeze,runtime,fast_launch,commit)
identity_tampering=[]
for label, mutate in [
    ('wrong_model',lambda m,f,t,l:m.update(model_id='Qwen/Qwen3-32B-AWQ')),
    ('wrong_development_split',lambda m,f,t,l:m.update(split='development')),
    ('different_dataset',lambda m,f,t,l:m['sha256'].update(dataset='0'*64)),
    ('dirty_run',lambda m,f,t,l:m['git'].update(dirty=True)),
    ('legacy_protocol',lambda m,f,t,l:m['protocol'].update(structured_output_protocol='legacy_guided_json')),
    ('thinking_mode',lambda m,f,t,l:m['protocol'].update(enable_thinking=True)),
    ('history_penalty',lambda m,f,t,l:m['protocol']['sampling_request_parameters'].update(presence_penalty=1.5)),
    ('wrong_physical_gpu',lambda m,f,t,l:t.update(physical_gpu=1)),
    ('old_batch_one',lambda m,f,t,l:l.update(batch_size=1)),
    ('unreviewed_batch_pair',lambda m,f,t,l:l.update(batch_size=64,ubatch_size=1)),
    ('bool_microbatch',lambda m,f,t,l:l.update(ubatch_size=True)),
    ('hide_hf_failure',lambda m,f,t,l:f['tokenizer_contract']['hf_equivalence'].update(status='PASS')),
    ('input_nfc_repair',lambda m,f,t,l:f['tokenizer_contract'].update(application_input_output_nfc_repair=True)),
    ('lower_quality_gate',lambda m,f,t,l:f['gate_targets'].update(semantic_required_at_least=108))]:
    m,f,t,l=deepcopy((meta,freeze,runtime,launch));mutate(m,f,t,l)
    try:r.validate_identity(m,f,t,l,commit)
    except AssertionError:identity_tampering.append(label)
    else:raise AssertionError('missed_identity_tamper')
# Only synthetic metadata below: no epoch probing, archive/body or GPU reads.
start='evaluations/results/phase5x/synthetic-v2-epoch/'
freeze.update(runtime_metadata=start+'runtime_metadata.json', current_attestation=start+'attestation.json',
              current_carry_forward=start+'contract_carry_forward.json',
              runtime_epoch_snapshot={'pid':333,'start_ticks':444,'guard_started_at_utc':'2026-09-19T23:59:00+00:00'})
freeze['time_budget']={'model_calls':85,'planned_seconds_per_call':30,'reserve_seconds':600,
    'required_remaining_seconds':3150,'guard_max_seconds':3600,'elapsed_seconds_at_freeze':30.,
    'remaining_seconds_at_freeze':3570.,'must_recheck_after_push_immediately_before_first_warmup':True}
launch.update(max_seconds=3600,log_file='var/synthetic-new.log',report_file='var/synthetic-new.json',port=8003)
historical_launch=dict(launch,max_seconds=10800,log_file='var/synthetic-old.log',report_file='var/synthetic-old.json')
proof_hashes={start+n:format(i+10,'064x') for i,n in enumerate(('launch_config.json','guard_before.json',
    'guard_after.json','listeners.json','attestation.json','contract_carry_forward.json'))}
runtime.update(launch_config_sha256=proof_hashes[start+'launch_config.json'],
    startup_report_sha256=proof_hashes[start+'attestation.json'],listener_report_sha256=proof_hashes[start+'listeners.json'])
historical_epoch={'pid':111,'process_start_ticks':222,'guard_started_at_utc':'2026-09-19T22:59:00+00:00'}
carry={**deepcopy(provenance),'kind':'NATIVE_HISTORICAL_CONTRACT_CARRY_FORWARD','status':'VERIFIED_REUSED_NOT_RERUN',
       'historical_freeze_path':r.HISTORICAL_FREEZE,'historical_freeze_sha256':r.HISTORICAL_FREEZE_SHA,
       'current_launch_config_sha256':proof_hashes[start+'launch_config.json'],'inference_config_equivalent':True,
       'allowed_operational_changes':['max_seconds','log_file','report_file'],
       'actual_changed_fields':['log_file','max_seconds','report_file'],'historical_epoch':historical_epoch,
       'tests_rerun':0,'cpu_probe_calls':0,'public_model_calls':0,'resource_model_calls':0}
attestation={**deepcopy(provenance),'kind':'NATIVE_MINIMAL_EPOCH_ATTESTATION','status':'PASS',
    'http_get_calls':1,'health_http_status':200,'health_status':'ok','model_inference_calls':0,'gpu_query_calls':0,
    'full_startup_probe_calls':0,'public_model_calls':0,'resource_model_calls':0,'cpu_tests_rerun':0,
    'raw_http_bodies_saved':False,'native_identity_verified':True,'pid':333,'process_start_ticks':444,
    'guard_started_at_utc':'2026-09-19T23:59:00+00:00','at_utc':'2026-09-19T23:59:40+00:00',
    'current_guard_elapsed_seconds':20.,'current_guard_remaining_seconds':3580.,'max_seconds':3600}
for k,n in [('launch_config_sha256','launch_config.json'),('guard_before_sha256','guard_before.json'),
    ('guard_after_sha256','guard_after.json'),('listener_report_sha256','listeners.json'),
    ('carry_forward_sha256','contract_carry_forward.json')]:attestation[k]=proof_hashes[start+n]
artifacts={k:launch[k] for k in ('binary_sha256','source_report_sha256','build_report_sha256','source_commit',
    'model_sha256','model_revision','model_header_report_sha256')}
guard={'child_pid':333,'started_at_utc':'2026-09-19T23:59:00+00:00','state':'RUNNING','runtime_family':'llama_cpp',
    'native_identity_verified':True,'physical_gpu_index':3,'required_cuda_visible_devices':'3',
    'max_model_len':4096,'max_num_seqs':1,'batch_size':64,'ubatch_size':64,'served_model_name':'synthetic',
    'enable_reasoning':False,'reasoning_parser':'deepseek','native_output_policy':'DISCARD_STDOUT_STDERR',
    'native_core_dump_limit_bytes':0,'peak_allowance_mib':0,'aggregate_increment_limit_mib':28672,
    'required_free_floor_mib':7275,'minimum_observed_free_mib':18000,'observed_baseline_relative_peak_mib':18000,
    'native_artifacts':artifacts,'elapsed_seconds':10.,'preflight':{'allowed':True,
    'policy':{'estimated_peak_mib':28672},'budget':{'estimated_startup_or_inference_peak_mib':28672,
    'available_model_budget_mib':29098,'required_safety_margin_mib':7275}}}
before=deepcopy(guard);after=dict(deepcopy(guard),elapsed_seconds=20.)
listeners={'pid':333,'process_start_ticks':444,'verdict':'PASS','all_loopback':True,'snapshot_complete':True,
    'uid':os.getuid(),'listeners':[{'address':'127.0.0.1','port':8003}]}
def evidence_check(items):
    r.validate_minimal_bundle(*items)
items=(freeze,runtime,launch,attestation,carry,before,after,listeners,historical_launch,historical_epoch,proof_hashes)
evidence_check(items)
evidence_tampering=[]
for label, mutate in [
    ('claim_full_startup',lambda x:x[3].update(kind='NATIVE_STARTUP_HTTP_PROOF',http_get_calls=3)),
    ('wrong_current_attestation_edge',lambda x:x[1].update(startup_report_sha256='0'*64)),
    ('wrong_current_listener_hash',lambda x:x[3].update(listener_report_sha256='0'*64)),
    ('model_probe_repeated',lambda x:x[3].update(model_inference_calls=1)),
    ('historical_suite_repeated',lambda x:x[4].update(resource_model_calls=1)),
    ('historical_pass_relabelled',lambda x:x[4].update(status='PASS_FRESH')),
    ('changed_inference',lambda x:x[2].update(max_model_len=8192)),
    ('changed_batch',lambda x:x[2].update(batch_size=2,ubatch_size=1)),
    ('hidden_config_change',lambda x:x[4].update(actual_changed_fields=[])),
    ('current_pid_mismatch',lambda x:x[6].update(child_pid=334)),
    ('current_ticks_mismatch',lambda x:x[7].update(process_start_ticks=445)),
    ('external_listener',lambda x:x[7].update(all_loopback=False)),
    ('wrong_uid',lambda x:x[7].update(uid=os.getuid()+1)),
    ('wrong_port',lambda x:x[7]['listeners'][0].update(port=8004)),
    ('wrong_gpu',lambda x:x[6].update(physical_gpu_index=1)),
    ('unverified_identity',lambda x:x[6].update(native_identity_verified=False)),
    ('failed_fresh_preflight',lambda x:x[6]['preflight'].update(allowed=False)),
    ('free_below_floor',lambda x:x[6].update(minimum_observed_free_mib=7274)),
    ('exceeded_peak',lambda x:x[6].update(observed_baseline_relative_peak_mib=28673)),
    ('expired_guard',lambda x:x[6].update(elapsed_seconds=3600)),
    ('reasoning_body_policy',lambda x:x[6].update(native_output_policy='CAPTURE')),
    ('insufficient_freeze_time',lambda x:x[0]['time_budget'].update(elapsed_seconds_at_freeze=451.,remaining_seconds_at_freeze=3149.)),
    ('disable_pre_warmup_recheck',lambda x:x[0]['time_budget'].update(must_recheck_after_push_immediately_before_first_warmup=False)),
    ('weaken_time_budget',lambda x:x[0]['time_budget'].update(required_remaining_seconds=1000)),
    ('late_attestation',lambda x:x[3].update(at_utc='2026-09-20T00:00:01+00:00')),
    ('current_old_epoch_conflation',lambda x:x[9].update(pid=333,process_start_ticks=444)),
    ('old_hf_failure_hidden',lambda x:x[4]['hf_equivalence'].update(status='PASS'))]:
    bad=deepcopy(items);mutate(bad)
    try:evidence_check(bad)
    except AssertionError:evidence_tampering.append(label)
    else:raise AssertionError('missed_evidence_tamper:'+label)
# The prior125 output is NOT read/replayed; only this independent synthetic proof link.
old_prefix='evaluations/results/phase5x/exposed-native-qwen38-diagnostic/'
hashes={r.V2_FREEZE:'f'*64,old_prefix+'results.json':'e16c753dd9701f1115a8d56445f27f68835e20b9323787316db776606769da48',
    old_prefix+'independent_replay.json':'6a9ce259b60348504cfa1afec9ddb7838d30190e46b88f2b1ab33917e46836ab'}
prior={'status':'PASS','diagnostic_gate':'PASS','run_id':'20260920T071218Z-d9e611b184ea4f8cbb0d7369982ef361',
       'trials':120,'warmups':5,'original_artifact_sha256':{'var/old/results.json':hashes[old_prefix+'results.json']}}
addendum={'kind':'EXPLICIT_USER_DIRECTED_EXECUTION_PROTOCOL_OVERRIDE','prior_dataset_freeze':r.V2_FREEZE,
    'prior_dataset_freeze_sha256':hashes[r.V2_FREEZE],'prior_dataset_freeze_preserved_unchanged':True,
    'replacement_execution_protocol':{'cases':80,'trials_per_case':1,'expected_trials':80,'warmups':5,
    'expected_http_calls':85,'split':'heldout','ready_gold':40,'nonready_gold':40,'same_exposed_dataset_additional_model_calls':0},
    'gate_targets':deepcopy(r.GATES),'prerequisite':{'results_sha256':hashes[old_prefix+'results.json'],
    'independent_replay_sha256':hashes[old_prefix+'independent_replay.json'],'completed_diagnostic_and_replay_will_not_be_repeated':True,
    'first_quality_gate':'PASS','diagnostic_run':prior['run_id']}}
r.validate_execution_addendum(addendum,prior,hashes)
addendum_tampering=[]
for label,mutate in [
    ('silently_three_trials',lambda a,p:a['replacement_execution_protocol'].update(trials_per_case=3)),
    ('warmup_removed',lambda a,p:a['replacement_execution_protocol'].update(warmups=0)),
    ('previous_freeze_changed',lambda a,p:a.update(prior_dataset_freeze_preserved_unchanged=False)),
    ('failed_prerequisite',lambda a,p:p.update(diagnostic_gate='FAIL')),
    ('unlinked_prior_results',lambda a,p:p['original_artifact_sha256'].update({'var/old/results.json':'0'*64})),
    ('weakened_semantic_gate',lambda a,p:a['gate_targets'].update(semantic_required_at_least=75))]:
    a,p=deepcopy((addendum,prior));mutate(a,p)
    try:r.validate_execution_addendum(a,p,hashes)
    except AssertionError:addendum_tampering.append(label)
    else:raise AssertionError('missed_addendum_tamper:'+label)
# Exact unchanged per-row replay from the reviewed diagnostic; no prior replay execution.
oldtree=ast.parse((root/'var/review-tools/replay_native_qwen38_exposed.py').read_text())
newtree=ast.parse(path.read_text())
func=lambda tree,name:next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
assert ast.dump(func(oldtree,'replay_row'),include_attributes=False)==ast.dump(func(newtree,'replay_row'),include_attributes=False)
assert r.digest(root/'var/review-tools/replay_native_qwen38_exposed.py')=='c1f063fe4a6ea14c9eaa57bb6e10467460f6765d9a3b4fce67a6fca0f69ac592'

assert 'torch' not in sys.modules
proof={'status':'PASS_SYNTHETIC_PREPARATION_ONLY','helper_sha256':r.digest(path),'selfcheck_sha256':r.digest(Path(__file__)),
       'source_scope':'Current exact source for synthetic preparation; run checkpoint snapshot binding deferred until root provides final pins',
       'source_sha256':{k:r.digest(root/r.PATHS[k]) for k in ('scorer','parser','generation_adapter','client')},
       'fixtures':observations,'row_tampering_rejected':row_tampering,'count_tampering_rejected':count_tampering,
       'identity_tampering_rejected':identity_tampering,'runtime_evidence_tampering_rejected':evidence_tampering,
       'execution_addendum_tampering_rejected':addendum_tampering,'synthetic_complete_protocols':2,
       'replay_row_ast_unchanged':True,'diagnostic_helper_unchanged':True,
       'full_80_plus_5_and_40_40_denominators':True,'unknown_keeps_denominator_and_blocks_gate':True,
       'actual_run_results_read':False,'private_dataset_reads':0,'reasoning_body_reads':0,
       'network_calls':0,'model_calls':0,'gpu_calls':0,'native_calls':0}
dest=root/'var/research'/('native-v2-minimal-replay-selfcheck-'+uuid4().hex+'.json')
with dest.open('x') as f:json.dump(proof,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'status':proof['status'],'row_fixtures':len(fixtures),'row_tampering':len(row_tampering),
    'count_tampering':len(count_tampering),'identity_tampering':len(identity_tampering),
    'runtime_evidence_tampering':len(evidence_tampering),'addendum_tampering':len(addendum_tampering),
    'proof':str(dest.relative_to(root)),'proof_sha256':r.digest(dest),'helper_sha256':r.digest(path)}))
