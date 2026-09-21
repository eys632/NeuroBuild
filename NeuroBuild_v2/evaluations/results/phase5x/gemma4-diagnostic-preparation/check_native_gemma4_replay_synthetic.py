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
path = root / 'var/review-tools/replay_native_gemma4_exposed.py'
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

# Whole synthetic 120/5 protocol and unknown coverage; no real evaluation file.
cases=[]
for i in range(120):
    c=deepcopy(case);c['id']=f'SYNTHETIC_{i:03}'
    if i<62:c['gold'].update(decision='requirement_ok',dx_m=.02,dy_m=0)
    cases.append(c)
def complete_result(timeout=False):
    trials=[evaluate(c,base if i<62 else nonready,error='LOCAL_MODEL_TIMEOUT' if timeout and i==119 else None)
            for i,c in enumerate(cases)]
    warmups=[evaluate(cases[i],base,trial=-i-1) for i in range(5)]
    return {'run_id':'native-synthetic','trials':trials,'warmups':warmups,'metrics':core.summarize(trials)}
manifest={'case_order':[c['id'] for c in cases],'served_model':'synthetic'}
perfect=complete_result(); audit=r.replay_groups(perfect,cases,manifest,validators,core,generation)
assert audit['diagnostic_gate']=='PASS' and audit['retained_generation_json_replayed']=={'warmups':5,'trials':120}
unknown=complete_result(True); a=r.replay_groups(unknown,cases,manifest,validators,core,generation)
assert a['diagnostic_gate']=='FAIL'
assert {k:a['metrics']['critical_fp_model_ready'][k] for k in ('numerator','denominator','rate')}=={'numerator':0,'denominator':58,'rate':0.0}
assert a['metrics']['nonready_gold_raw_decision_observed']['numerator']==57
assert a['unretained_response_rows']=={'warmups':0,'trials':1}
count_tampering=[]
for label, mutate in [('missing_trial',lambda d:d['trials'].pop()),('missing_warmup',lambda d:d['warmups'].pop()),
                      ('trial_order',lambda d:d['trials'].reverse()),('metric_denominator',lambda d:d['metrics']['critical_fp_model_ready'].update(denominator=57))]:
    bad=deepcopy(perfect);mutate(bad)
    try:r.replay_groups(bad,cases,manifest,validators,core,generation)
    except AssertionError:count_tampering.append(label)
    else:raise AssertionError('missed_count_tamper')

# Prove row/stage/scorer/denominator code has not drifted.
prior_path=root/'var/review-tools/replay_native_qwen38_exposed.py'
assert r.digest(prior_path)==r.ORIGINAL_REPLAY_SHA
prior=ast.parse(prior_path.read_text());current=ast.parse(path.read_text())
for name in ('replay_row','replay_groups','load_snapshot'):
    left=next(n for n in prior.body if getattr(n,'name',None)==name)
    right=next(n for n in current.body if getattr(n,'name',None)==name)
    assert ast.dump(left)==ast.dump(right),name

commit='a'*40
variant='SYNTHETIC_GEMMA_VARIANT_NOT_ACTUAL_FREEZE'
launch={'served_model_name':'synthetic','profile':'a100','batch_size':64,'ubatch_size':64,'max_model_len':4096,
        'enable_reasoning':False,'estimated_peak_mib':28672,'peak_allowance_mib':0,'source_commit':r.SOURCE_PIN,
        'model_sha256':r.GGUF_SHA,'model_revision':r.REVISION,
        'binary_sha256':'b'*64,'source_report_sha256':'c'*64,'build_report_sha256':'d'*64,'model_header_report_sha256':'e'*64}
runtime={'runtime_kind':'llama_cpp','profile':'a100','physical_gpu':3,'logical_gpu':0,'cuda_architecture':'80-real',
         'max_sequences':1,'max_model_len':4096,'enable_reasoning':False,'reasoning_parser':'deepseek','quantization':'Q4_0',
         'llama_cpp_commit':r.SOURCE_PIN,'gguf_sha256':r.GGUF_SHA,'chat_template_sha256':r.TEMPLATE_SHA,
         'binary_sha256':'b'*64,'source_provenance_sha256':'c'*64,'build_report_sha256':'d'*64,'gguf_header_sha256':'e'*64}
protocol={'generation_contract':'2.0','sampling_profile':r.PROFILE,'sampling_request_parameters':deepcopy(r.SAMPLING),
          'max_tokens':768,'timeout_seconds':120,'concurrency':1,'enable_thinking':False,'reasoning_parser':'deepseek',
          'structured_output_protocol':'llama_cpp_json_schema','guided_decoding_backend':None,
          'required_server_structured_backend':'llama_cpp_gbnf','response_format_type':'json_schema','tool_parser':None,
          'temperature':1.0,'seed':42,'warmups':5,'trials_per_case':1}
freeze={**{k:protocol[k] for k in ('generation_contract','sampling_profile','sampling_request_parameters','max_tokens',
        'timeout_seconds','concurrency','enable_thinking','reasoning_parser')},
        'dataset':r.PATHS['dataset'],'split':'development','lifecycle':r.LIFECYCLE,
        'candidate_variant':variant,'model_id':r.MODEL,'model_revision':r.REVISION,'tokenizer_revision':r.REVISION,
        'served_model':'synthetic','pipeline':'single','maximum_calls_per_case':1,'expected_http_calls':125,
        'protocol':'llama_cpp_json_schema','warmups_per_run':5,'trials_per_case':1,'cases':120,'ready_gold':62,'nonready_gold':58,
        'gate_targets':deepcopy(r.GATES),'prompt':r.PATHS['prompt'],'generation_schema':r.PATHS['schema'],
        'frozen_at_utc':'2026-09-20T00:00:00+00:00'}
meta={'git':{'commit':commit,'dirty':False},'sha256':{'dataset':'7e5b9a05932df7aafdbf683655b044b3e3b25cbffb4115d298e1490aecbc7a5b'},
      'split':'development','model_id':r.MODEL,'model_revision':r.REVISION,'tokenizer_revision':r.REVISION,
      'served_model':'synthetic','runtime':runtime,'protocol':protocol,'created_at_utc':'2026-09-20T00:01:00+00:00'}
r.validate_identity(meta,freeze,runtime,launch,commit,expected_variant=variant)
identity_tampering=[]
for label,mutate in [
 ('wrong_model',lambda m,f,t,l:m.update(model_id='Qwen/Qwen3-32B-AWQ')),
 ('qwen_sampling',lambda m,f,t,l:m['protocol'].update(sampling_profile='qwen38_nonthinking_llama_cpp')),
 ('qwen_quant',lambda m,f,t,l:t.update(quantization='Q4_K_M')),
 ('wrong_template',lambda m,f,t,l:t.update(chat_template_sha256='0'*64)),
 ('penalty_changed',lambda m,f,t,l:m['protocol']['sampling_request_parameters'].update(presence_penalty=1.5)),
 ('unknown_batch_pair',lambda m,f,t,l:l.update(batch_size=2,ubatch_size=1)),
 ('bool_batch',lambda m,f,t,l:l.update(batch_size=True)),
 ('weaker_gate',lambda m,f,t,l:f['gate_targets'].update(semantic_required_at_least=108)),
 ('dirty_snapshot',lambda m,f,t,l:m['git'].update(dirty=True)),
 ('wrong_gpu',lambda m,f,t,l:t.update(physical_gpu=1)),
 ('wrong_variant',lambda m,f,t,l:f.update(candidate_variant='OTHER')),
 ('freeze_after_run',lambda m,f,t,l:f.update(frozen_at_utc='2026-09-21T00:00:00+00:00'))]:
    m,f,t,l=deepcopy((meta,freeze,runtime,launch));mutate(m,f,t,l)
    try:r.validate_identity(m,f,t,l,commit,expected_variant=variant)
    except AssertionError:identity_tampering.append(label)
    else:raise AssertionError('missed_identity_tamper')
assert r.PREPARATION_STATUS=='DRAFT_RUNTIME_FREEZE_BINDING_PENDING'
assert 'torch' not in sys.modules
proof={'status':'PASS_SYNTHETIC_CORE_ONLY_DRAFT_RUNTIME_PENDING',
 'helper_sha256':r.digest(path),'selfcheck_sha256':r.digest(Path(__file__)),
 'original_replay_sha256':r.ORIGINAL_REPLAY_SHA,'core_functions_ast_exact':3,
 'source_sha256':{k:r.digest(root/r.PATHS[k]) for k in ('scorer','parser','generation_adapter','client')},
 'fixtures':observations,'row_tampering_rejected':row_tampering,
 'count_tampering_rejected':count_tampering,'identity_tampering_rejected':identity_tampering,
 'synthetic_complete_protocols':2,'full_120_plus_5_and_62_58_denominators':True,
 'unknown_keeps_denominator_and_blocks_gate':True,'actual_run_results_read':False,
 'historical125_replays':0,'private_dataset_reads':0,'reasoning_body_reads':0,
 'model_calls':0,'native_calls':0,'gpu_calls':0,'network_calls':0,
 'limitation':'Actual Gemma CPU/runtime/freeze evidence validation and final source snapshot not bound yet; main is fail-closed.'}
dest=root/'var/research'/('gemma4-replay-core-selfcheck-'+uuid4().hex+'.json')
with dest.open('x') as f:json.dump(proof,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'status':proof['status'],'row_fixtures':len(fixtures),
 'row_tampering':len(row_tampering),'count_tampering':len(count_tampering),
 'identity_tampering':len(identity_tampering),'proof':str(dest.relative_to(root)),
 'proof_sha256':r.digest(dest),'helper_sha256':r.digest(path)}))
