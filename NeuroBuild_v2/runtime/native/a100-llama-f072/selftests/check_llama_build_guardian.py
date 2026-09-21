"""Only newly created, same-UID CPU process trees; no cmake/build/GPU."""
from pathlib import Path
from hashlib import sha256
import ctypes,importlib.util,json,os,signal,subprocess,sys,tempfile,time
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('build_review_subject',ROOT/'var/research/run_llama_build.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert ctypes.CDLL(None,use_errno=True).prctl(36,1,0,0,0)==0  # adopt only this test's orphaned descendants
records=[]
def wait_path(p,timeout=5):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        if p.exists() and p.stat().st_size:
            try:return json.loads(p.read_text())
            except ValueError:pass
        time.sleep(.02)
    raise AssertionError('fixture did not become ready: '+p.name)
def stopped(pid):
    try:
        fd=os.open('/proc/'+str(pid),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    except FileNotFoundError:return True
    try:
        assert os.fstat(fd).st_uid==os.getuid()
        f=os.open('stat',os.O_RDONLY,dir_fd=fd)
        with os.fdopen(f) as stream:state=stream.read().rsplit(')',1)[1].split()[0]
        return state=='Z'
    finally:os.close(fd)
def reap(pid):
    try:os.waitpid(pid,os.WNOHANG)
    except ChildProcessError:pass
with tempfile.TemporaryDirectory(prefix='llama-guardian-test-',dir=ROOT/'var/tmp') as tmp:
    tmp=Path(tmp)
    fake=tmp/'fake_compiler.py'
    fake.write_text("""from pathlib import Path
import json,os,signal,subprocess,sys,time
signal.signal(signal.SIGTERM,signal.SIG_IGN)
grandchild=subprocess.Popen([sys.executable,'-c','import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(60)'])
Path(sys.argv[1]).write_text(json.dumps({'native_pid':os.getpid(),'grandchild_pid':grandchild.pid,'pgid':os.getpgrp()}))
if sys.argv[2]=='normal':raise SystemExit(0)
time.sleep(60)
""")
    for case in ('normal','supervisor_sigkill','supervisor_sigterm'):
        ready=tmp/(case+'-ready.json');cleanup=tmp/(case+'-cleanup.json');identity=tmp/(case+'-identity.json')
        supervisor_code="""from pathlib import Path
import json,os,subprocess,sys
p=subprocess.Popen([sys.executable,'-c',sys.argv[1],str(os.getpid()),sys.argv[2],sys.executable,sys.argv[3],sys.argv[4],sys.argv[5]],start_new_session=True)
Path(sys.argv[6]).write_text(json.dumps({'guardian_pid':p.pid}))
raise SystemExit(p.wait())
"""
        supervisor=subprocess.Popen([sys.executable,'-c',supervisor_code,m.BOOTSTRAP,str(cleanup),str(fake),str(ready),'normal' if case=='normal' else 'wait',str(identity)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        ids={}
        try:
            ids=wait_path(identity);ids.update(wait_path(ready))
            assert ids['pgid']==ids['native_pid']
            if case=='supervisor_sigkill':supervisor.kill()
            elif case=='supervisor_sigterm':supervisor.terminate()
            supervisor.wait(timeout=5)
            proof=wait_path(cleanup)
            assert proof['guardian_pid']==ids['guardian_pid'] and proof['native_pid']==ids['native_pid']
            assert proof['cleanup_complete'] and proof['native_reaped'] and proof['term_sent'] and proof['kill_sent']
            end=time.monotonic()+3
            while time.monotonic()<end and not all(stopped(ids[k]) for k in ('guardian_pid','native_pid','grandchild_pid')):time.sleep(.02)
            assert all(stopped(ids[k]) for k in ('guardian_pid','native_pid','grandchild_pid'))
            records.append({'case':case,'status':'PASS','supervisor_exit':supervisor.returncode,'guardian_cleanup':proof,'all_owned_fixture_processes_stopped':True})
        finally:
            if supervisor.poll() is None:supervisor.kill();supervisor.wait(timeout=3)
            # Only groups returned by this test's own child tree; no process scan.
            for key in ('native_pid','guardian_pid'):
                if key in ids:
                    try:os.killpg(ids[key],signal.SIGKILL)
                    except ProcessLookupError:pass
            for key in ('guardian_pid','native_pid','grandchild_pid'):
                if key in ids:reap(ids[key])
    for case,expected_parent,command in [('parent_mismatch',1,[sys.executable,'-c','raise SystemExit(99)']),('spawn_error',os.getpid(),[str(tmp/'missing-command')])]:
        report=tmp/(case+'.json')
        p=subprocess.Popen([sys.executable,'-c',m.BOOTSTRAP,str(expected_parent),str(report),*command],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        p.wait(timeout=5);proof=wait_path(report)
        assert proof['cleanup_complete'] and proof['native_pid'] is None and p.returncode!=0
        records.append({'case':case,'status':'PASS','guardian_exit':p.returncode,'native_started':False})
proof={'status':'PASS','supervisor_sha256':sha256((ROOT/'var/research/run_llama_build.py').read_bytes()).hexdigest(),'cases':records,'native_flag_env_names_removed':['NVCC_PREPEND_FLAGS','NVCC_APPEND_FLAGS'],'scope':'Synthetic new same-UID CPU process trees only; no cmake, source download, build, GPU query or model call. Guardian itself SIGKILL or kernel uninterruptible task is not an absolute cleanup guarantee.'}
p=ROOT/'var/research/llama-build-guardian-cpu-proof.json';p.write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps({'status':'PASS','cases':len(records),'path':str(p.relative_to(ROOT)),'sha256':sha256(p.read_bytes()).hexdigest(),'supervisor_sha256':proof['supervisor_sha256']},indent=2))
