#!/usr/bin/env python3
"""Explicit A100 native runtime adapter; no model download, protocol or GPU fallback."""
import argparse
from dataclasses import dataclass, fields
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import threading

try:
    from .gpu_preflight import Policy, PreflightError
    from .model_guard import require, local_path, run_lifecycle
except ImportError:
    from gpu_preflight import Policy, PreflightError
    from model_guard import require, local_path, run_lifecycle

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PIN = "f072b103714dfa1eee531f80b24512faf38e3dd2"
HASH = r"[a-f0-9]{64}"


def checked_file(path, root, *, sibling_of=None):
    path = root / path if not path.is_absolute() else path
    require(path.is_relative_to(root), "INVALID_PATH", "Native inputs must belong to this checkout")
    if sibling_of is None:
        require(not path.is_symlink(), "INVALID_PATH", "Native inputs must not be symlink aliases")
    else:
        require(path.parent == sibling_of and path.resolve().parent == sibling_of,
                "INVALID_PATH", "Native libraries must remain in the fixed binary directory")
    resolved = path.resolve()
    require(resolved.is_relative_to(root), "INVALID_PATH", "Native path escaped the checkout")
    for parent in path.parents:
        if parent == root:
            break
        require(not parent.is_symlink(), "INVALID_PATH", "Native directories must not be aliases")
    info = resolved.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and info.st_nlink == 1,
            "INVALID_PATH", "Native inputs must be owned regular files without hardlink aliases")
    return resolved


def verified_hash(path, expected, *, expected_bytes=None):
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
        after = os.fstat(stream.fileno())
    signature = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
    require(signature(before) == signature(after), "NATIVE_INPUT_CHANGED", "An input changed during validation")
    require(digest == expected and (expected_bytes is None or after.st_size == expected_bytes),
            "NATIVE_HASH_MISMATCH", "Native input bytes do not match pinned evidence")


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def load_proof(path, expected, root):
    path = checked_file(path, root)
    require(path.stat().st_size <= 2 * 1024 * 1024, "INVALID_NATIVE_PROOF", "Proof is too large")
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == expected, "NATIVE_HASH_MISMATCH", "Proof hash mismatch")
    return json.loads(raw, object_pairs_hook=_pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("constant")))


def reject_output_collisions(config, root, *inputs):
    outputs = {local_path(config.log_file, root, output=True),
               local_path(config.report_file, root, output=True)}
    require(outputs.isdisjoint(Path(path).resolve() for path in inputs),
            "INVALID_PATH", "Runtime output must not replace native input or evidence files")


@dataclass(frozen=True)
class NativeLaunchConfig:
    profile: str
    binary_path: Path
    binary_sha256: str
    build_report: Path
    build_report_sha256: str
    source_report: Path
    source_report_sha256: str
    source_commit: str
    model_path: Path
    model_sha256: str
    model_revision: str
    model_header_report: Path
    model_header_report_sha256: str
    estimated_peak_mib: int
    log_file: Path
    report_file: Path
    enable_reasoning: bool = False
    served_model_name: str = "neurobuild-local"
    port: int = 8003
    max_seconds: float = 1800
    max_model_len: int = 4096
    peak_allowance_mib: int = 0

    def __post_init__(self):
        Policy(self.profile, self.estimated_peak_mib)
        require(self.profile == "a100", "RUNTIME_PROFILE_NOT_VALIDATED", "Native SM80 launch supports only A100 physical GPU3")
        require(self.source_commit == SOURCE_PIN, "INVALID_CONFIG", "Use the reviewed source pin")
        for value in (self.binary_sha256, self.build_report_sha256, self.source_report_sha256,
                      self.model_sha256, self.model_header_report_sha256):
            require(type(value) is str and re.fullmatch(HASH, value) is not None,
                    "INVALID_CONFIG", "Exact SHA256 pins are required")
        require(type(self.model_revision) is str and re.fullmatch(r"[a-f0-9]{40}", self.model_revision) is not None,
                "INVALID_CONFIG", "An exact model revision is required")
        require(type(self.enable_reasoning) is bool and type(self.port) is int and 1024 <= self.port <= 65535,
                "INVALID_CONFIG", "Explicit mode and unprivileged port required")
        require(type(self.max_seconds) in (int, float) and math.isfinite(self.max_seconds)
                and 1 <= self.max_seconds <= 43200, "INVALID_CONFIG", "Execution needs a bounded duration")
        require(type(self.max_model_len) is int and self.max_model_len == 4096
                and type(self.peak_allowance_mib) is int and self.peak_allowance_mib == 0,
                "INVALID_CONFIG", "Native context4096 and zero peak allowance are fixed")
        require(type(self.served_model_name) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}", self.served_model_name),
                "INVALID_CONFIG", "Use a short safe model alias")
        for field in fields(self):
            if field.name.endswith("_path") or field.name in ("build_report", "source_report", "model_header_report", "log_file", "report_file"):
                require(isinstance(getattr(self, field.name), Path), "INVALID_CONFIG", "Use explicit local paths")


def child_environment(root, environ):
    # Start from a tiny allowlist; inherited LLAMA/GGML/LD/python/proxy settings are absent.
    child = {key: environ[key] for key in ("HOME", "LANG", "LC_ALL", "TZ") if key in environ}
    child.update(CUDA_VISIBLE_DEVICES="3", CUDA_DEVICE_ORDER="PCI_BUS_ID", PYTHONNOUSERSITE="1",
                 PATH="/usr/bin:/bin", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                 GGML_CUDA_DISABLE_GRAPHS="1", GGML_CUDA_PDL="0")
    for variable, directory in {"LLAMA_CACHE": "llama", "CUDA_CACHE_PATH": "cuda-native",
                                "XDG_CACHE_HOME": "xdg-native", "TMPDIR": "tmp-native"}.items():
        path = local_path(root / "var/cache" / directory, root, output=True)
        path.mkdir(parents=True, exist_ok=True)
        child[variable] = str(path)
    return child


def native_arguments(config, root):
    return [str(checked_file(config.binary_path, root)), "--model", str(checked_file(config.model_path, root)),
            "--alias", config.served_model_name, "--host", "127.0.0.1", "--port", str(config.port),
            "--device", "CUDA0", "--main-gpu", "0", "--split-mode", "none", "--gpu-layers", "all",
            "--fit", "off", "--ctx-size", "4096", "--parallel", "1", "--no-context-shift",
            "--cache-type-k", "f16", "--cache-type-v", "f16", "--flash-attn", "off",
            "--batch-size", "1", "--ubatch-size", "1", "--threads", "2", "--threads-batch", "2",
            "--threads-http", "1", "--ctx-checkpoints", "0", "--cache-ram", "0",
            "--no-cache-idle-slots", "--no-cache-prompt", "--offline", "--no-mmproj", "--no-ui",
            "--no-ui-mcp-proxy", "--no-models-autoload", "--jinja", "--reasoning",
            "on" if config.enable_reasoning else "off", "--reasoning-format", "deepseek",
            "--no-reasoning-preserve", "--no-skip-chat-parsing", "--log-disable"]


class _NativeRuntime:
    def __init__(self):
        self.read_fd = self.write_fd = None
        self.buffer = bytearray()
        self.identity_done = False
        self.artifacts = None

    def initial_fields(self, config):
        return {"runtime_family": "llama_cpp", "enable_reasoning": config.enable_reasoning,
                "reasoning_parser": "deepseek",
                "native_reasoning_format": "deepseek", "native_identity_verified": False,
                "native_output_policy": "DISCARD_STDOUT_STDERR", "native_core_dump_limit_bytes": 0,
                "native_all_tensor_gpu_residency_verified": False,
                "native_allocation_policy": "EXPLICIT_CUDA0_ALL_LAYERS_FIT_OFF_NO_CAPACITY_FALLBACK",
                "native_cpu_notice": "Fixed CPU input embeddings or unsupported operations may still exist; arguments do not prove every tensor is GPU resident.",
                "ready": False}

    def validate(self, config, root, model):
        try:
            binary = checked_file(config.binary_path, root)
            model = checked_file(config.model_path, root)
            proofs = [checked_file(path, root) for path in
                      (config.build_report, config.source_report, config.model_header_report)]
            reject_output_collisions(config, root, binary, model, *proofs)
            require(model.suffix == ".gguf" and os.access(binary, os.X_OK),
                    "INVALID_NATIVE_PROOF", "Local GGUF and executable native binary required")
            require(not binary.stat().st_mode & (stat.S_ISUID | stat.S_ISGID),
                    "INVALID_NATIVE_PROOF", "Privilege-changing binaries are forbidden")
            build = load_proof(config.build_report, config.build_report_sha256, root)
            source = load_proof(config.source_report, config.source_report_sha256, root)
            header = load_proof(config.model_header_report, config.model_header_report_sha256, root)
            require(source["kind"] == "LLAMA_SOURCE_TOOL_BOOTSTRAP" and source["status"] == "PASS"
                    and source["llama_commit"] == config.source_commit, "INVALID_NATIVE_PROOF", "Source evidence mismatch")
            for key, value in {"verified_blobs": 3607, "verified_blob_bytes": 172243701, "extra_or_missing_paths": 0}.items():
                require(type(source["source_verification"][key]) is int and source["source_verification"][key] == value,
                        "INVALID_NATIVE_PROOF", "Source inventory mismatch")
            require(all(source[key] is True for key in
                        ("no_build", "no_weights", "no_gpu_calls", "no_tool_execution")),
                    "INVALID_NATIVE_PROOF", "Source bootstrap scope mismatch")
            require(build["status"] == "COMPILE_PASS_NOT_RUNTIME_VALIDATED"
                    and build["source_pin"] == config.source_commit
                    and build["bootstrap_report_sha256"] == config.source_report_sha256
                    and build["binary_sha256"] == config.binary_sha256,
                    "INVALID_NATIVE_PROOF", "Build evidence mismatch")
            require(type(build["original_compile_report_sha256"]) is str
                    and re.fullmatch(HASH, build["original_compile_report_sha256"]),
                    "INVALID_NATIVE_PROOF", "Original compile report binding required")
            for key, value in {"CMAKE_CUDA_ARCHITECTURES": "80-real", "GGML_CUDA": "ON",
                               "GGML_NATIVE": "OFF", "GGML_BACKEND_DL": "OFF",
                               "LLAMA_SUBPROCESS": "OFF", "GGML_CUDA_GRAPHS": "OFF"}.items():
                require(build["settings"][key] == value, "INVALID_NATIVE_PROOF", "Build configuration mismatch")
            deps = build["runtime_dependencies"]
            require(type(deps) is list and 1 <= len(deps) <= 64, "INVALID_NATIVE_PROOF", "Pinned native library closure required")
            names = []
            for dep in deps:
                require(type(dep) is dict and set(dep) == {"path", "bytes", "sha256"}
                        and type(dep["path"]) is str
                        and type(dep["bytes"]) is int and dep["bytes"] > 0
                        and type(dep["sha256"]) is str and re.fullmatch(HASH, dep["sha256"]),
                        "INVALID_NATIVE_PROOF", "Invalid native dependency record")
                library = checked_file(Path(dep["path"]), root, sibling_of=binary.parent)
                reject_output_collisions(config, root, library)
                require(not (root / dep["path"]).is_symlink()
                        and re.fullmatch(r"lib[A-Za-z0-9_-]+\.so(?:\.[0-9]+)*", library.name),
                        "INVALID_NATIVE_PROOF", "Dependency hashes must name real shared libraries")
                require(not library.name.startswith(("libcuda.", "libcudart.", "libnvidia")),
                        "INVALID_NATIVE_PROOF", "Driver/toolkit replacements are forbidden")
                verified_hash(library, dep["sha256"], expected_bytes=dep["bytes"])
                names.append(Path(dep["path"]).name)
            require(len(names) == len(set(names)) and any(n.startswith("libllama.") for n in names)
                    and any(n.startswith("libggml-cuda.") for n in names),
                    "INVALID_NATIVE_PROOF", "Required CUDA/llama libraries are missing")
            aliases = build["runtime_dependency_symlinks"]
            require(type(aliases) is list and len(aliases) <= 128,
                    "INVALID_NATIVE_PROOF", "Invalid library alias inventory")
            alias_names = set()
            for alias in aliases:
                require(type(alias) is dict and set(alias) == {"path", "target", "real_path"}
                        and all(type(value) is str for value in alias.values()),
                        "INVALID_NATIVE_PROOF", "Invalid library alias record")
                path = root / alias["path"]
                target = checked_file(path, root, sibling_of=binary.parent)
                reject_output_collisions(config, root, path, target)
                require(path.is_symlink() and os.readlink(path) == alias["target"]
                        and Path(alias["target"]).name == alias["target"]
                        and str(target.relative_to(root)) == alias["real_path"]
                        and target.name in names and path.name not in alias_names,
                        "INVALID_NATIVE_PROOF", "Library alias differs from linked evidence")
                alias_names.add(path.name)
            require({path.name for path in binary.parent.glob("*.so*")} == set(names) | alias_names,
                    "INVALID_NATIVE_PROOF", "Binary directory library inventory changed")
            require(header["kind"] == "GGUF_HEADER_AUDIT" and header["status"] == "PASS"
                    and header["model_path"] == str(model.relative_to(root))
                    and header["file_sha256"] == config.model_sha256
                    and header["revision"] == config.model_revision
                    and type(header["file_bytes"]) is int and header["file_bytes"] > 0,
                    "INVALID_NATIVE_PROOF", "GGUF header evidence mismatch")
            verified_hash(binary, config.binary_sha256)
            verified_hash(model, config.model_sha256, expected_bytes=header["file_bytes"])
            runtime = root / ".conda-vllm/bin/python"
            require(runtime.is_file() and runtime.resolve().is_relative_to((root / ".conda-vllm").resolve()),
                    "RUNTIME_NOT_LOCAL", "Project-owned bootstrap Python required")
            checked_file(root / "scripts/native_model_bootstrap.py", root)
            self.artifacts = {"binary_sha256": config.binary_sha256, "build_report_sha256": config.build_report_sha256,
                              "source_report_sha256": config.source_report_sha256, "source_commit": config.source_commit,
                              "model_sha256": config.model_sha256, "model_revision": config.model_revision,
                              "model_header_report_sha256": config.model_header_report_sha256,
                              "project_library_count": len(deps)}
        except PreflightError:
            raise
        except (KeyError, TypeError, ValueError, UnicodeError):
            raise PreflightError("INVALID_NATIVE_PROOF", "Pinned native evidence is malformed") from None

    def environment(self, config, root, environ):
        return child_environment(root, environ)

    def fields(self, config):
        return {"allocator_cap_kind": "NONE_VERIFIED", "torch_allocator_fraction": None,
                "gpu_memory_utilization": None, "native_artifacts": self.artifacts,
                "max_num_seqs": 1, "batch_size": 1, "ubatch_size": 1,
                "cache_type_k": "f16", "cache_type_v": "f16", "flash_attention": "off", "skip_chat_parsing": False}

    def check_budget(self, config, total, budget):
        pass  # Common preflight applies the required explicit whole-peak estimate.

    def prepare(self, config, root, report):
        self.read_fd, self.write_fd = os.pipe()
        os.set_blocking(self.read_fd, False)
        return [str(root / ".conda-vllm/bin/python"), "-I", "-B", str(root / "scripts/native_model_bootstrap.py"),
                str(os.getpid()), str(self.write_fd), *native_arguments(config, root)]

    def output_options(self, log):
        return {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL, "pass_fds": (self.write_fd,)}

    def after_spawn(self, child):
        os.close(self.write_fd)
        self.write_fd = None

    def observe(self, child, report):
        if self.identity_done:
            return
        try:
            chunk = os.read(self.read_fd, 4097 - len(self.buffer))
        except BlockingIOError:
            chunk = None
        if chunk:
            self.buffer.extend(chunk)
            require(len(self.buffer) <= 4096, "NATIVE_BOOTSTRAP_INVALID", "Bootstrap status exceeded its bound")
        if chunk == b"":
            try:
                value = json.loads(self.buffer, object_pairs_hook=_pairs)
                require(value.get("pid") == child.pid, "NATIVE_BOOTSTRAP_INVALID", "Bootstrap identity mismatch")
                if value.get("event") == "BOOTSTRAP_FAILED":
                    allowed = {"CUDA_MASK_MISMATCH", "GPU_IDENTITY_FAILED", "GPU_IDENTITY_MISMATCH",
                               "WATCHDOG_PARENT_CHANGED", "WATCHDOG_DEATH_SIGNAL_FAILED", "BOOTSTRAP_FAILED"}
                    code = value.get("code")
                    require(code in allowed, "NATIVE_BOOTSTRAP_INVALID", "Unknown bootstrap status")
                    raise PreflightError(code, "Native bootstrap rejected startup")
                require(value == {"event": "GPU_IDENTITY_VERIFIED", "pid": child.pid,
                                  "physical_gpu_index": 3, "logical_device": 0},
                        "NATIVE_BOOTSTRAP_INVALID", "Invalid bootstrap identity record")
            except PreflightError:
                raise
            except (ValueError, TypeError, AttributeError):
                raise PreflightError("NATIVE_BOOTSTRAP_INVALID", "Invalid bootstrap status") from None
            self.identity_done = True
            report["native_identity_verified"] = True
            os.close(self.read_fd)
            self.read_fd = None
        require(self.identity_done or report["elapsed_seconds"] < 15,
                "NATIVE_BOOTSTRAP_TIMEOUT", "Native identity was not confirmed within its bound")

    def cleanup(self, report, safe_to_release):
        for name in ("read_fd", "write_fd"):
            descriptor = getattr(self, name)
            if descriptor is not None:
                os.close(descriptor)
                setattr(self, name, None)


def run_guard(config, *, root=ROOT, **injections):
    return run_lifecycle(config, _NativeRuntime(), root=root, **injections)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path, help="Explicit local JSON launch pins and budget")
    arguments = parser.parse_args(argv)
    stop = threading.Event()
    previous = {sig: signal.signal(sig, lambda *_: stop.set()) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        try:
            path = checked_file(arguments.config, ROOT)
            require(path.stat().st_size <= 65536, "INVALID_CONFIG", "Config is too large")
            values = json.loads(path.read_text(), object_pairs_hook=_pairs)
            for key in ("binary_path", "build_report", "source_report", "model_path", "model_header_report", "log_file", "report_file"):
                values[key] = Path(values[key])
            config = NativeLaunchConfig(**values)
            reject_output_collisions(config, ROOT, path)
            report = run_guard(config, stop_requested=stop.is_set)
        except PreflightError as error:
            report = {"state": "BLOCKED", "reason": error.code}
        except (OSError, ValueError, TypeError, KeyError):
            report = {"state": "BLOCKED", "reason": "INVALID_CONFIG"}
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    print(json.dumps(report, indent=2, allow_nan=False))
    clean = report.get("reason") in ("TIME_LIMIT", "STOP_REQUESTED") or (
        report.get("reason") == "CHILD_EXITED" and report.get("child_exit_code") == 0)
    return 0 if clean and report.get("native_identity_verified") and report.get("shutdown", {}).get("child_reaped") else 2


if __name__ == "__main__":
    raise SystemExit(main())
