import importlib.util
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path('/home/a202192020/NeuroBuild_v2')
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('diag_native',ROOT/'var/research/diagnose_native_startup.py')
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)


class DiagnosticTests(unittest.TestCase):
    def test_source_assert_location_only_no_expression(self):
        parser=d.StderrParser()
        raw=(str(d.SOURCE)+'/src/llama-context.cpp:1734: GGML_ASSERT(secret_user_text <= cparams.n_batch) failed\n').encode()
        for index in range(0,len(raw),7):parser.feed(raw[index:index+7])
        parser.finish();result=parser.snapshot()
        self.assertEqual(result['events'][0]['code'],'GGML_ASSERT_FAILED')
        self.assertEqual(result['events'][0]['source_basename'],'llama-context.cpp')
        self.assertEqual(result['events'][0]['source_line'],1734)
        self.assertEqual(len(result['events'][0]['assertion_location_sha256']),64)
        self.assertNotIn('secret_user_text',json.dumps(result))
        self.assertNotIn(str(d.SOURCE),json.dumps(result))
        self.assertEqual(parser.buffer,bytearray())

    def test_unknown_unicode_backtrace_paths_and_dynamic_content_discarded(self):
        parser=d.StderrParser()
        for raw in [b'request secret API-key XYZ\n',b'backtrace /home/other/student/file:222\n',
                    b'CUDA error: arbitrary private contents\n',b'\xff\xfe\n',
                    (str(d.SOURCE)+'/../../secret.cpp:12: GGML_ASSERT(x) failed\n').encode(),
                    (str(d.SOURCE)+'/src/does-not-exist.cpp:12: GGML_ASSERT(x) failed\n').encode()]:
            parser.feed(raw)
        parser.finish();self.assertEqual(parser.snapshot()['events'],[])

    def test_absolute_tail_rejected_before_any_filesystem_lookup(self):
        parser=d.StderrParser()
        line=(str(d.SOURCE)+'//home/other/student/private.cpp:12: GGML_ASSERT(x) failed\n').encode()
        with patch.object(Path,'is_file',side_effect=AssertionError('External metadata forbidden')) as is_file, \
             patch.object(Path,'resolve',side_effect=AssertionError('External resolution forbidden')) as resolve, \
             patch.object(Path,'stat',side_effect=AssertionError('External stat forbidden')) as stat:
            parser.feed(line);parser.finish()
        is_file.assert_not_called();resolve.assert_not_called();stat.assert_not_called()
        self.assertEqual(parser.snapshot()['events'],[])

    def test_known_codes_and_event_limit(self):
        parser=d.StderrParser()
        parser.feed(b'CUDA error: out of memory\n')
        parser.feed((str(d.SOURCE)+'/ggml/src/ggml-cuda/ggml-cuda.cu:111: CUDA error\n').encode())
        for n in range(1,30):parser.feed((str(d.SOURCE)+f'/src/llama-context.cpp:{n}: GGML_ASSERT(x) failed\n').encode())
        result=parser.snapshot();self.assertEqual(len(result['events']),d.EVENT_LIMIT)
        self.assertGreater(result['events_dropped'],0)
        self.assertEqual(result['events'][0],{'code':'CUDA_OUT_OF_MEMORY'})

    def test_overlong_and_total_overflow_do_not_retain_raw(self):
        parser=d.StderrParser();parser.feed(b'private'*(d.LINE_LIMIT+1))
        self.assertLessEqual(len(parser.buffer),d.LINE_LIMIT)
        parser.feed(b'\n')
        self.assertTrue(parser.snapshot()['parse_limit_exceeded'])
        self.assertEqual(parser.snapshot()['discarded_overlong_lines'],1)
        parser.feed(b'private'*(d.PARSE_LIMIT+1));parser.finish()
        self.assertEqual(parser.buffer,bytearray())
        self.assertEqual(parser.snapshot()['events'],[])

    def test_cpu_child_pipe_drains_past_capacity_without_deadlock(self):
        # New own CPU-only producer, no native/GPU/model/library execution.
        code="import os\nfor i in range(512): os.write(2,b'PRIVATE_BODY'*512)\n"
        child=subprocess.Popen([sys.executable,'-I','-B','-c',code],stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,env={'PATH':'/usr/bin:/bin','CUDA_VISIBLE_DEVICES':''},start_new_session=True)
        parser=d.StderrParser();reader=d.PipeDrainer(child.stderr,parser)
        try:
            self.assertEqual(child.wait(timeout=5),0)
            self.assertTrue(reader.close())
            self.assertTrue(parser.snapshot()['stderr_eof'])
            self.assertGreater(parser.bytes_seen,d.PARSE_LIMIT)
            self.assertEqual(parser.snapshot()['events'],[])
            self.assertTrue(child.stderr.closed)
        finally:
            if child.poll() is None:
                child.kill();child.wait(timeout=3)
            reader.close()

    def test_cleanup_waits_for_eof_or_marks_incomplete(self):
        read_fd,write_fd=os.pipe();stream=os.fdopen(read_fd,'rb',buffering=0)
        runtime=d.DiagnosticRuntime();runtime.drainer=d.PipeDrainer(stream,runtime.parser)
        os.write(write_fd,b'CUDA error: invalid argument\n');os.close(write_fd)
        report={};runtime.cleanup(report,True)
        self.assertTrue(report['startup_diagnostic']['reader_thread_stopped'])
        self.assertTrue(report['startup_diagnostic']['diagnostic_complete'])
        self.assertTrue(stream.closed)

    def test_cleanup_closes_pipe_if_reader_start_failed(self):
        read_fd,write_fd=os.pipe();stream=os.fdopen(read_fd,'rb',buffering=0)
        runtime=d.DiagnosticRuntime();runtime.stderr_stream=stream
        os.close(write_fd);report={};runtime.cleanup(report,True)
        self.assertTrue(stream.closed)
        self.assertTrue(report['startup_diagnostic']['stderr_io_failed'])
        self.assertFalse(report['startup_diagnostic']['diagnostic_complete'])

    def test_pipe_io_failure_is_sanitized(self):
        read_fd,write_fd=os.pipe();stream=os.fdopen(read_fd,'rb',buffering=0)
        parser=d.StderrParser()
        with patch.object(d.select,'select',side_effect=OSError('SECRET')):
            reader=d.PipeDrainer(stream,parser);reader.thread.join(timeout=1)
        os.close(write_fd);self.assertTrue(reader.close())
        self.assertTrue(parser.snapshot()['stderr_io_failed'])
        self.assertNotIn('SECRET',json.dumps(parser.snapshot()))

    def fixture(self):
        from tests.test_llama_server import NativeGuardTests
        fixture=NativeGuardTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        return fixture

    def test_same_launch_changes_only_fresh_outputs_and_short_deadline(self):
        fixture=self.fixture();base=fixture.config
        diag=replace(base,log_file=Path('var/logs/new.log'),report_file=Path('var/reports/new.json'),max_seconds=120)
        with patch.object(d,'ROOT',fixture.root):
            d.validate_same_launch(diag,base)
            for changed in [replace(diag,estimated_peak_mib=20000),replace(diag,max_seconds=121),
                            replace(diag,log_file=base.log_file)]:
                with self.assertRaises(ValueError):d.validate_same_launch(changed,base)
        runtime=d.DiagnosticRuntime()
        self.assertIs(type(runtime).prepare,d._NativeRuntime.prepare)
        self.assertIs(type(runtime).environment,d._NativeRuntime.environment)
        runtime.write_fd=44
        options=runtime.output_options(None)
        self.assertEqual(options['stdout'],subprocess.DEVNULL)
        self.assertEqual(options['stderr'],subprocess.PIPE)
        self.assertEqual(options['pass_fds'],(44,))

    def test_fake_common_guard_preserves_gpu3_floor_and_own_cleanup(self):
        fixture=self.fixture()
        from tests.test_llama_server import FakeChild,STABLE
        runtime=d.DiagnosticRuntime();now=[0.0];terminated=[False];signals=[];queries=[]
        def query(index):queries.append(index);return STABLE
        def popen(command,**kwargs):
            child=FakeChild();child.returncode=None
            read_fd,write_fd=os.pipe();child.stderr=os.fdopen(read_fd,'rb',buffering=0)
            os.write(write_fd,(str(d.SOURCE)+'/src/llama-context.cpp:1734: GGML_ASSERT(x) failed\n').encode());os.close(write_fd)
            os.write(kwargs['pass_fds'][0],json.dumps({'event':'GPU_IDENTITY_VERIFIED','pid':child.pid,
                'physical_gpu_index':3,'logical_device':0}).encode())
            return child
        def signal(pid,sig):signals.append((pid,sig));terminated[0]=True
        report=d.run_lifecycle(fixture.config,runtime,root=fixture.root,environ={'CUDA_VISIBLE_DEVICES':'3'},
            query=query,popen=popen,killpg=signal,peek_exit=lambda _:terminated[0],
            sleep=lambda duration:now.__setitem__(0,now[0]+duration),monotonic=lambda:now[0])
        self.assertEqual(report['reason'],'TIME_LIMIT')
        self.assertEqual(set(queries),{3})
        self.assertEqual(report['required_free_floor_mib'],7275)
        self.assertEqual(report['aggregate_increment_limit_mib'],25600)
        self.assertTrue(report['shutdown']['child_reaped'])
        self.assertTrue(report['startup_diagnostic']['diagnostic_complete'])
        self.assertEqual(report['startup_diagnostic']['events'][0]['code'],'GGML_ASSERT_FAILED')
        self.assertTrue(all(pid==FakeChild.pid for pid,sig in signals))

if __name__=='__main__':unittest.main()
