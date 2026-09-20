"""Immutable local IFC snapshots with atomic, no-clobber publication.

The trusted application owns the store directories. Finalized files are read-only
as an accidental-write guard, not an OS security boundary against their owner.
Publication precedes the database transaction: failures after publication can
leave a complete orphan, which recovery may inspect but this adapter never deletes.
"""

from contextlib import contextmanager
from hashlib import sha256
from io import BytesIO
import os
from pathlib import Path
import stat
from typing import BinaryIO, Iterator
from uuid import UUID, uuid4

from neurobuild.domain.contracts import ArtifactRef
from neurobuild.domain.errors import DomainError


_CHUNK_SIZE = 1024 * 1024
_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_READ_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC


def _absolute_path(path: Path) -> Path:
    if not isinstance(path, Path) or ".." in path.parts:
        raise DomainError("UNSAFE_ARTIFACT_PATH", "A path without parent traversal is required")
    return path.absolute()


@contextmanager
def _directory(path: Path, *, create: bool = False) -> Iterator[int]:
    """Walk from / with directory descriptors; reject symlinks in every component."""
    fd = os.open(path.anchor, _DIRECTORY_FLAGS)
    try:
        for component in path.parts[1:]:
            if create:
                try:
                    os.mkdir(component, mode=0o700, dir_fd=fd)
                except FileExistsError:
                    pass
                else:
                    os.fsync(fd)
            next_fd = os.open(component, _DIRECTORY_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        yield fd
    finally:
        os.close(fd)


def _regular(fd: int) -> os.stat_result:
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode):
        raise DomainError("UNSAFE_ARTIFACT_PATH", "Artifact inputs must be regular files")
    return info


@contextmanager
def _regular_file(parent_fd: int, name: str) -> Iterator[tuple[BinaryIO, os.stat_result]]:
    fd = os.open(name, _READ_FLAGS, dir_fd=parent_fd)
    try:
        info = _regular(fd)
        with os.fdopen(fd, "rb", closefd=False) as stream:
            yield stream, info
    finally:
        os.close(fd)


class LocalArtifactStore:
    """Store full snapshots under objects/<UUID>.ifc, without overwrites.

    Reusing an artifact ID always raises ARTIFACT_EXISTS, including identical
    content. Idempotent workflow retries must reuse their previously committed
    ArtifactRef and verify it, rather than attempting another put with that ID.
    """

    def __init__(self, root: Path) -> None:
        self.root = _absolute_path(root)
        try:
            with _directory(self.root, create=True) as root_fd:
                for name in ("objects", ".staging"):
                    try:
                        os.mkdir(name, mode=0o700, dir_fd=root_fd)
                    except FileExistsError:
                        pass
                    child_fd = os.open(name, _DIRECTORY_FLAGS, dir_fd=root_fd)
                    os.close(child_fd)
                os.fsync(root_fd)
        except OSError as exc:
            raise DomainError("UNSAFE_ARTIFACT_PATH", "Artifact store directories are unavailable or unsafe") from exc

    @contextmanager
    def _directories(self) -> Iterator[tuple[int, int]]:
        with _directory(self.root) as root_fd:
            objects_fd = os.open("objects", _DIRECTORY_FLAGS, dir_fd=root_fd)
            try:
                staging_fd = os.open(".staging", _DIRECTORY_FLAGS, dir_fd=root_fd)
                try:
                    yield objects_fd, staging_fd
                finally:
                    os.close(staging_fd)
            finally:
                os.close(objects_fd)

    @staticmethod
    def _name(ref: ArtifactRef) -> str:
        if type(ref) is not ArtifactRef:
            raise DomainError("INVALID_ARTIFACT", "An ArtifactRef is required")
        # Revalidate even if a caller bypassed a frozen dataclass's constructor.
        ArtifactRef(ref.artifact_id, ref.sha256, ref.size_bytes, ref.storage_key)
        name = f"{ref.artifact_id}.ifc"
        if ref.storage_key != f"objects/{name}":
            raise DomainError("UNSAFE_ARTIFACT_PATH", "Artifact key must match its canonical object identity")
        return name

    def put_bytes(self, data: bytes, artifact_id: UUID | None = None) -> ArtifactRef:
        if type(data) is not bytes:
            raise DomainError("INVALID_ARTIFACT", "Artifact content must be bytes")
        return self._put_stream(BytesIO(data), artifact_id)

    def put_file(self, source: Path, artifact_id: UUID | None = None) -> ArtifactRef:
        """Copy a regular, non-symlink source; never rename or modify the source."""
        source = _absolute_path(source)
        try:
            with _directory(source.parent) as parent_fd:
                with _regular_file(parent_fd, source.name) as (stream, info):
                    return self._put_stream(stream, artifact_id, source_info=info)
        except OSError as exc:
            raise DomainError("INVALID_ARTIFACT_SOURCE", "Artifact source could not be read safely") from exc

    @staticmethod
    def _publish(staging_fd: int, temporary: str, objects_fd: int, final: str) -> None:
        # link() is an atomic create-if-absent on the same filesystem. replace()
        # and ordinary rename() would violate immutability on an ID collision.
        os.link(temporary, final, src_dir_fd=staging_fd, dst_dir_fd=objects_fd, follow_symlinks=False)

    def _put_stream(
        self, stream: BinaryIO, artifact_id: UUID | None, *, source_info: os.stat_result | None = None
    ) -> ArtifactRef:
        artifact_id = uuid4() if artifact_id is None else artifact_id
        if not isinstance(artifact_id, UUID):
            raise DomainError("INVALID_ID", "Artifact ID must be a UUID")
        final = f"{artifact_id}.ifc"
        temporary = f"{uuid4()}.partial"
        try:
            with self._directories() as (objects_fd, staging_fd):
                created = False
                try:
                    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                                 mode=0o600, dir_fd=staging_fd)
                    created = True
                    digest, size = sha256(), 0
                    with os.fdopen(fd, "wb") as output:
                        while chunk := stream.read(_CHUNK_SIZE):
                            output.write(chunk)
                            digest.update(chunk)
                            size += len(chunk)
                        if source_info is not None:
                            after = _regular(stream.fileno())
                            before_key = (source_info.st_size, source_info.st_mtime_ns, source_info.st_ctime_ns)
                            after_key = (after.st_size, after.st_mtime_ns, after.st_ctime_ns)
                            if before_key != after_key or size != source_info.st_size:
                                raise DomainError("ARTIFACT_SOURCE_CHANGED", "Artifact source changed while being copied")
                        ref = ArtifactRef(artifact_id, digest.hexdigest(), size, f"objects/{final}")
                        output.flush()
                        os.fchmod(output.fileno(), 0o444)
                        os.fsync(output.fileno())
                    os.fsync(staging_fd)
                    try:
                        self._publish(staging_fd, temporary, objects_fd, final)
                    except FileExistsError as exc:
                        raise DomainError("ARTIFACT_EXISTS", "Artifact identity has already been finalized") from exc
                    os.fsync(objects_fd)
                    return ref
                finally:
                    if created:
                        # Only the temporary name created by this invocation is
                        # ours to remove. Never unlink a finalized artifact.
                        os.unlink(temporary, dir_fd=staging_fd)
                        os.fsync(staging_fd)
        except OSError as exc:
            raise DomainError("ARTIFACT_IO_ERROR", "Artifact storage operation failed") from exc

    @staticmethod
    def _read_file(
        objects_fd: int, name: str, *, collect: bool,
        expected: ArtifactRef | None = None, durable: bool = False,
    ) -> tuple[str, int, bytes]:
        with _regular_file(objects_fd, name) as (stream, _):
            digest, size, chunks = sha256(), 0, []
            while chunk := stream.read(_CHUNK_SIZE):
                digest.update(chunk)
                size += len(chunk)
                if collect:
                    chunks.append(chunk)
            checksum = digest.hexdigest()
            if expected is not None and (checksum != expected.sha256 or size != expected.size_bytes):
                raise DomainError("ARTIFACT_CORRUPT", "Artifact checksum or size does not match its reference")
            if durable:
                try:
                    # Sync the exact descriptor whose bytes were verified, then
                    # the published directory entry. Recovery can safely retry
                    # this after a put failed between link() and directory sync.
                    os.fsync(stream.fileno())
                    os.fsync(objects_fd)
                except OSError as exc:
                    raise DomainError("ARTIFACT_IO_ERROR", "Artifact durability could not be established") from exc
            return checksum, size, b"".join(chunks)

    def _read(self, ref: ArtifactRef, *, collect: bool, durable: bool = False) -> bytes:
        name = self._name(ref)
        try:
            with self._directories() as (objects_fd, _):
                _, _, data = self._read_file(objects_fd, name, collect=collect, expected=ref, durable=durable)
                return data
        except FileNotFoundError as exc:
            raise DomainError("ARTIFACT_NOT_FOUND", "Artifact is unavailable") from exc
        except OSError as exc:
            raise DomainError("UNSAFE_ARTIFACT_PATH", "Artifact could not be opened safely") from exc

    def read_bytes(self, ref: ArtifactRef) -> bytes:
        """Return integrity-checked bytes; this read does not establish durability."""
        return self._read(ref, collect=True)

    def verify(self, ref: ArtifactRef) -> None:
        """Verify integrity and fsync the file and its objects directory.

        Call before committing metadata, including when recovering a finalized
        orphan after a failed put. Success establishes publication durability
        under the owned, immutable-store assumption. Failed fsync raises
        ARTIFACT_IO_ERROR and must prevent the database commit.
        """
        self._read(ref, collect=False, durable=True)

    def path_for(self, ref: ArtifactRef) -> Path:
        """Verified read-only input path for trusted internal IFC adapters.

        A returned path cannot prevent TOCTOU changes by another filesystem
        writer. The application must own the store and never mutate objects;
        use read_bytes for consumers requiring verified bytes from one open FD.
        """
        self.verify(ref)
        return self.root / ref.storage_key

    def list_artifacts(self) -> list[ArtifactRef]:
        """Inventory finalized objects for orphan inspection, without deletion.

        Digests describe the bytes observed now. Compare against database refs
        to detect corruption; this inventory is not authoritative metadata.
        Unknown object names and nonregular files fail closed. Staging is ignored.
        Inventory does not establish durability: verify each ref before DB commit.
        """
        result = []
        try:
            with self._directories() as (objects_fd, _):
                for name in sorted(os.listdir(objects_fd)):
                    try:
                        artifact_id = UUID(name.removesuffix(".ifc"))
                    except ValueError as exc:
                        raise DomainError("UNSAFE_ARTIFACT_PATH", "Unexpected finalized artifact name") from exc
                    if name != f"{artifact_id}.ifc":
                        raise DomainError("UNSAFE_ARTIFACT_PATH", "Noncanonical finalized artifact name")
                    digest, size, _ = self._read_file(objects_fd, name, collect=False)
                    result.append(ArtifactRef(artifact_id, digest, size, f"objects/{name}"))
        except OSError as exc:
            raise DomainError("UNSAFE_ARTIFACT_PATH", "Artifact inventory could not be read safely") from exc
        return result
