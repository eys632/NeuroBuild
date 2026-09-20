#!/usr/bin/env python3
"""Check TCP listeners owned by one current-UID process; never query other PIDs."""

import argparse
from datetime import datetime, timezone
import ipaddress
import json
import os
from pathlib import Path
import re
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]


class ListenerCheckError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def require(condition, code):
    if not condition:
        raise ListenerCheckError(code)


class ProcReader:
    """Anchor a single proc directory before UID validation; PID reuse cannot retarget reads."""

    def __init__(self, pid, uid):
        self.pid, self.uid, self.descriptor = pid, uid, None

    def __enter__(self):
        self.descriptor = os.open(f"/proc/{self.pid}", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            require(os.fstat(self.descriptor).st_uid == self.uid, "FOREIGN_PROCESS")
        except BaseException:
            os.close(self.descriptor)
            self.descriptor = None
            raise
        return self

    def __exit__(self, *_):
        os.close(self.descriptor)

    def read_text(self, name):
        descriptor = os.open(name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=self.descriptor)
        with os.fdopen(descriptor, "r", encoding="ascii", errors="strict") as stream:
            return stream.read()

    def identity(self):
        require(os.fstat(self.descriptor).st_uid == self.uid, "FOREIGN_PROCESS")
        statuses = self.read_text("status").splitlines()
        identifiers = [line.split()[1:] for line in statuses if line.startswith("Uid:")]
        require(len(identifiers) == 1 and len(identifiers[0]) == 4
                and all(value.isdecimal() and int(value) == self.uid for value in identifiers[0]), "FOREIGN_PROCESS")
        # comm may contain spaces or parentheses; no name/command is returned.
        fields = self.read_text("stat").rsplit(")", 1)
        require(len(fields) == 2, "INVALID_PROC_DATA")
        tail = fields[1].split()
        require(len(tail) >= 20 and tail[19].isdecimal(), "INVALID_PROC_DATA")
        require(tail[0] not in ("Z", "X", "x"), "PROCESS_UNAVAILABLE")
        return int(tail[19])

    def socket_inodes(self):
        descriptor = os.open("fd", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
                             dir_fd=self.descriptor)
        try:
            inodes = set()
            for name in os.listdir(descriptor):
                require(name.isdecimal(), "INVALID_PROC_DATA")
                try:
                    target = os.readlink(name, dir_fd=descriptor)
                except FileNotFoundError:
                    raise ListenerCheckError("UNSTABLE_SNAPSHOT") from None
                if target.startswith("socket:"):
                    match = re.fullmatch(r"socket:\[([1-9][0-9]*)\]", target)
                    require(match is not None, "INVALID_PROC_DATA")
                    inodes.add(match[1])
            return inodes
        finally:
            os.close(descriptor)


def decode_endpoint(value, ipv6):
    match = re.fullmatch(r"([0-9A-Fa-f]{32}|[0-9A-Fa-f]{8}):([0-9A-Fa-f]{4})", value)
    require(match is not None and len(match[1]) == (32 if ipv6 else 8), "INVALID_PROC_DATA")
    packed = b"".join(int(match[1][offset:offset + 8], 16).to_bytes(4, sys.byteorder)
                      for offset in range(0, len(match[1]), 8))
    address = ipaddress.ip_address(packed)
    loopback = address.is_loopback or (address.version == 6 and address.ipv4_mapped is not None
                                       and address.ipv4_mapped.is_loopback)
    return {"family": "IPv6" if ipv6 else "IPv4", "address": str(address),
            "port": int(match[2], 16), "loopback": bool(loopback)}


def classify_sockets(reader, inodes):
    """Filter table rows by already-owned socket inode before decoding addresses."""
    found, tcp_inodes, listeners = set(), set(), []
    # These are network-namespace tables, not PID-only tables. Only rows joining
    # our verified PID's FD inodes are inspected further, returned or persisted.
    for table in ("tcp", "tcp6", "unix", "udp", "udp6", "netlink", "raw", "raw6"):
        if table not in ("tcp", "tcp6") and found == inodes:
            break
        lines = reader.read_text("net/" + table).splitlines()
        require(bool(lines), "INVALID_PROC_DATA")
        inode_column = 6 if table == "unix" else 9
        for line in lines[1:]:
            if not line.strip():
                continue
            fields = line.split()
            require(len(fields) > inode_column and fields[inode_column].isdecimal(), "INVALID_PROC_DATA")
            inode = fields[inode_column]
            if inode not in inodes:
                continue
            require(inode not in found, "UNSTABLE_SNAPSHOT")
            found.add(inode)
            if table in ("tcp", "tcp6"):
                tcp_inodes.add(inode)
                require(re.fullmatch(r"[0-9A-Fa-f]{2}", fields[3]) is not None, "INVALID_PROC_DATA")
                if fields[3].upper() == "0A":
                    listeners.append(decode_endpoint(fields[1], table == "tcp6"))
    require(found == inodes, "UNCLASSIFIED_SOCKET")
    return sorted(listeners, key=lambda item: (item["family"], item["address"], item["port"])), len(inodes - tcp_inodes)


def verify_listeners(pid, *, reader_factory=ProcReader):
    report = {"schema_version": 1, "pid": pid if type(pid) is int else None,
              "checked_at_utc": datetime.now(timezone.utc).isoformat(), "scope": "OWN_UID_PID_TCP_LISTENERS",
              "verdict": "BLOCKED", "all_loopback": False, "snapshot_complete": False,
              "listeners": [], "reason_codes": [],
              "notice": "One process and one snapshot only; no descendant, UDP exposure, firewall or future-listener guarantee."}
    try:
        require(type(pid) is int and 0 < pid <= 2147483647, "INVALID_PID")
        uid = os.getuid()
        require(os.geteuid() == uid, "UID_CONTEXT_UNSUPPORTED")
        with reader_factory(pid, uid) as reader:
            before = reader.identity()
            inodes = reader.socket_inodes()
            require(bool(inodes), "NO_SOCKET_FDS")
            listeners, other_count = classify_sockets(reader, inodes)
            require(reader.socket_inodes() == inodes and reader.identity() == before, "UNSTABLE_SNAPSHOT")
        require(bool(listeners), "NO_TCP_LISTENERS")
        report.update(process_start_ticks=before, uid=uid, socket_inode_count=len(inodes),
                      non_tcp_socket_count=other_count, listeners=listeners, snapshot_complete=True)
        report["all_loopback"] = all(listener["loopback"] for listener in listeners)
        report["verdict"] = "PASS" if report["all_loopback"] else "BLOCKED"
        report["reason_codes"] = [] if report["all_loopback"] else ["NON_LOOPBACK_LISTENER"]
    except ListenerCheckError as error:
        report["reason_codes"] = [error.code]
    except PermissionError:
        report["reason_codes"] = ["PROC_ACCESS_DENIED"]
    except (FileNotFoundError, ProcessLookupError):
        report["reason_codes"] = ["PROCESS_UNAVAILABLE"]
    except (OSError, UnicodeError, ValueError):
        report["reason_codes"] = ["PROC_READ_FAILED"]
    return report


def save_report(value, report, root=ROOT):
    path = Path(value)
    path = root / path if not path.is_absolute() else path
    boundary = root / "var" / "reports"
    require(not (root / "var").is_symlink() and not boundary.is_symlink(), "INVALID_REPORT_PATH")
    boundary = boundary.resolve()
    require(boundary.is_relative_to(root.resolve()) and not path.is_symlink(), "INVALID_REPORT_PATH")
    path = path.resolve()
    require(path.is_relative_to(boundary) and path != boundary, "INVALID_REPORT_PATH")
    require(not path.exists(), "REPORT_EXISTS")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".listeners-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        # Atomic no-clobber publication also covers a competing creator after
        # the earlier existence check. Existing reports and task data survive.
        try:
            os.link(temporary, path)
        except FileExistsError:
            raise ListenerCheckError("REPORT_EXISTS") from None
    finally:
        Path(temporary).unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", required=True, type=int, help="One process owned by the current UID")
    parser.add_argument("--report-file", type=Path,
                        help="New JSON snapshot below this checkout's var/reports directory; never overwrites")
    args = parser.parse_args(argv)
    report = verify_listeners(args.pid)
    if args.report_file is not None:
        try:
            save_report(args.report_file, report)
        except (ListenerCheckError, OSError):
            report.update(verdict="BLOCKED", all_loopback=False, report_write_failed=True)
            report["reason_codes"].append("REPORT_WRITE_FAILED")
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
