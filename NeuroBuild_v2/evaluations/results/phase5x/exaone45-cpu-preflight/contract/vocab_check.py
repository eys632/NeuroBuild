"""Audited GGUF, public-only CPU vocabulary probe; no tensor/context/inference.

Observe all twenty official comparisons. Mismatches remain FAIL, never repaired.
The metadata-only proofs and official fixture are immutable inputs.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,importlib.util,json,os,re,resource,stat,subprocess,sys,signal
ROOT=Path('/home/a202192020/NeuroBuild_v2');BASE=ROOT/'var/research/native-exaone45-contract'
MODEL_ID='LGAI-EXAONE/EXAONE-4.5-33B-GGUF';REVISION='0e969634ef24db05151b435970297a6dee634b7e'
MODEL=ROOT/'var/models/LGAI-EXAONE--EXAONE-4.5-33B-GGUF'/REVISION/'EXAONE-4.5-33B-Q4_K_M.gguf'
MODEL_SHA='5ba3839b67dcee5618ea7b2206cedc8f9e2ec90fbcec3c95a8cc8b33967f6baf';MODEL_BYTES=20047839424
HEADER=ROOT/'var/reports/exaone45-gguf-header-v2.json';HEADER_SHA='fb5260c6e1e3356741f7728e4077f771763ea39affd77e8ac9772e417aa70c12'
PINS={'public_check_v3.py':'803767732db366774600f2521eb39db475e8c1d587ba28e9680a0be3a47deb74',
 'public-proof-v3.json':'fc7109fe4e9fbbe4a619ad16dc701cda01a4976ec8bd53d726aeb09f34f39408',
 'official-tokenizer-fixture.json':'49b40b3390cba92f3088c22606632348ba261e69ea0b385b74aa9126be8c46cb'}
SAFE_ENV={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','LC_ALL':'C.UTF-8','CUDA_VISIBLE_DEVICES':'','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','PYTHONNOUSERSITE':'1'}
BOOTSTRAP='''import ctypes,os,resource,signal,sys
parent=int(sys.argv[1])
if os.getppid()!=parent:raise SystemExit(91)
if ctypes.CDLL(None,use_errno=True).prctl(1,signal.SIGKILL,0,0,0)!=0:raise SystemExit(91)
if os.getppid()!=parent:os.kill(os.getpid(),signal.SIGKILL)
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
os.execve(sys.argv[2],sys.argv[2:],dict(os.environ))
'''
def require(value,code):
 if not value:raise ValueError(code)
def sha(path):
 with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def own(path):
 require(path.is_relative_to(ROOT) and '..' not in path.parts,'OUTSIDE_PROJECT')
 for p in (path,*path.parents):
  s=p.lstat();require(s.st_uid==os.getuid() and not stat.S_ISLNK(s.st_mode),'UNSAFE_PATH')
  if p==ROOT:break
 require(path.is_file() and path.stat().st_nlink==1,'UNSAFE_FILE')
def stat_key(s):return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
def read_bound(path,digest,cap):
 own(path);require(path.stat().st_size<=cap,'INPUT_TOO_LARGE');data=path.read_bytes()
 require(hashlib.sha256(data).hexdigest()==digest,'INPUT_HASH_CHANGED');return data
def prepare():
 require(len(sys.argv)==1 and Path(sys.prefix)==ROOT/'.conda' and os.environ.get('CUDA_VISIBLE_DEVICES')=='','CPU_ENV_REQUIRED')
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 header=json.loads(read_bound(HEADER,HEADER_SHA,2*1024**2))
 require(header['kind']=='GGUF_HEADER_AUDIT' and header['status']=='PASS' and header['model_id']==MODEL_ID
  and header['revision']==REVISION and header['file_sha256']==MODEL_SHA and header['file_bytes']==MODEL_BYTES
  and header['model_path']==str(MODEL.relative_to(ROOT)) and header['gpu_or_native_execution'] is False,'HEADER_REQUIRED')
 for name,h in PINS.items():read_bound(BASE/name,h,2*1024**2)
 s=importlib.util.spec_from_file_location('exaone_public_v3',BASE/'public_check_v3.py');public=importlib.util.module_from_spec(s);s.loader.exec_module(public)
 for p,h in public.PINS.items():read_bound(p,h,256*1024)
 public.BUILD_REPORT=BASE/'build-v4.json' # Explicit new CPU TU; old public helper stays immutable.
 binary,build=public.inspect_cpu_binary()
 own(MODEL)
 with os.fdopen(os.open(MODEL,os.O_RDONLY|os.O_NOFOLLOW),'rb') as f:
  before=os.fstat(f.fileno());require(before.st_size==MODEL_BYTES,'MODEL_SIZE_CHANGED')
  require(hashlib.file_digest(f,'sha256').hexdigest()==MODEL_SHA,'MODEL_HASH_CHANGED')
  require(stat_key(os.fstat(f.fileno()))==stat_key(before),'MODEL_CHANGED_DURING_HASH')
 require(stat_key(MODEL.stat())==stat_key(before),'MODEL_PATH_CHANGED')
 fixture=json.loads((BASE/'official-tokenizer-fixture.json').read_text())
 require(fixture['case_count']==20 and fixture['official_raw_roundtrip_count']==18
  and fixture['official_raw_mismatch_indices']==[11,12],'OFFICIAL_REFERENCE_CHANGED')
 return public,binary,build,fixture,stat_key(before)
def invoke(public,binary,bundle,model_stat):
 require(stat_key(MODEL.stat())==model_stat,'MODEL_CHANGED_BEFORE_CPU')
 raw=json.dumps(bundle,ensure_ascii=False).encode();require(len(raw)<=16*1024**2,'BUNDLE_TOO_LARGE')
 args=[str(ROOT/'.conda/bin/python'),'-I','-B','-c',BOOTSTRAP,str(os.getpid()),str(binary),str(public.TEMPLATE),str(public.SCHEMA),str(MODEL)]
 child=subprocess.Popen(args,cwd=ROOT,env=SAFE_ENV,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
 try:stdout,stderr=child.communicate(raw,timeout=180)
 except BaseException:
  os.killpg(child.pid,signal.SIGKILL);child.wait();raise
 require(not stderr and len(stdout)<65536,'UNSAFE_CPU_OUTPUT')
 native=json.loads(stdout)
 require(type(native) is dict and native.get('kind')=='EXAONE45_NATIVE_PUBLIC_CONTRACT_CPU_PREFLIGHT','CPU_KIND_CHANGED')
 allowed=set(json.loads((BASE/'public-proof-v3.json').read_text())['native']) | {
  'code','stage','check_line','embedded_original_template_exact_match','effective_override_vocab_render_exact',
  'native_vocab_grammar_generation_prompt_exact','native_vocab_bos_id','native_vocab_eos_id','native_vocab_add_bos','native_vocab_add_eos',
  'native_vocab_grammar_cases_accepted','native_vocab_grammar_cases_rejected','native_vocab_grammar_eog_checked',
  'tokenizer_cases_checked','tokenizer_id_match_count','tokenizer_id_mismatch_mask','tokenizer_native_raw_roundtrip_count',
  'tokenizer_native_raw_mismatch_mask','tokenizer_reference_ids_raw_roundtrip_count','tokenizer_reference_parity',
  'resource_probe_token_id','resource_probe_token_count','resource_probe_raw_roundtrip','public_input_tokens',
  'public_input_plus_output','official_reference_gate_pass'}
 require(set(native)<=allowed,'CPU_UNKNOWN_OUTPUT_FIELDS')
 require(all(type(v) in (str,int,bool) for v in native.values()),'CPU_BODY_OUTPUT_FORBIDDEN')
 require(stat_key(MODEL.stat())==model_stat and sha(binary)==json.loads(public.BUILD_REPORT.read_text())['binary_sha256'],'MODEL_OR_BINARY_CHANGED')
 return child.returncode,native,hashlib.sha256(raw).hexdigest()
def main():
 report=BASE/'public-vocab-proof.json';require(not report.exists() and not report.is_symlink(),'OUTPUT_EXISTS')
 public,binary,build,fixture,model_stat=prepare()
 request=public.capture_request();cases,version=public.official_reference(request)
 bundle={'request':request,'cases':public.corpus(),'original_template':public.ORIGINAL_TEMPLATE.read_text(),
  'template_cases':cases,'tokenizer_parity':fixture['tokenizer_parity']}
 code,native,bundle_sha=invoke(public,binary,bundle,model_stat)
 mismatch_mask=native.get('tokenizer_id_mismatch_mask',0)
 mismatch_indices=[i for i in range(20) if mismatch_mask&(1<<i)]
 observed=native.get('tokenizer_cases_checked')==20
 passed=code==0 and native['status']=='PASS' and observed and native.get('tokenizer_id_match_count')==20 and native.get('tokenizer_native_raw_roundtrip_count')==20
 result={'kind':'EXAONE45_NATIVE_PUBLIC_VOCAB_CPU_PROOF','status':'PASS' if passed else 'FAIL',
  'at_utc':datetime.now(timezone.utc).isoformat(),'runtime_variant':'exaone45-gguf-continue-free-korean-v1',
  'model_id':MODEL_ID,'revision':REVISION,'gguf_sha256':MODEL_SHA,'header_sha256':HEADER_SHA,
  'source_pin':build['source_pin'],'binary_sha256':sha(binary),'build_report_sha256':sha(public.BUILD_REPORT),
  'public_contract_sha256':PINS['public-proof-v3.json'],'tokenizer_fixture_sha256':PINS['official-tokenizer-fixture.json'],
  'helper_sha256':sha(Path(__file__)),'original_template_sha256':sha(public.ORIGINAL_TEMPLATE),'effective_template_sha256':sha(public.TEMPLATE),
  'official_reference_observed_all20':observed,'official_reference_native_id_mismatch_indices':mismatch_indices,
  'official_metadata_raw_roundtrip_count':18,'native':native,'exit_code':code,'bundle_sha256':bundle_sha,
  'jinja2_reference_version':version,'model_inference_calls':0,'http_calls':0,'gpu_calls':0,
  'gguf_load_mode':'VOCAB_ONLY_NO_ALLOC_NO_TENSORS_NO_CONTEXT_EMPTY_DEVICES','application_input_output_nfc_repair':False,
  'eligibility':'PENDING_UNICODE_CONTRACT_DECISION','scope':'Public30 grammar,20 official tokenizer comparisons,18 renders,one public prompt length; no evaluation bodies/results.'}
 with report.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps({'status':result['status'],'native':native,'mismatch_indices':mismatch_indices,'report':str(report.relative_to(ROOT)),'sha256':sha(report)}))
 return 0 if passed else 1
if __name__=='__main__':
 try:raise SystemExit(main())
 except Exception as e:
  print(json.dumps({'status':'FAIL','error_type':type(e).__name__,'code':str(e) if isinstance(e,ValueError) and re.fullmatch('[A-Z0-9_]+',str(e)) else 'INPUT_OR_IO_ERROR'}));raise SystemExit(1)
