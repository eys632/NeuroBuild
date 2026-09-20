"""Pinned source/tool acquisition only; run explicitly with project .conda Python.

No subprocesses, tool execution, build, weights, CUDA, or package installation.
Existing outputs are never reused/overwritten. Failed partial trees are retained
for review and must never be used as successful build inputs.
"""
from __future__ import annotations

import contextlib
import datetime as dt
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tarfile
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).absolute().parents[2]
PIN = "f072b103714dfa1eee531f80b24512faf38e3dd2"
CMAKE_NAME = "cmake-3.23.5-linux-x86_64"
CMAKE_BYTES = 46_031_464
CMAKE_SHA256 = "bbd7ad93d2a14ed3608021a9466ae63db76a24efd1fae7a5f7798c1de7ab9344"
EXPECTED_BLOBS = 3607
EXPECTED_SOURCE_BYTES = 172_243_701
MiB = 1024**2
GiB = 1024**3
RESERVE = 20 * GiB
TOTAL_LIMIT = GiB
REPORT_LIMIT = 256 * 1024
MAX_FILE = 128 * MiB
MAX_MEMBERS = 20_000
DOWNLOAD_DIR = f"var/runtime-downloads/llama-{PIN}"
SOURCE_DIR = f"var/runtime-src/llama.cpp-{PIN}"
TOOL_DIR = f"var/tools/{CMAKE_NAME}"
REPORT = "var/reports/llama-source-bootstrap.json"
COMMIT_URL = f"https://api.github.com/repos/ggml-org/llama.cpp/git/commits/{PIN}"
TREE_URL_BASE = "https://api.github.com/repos/ggml-org/llama.cpp/git/trees/"
SOURCE_URL = f"https://codeload.github.com/ggml-org/llama.cpp/tar.gz/{PIN}"
CMAKE_URL = f"https://github.com/Kitware/CMake/releases/download/v3.23.5/{CMAKE_NAME}.tar.gz"
ALLOWED_HOSTS = frozenset({"github.com", "api.github.com", "codeload.github.com",
                           "release-assets.githubusercontent.com", "objects.githubusercontent.com"})


class BootstrapError(Exception):
    pass


def require(ok: bool, code: str) -> None:
    if not ok:
        raise BootstrapError(code)


def parts(name: str) -> tuple[str, ...]:
    require(isinstance(name, str) and bool(name) and not name.startswith("/"), "UNSAFE_PATH")
    require("\\" not in name and not any(ord(c) < 32 or ord(c) == 127 for c in name), "UNSAFE_PATH")
    value = tuple(name.split("/"))
    require(len(value) <= 64 and all(p not in ("", ".", "..") for p in value), "UNSAFE_PATH")
    return value


def strict_json(data: bytes):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(BootstrapError("INVALID_JSON")))
    except (UnicodeError, ValueError) as error:
        raise BootstrapError("INVALID_JSON") from error


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def check_url(url: str) -> None:
    value = urllib.parse.urlsplit(url)
    require(value.scheme == "https" and value.hostname in ALLOWED_HOSTS
            and value.port in (None, 443) and value.username is None
            and value.password is None and not value.fragment, "UNSAFE_URL")


class PinnedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Workspace:
    """Owned directories via dir_fd; new namespaces are private mode 0700.

    Existing project ancestors are 0775 with this account's primary GID. Their
    permissions are not changed: own UID/GID and no world-write are required.
    """
    def __init__(self):
        require(ROOT == Path("/home/a202192020/NeuroBuild_v2"), "WRONG_PROJECT_ROOT")
        require(sys.version_info[:2] == (3, 12)
                and Path(sys.prefix).absolute() == ROOT / ".conda", "WRONG_PYTHON_ENVIRONMENT")
        self.root_fd = os.open(ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            self._directory(self.root_fd)
        except BaseException:
            os.close(self.root_fd)
            raise
        self.owned_dirs: set[str] = set()
        self.bytes_charged = 0
        self.started = time.monotonic()
        self.free_start = shutil.disk_usage(ROOT).free
        self.reserve(0)

    def close(self):
        os.close(self.root_fd)

    @staticmethod
    def _directory(fd: int):
        s = os.fstat(fd)
        require(stat.S_ISDIR(s.st_mode) and s.st_uid == os.getuid()
                and s.st_gid == os.getgid() and not (s.st_mode & 0o002), "UNSAFE_DIRECTORY")

    def reserve(self, more: int, *, report=False):
        require(report or time.monotonic() - self.started <= 900, "BOOTSTRAP_TIME_LIMIT")
        ceiling = TOTAL_LIMIT if report else TOTAL_LIMIT - REPORT_LIMIT
        require(more >= 0 and self.bytes_charged + more <= ceiling, "BOOTSTRAP_SIZE_LIMIT")
        require(shutil.disk_usage(ROOT).free >= RESERVE + more, "DISK_RESERVE_REQUIRED")

    def charge(self, more: int, *, report=False):
        self.reserve(more, report=report)
        self.bytes_charged += more

    @contextlib.contextmanager
    def parent(self, relative: str, *, create=False):
        components = parts(relative)
        require(components[0] == "var" and len(components) >= 2, "OUTSIDE_PROJECT_VAR")
        fd = os.dup(self.root_fd)
        walked = []
        try:
            for component in components[:-1]:
                walked.append(component)
                if create:
                    try:
                        self.charge(4096)
                        os.mkdir(component, 0o700, dir_fd=fd)
                        self.owned_dirs.add("/".join(walked))
                    except FileExistsError:
                        self.bytes_charged -= 4096
                nxt = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                self._directory(nxt)
                os.close(fd)
                fd = nxt
            yield fd, components[-1]
        finally:
            os.close(fd)

    def absent(self, relative: str):
        try:
            with self.parent(relative) as (fd, name):
                try:
                    os.stat(name, dir_fd=fd, follow_symlinks=False)
                except FileNotFoundError:
                    return
                raise BootstrapError("OUTPUT_ALREADY_EXISTS")
        except FileNotFoundError:
            return

    def mkdir(self, relative: str):
        with self.parent(relative, create=True) as (fd, name):
            self.charge(4096)
            os.mkdir(name, 0o700, dir_fd=fd)
            self.owned_dirs.add(relative)
            os.fsync(fd)

    def ensure_owned_dir(self, relative: str):
        if relative in self.owned_dirs:
            with self.parent(relative + "/_check"):
                return
        self.mkdir(relative)

    @contextlib.contextmanager
    def new_file(self, relative: str, *, report=False):
        with self.parent(relative, create=not report) as (parent_fd, name):
            self.charge(4096, report=report)
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=parent_fd)
            try:
                s = os.fstat(fd)
                require(stat.S_ISREG(s.st_mode) and s.st_uid == os.getuid() and s.st_nlink == 1,
                        "UNSAFE_OUTPUT_FILE")
                with os.fdopen(fd, "wb", closefd=False) as stream:
                    yield stream, fd
                    stream.flush()
                    os.fsync(fd)
                os.fsync(parent_fd)
            finally:
                os.close(fd)

    @contextlib.contextmanager
    def read_file(self, relative: str):
        with self.parent(relative) as (fd, name):
            file_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
            try:
                s = os.fstat(file_fd)
                require(stat.S_ISREG(s.st_mode) and s.st_uid == os.getuid()
                        and s.st_nlink == 1, "UNSAFE_INPUT_FILE")
                with os.fdopen(file_fd, "rb", closefd=False) as stream:
                    yield stream
            finally:
                os.close(file_fd)

    def put_json(self, relative: str, value: dict):
        data = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
        require(len(data) <= REPORT_LIMIT, "REPORT_SIZE_LIMIT")
        with self.new_file(relative, report=True) as (stream, _):
            self.charge(len(data), report=True)
            stream.write(data)


def download(ws: Workspace, url: str, relative: str, maximum: int, *, size=None, sha256=None) -> dict:
    check_url(url)
    ws.absent(relative)
    ws.reserve(size if size is not None else maximum)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), PinnedRedirect())
    request = urllib.request.Request(url, headers={"User-Agent": "NeuroBuild-source-bootstrap/1",
                                                   "Accept-Encoding": "identity"})
    digest = hashlib.sha256()
    count = 0
    with opener.open(request, timeout=30) as response:
        check_url(response.geturl())
        require(response.status == 200, "DOWNLOAD_HTTP_STATUS")
        declared = response.headers.get("Content-Length")
        if declared is not None:
            require(declared.isascii() and declared.isdigit() and int(declared) <= maximum,
                    "DOWNLOAD_DECLARED_SIZE")
            if size is not None:
                require(int(declared) == size, "DOWNLOAD_DECLARED_SIZE")
        require(response.headers.get("Content-Encoding", "identity").lower() == "identity",
                "DOWNLOAD_ENCODING")
        with ws.new_file(relative) as (stream, _):
            while True:
                block = response.read(min(MiB, maximum - count + 1))
                if not block:
                    break
                count += len(block)
                require(count <= maximum, "DOWNLOAD_SIZE_LIMIT")
                ws.charge(len(block))
                digest.update(block)
                stream.write(block)
    require(size is None or count == size, "DOWNLOAD_SIZE_MISMATCH")
    require(sha256 is None or digest.hexdigest() == sha256, "DOWNLOAD_HASH_MISMATCH")
    return {"url": url, "path": relative, "bytes": count, "sha256": digest.hexdigest()}


def validate_tree(commit: dict, tree: dict):
    require(type(commit) is dict and commit.get("sha") == PIN, "COMMIT_ID_MISMATCH")
    require(type(tree) is dict and tree.get("truncated") is False, "TREE_INCOMPLETE")
    root_sha = commit.get("tree", {}).get("sha")
    require(type(root_sha) is str and re.fullmatch("[0-9a-f]{40}", root_sha)
            and tree.get("sha") == root_sha, "TREE_COMMIT_BINDING")
    require(type(tree.get("tree")) is list and len(tree["tree"]) <= MAX_MEMBERS, "TREE_SIZE_LIMIT")
    entries = {}
    for item in tree["tree"]:
        require(type(item) is dict, "INVALID_TREE_ENTRY")
        name = item.get("path")
        parts(name)
        require(name not in entries, "DUPLICATE_TREE_PATH")
        mode, kind, digest = item.get("mode"), item.get("type"), item.get("sha")
        require(type(digest) is str and re.fullmatch("[0-9a-f]{40}", digest), "INVALID_TREE_HASH")
        require((kind == "tree" and mode == "040000")
                or (kind == "blob" and mode in ("100644", "100755", "120000")),
                "UNSUPPORTED_TREE_MODE_OR_GITLINK")
        if kind == "blob":
            require(type(item.get("size")) is int and 0 <= item["size"] <= MAX_FILE,
                    "INVALID_TREE_BLOB_SIZE")
        entries[name] = item
    blobs = {name: e for name, e in entries.items() if e["type"] == "blob"}
    require(len(blobs) == EXPECTED_BLOBS and sum(e["size"] for e in blobs.values())
            == EXPECTED_SOURCE_BYTES, "UNEXPECTED_SOURCE_INVENTORY")
    for name in entries:
        parent = str(PurePosixPath(name).parent)
        require(parent == "." or parent in entries and entries[parent]["type"] == "tree",
                "TREE_PARENT_MISSING")
    # Check every directory hash, including the commit-bound root tree.
    def directory_sha(parent):
        children = [(name.rsplit("/", 1)[-1], e) for name, e in entries.items()
                    if str(PurePosixPath(name).parent) == parent]
        children.sort(key=lambda pair: pair[0].encode() + (b"/" if pair[1]["type"] == "tree" else b""))
        raw = b"".join(("40000" if e["type"] == "tree" else e["mode"]).encode()
                       + b" " + name.encode() + b"\0" + bytes.fromhex(e["sha"])
                       for name, e in children)
        return hashlib.sha1(b"tree " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    for name, e in entries.items():
        if e["type"] == "tree":
            require(directory_sha(name) == e["sha"], "TREE_OBJECT_HASH_MISMATCH")
    require(directory_sha(".") == root_sha, "ROOT_TREE_OBJECT_HASH_MISMATCH")
    return entries


def verify_symlink_metadata(entries: dict, targets: dict):
    """Resolve authenticated link chains lexically without probing other paths."""
    for link in targets:
        pending = list(PurePosixPath(link).parts)
        resolved = []
        hops = 0
        while pending:
            component = pending.pop(0)
            if component in ("", "."):
                continue
            if component == "..":
                require(bool(resolved), "ESCAPING_SYMLINK_CHAIN")
                resolved.pop()
                continue
            name = "/".join(resolved + [component])
            require(name in entries, "DANGLING_SYMLINK_CHAIN")
            entry = entries[name]
            if entry["mode"] == "120000":
                hops += 1
                require(hops <= 64 and name in targets, "CYCLIC_SYMLINK_CHAIN")
                target = targets[name]
                require(not target.startswith("/"), "ESCAPING_SYMLINK_CHAIN")
                pending = target.split("/") + pending
            else:
                require(not pending or entry["type"] == "tree", "NON_DIRECTORY_SYMLINK_CHAIN")
                resolved.append(component)
        require(bool(resolved), "SYMLINK_TO_ROOT_REJECTED")


class BoundedTarReader(io.RawIOBase):
    def __init__(self, source, maximum):
        self.source, self.remaining = source, maximum

    def read(self, size=-1):
        limit = min(1024 * 1024, self.remaining + 1, size if size >= 0 else 1024 * 1024)
        data = self.source.read(limit)
        self.remaining -= len(data)
        require(self.remaining >= 0, "TAR_DECOMPRESSED_SIZE_LIMIT")
        return data


def extract(ws: Workspace, archive: str, destination: str, prefix: str,
            maximum_expanded: int, expected=None):
    ws.mkdir(destination)
    seen, total, targets = set(), 0, {}
    with ws.read_file(archive) as source, gzip.GzipFile(fileobj=source) as decompressed:
        bounded = BoundedTarReader(decompressed, maximum_expanded)
        with tarfile.open(fileobj=bounded, mode="r|") as tar:
            for original in tar:
                require(len(seen) < MAX_MEMBERS, "TAR_MEMBER_COUNT_LIMIT")
                name = original.name.rstrip("/") if original.isdir() else original.name
                path = parts(name)
                require(path[0] == prefix, "TAR_ROOT_MISMATCH")
                tail = "/".join(path[1:])
                require(tail not in seen, "DUPLICATE_TAR_PATH")
                seen.add(tail)
                require(not original.sparse and not (original.mode & 0o7000), "UNSAFE_TAR_MODE")
                if not tail:
                    require(original.isdir(), "INVALID_TAR_ROOT")
                    continue
                # Filter the exact stripped path actually written, not archive prefix twice.
                try:
                    member = tarfile.data_filter(original.replace(name=tail), str(ROOT / destination))
                except tarfile.FilterError as error:
                    raise BootstrapError("TAR_FILTER_REJECTED") from error
                require(member is not None, "TAR_FILTER_REJECTED")
                entry = expected.get(tail) if expected is not None else None
                if expected is not None:
                    require(entry is not None, "EXTRA_SOURCE_MEMBER")
                relative = destination + "/" + tail
                if member.isdir():
                    require(entry is None or entry["type"] == "tree", "SOURCE_TYPE_MISMATCH")
                    ws.ensure_owned_dir(relative)
                    continue
                require(member.isfile() or member.issym(), "UNSAFE_TAR_ENTRY_TYPE")
                require(0 <= member.size <= MAX_FILE, "TAR_MEMBER_SIZE_LIMIT")
                if member.issym():
                    require(entry is not None and entry["mode"] == "120000", "UNEXPECTED_SYMLINK")
                    target = original.linkname
                    require(target and not target.startswith("/") and "\\" not in target
                            and not any(ord(c) < 32 or ord(c) == 127 for c in target), "UNSAFE_SYMLINK")
                    target_parts = list(PurePosixPath(tail).parts[:-1])
                    for component in target.split("/"):
                        if component in ("", "."):
                            continue
                        if component == "..":
                            require(bool(target_parts), "ESCAPING_SYMLINK")
                            target_parts.pop()
                        else:
                            target_parts.append(component)
                    require("/".join(target_parts) in expected, "SYMLINK_TARGET_NOT_IN_TREE")
                    data = os.fsencode(target)
                    require(len(data) == entry["size"] and git_blob(data) == entry["sha"],
                            "SOURCE_SYMLINK_HASH_MISMATCH")
                    targets[tail] = target
                    with ws.parent(relative, create=True) as (fd, basename):
                        ws.charge(4096 + len(data))
                        os.symlink(target, basename, dir_fd=fd)
                        os.fsync(fd)
                    total += len(data)
                    continue
                executable = bool(original.mode & 0o111)
                mode = "100755" if executable else "100644"
                require(entry is None or entry["mode"] == mode and entry["size"] == member.size,
                        "SOURCE_SIZE_OR_MODE_MISMATCH")
                ws.reserve(member.size)
                payload = tar.extractfile(member)
                require(payload is not None, "TAR_PAYLOAD_MISSING")
                digest = hashlib.sha1(b"blob " + str(member.size).encode() + b"\0")
                written = 0
                with payload, ws.new_file(relative) as (output, fd):
                    while block := payload.read(MiB):
                        written += len(block)
                        require(written <= member.size, "TAR_MEMBER_OVERFLOW")
                        ws.charge(len(block))
                        output.write(block)
                        digest.update(block)
                    require(written == member.size, "TAR_MEMBER_TRUNCATED")
                    require(entry is None or digest.hexdigest() == entry["sha"], "SOURCE_BLOB_HASH_MISMATCH")
                    os.fchmod(fd, 0o755 if executable else 0o644)
                total += written
            # tar stops at its first zero header. Reject hidden concatenated
            # archives/nonzero trailers and consume gzip fully to verify CRC.
            while trailer := tar.fileobj.read(MiB):
                require(not any(trailer), "NONZERO_TAR_TRAILER")
    if expected is not None:
        require({name for name in seen if name} == set(expected), "SOURCE_MEMBER_SET_MISMATCH")
        verify_symlink_metadata(expected, targets)
    return {"path": destination, "archive_member_count": len(seen), "payload_bytes": total}


def verify_source(ws: Workspace, entries: dict):
    actual = set()
    modes = {}
    total = 0
    targets = {}
    for base, directories, files in os.walk(ROOT / SOURCE_DIR, followlinks=False):
        for name in directories + files:
            relative = (Path(base) / name).relative_to(ROOT / SOURCE_DIR).as_posix()
            require(relative in entries, "EXTRA_EXTRACTED_SOURCE_PATH")
            actual.add(relative)
            e = entries[relative]
            with ws.parent(SOURCE_DIR + "/" + relative) as (fd, basename):
                s = os.stat(basename, dir_fd=fd, follow_symlinks=False)
                require(s.st_uid == os.getuid(), "SOURCE_OWNER_MISMATCH")
                if e["type"] == "tree":
                    require(stat.S_ISDIR(s.st_mode) and not s.st_mode & 0o022, "SOURCE_DIRECTORY_MISMATCH")
                    continue
                if e["mode"] == "120000":
                    require(stat.S_ISLNK(s.st_mode), "SOURCE_SYMLINK_MISMATCH")
                    data = os.fsencode(os.readlink(basename, dir_fd=fd))
                    require(len(data) == e["size"] and git_blob(data) == e["sha"], "SOURCE_BLOB_HASH_MISMATCH")
                    targets[relative] = os.fsdecode(data)
                else:
                    require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1
                            and stat.S_IMODE(s.st_mode) == (0o755 if e["mode"] == "100755" else 0o644),
                            "SOURCE_MODE_MISMATCH")
                    digest = hashlib.sha1(b"blob " + str(e["size"]).encode() + b"\0")
                    count = 0
                    with ws.read_file(SOURCE_DIR + "/" + relative) as source:
                        while block := source.read(MiB):
                            count += len(block)
                            require(count <= e["size"], "SOURCE_SIZE_MISMATCH")
                            digest.update(block)
                    require(count == e["size"] and digest.hexdigest() == e["sha"], "SOURCE_BLOB_HASH_MISMATCH")
                total += e["size"]
                modes[e["mode"]] = modes.get(e["mode"], 0) + 1
    require(actual == set(entries), "EXTRACTED_SOURCE_SET_MISMATCH")
    verify_symlink_metadata(entries, targets)
    return {"verified_blobs": sum(modes.values()), "verified_blob_bytes": total,
            "git_modes": modes, "extra_or_missing_paths": 0, "verification": "GIT_BLOB_SHA1_SIZE_MODE"}


def main():
    require(len(sys.argv) == 1, "NO_ARGUMENTS_ALLOWED")
    ws = Workspace()
    report = {"kind": "LLAMA_SOURCE_TOOL_BOOTSTRAP", "status": "FAILED",
              "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "llama_commit": PIN, "source_path": SOURCE_DIR, "tool_path": TOOL_DIR,
              "report_path": REPORT, "downloads": [], "no_tool_execution": True,
              "no_build": True, "no_weights": True, "no_gpu_calls": True,
              "disk_reserve_bytes": RESERVE, "bootstrap_storage_limit_bytes": TOTAL_LIMIT}
    report_available = False
    try:
        for name in (DOWNLOAD_DIR, SOURCE_DIR, TOOL_DIR, REPORT):
            ws.absent(name)
        report_available = True
        with ws.parent(REPORT, create=True):
            pass
        ws.mkdir(DOWNLOAD_DIR)
        report["downloads"].append(download(ws, COMMIT_URL, DOWNLOAD_DIR + "/commit.json", MiB))
        with ws.read_file(DOWNLOAD_DIR + "/commit.json") as stream:
            commit = strict_json(stream.read(MiB + 1))
        require(type(commit) is dict and commit.get("sha") == PIN
                and type(commit.get("tree")) is dict, "COMMIT_ID_MISMATCH")
        root_tree_sha = commit["tree"].get("sha")
        require(type(root_tree_sha) is str and re.fullmatch("[0-9a-f]{40}", root_tree_sha),
                "INVALID_COMMIT_TREE_HASH")
        # Resolve the pin to its actual tree object first; do not rely on how
        # GitHub reports .sha when /git/trees is addressed by a commit alias.
        tree_url = TREE_URL_BASE + root_tree_sha + "?recursive=1"
        report["downloads"].append(download(ws, tree_url, DOWNLOAD_DIR + "/tree.json", 2 * MiB))
        with ws.read_file(DOWNLOAD_DIR + "/tree.json") as stream:
            tree = strict_json(stream.read(2 * MiB + 1))
        entries = validate_tree(commit, tree)
        report["source_tree_sha1"] = tree["sha"]
        source_archive = DOWNLOAD_DIR + f"/llama.cpp-{PIN}.tar.gz"
        report["downloads"].append(download(ws, SOURCE_URL, source_archive, 128 * MiB))
        report["source_extraction"] = extract(ws, source_archive, SOURCE_DIR, f"llama.cpp-{PIN}",
                                                256 * MiB, expected=entries)
        report["source_verification"] = verify_source(ws, entries)
        cmake_archive = DOWNLOAD_DIR + f"/{CMAKE_NAME}.tar.gz"
        report["downloads"].append(download(ws, CMAKE_URL, cmake_archive, CMAKE_BYTES,
                                            size=CMAKE_BYTES, sha256=CMAKE_SHA256))
        report["tool_extraction"] = extract(ws, cmake_archive, TOOL_DIR, CMAKE_NAME, 512 * MiB)
        # Verify the intended tool exists and is executable without running it.
        with ws.parent(TOOL_DIR + "/bin/cmake") as (fd, name):
            value = os.stat(name, dir_fd=fd, follow_symlinks=False)
            require(stat.S_ISREG(value.st_mode) and value.st_uid == os.getuid()
                    and value.st_nlink == 1 and value.st_mode & 0o111, "CMAKE_TOOL_MISSING")
        tool_digest = hashlib.sha256()
        tool_size = 0
        with ws.read_file(TOOL_DIR + "/bin/cmake") as tool:
            while block := tool.read(MiB):
                tool_size += len(block)
                require(tool_size <= MAX_FILE, "CMAKE_TOOL_SIZE_LIMIT")
                tool_digest.update(block)
        require(tool_size == value.st_size, "CMAKE_TOOL_SIZE_CHANGED")
        report["tool_identity"] = {"path": TOOL_DIR + "/bin/cmake", "bytes": tool_size,
                                   "sha256": tool_digest.hexdigest(), "executed": False}
        report["status"] = "PASS"
    except Exception as error:
        report["error_code"] = str(error) if isinstance(error, BootstrapError) else type(error).__name__
        # Never include response bodies, signed redirects, or exception stack traces.
        raise
    finally:
        try:
            report["charged_storage_bytes_before_report"] = ws.bytes_charged
            report["available_bytes_before"] = ws.free_start
            report["available_bytes_after"] = shutil.disk_usage(ROOT).free
            report["elapsed_seconds"] = round(time.monotonic() - ws.started, 3)
            if report_available:
                ws.put_json(REPORT, report)
        finally:
            ws.close()
    print(json.dumps({"status": report["status"], "report": REPORT}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        code = str(error) if isinstance(error, BootstrapError) else type(error).__name__
        print(json.dumps({"status": "FAILED", "error_code": code,
                          "partial_outputs_retained": True}), file=sys.stderr)
        raise SystemExit(1)
