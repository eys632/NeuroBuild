"""Filesystem acceptance tests: immutable publication, integrity and failures."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
import os
from pathlib import Path
import stat
import tempfile
from threading import Barrier
import unittest
from unittest.mock import patch
from uuid import uuid4

from neurobuild.domain.contracts import ArtifactRef
from neurobuild.domain.errors import DomainError
from neurobuild.infrastructure.artifacts import LocalArtifactStore


class LocalArtifactStoreTests(unittest.TestCase):
    def setUp(self):
        temporary_root = Path(__file__).resolve().parents[1] / "var"
        temporary_root.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="artifact-test-", dir=temporary_root)
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.store = LocalArtifactStore(self.directory / "store")

    def assert_rejected(self, code, operation):
        with self.assertRaises(DomainError) as caught:
            operation()
        self.assertEqual(caught.exception.code, code)

    def test_snapshot_roundtrip_hash_size_and_read_only_path(self):
        content = b"ISO-10303-21;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n"
        ref = self.store.put_bytes(content)
        self.assertEqual(ref.sha256, sha256(content).hexdigest())
        self.assertEqual(ref.size_bytes, len(content))
        self.assertEqual(ref.storage_key, f"objects/{ref.artifact_id}.ifc")
        self.assertEqual(self.store.read_bytes(ref), content)
        self.assertIsNone(self.store.verify(ref))
        self.assertEqual(self.store.path_for(ref), self.store.root / ref.storage_key)
        self.assertEqual(self.store.path_for(ref).stat().st_mode & 0o222, 0)
        self.assertEqual(list((self.store.root / ".staging").iterdir()), [])

    def test_file_import_copies_large_source_without_changing_it(self):
        source = self.directory / "original.ifc"
        content = bytes(range(256)) * 9000
        source.write_bytes(content)
        before = source.stat()
        ref = self.store.put_file(source)
        self.assertEqual(source.read_bytes(), content)
        self.assertEqual(self.store.read_bytes(ref), content)
        self.assertEqual(source.stat().st_ino, before.st_ino)
        self.assertEqual(source.stat().st_mtime_ns, before.st_mtime_ns)
        self.assertNotEqual(self.store.path_for(ref).stat().st_ino, before.st_ino)

    def test_same_identity_never_overwrites_even_with_equal_content(self):
        ref = self.store.put_bytes(b"original")
        for content in (b"original", b"different"):
            with self.subTest(content=content):
                self.assert_rejected("ARTIFACT_EXISTS", lambda: self.store.put_bytes(content, ref.artifact_id))
                self.assertEqual(self.store.read_bytes(ref), b"original")
        self.assertEqual(list((self.store.root / ".staging").iterdir()), [])

    def test_identity_collision_is_atomic_under_concurrent_writers(self):
        artifact_id, barrier = uuid4(), Barrier(2)
        publish = self.store._publish

        def simultaneous_publish(*args):
            barrier.wait(timeout=10)
            publish(*args)

        def put(content):
            try:
                return self.store.put_bytes(content, artifact_id)
            except DomainError as exc:
                return exc.code

        with patch.object(self.store, "_publish", side_effect=simultaneous_publish):
            with ThreadPoolExecutor(max_workers=2) as workers:
                outcomes = list(workers.map(put, (b"first", b"second")))
        refs = [value for value in outcomes if isinstance(value, ArtifactRef)]
        self.assertEqual(len(refs), 1)
        self.assertEqual(outcomes.count("ARTIFACT_EXISTS"), 1)
        self.assertIn(self.store.read_bytes(refs[0]), (b"first", b"second"))
        self.assertEqual(self.store.list_artifacts(), refs)
        self.assertEqual(list((self.store.root / ".staging").iterdir()), [])

    def test_empty_invalid_content_and_invalid_identity_do_not_publish(self):
        for data in (b"", "text", bytearray(b"data"), None):
            with self.subTest(data=data):
                self.assert_rejected("INVALID_ARTIFACT", lambda: self.store.put_bytes(data))
        self.assert_rejected("INVALID_ID", lambda: self.store.put_bytes(b"data", "not-a-uuid"))
        self.assertEqual(self.store.list_artifacts(), [])
        self.assertEqual(list((self.store.root / ".staging").iterdir()), [])

    def test_corruption_same_length_is_detected_on_every_read_api(self):
        ref = self.store.put_bytes(b"first")
        path = self.store.root / ref.storage_key
        path.chmod(0o600)  # Simulate external corruption by the filesystem owner.
        path.write_bytes(b"other")
        for method in (self.store.read_bytes, self.store.verify, self.store.path_for):
            with self.subTest(method=method.__name__):
                self.assert_rejected("ARTIFACT_CORRUPT", lambda: method(ref))

    def test_size_metadata_mismatch_and_missing_snapshot_fail_closed(self):
        ref = self.store.put_bytes(b"data")
        self.assert_rejected("ARTIFACT_CORRUPT", lambda: self.store.verify(replace(ref, size_bytes=100)))
        missing_id = uuid4()
        missing = replace(ref, artifact_id=missing_id, storage_key=f"objects/{missing_id}.ifc")
        self.assert_rejected("ARTIFACT_NOT_FOUND", lambda: self.store.read_bytes(missing))

    def test_reference_cannot_address_a_different_object_or_external_path(self):
        ref = self.store.put_bytes(b"data")
        foreign = self.directory / "external.ifc"
        foreign.write_bytes(b"external")
        for key in (f"objects/{uuid4()}.ifc", "other.ifc", ".staging/temporary"):
            with self.subTest(key=key):
                self.assert_rejected("UNSAFE_ARTIFACT_PATH", lambda: self.store.read_bytes(replace(ref, storage_key=key)))
        for key in (str(foreign), "../external.ifc", "objects/../../external.ifc"):
            with self.subTest(key=key):
                forged = replace(ref)
                object.__setattr__(forged, "storage_key", key)
                self.assert_rejected("INVALID_ARTIFACT", lambda: self.store.read_bytes(forged))
        self.assertEqual(foreign.read_bytes(), b"external")

    def test_symlink_as_finalized_object_is_never_followed_or_replaced(self):
        external = self.directory / "external.ifc"
        external.write_bytes(b"external")
        artifact_id = uuid4()
        final = self.store.root / "objects" / f"{artifact_id}.ifc"
        final.symlink_to(external)
        ref = ArtifactRef(artifact_id, sha256(b"external").hexdigest(), 8, f"objects/{artifact_id}.ifc")
        self.assert_rejected("UNSAFE_ARTIFACT_PATH", lambda: self.store.read_bytes(ref))
        self.assert_rejected("ARTIFACT_EXISTS", lambda: self.store.put_bytes(b"replacement", artifact_id))
        self.assertTrue(final.is_symlink())
        self.assertEqual(external.read_bytes(), b"external")

    def test_source_symlink_and_symlink_ancestor_are_rejected(self):
        source_dir = self.directory / "sources"
        source_dir.mkdir()
        source = source_dir / "original.ifc"
        source.write_bytes(b"original")
        link = self.directory / "link.ifc"
        link.symlink_to(source)
        parent_link = self.directory / "linked_directory"
        parent_link.symlink_to(source_dir, target_is_directory=True)
        for unsafe in (link, parent_link / source.name):
            with self.subTest(unsafe=unsafe):
                self.assert_rejected("INVALID_ARTIFACT_SOURCE", lambda: self.store.put_file(unsafe))
        self.assertEqual(self.store.list_artifacts(), [])

    def test_symlink_store_root_and_internal_directory_are_rejected(self):
        link = self.directory / "linked_store"
        link.symlink_to(self.store.root, target_is_directory=True)
        self.assert_rejected("UNSAFE_ARTIFACT_PATH", lambda: LocalArtifactStore(link))
        root = self.directory / "unsafe_store"
        root.mkdir()
        (root / "objects").symlink_to(self.store.root / "objects", target_is_directory=True)
        self.assert_rejected("UNSAFE_ARTIFACT_PATH", lambda: LocalArtifactStore(root))

    def test_swapped_objects_directory_is_rejected_after_initialization(self):
        ref = self.store.put_bytes(b"data")
        objects = self.store.root / "objects"
        moved = self.store.root / "moved_objects"
        objects.rename(moved)
        objects.symlink_to(moved, target_is_directory=True)
        self.assert_rejected("UNSAFE_ARTIFACT_PATH", lambda: self.store.verify(ref))
        self.assert_rejected("ARTIFACT_IO_ERROR", lambda: self.store.put_bytes(b"new"))
        self.assertEqual((moved / f"{ref.artifact_id}.ifc").read_bytes(), b"data")

    def test_nonregular_source_and_object_are_rejected_without_fifo_block(self):
        source = self.directory / "source_fifo"
        os.mkfifo(source)
        self.assert_rejected("UNSAFE_ARTIFACT_PATH", lambda: self.store.put_file(source))
        self.assert_rejected("UNSAFE_ARTIFACT_PATH", lambda: self.store.put_file(self.directory))
        artifact_id = uuid4()
        os.mkfifo(self.store.root / "objects" / f"{artifact_id}.ifc")
        ref = ArtifactRef(artifact_id, "0" * 64, 1, f"objects/{artifact_id}.ifc")
        self.assert_rejected("UNSAFE_ARTIFACT_PATH", lambda: self.store.verify(ref))

    def test_finalize_failure_cleans_only_own_temporary_and_never_creates_final(self):
        foreign_stage = self.store.root / ".staging" / "another-call.partial"
        foreign_stage.write_bytes(b"keep")
        with patch.object(self.store, "_publish", side_effect=OSError("simulated finalize failure")):
            self.assert_rejected("ARTIFACT_IO_ERROR", lambda: self.store.put_bytes(b"data"))
        self.assertEqual(self.store.list_artifacts(), [])
        self.assertEqual(list(foreign_stage.parent.iterdir()), [foreign_stage])
        self.assertEqual(foreign_stage.read_bytes(), b"keep")

    def test_file_fsync_failure_cannot_publish_partial_snapshot(self):
        original_fsync = os.fsync

        def fail_file_sync(fd):
            if stat.S_ISREG(os.fstat(fd).st_mode):
                raise OSError("simulated file sync failure")
            original_fsync(fd)

        with patch("neurobuild.infrastructure.artifacts.os.fsync", side_effect=fail_file_sync):
            self.assert_rejected("ARTIFACT_IO_ERROR", lambda: self.store.put_bytes(b"data"))
        self.assertEqual(self.store.list_artifacts(), [])
        self.assertEqual(list((self.store.root / ".staging").iterdir()), [])

    def test_failure_after_publication_keeps_complete_orphan_for_recovery(self):
        publish = self.store._publish
        artifact_id = uuid4()

        def fail_after_link(*args):
            publish(*args)
            raise OSError("simulated failure after atomic publication")

        with patch.object(self.store, "_publish", side_effect=fail_after_link):
            self.assert_rejected("ARTIFACT_IO_ERROR", lambda: self.store.put_bytes(b"complete", artifact_id))
        recovered = self.store.list_artifacts()
        self.assertEqual(len(recovered), 1)
        self.assertEqual(recovered[0].artifact_id, artifact_id)
        self.assertEqual(self.store.read_bytes(recovered[0]), b"complete")
        self.assertEqual(list((self.store.root / ".staging").iterdir()), [])

    def test_recovery_verification_retries_file_and_publication_directory_sync(self):
        objects_inode = (self.store.root / "objects").stat().st_ino
        original_fsync = os.fsync

        def fail_objects_sync(fd):
            if os.fstat(fd).st_ino == objects_inode:
                raise OSError("simulated directory sync failure after publication")
            original_fsync(fd)

        with patch("neurobuild.infrastructure.artifacts.os.fsync", side_effect=fail_objects_sync):
            self.assert_rejected("ARTIFACT_IO_ERROR", lambda: self.store.put_bytes(b"recoverable"))
        # Inventory/read can inspect the complete orphan but are not commit gates.
        with patch("neurobuild.infrastructure.artifacts.os.fsync", wraps=original_fsync) as sync:
            ref, = self.store.list_artifacts()
            self.assertEqual(self.store.read_bytes(ref), b"recoverable")
            sync.assert_not_called()
        file_inode = (self.store.root / ref.storage_key).stat().st_ino
        synced = []

        def record_sync(fd):
            synced.append(os.fstat(fd).st_ino)
            original_fsync(fd)

        with patch("neurobuild.infrastructure.artifacts.os.fsync", side_effect=record_sync):
            self.store.verify(ref)
        self.assertEqual(synced, [file_inode, objects_inode])
        self.assertEqual(list((self.store.root / ".staging").iterdir()), [])

    def test_recovery_verification_failure_cannot_claim_commit_readiness(self):
        ref = self.store.put_bytes(b"data")
        with patch("neurobuild.infrastructure.artifacts.os.fsync", side_effect=OSError("sync unavailable")):
            self.assert_rejected("ARTIFACT_IO_ERROR", lambda: self.store.verify(ref))
        self.assertEqual(self.store.read_bytes(ref), b"data")
        # A retry after storage recovers can establish durability.
        self.store.verify(ref)

    def test_inventory_survives_reopening_and_does_not_promote_staging(self):
        refs = [self.store.put_bytes(b"one"), self.store.put_bytes(b"two")]
        abandoned = self.store.root / ".staging" / "abandoned.partial"
        abandoned.write_bytes(b"incomplete")
        reopened = LocalArtifactStore(self.store.root)
        self.assertEqual(set(reopened.list_artifacts()), set(refs))
        self.assertTrue(abandoned.exists())
        for ref in refs:
            reopened.verify(ref)

    def test_inventory_rejects_unexpected_names_and_symlinks(self):
        unexpected = self.store.root / "objects" / "unknown.ifc"
        unexpected.write_bytes(b"unknown")
        self.assert_rejected("UNSAFE_ARTIFACT_PATH", self.store.list_artifacts)
        unexpected.unlink()
        (self.store.root / "objects" / f"{uuid4()}.ifc").symlink_to(self.directory / "missing")
        self.assert_rejected("UNSAFE_ARTIFACT_PATH", self.store.list_artifacts)


if __name__ == "__main__":
    unittest.main()
