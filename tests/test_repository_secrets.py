"""Synthetic credentials only; every Git mutation stays in project var test repos."""

from contextlib import redirect_stderr, redirect_stdout
from io import BytesIO, StringIO
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import check_repository_secrets as scanner


PROJECT = Path(__file__).resolve().parents[1]


def synthetic_credentials():
    # Split prefixes deliberately: the tracked test source contains no credential.
    return {
        "GOOGLE_API_KEY": "AI" + "za" + "A" * 35,
        "HUGGING_FACE_TOKEN": "h" + "f_" + "B" * 25,
        "GITHUB_TOKEN": "gh" + "p_" + "C" * 36,
        "AWS_ACCESS_KEY_ID": "AK" + "IA" + "D" * 16,
        "PRIVATE_KEY": "-----BE" + "GIN OPENSSH PRIVATE KEY-----",
        "SLACK_TOKEN": "xo" + "xb-" + "1234567890-" + "E" * 24,
        "STRIPE_SECRET_KEY": "sk" + "_live_" + "F" * 24,
        "OPENAI_API_KEY": "sk" + "-proj-" + "G" * 80,
    }


class RepositorySecretsTests(unittest.TestCase):
    def setUp(self):
        temporary_parent = PROJECT / "var" / "repository-secret-tests"
        temporary_parent.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=temporary_parent)
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.repository = self.base / "repository"
        self.repository.mkdir()
        # An inherited GIT_DIR/INDEX_FILE must never point these tests at the real repo.
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith("GIT_")}
        environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                           GIT_CEILING_DIRECTORIES=str(temporary_parent))
        self.environment_patch = patch.dict(os.environ, environment, clear=True)
        self.environment_patch.start()
        self.addCleanup(self.environment_patch.stop)
        self.git("-c", "init.templateDir=", "init", "--quiet")

    def git(self, *arguments, data=None):
        result = subprocess.run(
            ["git", "-C", str(self.repository), *arguments], input=data,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
        )
        if result.returncode:
            self.fail("Temporary-repository Git operation failed; details suppressed")
        return result.stdout

    def write(self, name, content=b"safe\n", *, stage=True):
        path = self.repository / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode() if isinstance(content, str) else content)
        if stage:
            self.git("add", "--", name)
        return path

    def commit(self):
        self.git("-c", "user.name=Synthetic Test", "-c", "user.email=test@example.invalid",
                 "-c", "commit.gpgsign=false", "commit", "--quiet", "--no-verify", "-m", "fixture")

    def call(self, *options, repository=None):
        output, errors = StringIO(), StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            code = scanner.main(["--repository", str(repository or self.repository), *options])
        self.assertEqual(errors.getvalue(), "")
        return code, json.loads(output.getvalue()), output.getvalue()

    def assert_redacted(self, output, values):
        # assertNotIn would itself print the secret on failure, so use a fixed message.
        if any(value in output for value in values):
            self.fail("Scanner output exposed a synthetic credential")

    def test_all_secret_rules_count_without_printing_values_or_context(self):
        credentials = synthetic_credentials()
        content = "private surrounding text\n" + "\n".join(credentials.values())
        content += "\n" + credentials["GOOGLE_API_KEY"]
        self.write("settings.txt", content)
        code, report, output = self.call()
        self.assertEqual(code, 1)
        counts = {item["rule_id"]: item["count"] for item in report["findings"]}
        self.assertEqual(counts, {rule: 2 if rule == "GOOGLE_API_KEY" else 1
                                  for rule in credentials})
        self.assertEqual(report["counts"]["findings"], 9)
        self.assert_redacted(output, [*credentials.values(), "private surrounding text"])
        for item in report["findings"]:
            self.assertEqual(set(item), {"path", "rule_id", "count"})
            self.assertEqual(item["path"], "settings.txt")

    def test_additional_provider_variants_are_detected(self):
        values = ["github" + "_pat_" + "A" * 70,
                  "gh" + "s_" + "B" * 36,
                  "AS" + "IA" + "C" * 16,
                  "xa" + "pp-" + "1-" + "D" * 24,
                  "rk" + "_test_" + "E" * 24,
                  "sk" + "-svcacct-" + "F" * 40,
                  "sk" + "-" + "G" * 48,
                  "-----BE" + "GIN PRIVATE KEY-----"]
        self.write("variants.txt", "\n".join(values))
        code, report, output = self.call("--staged")
        self.assertEqual(code, 1)
        self.assertEqual(report["counts"]["findings"], len(values))
        self.assert_redacted(output, values)

    def test_staged_scans_full_index_even_unchanged_and_worktree_redacted(self):
        value = synthetic_credentials()["HUGGING_FACE_TOKEN"]
        tracked = self.write("unchanged.txt", value)
        self.commit()
        tracked.write_text("redacted working tree\n")
        self.write("unrelated.txt")
        before = (self.repository / ".git/index").read_bytes()
        self.assertEqual(self.call()[0], 0)
        code, report, output = self.call("--staged")
        self.assertEqual(code, 1)
        self.assertEqual(report["findings"][0]["path"], "unchanged.txt")
        self.assertEqual(report["counts"]["scanned_files"], 2)
        self.assertEqual((self.repository / ".git/index").read_bytes(), before)
        self.assertEqual(tracked.read_text(), "redacted working tree\n")
        self.assert_redacted(output, [value])

    def test_worktree_change_is_not_confused_with_staged_blob(self):
        tracked = self.write("application.conf")
        tracked.write_text(synthetic_credentials()["GOOGLE_API_KEY"])
        self.assertEqual(self.call()[0], 1)
        self.assertEqual(self.call("--staged")[0], 0)

    def test_ignored_and_untracked_files_are_not_opened_but_tracked_ignored_is_scanned(self):
        value = synthetic_credentials()["OPENAI_API_KEY"]
        self.write("already-tracked.txt", value)
        self.write(".gitignore", "ignored.txt\nalready-tracked.txt\n")
        self.write("ignored.txt", value, stage=False)
        self.write("untracked.txt", value, stage=False)
        for options in ((), ("--staged",)):
            with self.subTest(options=options):
                code, report, _ = self.call(*options)
                self.assertEqual(code, 1)
                self.assertEqual(report["counts"]["tracked_files"], 2)
                self.assertEqual([item["path"] for item in report["findings"]], ["already-tracked.txt"])

    def test_deletions_do_not_read_missing_worktree_files(self):
        self.write("deleted.txt", synthetic_credentials()["STRIPE_SECRET_KEY"])
        self.commit()
        (self.repository / "deleted.txt").unlink()
        code, report, _ = self.call()
        self.assertEqual(code, 0)
        self.assertEqual(report["counts"]["missing_worktree_files"], 1)
        self.assertEqual(self.call("--staged")[0], 1)
        self.git("add", "-u")
        self.assertEqual(self.call("--staged")[0], 0)

    def test_unusual_filenames_and_subdirectory_invocation(self):
        name = "nested/- space\tline\nfile.txt"
        self.write(name, synthetic_credentials()["SLACK_TOKEN"])
        for options in ((), ("--staged",)):
            with self.subTest(options=options):
                code, report, output = self.call(*options, repository=self.repository / "nested")
                self.assertEqual(code, 1)
                self.assertEqual(report["findings"][0]["path"], name)
                self.assertEqual(output.count("\n"), 1)

    def test_credential_in_filename_is_redacted_too(self):
        value = synthetic_credentials()["GOOGLE_API_KEY"]
        self.write(value + ".txt", value)
        code, report, output = self.call("--staged")
        self.assertEqual(code, 1)
        self.assertEqual(report["findings"][0]["path"], "[REDACTED:GOOGLE_API_KEY].txt")
        self.assert_redacted(output, [value])

    def test_symlinks_are_scanned_as_text_without_following_targets(self):
        outside = self.base / "outside.txt"
        outside.write_text(synthetic_credentials()["GITHUB_TOKEN"])
        (self.repository / "link.txt").symlink_to(outside)
        (self.repository / "dangling.txt").symlink_to(self.base / "missing")
        self.git("add", "--", "link.txt", "dangling.txt")
        for options in ((), ("--staged",)):
            with self.subTest(options=options):
                code, report, _ = self.call(*options)
                self.assertEqual(code, 0)
                self.assertEqual(report["counts"]["scanned_files"], 2)

    def test_symlinked_parent_is_rejected_without_reading_outside(self):
        self.write("directory/file.txt")
        (self.repository / "directory/file.txt").unlink()
        (self.repository / "directory").rmdir()
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "file.txt").write_text(synthetic_credentials()["HUGGING_FACE_TOKEN"])
        (self.repository / "directory").symlink_to(outside, target_is_directory=True)
        code, report, _ = self.call()
        self.assertEqual(code, 2)
        self.assertEqual(report["errors"][0]["rule_id"], "SCAN_UNSAFE_PARENT")
        self.assertEqual(report["findings"], [])
        self.assertEqual(self.call("--staged")[0], 0)

    def test_raw_evidence_rejected_but_apache_and_application_html_retained(self):
        allowed = ["LICENSE", "legacy/application/index.html", "frontend/app.js"]
        for name in allowed:
            self.write(name, "Apache License, Version 2.0\nsynthetic application content\n")
        self.assertEqual(self.call()[0], 0)
        forbidden = ["evaluations/results/model/page.html", "evaluations/results/page.HTM",
                     "evaluations/results/model/app.js", "docs/provenance/app.mjs",
                     "candidate-provenance/raw/app.cjs"]
        for name in forbidden:
            self.write(name, "synthetic external evidence placeholder\n")
        code, report, _ = self.call("--staged")
        self.assertEqual(code, 1)
        self.assertEqual({item["path"] for item in report["findings"]}, set(forbidden))
        self.assertEqual({item["rule_id"] for item in report["findings"]}, {"RAW_EXTERNAL_EVIDENCE"})
        # Allowed application HTML remains subject to credential scanning.
        self.write("legacy/application/index.html", synthetic_credentials()["GOOGLE_API_KEY"])
        self.assertIn("GOOGLE_API_KEY", {item["rule_id"] for item in self.call()[1]["findings"]})

    def test_non_repository_and_invalid_argument_fail_without_external_text(self):
        self.assertEqual(self.call(repository=self.base)[0], 2)
        value = synthetic_credentials()["OPENAI_API_KEY"]
        code, report, output = self.call("--" + value)
        self.assertEqual(code, 2)
        self.assertEqual(report["errors"][0]["rule_id"], "SCAN_ARGUMENT_ERROR")
        self.assert_redacted(output, [value])

    def test_unmerged_index_is_an_error_in_both_modes(self):
        oid = self.git("hash-object", "-w", "--stdin", data=b"safe\n").strip()
        entries = b"100644 " + oid + b" 1\tconflict.txt\n100644 " + oid + b" 2\tconflict.txt\n"
        self.git("update-index", "--index-info", data=entries)
        for options in ((), ("--staged",)):
            with self.subTest(options=options):
                code, report, _ = self.call(*options)
                self.assertEqual(code, 2)
                self.assertEqual(report["errors"][0]["rule_id"], "SCAN_UNMERGED_INDEX")

    def test_oversized_index_stops_before_body_or_later_objects_are_read(self):
        self.write("a-large.txt", b"a" * 128)
        self.write("b-credential.txt", synthetic_credentials()["HUGGING_FACE_TOKEN"])
        with patch.object(scanner, "MAX_FILE_BYTES", 64):
            oid = "a" * 40
            header = (oid + " blob 128\n").encode()
            process = SimpleNamespace(stdin=BytesIO(), stdout=BytesIO(header + b"a" * 128 + b"\n"))
            with self.assertRaises(scanner.FatalIndexError):
                scanner.read_blob(process, oid)
            self.assertEqual(process.stdout.tell(), len(header))
            code, report, output = self.call("--staged")
            self.assertEqual(code, 2)
            self.assertEqual(report["errors"][0]["rule_id"], "SCAN_FILE_TOO_LARGE")
            self.assertEqual(report["errors"][0]["path"], "a-large.txt")
            self.assertEqual(report["findings"], [])
            self.assertEqual(report["counts"]["scanned_files"], 0)
            self.assert_redacted(output, synthetic_credentials().values())
            code, report, _ = self.call()
            self.assertEqual(code, 2)
            self.assertEqual(report["errors"][0]["rule_id"], "SCAN_FILE_TOO_LARGE")
            self.assertEqual(report["findings"][0]["rule_id"], "HUGGING_FACE_TOKEN")


if __name__ == "__main__":
    unittest.main()
