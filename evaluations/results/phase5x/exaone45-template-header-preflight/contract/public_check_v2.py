"""Public-only EXAONE native CPU grammar/parser check; no GGUF/model/network."""
from pathlib import Path
from datetime import datetime, timezone
import copy, ctypes, hashlib, json, os, re, resource, signal, subprocess, sys
from urllib.error import URLError
ROOT=Path('/home/a202192020/NeuroBuild_v2')
BASE=ROOT/'var/research/native-exaone45-contract'
sys.path.insert(0,str(ROOT/'src'))
from neurobuild.infrastructure.local_model import LocalRequirementClient
from neurobuild.domain.errors import DomainError
from jsonschema import Draft202012Validator
TEMPLATE=ROOT/'var/research/exaone45-33b-candidate-metadata/upstream/chat_template.jinja'
SCHEMA=ROOT/'schemas/requirement_generation_v2_decision_branches.schema.json'
PROMPT=ROOT/'prompts/requirement_generation_v2_v2.txt'
REPORT=BASE/'public-proof-v2.json';BUILD_REPORT=BASE/'build-v2.json'
PINS={TEMPLATE:'e4ece7acc79ba82121d4d57791fb7ecb796e39185087197377da5d2286bec0e5',
SCHEMA:'36d42b9fa3d24f4a1bc1d14381110e36e8d89103b696bc83113be006b64934e2',
PROMPT:'99d737124372836ba5f985fa6e5570afef693e769798844931f000fb21403cf6',
ROOT/'src/neurobuild/infrastructure/local_model.py':'48276a8f9cb7a2a818a9f12e7f86b2b53f525a37de61a1be70fe73648f07c151'}
SAFE_ENV={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','LC_ALL':'C.UTF-8','CUDA_VISIBLE_DEVICES':'','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'}
def sha(path):
 with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def capture_request(source_text='공개 실험용 보관장을 X축 양의 방향으로 2cm 옮겨줘.',axis_convention='project_xy'):
 class Capture:
  def open(self,request,**kwargs):self.body=request.data;raise URLError('CPU capture')
 capture=Capture()
 client=LocalRequirementClient('http://127.0.0.1:8003','neurobuild-exaone45-33b-q4-k-m',
  prompt_path=PROMPT,schema_path=SCHEMA,generation_contract='2.0',
  protocol='llama_cpp_json_schema',sampling_profile='exaone45_nonthinking_llama_cpp')
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
 assert build['kind']=='EXAONE45_NATIVE_CONTRACT_CPU_BUILD' and build['status']=='COMPILE_PASS_NOT_EXECUTED'
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

def run_binary(binary,bundle):
 # No raw stderr retention: helper discards/counts converter messages itself;
 # unexpected child stderr is drained into a fixed byte count, never a report.
 parent=os.getpid()
 def prepare():
  resource.setrlimit(resource.RLIMIT_CORE,(0,0))
  libc=ctypes.CDLL(None,use_errno=True)
  if libc.prctl(1,signal.SIGKILL)!=0 or os.getppid()!=parent:os._exit(91)
 args=[str(binary),str(TEMPLATE),str(SCHEMA)]
 payload=json.dumps(bundle,ensure_ascii=False).encode()
 child=subprocess.Popen(args,cwd=ROOT,env=SAFE_ENV,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
  start_new_session=True,preexec_fn=prepare)
 try:stdout,stderr=child.communicate(payload,timeout=180)
 except BaseException:
  os.killpg(child.pid,signal.SIGKILL);child.wait();raise
 assert len(stdout)<65536 and not stderr
 native=json.loads(stdout)
 assert native['kind']=='EXAONE45_NATIVE_PUBLIC_CONTRACT_CPU_PREFLIGHT'
 # Result contains fixed checks/counts only; C++ never echoes fixture bodies.
 assert all(isinstance(v,(str,int,bool)) for v in native.values())
 return child.returncode,native,hashlib.sha256(payload).hexdigest()

def main():
 assert len(sys.argv)==1 and Path(sys.prefix)==ROOT/'.conda' and os.environ.get('CUDA_VISIBLE_DEVICES')==''
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 assert not REPORT.exists() and not REPORT.is_symlink()
 for p,h in PINS.items():assert sha(p)==h
 binary,build=inspect_cpu_binary()
 bundle={'request':capture_request(),'cases':corpus()}
 assert len(bundle['cases'])==30 and sum(x['accept'] for x in bundle['cases'])==10
 code,native,corpus_sha=run_binary(binary,bundle)
 for p,h in PINS.items():assert sha(p)==h
 assert sha(binary)==build['binary_sha256']
 result={'kind':'EXAONE45_NATIVE_PUBLIC_TEMPLATE_CPU_PROOF','status':'PASS' if code==0 and native['status']=='PASS' else 'FAIL',
 'at_utc':datetime.now(timezone.utc).isoformat(),'source_pin':build['source_pin'],'model_id':'LGAI-EXAONE/EXAONE-4.5-33B-GGUF',
 'model_revision':'0e969634ef24db05151b435970297a6dee634b7e','protocol':'llama_cpp_json_schema','sampling_profile':'exaone45_nonthinking_llama_cpp',
 'enable_thinking':False,'native':native,'exit_code':code,'binary_sha256':sha(binary),'build_report_sha256':sha(BUILD_REPORT),
 'helper_sha256':sha(Path(__file__)),'inputs':{str(p.relative_to(ROOT)):h for p,h in PINS.items()},
 'production_client_sha256':sha(ROOT/'src/neurobuild/infrastructure/local_model.py'),
 'corpus_sha256':corpus_sha,'request_sha256':hashlib.sha256(json.dumps(bundle['request'],ensure_ascii=False).encode()).hexdigest(),
 'gpu_calls':0,'http_calls':0,'model_calls':0,'gguf_loaded':False,'prior_failed_public_sha256':sha(BASE/'public-proof.json'),
 'fence_scope':'Native eager grammar accepts plain JSON or json-fenced JSON; native PEG extracts identical JSON content bytes from each. Client sees final content only and still rejects inline fences; no application repair.',
 'reasoning_scope':'Artificial public parser fixture only; exact trailing LF retained in separate reasoning field; no reasoning body saved.',
 'scope':'Public policy examples and synthetic fixtures only; no evaluation body or model output'}
 with REPORT.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps({'status':result['status'],'native':native,'report':str(REPORT.relative_to(ROOT)),'sha256':sha(REPORT)}))
 return 0 if result['status']=='PASS' else 1
if __name__=='__main__':
 try:raise SystemExit(main())
 except Exception as error:print(json.dumps({'status':'FAIL','error_type':type(error).__name__}));raise SystemExit(1)
