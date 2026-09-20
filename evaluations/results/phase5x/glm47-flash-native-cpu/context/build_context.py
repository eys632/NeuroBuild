"""Compile one GLM47_FLASH metadata-only CPU validator TU; reuse immutable pinned CPU archives only."""
from pathlib import Path
import hashlib, importlib.util, json, os, re, resource, shlex, signal, stat, subprocess, sys
from datetime import datetime, timezone
ROOT=Path('/home/a202192020/NeuroBuild_v2')
BASE=ROOT/'var/research/native-glm47-contract'
BUILD=ROOT/'var/runtime-build/llama-native-contract-cpu'
OLD=ROOT/'var/reports/llama-native-contract-cpu-build-v4.json'
REPORT=BASE/'context-build.json'; LOG=BASE/'context-build.log'; TMP=BASE/'context-tmp'
CPP=BASE/'context_validator.cpp'; OBJECT=BASE/'context-validator.o'; BINARY=BASE/'glm47-context-cpu-validator'
INVENTORY={'files':194,'bytes':66339126,'inventory_sha256':'b16b4bdbac76fe000c4c3d00553b43b6ee8a81115438f06ee7a67c7163cd0e76'}
PINS={'var/research/run_llama_build.py': 'e901372cc4f39dbee1e0574baf318fd2ae6edca167963f8bfe66274c06b8d52f', 'var/research/relink_llama_rpath.py': '52ab2e85128c1ff8fff978017aa7225268615d31ba653cdf20bb1c7f202333e0', 'var/research/verify_llama_build.py': '81285c40d1ee3862f747bbbc32fc9868d7a0604b4ea402dc8a8b5e9a1a06573e', 'var/research/build_native_contract_cpu.py': '0f46ea1d2009d882077a5735aef17a62ad6cd9d327e5635c32081b7f82299510', 'var/reports/llama-native-contract-cpu-build-v4.json': 'f149c7eda01dda9b36f4dba9327cb368bbdf2e3c591fa7db287b47787be7aea0', 'var/research/native-contract-validator/validator.cpp': '92ed10acd9be33d02d4cc6ea446dc2bea93ffb60b7d17ffc3c0f0268aab6c6b2', 'var/research/native-glm47-contract/validator.cpp': 'c99c5759b65a4ae4a4f31df9f3fda75cdcd454771b126683afe7c75d7707edf9'}
PINS.update({'var/research/native-glm47-contract/validator.cpp': 'c99c5759b65a4ae4a4f31df9f3fda75cdcd454771b126683afe7c75d7707edf9', 'var/research/native-glm47-contract/build.py': '5c2a98c7aa2f86e293ec3bd5ff37ddaa9c7cd3fa461e7ccb8065289bacb08e86', 'var/research/native-glm47-contract/public_check.py': '2ee13e3092232beecfdf0a550de2bd5ba18e1935901ec8d406303cc06722e43b', 'var/research/native-glm47-contract/build.json': 'fe348c07e21c1c601e1a48a529cd5a8de00938b647da9dd926480b9e0d213c74', 'var/research/native-glm47-contract/glm47-cpu-validator': '4bcff0326ead4a3572394cf8fb701aea78e77586ea15bbec32dfb4e4f498ba83', 'var/research/native-glm47-contract/public-proof.json': '7eba381e83c09f14d9dcfaf898e20dd02badc3cc02362ac5e8eab5d9eb9b5b43', 'var/research/native-glm47-contract/official-tokenizer-fixture.json': 'e67bd4d05462587e0466f092351ada8c8fa4efdd9a10da0b4cecb25a4d3dc8f3', 'var/research/native-glm47-contract/validator_v2.cpp': 'd206571cdc4b6893a1bf6565a260303b6d5c1ea1fb7b4e7efba46d60b0046d29'})
PINS.update({'var/research/native-glm47-contract/validator_v2.cpp': 'd206571cdc4b6893a1bf6565a260303b6d5c1ea1fb7b4e7efba46d60b0046d29', 'var/research/native-glm47-contract/build_v2.py': '18f1af03d12c4e0fa4353e48bd935dcc11a1009b987d2359cb4a57d640910f26', 'var/research/native-glm47-contract/public_check_v2.py': '1f138f3cd54b0f3e660c0f0afe866b31db2f4c06d4d86646cdada249f504c996', 'var/research/native-glm47-contract/build-v2.json': '62d6f9eee9857f985248f2c744199a189dd13d8c2b73229b83cb248b3688fd15', 'var/research/native-glm47-contract/glm47-cpu-validator-v2': '07da57f39ef3d68f9b59e46ffb41d7c416d58c8a444e81b594623c4d2f892e1f', 'var/research/native-glm47-contract/public-proof-v2.json': '534f6aba740056ea8f959a1834bf6ce66f299952bfbe26c35d19b9f71385ae01', 'var/research/native-glm47-contract/validator_v3.cpp': 'c0676b4c6f4bb962bc228cc041ee3fba85fdcd1824e68d17ab7a2c7eb4adf272'})
PINS.update({'var/research/native-glm47-contract/validator_v3.cpp': 'c0676b4c6f4bb962bc228cc041ee3fba85fdcd1824e68d17ab7a2c7eb4adf272', 'var/research/native-glm47-contract/build_v3.py': 'd4fc565e3cac0f49b949fba9d059a166805d4befc0a6e7d7a96139a3b522efc4', 'var/research/native-glm47-contract/public_check_v3.py': '06dc94dc5211e84c91fedde470ea5aebbc11bd93f1bd83e6a3b3aae85f8ffc45', 'var/research/native-glm47-contract/build-v3.json': 'befeeb0c258f9c570b6c148e78e426979811a1b628090bf0ad1bc25ceac2cbef', 'var/research/native-glm47-contract/glm47-cpu-validator-v3': '19e5641f0e6051348a96f06fe6986cb40c5228e83bb352a2c21ea9317fcad3cb', 'var/research/native-glm47-contract/public-proof-v3.json': 'd8f8fe1faf2ee73b06f6df35d16dba3a29cb78ad41af35a8a1be6cff888ac85c', 'var/research/native-glm47-contract/context_validator.cpp': 'fe5f71fdce897d4138b77f670d5931ea685715b29b2795d50219f80b25510410'})
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
 builder=load('glm_guardian','var/research/run_llama_build.py')
 supervisor=load('glm_supervisor','var/research/relink_llama_rpath.py')
 cpu=load('glm_cpu_settings','var/research/build_native_contract_cpu.py')
 for rel,h in PINS.items(): builder.owned_path(ROOT/rel);require(sha(ROOT/rel)==h,'PIN_CHANGED')
 old=json.loads(OLD.read_text()); require(old['status']=='COMPILE_PASS_NOT_EXECUTED','PREVIOUS_BUILD_INVALID')
 require(sha(ROOT/old['binary_path'])==old['binary_sha256'],'OLD_BINARY_CHANGED')
 require(sha(BUILD/'compile_commands.json')==old['compile_commands_sha256'],'COMMANDS_CHANGED')
 require(sha(BUILD/'CMakeCache.txt')==old['cmake_cache_sha256'],'CACHE_CHANGED')
 settings=cpu.validate_cache((BUILD/'CMakeCache.txt').read_text(),cpu.settings())
 verifier=load('glm_source_verifier','var/research/verify_llama_build.py')
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
 pinned=dict(PINS);pinned['var/research/native-glm47-contract/build_context.py']=sha(Path(__file__))
 pinned['scripts/model_guard.py']=sha(ROOT/'scripts/model_guard.py')
 record={'kind':'GLM47_FLASH_NATIVE_CONTRACT_CPU_BUILD','status':'RUNNING','source_pin':old['source_pin'],
 'started_at_utc':datetime.now(timezone.utc).isoformat(),'pinned_inputs':pinned,'settings':settings,
 'source_before_build':source_before,'prior_cpu_build_sha256':sha(OLD),'revision_reason':'Separate GLM context-only CPU TU; actual captured full prompt bytes and token lengths; public official20 proof reused without tokenizer corpus replay', 'prior_public_v2_sha256':PINS['var/research/native-glm47-contract/public-proof-v2.json'], 'prior_failed_public_sha256':PINS['var/research/native-glm47-contract/public-proof.json'], 'reused_upstream_objects_before':before,'cuda_visible_devices':'',
 'native_validator_executed':False,'model_or_weights_loaded':False,'phases':[],
 'minimum_free_bytes':None,'maximum_own_allocated_bytes':0,'disk_reserve_bytes':20*1024**3,
 'own_allocation_budget_bytes':512*1024**2,'compile_commands_sha256':sha(BUILD/'compile_commands.json'),
 'link_definition_sha256':sha(BUILD/'CMakeFiles/nb-native-contract-validator.dir/link.txt')}
 builder.publish(record);builder.created_record=True
 handlers={s:signal.signal(s,cancel) for s in (signal.SIGINT,signal.SIGTERM)}
 try:
  with LOG.open('xb',buffering=0) as log:
   for name,command in [('compile-glm-cpu',compile_command),('link-glm-cpu',link)]:
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
