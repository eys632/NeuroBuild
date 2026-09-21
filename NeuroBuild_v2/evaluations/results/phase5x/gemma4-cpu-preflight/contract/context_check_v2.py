"""Prepared 200-input length-only CPU proof. Root header/run authorization first.

No gold scoring, model generation, GPU or HTTP. Inputs pass through the actual
client fake opener and native template/tokenizer in memory only; report aggregates.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, importlib.util, json, os, re, resource, sys
ROOT=Path('/home/a202192020/NeuroBuild_v2');BASE=ROOT/'var/research/native-gemma4-contract'
VOCAB_SHA='ee4231de917a8d0165dda17400d231e65caa6f84c96b0a3251c3a7afd7556c56'
SPLITS={
 'exposed120':('evaluations/requirement_hardening_v1_exposed_regression.jsonl',120,'7e5b9a05932df7aafdbf683655b044b3e3b25cbffb4115d298e1490aecbc7a5b'),
 'v2_length80':('evaluations/requirement_hardening_v2_holdout.jsonl',80,'7416f05613b1490358672f3926770dbd8653e676577eeee6ba65f863b27cec40')}
SOURCE_PATHS=['src/neurobuild/infrastructure/local_model.py','src/neurobuild/application/requirement_generation.py',
 'src/neurobuild/application/requirements.py','prompts/requirement_generation_v2_v2.txt','schemas/requirement_generation_v2_decision_branches.schema.json']
SOURCE_SHA256={'src/neurobuild/infrastructure/local_model.py': '68c086f08bf2c3f5d6464f689baa8e628c8c33664397db06868c26cb6dd0d763', 'src/neurobuild/application/requirement_generation.py': 'fcba16f6adc906923859f3bcf4ae2f680e76716863a759582167cd9326f03198', 'src/neurobuild/application/requirements.py': 'a940f3952c0c4133ab51732f6abf76516d8ff66617470545222b52adfa49fb4a', 'prompts/requirement_generation_v2_v2.txt': '99d737124372836ba5f985fa6e5570afef693e769798844931f000fb21403cf6', 'schemas/requirement_generation_v2_decision_branches.schema.json': '36d42b9fa3d24f4a1bc1d14381110e36e8d89103b696bc83113be006b64934e2'}
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load():
 assert sha(BASE/'vocab_check_v2.py')==VOCAB_SHA
 spec=importlib.util.spec_from_file_location('gemma_vocab',BASE/'vocab_check_v2.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--header',required=True);parser.add_argument('--header-sha',required=True)
 parser.add_argument('--run-length-only-200',required=True,action='store_true');args=parser.parse_args()
 m=load();m.require(Path(sys.prefix)==ROOT/'.conda' and os.environ.get('CUDA_VISIBLE_DEVICES')=='','CPU_ENV')
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 for rel,h in SOURCE_SHA256.items():m.read_bound(ROOT/rel,h,2*1024**2)
 # Read/validate full header/model/ELF/template before any evaluation input.
 public,binary,build,fixture,model_stat=m.prepare(ROOT/args.header,args.header_sha)
 corpus=public.corpus();request=public.capture_request();groups={};native_checks=[]
 for name,(rel,count,digest) in SPLITS.items():
  raw=m.read_bound(ROOT/rel,digest,2*1024**2)
  rows=[json.loads(line) for line in raw.splitlines() if line.strip()];m.require(len(rows)==count,'SPLIT_COUNT')
  requests=[]
  for row in rows:
   m.require(type(row['input']) is str and type(row['context']) is dict,'SPLIT_INPUT_INVALID')
   requests.append(public.capture_request(row['input'],row['context'].get('axis_convention')))
  del rows,raw
  bundle={'request':request,'cases':corpus,'context_requests':requests,'max_output_tokens':768,'tokenizer_parity':fixture['tokenizer_parity']}
  code,native,bundle_sha=m.invoke(public,binary,bundle,model_stat)
  # Fixed metadata only if failed; no source/quote/token/exception text persisted.
  try:m.validate_pass(code,native,count)
  except ValueError:
   m.save(BASE/('context-failure-'+name+'.json'),{'kind':'GEMMA4_NATIVE_CONTEXT_FAILURE','status':'FAIL','split':name,'native':native,'exit_code':code})
   raise
  groups[name]={'dataset_sha256':digest,'input_count':count,'min_input_tokens':native['min_input_tokens'],
   'max_input_tokens':native['max_input_tokens'],'max_input_plus_output':native['max_input_plus_output'],'bundle_sha256':bundle_sha}
  native_checks.append(native)
  del requests,bundle
 for rel,h in SOURCE_SHA256.items():m.read_bound(ROOT/rel,h,2*1024**2)
 m.require(m.stat_key(m.MODEL.stat())==model_stat,'MODEL_CHANGED')
 token=native_checks[0]['resource_probe_token'];m.require(all(n['resource_probe_token']==token for n in native_checks),'TOKEN_ID_CHANGED')
 details={'kind':'GEMMA4_NATIVE_VOCAB_CONTEXT_CPU_PROOF','status':'PASS','at_utc':datetime.now(timezone.utc).isoformat(),
  'model_id':m.MODEL_ID,'revision':m.REVISION,'gguf_sha256':m.MODEL_SHA,'header_sha256':args.header_sha,
  'binary_sha256':m.sha(binary),'cpu_build_report_sha256':m.sha(BASE/'build-v2.json'),'helper_sha256':sha(Path(__file__)),
  'splits':groups,'native_checks':native_checks,'model_inference_calls':0,'gpu_or_http_calls':0,'vocab_only_model_open_count':2,
  'input_bodies_gold_token_ids_saved':False,'gold_fields_scored':False,'source_sha256':SOURCE_SHA256}
 m.save(BASE/'vocab-context-v2-proof.json',details)
 proof={'kind':'GEMMA4_NATIVE_CONTRACT_CPU_PROOF','status':'PASS','at_utc':datetime.now(timezone.utc).isoformat(),
  'model_id':m.MODEL_ID,'revision':m.REVISION,'gguf_sha256':m.MODEL_SHA,'header_sha256':args.header_sha,
  'source_pin':build['source_pin'],'cpu_binary_sha256':sha(binary),'cpu_cpp_source_sha256':sha(BASE/'validator_v2.cpp'),
  'cpu_build_report_sha256':sha(BASE/'build-v2.json'),'template_sha256':public.PINS[public.TEMPLATE],
  'tokenizer_json_sha256':fixture['tokenizer_sha256'],'protocol':'llama_cpp_json_schema','sampling_profile':'gemma4_nonthinking_llama_cpp',
  'enable_thinking':False,'application_input_output_nfc_repair':False,'model_inference_calls':0,'gpu_or_http_calls':0,
  'max_output_tokens':768,'max_context_tokens':4096,'splits':groups,
  'official_tokenizer_parity':{'status':'PASS','case_count':20,'id_match_count':20,'native_original_roundtrip_count':20},
  'resource_probe_token':dict(token,native_token_count=1,native_roundtrip=True),
  'proof_refs':{key:{'path':str((BASE/name).relative_to(ROOT)),'sha256':sha(BASE/name)} for key,name in
   [('public_contract','public-proof.json'),('vocab_context','vocab-context-v2-proof.json'),('tokenizer_fixture','tokenizer-fixture.json')]},
  'source_sha256':SOURCE_SHA256,
  'normalization_limitation':{'official_hf_literal_u2581_raw_roundtrip':False,'reference':'tokenizer_fixture.normalization_witness',
   'global_unicode_roundtrip_guarantee':False,'input_output_repair':False},
  'limits':['Twenty public probes do not prove all Unicode or all token sequences equivalent.',
   'Official metadata normalization loses literal U+2581; witness retained separately; no application repair.',
   'CPU vocab-only context is not inference/VRAM/semantic acceptance. V2 length-only processing is not scoring or hidden-blinding.']}
 m.save(BASE/'final-cpu-proof.json',proof)
 print(json.dumps({'status':'PASS','proof_path':str((BASE/'final-cpu-proof.json').relative_to(ROOT)),
  'sha256':sha(BASE/'final-cpu-proof.json'),'splits':{k:{a:b for a,b in v.items() if a not in ('bundle_sha256','dataset_sha256')} for k,v in groups.items()},'model_inference_calls':0}))
if __name__=='__main__':
 try:main()
 except Exception as error:
  code=str(error) if type(error) is ValueError and re.fullmatch('[A-Z0-9_]+',str(error)) else 'INPUT_OR_IO_ERROR'
  print(json.dumps({'status':'FAIL','code':code,'error_type':type(error).__name__}));raise SystemExit(1)
