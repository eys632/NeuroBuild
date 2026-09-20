"""Native launch boundaries; only temporary files, fake children and fake GPU readings."""
from contextlib import redirect_stdout
from dataclasses import asdict, replace
from io import StringIO
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import llama_server as native
from scripts.gpu_preflight import PreflightError
from scripts.model_guard import acquire_project_lock

STABLE = "40960, 36373, 3965, 0"


class FakeChild:
    pid = 765433
    returncode = None

    def wait(self, timeout):
        self.returncode = -15
        return self.returncode


class NativeGuardTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.binary = self.write("var/runtime-build/pin/bin/llama-server", b"fake binary; never run")
        self.binary.chmod(0o755)
        self.model = self.write("var/models/pin/model.gguf", b"fake GGUF; never run")
        self.write(".conda-vllm/bin/python", b"fake Python; never run")
        self.write("scripts/native_model_bootstrap.py", b"fake bootstrap; never run")
        self.libs = [self.write("var/runtime-build/pin/bin/" + name, name.encode())
                     for name in ("libllama.so.0", "libggml-cuda.so.0")]
        alias = self.binary.parent / "libllama.so"
        alias.symlink_to(self.libs[0].name)
        self.source = {"kind": "LLAMA_SOURCE_TOOL_BOOTSTRAP", "status": "PASS", "llama_commit": native.SOURCE_PIN,
                       "source_verification": {"verified_blobs": 3607, "verified_blob_bytes": 172243701, "extra_or_missing_paths": 0},
                       "no_build": True, "no_weights": True, "no_gpu_calls": True, "no_tool_execution": True}
        self.source_path = self.proof("source", self.source)
        self.build = {"status": "COMPILE_PASS_NOT_RUNTIME_VALIDATED", "source_pin": native.SOURCE_PIN,
                      "bootstrap_report_sha256": self.sha(self.source_path), "binary_sha256": self.sha(self.binary),
                      "original_compile_report_sha256": "a" * 64,
                      "settings": {"CMAKE_CUDA_ARCHITECTURES": "80-real", "GGML_CUDA": "ON", "GGML_NATIVE": "OFF",
                                   "GGML_BACKEND_DL": "OFF", "LLAMA_SUBPROCESS": "OFF", "GGML_CUDA_GRAPHS": "OFF"},
                      "runtime_dependencies": [{"path": str(p.relative_to(self.root)), "bytes": p.stat().st_size,
                                                "sha256": self.sha(p)} for p in self.libs],
                      "runtime_dependency_symlinks": [{"path": str(alias.relative_to(self.root)), "target": self.libs[0].name,
                                                       "real_path": str(self.libs[0].relative_to(self.root))}]}
        self.build_path = self.proof("build", self.build)
        self.header = {"kind": "GGUF_HEADER_AUDIT", "status": "PASS", "model_path": str(self.model.relative_to(self.root)),
                       "file_sha256": self.sha(self.model), "file_bytes": self.model.stat().st_size, "revision": "b" * 40}
        self.header_path = self.proof("header", self.header)
        self.config = native.NativeLaunchConfig(
            profile="a100", binary_path=self.binary, binary_sha256=self.sha(self.binary),
            build_report=self.build_path, build_report_sha256=self.sha(self.build_path),
            source_report=self.source_path, source_report_sha256=self.sha(self.source_path), source_commit=native.SOURCE_PIN,
            model_path=self.model, model_sha256=self.sha(self.model), model_revision="b" * 40,
            model_header_report=self.header_path, model_header_report_sha256=self.sha(self.header_path),
            estimated_peak_mib=25600, log_file=Path("var/logs/native.log"), report_file=Path("var/reports/native.json"),
            max_seconds=2)
        self.addCleanup(patch.stopall)
        patch("scripts.model_guard._query_gpu", side_effect=AssertionError("Actual GPU query forbidden")).start()
        patch("scripts.model_guard.subprocess.Popen", side_effect=AssertionError("Actual native launch forbidden")).start()
        patch("scripts.model_guard.os.killpg", side_effect=AssertionError("Actual process signal forbidden")).start()

    def write(self, path, data):
        path = self.root / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def proof(self, name, value):
        return self.write("var/reports/" + name + ".json", json.dumps(value).encode())

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def run_fake(self, *, config=None, rows=(), status=None, env=None, spawn_error=False):
        now, queried, launched, signals = [0.0], [], [], []
        readings = iter([STABLE] * 5 + list(rows))
        terminated = [False]
        child = FakeChild()
        child.returncode = None
        held_fds = []

        def query(index):
            queried.append(index)
            row = next(readings, STABLE)
            if isinstance(row, Exception):
                raise row
            return row

        def sleep(duration):
            now[0] += duration

        def popen(command, **kwargs):
            if spawn_error:
                raise OSError("synthetic spawn failure")
            launched.append((command, kwargs))
            if status is False:
                held_fds.append(os.dup(kwargs["pass_fds"][0]))
                return child
            value = status if status is not None else {"event": "GPU_IDENTITY_VERIFIED", "pid": child.pid,
                                                       "physical_gpu_index": 3, "logical_device": 0}
            os.write(kwargs["pass_fds"][0], json.dumps(value).encode())
            return child

        def killpg(pid, sig):
            signals.append((pid, sig))
            terminated[0] = True

        try:
            report = native.run_guard(config or self.config, root=self.root, environ=env or {"CUDA_VISIBLE_DEVICES": "3"},
                                      query=query, sleep=sleep, monotonic=lambda: now[0], popen=popen,
                                      killpg=killpg, peek_exit=lambda _: terminated[0])
        finally:
            for fd in held_fds:
                os.close(fd)
        return report, queried, launched, signals

    def test_owned_bounded_lifecycle_discard_streams_and_report_is_not_readiness(self):
        with patch.object(native, "verified_hash", wraps=native.verified_hash) as digest:
            report, queries, launches, signals = self.run_fake()
        self.assertEqual(report["reason"], "TIME_LIMIT")
        self.assertEqual(report["state"], "STOPPED")
        self.assertTrue(report["native_identity_verified"])
        self.assertFalse(report["ready"])
        self.assertFalse(report["per_process_measurement"])
        self.assertFalse(report["memory_fit_guaranteed"])
        self.assertIsNone(report["torch_allocator_fraction"])
        self.assertEqual(report["required_free_floor_mib"], 7275)
        self.assertEqual(report["aggregate_increment_limit_mib"], 25600)
        self.assertEqual((report["batch_size"], report["ubatch_size"], report["max_num_seqs"]), (2, 1, 1))
        self.assertEqual(queries, [3] * 9)
        self.assertEqual(signals, [(FakeChild.pid, signal.SIGTERM), (FakeChild.pid, signal.SIGKILL)])
        self.assertEqual(sum(call.args[0] == self.model for call in digest.call_args_list), 1)
        command, kwargs = launches[0]
        self.assertEqual(kwargs["stdout"], subprocess.DEVNULL)
        self.assertEqual(kwargs["stderr"], subprocess.DEVNULL)
        self.assertTrue(kwargs["start_new_session"])
        self.assertEqual(command[:3], [str(self.root / ".conda-vllm/bin/python"), "-I", "-B"])
        self.assertEqual((self.root / self.config.log_file).read_bytes(), b"")
        self.assertEqual(json.loads((self.root / self.config.report_file).read_text()), report)

    def test_explicit_native_command_and_thinking_do_not_enable_fallback(self):
        off = native.native_arguments(self.config, self.root)
        on = native.native_arguments(replace(self.config, enable_reasoning=True), self.root)
        self.assertEqual([(a, b) for a, b in zip(off, on) if a != b], [("off", "on")])
        for key, value in {"--host": "127.0.0.1", "--device": "CUDA0", "--gpu-layers": "all",
                           "--split-mode": "none", "--fit": "off", "--ctx-size": "4096", "--parallel": "1",
                           "--batch-size": "2", "--ubatch-size": "1", "--reasoning-format": "deepseek",
                           "--cache-type-k": "f16", "--cache-type-v": "f16", "--flash-attn": "off"}.items():
            self.assertEqual(off.count(key), 1)
            self.assertEqual(off[off.index(key) + 1], value)
        for flag in ("--offline", "--no-mmproj", "--no-ui", "--no-ui-mcp-proxy", "--no-models-autoload",
                     "--no-reasoning-preserve", "--no-skip-chat-parsing", "--log-disable"):
            self.assertEqual(off.count(flag), 1)

    def test_scrubbed_environment_cannot_override_device_libraries_or_body_logs(self):
        bad = {name: "UNTRUSTED" for name in ("LD_LIBRARY_PATH", "LD_PRELOAD", "CUDA_VISIBLE_DEVICES", "CUDA_DEVICE_ORDER",
               "GGML_CUDA_DEVICES", "GGML_CUDA_ENABLE_UNIFIED_MEMORY", "GGML_BACKEND_PATH", "LLAMA_ARG_HOST",
               "LLAMA_LOG_FILE", "PYTHONPATH", "PYTHONHOME", "HTTPS_PROXY", "NVCC_PREPEND_FLAGS", "BASH_ENV")}
        env = native.child_environment(self.root, bad)
        self.assertEqual(env["CUDA_VISIBLE_DEVICES"], "3")
        self.assertEqual(env["CUDA_DEVICE_ORDER"], "PCI_BUS_ID")
        self.assertFalse(any(value == "UNTRUSTED" for value in env.values()))
        self.assertEqual(env["GGML_CUDA_DISABLE_GRAPHS"], "1")
        for key in ("LLAMA_CACHE", "CUDA_CACHE_PATH", "XDG_CACHE_HOME", "TMPDIR"):
            self.assertTrue(Path(env[key]).is_relative_to(self.root / "var/cache"))

    def test_strict_configuration_rejects_other_profile_missing_budget_and_truthy_modes(self):
        for delta in ({"profile": "rtx5090"}, {"estimated_peak_mib": 0}, {"estimated_peak_mib": True},
                      {"enable_reasoning": "false"}, {"peak_allowance_mib": 1}, {"max_model_len": 8192},
                      {"source_commit": "a" * 40}, {"model_sha256": "AUTO"}):
            with self.subTest(delta=delta), self.assertRaises(PreflightError):
                replace(self.config, **delta)

    def test_default_batch_pair_is_two_one_and_single_field_changes_are_rejected(self):
        self.assertEqual((self.config.batch_size, self.config.ubatch_size), (2, 1))
        serialized = asdict(self.config)
        self.assertEqual((serialized["batch_size"], serialized["ubatch_size"]), (2, 1))
        for field, bad_values in (
                ("batch_size", (0, 1, 3, True, False, 2.0, "2", None)),
                ("ubatch_size", (0, 2, 3, True, False, 1.0, "1", None))):
            for value in bad_values:
                with self.subTest(field=field, value=value), self.assertRaises(PreflightError) as error:
                    replace(self.config, **{field: value})
                self.assertEqual(error.exception.code, "INVALID_CONFIG")

    def test_cli_rejects_old_explicit_batch_one_before_guard_or_gpu(self):
        path = self.root / "launch-batch-one.json"
        values = asdict(self.config)
        values["batch_size"] = 1
        path.write_text(json.dumps({key: str(value) if isinstance(value, Path) else value
                                    for key, value in values.items()}))
        before = path.read_bytes()
        with patch.object(native, "ROOT", self.root), patch.object(native, "run_guard") as guard, redirect_stdout(StringIO()) as output:
            result = native.main(["--config", str(path)])
        self.assertEqual(result, 2)
        self.assertEqual(json.loads(output.getvalue()), {"state": "BLOCKED", "reason": "INVALID_CONFIG"})
        guard.assert_not_called()
        self.assertEqual(path.read_bytes(), before)

    def test_explicit_batch64_pair_binds_arguments_report_and_peak_budget(self):
        candidate = replace(self.config, batch_size=64, ubatch_size=64, estimated_peak_mib=28672)
        baseline = native.native_arguments(self.config, self.root)
        expected = list(baseline)
        expected[expected.index("--batch-size") + 1] = "64"
        expected[expected.index("--ubatch-size") + 1] = "64"
        self.assertEqual(native.native_arguments(candidate, self.root), expected)
        # Default flags and all other production arguments remain unchanged.
        self.assertEqual(native.native_arguments(self.config, self.root), baseline)
        report, queries, launches, signals = self.run_fake(config=candidate)
        self.assertEqual((report["batch_size"], report["ubatch_size"]), (64, 64))
        self.assertEqual(report["aggregate_increment_limit_mib"], 28672)
        self.assertEqual(report["required_free_floor_mib"], 7275)
        self.assertEqual(set(queries), {3})
        self.assertEqual(launches[0][0][-len(expected):], expected)
        self.assertEqual(len(signals), 2)

    def test_cli_batch_pair_and_peak_floor_reject_before_guard_or_gpu(self):
        path = self.root / "launch-prefill-candidate.json"
        for batch, ubatch, peak in ((64, 64, 28671), (32, 32, 28672), (64, 1, 28672),
                                   (2, 64, 28672), (True, 64, 28672), (64, 64.0, 28672)):
            values = asdict(self.config)
            values.update(batch_size=batch, ubatch_size=ubatch, estimated_peak_mib=peak)
            path.write_text(json.dumps(values, default=str))
            with self.subTest(batch=batch, ubatch=ubatch, peak=peak), \
                    patch.object(native, "ROOT", self.root), patch.object(native, "run_guard") as guard, \
                    redirect_stdout(StringIO()) as output:
                status = native.main(["--config", str(path)])
            self.assertEqual(status, 2)
            self.assertEqual(json.loads(output.getvalue())["reason"], "INVALID_CONFIG")
            guard.assert_not_called()

    def test_preflight_mask_budget_lock_and_output_fail_before_query_or_child(self):
        report, queries, launches, _ = self.run_fake(env={"CUDA_VISIBLE_DEVICES": "1"})
        self.assertEqual((report["reason"], queries, launches), ("PREFLIGHT_BLOCKED", [], []))
        self.assertEqual(report["preflight"]["reason_codes"], ["CUDA_MASK_MISMATCH"])
        report, _, launches, _ = self.run_fake(config=replace(self.config, estimated_peak_mib=30000))
        self.assertEqual(report["reason"], "PREFLIGHT_BLOCKED")
        self.assertEqual(launches, [])
        lock = acquire_project_lock(self.root)
        try:
            report, queries, launches, _ = self.run_fake()
            self.assertEqual((report["reason"], queries, launches), ("OWN_MODEL_ALREADY_RUNNING", [], []))
        finally:
            os.close(lock)
        for key in ("log_file", "report_file"):
            report, queries, launches, _ = self.run_fake(config=replace(self.config, **{key: self.model}))
            self.assertEqual((report["reason"], queries, launches), ("INVALID_PATH", [], []))

    def test_bad_pins_and_tampered_model_library_or_header_never_query_or_spawn(self):
        for key in ("binary_sha256", "build_report_sha256", "source_report_sha256", "model_sha256", "model_header_report_sha256"):
            with self.subTest(key=key):
                report, queries, launches, _ = self.run_fake(config=replace(self.config, **{key: "0" * 64}))
                self.assertIn(report["reason"], ("NATIVE_HASH_MISMATCH", "INVALID_NATIVE_PROOF"))
                self.assertEqual((queries, launches), ([], []))
        for path in (self.model, self.libs[0], self.binary):
            original = path.read_bytes()
            path.write_bytes(original + b"tampered")
            try:
                report, queries, launches, _ = self.run_fake()
                self.assertEqual((report["reason"], queries, launches), ("NATIVE_HASH_MISMATCH", [], []))
            finally:
                path.write_bytes(original)

    def test_missing_source_flags_or_library_closure_or_soname_changes_fail(self):
        def check_config(config):
            report, queries, launches, _ = self.run_fake(config=config)
            self.assertIn(report["reason"], ("INVALID_NATIVE_PROOF", "INVALID_PATH"))
            self.assertEqual((queries, launches), ([], []))
        for mutate in (lambda b: b.pop("original_compile_report_sha256"),
                       lambda b: b.update(runtime_dependencies=[]),
                       lambda b: b["settings"].update(LLAMA_SUBPROCESS="ON"),
                       lambda b: b["runtime_dependency_symlinks"][0].update(target="../libllama.so.0")):
            build = json.loads(json.dumps(self.build))
            mutate(build)
            self.proof("build", build)
            check_config(replace(self.config, build_report_sha256=self.sha(self.build_path)))
        self.proof("build", self.build)
        source = dict(self.source, no_gpu_calls=False)
        self.proof("source", source)
        check_config(replace(self.config, source_report_sha256=self.sha(self.source_path)))
        self.proof("source", self.source)
        self.write("var/runtime-build/pin/bin/libunlisted.so", b"unlisted")
        check_config(self.config)

    def test_watchdog_floor_peak_and_query_failures_clean_only_own_child(self):
        for row, reason in (("40960, 7274, 33064, 70", "FREE_MARGIN_BREACHED"),
                            ("40960, 10772, 29566, 70", "PEAK_BUDGET_EXCEEDED"),
                            ("N/A", "INVALID_READING"),
                            (PreflightError("GPU_QUERY_FAILED", "safe"), "GPU_QUERY_FAILED")):
            with self.subTest(reason=reason):
                report, _, launches, signals = self.run_fake(rows=[row])
                self.assertEqual(report["reason"], reason)
                self.assertEqual(report["state"], "STOPPED")
                self.assertEqual(len(launches), 1)
                self.assertEqual(signals, [(FakeChild.pid, signal.SIGTERM), (FakeChild.pid, signal.SIGKILL)])

    def test_bootstrap_mismatch_unknown_body_and_spawn_failure_are_fail_closed(self):
        cases = [({"event": "BOOTSTRAP_FAILED", "pid": FakeChild.pid, "code": "GPU_IDENTITY_MISMATCH"}, "GPU_IDENTITY_MISMATCH"),
                 ({"event": "GPU_IDENTITY_VERIFIED", "pid": FakeChild.pid + 1}, "NATIVE_BOOTSTRAP_INVALID"),
                 ({"event": "BOOTSTRAP_FAILED", "pid": FakeChild.pid, "code": "raw body must not enter report"}, "NATIVE_BOOTSTRAP_INVALID")]
        for value, reason in cases:
            with self.subTest(reason=reason):
                report, _, _, signals = self.run_fake(status=value)
                self.assertEqual(report["reason"], reason)
                self.assertFalse(report["native_identity_verified"])
                self.assertNotIn("raw body", json.dumps(report))
                self.assertEqual(len(signals), 2)
        report, _, launches, signals = self.run_fake(spawn_error=True)
        self.assertEqual(report["reason"], "LAUNCH_OR_MONITOR_IO_FAILED")
        self.assertEqual((launches, signals), ([], []))

    def test_missing_identity_is_bounded_and_releases_shared_project_lock(self):
        report, _, launches, signals = self.run_fake(status=False, config=replace(self.config, max_seconds=20))
        self.assertEqual(report["reason"], "NATIVE_BOOTSTRAP_TIMEOUT")
        self.assertEqual(report["elapsed_seconds"], 15)
        self.assertFalse(report["native_identity_verified"])
        self.assertEqual(len(launches), 1)
        self.assertEqual(len(signals), 2)
        lock = acquire_project_lock(self.root)
        os.close(lock)

    def test_output_cannot_overwrite_or_append_to_any_of_the_three_input_proofs(self):
        for field in ("build_report", "source_report", "model_header_report"):
            original = getattr(self.config, field)
            before = original.read_bytes()
            with self.subTest(field=field, output="report"):
                report, queries, launches, _ = self.run_fake(config=replace(self.config, report_file=original))
                self.assertEqual((report["reason"], queries, launches), ("INVALID_PATH", [], []))
                self.assertEqual(original.read_bytes(), before)
            # A proof may legitimately be stored under logs, but appending runtime output to it is forbidden.
            relocated = self.write("var/logs/" + field + ".json", before)
            with self.subTest(field=field, output="log"):
                report, queries, launches, _ = self.run_fake(config=replace(self.config, **{field: relocated, "log_file": relocated}))
                self.assertEqual((report["reason"], queries, launches), ("INVALID_PATH", [], []))
                self.assertEqual(relocated.read_bytes(), before)

    def test_binary_dependency_and_soname_inputs_remain_unchanged_at_report_destination(self):
        newbin = self.root / "var/reports/bin"
        binary = self.write(str(newbin.relative_to(self.root) / "llama-server"), self.binary.read_bytes())
        binary.chmod(0o755)
        for library in self.libs:
            self.write(str((newbin / library.name).relative_to(self.root)), library.read_bytes())
        alias = newbin / "libllama.so"
        alias.symlink_to("libllama.so.0")
        build = json.loads(json.dumps(self.build))
        for entry in build["runtime_dependencies"]:
            entry["path"] = str((newbin / Path(entry["path"]).name).relative_to(self.root))
        for entry in build["runtime_dependency_symlinks"]:
            entry["path"] = str(alias.relative_to(self.root))
            entry["real_path"] = str(alias.resolve().relative_to(self.root))
        self.proof("build", build)
        config = replace(self.config, binary_path=binary, build_report_sha256=self.sha(self.build_path))
        for path in (binary, newbin / "libllama.so.0", newbin / "libggml-cuda.so.0", alias):
            before = path.read_bytes()
            with self.subTest(input=path.name):
                report, queries, launches, _ = self.run_fake(config=replace(config, report_file=path))
                self.assertEqual((report["reason"], queries, launches), ("INVALID_PATH", [], []))
                self.assertEqual(path.read_bytes(), before)
        self.assertTrue(alias.is_symlink())

    def test_template_override_requires_a_complete_explicit_pair(self):
        path = Path("var/templates/public.jinja")
        for change in ({"chat_template_path": path}, {"chat_template_sha256": "a" * 64},
                       {"chat_template_path": str(path), "chat_template_sha256": "a" * 64},
                       {"chat_template_path": path, "chat_template_sha256": "A" * 64},
                       {"chat_template_path": path, "chat_template_sha256": True}):
            with self.subTest(change=change), self.assertRaises(PreflightError) as caught:
                replace(self.config, **change)
            self.assertEqual(caught.exception.code, "INVALID_CONFIG")

    def test_template_override_is_pinned_in_argv_and_report_without_logging_body(self):
        template = self.write("var/templates/public.jinja", b"PUBLIC_TEMPLATE_SENTINEL {{ messages }}")
        config = replace(self.config, chat_template_path=template, chat_template_sha256=self.sha(template))
        plain = native.native_arguments(self.config, self.root)
        self.assertNotIn("--chat-template-file", plain)
        self.assertEqual(native.native_arguments(config, self.root), plain + ["--chat-template-file", str(template)])
        report, queries, launches, _ = self.run_fake(config=config)
        self.assertEqual(report["reason"], "TIME_LIMIT")
        self.assertTrue(queries)
        self.assertEqual(launches[0][0][-2:], ["--chat-template-file", str(template)])
        self.assertEqual(report["native_artifacts"]["chat_template_override"],
                         {"path": str(template.relative_to(self.root)), "sha256": self.sha(template)})
        self.assertNotIn("PUBLIC_TEMPLATE_SENTINEL", json.dumps(report))

    def test_invalid_or_aliased_template_never_queries_or_spawns(self):
        template = self.write("var/templates/public.jinja", b"{{ messages }}")
        original = template.read_bytes()
        config = replace(self.config, chat_template_path=template, chat_template_sha256=self.sha(template))
        for value, expected in ((b"changed", "NATIVE_HASH_MISMATCH"), (b"", "INVALID_NATIVE_PROOF"),
                                (b"x" * 65537, "INVALID_NATIVE_PROOF"), (b"\xff", "INVALID_NATIVE_PROOF"),
                                (b"nul\0text", "INVALID_NATIVE_PROOF")):
            template.write_bytes(value)
            candidate = config if expected == "NATIVE_HASH_MISMATCH" else replace(config, chat_template_sha256=self.sha(template))
            with self.subTest(expected=expected, size=len(value)):
                report, queries, launches, _ = self.run_fake(config=candidate)
                self.assertEqual((report["reason"], queries, launches), (expected, [], []))
        template.write_bytes(original)
        alias = template.with_name("alias.jinja")
        alias.symlink_to(template.name)
        report, queries, launches, _ = self.run_fake(config=replace(config, chat_template_path=alias))
        self.assertEqual((report["reason"], queries, launches), ("INVALID_PATH", [], []))
        alias.unlink()
        os.link(template, alias)
        report, queries, launches, _ = self.run_fake(config=config)
        self.assertEqual((report["reason"], queries, launches), ("INVALID_PATH", [], []))

    def test_template_cannot_be_a_runtime_output_and_is_rechecked_before_spawn(self):
        template = self.write("var/reports/public.jinja", b"{{ messages }}")
        before = template.read_bytes()
        config = replace(self.config, chat_template_path=template, chat_template_sha256=self.sha(template))
        for key in ("log_file", "report_file"):
            with self.subTest(output=key):
                report, queries, launches, _ = self.run_fake(config=replace(config, **{key: template}))
                self.assertEqual((report["reason"], queries, launches), ("INVALID_PATH", [], []))
                self.assertEqual(template.read_bytes(), before)
        runtime = native._NativeRuntime()
        runtime.validate(config, self.root, self.model)
        template.write_bytes(b"changed after validation")
        with self.assertRaises(PreflightError) as caught:
            native.native_arguments(config, self.root)
        self.assertEqual(caught.exception.code, "NATIVE_HASH_MISMATCH")

    def test_cli_parses_optional_template_path_and_keeps_absence_as_none(self):
        template = self.write("var/templates/public.jinja", b"{{ messages }}")
        for candidate in (self.config, replace(self.config, chat_template_path=template, chat_template_sha256=self.sha(template))):
            values = asdict(candidate)
            path = self.proof("launch", {key: str(value) if isinstance(value, Path) else value for key, value in values.items()})
            result = {"reason": "TIME_LIMIT", "native_identity_verified": True, "shutdown": {"child_reaped": True}}
            with patch.object(native, "ROOT", self.root), patch.object(native, "run_guard", return_value=result) as guard, redirect_stdout(StringIO()):
                self.assertEqual(native.main(["--config", str(path)]), 0)
            actual = guard.call_args.args[0]
            self.assertEqual(actual.chat_template_path, candidate.chat_template_path)
            self.assertEqual(actual.chat_template_sha256, candidate.chat_template_sha256)

    def test_cli_configuration_itself_cannot_be_a_live_report_file(self):
        path = self.root / "var/reports/launch-config.json"
        values = asdict(replace(self.config, report_file=path))
        before = json.dumps({key: str(value) if isinstance(value, Path) else value for key, value in values.items()}).encode()
        path.write_bytes(before)
        with patch.object(native, "ROOT", self.root), patch.object(native, "run_guard") as guard, redirect_stdout(StringIO()) as output:
            result = native.main(["--config", str(path)])
        self.assertEqual(result, 2)
        self.assertEqual(json.loads(output.getvalue())["reason"], "INVALID_PATH")
        guard.assert_not_called()
        self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
