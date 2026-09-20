"""Public literal-U+2581 witness; only invoke after root full-header GO.

The original 20-case fixture is unchanged. This separate CPU invocation tests
one explicit normalization witness against unchanged official token IDs. A
native roundtrip failure is preserved as FAIL, never turned into parity PASS.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,importlib.util,json,re,sys
ROOT=Path('/home/a202192020/NeuroBuild_v2');BASE=ROOT/'var/research/native-gemma4-contract'
VOCAB_SHA='4a9b873df6a8a28d5123210b15215840a6f6dcb66f88d20a4923fe34121ef6c1'
CPP_SHA='f9d05d6164ddae3c2550933cda1ad991259929caec370a354a05b16cd3459366'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def classify(code,native,cpp):
 lines=cpp.splitlines()
 id_guard=lines.index('                ensure(!parity_mismatch_observed);')+1
 roundtrip_guard=lines.index('                ensure(parity_native_roundtrip_cases == parity.size());')+1
 assert roundtrip_guard==id_guard+1
 assert native['kind']=='GEMMA4_NATIVE_CONTRACT_CPU_PREFLIGHT'
 if code==1 and native['status']=='FAIL' and native.get('stage')==101 and native.get('check_line')==roundtrip_guard:
  # With one fixture, the unchanged ID-mismatch guard immediately before this
  # executed successfully. This line's failure proves raw roundtrip != original.
  # Do not label the whole witness PASS or waive the failing roundtrip assertion.
  return {'status':'FAIL_NATIVE_ORIGINAL_ROUNDTRIP','official_ids_match_native':True,
   'native_original_roundtrip':False,'evidence':'Pinned C++ one-case control flow: ID mismatch guard passed, immediately following native raw-roundtrip guard failed',
   'native_check_line':roundtrip_guard,'classification_scope':'One explicit public witness; no universal tokenizer equivalence claim'}
 if code==1 and native['status']=='FAIL' and native.get('parity_cases_checked')==1:
  return {'status':'FAIL_NATIVE_ID_PARITY','official_ids_match_native':False,
   'native_original_roundtrip':native['parity_native_roundtrip_cases']==1,
   'native_check_line':native.get('check_line'),'classification_scope':'One explicit public witness'}
 if code==0 and native['status']=='PASS':
  return {'status':'PASS_ONE_PUBLIC_WITNESS','official_ids_match_native':True,
   'native_original_roundtrip':True,'classification_scope':'One explicit public witness'}
 return {'status':'FAIL_OTHER_CPU_CHECK','official_ids_match_native':None,'native_original_roundtrip':None,
  'classification_scope':'Failure occurred outside the resolved one-case parity checks; no inference about normalization'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--header',required=True);p.add_argument('--header-sha',required=True);args=p.parse_args()
 assert sha(BASE/'vocab_check.py')==VOCAB_SHA and sha(BASE/'validator.cpp')==CPP_SHA
 spec=importlib.util.spec_from_file_location('gemma_witness_vocab',BASE/'vocab_check.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 public,binary,build,fixture,model_stat=m.prepare(ROOT/args.header,args.header_sha)
 witness=fixture['normalization_witness'];m.require(witness['kind']=='PUBLIC_LITERAL_U2581' and witness['original_roundtrip'] is False,'EXPECTED_OFFICIAL_WITNESS_CHANGED')
 request=public.capture_request();entry={k:witness[k] for k in ['text','expected_token_ids']}
 bundle={'request':request,'cases':public.corpus(),'context_requests':[request],'max_output_tokens':768,'tokenizer_parity':[entry]}
 code,native,bundle_sha=m.invoke(public,binary,bundle,model_stat)
 diagnosis=classify(code,native,(BASE/'validator.cpp').read_text())
 result={'kind':'GEMMA4_NATIVE_PUBLIC_NORMALIZATION_WITNESS','status':diagnosis['status'],
  'at_utc':datetime.now(timezone.utc).isoformat(),'model_id':m.MODEL_ID,'revision':m.REVISION,
  'gguf_sha256':m.MODEL_SHA,'header_sha256':args.header_sha,'binary_sha256':sha(binary),'cpp_sha256':CPP_SHA,
  'fixture_sha256':sha(BASE/'tokenizer-fixture.json'),'helper_sha256':sha(Path(__file__)),
  'official_hf_original_roundtrip':False,'diagnosis':diagnosis,'native':native,'exit_code':code,
  'bundle_sha256':bundle_sha,'public_case_count':1,'original_public20_unchanged':True,
  'input_output_repair':False,'model_inference_calls':0,'gpu_or_http_calls':0,
  'limits':['This separate witness never changes the original 20-case reference or quality gates.',
   'An observed roundtrip failure is retained; it does not prove application quotes can be copied for all Unicode.']}
 m.save(BASE/'normalization-witness-proof.json',result)
 print(json.dumps({'status':result['status'],'diagnosis':diagnosis,'report':str((BASE/'normalization-witness-proof.json').relative_to(ROOT)),
  'sha256':sha(BASE/'normalization-witness-proof.json'),'model_inference_calls':0}))
 # Completed diagnostic evidence can legitimately describe a failing witness.
 return 0 if diagnosis['status'] in ('FAIL_NATIVE_ORIGINAL_ROUNDTRIP','FAIL_NATIVE_ID_PARITY','PASS_ONE_PUBLIC_WITNESS') else 1
if __name__=='__main__':
 try:raise SystemExit(main())
 except Exception as error:
  code=str(error) if type(error) is ValueError and re.fullmatch('[A-Z0-9_]+',str(error)) else 'INPUT_OR_IO_ERROR'
  print(json.dumps({'status':'FAIL','code':code,'error_type':type(error).__name__}));raise SystemExit(1)
