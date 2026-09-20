"""PostgreSQL metadata and serialized revision publication; no IFC/workflow logic."""

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import re
from uuid import UUID, uuid4

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from neurobuild.domain.contracts import ArtifactRef, Project, Revision
from neurobuild.domain.errors import DomainError
from .artifacts import LocalArtifactStore


@dataclass(frozen=True)
class ExecutionIntent:
    execution_id: UUID
    project_id: UUID
    base_revision_id: UUID | None
    proposal_id: UUID | None
    payload_fingerprint: str
    artifact_id: UUID
    status: str
    result_revision_id: UUID | None


def _require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise DomainError(code, message)


def _ids(*values: UUID) -> None:
    _require(all(isinstance(value, UUID) for value in values), "INVALID_ID", "Expected UUID values")


def _fingerprint(value: str) -> None:
    _require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
             "INVALID_EXECUTION", "Payload fingerprint must be lowercase SHA256")


class PostgresStore:
    """Each call owns a short connection/transaction; instances share no connection."""

    def __init__(self, dsn: str, artifacts: LocalArtifactStore, schema: str = "neurobuild") -> None:
        _require(isinstance(schema, str) and re.fullmatch(r"[a-z][a-z0-9_]{0,62}", schema) is not None
                 and not schema.startswith("pg_") and schema not in {"public", "information_schema"},
                 "INVALID_SCHEMA", "A dedicated lowercase PostgreSQL schema name is required")
        self.dsn = dsn
        self.artifacts = artifacts
        self.schema = schema

    @contextmanager
    def _connection(self):
        try:
            with psycopg.connect(self.dsn, row_factory=dict_row) as connection:
                connection.execute(sql.SQL("SET LOCAL search_path TO {}, pg_catalog").format(sql.Identifier(self.schema)))
                yield connection
        except psycopg.IntegrityError:
            raise DomainError("PERSISTENCE_CONFLICT", "Database constraints rejected the change") from None
        except psycopg.Error:
            # Do not expose connection strings or raw SQL/server messages to callers.
            raise DomainError("PERSISTENCE_ERROR", "Database operation failed") from None

    def migrate(self) -> None:
        """Apply repository migration 001 once, atomically, to this schema only."""
        migration = Path(__file__).resolve().parents[3] / "migrations" / "001_initial.sql"
        with self._connection() as connection:
            connection.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ("neurobuild:migrate:" + self.schema,))
            connection.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(self.schema)))
            connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version integer PRIMARY KEY)")
            versions = {row["version"] for row in connection.execute("SELECT version FROM schema_migrations")}
            _require(not versions - {1}, "MIGRATION_VERSION", "Database migration version is newer than this application")
            if 1 not in versions:
                connection.execute(migration.read_text(encoding="utf-8"))
                for name in ("reject_immutable_change", "validate_revision_insert", "validate_intent_change"):
                    connection.execute(
                        sql.SQL("ALTER FUNCTION {}.{}() SET search_path TO {}, pg_catalog").format(
                            sql.Identifier(self.schema), sql.Identifier(name), sql.Identifier(self.schema)
                        )
                    )
                connection.execute("INSERT INTO schema_migrations(version) VALUES (1)")

    @staticmethod
    def _project(row) -> Project:
        return Project(row["project_id"], row["name"], row["head_revision_id"])

    @staticmethod
    def _intent(row) -> ExecutionIntent:
        return ExecutionIntent(**row)

    @staticmethod
    def _revision(row) -> Revision:
        artifact = ArtifactRef(row["artifact_id"], row["sha256"], row["size_bytes"], row["storage_key"])
        return Revision(row["revision_id"], row["project_id"], row["number"], artifact,
                        row["parent_revision_id"], row["ifc_schema"])

    def _fetch_project(self, connection, project_id: UUID, *, lock=False) -> Project:
        query = "SELECT * FROM projects WHERE project_id = %s" + (" FOR UPDATE" if lock else "")
        row = connection.execute(query, (project_id,)).fetchone()
        _require(row is not None, "PROJECT_NOT_FOUND", "Project does not exist")
        return self._project(row)

    def _fetch_revision(self, connection, revision_id: UUID) -> Revision:
        row = connection.execute(
            "SELECT r.*, a.sha256, a.size_bytes, a.storage_key FROM revisions r "
            "JOIN artifacts a USING (artifact_id) WHERE r.revision_id = %s", (revision_id,)
        ).fetchone()
        _require(row is not None, "REVISION_NOT_FOUND", "Revision does not exist")
        return self._revision(row)

    def _fetch_intent(self, connection, execution_id: UUID, *, lock=False) -> ExecutionIntent:
        query = "SELECT * FROM execution_intents WHERE execution_id = %s" + (" FOR UPDATE" if lock else "")
        row = connection.execute(query, (execution_id,)).fetchone()
        _require(row is not None, "EXECUTION_NOT_FOUND", "Prepare execution before finalizing an artifact")
        return self._intent(row)

    def create_project(self, name: str, project_id: UUID | None = None) -> Project:
        project = Project(uuid4() if project_id is None else project_id, name)
        with self._connection() as connection:
            connection.execute("INSERT INTO projects(project_id, name) VALUES (%s, %s)",
                               (project.project_id, project.name))
        return project

    def get_project(self, project_id: UUID) -> Project:
        _ids(project_id)
        with self._connection() as connection:
            return self._fetch_project(connection, project_id)

    def get_revision(self, revision_id: UUID) -> Revision:
        _ids(revision_id)
        with self._connection() as connection:
            return self._fetch_revision(connection, revision_id)

    def list_revisions(self, project_id: UUID) -> list[Revision]:
        _ids(project_id)
        with self._connection() as connection:
            self._fetch_project(connection, project_id)
            rows = connection.execute(
                "SELECT r.*, a.sha256, a.size_bytes, a.storage_key FROM revisions r "
                "JOIN artifacts a USING (artifact_id) WHERE r.project_id = %s ORDER BY r.number", (project_id,)
            )
            return [self._revision(row) for row in rows]

    def get_execution(self, execution_id: UUID) -> ExecutionIntent:
        _ids(execution_id)
        with self._connection() as connection:
            return self._fetch_intent(connection, execution_id)

    def prepare_execution(
        self, execution_id: UUID, project_id: UUID, base_revision_id: UUID | None,
        proposal_id: UUID | None, payload_fingerprint: str, *, artifact_id: UUID | None = None,
    ) -> ExecutionIntent:
        """Durably reserve identity and expected content before filesystem finalize."""
        artifact_id = execution_id if artifact_id is None else artifact_id
        _ids(execution_id, project_id, artifact_id)
        _fingerprint(payload_fingerprint)
        _require((base_revision_id is None) == (proposal_id is None), "INVALID_EXECUTION", "Import has no base/proposal; Apply requires both")
        if base_revision_id is not None:
            _ids(base_revision_id, proposal_id)
        expected = ExecutionIntent(execution_id, project_id, base_revision_id, proposal_id,
                                   payload_fingerprint, artifact_id, "PREPARED", None)
        with self._connection() as connection:
            project = self._fetch_project(connection, project_id, lock=True)
            existing = connection.execute("SELECT * FROM execution_intents WHERE execution_id = %s", (execution_id,)).fetchone()
            if existing is not None:
                intent = self._intent(existing)
                self._same_intent(intent, expected)
                return intent
            _require(project.head_revision_id == base_revision_id,
                     "PROJECT_ALREADY_INITIALIZED" if base_revision_id is None else "STALE_PROPOSAL",
                     "Execution base does not match current project head")
            connection.execute(
                "INSERT INTO execution_intents(execution_id, project_id, base_revision_id, proposal_id, "
                "payload_fingerprint, artifact_id) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (execution_id, project_id, base_revision_id, proposal_id, payload_fingerprint, artifact_id),
            )
            row = connection.execute("SELECT * FROM execution_intents WHERE execution_id = %s", (execution_id,)).fetchone()
            _require(row is not None, "IDEMPOTENCY_CONFLICT", "Proposal or artifact identity is already reserved by another execution")
            intent = self._intent(row)
            self._same_intent(intent, expected)
            return intent

    @staticmethod
    def _same_intent(actual: ExecutionIntent, expected: ExecutionIntent) -> None:
        fields = ("execution_id", "project_id", "base_revision_id", "proposal_id", "payload_fingerprint", "artifact_id")
        _require(all(getattr(actual, name) == getattr(expected, name) for name in fields),
                 "IDEMPOTENCY_CONFLICT", "Execution key is already bound to different content")

    def import_revision(self, project_id: UUID, artifact: ArtifactRef, execution_id: UUID) -> Revision:
        """Publish V0 only after an import intent and immutable artifact exist."""
        return self._commit_revision(project_id, None, artifact, execution_id, None,
                                     payload_fingerprint=artifact.sha256 if type(artifact) is ArtifactRef else None)

    def commit_revision(
        self, project_id: UUID, base_revision_id: UUID, artifact: ArtifactRef,
        execution_id: UUID, proposal_id: UUID, *, payload_fingerprint: str | None = None,
    ) -> Revision:
        """Publish one full snapshot; Phase 4 caller must supply authorization first."""
        _ids(base_revision_id, proposal_id)
        return self._commit_revision(project_id, base_revision_id, artifact, execution_id, proposal_id,
                                     payload_fingerprint=payload_fingerprint)

    def _commit_revision(
        self, project_id: UUID, base_revision_id: UUID | None, artifact: ArtifactRef,
        execution_id: UUID, proposal_id: UUID | None, *, payload_fingerprint: str | None,
    ) -> Revision:
        _ids(project_id, execution_id)
        _require(type(artifact) is ArtifactRef, "INVALID_ARTIFACT", "An immutable ArtifactRef is required")
        if payload_fingerprint is not None:
            _fingerprint(payload_fingerprint)
        self.artifacts.verify(artifact)
        with self._connection() as connection:
            project = self._fetch_project(connection, project_id, lock=True)
            intent = self._fetch_intent(connection, execution_id, lock=True)
            expected = ExecutionIntent(execution_id, project_id, base_revision_id, proposal_id,
                                       intent.payload_fingerprint if payload_fingerprint is None else payload_fingerprint,
                                       artifact.artifact_id, "PREPARED", None)
            self._same_intent(intent, expected)
            if intent.status == "COMMITTED":
                result = self._fetch_revision(connection, intent.result_revision_id)
                _require(result.artifact == artifact, "IDEMPOTENCY_CONFLICT", "Retry artifact differs from the committed snapshot")
                return result
            _require(project.head_revision_id == base_revision_id,
                     "PROJECT_ALREADY_INITIALIZED" if base_revision_id is None else "STALE_PROPOSAL",
                     "Execution base no longer matches current project head")
            number = 0 if base_revision_id is None else self._fetch_revision(connection, base_revision_id).number + 1
            revision = Revision(uuid4(), project_id, number, artifact, base_revision_id)
            connection.execute(
                "INSERT INTO artifacts(artifact_id, sha256, size_bytes, storage_key) VALUES (%s, %s, %s, %s)",
                (artifact.artifact_id, artifact.sha256, artifact.size_bytes, artifact.storage_key),
            )
            connection.execute(
                "INSERT INTO revisions(revision_id, project_id, number, parent_revision_id, artifact_id, execution_id) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (revision.revision_id, project_id, number, base_revision_id, artifact.artifact_id, execution_id),
            )
            changed = connection.execute(
                "UPDATE projects SET head_revision_id = %s WHERE project_id = %s AND head_revision_id IS NOT DISTINCT FROM %s",
                (revision.revision_id, project_id, base_revision_id),
            ).rowcount
            _require(changed == 1, "STALE_PROPOSAL", "Project head changed before publication")
            connection.execute(
                "UPDATE execution_intents SET status = 'COMMITTED', result_revision_id = %s WHERE execution_id = %s",
                (revision.revision_id, execution_id),
            )
            return revision
