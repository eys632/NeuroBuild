"""Fake-only supervisor evidence/env/report/pre-spawn disk checks."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from types import SimpleNamespace
import importlib.util,json,os,sys,tempfile
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('subject',ROOT/'var/research/run_llama_build.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
evidence={'kind':'LLAMA_SOURCE_TOOL_BOOTSTRAP','status':'PASS','llama_commit':m.PIN,'source_path':str(m.SOURCE.relative_to(m.ROOT)),'tool_path':str(m.TOOLS.relative_to(m.ROOT)),'source_verification':{'verified_blobs':3607,'verified_blob_bytes':172243701,'extra_or_missing_paths':0},'no_build':True,'no_weights':True,'no_gpu_calls':True,'no_tool_execution':True,'downloads':[{'path':'var/runtime-downloads/llama-'+m.PIN+'/cmake-3.23.5-linux-x86_64.tar.gz','bytes':46031464,'sha256':'bbd7ad93d2a14ed3608021a9466ae63db76a24efd1fae7a5f7798c1de7ab9344','url':'https://github.com/Kitware/CMake/releases/download/v3.23.5/cmake-3.23.5-linux-x86_64.tar.gz'}]}
m.verify_bootstrap(evidence)
mutations=[('status',lambda d:d.update(status='NOT_PASS')),('kind',lambda d:d.update(kind='other')),('pin',lambda d:d.update(llama_commit='x')),('source_path',lambda d:d.update(source_path='var/other')),('tool_path',lambda d:d.update(tool_path='var/other')),('blob_count',lambda d:d['source_verification'].update(verified_blobs=3606)),('blob_bytes',lambda d:d['source_verification'].update(verified_blob_bytes=0)),('extra_paths',lambda d:d['source_verification'].update(extra_or_missing_paths=False)),('no_gpu',lambda d:d.update(no_gpu_calls=1)),('cmake_size',lambda d:d['downloads'][0].update(bytes=0)),('cmake_hash',lambda d:d['downloads'][0].update(sha256='0'*64)),('cmake_url',lambda d:d['downloads'][0].update(url='https://example.invalid/file')),('duplicate',lambda d:d['downloads'].append(deepcopy(d['downloads'][0])))]
for name,mutate in mutations:
    bad=deepcopy(evidence);mutate(bad)
    try:m.verify_bootstrap(bad)
    except (AssertionError,KeyError):pass
    else:raise AssertionError(name)
blocked=['MAKEFLAGS','MFLAGS','GNUMAKEFLAGS','CUDAARCHS','NVCC_PREPEND_FLAGS','NVCC_APPEND_FLAGS','NVCC_CUSTOM_FLAG','CPATH','C_INCLUDE_PATH','CPLUS_INCLUDE_PATH','LIBRARY_PATH','GCC_EXEC_PREFIX','COMPILER_PATH','ENV','BASH_ENV','LD_PRELOAD','LD_LIBRARY_PATH','CMAKE_BUILD_PARALLEL_LEVEL','GGML_TEST','LLAMA_TEST','VLLM_TEST','TORCH_TEST','NCCL_TEST','PYTHONHOME','PYTHONPATH']
env=m.build_environment({**{k:'hostile-fixture' for k in blocked},'CUDA_VISIBLE_DEVICES':'3','HOME':str(ROOT.parent)})
assert not set(blocked)&set(env) and env['CUDA_VISIBLE_DEVICES']=='' and env['CUDA_DEVICE_ORDER']=='PCI_BUS_ID'
checks=['bootstrap_valid_and_13_tampered_rejections','25_inherited_override_names_removed']
with tempfile.TemporaryDirectory(prefix='llama-build-boundary-',dir=ROOT/'var/tmp') as td:
    td=Path(td);m.REPORT=td/'report.json';m.created_record=False
    m.REPORT.write_text('SENTINEL')
    try:m.publish({'new':True})
    except FileExistsError:pass
    else:raise AssertionError('initial report overwrite')
    assert m.REPORT.read_text()=='SENTINEL';m.REPORT.unlink()
    m.publish({'first':True});m.created_record=True;m.publish({'live_update':True})
    assert json.loads(m.REPORT.read_text())=={'live_update':True};checks.append('initial_report_no_clobber_and_owned_live_update')
    m.ROOT=td/'fake-project';m.SOURCE=m.ROOT/evidence['source_path'];m.TOOLS=m.ROOT/evidence['tool_path'];m.BUILD=m.ROOT/'var/runtime-build/new';m.TEMP=m.ROOT/'var/tmp/new';m.REPORT=m.ROOT/'var/reports/build.json';m.LOG=m.ROOT/'var/logs/build.log'
    for p in (m.SOURCE,m.TOOLS/'bin',m.REPORT.parent,m.LOG.parent,m.ROOT/'.conda'):p.mkdir(parents=True,exist_ok=True)
    (m.TOOLS/'bin/cmake').write_text('NEVER_EXECUTE')
    (m.ROOT/'var/reports/llama-source-bootstrap.json').write_text(json.dumps(evidence))
    fakepython=m.ROOT/'.conda/python';fakepython.write_text('NEVER_EXECUTE')
    actualpython=sys.executable;actualstat=os.statvfs;actualpopen=m.subprocess.Popen;original_handlers={s:m.signal.getsignal(s) for s in (m.signal.SIGTERM,m.signal.SIGINT)}
    calls=[]
    def forbidden(*a,**kw):calls.append(True);raise AssertionError('spawn before disk gate')
    try:
        sys.executable=str(fakepython);os.statvfs=lambda _:SimpleNamespace(f_bavail=10*1024**3,f_frsize=1);m.subprocess.Popen=forbidden;m.created_record=False
        try:m.main()
        except RuntimeError as error:assert str(error)=='PRE_PHASE_DISK_OR_STOP_BUDGET'
        else:raise AssertionError('disk gate skipped')
        assert not calls;checks.append('insufficient_disk_rejected_before_process_creation')
    finally:
        sys.executable=actualpython;os.statvfs=actualstat;m.subprocess.Popen=actualpopen
        for sig,handler in original_handlers.items():m.signal.signal(sig,handler)
proof={'status':'PASS','supervisor_sha256':sha256((ROOT/'var/research/run_llama_build.py').read_bytes()).hexdigest(),'checks':checks,'actual_builds':0,'source_downloads':0,'gpu_calls':0,'process_spawns':0}
p=ROOT/'var/research/llama-build-boundary-cpu-proof.json';p.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof,indent=2))
