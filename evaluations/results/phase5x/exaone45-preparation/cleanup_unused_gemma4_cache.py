"""Remove only one inactive, fully verified re-downloadable Gemma GGUF cache file."""
from pathlib import Path
from datetime import datetime, timezone
import fcntl,hashlib,json,os,stat,sys
ROOT=Path('/home/a202192020/NeuroBuild_v2')
MANIFEST=ROOT/'runtime/models/gemma4-31b-qat-q4-0.json'
MANIFEST_SHA='16d471fc5bb8ae266015d73b0a648e2b576dab6e6e453de8c28fdc0f1a8a6e3c'
REV='59dde24573e7e61570dba08b18a2e1fe246955ed'
BASE=ROOT/'var/models/google--gemma-4-31B-it-qat-q4_0-gguf'/REV
REPORT=ROOT/'var/reports/unused-gemma4-weight-cache-cleanup.json'

def sha(path):
 with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def own(path):
 for p in (path,*path.parents):
  s=p.lstat();assert s.st_uid==os.getuid() and not stat.S_ISLNK(s.st_mode),str(p)
  if p==ROOT:break
 else:raise AssertionError('not in project')
def free():
 s=os.statvfs(ROOT);return s.f_bavail*s.f_frsize

def no_own_users(inodes):
 checked=0;session_limits=[]
 for proc in Path('/proc').iterdir():
  if not proc.name.isdecimal():continue
  anchor=None
  try:
   if proc.stat().st_uid!=os.getuid():continue
   anchor=os.open(proc,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
   # A numeric PID may have been reused after the first metadata lookup.
   # All contents below stay relative to this directory FD and verified UID.
   if os.fstat(anchor).st_uid!=os.getuid():continue
   with os.fdopen(os.open('cmdline',os.O_RDONLY,dir_fd=anchor),'rb') as f:
    command=f.read()
   assert str(BASE).encode() not in command and REV.encode() not in command,'active own model command'
   try:
    mapfd=os.open('maps',os.O_RDONLY,dir_fd=anchor)
   except PermissionError:
    # Same-UID login services remain nondumpable. Their cmdline and kernel
    # comm identify session infrastructure, not an inference runtime. Preserve
    # this limitation explicitly; any other inaccessible own process blocks.
    with os.fdopen(os.open('comm',os.O_RDONLY,dir_fd=anchor)) as f:comm=f.read().strip()
    argv0=command.split(b'\0')[0].decode()
    assert (comm,argv0) in {('(sd-pam)','(sd-pam)'),('sshd','sshd: a202192020@notty')},'uninspected own process'
    session_limits.append({'pid':int(proc.name),'comm':comm,'maps_and_descriptors':'PERMISSION_DENIED_SESSION_INFRASTRUCTURE'})
    continue
   with os.fdopen(mapfd) as f:maps=f.read()
   assert str(BASE) not in maps,'active own model mapping'
   descriptors=os.open('fd',os.O_RDONLY|os.O_DIRECTORY,dir_fd=anchor)
   try:
    for name in os.listdir(descriptors):
     try:
      info=os.stat(name,dir_fd=descriptors)
      assert (info.st_dev,info.st_ino) not in inodes,'active own model descriptor'
     except FileNotFoundError:pass
   finally:os.close(descriptors)
   checked+=1
  except (FileNotFoundError,ProcessLookupError):continue
  finally:
   if anchor is not None:os.close(anchor)
 return {'maps_and_descriptors_checked':checked,'permission_limited_session_processes':session_limits}

def main():
 assert sys.argv[1:]==['--remove']
 own(MANIFEST);assert sha(MANIFEST)==MANIFEST_SHA
 build=ROOT/'var/reports/llama-cuda-build-verified.json'
 own(build);assert json.loads(build.read_text())['status']=='COMPILE_PASS_NOT_RUNTIME_VALIDATED'
 shutdown=ROOT/'evaluations/results/phase5x/exposed-native-gemma4-diagnostic/resource_final.json'
 assert sha(shutdown)=='526e5247cc6eb881a0ef364f5e97a9c5bc7e8732224cf5796b0264174e2501ed'
 header=ROOT/'var/reports/gemma4-gguf-header-v2.json'
 assert sha(header)=='d867a3300b2a93534fb1b480e8e42b30321c894aaec05b5729a529e848817756'
 s=json.loads(shutdown.read_text());assert s['state']=='STOPPED' and s['child_exit_code']==0 and s['shutdown']['child_reaped'] is True
 assert s['model_path']==str(BASE/'gemma-4-31B_q4_0-it.gguf')
 own(BASE);own(REPORT.parent);assert not REPORT.exists() and not REPORT.is_symlink()
 manifest=json.loads(MANIFEST.read_text());assert manifest['revision']==REV
 assert json.loads((BASE/'neurobuild-manifest.json').read_text())==manifest
 entries=[x for x in manifest['files'] if x['name']=='gemma-4-31B_q4_0-it.gguf']
 assert len(entries)==1 and entries[0]['bytes']==17651001568 and entries[0]['sha256']=='179cfb99212709597eae5929112cfca677e1bbf566178b479ae1da0c4772874b'
 lock=ROOT/'var/run/model-server.lock';own(lock)
 lockfd=os.open(lock,os.O_RDWR|os.O_CLOEXEC|os.O_NOFOLLOW)
 fcntl.flock(lockfd,fcntl.LOCK_EX|fcntl.LOCK_NB)
 dirfd=os.open(BASE,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 snapshots={}
 for e in entries:
  p=BASE/e['name'];own(p);s=p.lstat()
  assert stat.S_ISREG(s.st_mode) and s.st_nlink==1 and s.st_size==e['bytes']
  snapshots[e['name']]=(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
 checked=no_own_users({x[:2] for x in snapshots.values()})
 before=free();removed=[]
 report={'kind':'REMOVE_VERIFIED_REDOWNLOADABLE_UNUSED_GEMMA4_WEIGHT_CACHE','state':'IN_PROGRESS',
  'started_at_utc':datetime.now(timezone.utc).isoformat(),'model_id':manifest['model_id'],'revision':REV,
  'manifest_sha256':MANIFEST_SHA,'shutdown_report_sha256':sha(shutdown),'native_build_report_sha256':sha(build),
  'own_process_inspection':checked,'free_before_bytes':before,'removed_files':removed,
  'restore_command':'.conda/bin/python scripts/download_model.py runtime/models/gemma4-31b-qat-q4-0.json',
  'scope':'One same-UID regular single-link cache file only; all metadata, manifests and evaluation results retained',
  'foreign_processes_or_files_changed':False}
 # Publish before deletion, then retain each successful step even after interruption.
 with REPORT.open('x') as f:
  json.dump(report,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 report_dir_fd=os.open(REPORT.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 os.fsync(report_dir_fd)
 for e in entries:
  name=e['name'];p=BASE/name
  fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=dirfd)
  try:
   s=os.fstat(fd);assert (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)==snapshots[name]
   with os.fdopen(os.dup(fd),'rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==e['sha256']
   a=os.fstat(fd);b=os.stat(name,dir_fd=dirfd,follow_symlinks=False)
   assert (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns)==snapshots[name]
   assert (b.st_dev,b.st_ino,b.st_size,b.st_mtime_ns,b.st_ctime_ns)==snapshots[name]
   assert a.st_nlink==b.st_nlink==1 and a.st_uid==b.st_uid==os.getuid()
  finally:os.close(fd)
  # Own open hash FD is closed before inspecting all own descriptors again.
  report['own_process_inspection_before_unlink']=no_own_users({x[:2] for x in snapshots.values()})
  b=os.stat(name,dir_fd=dirfd,follow_symlinks=False)
  assert (b.st_dev,b.st_ino,b.st_size,b.st_mtime_ns,b.st_ctime_ns)==snapshots[name]
  assert stat.S_ISREG(b.st_mode) and b.st_nlink==1 and b.st_uid==os.getuid()
  os.unlink(name,dir_fd=dirfd)
  removed.append(e)
  temporary=REPORT.with_suffix('.json.tmp')
  with temporary.open('x') as f:json.dump(report,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
  os.replace(temporary,REPORT);os.fsync(report_dir_fd);os.fsync(dirfd)
 report.update(state='COMPLETE',removed_bytes=sum(x['bytes'] for x in removed),free_after_bytes=free(),finished_at_utc=datetime.now(timezone.utc).isoformat())
 temporary=REPORT.with_suffix('.json.tmp')
 with temporary.open('x') as f:json.dump(report,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(temporary,REPORT);os.fsync(report_dir_fd)
 os.close(report_dir_fd);os.close(dirfd);os.close(lockfd)
 print(json.dumps({'state':report['state'],'removed_bytes':report['removed_bytes'],'free_after_bytes':report['free_after_bytes']}))
if __name__=='__main__':main()
