"""Small local files only: never execute curl or download model weights."""

from contextlib import redirect_stdout
from hashlib import sha256
from io import StringIO
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from scripts import download_model


class DownloadModelTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "project"
        self.root.mkdir()
        self.outside = self.base / "outside"
        self.outside.mkdir()
        self.content = b"synthetic weight bytes; not a model"
        self.manifest = {"model_id": "Example/TestModel", "revision": "a" * 40,
                         "files": [{"name": "model.safetensors", "bytes": len(self.content),
                                    "sha256": sha256(self.content).hexdigest()}]}
        self.manifest_path = self.root / "manifest.json"
        self.manifest_path.write_text(json.dumps(self.manifest))
        self.destination = self.root / "var/models/Example--TestModel" / ("a" * 40)
        self.metadata = self.destination / "neurobuild-manifest.json"
        self.target = self.destination / "model.safetensors"
        self.partial = self.destination / "model.safetensors.part"
        self.root_patch = patch.object(download_model, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.network_patch = patch.object(download_model.subprocess, "run",
                                         side_effect=AssertionError("Tests must never invoke curl"))
        self.network = self.network_patch.start()
        self.addCleanup(self.network_patch.stop)
        self.disk_patch = patch.object(download_model.shutil, "disk_usage",
                                      return_value=SimpleNamespace(free=2 * download_model.RESERVE))
        self.disk = self.disk_patch.start()
        self.addCleanup(self.disk_patch.stop)

    def call(self):
        with redirect_stdout(StringIO()):
            download_model.download(self.manifest_path)

    def existing_weight(self):
        self.destination.mkdir(parents=True)
        self.target.write_bytes(self.content)

    def test_storage_symlink_rejects_before_creating_any_outside_directory(self):
        (self.root / "var").mkdir()
        (self.root / "var/models").symlink_to(self.outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "within the project"):
            self.call()
        self.assertEqual(list(self.outside.iterdir()), [])
        self.network.assert_not_called()
        self.disk.assert_not_called()

    def test_model_directory_symlink_rejects_before_external_revision_mkdir(self):
        (self.root / "var/models").mkdir(parents=True)
        (self.root / "var/models/Example--TestModel").symlink_to(self.outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "within the project"):
            self.call()
        self.assertFalse((self.outside / ("a" * 40)).exists())
        self.assertEqual(list(self.outside.iterdir()), [])
        self.network.assert_not_called()

    def test_metadata_symlink_is_rejected_without_reading_or_changing_external_file(self):
        self.existing_weight()
        sentinel = self.outside / "sentinel.json"
        sentinel.write_bytes(b"do not overwrite or parse")
        before = sentinel.stat()
        self.metadata.symlink_to(sentinel)
        with self.assertRaisesRegex(ValueError, "regular local file"):
            self.call()
        self.assertTrue(self.metadata.is_symlink())
        self.assertEqual(sentinel.read_bytes(), b"do not overwrite or parse")
        self.assertEqual(sentinel.stat().st_mtime_ns, before.st_mtime_ns)
        self.network.assert_not_called()

    def test_dangling_metadata_symlink_never_creates_external_target(self):
        self.existing_weight()
        sentinel = self.outside / "missing.json"
        self.metadata.symlink_to(sentinel)
        with self.assertRaises(ValueError):
            self.call()
        self.assertFalse(sentinel.exists())
        self.assertTrue(self.metadata.is_symlink())
        self.network.assert_not_called()

    def test_existing_different_metadata_is_preserved_without_http(self):
        self.existing_weight()
        different = dict(self.manifest, revision="b" * 40)
        original = json.dumps(different).encode()
        self.metadata.write_bytes(original)
        with self.assertRaisesRegex(ValueError, "differs"):
            self.call()
        self.assertEqual(self.metadata.read_bytes(), original)
        self.assertEqual(self.target.read_bytes(), self.content)
        self.network.assert_not_called()

    def test_reserved_metadata_and_partial_names_fail_before_destination_creation(self):
        for name in ("neurobuild-manifest.json", "model.safetensors.part", "config.part"):
            with self.subTest(name=name):
                self.manifest["files"][0]["name"] = name
                self.manifest_path.write_text(json.dumps(self.manifest))
                with self.assertRaisesRegex(ValueError, "filename"):
                    self.call()
                self.assertFalse(self.destination.exists())
        self.network.assert_not_called()

    def test_existing_valid_weights_publish_manifest_and_second_call_is_idempotent(self):
        self.existing_weight()
        before_weight = self.target.stat()
        self.call()
        self.assertEqual(json.loads(self.metadata.read_text()), self.manifest)
        first_metadata = self.metadata.stat()
        first_bytes = self.metadata.read_bytes()
        self.call()
        self.assertEqual(self.metadata.stat().st_ino, first_metadata.st_ino)
        self.assertEqual(self.metadata.stat().st_mtime_ns, first_metadata.st_mtime_ns)
        self.assertEqual(self.metadata.read_bytes(), first_bytes)
        self.assertEqual(self.target.stat().st_ino, before_weight.st_ino)
        self.assertEqual(self.target.stat().st_mtime_ns, before_weight.st_mtime_ns)
        self.assertEqual(list(self.destination.glob(".manifest-*")), [])
        self.network.assert_not_called()

    def test_nonregular_metadata_target_and_partial_are_rejected(self):
        self.destination.mkdir(parents=True)
        for path in (self.metadata, self.target, self.partial):
            with self.subTest(path=path.name):
                path.mkdir()
                with self.assertRaisesRegex(ValueError, "regular local file"):
                    self.call()
                self.assertTrue(path.is_dir())
                path.rmdir()  # This test's own empty fixture only.
        self.network.assert_not_called()

    def test_existing_target_and_partial_symlinks_do_not_read_external_bytes(self):
        self.destination.mkdir(parents=True)
        sentinel = self.outside / "sentinel.bin"
        sentinel.write_bytes(self.content)
        with patch.object(download_model, "digest", side_effect=AssertionError("must not follow symlink")):
            for path in (self.target, self.partial):
                with self.subTest(path=path.name):
                    path.symlink_to(sentinel)
                    with self.assertRaisesRegex(ValueError, "regular local file"):
                        self.call()
                    path.unlink()  # This test's own symlink only.
        self.assertEqual(sentinel.read_bytes(), self.content)
        self.network.assert_not_called()

    def test_corrupt_existing_weight_is_not_overwritten_or_marked_verified(self):
        self.existing_weight()
        self.target.write_bytes(b"x" * len(self.content))  # Same size, wrong SHA256.
        with self.assertRaisesRegex(ValueError, "differs"):
            self.call()
        self.assertEqual(self.target.read_bytes(), b"x" * len(self.content))
        self.assertFalse(self.metadata.exists())
        self.network.assert_not_called()

    def test_competing_manifest_publication_never_overwrites_file_or_leaves_staging(self):
        self.existing_weight()
        real_link = os.link
        competing = b"competing manifest"

        def race(source, destination):
            Path(destination).write_bytes(competing)
            real_link(source, destination)

        with patch.object(download_model.os, "link", side_effect=race):
            with self.assertRaises(FileExistsError):
                self.call()
        self.assertEqual(self.metadata.read_bytes(), competing)
        self.assertEqual(list(self.destination.glob(".manifest-*")), [])
        self.network.assert_not_called()

    def test_competing_metadata_symlink_never_writes_through_external_target(self):
        self.existing_weight()
        real_link = os.link
        sentinel = self.outside / "never-created.json"

        def race(source, destination):
            Path(destination).symlink_to(sentinel)
            real_link(source, destination)

        with patch.object(download_model.os, "link", side_effect=race):
            with self.assertRaises(FileExistsError):
                self.call()
        self.assertTrue(self.metadata.is_symlink())
        self.assertFalse(sentinel.exists())
        self.assertEqual(list(self.destination.glob(".manifest-*")), [])
        self.network.assert_not_called()

    def test_insufficient_disk_never_starts_download_or_publishes_metadata(self):
        self.disk.return_value = SimpleNamespace(free=download_model.RESERVE)
        with self.assertRaisesRegex(RuntimeError, "Insufficient disk"):
            self.call()
        self.assertFalse(self.metadata.exists())
        self.assertFalse(self.target.exists())
        self.network.assert_not_called()

    def test_completed_partial_publishes_without_overwrite_and_retains_resume_arguments(self):
        self.destination.mkdir(parents=True)
        self.partial.write_bytes(self.content[:5])

        def transfer(command, **kwargs):
            self.assertIn('--continue-at', command)
            self.assertEqual(command[command.index('--continue-at') + 1], '-')
            self.assertEqual(command[command.index('--output') + 1], str(self.partial))
            self.partial.write_bytes(self.content)

        self.network.side_effect = transfer
        self.call()
        self.assertEqual(self.target.read_bytes(), self.content)
        self.assertEqual(self.target.stat().st_nlink, 1)
        self.assertFalse(self.partial.exists())
        self.assertEqual(json.loads(self.metadata.read_text()), self.manifest)

    def test_target_created_after_download_never_gets_replaced_and_partial_survives(self):
        competing = b'new independent target'

        def transfer(*args, **kwargs):
            self.partial.write_bytes(self.content)
            self.target.write_bytes(competing)

        self.network.side_effect = transfer
        with self.assertRaises(FileExistsError):
            self.call()
        self.assertEqual(self.target.read_bytes(), competing)
        self.assertEqual(self.partial.read_bytes(), self.content)
        self.assertFalse(self.metadata.exists())

    def test_target_symlink_created_after_download_is_not_followed_or_replaced(self):
        sentinel = self.outside / 'weight-sentinel'

        def transfer(*args, **kwargs):
            self.partial.write_bytes(self.content)
            self.target.symlink_to(sentinel)

        self.network.side_effect = transfer
        with self.assertRaises(FileExistsError):
            self.call()
        self.assertTrue(self.target.is_symlink())
        self.assertFalse(sentinel.exists())
        self.assertEqual(self.partial.read_bytes(), self.content)
        self.assertFalse(self.metadata.exists())


if __name__ == "__main__":
    unittest.main()
