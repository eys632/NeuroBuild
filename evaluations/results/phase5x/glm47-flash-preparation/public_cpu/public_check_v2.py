"""GLM public-only CPU contract. Main must be authorized separately; no GGUF argument."""
from pathlib import Path
from datetime import datetime, timezone
import copy, ctypes, hashlib, json, os, re, resource, signal, subprocess, sys
from urllib.error import URLError
ROOT=Path('/home/a202192020/NeuroBuild_v2')
BASE=ROOT/'var/research/native-glm47-contract'
sys.path.insert(0,str(ROOT/'src'))
from neurobuild.infrastructure.local_model import LocalRequirementClient
from neurobuild.domain.errors import DomainError
from jsonschema import Draft202012Validator
TEMPLATE=ROOT/'var/research/glm47-flash-candidate-metadata/upstream/chat_template.jinja'
RENDERER=BASE/'render_official.py'
SCHEMA=ROOT/'schemas/requirement_generation_v2_decision_branches.schema.json'
PROMPT=ROOT/'prompts/requirement_generation_v2_v2.txt'
REPORT=BASE/'public-proof-v2.json';BUILD_REPORT=BASE/'build-v2.json'
SAFE_ENV={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','LC_ALL':'C.UTF-8','CUDA_VISIBLE_DEVICES':'','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'}
PINS={ROOT/path:h for path,h in {'var/research/glm47-flash-candidate-metadata/upstream/chat_template.jinja': 'd63ad536c3c81880043e22ec7fd08db42b4d8fb7c89c7138bc562bfa25281375', 'var/research/native-glm47-contract/render_official.py': 'fcfce9d2167a73d3a0e99332f430026aff2f1b7ba10df0cf3eb7d0778ad4af2c', 'schemas/requirement_generation_v2_decision_branches.schema.json': '36d42b9fa3d24f4a1bc1d14381110e36e8d89103b696bc83113be006b64934e2', 'prompts/requirement_generation_v2_v2.txt': '99d737124372836ba5f985fa6e5570afef693e769798844931f000fb21403cf6', 'src/neurobuild/infrastructure/local_model.py': '7dfc3f673ba6ab4e4970055c4cbee66ae440da2d42070af959a5fe415a9ab780'}.items()}
PINS.update({ROOT/path:h for path,h in {'src/neurobuild/application/requirements.py': 'a940f3952c0c4133ab51732f6abf76516d8ff66617470545222b52adfa49fb4a', 'src/neurobuild/application/requirement_generation.py': 'fcba16f6adc906923859f3bcf4ae2f680e76716863a759582167cd9326f03198'}.items()})

PINS.update({ROOT/path:h for path,h in {'var/research/native-glm47-contract/validator.cpp': 'c99c5759b65a4ae4a4f31df9f3fda75cdcd454771b126683afe7c75d7707edf9', 'var/research/native-glm47-contract/build.py': '5c2a98c7aa2f86e293ec3bd5ff37ddaa9c7cd3fa461e7ccb8065289bacb08e86', 'var/research/native-glm47-contract/public_check.py': '2ee13e3092232beecfdf0a550de2bd5ba18e1935901ec8d406303cc06722e43b', 'var/research/native-glm47-contract/build.json': 'fe348c07e21c1c601e1a48a529cd5a8de00938b647da9dd926480b9e0d213c74', 'var/research/native-glm47-contract/glm47-cpu-validator': '4bcff0326ead4a3572394cf8fb701aea78e77586ea15bbec32dfb4e4f498ba83', 'var/research/native-glm47-contract/public-proof.json': '7eba381e83c09f14d9dcfaf898e20dd02badc3cc02362ac5e8eab5d9eb9b5b43', 'var/research/native-glm47-contract/official-tokenizer-fixture.json': 'e67bd4d05462587e0466f092351ada8c8fa4efdd9a10da0b4cecb25a4d3dc8f3', 'var/research/native-glm47-contract/validator_v2.cpp': 'd206571cdc4b6893a1bf6565a260303b6d5c1ea1fb7b4e7efba46d60b0046d29'}.items()})


def sha(path):
 with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def capture_request(source_text='공개 실험용 보관장을 X축 양의 방향으로 2cm 옮겨줘.',axis_convention='project_xy'):
 class Capture:
  def open(self,request,**kwargs):self.body=request.data;raise URLError('CPU capture')
 capture=Capture()
 client=LocalRequirementClient('http://127.0.0.1:8003','neurobuild-glm47-flash-q4-k',
  prompt_path=PROMPT,schema_path=SCHEMA,generation_contract='2.0',
  protocol='llama_cpp_json_schema',sampling_profile='glm47_flash_nonthinking_llama_cpp')
 client._opener=capture
 try:client.complete(source_text,axis_convention=axis_convention)
 except DomainError as error:assert error.code=='LOCAL_MODEL_UNAVAILABLE'
 return json.loads(capture.body)

def corpus():
    examples = [json.loads(line.removeprefix('출력: ')) for line in PROMPT.read_text().splitlines()
                if line.startswith('출력: ')]
    assert len(examples) == 7
    ready, nonready = copy.deepcopy(examples[0]), copy.deepcopy(examples[2])
    xy = dict(ready, dy_evidence='Y축 -2cm')
    escaped = dict(ready, target_selection_quote='"인용"\\경로\n한국어 😀')
    accepts = examples + [xy, escaped, dict(ready, target_selection_quote='')]
    rejects = []
    for key in ready:
        case = copy.deepcopy(ready)
        del case[key]
        rejects.append(case)
    rejects += [dict(ready, extra=True), dict(ready, schema_version='1.0'),
                dict(ready, decision='UNKNOWN'), dict(ready, dx_evidence=None),
                dict(ready, reason='null'), dict(ready, current_instruction_quote=None),
                dict(nonready, current_instruction_quote='지원되지 않은 지시'),
                dict(nonready, dx_evidence='X축 +1m'), dict(nonready, reason=None), [ready]]
    validator = Draft202012Validator(json.loads(SCHEMA.read_text()))
    assert all(validator.is_valid(case) for case in accepts)
    assert all(not validator.is_valid(case) for case in rejects)
    encode = lambda case: json.dumps(case, ensure_ascii=False, separators=(',', ':'))
    cases = [{'text': encode(case), 'accept': True} for case in accepts]
    cases += [{'text': encode(case), 'accept': False} for case in rejects]
    cases += [{'text': text, 'accept': False} for text in
              (encode(ready)[:-1], encode(ready) + 'x', encode(ready) + encode(ready))]
    return cases

def inspect_cpu_binary():
 build=json.loads(BUILD_REPORT.read_text())
 assert build['kind']=='GLM47_FLASH_NATIVE_CONTRACT_CPU_BUILD' and build['status']=='COMPILE_PASS_NOT_EXECUTED'
 assert build['cuda_visible_devices']=='' and build['native_validator_executed'] is False
 assert all(build['settings'][key]=='OFF' for key in ['GGML_CUDA','GGML_BACKEND_DL','BUILD_SHARED_LIBS'])
 assert build['reused_upstream_objects_before']==build['reused_upstream_objects_after']
 for rel,h in build['pinned_inputs'].items():assert sha(ROOT/rel)==h
 binary=ROOT/build['binary_path'];assert binary.is_file() and not binary.is_symlink() and sha(binary)==build['binary_sha256']
 dynamic=subprocess.run(['/usr/bin/readelf','--wide','--dynamic',str(binary)],env=SAFE_ENV,capture_output=True,text=True,check=True,timeout=30)
 assert not dynamic.stderr
 needed=re.findall(r'\(NEEDED\).*\[([^\]]+)\]',dynamic.stdout)
 assert needed==build['elf_needed'] and not re.search(r'\((?:RPATH|RUNPATH)\)',dynamic.stdout)
 assert set(needed)<={'libstdc++.so.6','libm.so.6','libgcc_s.so.1','libc.so.6','libpthread.so.0','libdl.so.2','librt.so.1','ld-linux-x86-64.so.2'}
 assert all(p['exit_code']==0 and p['native_cleanup']['cleanup_complete'] and p['native_cleanup']['native_reaped'] for p in build['phases'])
 return binary,build

def prepare_child():
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 libc=ctypes.CDLL(None,use_errno=True)
 # Actual parent identity is set by the closure in invoke, not inherited env.
 if libc.prctl(1,signal.SIGKILL)!=0:os._exit(91)

def invoke(command,payload,timeout):
 parent=os.getpid()
 def setup():
  prepare_child()
  if os.getppid()!=parent:os._exit(91)
 child=subprocess.Popen(command,cwd=ROOT,env=SAFE_ENV,stdin=subprocess.PIPE,
  stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,preexec_fn=setup)
 try:stdout,stderr=child.communicate(payload,timeout=timeout)
 except BaseException:
  try:os.killpg(child.pid,signal.SIGKILL)
  except ProcessLookupError:pass
  child.wait();raise
 # No raw stderr is stored. Fixed helper emits at most a small numeric object.
 assert len(stdout)<=1024*1024
 return child.returncode,stdout,len(stderr)

def run_binary(binary,bundle):
 payload=json.dumps(bundle,ensure_ascii=False).encode()
 assert len(payload)<=2*1024*1024
 code,stdout,stderr_bytes=invoke([str(binary),str(TEMPLATE),str(SCHEMA)],payload,180)
 assert len(stdout)<65536
 native=json.loads(stdout)
 assert native['kind']=='GLM47_FLASH_NATIVE_PUBLIC_CONTRACT_CPU_PREFLIGHT'
 assert all(isinstance(v,(str,int,bool)) for v in native.values())
 if stderr_bytes:
  native={'kind':native['kind'],'status':'FAIL','code':'UNEXPECTED_STDERR','stderr_bytes':stderr_bytes}
  code=1
 return code,native,hashlib.sha256(payload).hexdigest()

def template_variables(request):
 def case(messages,**kwargs):
  return {'messages':messages,'tools':None,'add_generation_prompt':True,
          'enable_thinking':False,'bos_token':'[gMASK]','eos_token':'<|endoftext|>',**kwargs}
 system={'role':'system','content':'  공개 system 공백과 줄바꿈\n정확히 유지.  '}
 user={'role':'user','content':'공개 사용자 문자열\n  원문 보존.'}
 assistant={'role':'assistant','content':'  공개 답변  '}
 tool={'type':'function','function':{'name':'public_lookup','description':'공개 검색','parameters':{'type':'object','properties':{'key':{'type':'string'}},'required':['key']}}}
 function={'name':'public_lookup','arguments':{'key':'공개 값','count':2}}
 rows=[case(request['messages']),case([user],tools=[]),case([system]),case([system,system,user]),
       case([system,user,assistant,user]),case([user,system]),
       case([user,dict(assistant,reasoning_content='PUBLIC SYNTHETIC'),user],clear_thinking=True),
       case([user,dict(assistant,content='<think>PUBLIC SYNTHETIC</think>  공개 답변  ')]),
       case([system,user],tools=[tool]),
       case([user,dict(assistant,tool_calls=[{'function':function}]),{'role':'tool','content':'공개 결과'},user],tools=[tool]),
       case([user,dict(assistant,tool_calls=[function]),{'role':'tool','content':'공개 결과'},{'role':'tool','content':'두 번째 결과'},user],tools=[tool]),
       case([{'role':'user','content':[{'type':'text','text':'앞부분 '},{'type':'text','text':'뒷부분'}]}]),
       case([{'role':'user','content':['문자열 앞 ',{'type':'text','text':'텍스트 뒤'}]}]),
       case([system,user],enable_thinking=True),case([system,user],add_generation_prompt=False),
       case([user,dict(assistant,reasoning_content='PUBLIC SYNTHETIC')],clear_thinking=False),
       case([{'role':'user','content':[{'type':'image'},{'type':'text','text':'공개 이미지 표식'}]}]),
       case([{'role':'tool','content':[{'output':'공개 결과 1'},'공개 결과 2']},user]),
       case([user,dict(assistant,content='',reasoning_content='')]),
       case([{'role':'system','content':''},{'role':'user','content':''}])]
 assert len(rows)==20
 return rows

def official_reference(request):
 variables=template_variables(request)
 payload={'original_template':TEMPLATE.read_text(),'variables':variables}
 code,stdout,stderr_bytes=invoke([str(ROOT/'.conda-vllm/bin/python'),str(RENDERER)],
  json.dumps(payload,ensure_ascii=False).encode(),30)
 assert code==0 and stderr_bytes==0 and len(stdout)<1024*1024
 ref=json.loads(stdout)
 assert ref['reference_cases']==20 and ref['torch_imported'] is False and ref['template_override_used'] is False
 return [{'variables':v,'expected_render':r} for v,r in zip(variables,ref['rendered'],strict=True)],ref['jinja2_version']

def main():
 assert len(sys.argv)==1 and Path(sys.prefix)==ROOT/'.conda' and os.environ.get('CUDA_VISIBLE_DEVICES')==''
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 assert not REPORT.exists() and not REPORT.is_symlink()
 record={'kind':'GLM47_FLASH_NATIVE_PUBLIC_TEMPLATE_CPU_PROOF','status':'FAIL',
  'at_utc':datetime.now(timezone.utc).isoformat(),'phase':'INITIAL','gpu_calls':0,'http_calls':0,
  'model_calls':0,'gguf_loaded':False,'evaluation_inputs_read':0,'helper_sha256':sha(Path(__file__)),
  'prior_failed_public_sha256':PINS[BASE/'public-proof.json'],
  'revision_reason':'Configured nonthinking prefix must reject a complete artificial thought block; alternate-mode positive parsing is outside this candidate gate.'}
 try:
  for p,h in PINS.items():assert sha(p)==h
  record['phase']='BUILD_ELF_VERIFICATION'
  binary,build=inspect_cpu_binary()
  record['phase']='OFFICIAL_PUBLIC_REFERENCE'
  request=capture_request();template_cases,jinja2_version=official_reference(request)
  bundle={'request':request,'cases':corpus(),'template_cases':template_cases,
          'reference_kind':'official_pinned_tokenizer_no_normalizer_change'}
  assert len(bundle['cases'])==30 and sum(x['accept'] for x in bundle['cases'])==10
  record['phase']='NATIVE_PUBLIC_CONTRACT'
  code,native,corpus_sha=run_binary(binary,bundle)
  for p,h in PINS.items():assert sha(p)==h
  assert sha(binary)==build['binary_sha256']
  record.update(status='PASS' if code==0 and native['status']=='PASS' else 'FAIL',
   phase='FINISHED',source_pin=build['source_pin'],model_id='ggml-org/GLM-4.7-Flash-GGUF',
   model_revision='7559e96b7e324ab405897dc2b91492b0f376ad4a',protocol='llama_cpp_json_schema',
   sampling_profile='glm47_flash_nonthinking_llama_cpp',enable_thinking=False,
   jinja2_reference_version=jinja2_version,template_reference_cases=len(template_cases),
   official_template_sha256=sha(TEMPLATE),template_override_used=False,native=native,
   exit_code=code,binary_sha256=sha(binary),build_report_sha256=sha(BUILD_REPORT),
   inputs={str(p.relative_to(ROOT)):h for p,h in PINS.items()},
   production_client_sha256=sha(ROOT/'src/neurobuild/infrastructure/local_model.py'),
   corpus_sha256=corpus_sha,request_sha256=hashlib.sha256(json.dumps(request,ensure_ascii=False).encode()).hexdigest(),
   fence_scope='Expected native grammar plain/fenced JSON acceptance and byte-exact native final content are measured separately. Client inline-fence rejection and no repair remain unchanged.',
   reasoning_scope='Configured nonthinking grammar rejects a complete artificial thought block. Alternate thinking-mode parse is not tested; no reasoning body is retained.',
   scope='Public policy examples and synthetic fixtures only; vocabulary and dataset context NOT_RUN.')
 except Exception as error:
  record['error_type']=type(error).__name__
 finally:
  with REPORT.open('x') as f:json.dump(record,f,indent=2);f.write('\n')
 print(json.dumps({'status':record['status'],'phase':record['phase'],'report':str(REPORT.relative_to(ROOT)),'sha256':sha(REPORT)}))
 return 0 if record['status']=='PASS' else 1

if __name__=='__main__':
 try:raise SystemExit(main())
 except Exception as error:print(json.dumps({'status':'FAIL','error_type':type(error).__name__}));raise SystemExit(1)
