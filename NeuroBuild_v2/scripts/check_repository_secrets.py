"""Scan tracked working-tree files or the complete Git index without leaking matches.

Only paths, rule identifiers and counts are reported. Git ignores are respected for
untracked files; an already tracked file is always scanned. Symlink text is scanned
without opening its target. Submodules, unreadable files, unresolved index entries
and files over 64 MiB fail closed. This is a pattern check, not a history scan or a
claim that every possible credential format can be recognized.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import errno
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys


MAX_FILE_BYTES = 64 * 1024 * 1024
RAW_EVIDENCE_EXTENSIONS = {".html", ".htm", ".js", ".mjs", ".cjs"}
RULES = (
    ("GOOGLE_API_KEY", rb"(?<![A-Za-z0-9_-])AIza[A-Za-z0-9_-]{35}(?![A-Za-z0-9_-])"),
    ("HUGGING_FACE_TOKEN", rb"(?<![A-Za-z0-9_])hf_[A-Za-z0-9]{25,}(?![A-Za-z0-9_])"),
    ("GITHUB_TOKEN", rb"(?<![A-Za-z0-9_])(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})(?![A-Za-z0-9_])"),
    ("AWS_ACCESS_KEY_ID", rb"(?<![A-Z0-9])(?:AKIA|ASIA)[A-Z0-9]{16}(?![A-Z0-9])"),
    ("PRIVATE_KEY", rb"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"),
    ("SLACK_TOKEN", rb"(?<![A-Za-z0-9_-])(?:xox[baprs]-[A-Za-z0-9-]{10,}|xapp-[A-Za-z0-9-]{10,})(?![A-Za-z0-9_-])"),
    ("STRIPE_SECRET_KEY", rb"(?<![A-Za-z0-9_])(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}(?![A-Za-z0-9_])"),
    ("OPENAI_API_KEY", rb"(?<![A-Za-z0-9_-])sk-(?:(?:proj|svcacct)-[A-Za-z0-9_-]{20,}|[A-Za-z0-9]{20,})(?![A-Za-z0-9_-])"),
)
PATTERNS = tuple((name, re.compile(pattern)) for name, pattern in RULES)


class ScanError(Exception):
    """A fixed diagnostic identifier, never an external error message."""

    def __init__(self, rule_id: str):
        self.rule_id = rule_id
        super().__init__(rule_id)


class FatalIndexError(ScanError):
    """Stop the batch reader before consuming an oversized or invalid object."""


def safe_path(path: str) -> str:
    """Even credentials accidentally used as filenames must not be printed."""
    value = os.fsencode(path)
    for rule_id, pattern in PATTERNS:
        value = pattern.sub(("[REDACTED:" + rule_id + "]").encode(), value)
    return os.fsdecode(value)


def git(repository: Path, *arguments: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", "--no-replace-objects", "-C", os.fspath(repository), *arguments],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, check=False, timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        raise ScanError("SCAN_GIT_ERROR") from None
    if result.returncode:
        raise ScanError("SCAN_GIT_ERROR")
    return result.stdout


def inventory(repository: Path) -> list[tuple[str, str, str, str]]:
    entries = []
    for record in git(repository, "ls-files", "--stage", "--full-name", "-z").split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, oid, stage = metadata.decode("ascii").split()
            path = os.fsdecode(raw_path)
            if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", oid):
                raise ValueError
            if not path or any(part in ("", ".", "..") for part in path.split("/")):
                raise ValueError
            if stage not in {"0", "1", "2", "3"}:
                raise ValueError
        except (ValueError, UnicodeError):
            raise ScanError("SCAN_INDEX_FORMAT") from None
        entries.append((mode, oid, stage, path))
    return entries


@contextmanager
def index_reader(repository: Path):
    """One local cat-file process; object IDs, never filenames, enter its protocol."""
    try:
        process = subprocess.Popen(
            ["git", "--no-replace-objects", "-C", os.fspath(repository), "cat-file", "--batch"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
    except OSError:
        raise ScanError("SCAN_GIT_ERROR") from None
    try:
        yield process
        process.stdin.close()
        if process.wait(timeout=60):
            raise ScanError("SCAN_GIT_ERROR")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        process.stdin.close()
        process.stdout.close()


def read_blob(process: subprocess.Popen, oid: str) -> bytes:
    process.stdin.write(oid.encode("ascii") + b"\n")
    process.stdin.flush()
    header = process.stdout.readline(256).split()
    if len(header) != 3 or header[0] != oid.encode("ascii") or header[1] != b"blob":
        raise FatalIndexError("SCAN_GIT_BLOB_ERROR")
    try:
        size = int(header[2])
    except ValueError:
        raise FatalIndexError("SCAN_GIT_BLOB_ERROR") from None
    if size < 0:
        raise FatalIndexError("SCAN_GIT_BLOB_ERROR")
    if size > MAX_FILE_BYTES:
        raise FatalIndexError("SCAN_FILE_TOO_LARGE")
    remaining = size
    chunks = []
    while remaining:
        chunk = process.stdout.read(min(remaining, 1024 * 1024))
        if not chunk:
            raise FatalIndexError("SCAN_GIT_BLOB_ERROR")
        chunks.append(chunk)
        remaining -= len(chunk)
    if process.stdout.read(1) != b"\n":
        raise FatalIndexError("SCAN_GIT_BLOB_ERROR")
    return b"".join(chunks)


def read_worktree(root_fd: int, path: str) -> bytes | None:
    """Use directory descriptors so no tracked path can follow an outside symlink."""
    parts = path.split("/")
    directory = os.dup(root_fd)
    try:
        for part in parts[:-1]:
            try:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                dir_fd=directory)
            except FileNotFoundError:
                return None  # ordinary unstaged deletion
            except OSError as exc:
                if exc.errno in (errno.ELOOP, errno.ENOTDIR):
                    raise ScanError("SCAN_UNSAFE_PARENT") from None
                raise
            os.close(directory)
            directory = child
        try:
            info = os.stat(parts[-1], dir_fd=directory, follow_symlinks=False)
        except FileNotFoundError:
            return None
        if stat.S_ISLNK(info.st_mode):
            return os.fsencode(os.readlink(parts[-1], dir_fd=directory))
        if not stat.S_ISREG(info.st_mode):
            raise ScanError("SCAN_NOT_REGULAR_FILE")
        descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                             dir_fd=directory)
        with os.fdopen(descriptor, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
                raise ScanError("SCAN_FILE_CHANGED")
            if opened.st_size > MAX_FILE_BYTES:
                raise ScanError("SCAN_FILE_TOO_LARGE")
            content = stream.read(MAX_FILE_BYTES + 1)
            if len(content) > MAX_FILE_BYTES:
                raise ScanError("SCAN_FILE_TOO_LARGE")
            after = os.fstat(stream.fileno())
            if (opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise ScanError("SCAN_FILE_CHANGED")
            return content
    finally:
        os.close(directory)


def forbidden_raw_evidence(path: str) -> bool:
    parts = path.lower().split("/")
    evidence_path = parts[:2] == ["evaluations", "results"]
    provenance_path = any("provenance" in part for part in parts[:-1])
    return (evidence_path or provenance_path) and Path(parts[-1]).suffix in RAW_EVIDENCE_EXTENSIONS


def scan_repository(repository: Path, *, staged: bool = False) -> dict:
    report = {"findings": [], "errors": [], "counts": {
        "tracked_files": 0, "scanned_files": 0, "missing_worktree_files": 0,
        "findings": 0, "errors": 0,
    }}

    def add(section: str, path: str, rule_id: str, count: int = 1):
        report[section].append({"path": safe_path(path), "rule_id": rule_id, "count": count})
        report["counts"][section] += count

    def inspect(entries, read):
        seen = set()
        for mode, oid, stage, path in entries:
            if path in seen:
                continue
            seen.add(path)
            report["counts"]["tracked_files"] += 1
            try:
                if stage != "0":
                    raise ScanError("SCAN_UNMERGED_INDEX")
                if mode == "160000":
                    raise ScanError("SCAN_SUBMODULE_UNSUPPORTED")
                if mode not in {"100644", "100755", "120000"}:
                    raise ScanError("SCAN_INDEX_MODE")
                content = read(oid, path)
                if content is None:
                    report["counts"]["missing_worktree_files"] += 1
                    continue
                report["counts"]["scanned_files"] += 1
                if forbidden_raw_evidence(path):
                    add("findings", path, "RAW_EXTERNAL_EVIDENCE")
                for rule_id, pattern in PATTERNS:
                    count = sum(1 for _ in pattern.finditer(content))
                    if count:
                        add("findings", path, rule_id, count)
            except FatalIndexError as exc:
                exc.path = path
                raise
            except ScanError as exc:
                add("errors", path, exc.rule_id)
            except OSError:
                add("errors", path, "SCAN_FILE_READ_ERROR")

    try:
        # Run from the discovered root so subdirectory invocation still scans all files.
        raw_root = git(repository, "rev-parse", "--show-toplevel")
        root = Path(os.fsdecode(raw_root.removesuffix(b"\n")))
        entries = inventory(root)
        if staged:
            with index_reader(root) as process:
                inspect(entries, lambda oid, path: read_blob(process, oid))
        else:
            root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                inspect(entries, lambda oid, path: read_worktree(root_fd, path))
            finally:
                os.close(root_fd)
    except ScanError as exc:
        add("errors", getattr(exc, "path", "."), exc.rule_id)
    except (OSError, subprocess.SubprocessError):
        add("errors", ".", "SCAN_IO_ERROR")
    return report


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's default echoes unknown arguments, which could contain a token.
        raise ScanError("SCAN_ARGUMENT_ERROR")


def main(argv: list[str] | None = None) -> int:
    parser = SafeArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true", help="scan every file in the index")
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    try:
        args = parser.parse_args(argv)
        report = scan_repository(args.repository, staged=args.staged)
    except ScanError as exc:
        report = {"findings": [], "errors": [{"path": ".", "rule_id": exc.rule_id, "count": 1}],
                  "counts": {"tracked_files": 0, "scanned_files": 0,
                             "missing_worktree_files": 0, "findings": 0, "errors": 1}}
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))
    return 2 if report["counts"]["errors"] else int(bool(report["counts"]["findings"]))


if __name__ == "__main__":
    sys.exit(main())
