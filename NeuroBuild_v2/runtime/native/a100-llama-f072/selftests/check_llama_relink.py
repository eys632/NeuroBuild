"""CPU fake supervision only; no actual process, signal, build, ELF or GPU call."""
from contextlib import ExitStack
from hashlib import sha256
import ast
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts import model_guard
path = ROOT / 'var/research/relink_llama_rpath.py'
ast.parse(path.read_text())
spec = importlib.util.spec_from_file_location('relink_subject', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
cases = []
GiB = 1024**3


class Child:
    pid = 123456789  # never used with a real signal syscall
    returncode = None

    def __init__(self, exit_code, events):
        self.exit_code, self.events = exit_code, events

    def wait(self, timeout):
        self.events.append('reap')
        self.returncode = self.exit_code
        return self.returncode


with tempfile.TemporaryDirectory(prefix='relink-fake-', dir=ROOT / 'var/tmp') as temporary:
    temp = Path(temporary)
    for case in ('success', 'nonzero_exit', 'initial_stop', 'initial_disk', 'postspawn_stop',
                 'postspawn_disk', 'postspawn_allocation', 'timeout', 'cleanup_incomplete', 'spawn_failure'):
        events, publications = [], []
        child = Child(2 if case == 'nonzero_exit' else 0, events)
        directory = temp / case
        directory.mkdir()
        cleanup = {'guardian_pid': child.pid, 'native_pid': 987654321, 'native_reaped': True,
                   'cleanup_complete': case != 'cleanup_incomplete', 'native_exit_code': child.exit_code}
        (directory / 'guardian-check.json').write_text(json.dumps(cleanup))
        allocation_values = iter([0, 7 * GiB])
        builder = SimpleNamespace(
            RESERVE=20 * GiB, BUDGET=6 * GiB, TEMP=directory, BOOTSTRAP='FAKE_NOT_EXECUTED',
            allocation=(lambda _: next(allocation_values)) if case == 'postspawn_allocation' else (lambda _: 0),
            publish=lambda record: publications.append(json.loads(json.dumps(record))),
        )
        record, phases = {}, []
        stopped = iter([False, True])
        stop = (lambda: True) if case == 'initial_stop' else ((lambda: next(stopped)) if case == 'postspawn_stop' else (lambda: False))
        disks = iter([SimpleNamespace(f_bavail=48 * GiB, f_frsize=1),
                      SimpleNamespace(f_bavail=20 * GiB, f_frsize=1)])
        disk = (lambda _: SimpleNamespace(f_bavail=20 * GiB, f_frsize=1)) if case == 'initial_disk' else (
            (lambda _: next(disks)) if case == 'postspawn_disk' else (lambda _: SimpleNamespace(f_bavail=48 * GiB, f_frsize=1)))
        loop_case = case.startswith('postspawn') or case == 'timeout'
        peeks = iter([False, True])
        peek = (lambda _: next(peeks)) if loop_case else (lambda _: True)
        times = iter([0.0, 2000.0, 2000.0])
        clock = (lambda: next(times)) if case == 'timeout' else (lambda: 0.0)
        failure = None
        with ExitStack() as stack:
            spawn = stack.enter_context(patch.object(module.subprocess, 'Popen', side_effect=OSError('fake spawn') if case == 'spawn_failure' else None, return_value=child))
            stack.enter_context(patch.object(module.os, 'statvfs', side_effect=disk))
            stack.enter_context(patch.object(module.os, 'killpg', side_effect=lambda pid, sig: events.append(['signal', pid, int(sig)])))
            stack.enter_context(patch.object(module.time, 'monotonic', side_effect=clock))
            stack.enter_context(patch.object(module.time, 'sleep', side_effect=lambda _: None))
            stack.enter_context(patch.object(model_guard, 'peek_child_exit', side_effect=peek))
            try:
                module.run_phase(builder, name='check', command=['FAKE-COMPILER'], env={'CUDA_VISIBLE_DEVICES': ''},
                                 log=None, record=record, phases=phases, paths=[], stop_requested=stop)
            except (ValueError, OSError) as error:
                failure = str(error)
            assert (failure is None) == (case == 'success'), (case, failure)
            if case in ('initial_stop', 'initial_disk'):
                spawn.assert_not_called()
                assert not events
            elif case == 'spawn_failure':
                assert not events
            else:
                assert events[-1] == 'reap' and len(events) == 3, (case, events)
                assert events[0][0] == events[1][0] == 'signal'
                assert events[0][1] == events[1][1] == child.pid
                assert events[0][2] == 15 and events[1][2] == 9
                assert phases[0]['guardian_shutdown']['child_reaped'] is True
        cases.append({'case': case, 'status': 'PASS', 'expected_error': failure,
                      'real_processes_or_signals': 0})

proof = {'status': 'PASS', 'kind': 'FAKE_CPU_RELINK_SUPERVISION', 'cases': cases,
         'helper_sha256': sha256(path.read_bytes()).hexdigest(),
         'shared_shutdown_sha256': sha256((ROOT / 'scripts/model_guard.py').read_bytes()).hexdigest(),
         'checker_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
         'main_or_cmake_called': False, 'native_executable_or_gpu_called': False}
output = ROOT / 'var/research/llama-rpath-relink-cpu-proof.json'
output.write_text(json.dumps(proof, indent=2) + '\n')
print(json.dumps({'status': 'PASS', 'cases': len(cases), 'helper_sha256': proof['helper_sha256'],
                  'proof_sha256': sha256(output.read_bytes()).hexdigest()}))
