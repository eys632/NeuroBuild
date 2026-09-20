"""Metadata-only EXAONE replay preparation; no core calls or actual run/data reads."""
import ast
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys

ROOT=Path(__file__).resolve().parents[2]
assert os.environ.get('CUDA_VISIBLE_DEVICES')==''
path=ROOT/'var/review-tools/replay_native_exaone45_exposed_v2.py'
spec=importlib.util.spec_from_file_location('exaone_replay_draft',path)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
socket.create_connection=socket.getaddrinfo=r.deny_network
prior=ROOT/'var/review-tools/replay_native_gemma4_exposed.py'
assert sha256(prior.read_bytes()).hexdigest()=='0ce14fc2a532eb5add9a02f0137ce3a7aec77ae5837b7a1942a96e7804c41ff0'
before,after=ast.parse(prior.read_text()),ast.parse(path.read_text())
core_names=('load_snapshot','replay_row','replay_groups')
for name in core_names:
    get=lambda tree:next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    assert ast.dump(get(before),include_attributes=False)==ast.dump(get(after),include_attributes=False),name
commit='a'*40
launch={'served_model_name':'synthetic','profile':'a100','batch_size':64,'ubatch_size':64,
    'max_model_len':4096,'enable_reasoning':False,'estimated_peak_mib':28672,'peak_allowance_mib':0,
    'source_commit':r.SOURCE_PIN,'model_sha256':r.GGUF_SHA,'model_revision':r.REVISION,
    'binary_sha256':'b'*64,'source_report_sha256':'c'*64,'build_report_sha256':'d'*64,
    'model_header_report_sha256':r.HEADER_SHA, 'chat_template_path':str(ROOT/r.OVERRIDE_PATH),
    'chat_template_sha256':r.TEMPLATE_SHA}
runtime={'runtime_kind':'llama_cpp','profile':'a100','physical_gpu':3,'logical_gpu':0,
    'cuda_architecture':'80-real','max_sequences':1,'max_model_len':4096,
    'enable_reasoning':False,'reasoning_parser':'deepseek','quantization':'Q4_K_M',
    'llama_cpp_commit':r.SOURCE_PIN,'gguf_sha256':r.GGUF_SHA,'chat_template_sha256':r.TEMPLATE_SHA,
    'binary_sha256':'b'*64,'source_provenance_sha256':'c'*64,'build_report_sha256':'d'*64,
    'gguf_header_sha256':r.HEADER_SHA}
protocol={'generation_contract':'2.0','sampling_profile':r.PROFILE,'sampling_request_parameters':deepcopy(r.SAMPLING),
    'max_tokens':768,'timeout_seconds':120,'concurrency':1,'enable_thinking':False,
    'reasoning_parser':'deepseek','structured_output_protocol':'llama_cpp_json_schema',
    'guided_decoding_backend':None,'required_server_structured_backend':'llama_cpp_gbnf',
    'response_format_type':'json_schema','tool_parser':None,'temperature':.6,'seed':42,
    'warmups':5,'trials_per_case':1}
freeze={**{k:deepcopy(protocol[k]) for k in ('generation_contract','sampling_profile',
    'sampling_request_parameters','max_tokens','timeout_seconds','concurrency','enable_thinking','reasoning_parser')},
    'dataset':r.PATHS['dataset'],'split':'development','lifecycle':r.LIFECYCLE,
    'candidate_variant':r.VARIANT,'model_id':r.MODEL,'model_revision':r.REVISION,'tokenizer_revision':r.REVISION,
    'served_model':'synthetic','pipeline':'single','maximum_calls_per_case':1,'expected_http_calls':125,
    'protocol':'llama_cpp_json_schema','warmups_per_run':5,'trials_per_case':1,'cases':120,
    'ready_gold':62,'nonready_gold':58,'gate_targets':deepcopy(r.GATES),'prompt':r.PATHS['prompt'],
    'generation_schema':r.PATHS['schema'],'frozen_at_utc':'2026-09-20T00:00:00+00:00'}
manifest={'git':{'commit':commit,'dirty':False},'sha256':{'dataset':'7e5b9a05932df7aafdbf683655b044b3e3b25cbffb4115d298e1490aecbc7a5b'},
    'split':'development','model_id':r.MODEL,'model_revision':r.REVISION,'tokenizer_revision':r.REVISION,
    'served_model':'synthetic','runtime':runtime,'protocol':protocol,'created_at_utc':'2026-09-20T00:01:00+00:00'}
freeze.update(template_proof_variant=r.TEMPLATE_VARIANT,original_embedded_template_sha256=r.ORIGINAL_TEMPLATE_SHA,
    chat_template_override={'path':r.OVERRIDE_PATH,'sha256':r.TEMPLATE_SHA},
    official_hf_equivalence={'status':'FAIL','case_count':20,'id_match_count':18,'mismatch_indices':[11,12],
        'native_raw_roundtrip_count':20,'official_ids_raw_roundtrip_count':18,
        'proof_ref':{'path':'var/research/native-exaone45-contract/public-vocab-proof.json','sha256':r.OFFICIAL_VOCAB_SHA}},
    application_input_output_nfc_repair=False,context_tokenizer='native_raw_unicode_no_nfc_repair')
r.validate_identity(manifest,freeze,runtime,launch,commit,expected_variant=r.VARIANT)
tampering=[
 ('other_model',lambda m,f,t,l:m.update(model_id='ggml-org/Qwen3.8-27B-GGUF')),
 ('other_revision',lambda m,f,t,l:f.update(model_revision='0'*40)),
 ('old_profile',lambda m,f,t,l:m['protocol'].update(sampling_profile='gemma4_nonthinking_llama_cpp')),
 ('neutral_presence',lambda m,f,t,l:m['protocol']['sampling_request_parameters'].update(presence_penalty=0.0)),
 ('disabled_window',lambda m,f,t,l:m['protocol']['sampling_request_parameters'].update(repeat_last_n=0)),
 ('wrong_sampler_order',lambda m,f,t,l:m['protocol']['sampling_request_parameters']['samplers'].reverse()),
 ('omitted_penalties',lambda m,f,t,l:m['protocol']['sampling_request_parameters']['samplers'].remove('penalties')),
 ('boolean_repeat',lambda m,f,t,l:m['protocol']['sampling_request_parameters'].update(repeat_penalty=True)),
 ('other_quantization',lambda m,f,t,l:t.update(quantization='Q4_0')),
 ('other_template',lambda m,f,t,l:t.update(chat_template_sha256='0'*64)),
 ('unbound_header',lambda m,f,t,l:l.update(model_header_report_sha256='0'*64)),
 ('other_gpu',lambda m,f,t,l:t.update(physical_gpu=1)),
 ('other_batch',lambda m,f,t,l:l.update(batch_size=2,ubatch_size=1)),
 ('weaker_gate',lambda m,f,t,l:f['gate_targets'].update(critical_model_ready_fp_required=1)),
 ('denominator_shrink',lambda m,f,t,l:f['gate_targets'].update(critical_model_ready_fp_denominator=57)),
 ('trial_repetition',lambda m,f,t,l:f.update(trials_per_case=3)),
 ('extra_http',lambda m,f,t,l:f.update(expected_http_calls=126)),
 ('unknown_variant',lambda m,f,t,l:f.update(candidate_variant='qwen38-gguf-raw-unicode-v1')),
 ('dirty_source',lambda m,f,t,l:m['git'].update(dirty=True)),
 ('late_freeze',lambda m,f,t,l:f.update(frozen_at_utc='2026-09-21T00:00:00+00:00')),
]
tampering.extend([
 ('old_template_variant',lambda m,f,t,l:f.update(template_proof_variant=r.VARIANT)),
 ('official_failure_erased',lambda m,f,t,l:f['official_hf_equivalence'].update(status='PASS',id_match_count=20)),
 ('input_nfc_repair',lambda m,f,t,l:f.update(application_input_output_nfc_repair=True)),
 ('wrong_override_path',lambda m,f,t,l:l.update(chat_template_path='runtime/templates/wrong.jinja')),
 ('embedded_as_effective',lambda m,f,t,l:l.update(chat_template_sha256=r.ORIGINAL_TEMPLATE_SHA)),
 ('omitted_override',lambda m,f,t,l:f.update(chat_template_override={})),
])
rejected=[]
for label,mutate in tampering:
    values=deepcopy((manifest,freeze,runtime,launch));mutate(*values)
    try:r.validate_identity(*values,commit,expected_variant=r.VARIANT)
    except AssertionError:rejected.append(label)
    else:raise AssertionError('accepted_'+label)
assert r.CPU_SHA is None and r.HEADER_SHA is not None
assert r.PREPARATION_STATUS=='DRAFT_RUNTIME_FREEZE_BINDING_PENDING'
try:r.validate_evidence({}, {}, {}, lambda _: (_ for _ in ()).throw(AssertionError('must_not_load')), {})
except AssertionError as exc:assert str(exc)=='exaone_actual_evidence_binding_pending'
else:raise AssertionError('pending_runtime_bypass')
# Static check only: main cannot read saved results or data before evidence gate.
main=next(n for n in after.body if isinstance(n,ast.FunctionDef) and n.name=='main')
text=ast.get_source_segment(path.read_text(),main)
assert text.index('validate_evidence(')<text.index('result = load(')<text.index('archived = load(')
for arg in ('--freeze-sha256','--source-commit','--snapshot-sha256','--candidate-variant','--completed-run'):
    assert f'parser.add_argument("{arg}",' in text
assert 'torch' not in sys.modules
proof={'kind':'EXAONE45_REPLAY_METADATA_SYNTHETIC_CONTROLS','status':'PASS_RAW_VARIANT_METADATA_ONLY_RUNTIME_PENDING',
    'helper_sha256':r.digest(path),'selfcheck_sha256':r.digest(Path(__file__)),
    'gemma_helper_preserved_sha256':r.digest(prior),'core_functions_ast_exact':list(core_names),
    'identity_tampering_rejected':rejected,'evidence_gate_always_blocked':True,
    'actual_freeze_available':False,'actual_snapshot_created':False,'core_rows_replayed':0,
    'actual_run_results_read':False,'dataset_bodies_read':0,'historical_replays':0,
    'model_calls':0,'native_calls':0,'gpu_calls':0,'network_calls':0,
    'limitation':'Actual CPU/header/startup/resource and tokenizer contract bindings remain pending; no run or gate verdict.'}
dest=ROOT/'var/research/exaone45-replay-raw-metadata-draft-cpu-proof.json'
with dest.open('x') as f:json.dump(proof,f,indent=2);f.write('\n')
print(json.dumps({'status':proof['status'],'tampering_rejected':len(rejected),
    'proof_path':str(dest.relative_to(ROOT)),'proof_sha256':r.digest(dest),'helper_sha256':r.digest(path)}))
