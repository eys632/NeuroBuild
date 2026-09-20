"""Temporary/fake boundaries; never call the supervisor main/curl/native/GPU."""
from contextlib import ExitStack
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from scripts import model_guard

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path)
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=load('download_guard_subject',ROOT/'var/research/download_qwen38_guarded.py')
r=load('download_pinned_phase',ROOT/'var/research/relink_llama_rpath.py')


class DownloadGuardTests(unittest.TestCase):
 def setUp(self):
  self.temporary=tempfile.TemporaryDirectory(prefix='guard-download-',dir=ROOT/'var/tmp')
  self.addCleanup(self.temporary.cleanup);self.root=Path(self.temporary.name)
  self.body=b'known bytes'
  self.manifest={'model_id':m.MODEL,'revision':m.REVISION,'files':[{'name':'synthetic.gguf','bytes':len(self.body),'sha256':hashlib.sha256(self.body).hexdigest()}]}
  self.pins={}
  for relative in m.PINS:
   data=json.dumps(self.manifest).encode() if relative==str(m.MANIFEST) else b'fake code never executed'
   p=self.root/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
   self.pins[relative]=hashlib.sha256(data).hexdigest()
  self.build={'status':'COMPILE_PASS_NOT_RUNTIME_VALIDATED','verification_kind':'LLAMA_POSTCOMPILE_STATIC_VERIFICATION',
              'source_pin':m.SOURCE_PIN,'native_binary_executed':False,'weights_read':False,
              'source_reverification':{'verified_blobs':3607,'verified_blob_bytes':172243701,'extra_or_missing_paths':0,'additional':'allowed'},
              'elf_linkage':{'method':'STATIC_READELF_RPATH_RUNPATH_SYSTEM_CACHE','ld_library_path':None}}
  self.build_path=self.root/m.BUILD_PROOF;self.build_path.parent.mkdir(parents=True,exist_ok=True)
  self.build_path.write_text(json.dumps(self.build));self.build_sha=m.digest(self.build_path)
  self.patch=patch.object(m,'PINS',self.pins);self.patch.start();self.addCleanup(self.patch.stop)
  self.addCleanup(patch.stopall)
  patch.object(m.subprocess,'Popen',side_effect=AssertionError('Real child forbidden')).start()

 def check(self,**kwargs):
  return m.precheck(self.root,build_sha=self.build_sha,free_bytes=50*1024**3,**kwargs)

 def test_clean_precheck_and_conservative_partial_accounting(self):
  expected=self.check();self.assertEqual(expected['remaining_conservative_bytes'],len(self.body))
  directory=self.root/m.DESTINATION;directory.mkdir(parents=True)
  (directory/'synthetic.gguf.part').write_bytes(self.body[:2])
  self.assertEqual(self.check()['remaining_conservative_bytes'],len(self.body))
  (directory/'synthetic.gguf').write_bytes(self.body)
  self.assertEqual(self.check()['remaining_conservative_bytes'],0)

 def test_disk_floor_and_artifact_buffer_apply_before_outputs(self):
  needed=len(self.body)+m.RESERVE+m.BUFFER
  m.precheck(self.root,build_sha=self.build_sha,free_bytes=needed)
  with self.assertRaisesRegex(ValueError,'INITIAL_DISK_BUDGET'):
   m.precheck(self.root,build_sha=self.build_sha,free_bytes=needed-1)
  self.assertFalse((self.root/m.REPORT).exists());self.assertFalse((self.root/m.TEMP).exists())

 def test_changed_pins_incomplete_final_proof_and_unsafe_source_inventory_reject(self):
  for change in ({'status':'RUNNING'},{'verification_kind':'compile-only'},{'native_binary_executed':True}):
   value=dict(self.build,**change);self.build_path.write_text(json.dumps(value))
   with self.assertRaises(ValueError):m.precheck(self.root,build_sha=m.digest(self.build_path),free_bytes=50*1024**3)
  self.build_path.write_text(json.dumps(self.build))
  p=self.root/'scripts/download_model.py';p.write_bytes(b'changed')
  with self.assertRaisesRegex(ValueError,'PINNED_INPUT_CHANGED'):self.check()

 def test_cleanup_if_present_requires_exact_complete_proof_and_hash(self):
  p=self.root/m.CLEANUP_PROOF
  value={'kind':'REMOVE_VERIFIED_REDOWNLOADABLE_UNUSED_MOE_WEIGHT_CACHE','state':'COMPLETE',
         'revision':'9f41ff709102dbe73e614f9365f8280170db268e','removed_bytes':16809467824,
         'removed_files':[{}]*4,'foreign_processes_or_files_changed':False}
  p.write_text(json.dumps(value))
  with self.assertRaisesRegex(ValueError,'EXACT_PROOF_SHA_REQUIRED'):self.check()
  self.check(cleanup_sha=m.digest(p))
  value['state']='IN_PROGRESS';p.write_text(json.dumps(value))
  with self.assertRaisesRegex(ValueError,'CLEANUP_INCOMPLETE'):self.check(cleanup_sha=m.digest(p))

 def test_input_output_collision_and_existing_report_are_preserved(self):
  before=self.build_path.read_bytes()
  with patch.object(m,'REPORT',m.BUILD_PROOF):
   with self.assertRaisesRegex(ValueError,'OUTPUT_EXISTS_OR_INPUT_COLLISION'):self.check()
  self.assertEqual(self.build_path.read_bytes(),before)
  p=self.root/m.REPORT;p.write_bytes(b'old proof')
  with self.assertRaises(ValueError):self.check()
  self.assertEqual(p.read_bytes(),b'old proof')

 def test_publication_never_overwrites_raced_initial_report(self):
  publish=m.publisher(self.root);p=self.root/m.REPORT;p.write_bytes(b'other proof')
  with self.assertRaises(FileExistsError):publish({'status':'RUNNING'})
  self.assertEqual(p.read_bytes(),b'other proof')
  self.assertFalse(p.with_suffix('.json.tmp').exists())

 def test_empty_cuda_and_environment_allowlist(self):
  env=m.environment(self.root,{'CUDA_VISIBLE_DEVICES':'0','LD_PRELOAD':'bad','HTTP_PROXY':'bad',
                               'CURL_CA_BUNDLE':'bad','PYTHONOPTIMIZE':'1','HF_TOKEN':'bad'})
  self.assertEqual(env['CUDA_VISIBLE_DEVICES'],'');self.assertEqual(env['PATH'],'/usr/bin:/bin')
  self.assertNotIn('bad',env.values());self.assertNotIn('PYTHONOPTIMIZE',env)

 def test_reused_phase_sends_only_own_group_signals_for_disk_timeout_and_child_failure(self):
  # Directly exercise the SAME pinned run_phase used by main, with every process/disk/clock injected.
  for case in ('success','initial_disk','post_disk','timeout','child_failure','cleanup_failure'):
   with self.subTest(case=case), tempfile.TemporaryDirectory(dir=self.root) as temp:
    directory=Path(temp);events=[]
    child=SimpleNamespace(pid=123456789,returncode=None)
    def wait(timeout):
     events.append('reap');child.returncode=2 if case=='child_failure' else 0;return child.returncode
    child.wait=wait
    cleanup={'guardian_pid':child.pid,'native_pid':987654321,'native_reaped':True,'cleanup_complete':case!='cleanup_failure'}
    (directory/'guardian-download.json').write_text(json.dumps(cleanup))
    builder=SimpleNamespace(BOOTSTRAP='FAKE_NOT_EXECUTED',RESERVE=m.RESERVE,BUDGET=1024,TEMP=directory,
                            allocation=lambda _:0,publish=lambda _:None)
    disks=iter([SimpleNamespace(f_bavail=50*1024**3,f_frsize=1),SimpleNamespace(f_bavail=m.RESERVE,f_frsize=1)])
    disk=lambda _: next(disks) if case=='post_disk' else SimpleNamespace(f_bavail=m.RESERVE if case=='initial_disk' else 50*1024**3,f_frsize=1)
    peek_values=iter([False,True]);peek=lambda _:next(peek_values) if case in ('post_disk','timeout') else True
    times=iter([0,2000]);clock=lambda:next(times,2000) if case=='timeout' else 0
    failure=None
    with ExitStack() as stack:
     spawn=stack.enter_context(patch.object(r.subprocess,'Popen',return_value=child))
     stack.enter_context(patch.object(r.os,'statvfs',side_effect=disk))
     stack.enter_context(patch.object(r.os,'killpg',side_effect=lambda pid,sig:events.append((pid,int(sig)))))
     stack.enter_context(patch.object(r.time,'monotonic',side_effect=clock))
     stack.enter_context(patch.object(r.time,'sleep',return_value=None))
     stack.enter_context(patch.object(model_guard,'peek_child_exit',side_effect=peek))
     try:r.run_phase(builder,name='download',command=['FAKE-DOWNLOADER'],env={'CUDA_VISIBLE_DEVICES':''},
                     log=-3,record={},phases=[],paths=[],stop_requested=lambda:False,
                     reserve_bytes=m.RESERVE,budget_bytes=1024,max_seconds=1800,temp_dir=directory)
     except ValueError as error:failure=str(error)
     if case=='initial_disk':spawn.assert_not_called();self.assertEqual(events,[])
     else:self.assertEqual(events,[(child.pid,15),(child.pid,9),'reap'])
    self.assertEqual(failure is None,case=='success')


if __name__=='__main__':unittest.main()
