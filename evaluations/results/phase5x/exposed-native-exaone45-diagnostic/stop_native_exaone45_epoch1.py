"""Stop only the pinned, still-owned EXAONE epoch1 guard through its pidfd."""
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import signal
from types import ModuleType

ROOT = Path('/home/a202192020/NeuroBuild_v2')
GUARD = 3622309
GUARD_TICKS = 478399607
CHILD = 3622453
CHILD_TICKS = 478405342
HELPER = ROOT / 'var/research/exaone45_runtime_probe_v4.py'
HELPER_SHA = '7e2ff0e719304df4667baa988c416307405c61b5bca090f6609b8715eb024ee2'
CONFIG = ROOT / 'var/research/exaone45-native-launch-epoch1.json'
CONFIG_SHA = '1e872da88b6d00750447dd7c39213d7a4ce19b161fa64cb4c51cab1f7b8b7761'
OUTPUT = ROOT / 'var/reports/exaone45-epoch1-stop-request.json'


def require(ok, code):
    if not ok:
        raise ValueError(code)


def guard_identity():
    for pid in (GUARD, CHILD):
        require(Path(f'/proc/{pid}').stat().st_uid == os.getuid() == 1003, 'NOT_OWN_PROCESS')
    gs = Path(f'/proc/{GUARD}/stat').read_text().rsplit(')', 1)[1].split()
    cs = Path(f'/proc/{CHILD}/stat').read_text().rsplit(')', 1)[1].split()
    require(int(gs[19]) == GUARD_TICKS and int(cs[19]) == CHILD_TICKS
            and int(cs[1]) == GUARD, 'OWN_EPOCH_CHANGED')
    require(Path(f'/proc/{GUARD}/cmdline').read_bytes().split(b'\0')[:-1] == [
        b'.conda/bin/python', b'scripts/llama_server.py', b'--config',
        b'var/research/exaone45-native-launch-epoch1.json'], 'GUARD_ARGV_CHANGED')
    require(os.readlink(f'/proc/{GUARD}/exe') == str(ROOT / '.conda/bin/python3.12')
            and os.readlink(f'/proc/{GUARD}/cwd') == str(ROOT), 'GUARD_EXECUTABLE_CHANGED')


def main():
    require(not OUTPUT.exists() and not OUTPUT.is_symlink(), 'STOP_ALREADY_RECORDED')
    require(platform.machine() == 'x86_64', 'SYSCALL_ABI_UNSUPPORTED')
    uapi = Path('/usr/include/x86_64-linux-gnu/asm/unistd_64.h').read_text()
    for name, number in (('pidfd_open', 434), ('pidfd_send_signal', 424)):
        require(re.search(r'^#define __NR_' + name + r'\s+' + str(number) + r'$', uapi, re.M),
                'SYSCALL_NUMBER_UNVERIFIED')
    raw = HELPER.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == HELPER_SHA, 'HELPER_CHANGED')
    probe = ModuleType('exaone45_pinned_stop_probe')
    probe.__file__ = str(HELPER)
    exec(compile(raw, str(HELPER), 'exec'), probe.__dict__)
    config, _ = probe.load_config(CONFIG, CONFIG_SHA)
    guard, before_raw = probe.read_json(config.report_file)
    probe.validate_guard(config, guard, probe.exaone_binding(config))
    require(guard['child_pid'] == CHILD
            and guard['started_at_utc'] == '2026-09-20T10:33:32.120893+00:00', 'GUARD_REPORT_CHANGED')
    probe.epoch(config, CHILD, CHILD_TICKS)
    guard_identity()
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    fd = libc.syscall(434, GUARD, 0)
    if fd < 0:
        raise OSError(ctypes.get_errno(), 'PIDFD_OPEN_FAILED')
    try:
        guard_identity()
        result = libc.syscall(424, fd, signal.SIGTERM, ctypes.c_void_p(), 0)
        if result != 0:
            raise OSError(ctypes.get_errno(), 'PIDFD_SIGNAL_FAILED')
    finally:
        os.close(fd)
    receipt = {'kind': 'OWN_NATIVE_EPOCH_STOP_REQUEST', 'at_utc': datetime.now(timezone.utc).isoformat(),
        'guard_pid': GUARD, 'guard_start_ticks': GUARD_TICKS, 'child_pid': CHILD,
        'child_start_ticks': CHILD_TICKS, 'uid': os.getuid(), 'pidfd_signal': 'SIGTERM',
        'pidfd_method': 'verified x86_64 syscalls434/424; exact owned guard only',
        'guard_before_sha256': hashlib.sha256(before_raw).hexdigest(),
        'foreign_process_signals': 0, 'broad_process_matching_used': False,
        'child_signals_sent_by_this_helper': 0}
    with OUTPUT.open('x') as out:
        json.dump(receipt, out, indent=2); out.write('\n')
    print(json.dumps({'status': 'OWN_GUARD_TERM_REQUESTED', 'guard_pid': GUARD}))


if __name__ == '__main__':
    main()
