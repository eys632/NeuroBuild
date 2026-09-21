#!/usr/bin/env python3
"""Explicit bounded public-weight download; no model/native/GPU execution.

Reuses pinned CPU guardian + shared WNOWAIT cleanup. The 2-second disk watcher
is sampled protection, not a filesystem reservation. Partial downloads survive.
"""
from datetime import datetime, timezone
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys

ROOT = Path('/home/a202192020/NeuroBuild_v2')
MODEL = 'ggml-org/Qwen3.6-35B-A3B-GGUF'
REVISION = 'baec3ebee244827cda0f4557eafa8b28f7545fa6'
SOURCE_PIN = 'f072b103714dfa1eee531f80b24512faf38e3dd2'
MANIFEST = Path('runtime/models/qwen36-35b-a3b-q4-k-m.json')
BUILD_PROOF = Path('var/reports/llama-cuda-build-verified.json')
CLEANUP_PROOF = Path('var/reports/unused-gemma12-weight-cache-cleanup.json')
DESTINATION = Path('var/models/ggml-org--Qwen3.6-35B-A3B-GGUF') / REVISION
REPORT = Path('var/reports/qwen36-guarded-download.json')
TEMP = Path('var/tmp/qwen36-guarded-download')
RESERVE = 20 * 1024**3
BUFFER = 512 * 1024**2
MAX_SECONDS = 1800
PINS = {
 'runtime/models/qwen36-35b-a3b-q4-k-m.json':'70d4c0f73f763e10d17b0bad75acda2079dff6d49a9e2ed25575a86cff62b76c',
 'scripts/download_model.py':'eea7da3f210addeaece15cb2a7072145cb9c380bd475c4a4f92292df78b88353',
 'scripts/model_guard.py':'cc95f6cccf9ca5b749bea2fc8c82d2af9d56d55b94a6aee947379b3a2f4de528',
 'var/research/run_llama_build.py':'e901372cc4f39dbee1e0574baf318fd2ae6edca167963f8bfe66274c06b8d52f',
 'var/research/relink_llama_rpath.py':'52ab2e85128c1ff8fff978017aa7225268615d31ba653cdf20bb1c7f202333e0',
}


def require(value, code):
 if not value: raise ValueError(code)


def digest(path):
 with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()


def own(path, root, *, missing=False):
 require(path.is_relative_to(root), 'PATH_OUTSIDE_PROJECT')
 for part in (path,*path.parents):
  if part == root: break
  if missing and not part.exists() and not part.is_symlink(): continue
  info=part.lstat()
  require(info.st_uid==os.getuid() and not stat.S_ISLNK(info.st_mode),'UNSAFE_OWN_PATH')
 else: raise ValueError('PATH_OUTSIDE_PROJECT')
 if path.exists() and path.is_file():
  require(path.stat().st_nlink==1,'INPUT_HARDLINK_ALIAS')


def proof(path, expected, root):
 own(path,root)
 require(type(expected) is str and re.fullmatch('[a-f0-9]{64}',expected),'EXACT_PROOF_SHA_REQUIRED')
 require(path.is_file() and path.stat().st_size<=2*1024**2 and digest(path)==expected,'PROOF_HASH_MISMATCH')
 return json.loads(path.read_text())


def precheck(root, *, build_sha, cleanup_sha=None, free_bytes=None):
 """Read own metadata/files only. Tests inject a temporary root and free bytes."""
 root=Path(root).resolve()
 for relative,sha in PINS.items():
  path=root/relative;own(path,root)
  require(path.is_file() and digest(path)==sha,'PINNED_INPUT_CHANGED')
 manifest=json.loads((root/MANIFEST).read_text())
 require(manifest['model_id']==MODEL and manifest['revision']==REVISION,'MODEL_IDENTITY_CHANGED')
 build=proof(root/BUILD_PROOF,build_sha,root)
 require(build['status']=='COMPILE_PASS_NOT_RUNTIME_VALIDATED'
         and build['verification_kind']=='LLAMA_POSTCOMPILE_STATIC_VERIFICATION'
         and build['source_pin']==SOURCE_PIN and build['native_binary_executed'] is False
         and build['weights_read'] is False,'FINAL_BUILD_PROOF_REQUIRED')
 require(all(type(build['source_reverification'][key]) is int and build['source_reverification'][key]==value
             for key,value in {'verified_blobs':3607,'verified_blob_bytes':172243701,'extra_or_missing_paths':0}.items()),
         'SOURCE_REVERIFICATION_MISMATCH')
 require(build['elf_linkage']['method']=='STATIC_READELF_RPATH_RUNPATH_SYSTEM_CACHE'
         and build['elf_linkage']['ld_library_path'] is None,'FINAL_LINKAGE_PROOF_REQUIRED')
 if (root/CLEANUP_PROOF).exists() or (root/CLEANUP_PROOF).is_symlink() or cleanup_sha is not None:
  cleanup=proof(root/CLEANUP_PROOF,cleanup_sha,root)
  require(cleanup['kind']=='REMOVE_VERIFIED_REDOWNLOADABLE_UNUSED_GEMMA12_WEIGHT_CACHE'
          and cleanup['state']=='COMPLETE' and cleanup['revision']=='29d097773436b69ff9feafd636ab4cf873786537'
          and cleanup['removed_bytes']==6975879296 and len(cleanup['removed_files'])==1
          and cleanup['foreign_processes_or_files_changed'] is False,'CLEANUP_INCOMPLETE')
 destination=root/DESTINATION;own(destination,root,missing=True)
 protected={root/path for path in PINS}|{root/BUILD_PROOF,root/CLEANUP_PROOF}
 needed=0
 for entry in manifest['files']:
  target=destination/entry['name'];partial=target.with_suffix(target.suffix+'.part')
  for path in (target,partial):
   own(path,root,missing=True)
   require(not path.exists() or path.is_file(),'NONREGULAR_DOWNLOAD_PATH')
  protected.update((target,partial))
  if target.exists():
   require(target.stat().st_size==entry['bytes'] and digest(target)==entry['sha256'],'EXISTING_TARGET_CHANGED')
  else: needed+=entry['bytes'] # Same conservative accounting as existing downloader, even with a .part.
  require(not partial.exists() or partial.stat().st_size<=entry['bytes'],'PARTIAL_OVERSIZED')
 metadata=destination/'neurobuild-manifest.json';own(metadata,root,missing=True)
 require(not metadata.exists() or json.loads(metadata.read_text())==manifest,'MODEL_METADATA_CHANGED')
 protected.add(metadata)
 for relative in (REPORT,TEMP):
  path=root/relative;own(path,root,missing=True)
  require(path not in protected and not path.exists() and not path.is_symlink(),'OUTPUT_EXISTS_OR_INPUT_COLLISION')
 if free_bytes is None:
  disk=os.statvfs(root);free_bytes=disk.f_bavail*disk.f_frsize
 require(type(free_bytes) is int and free_bytes>=needed+RESERVE+BUFFER,'INITIAL_DISK_BUDGET')
 return {'manifest':manifest,'remaining_conservative_bytes':needed,'initial_free_bytes':free_bytes,
         'total_manifest_bytes':sum(e['bytes'] for e in manifest['files'])}


def module(root,name,relative):
 spec=importlib.util.spec_from_file_location(name,root/relative)
 value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
 return value


def environment(root,environ):
 env={key:environ[key] for key in ('HOME','LANG','LC_ALL','TZ') if key in environ}
 env.update(CUDA_VISIBLE_DEVICES='',CUDA_DEVICE_ORDER='PCI_BUS_ID',PYTHONNOUSERSITE='1',
            PATH='/usr/bin:/bin',TMPDIR=str(root/TEMP))
 return env


def publisher(root):
 """First report is exclusive; later own live report updates are atomic/fsynced."""
 created=False
 path=root/REPORT
 def publish(record):
  nonlocal created
  temporary=path.with_suffix('.json.tmp')
  with temporary.open('x') as stream:
   json.dump(record,stream,indent=2,allow_nan=False);stream.write('\n');stream.flush();os.fsync(stream.fileno())
  try:
   if created: os.replace(temporary,path)
   else: os.link(temporary,path)
  finally: temporary.unlink(missing_ok=True)
  fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
  try: os.fsync(fd)
  finally: os.close(fd)
  created=True
 return publish


def main(argv=None):
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--build-report-sha256',required=True)
 parser.add_argument('--cleanup-report-sha256')
 args=parser.parse_args(argv)
 require(Path(sys.prefix)==ROOT/'.conda' and os.environ.get('CUDA_VISIBLE_DEVICES')=='','CPU_PROJECT_ENV_REQUIRED')
 # Pin reusable code before importing it. No module main or executable is invoked by import.
 for relative,sha in PINS.items():
  own(ROOT/relative,ROOT);require(digest(ROOT/relative)==sha,'PINNED_INPUT_CHANGED')
 sys.path.insert(0,str(ROOT))
 from scripts.model_guard import acquire_project_lock
 lock=acquire_project_lock(ROOT)
 try:
  checked=precheck(ROOT,build_sha=args.build_report_sha256,cleanup_sha=args.cleanup_report_sha256)
  builder=module(ROOT,'pinned_download_guardian','var/research/run_llama_build.py')
  supervisor=module(ROOT,'pinned_download_supervisor','var/research/relink_llama_rpath.py')
  temporary=ROOT/TEMP;temporary.mkdir(mode=0o700)
  publish=publisher(ROOT)
  record={'kind':'GUARDED_PINNED_PUBLIC_MODEL_DOWNLOAD','status':'RUNNING',
          'created_at_utc':datetime.now(timezone.utc).isoformat(),'helper_sha256':digest(Path(__file__)),
          'model_id':MODEL,'revision':REVISION,'source_pin':SOURCE_PIN,'input_sha256':PINS,
          'build_report_sha256':args.build_report_sha256,'cleanup_report_sha256':args.cleanup_report_sha256,
          'cuda_visible_devices':'','disk_floor_bytes':RESERVE+BUFFER,'disk_poll_seconds':2,
          'max_phase_seconds':MAX_SECONDS,'termination_grace_is_additional':True,
          'initial_free_bytes':checked['initial_free_bytes'],'conservative_remaining_bytes':checked['remaining_conservative_bytes'],
          'child_stdout_stderr':'DISCARDED; supervisor emits only fixed metadata',
          'gpu_or_native_execution':False,'phases':[]}
  publish(record);builder.publish=publish
  stopped=[False]
  def stop(*_): stopped[0]=True
  previous={sig:signal.signal(sig,stop) for sig in (signal.SIGINT,signal.SIGTERM)}
  try:
   supervisor.run_phase(builder,name='download-qwen36',
       command=[str(ROOT/'.conda/bin/python'),'-I','-B',str(ROOT/'scripts/download_model.py'),str(ROOT/MANIFEST)],
       env=environment(ROOT,os.environ),log=subprocess.DEVNULL,record=record,phases=record['phases'],
       paths=[ROOT/DESTINATION,temporary,ROOT/REPORT],stop_requested=lambda:stopped[0],
       reserve_bytes=RESERVE,budget_bytes=checked['total_manifest_bytes']+BUFFER,
       max_seconds=MAX_SECONDS,temp_dir=temporary)
   # Downloader exit0 follows exact size/SHA checks; record public manifest metadata only.
   metadata=ROOT/DESTINATION/'neurobuild-manifest.json';own(metadata,ROOT)
   require(json.loads(metadata.read_text())==checked['manifest'],'FINAL_METADATA_MISMATCH')
   record.update(status='PASS_DOWNLOAD_ONLY_NOT_RUNTIME_VALIDATED',verified_files=len(checked['manifest']['files']),
                 model_path=str(DESTINATION),downloaded_manifest_sha256=digest(metadata))
  except BaseException as error:
   record.update(status='FAILED',failure_type=type(error).__name__)
   raise
  finally:
   record['finished_at_utc']=datetime.now(timezone.utc).isoformat();publish(record)
   for sig,handler in previous.items():signal.signal(sig,handler)
 finally:os.close(lock)
 print(json.dumps({'status':record['status'],'report':str(REPORT),'model_path':str(DESTINATION)}))


if __name__=='__main__':
 try:main()
 except Exception as error:
  code=str(error) if isinstance(error,ValueError) and re.fullmatch('[A-Z0-9_]+',str(error)) else 'INPUT_OR_IO_ERROR'
  print(json.dumps({'status':'FAILED','error_type':type(error).__name__,'error_code':code}));raise SystemExit(1)
