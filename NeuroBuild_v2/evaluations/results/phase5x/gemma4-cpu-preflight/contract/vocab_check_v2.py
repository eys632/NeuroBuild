"""Prepared public GGUF vocab-only check. Run only after root header audit go.

No dataset/body/model inference/GPU/network; full GGUF bytes are hash-only read,
then the CPU binary loads vocabulary metadata without tensors or context.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, importlib.util, json, os, re, resource, stat, subprocess, sys
ROOT=Path('/home/a202192020/NeuroBuild_v2');BASE=ROOT/'var/research/native-gemma4-contract'
MODEL_ID='google/gemma-4-31B-it-qat-q4_0-gguf';REVISION='59dde24573e7e61570dba08b18a2e1fe246955ed'
MODEL=ROOT/'var/models/google--gemma-4-31B-it-qat-q4_0-gguf'/REVISION/'gemma-4-31B_q4_0-it.gguf'
MODEL_SHA='179cfb99212709597eae5929112cfca677e1bbf566178b479ae1da0c4772874b';MODEL_BYTES=17651001568
PINS={'public_check_v2.py':'1eed1877142a1382e46d0832513b8b3675a73937885235ee951e4158a685e013','build-v2.json':'1b6dce0e85790b267ec2514da8c81158c76b9d01a27aa6c2e584787a160e67ee',
 'public-proof.json':'d7cd7032f019af566e2d7484afed85f9dab95fcbc0da06fc2a602cf5b7a76334',
 'tokenizer-fixture.json':'42b2a10fdc4ebc066acb878a5a9e0c9e407affe0b91bc7d32145d8d360dc13e5'}
SAFE_ENV={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','LC_ALL':'C.UTF-8','CUDA_VISIBLE_DEVICES':'',
 'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','PYTHONNOUSERSITE':'1'}
EXEC_BOOTSTRAP='''import ctypes,os,resource,signal,sys
expected=int(sys.argv[1])
if os.getppid()!=expected:raise SystemExit(2)
if ctypes.CDLL(None,use_errno=True).prctl(1,signal.SIGKILL,0,0,0)!=0:raise SystemExit(2)
if os.getppid()!=expected:os.kill(os.getpid(),signal.SIGKILL)
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
os.execve(sys.argv[2],sys.argv[2:],dict(os.environ))
'''
def require(ok,code):
 if not ok:raise ValueError(code)
def sha(path):
 with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def own(path):
 require(path.is_relative_to(ROOT) and '..' not in path.parts,'OUTSIDE_PROJECT')
 for p in (path,*path.parents):
  info=p.lstat();require(info.st_uid==os.getuid() and not stat.S_ISLNK(info.st_mode),'UNSAFE_PATH')
  if p==ROOT:break
 require(path.is_file() and path.stat().st_nlink==1,'UNSAFE_FILE')
def read_bound(path,digest,cap):
 own(path);require(path.stat().st_size<=cap,'INPUT_TOO_LARGE');data=path.read_bytes()
 require(hashlib.sha256(data).hexdigest()==digest,'INPUT_HASH_CHANGED');return data
def stat_key(s):return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
def prepare(header_path,header_sha):
 require(os.environ.get('CUDA_VISIBLE_DEVICES')=='' and Path(sys.prefix)==ROOT/'.conda','CPU_ENV_REQUIRED')
 require(header_path.is_relative_to(ROOT/'var/reports'),'HEADER_PATH_INVALID')
 header=json.loads(read_bound(header_path,header_sha,2*1024**2))
 require(header['kind']=='GGUF_HEADER_AUDIT' and header['status']=='PASS' and header['model_id']==MODEL_ID
  and header['revision']==REVISION and header['file_sha256']==MODEL_SHA and header['file_bytes']==MODEL_BYTES
  and header['model_path']==str(MODEL.relative_to(ROOT)) and header['gpu_or_native_execution'] is False,'HEADER_REQUIRED')
 for name,h in PINS.items():read_bound(BASE/name,h,2*1024**2)
 spec=importlib.util.spec_from_file_location('gemma_public',BASE/'public_check_v2.py');public=importlib.util.module_from_spec(spec);spec.loader.exec_module(public)
 for p,h in public.PINS.items():read_bound(p,h,256*1024)
 binary,build=public.inspect_cpu_binary()
 own(MODEL)
 with os.fdopen(os.open(MODEL,os.O_RDONLY|os.O_NOFOLLOW),'rb') as f:
  before=os.fstat(f.fileno());require(before.st_size==MODEL_BYTES,'MODEL_SIZE_CHANGED')
  require(hashlib.file_digest(f,'sha256').hexdigest()==MODEL_SHA,'MODEL_HASH_CHANGED')
  require(stat_key(os.fstat(f.fileno()))==stat_key(before),'MODEL_CHANGED_DURING_HASH')
 require(stat_key(MODEL.stat())==stat_key(before),'MODEL_PATH_CHANGED')
 fixture=json.loads((BASE/'tokenizer-fixture.json').read_text())
 require(fixture['case_count']==20 and fixture['official_original_roundtrip_count']==20,'FIXTURE_INVALID')
 return public,binary,build,fixture,stat_key(before)
def invoke(public,binary,bundle,model_stat):
 own(MODEL);require(stat_key(MODEL.stat())==model_stat,'MODEL_CHANGED_BEFORE_CPU')
 raw=json.dumps(bundle,ensure_ascii=False).encode();require(len(raw)<=16*1024**2,'BUNDLE_TOO_LARGE')
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 command=[str(ROOT/'.conda/bin/python'),'-I','-B','-c',EXEC_BOOTSTRAP,str(os.getpid()),str(binary),str(public.TEMPLATE),str(public.SCHEMA),str(MODEL)]
 p=subprocess.Popen(command,cwd=ROOT,env=SAFE_ENV,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
 try:stdout,stderr=p.communicate(raw,timeout=180)
 except BaseException:
  import signal
  os.killpg(p.pid,signal.SIGKILL);p.wait();raise
 require(not stderr and len(stdout)<65536,'UNSAFE_CPU_OUTPUT')
 native=json.loads(stdout);require(type(native) is dict and native.get('kind')=='GEMMA4_NATIVE_CONTRACT_CPU_PREFLIGHT','INVALID_CPU_KIND')
 allowed={'status','kind','code','stage','check_line','discarded_stderr_bytes','schema_cases_accepted','schema_cases_rejected',
 'native_final_content_exact_cases','native_grammar_generation_prompt_prefilled','native_grammar_prefill_bytes','core_dump_limit_zero',
 'native_sampling_schema_binding','native_request_grammar_nonempty','grammar_lazy','grammar_triggers','native_fence_rejection_cases',
 'artificial_thought_split_cases','final_json_bytes_unchanged','native_grammar_bytes','standalone_grammar_bytes','native_request_prompt_bytes',
 'model_context_created','backend_init_called','weight_tensors_loaded','native_tokenization','native_vocab_grammar_cases_accepted',
 'native_vocab_grammar_cases_rejected','native_vocab_grammar_eog_checked','tokenizer_metadata_parity','tokenizer_metadata_parity_cases',
 'tokenizer_native_roundtrip_cases','tokenizer_expected_roundtrip_cases','resource_probe_token','embedded_template_exact_match',
 'native_embedded_vs_external_effective_tokens_match','native_embedded_vs_external_grammar_match','native_generation_prompt_byte_match','native_bos_template_prefix_removed','native_bos_added_by_tokenizer','metadata_prompt_extra_bos_bytes','input_count','min_input_tokens','max_input_tokens','max_input_plus_output',
 'parity_native_tokens','parity_expected_tokens','parity_native_roundtrip_original','parity_expected_roundtrip_original',
 'parity_cases_checked','parity_id_matches','parity_id_mismatches','parity_mismatch_mask','parity_native_roundtrip_cases','parity_expected_roundtrip_cases'}
 require(set(native)<=allowed,'UNKNOWN_CPU_OUTPUT_FIELDS')
 require(all(type(v) in (str,int,bool) for k,v in native.items() if k!='resource_probe_token'),'INVALID_CPU_VALUES')
 if 'resource_probe_token' in native:
  token=native['resource_probe_token'];require(set(token)=={'text','token_id'} and token['text']==' ' and type(token['token_id']) is int,'INVALID_PUBLIC_TOKEN')
 require(stat_key(MODEL.stat())==model_stat,'MODEL_CHANGED_AFTER_CPU')
 return p.returncode,native,hashlib.sha256(raw).hexdigest()
def validate_pass(code,value,count):
 require(code==0 and value['status']=='PASS','CPU_PROBE_FAILED')
 expected={'schema_cases_accepted':10,'schema_cases_rejected':20,'native_final_content_exact_cases':10,
 'native_vocab_grammar_cases_accepted':10,'native_vocab_grammar_cases_rejected':20,'tokenizer_metadata_parity_cases':20,
 'tokenizer_native_roundtrip_cases':20,'tokenizer_expected_roundtrip_cases':20,'native_fence_rejection_cases':4,
 'artificial_thought_split_cases':1,'metadata_prompt_extra_bos_bytes':5,'grammar_triggers':1,'discarded_stderr_bytes':0,'input_count':count}
 for key,v in expected.items():require(type(value[key]) is int and value[key]==v,'CPU_COUNT_MISMATCH')
 for key in ['native_grammar_generation_prompt_prefilled','core_dump_limit_zero','native_sampling_schema_binding',
 'native_request_grammar_nonempty','final_json_bytes_unchanged','native_vocab_grammar_eog_checked',
 'embedded_template_exact_match','native_embedded_vs_external_effective_tokens_match','native_embedded_vs_external_grammar_match','native_generation_prompt_byte_match','native_bos_template_prefix_removed','native_bos_added_by_tokenizer']:
  require(value[key] is True,'CPU_INVARIANT_FALSE')
 for key in ['grammar_lazy','model_context_created','backend_init_called','weight_tensors_loaded']:require(value[key] is False,'CPU_SCOPE_VIOLATION')
 require(value['tokenizer_metadata_parity']=='PASS' and value['native_tokenization']=='PASS_VOCAB_ONLY','CPU_PARITY_FAILED')
 require(0<value['min_input_tokens']<=value['max_input_tokens'] and value['max_input_tokens']+768==value['max_input_plus_output']<=4096,'CPU_CONTEXT_LIMIT')
def save(path,result):
 require(path.parent==BASE and not path.exists() and not path.is_symlink(),'OUTPUT_EXISTS_OR_SCOPE')
 with path.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--header',required=True);parser.add_argument('--header-sha',required=True)
 args=parser.parse_args();header=ROOT/args.header
 public,binary,build,fixture,model_stat=prepare(header,args.header_sha)
 request=public.capture_request();bundle={'request':request,'cases':public.corpus(),'context_requests':[request],
 'max_output_tokens':768,'tokenizer_parity':fixture['tokenizer_parity']}
 code,native,bundle_sha=invoke(public,binary,bundle,model_stat)
 validation_error=None
 try:validate_pass(code,native,1)
 except ValueError as e:validation_error=str(e)
 result={'kind':'GEMMA4_NATIVE_PUBLIC_VOCAB_CPU_PROOF','status':'PASS' if validation_error is None else 'FAIL',
 'at_utc':datetime.now(timezone.utc).isoformat(),'model_id':MODEL_ID,'revision':REVISION,'gguf_sha256':MODEL_SHA,
 'header_sha256':args.header_sha,'binary_sha256':sha(binary),'build_report_sha256':sha(BASE/'build-v2.json'),
 'public_contract_sha256':sha(BASE/'public-proof.json'),'tokenizer_fixture_sha256':sha(BASE/'tokenizer-fixture.json'),
 'helper_sha256':sha(Path(__file__)),'model_inference_calls':0,'gpu_or_http_calls':0,'native':native,'exit_code':code,
 'bundle_sha256':bundle_sha,'validation_error':validation_error,'scope':'Public30 schema cases + public20 tokenizer parity + one public input length; no evaluation bodies'}
 save(BASE/'public-vocab-v2-proof.json',result)
 print(json.dumps({'status':result['status'],'native':native,'path':str((BASE/'public-vocab-v2-proof.json').relative_to(ROOT)),'sha256':sha(BASE/'public-vocab-v2-proof.json')}))
 validate_pass(code,native,1)
if __name__=='__main__':
 try:main()
 except Exception as error:
  code=str(error) if type(error) is ValueError and re.fullmatch('[A-Z0-9_]+',str(error)) else 'INPUT_OR_IO_ERROR'
  print(json.dumps({'status':'FAIL','code':code,'error_type':type(error).__name__}));raise SystemExit(1)
