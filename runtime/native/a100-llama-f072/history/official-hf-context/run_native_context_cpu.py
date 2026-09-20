#!/usr/bin/env python3
"""PREPARED ONLY: run after root verifies GGUF/header and the final CPU build.

Actual production requests stay in RAM/stdin. Report only split aggregates and
identity hashes; no source, gold, token IDs, model output or reasoning is saved.
Vocab-only native loading is not a model-inference call or a quality measure.
"""
from datetime import datetime, timezone
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import stat
import subprocess
import sys
from urllib.error import URLError

ROOT=Path('/home/a202192020/NeuroBuild_v2')
HEADER=Path('var/reports/qwen38-gguf-header.json')
BUILD=Path('var/reports/llama-native-contract-cpu-build-v2.json')
PUBLIC_RUNNER=Path('var/research/run_native_contract_cpu.py')
PARITY=Path('var/research/native-tokenizer-public-parity.json')
REPORT=Path('var/reports/native-contract-cpu-context.json')
MODEL=Path('var/models/ggml-org--Qwen3.8-27B-GGUF/efbb3b1f70a21d97fd4495240648405f7228554f/Qwen3.8-27B-Q4_K_M.gguf')
REVISION='efbb3b1f70a21d97fd4495240648405f7228554f'
MODEL_SHA='c600de0300ae8a0eb3a6c0b8b5561b8b96f16bd2c863c2a66c42de29d391a747'
MODEL_BYTES=18973870528
V2_FREEZE=Path('evaluations/hardening_v2_dataset_freeze.json')
SPLITS={
 'exposed120':(Path('evaluations/requirement_hardening_v1_exposed_regression.jsonl'),120,'7e5b9a05932df7aafdbf683655b044b3e3b25cbffb4115d298e1490aecbc7a5b'),
 'v2_length80':(Path('evaluations/requirement_hardening_v2_holdout.jsonl'),80,'7416f05613b1490358672f3926770dbd8653e676577eeee6ba65f863b27cec40'),
}
PINS={
 str(PARITY):'79c4448b7ee949add0a80e8a7f0fc0d73575aaf01ff6e52beb3cfae8434ea1bd',
 str(V2_FREEZE):'34e3823a6633faa5237849725f4b3120dee348aa19208d0c62403fedda5c5995',
 'src/neurobuild/infrastructure/local_model.py':'3ebef3a1b3cf16b577566c7644952ac5da0def1d1dc11cc0d0b01c581b9d9f1c',
}
SAFE_ENV={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','LC_ALL':'C.UTF-8','CUDA_VISIBLE_DEVICES':'',
          'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','PYTHONNOUSERSITE':'1'}
# Same PID survives exec; only this owned CPU child is killed if its parent dies.
EXEC_BOOTSTRAP="""import ctypes,os,resource,signal,sys
expected=int(sys.argv[1])
if os.getppid()!=expected:raise SystemExit(2)
if ctypes.CDLL(None,use_errno=True).prctl(1,signal.SIGKILL,0,0,0)!=0:raise SystemExit(2)
if os.getppid()!=expected:os.kill(os.getpid(),signal.SIGKILL)
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
os.execve(sys.argv[2],sys.argv[2:],dict(os.environ))
"""


def require(ok,code):
 if not ok:raise ValueError(code)


def own(path):
 require(path.is_relative_to(ROOT) and '..' not in path.parts,'OUTSIDE_PROJECT')
 for p in (path,*path.parents):
  if p==ROOT:break
  info=p.lstat();require(info.st_uid==os.getuid() and not stat.S_ISLNK(info.st_mode),'UNSAFE_INPUT_PATH')
 require(path.is_file() and path.stat().st_nlink==1,'INPUT_NOT_OWN_REGULAR')


def sha(path):
 with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def read_bound(path,expected,cap):
 own(path);require(type(expected) is str and re.fullmatch('[a-f0-9]{64}',expected),'EXACT_HASH_REQUIRED')
 require(path.stat().st_size<=cap,'INPUT_TOO_LARGE')
 raw=path.read_bytes();require(hashlib.sha256(raw).hexdigest()==expected,'INPUT_HASH_MISMATCH')
 return raw


def stat_key(info):
 return (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns)


def bind_model(header):
 require(header['kind']=='GGUF_HEADER_AUDIT' and header['status']=='PASS'
         and header['model_path']==str(MODEL) and header['file_sha256']==MODEL_SHA
         and type(header['file_bytes']) is int and header['file_bytes']==MODEL_BYTES
         and header['revision']==REVISION and header['gpu_or_native_execution'] is False,'HEADER_AUDIT_REQUIRED')
 path=ROOT/MODEL;own(path)
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
 with os.fdopen(fd,'rb') as stream:
  before=os.fstat(stream.fileno());require(before.st_size==MODEL_BYTES,'GGUF_SIZE_CHANGED')
  require(hashlib.file_digest(stream,'sha256').hexdigest()==MODEL_SHA,'GGUF_HASH_CHANGED')
  require(stat_key(before)==stat_key(os.fstat(stream.fileno())),'GGUF_CHANGED_DURING_HASH')
 require(stat_key(before)==stat_key(path.stat()),'GGUF_PATH_CHANGED')
 return stat_key(before)


def capture_requests(client,raw,expected_count):
 """Read only input/context fields for transport. Companion gold is neither used nor emitted."""
 class Capture:
  def open(self,request,**kwargs):self.body=request.data;raise URLError('CPU_CAPTURE')
 capture=Capture();client._opener=capture
 rows=[json.loads(line) for line in raw.splitlines() if line.strip()]
 require(len(rows)==expected_count,'SPLIT_COUNT_MISMATCH')
 requests=[]
 for row in rows:
  require(type(row) is dict and type(row.get('input')) is str and type(row.get('context')) is dict,'INVALID_SOURCE_SHAPE')
  capture.body=None
  try:client.complete(row['input'],axis_convention=row['context'].get('axis_convention'))
  except Exception as error:
   require(getattr(error,'code',None)=='LOCAL_MODEL_UNAVAILABLE','PRODUCTION_CAPTURE_REJECTED')
  require(capture.body is not None,'REQUEST_NOT_CAPTURED')
  requests.append(json.loads(capture.body))
 return requests


def validate_native(value,count,accepts,rejects):
 # Only selected fixed metadata is persisted; unknown native output keys fail.
 keys={'status','kind','schema_cases_accepted','schema_cases_rejected','native_final_content_exact_cases',
       'native_grammar_generation_prompt_prefilled','native_grammar_prefill_bytes','core_dump_limit_zero',
       'native_sampling_schema_binding','native_request_grammar_nonempty','grammar_lazy','grammar_triggers',
       'native_grammar_bytes','standalone_grammar_bytes','native_request_prompt_bytes','model_context_created',
       'backend_init_called','weight_tensors_loaded','native_tokenization','native_vocab_grammar_cases_accepted',
       'native_vocab_grammar_cases_rejected','native_vocab_grammar_eog_checked','tokenizer_metadata_parity',
       'tokenizer_metadata_parity_cases','embedded_template_exact_match','native_embedded_vs_external_prompt_grammar_match',
       'input_count','min_input_tokens','max_input_tokens','max_input_plus_output','discarded_stderr_bytes'}
 require(type(value) is dict and set(value)==keys,'NATIVE_OUTPUT_SHAPE_INVALID')
 require(value['kind']=='NATIVE_CONTRACT_CPU_PREFLIGHT' and value['status']=='PASS'
         and value['native_tokenization']=='PASS_VOCAB_ONLY' and value['tokenizer_metadata_parity']=='PASS','NATIVE_CHECK_FAILED')
 for key in ('model_context_created','backend_init_called','weight_tensors_loaded','grammar_lazy'):
  require(value[key] is False,'UNEXPECTED_NATIVE_EXECUTION')
 for key in ('core_dump_limit_zero','native_sampling_schema_binding','native_request_grammar_nonempty',
             'native_grammar_generation_prompt_prefilled','native_vocab_grammar_eog_checked',
             'embedded_template_exact_match','native_embedded_vs_external_prompt_grammar_match'):
  require(value[key] is True,'NATIVE_BOUNDARY_UNCONFIRMED')
 for key,expected in {'input_count':count,'schema_cases_accepted':accepts,'schema_cases_rejected':rejects,
                     'native_final_content_exact_cases':accepts,'native_vocab_grammar_cases_accepted':accepts,
                     'native_vocab_grammar_cases_rejected':rejects,'tokenizer_metadata_parity_cases':20,
                     'grammar_triggers':0,'discarded_stderr_bytes':0}.items():
  require(type(value[key]) is int and value[key]==expected,'NATIVE_COUNT_MISMATCH')
 for key in ('min_input_tokens','max_input_tokens','max_input_plus_output','native_grammar_bytes',
             'standalone_grammar_bytes','native_request_prompt_bytes','native_grammar_prefill_bytes'):
  require(type(value[key]) is int and value[key]>=0,'INVALID_NATIVE_COUNT')
 require(0<value['min_input_tokens']<=value['max_input_tokens']
         and value['max_input_plus_output']==value['max_input_tokens']+768<=4096,'CONTEXT_CAP_EXCEEDED')
 return value


def main(argv=None):
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--header-report-sha256',required=True)
 parser.add_argument('--cpu-build-report-sha256',required=True)
 parser.add_argument('--public-runner-sha256',required=True)
 args=parser.parse_args(argv)
 require(Path(sys.prefix)==ROOT/'.conda' and os.environ.get('CUDA_VISIBLE_DEVICES')=='','EXPLICIT_CPU_ENV_REQUIRED')
 resource.setrlimit(resource.RLIMIT_CORE,(0,0)) # Before any source/context payload is read.
 output=ROOT/REPORT
 require(not output.exists() and not output.is_symlink(),'REPORT_ALREADY_EXISTS')
 for relative,expected in PINS.items():read_bound(ROOT/relative,expected,2*1024**2)
 read_bound(ROOT/PUBLIC_RUNNER,args.public_runner_sha256,65536)
 build=json.loads(read_bound(ROOT/BUILD,args.cpu_build_report_sha256,2*1024**2))
 header=json.loads(read_bound(ROOT/HEADER,args.header_report_sha256,2*1024**2))
 # Require root's completed header proof BEFORE opening either evaluation dataset.
 model_stat=bind_model(header)
 sys.path.insert(0,str(ROOT/'src'))
 spec=importlib.util.spec_from_file_location('pinned_native_public_runner',ROOT/PUBLIC_RUNNER)
 public=importlib.util.module_from_spec(spec);spec.loader.exec_module(public)
 for path,expected in public.PINS.items():read_bound(path,expected,2*1024**2)
 require(type(build['binary_path']) is str,'INVALID_CPU_BINARY_PATH')
 own(ROOT/build['binary_path'])
 binary,needed=public.inspect_cpu_binary(build)
 cpp_path='var/research/native-contract-validator/validator.cpp'
 cpp_sha=build['pinned_inputs'][cpp_path]
 read_bound(ROOT/cpp_path,cpp_sha,128*1024) # Exact completed CPU-report pin, including the reviewed compile correction.
 freeze=json.loads(read_bound(ROOT/V2_FREEZE,PINS[str(V2_FREEZE)],2*1024**2))
 require(freeze['dataset_version']=='requirement_hardening_v2' and freeze['cases']==80
         and freeze['sha256'][str(SPLITS['v2_length80'][0])]==SPLITS['v2_length80'][2],'V2_FREEZE_BINDING_FAILED')
 parity=json.loads(read_bound(ROOT/PARITY,PINS[str(PARITY)],2*1024**2))['tokenizer_parity']
 require(type(parity) is list and len(parity)==20,'PUBLIC_PARITY_COUNT_CHANGED')
 corpus=public.corpus();public_request=public.capture_request()
 client=public.LocalRequirementClient('http://127.0.0.1:8003','neurobuild-qwen38-27b-q4-k-m',
        prompt_path=public.PROMPT,schema_path=public.SCHEMA,generation_contract='2.0',
        protocol='llama_cpp_json_schema',sampling_profile='qwen38_nonthinking_llama_cpp',max_tokens=768)
 groups={}
 for name,(dataset,count,expected) in SPLITS.items():
  own(ROOT/MODEL);require(stat_key((ROOT/MODEL).stat())==model_stat,'GGUF_CHANGED_BEFORE_RUN')
  requests=capture_requests(client,read_bound(ROOT/dataset,expected,2*1024**2),count)
  bundle={'request':public_request,'cases':corpus,'context_requests':requests,'max_output_tokens':768,'tokenizer_parity':parity}
  payload=json.dumps(bundle,ensure_ascii=False).encode();require(len(payload)<=16*1024**2,'BUNDLE_TOO_LARGE')
  result=subprocess.run([str(ROOT/'.conda/bin/python'),'-I','-B','-c',EXEC_BOOTSTRAP,str(os.getpid()),
                         str(binary),str(public.TEMPLATE),str(public.SCHEMA),str(ROOT/MODEL)],
                        input=payload,cwd=ROOT,env=SAFE_ENV,capture_output=True,timeout=180,check=False)
  require(result.returncode==0 and not result.stderr and len(result.stdout)<65536,'NATIVE_CPU_PROBE_FAILED')
  native=validate_native(json.loads(result.stdout),count,sum(row['accept'] for row in corpus),sum(not row['accept'] for row in corpus))
  groups[name]={'dataset_sha256':expected,'input_count':count,'min_input_tokens':native['min_input_tokens'],
                'max_input_tokens':native['max_input_tokens'],'max_input_plus_output':native['max_input_plus_output'],
                'native':native,'bundle_sha256':hashlib.sha256(payload).hexdigest()}
  del payload,bundle,requests,result
 require(stat_key((ROOT/MODEL).stat())==model_stat,'GGUF_CHANGED_AFTER_RUN')
 report={'kind':'NATIVE_CONTEXT_CPU_PROOF','status':'PASS','at_utc':datetime.now(timezone.utc).isoformat(),
         'splits':groups,'max_output_tokens':768,'max_context_tokens':4096,'model_inference_calls':0,
         'gpu_or_network_calls':0,'vocab_only_model_open_count':2,'raw_inputs_tokens_outputs_saved':False,
         'header_sha256':args.header_report_sha256,'cpu_build_report_sha256':args.cpu_build_report_sha256,
         'public_runner_sha256':args.public_runner_sha256,'binary_sha256':sha(binary),'elf_needed':needed,
         'cpu_cpp_source_sha256':cpp_sha,
         'helper_sha256':sha(Path(__file__)),'pinned_inputs':PINS,'gguf_sha256':MODEL_SHA,
         'gold_fields_used_for_scoring':False,'limits':['Context fit and vocab/grammar parity only; no semantic accuracy or model adoption claim.',
             'V2 inputs are processed only for length; prior exposure/addendum remains, no full-blinding claim.']}
 with output.open('x') as stream:json.dump(report,stream,indent=2);stream.write('\n')
 print(json.dumps({'status':'PASS','report':str(REPORT),'splits':{key:{k:v for k,v in value.items() if k in ('input_count','min_input_tokens','max_input_tokens','max_input_plus_output')} for key,value in groups.items()},'model_inference_calls':0}))


if __name__=='__main__':
 try:main()
 except Exception as error:
  code=str(error) if type(error) is ValueError and re.fullmatch('[A-Z0-9_]+',str(error)) else 'INPUT_OR_IO_ERROR'
  print(json.dumps({'status':'FAIL','error_type':type(error).__name__,'code':code}));raise SystemExit(1)
