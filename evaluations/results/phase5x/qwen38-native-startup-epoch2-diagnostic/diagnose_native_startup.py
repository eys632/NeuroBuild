"""Startup-only diagnostic subclass. No HTTP; never save child stderr or stdout.

Main is for root's separately authorized fresh epoch, not import-time execution.
Production arguments/environment/lifecycle remain inherited without overrides.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import select
import signal
import subprocess
import sys
import threading

ROOT = Path('/home/a202192020/NeuroBuild_v2')
sys.path.insert(0, str(ROOT))
from scripts.llama_server import (_NativeRuntime, NativeLaunchConfig, checked_file,
                                 reject_output_collisions, _pairs, SOURCE_PIN)
from scripts.model_guard import run_lifecycle
from scripts.gpu_preflight import PreflightError

SOURCE = ROOT / 'var/runtime-src' / ('llama.cpp-' + SOURCE_PIN)
LINE_LIMIT = 4096
PARSE_LIMIT = 256 * 1024
EVENT_LIMIT = 16


class StderrParser:
    def __init__(self, source_root=SOURCE):
        self.source_root = Path(source_root)
        self.buffer = bytearray()
        self.dropping_line = False
        self.bytes_seen = self.lines_seen = self.dropped_lines = self.events_dropped = 0
        self.events = []
        self.limit_exceeded = self.eof = self.io_failed = False
        self.lock = threading.Lock()

    def _line(self, raw):
        self.lines_seen += 1
        try:
            line = raw.decode('ascii', errors='strict').strip()
        except UnicodeError:
            return
        event = None
        prefix = str(self.source_root) + '/'
        if line.startswith(prefix):
            match = re.fullmatch(r'([A-Za-z0-9_./-]+):([1-9][0-9]{0,6}): (.*)', line[len(prefix):])
            if match:
                relative, number, message = match.groups()
                path = Path(relative)
                if not path.is_absolute() and '..' not in path.parts and path.suffix in {'.c','.cpp','.cu','.cuh','.h','.hpp'}:
                    actual = self.source_root / path
                    # Source tree is already pinned by the unchanged runtime guard.
                    # Only an existing file under that tree can become a location.
                    if actual.is_file() and not actual.is_symlink() and actual.resolve().is_relative_to(self.source_root):
                        code = ('GGML_ASSERT_FAILED' if message.startswith('GGML_ASSERT(') and message.endswith(') failed')
                                else 'CUDA_ERROR' if message == 'CUDA error'
                                else 'GGML_FATAL_ERROR' if message == 'fatal error'
                                else 'GGML_ABORT_UNCLASSIFIED')
                        event = {'code': code, 'source_basename': path.name, 'source_line': int(number)}
                        if code == 'GGML_ASSERT_FAILED':
                            # Fingerprint only trusted static location, never emitted assertion text.
                            event['assertion_location_sha256'] = hashlib.sha256(
                                (SOURCE_PIN + ':' + relative + ':' + number).encode()).hexdigest()
        if event is None:
            allowed = {'CUDA error: out of memory': 'CUDA_OUT_OF_MEMORY',
                       'CUDA error: no kernel image is available for execution on the device': 'CUDA_NO_KERNEL_IMAGE',
                       'CUDA error: an illegal memory access was encountered': 'CUDA_ILLEGAL_ADDRESS',
                       'CUDA error: invalid argument': 'CUDA_INVALID_ARGUMENT',
                       'CUDA error: initialization error': 'CUDA_INITIALIZATION_ERROR'}
            if line in allowed:
                event = {'code': allowed[line]}
            elif line == "terminate called after throwing an instance of 'std::runtime_error'":
                event = {'code': 'CPP_UNCAUGHT_RUNTIME_ERROR'}
        if event is not None and event not in self.events:
            if len(self.events) < EVENT_LIMIT:
                self.events.append(event)
            else:
                self.events_dropped += 1

    def feed(self, chunk):
        with self.lock:
            self.bytes_seen += len(chunk)
            if self.bytes_seen > PARSE_LIMIT:
                self.limit_exceeded = True
                self.buffer.clear()
                return  # Reader continues draining; guard stops only its own child.
            for byte in chunk:
                if byte == 10:
                    if self.dropping_line:
                        self.dropped_lines += 1
                    else:
                        self._line(bytes(self.buffer))
                    self.buffer.clear()
                    self.dropping_line = False
                elif not self.dropping_line:
                    if len(self.buffer) == LINE_LIMIT:
                        self.buffer.clear()
                        self.dropping_line = True
                        self.limit_exceeded = True
                    else:
                        self.buffer.append(byte)

    def finish(self):
        with self.lock:
            if self.buffer and not self.dropping_line:
                self._line(bytes(self.buffer))
            self.buffer.clear()
            self.eof = True

    def snapshot(self):
        with self.lock:
            return {'stderr_bytes_seen': self.bytes_seen, 'stderr_lines_seen': self.lines_seen,
                    'discarded_overlong_lines': self.dropped_lines, 'events_dropped': self.events_dropped,
                    'parse_limit_exceeded': self.limit_exceeded, 'stderr_eof': self.eof,
                    'stderr_io_failed': self.io_failed, 'events': [dict(item) for item in self.events],
                    'raw_stderr_saved': False, 'raw_stdout_saved': False,
                    'assertion_fingerprint_scope': 'PINNED_SOURCE_LOCATION_ONLY_NOT_ASSERTION_TEXT'}


class PipeDrainer:
    def __init__(self, stream, parser):
        self.stream, self.parser = stream, parser
        self.stop = threading.Event()
        os.set_blocking(stream.fileno(), False)
        self.thread = threading.Thread(target=self._run, name='native-stderr-discard', daemon=True)
        self.thread.start()

    def _run(self):
        try:
            while not self.stop.is_set():
                if not select.select([self.stream], [], [], .05)[0]:
                    continue
                try:
                    chunk = os.read(self.stream.fileno(), 4096)
                except BlockingIOError:
                    continue
                if not chunk:
                    self.parser.finish()
                    return
                self.parser.feed(chunk)
        except (OSError, ValueError):
            with self.parser.lock:
                self.parser.io_failed = True

    def close(self):
        # The common guard has already terminated/reaped its child before cleanup.
        self.thread.join(timeout=2)
        if self.thread.is_alive():
            self.stop.set()
            self.thread.join(timeout=.2)
        done = not self.thread.is_alive()
        if done:
            self.stream.close()
        return done


class DiagnosticRuntime(_NativeRuntime):
    def __init__(self, *, protected_inputs=(), source_root=SOURCE):
        super().__init__()
        self.parser = StderrParser(source_root)
        self.drainer = None
        self.stderr_stream = None
        self.protected_inputs = protected_inputs

    def initial_fields(self, config):
        return {**super().initial_fields(config), 'diagnostic_startup_only': True,
                'native_output_policy': 'STDOUT_DEVNULL_STDERR_BOUNDED_MEMORY_ALLOWLIST',
                'diagnostic_model_http_calls': 0, 'diagnostic_stderr_parse_limit_bytes': PARSE_LIMIT,
                'diagnostic_stderr_line_limit_bytes': LINE_LIMIT}

    def validate(self, config, root, model):
        reject_output_collisions(config, root, *self.protected_inputs)
        super().validate(config, root, model)

    def output_options(self, log):
        return {**super().output_options(log), 'stderr': subprocess.PIPE}

    def after_spawn(self, child):
        self.stderr_stream = child.stderr
        super().after_spawn(child)
        self.drainer = PipeDrainer(child.stderr, self.parser)

    def observe(self, child, report):
        super().observe(child, report)
        report['startup_diagnostic'] = self.parser.snapshot()
        if report['startup_diagnostic']['parse_limit_exceeded']:
            raise PreflightError('DIAGNOSTIC_STDERR_LIMIT', 'Diagnostic stderr exceeded its memory parsing bound')
        if report['startup_diagnostic']['stderr_io_failed']:
            raise PreflightError('DIAGNOSTIC_PIPE_FAILED', 'Diagnostic stderr pipe failed')

    def cleanup(self, report, safe_to_release):
        try:
            reader_closed = self.drainer is None or self.drainer.close()
            if self.drainer is None and self.stderr_stream is not None:
                self.stderr_stream.close()
                self.parser.io_failed = True
            report['startup_diagnostic'] = self.parser.snapshot()
            report['startup_diagnostic']['reader_thread_stopped'] = reader_closed
            if not reader_closed or (self.drainer is not None and not self.parser.eof):
                report['startup_diagnostic']['diagnostic_complete'] = False
            else:
                report['startup_diagnostic']['diagnostic_complete'] = not self.parser.io_failed and not self.parser.limit_exceeded
        finally:
            super().cleanup(report, safe_to_release)


def load_config(path, expected):
    path = checked_file(path, ROOT)
    if path.stat().st_size > 65536:
        raise ValueError('CONFIG_TOO_LARGE')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('CONFIG_HASH_MISMATCH')
    data = json.loads(raw, object_pairs_hook=_pairs)
    for key in ('binary_path','build_report','source_report','model_path','model_header_report','log_file','report_file'):
        data[key] = Path(data[key])
    return NativeLaunchConfig(**data), path


def validate_same_launch(config, baseline):
    allowed = {'log_file', 'report_file', 'max_seconds'}
    if {k:v for k,v in asdict(config).items() if k not in allowed} != {k:v for k,v in asdict(baseline).items() if k not in allowed}:
        raise ValueError('PRODUCTION_LAUNCH_CHANGED')
    if not 1 <= config.max_seconds <= 120:
        raise ValueError('DIAGNOSTIC_TIME_LIMIT_REQUIRED')
    for name in ('log_file','report_file'):
        path = getattr(config,name)
        path = path if path.is_absolute() else ROOT/path
        if path.exists() or path.is_symlink() or path.resolve() == (ROOT/getattr(baseline,name)).resolve():
            raise ValueError('FRESH_DIAGNOSTIC_OUTPUT_REQUIRED')


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--config',type=Path,required=True)
    cli.add_argument('--config-sha256',required=True)
    cli.add_argument('--baseline-config',type=Path,required=True)
    cli.add_argument('--baseline-config-sha256',required=True)
    args=cli.parse_args()
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    config,path=load_config(args.config,args.config_sha256)
    baseline,baseline_path=load_config(args.baseline_config,args.baseline_config_sha256)
    validate_same_launch(config,baseline)
    stop=threading.Event()
    previous={sig:signal.signal(sig,lambda *_:stop.set()) for sig in (signal.SIGINT,signal.SIGTERM)}
    try:
        runtime=DiagnosticRuntime(protected_inputs=(path,baseline_path))
        report=run_lifecycle(config,runtime,root=ROOT,stop_requested=stop.is_set)
    finally:
        for sig,handler in previous.items():signal.signal(sig,handler)
    # Report contains scalar provenance/config paths and allowlisted diagnostic events only.
    print(json.dumps({'state':report['state'],'reason':report.get('reason'),
                     'child_exit_code':report.get('child_exit_code'),'diagnostic':report.get('startup_diagnostic'),
                     'report_path':str(config.report_file)},allow_nan=False))
    return 0 if (report.get('shutdown',{}).get('child_reaped') and report.get('child_exit_code')==0
                 and report.get('native_identity_verified') is True
                 and report.get('startup_diagnostic',{}).get('diagnostic_complete') is True) else 2


if __name__=='__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        # Never interpolate exception text, stderr or input contents.
        print(json.dumps({'status':'BLOCKED','error_type':type(error).__name__}))
        raise SystemExit(2)
