"""Own CPU socket and synthetic proc-table checks; no GPU or process signals."""

from contextlib import contextmanager, redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.verify_model_listeners import (
    ListenerCheckError, ProcReader, decode_endpoint, main, save_report, verify_listeners,
)


def tcp_row(inode="11", endpoint="0100007F:1F43", state="0A"):
    return f"0: {endpoint} 00000000:0000 {state} 0:0 0:0 0 1000 0 {inode} 1\n"


class FakeReader:
    def __init__(self, *, identities=(7, 7), inodes=({"11"}, {"11"}), tables=None, error=None):
        self.identities, self.inodes = iter(identities), iter(inodes)
        self.tables = {name: "header\n" for name in ("tcp", "tcp6", "unix", "udp", "udp6", "netlink", "raw", "raw6")}
        self.tables["tcp"] += tcp_row()
        self.tables.update(tables or {})
        self.error, self.reads = error, []

    def __call__(self, pid, uid):
        return self

    def __enter__(self):
        if self.error:
            raise self.error
        return self

    def __exit__(self, *_):
        pass

    def identity(self):
        return next(self.identities)

    def socket_inodes(self):
        return next(self.inodes)

    def read_text(self, name):
        self.reads.append(name)
        value = self.tables[name.removeprefix("net/")]
        if isinstance(value, Exception):
            raise value
        return value


@contextmanager
def own_cpu_listener(host, *, extras=False):
    source = """
import json, os, select, socket, sys
host = sys.argv[1]
family = socket.AF_INET6 if ':' in host else socket.AF_INET
listener = socket.socket(family, socket.SOCK_STREAM)
listener.bind((host, 0))
listener.listen(1)
owned = [listener]
if sys.argv[2] == 'extras':
    owned.extend(socket.socketpair())
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.bind(('127.0.0.1', 0))
    owned.append(udp)
print(json.dumps({'pid':os.getpid(), 'port':listener.getsockname()[1]}), flush=True)
select.select([sys.stdin], [], [], 10)
for item in owned:
    item.close()
"""
    child = subprocess.Popen([sys.executable, "-B", "-c", source, host, "extras" if extras else "plain"],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        row = child.stdout.readline()
        if not row:
            raise AssertionError(child.stderr.read())
        yield json.loads(row)
    finally:
        # EOF releases this tiny test process normally; no terminate/kill/signal.
        child.stdin.close()
        child.wait(timeout=12)
        child.stdout.close()
        child.stderr.close()


class ModelListenerTests(unittest.TestCase):
    def test_own_ipv4_loopback_with_unix_and_udp_descriptors_passes(self):
        with own_cpu_listener("127.0.0.1", extras=True) as child:
            report = verify_listeners(child["pid"])
            self.assertEqual(report["verdict"], "PASS", report)
            self.assertEqual(report["non_tcp_socket_count"], 3)
            self.assertEqual(report["listeners"], [{"family": "IPv4", "address": "127.0.0.1",
                                                  "port": child["port"], "loopback": True}])

    def test_own_ipv4_wildcard_is_blocked(self):
        with own_cpu_listener("0.0.0.0") as child:
            report = verify_listeners(child["pid"])
            self.assertEqual(report["reason_codes"], ["NON_LOOPBACK_LISTENER"])
            self.assertTrue(report["snapshot_complete"])
            self.assertFalse(report["all_loopback"])
            self.assertEqual(report["listeners"][0]["address"], "0.0.0.0")

    @unittest.skipUnless(socket.has_ipv6, "Kernel has no IPv6")
    def test_own_ipv6_loopback_and_wildcard(self):
        for host, verdict in (("::1", "PASS"), ("::", "BLOCKED")):
            with self.subTest(host=host), own_cpu_listener(host) as child:
                report = verify_listeners(child["pid"])
                self.assertEqual(report["verdict"], verdict, report)
                self.assertEqual(report["listeners"][0]["family"], "IPv6")

    def test_unrelated_table_rows_are_not_decoded_or_exposed(self):
        reader = FakeReader(tables={"tcp": "header\n" + tcp_row("999", "NOT_AN_OWN_ADDRESS") + tcp_row()})
        report = verify_listeners(os.getpid(), reader_factory=reader)
        self.assertEqual(report["verdict"], "PASS")
        self.assertNotIn("NOT_AN_OWN_ADDRESS", json.dumps(report))
        self.assertEqual(reader.reads, ["net/tcp", "net/tcp6"])

    def test_foreign_uid_is_rejected_before_proc_contents(self):
        with patch("scripts.verify_model_listeners.os.open", return_value=91), \
             patch("scripts.verify_model_listeners.os.fstat", return_value=SimpleNamespace(st_uid=os.getuid() + 1)), \
             patch("scripts.verify_model_listeners.os.close") as close, \
             patch.object(ProcReader, "read_text", side_effect=AssertionError("Foreign contents forbidden")) as read:
            report = verify_listeners(1234)
        self.assertEqual(report["reason_codes"], ["FOREIGN_PROCESS"])
        read.assert_not_called()
        close.assert_called_once_with(91)

    def test_permission_and_process_exit_fail_closed_without_exception_text(self):
        for error, code in ((PermissionError("DO_NOT_ECHO"), "PROC_ACCESS_DENIED"),
                            (FileNotFoundError("DO_NOT_ECHO"), "PROCESS_UNAVAILABLE"),
                            (ProcessLookupError("DO_NOT_ECHO"), "PROCESS_UNAVAILABLE")):
            with self.subTest(code=code):
                report = verify_listeners(1234, reader_factory=FakeReader(error=error))
                self.assertEqual(report["reason_codes"], [code])
                self.assertFalse(report["snapshot_complete"])
                self.assertNotIn("DO_NOT_ECHO", json.dumps(report))

    def test_identity_or_fd_inode_change_discards_partial_results(self):
        for reader in (FakeReader(identities=(7, 8)), FakeReader(inodes=({"11"}, {"11", "12"}))):
            report = verify_listeners(1234, reader_factory=reader)
            self.assertEqual(report["reason_codes"], ["UNSTABLE_SNAPSHOT"])
            self.assertEqual(report["listeners"], [])
            self.assertFalse(report["snapshot_complete"])

    def test_unresolved_socket_is_not_silently_ignored(self):
        reader = FakeReader(inodes=({"11", "88"}, {"11", "88"}))
        report = verify_listeners(1234, reader_factory=reader)
        self.assertEqual(report["reason_codes"], ["UNCLASSIFIED_SOCKET"])
        self.assertEqual(report["listeners"], [])

    def test_empty_fds_or_no_tcp_listener_cannot_pass_vacuously(self):
        cases = ((FakeReader(inodes=(set(), set())), "NO_SOCKET_FDS"),
                 (FakeReader(tables={"tcp": "header\n" + tcp_row(state="01")}), "NO_TCP_LISTENERS"))
        for reader, code in cases:
            with self.subTest(code=code):
                report = verify_listeners(1234, reader_factory=reader)
                self.assertEqual(report["reason_codes"], [code])
                self.assertFalse(report["all_loopback"])

    def test_missing_or_malformed_required_table_fails_closed(self):
        for value, code in ((FileNotFoundError(), "PROCESS_UNAVAILABLE"),
                            ("", "INVALID_PROC_DATA"),
                            ("header\nshort\n", "INVALID_PROC_DATA"),
                            ("header\n" + tcp_row(endpoint="broken"), "INVALID_PROC_DATA")):
            with self.subTest(code=code):
                report = verify_listeners(1234, reader_factory=FakeReader(tables={"tcp": value}))
                self.assertEqual(report["verdict"], "BLOCKED")
                self.assertEqual(report["reason_codes"], [code])

    def test_invalid_pid_never_opens_proc(self):
        for pid in (True, "123", None, 0, -1, 2**31):
            with self.subTest(pid=pid), patch("scripts.verify_model_listeners.os.open") as opened:
                report = verify_listeners(pid)
                self.assertEqual(report["reason_codes"], ["INVALID_PID"])
                opened.assert_not_called()

    def test_ipv6_mapped_loopback_and_nonloopback_are_distinguished(self):
        self.assertTrue(decode_endpoint("0000000000000000FFFF00000100007F:1F43", True)["loopback"])
        self.assertFalse(decode_endpoint("0000000000000000FFFF000000000000:1F43", True)["loopback"])
        self.assertFalse(decode_endpoint("0100000A:1F43", False)["loopback"])

    def test_report_destination_is_confined_and_symlinks_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = {"verdict": "PASS"}
            save_report(Path("var/reports/listeners.json"), report, root)
            self.assertEqual(json.loads((root / "var/reports/listeners.json").read_text()), report)
            for path in (Path("outside.json"), root.parent / "outside.json", Path("var/models/config.json")):
                with self.assertRaises(ListenerCheckError):
                    save_report(path, report, root)
            link = root / "var/reports/link.json"
            link.symlink_to(root / "var/reports/listeners.json")
            with self.assertRaises(ListenerCheckError):
                save_report(link, report, root)

    def test_existing_report_and_competing_creator_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "var/reports/listeners.json"
            path.parent.mkdir(parents=True)
            path.write_bytes(b"existing evidence")
            with self.assertRaisesRegex(ListenerCheckError, "REPORT_EXISTS"):
                save_report(path, {"verdict": "PASS"}, root)
            self.assertEqual(path.read_bytes(), b"existing evidence")
            raced_path = path.with_name("raced.json")
            original_link = os.link

            def competing_creator(source, destination):
                Path(destination).write_bytes(b"competing evidence")
                original_link(source, destination)

            with patch("scripts.verify_model_listeners.os.link", side_effect=competing_creator):
                with self.assertRaisesRegex(ListenerCheckError, "REPORT_EXISTS"):
                    save_report(raced_path, {"verdict": "PASS"}, root)
            self.assertEqual(raced_path.read_bytes(), b"competing evidence")
            self.assertEqual(sorted(item.name for item in path.parent.iterdir()), ["listeners.json", "raced.json"])

    def test_cli_emits_machine_readable_blocked_verdict(self):
        output = StringIO()
        with redirect_stdout(output):
            exit_code = main(["--pid", "0"])
        self.assertEqual(exit_code, 2)
        self.assertEqual(json.loads(output.getvalue())["reason_codes"], ["INVALID_PID"])


if __name__ == "__main__":
    unittest.main()
