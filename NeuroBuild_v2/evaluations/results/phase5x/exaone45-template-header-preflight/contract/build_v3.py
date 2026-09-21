"""Compile one EXAONE metadata-only CPU validator TU; reuse immutable pinned CPU archives only."""
from pathlib import Path
import hashlib, importlib.util, json, os, re, resource, shlex, signal, stat, subprocess, sys
from datetime import datetime, timezone
ROOT=Path('/home/a202192020/NeuroBuild_v2')
BASE=ROOT/'var/research/native-exaone45-contract'
BUILD=ROOT/'var/runtime-build/llama-native-contract-cpu'
OLD=ROOT/'var/reports/llama-native-contract-cpu-build-v4.json'
REPORT=BASE/'build-v3.json'; LOG=BASE/'build-v3.log'; TMP=BASE/'tmp-v3'
CPP=BASE/'validator_v3.cpp'; OBJECT=BASE/'validator-v3.o'; BINARY=BASE/'exaone45-cpu-validator-v3'
INVENTORY={'files':194,'bytes':66339126,'inventory_sha256':'b16b4bdbac76fe000c4c3d00553b43b6ee8a81115438f06ee7a67c7163cd0e76'}
PINS={'var/research/run_llama_build.py': 'e901372cc4f39dbee1e0574baf318fd2ae6edca167963f8bfe66274c06b8d52f', 'var/research/relink_llama_rpath.py': '52ab2e85128c1ff8fff978017aa7225268615d31ba653cdf20bb1c7f202333e0', 'var/research/verify_llama_build.py': '81285c40d1ee3862f747bbbc32fc9868d7a0604b4ea402dc8a8b5e9a1a06573e', 'var/research/build_native_contract_cpu.py': '0f46ea1d2009d882077a5735aef17a62ad6cd9d327e5635c32081b7f82299510', 'var/reports/llama-native-contract-cpu-build-v4.json': 'f149c7eda01dda9b36f4dba9327cb368bbdf2e3c591fa7db287b47787be7aea0', 'var/research/native-contract-validator/validator.cpp': '92ed10acd9be33d02d4cc6ea446dc2bea93ffb60b7d17ffc3c0f0268aab6c6b2', 'var/research/native-exaone45-contract/validator.cpp': '21292aa312940a41db31757f38039545b1d619b877754e1f268493eb3720e1f0', 'var/research/native-gemma4-contract/validator_v2.cpp': 'fecf647d431a3af0137f5e9459ddd8afece4e571d4a6a240dc2f4929acf9f20d', 'var/research/native-gemma4-contract/gemma4-cpu-validator-v2': '61abafb662bd944d10958c79cde6a5e308967af921beee6e63edcaa43e03a52d', 'var/research/native-gemma4-contract/build-v2.json': '1b6dce0e85790b267ec2514da8c81158c76b9d01a27aa6c2e584787a160e67ee'}
PINS.update({'var/research/native-exaone45-contract/validator_v2.cpp': 'ea747948a6e994b870c2aa21283ef84061752f2e37456587968f6b9749598d89', 'var/research/native-exaone45-contract/build.py': '44d6417eef50df522819acbb0d280c0a76f4b7b9baf53a242ef4de2f3c419126', 'var/research/native-exaone45-contract/build.json': '4fc1445dc63a61fe777fe65594a56156f7979b3041d42a70e0f93c758ca6689d', 'var/research/native-exaone45-contract/public_check.py': '41e4edb533045b1cb29f8ab99c0dfd0a04af16a4aa8ee5c117dc0a9037c46560', 'var/research/native-exaone45-contract/public-proof.json': 'c58985624c279226f8f9140ed7a5b298ef205280761c1cf45d80e7871e7f70c6', 'var/research/native-exaone45-contract/exaone45-cpu-validator': '7d0ecba0963b1ae07714e422f41cd7c05c1ee32bcb4c8cb8855f9c20aabd6fa1'})
PINS.update({'var/research/native-exaone45-contract/validator_v3.cpp': '61e95744bf27bee90b37719615e4a2c54c18b96b21ba65b9cd0f50bcc5ff93ab', 'var/research/native-exaone45-contract/build_v2.py': 'df5d703e80c5ed75d4c5002c5e0da16c65d661649e466da2d89b15964bb6372f', 'var/research/native-exaone45-contract/build-v2.json': '8d9c5f7bb4c3e7586df386b9ef8f9361ce375f75c6beb984a7ea93c5a956c8b3', 'var/research/native-exaone45-contract/public_check_v2.py': '69c1cfb6c4af783a4fce5328585a96f10c9d854f2dea520692f1d4c9d314c8ff', 'var/research/native-exaone45-contract/public-proof-v2.json': '76fe6c198061610ee93e62c65090988dab55b14f7a0c3c208facde1a33a16b81', 'var/research/native-exaone45-contract/exaone45-cpu-validator-v2': '57b11efe13d88847ef1059971f8b734a472207b1c606be5a564538337f1ff130', 'var/research/native-exaone45-contract/chat_template_continue_override.jinja': '7de6c8ba3df6db54564c7a63385cc29572c0a616d5848961e969ecbb8c349851'})
STOP=False

def require(ok, code):
 if not ok: raise ValueError(code)
def sha(path):
 with path.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def load(name,rel):
 require(sha(ROOT/rel)==PINS[rel],'HELPER_CHANGED')
 spec=importlib.util.spec_from_file_location(name,ROOT/rel);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def inventory(builder):
 rows=[]
 for p in sorted((BUILD/'llama').rglob('*')):
  if p.suffix not in ('.o','.a'): continue
  builder.owned_path(p);s=p.lstat();require(stat.S_ISREG(s.st_mode) and s.st_nlink==1,'UNSAFE_STATIC_INPUT')
  rows.append([str(p.relative_to(BUILD)),s.st_size,sha(p)])
 return {'files':len(rows),'bytes':sum(x[1] for x in rows),'inventory_sha256':hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()}
def cancel(*_):
 global STOP;STOP=True

def main():
 require(len(sys.argv)==1 and Path(sys.prefix)==ROOT/'.conda' and os.environ.get('CUDA_VISIBLE_DEVICES')=='','CPU_ENV')
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 builder=load('gemma_guardian','var/research/run_llama_build.py')
 supervisor=load('gemma_supervisor','var/research/relink_llama_rpath.py')
 cpu=load('gemma_cpu_settings','var/research/build_native_contract_cpu.py')
 for rel,h in PINS.items(): builder.owned_path(ROOT/rel);require(sha(ROOT/rel)==h,'PIN_CHANGED')
 old=json.loads(OLD.read_text()); require(old['status']=='COMPILE_PASS_NOT_EXECUTED','PREVIOUS_BUILD_INVALID')
 require(sha(ROOT/old['binary_path'])==old['binary_sha256'],'OLD_BINARY_CHANGED')
 require(sha(BUILD/'compile_commands.json')==old['compile_commands_sha256'],'COMMANDS_CHANGED')
 require(sha(BUILD/'CMakeCache.txt')==old['cmake_cache_sha256'],'CACHE_CHANGED')
 settings=cpu.validate_cache((BUILD/'CMakeCache.txt').read_text(),cpu.settings())
 verifier=load('gemma_source_verifier','var/research/verify_llama_build.py')
 source_validator=verifier.load_bootstrap();verifier.ws_module=source_validator
 workspace=source_validator.Workspace()
 try:
  bootstrap_path=ROOT/source_validator.REPORT
  require(sha(bootstrap_path)==old['source_report_sha256'],'BOOTSTRAP_CHANGED')
  bootstrap=verifier.read_json(workspace,bootstrap_path)
  meta={}
  for name in ('commit.json','tree.json'):
   path=ROOT/source_validator.DOWNLOAD_DIR/name
   entry=next(x for x in bootstrap['downloads'] if x['path']==str(path.relative_to(ROOT)))
   require(sha(path)==entry['sha256'],'TREE_METADATA_CHANGED')
   meta[name]=verifier.read_json(workspace,path)
  tree=source_validator.validate_tree(meta['commit.json'],meta['tree.json'])
  source_before=source_validator.verify_source(workspace,tree)
  require(source_before==bootstrap['source_verification']==old['source_before_build'],'SOURCE_CHANGED')
 finally:workspace.close()
 before=inventory(builder);require(before==INVENTORY,'STATIC_INVENTORY_CHANGED')
 commands=json.loads((BUILD/'compile_commands.json').read_text());entries=[x for x in commands if x['file'].endswith('/validator.cpp')]
 require(len(entries)==1,'AMBIGUOUS_COMMAND')
 original=shlex.split(entries[0]['command']);require(original[0]=='/usr/local/bin/g++','COMPILER')
 compile_command=list(original);compile_command[compile_command.index('-o')+1]=str(OBJECT);compile_command[compile_command.index('-c')+1]=str(CPP)
 link=shlex.split((BUILD/'CMakeFiles/nb-native-contract-validator.dir/link.txt').read_text())
 require(link[:3]==['/usr/local/bin/g++','-O3','-DNDEBUG'],'LINK_FLAGS')
 link=[str(OBJECT) if x=='CMakeFiles/nb-native-contract-validator.dir/validator.cpp.o' else x for x in link]
 link[link.index('-o')+1]=str(BINARY)
 link=[str(BUILD/x) if x.endswith('.a') else x for x in link]
 require(all(not x.endswith('.so') and 'cuda' not in x.lower() for x in link),'GPU_LINK')
 for p in (REPORT,LOG,TMP,OBJECT,BINARY): builder.owned_path(p,True);require(not p.exists() and not p.is_symlink(),'OUTPUT_EXISTS')
 TMP.mkdir(mode=0o700);builder.REPORT=REPORT;builder.TEMP=TMP;builder.created_record=False
 env=builder.build_environment({'HOME':str(ROOT.parent),'LANG':'C.UTF-8','LC_ALL':'C.UTF-8'})
 env.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
 pinned=dict(PINS);pinned['var/research/native-exaone45-contract/build_v3.py']=sha(Path(__file__))
 pinned['scripts/model_guard.py']=sha(ROOT/'scripts/model_guard.py')
 record={'kind':'EXAONE45_NATIVE_CONTRACT_CPU_BUILD','status':'RUNNING','source_pin':old['source_pin'],
 'started_at_utc':datetime.now(timezone.utc).isoformat(),'pinned_inputs':pinned,'settings':settings,
 'source_before_build':source_before,'prior_cpu_build_sha256':sha(OLD),'predecessor_gemma_build_sha256':sha(ROOT/'var/research/native-gemma4-contract/build-v2.json'),'revision_reason':'Preserve original template system-loss witness; source-equivalent continue-free candidate override and full public render parity', 'prior_failed_public_sha256':sha(BASE/'public-proof.json'),'reused_upstream_objects_before':before,'cuda_visible_devices':'',
 'native_validator_executed':False,'model_or_weights_loaded':False,'phases':[],
 'minimum_free_bytes':None,'maximum_own_allocated_bytes':0,'disk_reserve_bytes':20*1024**3,
 'own_allocation_budget_bytes':512*1024**2,'compile_commands_sha256':sha(BUILD/'compile_commands.json'),
 'link_definition_sha256':sha(BUILD/'CMakeFiles/nb-native-contract-validator.dir/link.txt')}
 builder.publish(record);builder.created_record=True
 handlers={s:signal.signal(s,cancel) for s in (signal.SIGINT,signal.SIGTERM)}
 try:
  with LOG.open('xb',buffering=0) as log:
   for name,command in [('compile-exaone-cpu',compile_command),('link-exaone-cpu',link)]:
    supervisor.run_phase(builder,name=name,command=command,env=env,log=log,record=record,phases=record['phases'],
     paths=[BASE],stop_requested=lambda:STOP,max_seconds=600,reserve_bytes=20*1024**3,budget_bytes=512*1024**2)
  require(inventory(builder)==before,'STATIC_INPUT_MUTATED')
  workspace=source_validator.Workspace()
  try:require(source_validator.verify_source(workspace,tree)==source_before,'SOURCE_MUTATED')
  finally:workspace.close()
  require(sha(ROOT/old['binary_path'])==old['binary_sha256'],'OLD_BINARY_MUTATED')
  for rel,h in pinned.items():require(sha(ROOT/rel)==h,'INPUT_MUTATED')
  dynamic=subprocess.run(['/usr/bin/readelf','--wide','--dynamic',str(BINARY)],env=env,capture_output=True,text=True,timeout=30,check=True)
  require(not dynamic.stderr,'ELF_STDERR')
  needed=re.findall(r'\(NEEDED\).*\[([^\]]+)\]',dynamic.stdout)
  require(bool(needed) and set(needed)<={'libstdc++.so.6','libm.so.6','libgcc_s.so.1','libc.so.6','libpthread.so.0','libdl.so.2','librt.so.1','ld-linux-x86-64.so.2'},'GPU_OR_UNKNOWN_LIBRARY')
  require(not re.search(r'\((?:RPATH|RUNPATH)\)',dynamic.stdout),'RPATH')
  record.update(status='COMPILE_PASS_NOT_EXECUTED',finished_at_utc=datetime.now(timezone.utc).isoformat(),
   binary_path=str(BINARY.relative_to(ROOT)),binary_sha256=sha(BINARY),binary_bytes=BINARY.stat().st_size,
   reused_upstream_objects_after=before,elf_needed=needed,elf_no_gpu_dependencies=True,elf_no_rpath=True,
   old_cpp_and_binary_unchanged=True,log_sha256=sha(LOG))
 except BaseException as error:
  record.update(status='FAILED',error_type=type(error).__name__,log_sha256=sha(LOG) if LOG.exists() else None)
  raise
 finally:
  builder.publish(record)
  for s,h in handlers.items():signal.signal(s,h)
 print(json.dumps({'status':record['status'],'report':str(REPORT.relative_to(ROOT)),'report_sha256':sha(REPORT),'binary_sha256':record['binary_sha256']}))

if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'FAIL','error_type':type(e).__name__}));raise SystemExit(1)
