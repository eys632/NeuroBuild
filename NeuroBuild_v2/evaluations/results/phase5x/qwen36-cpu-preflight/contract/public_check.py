"""One new Qwen36 public native request; no GGUF, tokenizer or context-corpus run.

Execute only after root reviews the actual full header and saved typed comparison.
All missing actual proof hashes are explicit CLI inputs; no placeholder PASS.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import resource
import signal
import subprocess
import sys
from urllib.error import URLError

ROOT=Path('/home/a202192020/NeuroBuild_v2')
BASE=ROOT/'var/research/native-qwen36-contract'
REPORT=BASE/'public-proof.json'
HEADER=Path('var/reports/qwen36-gguf-header.json')
COMPARISON=Path('var/reports/qwen36-qwen38-saved-tokenizer-comparison.json')
BUILD=Path('var/research/native-qwen36-contract/build.json')
EQUIVALENCE=Path('var/research/native-qwen36-contract/source-equivalence.json')
EQUIVALENCE_SHA='efd6529f1f2db9e7cdd4bd5fc24e8f31e0b8e87189ee1a8865c595d4e1bb2d66'
AUDITOR=Path('var/research/inspect_qwen36_gguf.py')
AUDITOR_SHA='6e19db06be126b95ec619d434b7230a88dc4542d10d506c026f9cebb71114d97'
TEMPLATE=Path('var/research/qwen36-candidate-metadata/upstream/chat_template.jinja')
SCHEMA=Path('schemas/requirement_generation_v2_decision_branches.schema.json')
PROMPT=Path('prompts/requirement_generation_v2_v2.txt')
SOURCE_PINS={
 'src/neurobuild/infrastructure/local_model.py':'0814c6a5a695c3abb3c4c6cf244990bd569ed372840b1786d2b488e72e0f3120',
 'src/neurobuild/application/requirement_generation.py':'fcba16f6adc906923859f3bcf4ae2f680e76716863a759582167cd9326f03198',
 'src/neurobuild/application/requirements.py':'a940f3952c0c4133ab51732f6abf76516d8ff66617470545222b52adfa49fb4a',
 str(PROMPT):'99d737124372836ba5f985fa6e5570afef693e769798844931f000fb21403cf6',
 str(SCHEMA):'36d42b9fa3d24f4a1bc1d14381110e36e8d89103b696bc83113be006b64934e2'}
PINS={**SOURCE_PINS,str(AUDITOR):AUDITOR_SHA,str(EQUIVALENCE):EQUIVALENCE_SHA,
 str(TEMPLATE):'e84f32a23fdda27689f868aa4a1a5621f41133e51a48d7f3efcbea2839574259',
 'var/research/native-qwen36-contract/validator.cpp':'c55f66ab7909a921bdf8c429151cf71eb4cc17cc34a0578e65b709eae4c41ec8',
 'var/research/native-qwen36-contract/build.py':'61760634036bd94e1922d6cb022ab6c2ffaf3cb30dc1c54d6bd2813a31196a0b'}
SAMPLE={'temperature':0.7,'top_p':0.8,'top_k':20,'min_p':0.0,'presence_penalty':1.5,
 'frequency_penalty':0.0,'repeat_penalty':1.0,'repeat_last_n':64,'seed':42,
 'samplers':['penalties','top_k','top_p','min_p','temperature']}
SAFE_ENV={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','LC_ALL':'C.UTF-8','CUDA_VISIBLE_DEVICES':'',
          'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'}
BOOTSTRAP='''import ctypes,os,resource,signal,sys
parent=int(sys.argv[1])
if ctypes.CDLL(None,use_errno=True).prctl(1,signal.SIGKILL,0,0,0)!=0:raise SystemExit(91)
if os.getppid()!=parent:raise SystemExit(91)
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
os.execve(sys.argv[2],sys.argv[2:],dict(os.environ))
'''
PUBLIC_SOURCE='검사실 책상을 X축 양의 방향으로 1m 옮겨줘.'


def require(ok,code):
    if not ok:raise ValueError(code)


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def capture_request():
    # Import only after source pins and saved prerequisites have been checked.
    sys.path.insert(0,str(ROOT/'src'))
    from neurobuild.infrastructure.local_model import LocalRequirementClient
    from neurobuild.domain.errors import DomainError
    class Capture:
        count=0
        body=None
        def open(self,request,**kwargs):
            self.count+=1;self.body=request.data;raise URLError('CPU capture')
    opener=Capture()
    client=LocalRequirementClient('http://127.0.0.1:8003','neurobuild-qwen36-35b-a3b-q4-k-m',
      prompt_path=ROOT/PROMPT,schema_path=ROOT/SCHEMA,generation_contract='2.0',
      protocol='llama_cpp_json_schema',sampling_profile='qwen36_nonthinking_llama_cpp',max_tokens=768)
    client._opener=opener
    try:client.complete(PUBLIC_SOURCE,axis_convention='project_xy')
    except DomainError as exc:require(exc.code=='LOCAL_MODEL_UNAVAILABLE','CAPTURE_ERROR')
    require(opener.count==1 and type(opener.body) is bytes,'CAPTURE_COUNT')
    return json.loads(opener.body)


def validate_native(native,code,stderr_bytes):
    fixed={'kind':'QWEN36_NATIVE_SINGLE_PUBLIC_CPU_CHECK','status':'PASS','public_request_count':1,
      'native_full_system_user_prompt_exact':True,'native_generation_prefix_exact':True,
      'native_sampling_schema_binding':True,'native_final_content_exact':True,
      'native_trailing_suffix_rejected':True,'grammar_lazy':False,'grammar_triggers':0,
      'generation_prefix_bytes':41,'core_dump_limit_zero':True,'discarded_stderr_bytes':0,
      'old_public_corpus_calls':0,'tokenizer_parity_cases':0,'context_requests':0,
      'gguf_opened':False,'model_context_created':False,'backend_init_called':False,
      'weight_tensors_loaded':False,'model_inference_calls':0}
    require(code==0 and stderr_bytes==0 and type(native) is dict
      and set(native)==set(fixed)|{'native_prompt_bytes'},'NATIVE_PUBLIC_FAILED')
    require(all(type(native[k]) is type(v) and native[k]==v for k,v in fixed.items()),'NATIVE_PUBLIC_FIELDS')
    require(type(native['native_prompt_bytes']) is int and 0<native['native_prompt_bytes']<128*1024,'PROMPT_SIZE')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--header-sha256',required=True)
    p.add_argument('--comparison-sha256',required=True)
    p.add_argument('--build-sha256',required=True)
    args=p.parse_args()
    require(Path(sys.prefix)==ROOT/'.conda' and os.environ.get('CUDA_VISIBLE_DEVICES')=='','CPU_ENV_REQUIRED')
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    require(not REPORT.exists() and not REPORT.is_symlink(),'OUTPUT_EXISTS')
    for path,digest in PINS.items():require(sha(ROOT/path)==digest,'PIN_CHANGED')
    spec=importlib.util.spec_from_file_location('qwen36_public_auditor',ROOT/AUDITOR)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    refs={str(HEADER):args.header_sha256,str(COMPARISON):args.comparison_sha256,str(BUILD):args.build_sha256}
    header,comparison,build=[json.loads(m.read_bound(Path(path),digest,2*1024**2)) for path,digest in refs.items()]
    require(header['kind']=='GGUF_HEADER_AUDIT' and header['status']=='PASS'
      and header['model_id']==m.MODEL_ID and header['revision']==m.REVISION
      and header['file_sha256']==m.FILE_SHA and header['full_file_sha256_verified'] is True,'HEADER_NOT_PASS')
    require(comparison['kind']=='QWEN36_QWEN38_SAVED_TYPED_TOKENIZER_COMPARISON'
      and comparison['status']=='PASS_EXACT_TYPED_TOKENIZER_EXCEPT_DECLARED_TEMPLATE'
      and comparison['typed_tokenizer_equal_excluding_template'] is True
      and comparison['proof_refs'][str(HEADER)]==args.header_sha256,'TYPED_VOCAB_CARRY_UNAVAILABLE')
    require(build['kind']=='QWEN36_NATIVE_CONTRACT_CPU_BUILD' and build['status']=='COMPILE_PASS_NOT_EXECUTED'
      and build['source_pin']==m.RUNTIME and build['cuda_visible_devices']==''
      and build['native_validator_executed'] is False and build['model_or_weights_loaded'] is False,'BUILD_INVALID')
    require(all(build['settings'][k]=='OFF' for k in ('GGML_CUDA','GGML_BACKEND_DL','BUILD_SHARED_LIBS')),'BUILD_GPU')
    require(build['reused_upstream_objects_before']==build['reused_upstream_objects_after']
      and build['reused_upstream_objects_before']['files']==194
      and build['reused_upstream_objects_before']['inventory_sha256']=='b16b4bdbac76fe000c4c3d00553b43b6ee8a81115438f06ee7a67c7163cd0e76'
      and build['elf_no_gpu_dependencies'] is True and build['elf_no_rpath'] is True,'BUILD_REUSE_MISMATCH')
    require(len(build['phases'])==2 and all(x['exit_code']==0 and x['native_cleanup']['cleanup_complete']
      and x['native_cleanup']['native_reaped'] for x in build['phases']),'BUILD_CLEANUP')
    for path,digest in build['pinned_inputs'].items():require(sha(ROOT/path)==digest,'BUILD_PIN_CHANGED')
    binary=BASE/'qwen36-cpu-validator'
    require(build['binary_path']==str(binary.relative_to(ROOT)) and not binary.is_symlink()
      and sha(binary)==build['binary_sha256'],'BINARY_CHANGED')
    request=capture_request()
    require({k:request[k] for k in SAMPLE}==SAMPLE and request['chat_template_kwargs']=={'enable_thinking':False}
      and request['max_tokens']==768 and request['stream'] is False,'WIRE_MISMATCH')
    messages=request['messages'];require(len(messages)==2 and messages[0]['role']=='system'
      and messages[1]['role']=='user' and messages[0]['content']==(ROOT/PROMPT).read_text(),'MESSAGES_CHANGED')
    prefix='<|im_start|>assistant\n<think>\n\n</think>\n\n'
    expected='<|im_start|>system\n'+messages[0]['content'].strip()+'<|im_end|>\n'
    expected+='<|im_start|>user\n'+messages[1]['content'].strip()+'<|im_end|>\n'+prefix
    final={'schema_version':'2.0','decision':'READY','target_selection_quote':'검사실 책상',
      'current_instruction_quote':PUBLIC_SOURCE,'dx_evidence':'X축 양의 방향으로 1m','dy_evidence':None,'reason':None}
    bundle={'request':request,'expected_prompt':expected,'expected_generation_prompt':prefix,
            'expected_final':json.dumps(final,ensure_ascii=False,separators=(',',':'))}
    payload=json.dumps(bundle,ensure_ascii=False).encode();require(len(payload)<256*1024,'BUNDLE_TOO_LARGE')
    cmd=[str(ROOT/'.conda/bin/python'),'-I','-B','-c',BOOTSTRAP,str(os.getpid()),str(binary),str(ROOT/TEMPLATE),str(ROOT/SCHEMA)]
    child=subprocess.Popen(cmd,cwd=ROOT,env=SAFE_ENV,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,start_new_session=True)
    try:stdout,stderr=child.communicate(payload,timeout=60)
    except BaseException:
        try:os.killpg(child.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        child.wait();raise
    require(len(stdout)<16384,'NATIVE_OUTPUT_SIZE')
    native=json.loads(stdout)
    validate_native(native,child.returncode,len(stderr))
    require(native['native_prompt_bytes']==len(expected.encode()),'PROMPT_BYTES_MISMATCH')
    for path,digest in {**PINS,**refs}.items():require(sha(ROOT/path)==digest,'INPUT_MUTATED')
    require(sha(binary)==build['binary_sha256'],'BINARY_MUTATED')
    record={'kind':'QWEN36_NATIVE_RESTRICTED_TEMPLATE_CPU_PROOF','status':'PASS',
      'created_utc':datetime.now(timezone.utc).isoformat(),'model_id':m.MODEL_ID,'revision':m.REVISION,
      'gguf_sha256':m.FILE_SHA,'header_sha256':args.header_sha256,'comparison_sha256':args.comparison_sha256,
      'template_sha256':m.TEMPLATE_SHA,'source_pin':m.RUNTIME,'protocol':'llama_cpp_json_schema',
      'sampling_profile':'qwen36_nonthinking_llama_cpp','sampling_request_parameters':SAMPLE,
      'source_sha256':SOURCE_PINS,'enable_thinking':False,'enable_reasoning':False,
      'max_output_tokens':768,'max_context_tokens':4096,'native':native,
      'request_sha256':hashlib.sha256(json.dumps(request,ensure_ascii=False).encode()).hexdigest(),
      'expected_prompt_sha256':hashlib.sha256(expected.encode()).hexdigest(),
      'source_equivalence_sha256':EQUIVALENCE_SHA,'build_report_sha256':args.build_sha256,
      'binary_sha256':build['binary_sha256'],'cpp_sha256':PINS['var/research/native-qwen36-contract/validator.cpp'],
      'helper_sha256':sha(Path(__file__)),'bound_inputs':{**PINS,**refs},
      'new_public_request_count':1,'native_process_count':1,'old_public_corpus_calls':0,
      'tokenizer_parity_cases':0,'context_requests':0,'weight_accesses':0,
      'model_inference_calls':0,'http_calls':0,'gpu_calls':0,'input_output_nfc_repair':False,
      'raw_http_reasoning_or_evaluation_bodies_saved':False}
    data=(json.dumps(record,ensure_ascii=False,indent=2)+'\n').encode()
    with m.safe_open(ROOT,REPORT.relative_to(ROOT),write=True) as f:f.write(data)
    print(json.dumps({'status':'PASS','report':str(REPORT.relative_to(ROOT)),
                      'report_sha256':hashlib.sha256(data).hexdigest(),'new_public_request_count':1}))
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as exc:
        code=str(exc) if type(exc) is ValueError and str(exc).replace('_','').isupper() else 'PUBLIC_CPU_INPUT_OR_CHECK_FAILED'
        print(json.dumps({'status':'FAIL','code':code}))
        raise SystemExit(1)
