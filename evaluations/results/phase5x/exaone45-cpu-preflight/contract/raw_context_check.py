"""Audited GGUF, raw-reference and length-only CPU vocabulary probe; no tensor/context/inference.

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
 'official-tokenizer-fixture.json':'49b40b3390cba92f3088c22606632348ba261e69ea0b385b74aa9126be8c46cb',
 'public-vocab-proof.json':'66442010a8c4ee9f5f554bfea34273fd80659d50d42b9acdba6b2879400285d1',
 'raw-reference-diagnostic.json':'9a379ccf7cab7c85c23582c45f77c6b4ec481a9bb1469009564dba0fe894bf2c'}
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
 public.BUILD_REPORT=BASE/'build-v5.json' # Explicit new CPU TU; old public helper stays immutable.
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
  'public_input_plus_output','reference_kind','reference_gate_pass','official_hf_equivalence','input_count',
 'min_input_tokens','max_input_tokens','max_input_plus_output','all_context_system_user_bytes_exact'}
 require(set(native)<=allowed,'CPU_UNKNOWN_OUTPUT_FIELDS')
 require(all(type(v) in (str,int,bool) for v in native.values()),'CPU_BODY_OUTPUT_FORBIDDEN')
 require(stat_key(MODEL.stat())==model_stat and sha(binary)==json.loads(public.BUILD_REPORT.read_text())['binary_sha256'],'MODEL_OR_BINARY_CHANGED')
 return child.returncode,native,hashlib.sha256(raw).hexdigest()
SPLITS={
 'exposed120':('evaluations/requirement_hardening_v1_exposed_regression.jsonl',120,'7e5b9a05932df7aafdbf683655b044b3e3b25cbffb4115d298e1490aecbc7a5b'),
 'v2_length80':('evaluations/requirement_hardening_v2_holdout.jsonl',80,'7416f05613b1490358672f3926770dbd8653e676577eeee6ba65f863b27cec40')}
SOURCE_SHA256={
 'src/neurobuild/infrastructure/local_model.py':'48276a8f9cb7a2a818a9f12e7f86b2b53f525a37de61a1be70fe73648f07c151',
 'src/neurobuild/application/requirement_generation.py':'fcba16f6adc906923859f3bcf4ae2f680e76716863a759582167cd9326f03198',
 'src/neurobuild/application/requirements.py':'a940f3952c0c4133ab51732f6abf76516d8ff66617470545222b52adfa49fb4a',
 'prompts/requirement_generation_v2_v2.txt':'99d737124372836ba5f985fa6e5570afef693e769798844931f000fb21403cf6',
 'schemas/requirement_generation_v2_decision_branches.schema.json':'36d42b9fa3d24f4a1bc1d14381110e36e8d89103b696bc83113be006b64934e2'}
VARIANT='exaone45-gguf-continue-free-raw-unicode-korean-v1'
def save(name,value):
 p=BASE/name;require(not p.exists() and not p.is_symlink(),'OUTPUT_EXISTS')
 with p.open('x') as f:json.dump(value,f,indent=2);f.write('\n')
 return {'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
def validate_raw(code,native,count):
 require(code==0 and native.get('status')=='PASS','RAW_CPU_FAILED')
 expected={'public_template_reference_cases':18,'original_template_native_mismatches':7,'original_native_prompt_bytes':177,
  'schema_cases_accepted':10,'schema_cases_rejected':20,'native_final_content_exact_cases':20,
  'native_protocol_rejection_cases':4,'artificial_thought_split_cases':1,'grammar_triggers':0,
  'native_vocab_grammar_cases_accepted':20,'native_vocab_grammar_cases_rejected':40,
  'tokenizer_cases_checked':20,'tokenizer_id_match_count':20,'tokenizer_id_mismatch_mask':0,
  'tokenizer_native_raw_roundtrip_count':20,'tokenizer_native_raw_mismatch_mask':0,
  'tokenizer_reference_ids_raw_roundtrip_count':20,'resource_probe_token_count':1,'discarded_stderr_bytes':0,'input_count':count}
 for key,v in expected.items():require(type(native.get(key)) is int and native[key]==v,'RAW_CPU_COUNT')
 for key in ['derived_native_system_and_user_exact','derived_native_prompt_equals_official_reference',
  'native_grammar_generation_prompt_prefilled','core_dump_limit_zero','native_sampling_schema_binding','native_request_grammar_nonempty',
  'final_json_bytes_unchanged','embedded_original_template_exact_match','effective_override_vocab_render_exact',
  'native_vocab_grammar_generation_prompt_exact','native_vocab_grammar_eog_checked','resource_probe_raw_roundtrip','reference_gate_pass','all_context_system_user_bytes_exact']:
  require(native.get(key) is True,'RAW_CPU_INVARIANT')
 for key in ['model_context_created','backend_init_called','weight_tensors_loaded','grammar_lazy','native_vocab_add_bos','native_vocab_add_eos']:
  require(native.get(key) is False,'RAW_CPU_SCOPE')
 require(native.get('reference_kind')=='derived_hf_nfc_disabled' and native.get('official_hf_equivalence')=='NOT_ASSERTED_BY_DERIVED_REFERENCE','REFERENCE_KIND')
 require('official_reference_gate_pass' not in native and native.get('tokenizer_reference_parity')=='PASS','OFFICIAL_EQUIVALENCE_MISLABEL')
 require(0<native['min_input_tokens']<=native['max_input_tokens'] and native['max_input_tokens']+768==native['max_input_plus_output']<=4096,'CONTEXT_LIMIT')
def main():
 for name in ('raw-vocab-proof.json','vocab-context-raw-proof.json'):
  require(not (BASE/name).exists() and not (BASE/name).is_symlink(),'OUTPUT_EXISTS')
 for rel,h in SOURCE_SHA256.items():read_bound(ROOT/rel,h,2*1024**2)
 public,binary,build,official,model_stat=prepare()
 original=json.loads((BASE/'public-vocab-proof.json').read_text())
 require(original['status']=='FAIL' and original['official_reference_observed_all20'] is True
  and original['official_reference_native_id_mismatch_indices']==[11,12]
  and original['native']['tokenizer_id_match_count']==18 and original['native']['tokenizer_native_raw_roundtrip_count']==20,'OFFICIAL_FAILURE_REQUIRED')
 raw=json.loads((BASE/'raw-reference-diagnostic.json').read_text())
 require(raw['case_count']==20 and raw['raw_roundtrip_count']==20 and raw['official_fixture_sha256']==PINS['official-tokenizer-fixture.json']
  and raw['reference_kind']=='official_metadata_with_only_NFC_normalizer_disabled'
  and [x['text'] for x in raw['tokenizer_parity']]==[x['text'] for x in official['tokenizer_parity']], 'RAW_REFERENCE_CHANGED')
 request=public.capture_request();template_cases,jinja_version=public.official_reference(request)
 base_bundle={'request':request,'cases':public.corpus(),'original_template':public.ORIGINAL_TEMPLATE.read_text(),
  'template_cases':template_cases,'tokenizer_parity':raw['tokenizer_parity'],'reference_kind':'derived_hf_nfc_disabled','max_output_tokens':768}
 common={'runtime_variant':VARIANT,'model_id':MODEL_ID,'revision':REVISION,'gguf_sha256':MODEL_SHA,'header_sha256':HEADER_SHA,
  'source_pin':build['source_pin'],'binary_sha256':sha(binary),'build_report_sha256':sha(public.BUILD_REPORT),
  'helper_sha256':sha(Path(__file__)),'official_fixture_sha256':PINS['official-tokenizer-fixture.json'],
  'official_native_failure_sha256':PINS['public-vocab-proof.json'],'raw_reference_sha256':PINS['raw-reference-diagnostic.json'],
  'reference_kind':raw['reference_kind'],'official_hf_equivalence':'FAIL_18_OF_20_PRESERVED','model_inference_calls':0,'gpu_calls':0,'http_calls':0,
  'original_embedded_template_sha256':sha(public.ORIGINAL_TEMPLATE),'effective_template_sha256':sha(public.TEMPLATE),
  'application_input_output_nfc_repair':False,'source_sha256':SOURCE_SHA256}
 code,native,bundle_sha=invoke(public,binary,dict(base_bundle,context_requests=[request]),model_stat)
 error=None
 try:validate_raw(code,native,1)
 except ValueError as exc:error=str(exc)
 public_ref=save('raw-vocab-proof.json',dict(common,kind='EXAONE45_NATIVE_RAW_REFERENCE_PUBLIC_CPU_PROOF',status='PASS' if error is None else 'FAIL',
  at_utc=datetime.now(timezone.utc).isoformat(),native=native,exit_code=code,validation_error=error,bundle_sha256=bundle_sha,scope='Public only; derived reference, never official HF equivalence.'))
 print(json.dumps({'phase':'PUBLIC_DERIVED_REFERENCE','status':'PASS' if error is None else 'FAIL','proof':public_ref,'id_matches':native.get('tokenizer_id_match_count'),'raw_roundtrips':native.get('tokenizer_native_raw_roundtrip_count')}),flush=True)
 require(error is None,'RAW_PUBLIC_FAILED_PRIVATE_NOT_READ')
 groups={};native_checks=[]
 for name,(rel,count,digest) in SPLITS.items():
  data=read_bound(ROOT/rel,digest,2*1024**2)
  rows=[json.loads(line) for line in data.splitlines() if line.strip()];require(len(rows)==count,'SPLIT_COUNT')
  requests=[]
  for row in rows:
   require(type(row.get('input')) is str and type(row.get('context')) is dict,'SPLIT_INPUT')
   requests.append(public.capture_request(row['input'],row['context'].get('axis_convention')))
  del rows,data
  code,native,bundle_sha=invoke(public,binary,dict(base_bundle,context_requests=requests),model_stat)
  try:validate_raw(code,native,count)
  except ValueError:
   save('context-failure-'+name+'.json',dict(common,kind='EXAONE45_NATIVE_CONTEXT_FAILURE',status='FAIL',split=name,native=native,exit_code=code))
   raise
  groups[name]={'dataset_sha256':digest,'input_count':count,'min_input_tokens':native['min_input_tokens'],
   'max_input_tokens':native['max_input_tokens'],'max_input_plus_output':native['max_input_plus_output'],'bundle_sha256':bundle_sha}
  native_checks.append(native);del requests
 for rel,h in SOURCE_SHA256.items():read_bound(ROOT/rel,h,2*1024**2)
 require(stat_key(MODEL.stat())==model_stat,'MODEL_CHANGED')
 token=native_checks[0]['resource_probe_token_id'];require(all(x['resource_probe_token_id']==token for x in native_checks),'RESOURCE_TOKEN_CHANGED')
 detail=dict(common,kind='EXAONE45_NATIVE_RAW_VOCAB_CONTEXT_CPU_PROOF',status='PASS',at_utc=datetime.now(timezone.utc).isoformat(),
  splits=groups,native_checks=native_checks,raw_public_proof_ref=public_ref,max_output_tokens=768,max_context_tokens=4096,
  resource_probe_token={'text':' ','token_id':token,'native_token_count':1,'native_roundtrip':True},
  input_bodies_gold_token_ids_saved=False,gold_fields_scored=False,vocab_only_model_open_count=3,
  limitations=['Native raw reference matches only these twenty public probes; no global Unicode guarantee.',
    'Official HF token ID equivalence remains FAIL: 18 matched and 2 differed; original NFC-normalized expectation unchanged.',
    'Length-only processing is not semantic evaluation; unused future holdout was not opened.'])
 proof=save('vocab-context-raw-proof.json',detail)
 print(json.dumps({'phase':'LENGTH_ONLY_200','status':'PASS','proof':proof,'splits':{k:{x:y for x,y in v.items() if x not in ('bundle_sha256','dataset_sha256')} for k,v in groups.items()}}))
 return 0
if __name__=='__main__':
 try:raise SystemExit(main())
 except Exception as e:
  print(json.dumps({'status':'FAIL','error_type':type(e).__name__,'code':str(e) if isinstance(e,ValueError) and re.fullmatch('[A-Z0-9_]+',str(e)) else 'INPUT_OR_IO_ERROR'}));raise SystemExit(1)
