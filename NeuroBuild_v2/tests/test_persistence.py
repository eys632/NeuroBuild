"""Real PostgreSQL/immutable-file integration tests using owned temporary schemas.

NEUROBUILD_TEST_DSN must name the project's private Unix-socket PostgreSQL.
These tests validate storage consistency, not IFC semantics or human approval.
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import os
from pathlib import Path
import tempfile
from threading import Barrier
import unittest
from uuid import uuid4

from neurobuild.domain.errors import DomainError


TEST_DSN = os.environ.get("NEUROBUILD_TEST_DSN")
PROJECT_ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(TEST_DSN, "NEUROBUILD_TEST_DSN is required for real PostgreSQL integration")
class PersistenceIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        from psycopg import sql
        from psycopg.conninfo import conninfo_to_dict, make_conninfo
        from neurobuild.infrastructure.artifacts import LocalArtifactStore
        from neurobuild.infrastructure.persistence import PostgresStore

        connection = conninfo_to_dict(TEST_DSN)
        host = connection.get("host", "")
        if (not host.startswith("/") or connection.get("hostaddr") or connection.get("service")
                or not Path(host).resolve().is_relative_to((PROJECT_ROOT / "var").resolve())):
            raise RuntimeError("Integration tests require this project's private Unix socket")
        if not connection.get("dbname") or not connection.get("user"):
            raise RuntimeError("Integration tests require explicit database and user names")
        cls.psycopg = psycopg
        cls.sql = sql
        cls.artifact_type = LocalArtifactStore
        cls.store_type = PostgresStore
        cls.dsn = make_conninfo(TEST_DSN, connect_timeout="5", options="-c statement_timeout=10000")

    def setUp(self):
        self.schema = "nb_test_" + uuid4().hex
        self.created_schema = False
        with self.psycopg.connect(self.dsn, autocommit=True) as connection:
            connection.execute(self.sql.SQL("CREATE SCHEMA {}").format(self.sql.Identifier(self.schema)))
        self.created_schema = True
        self.addCleanup(self.drop_owned_schema)
        temporary_parent = PROJECT_ROOT / "var" / "tests" / "persistence"
        temporary_parent.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix="nb_test_", dir=temporary_parent)
        self.addCleanup(temporary.cleanup)
        self.artifacts = self.artifact_type(Path(temporary.name) / "artifacts")
        self.store = self.new_store()
        self.store.migrate()

    def new_store(self):
        return self.store_type(self.dsn, self.artifacts, schema=self.schema)

    def drop_owned_schema(self):
        if not self.created_schema or not self.schema.startswith("nb_test_") or len(self.schema) != 40:
            raise RuntimeError("Refusing to drop a schema not created by this test")
        with self.psycopg.connect(self.dsn, autocommit=True) as connection:
            connection.execute(self.sql.SQL("DROP SCHEMA {} CASCADE").format(self.sql.Identifier(self.schema)))
        self.created_schema = False

    def statement(self, text, parameters=()):
        with self.psycopg.connect(self.dsn, autocommit=True) as connection:
            connection.execute(self.sql.SQL("SET search_path TO {}, pg_catalog").format(self.sql.Identifier(self.schema)))
            cursor = connection.execute(text, parameters)
            return cursor.fetchall() if cursor.description else None

    def import_fixture(self, name="Synthetic fixture", content=b"ISO-10303-21;\nSYNTHETIC V0\nEND-ISO-10303-21;\n"):
        project = self.store.create_project(name)
        execution_id = uuid4()
        fingerprint = hashlib.sha256(content).hexdigest()
        intent = self.store.prepare_execution(execution_id, project.project_id, None, None, fingerprint)
        artifact = self.artifacts.put_bytes(content, artifact_id=intent.artifact_id)
        revision = self.store.import_revision(project.project_id, artifact, execution_id)
        return self.store.get_project(project.project_id), revision

    def prepare_move(self, project, base, *, execution_id=None, proposal_id=None, content=b"SYNTHETIC V1"):
        execution_id = execution_id or uuid4()
        proposal_id = proposal_id or uuid4()
        fingerprint = hashlib.sha256((str(proposal_id) + ":move:x=1m").encode()).hexdigest()
        intent = self.store.prepare_execution(
            execution_id, project.project_id, base.revision_id, proposal_id, fingerprint,
        )
        artifact = self.artifacts.put_bytes(content, artifact_id=intent.artifact_id)
        return intent, artifact

    def commit(self, project, base, intent, artifact, store=None):
        return (store or self.store).commit_revision(
            project.project_id, base.revision_id, artifact, intent.execution_id,
            intent.proposal_id, payload_fingerprint=intent.payload_fingerprint,
        )

    def assert_rejected(self, callback, code=None):
        with self.assertRaises(DomainError) as caught:
            callback()
        if code is not None:
            self.assertEqual(caught.exception.code, code)

    def test_migration_is_repeatable_without_losing_existing_data(self):
        project, revision = self.import_fixture()
        self.new_store().migrate()
        self.store.migrate()
        self.assertEqual(self.store.get_project(project.project_id), project)
        self.assertEqual(self.store.get_revision(revision.revision_id), revision)

    def test_project_starts_empty_and_import_retains_full_snapshot(self):
        empty = self.store.create_project("Empty project")
        self.assertIsNone(empty.head_revision_id)
        self.assertEqual(self.store.list_revisions(empty.project_id), [])
        content = b"ISO-10303-21;\nCOMPLETE SYNTHETIC SNAPSHOT\nEND-ISO-10303-21;\n"
        project, revision = self.import_fixture(content=content)
        self.assertEqual(revision.number, 0)
        self.assertIsNone(revision.parent_revision_id)
        self.assertEqual(project.head_revision_id, revision.revision_id)
        self.assertEqual(self.artifacts.read_bytes(revision.artifact), content)
        self.assertEqual(revision.artifact.sha256, hashlib.sha256(content).hexdigest())
        self.assertEqual(revision.artifact.size_bytes, len(content))

    def test_revision_and_artifact_rows_reject_update_and_delete(self):
        project, original = self.import_fixture()
        statements = (
            ("UPDATE revisions SET ifc_schema = 'IFC4' WHERE revision_id = %s", original.revision_id),
            ("DELETE FROM revisions WHERE revision_id = %s", original.revision_id),
            ("UPDATE artifacts SET sha256 = %s WHERE artifact_id = %s", ("b" * 64, original.artifact.artifact_id)),
            ("DELETE FROM artifacts WHERE artifact_id = %s", original.artifact.artifact_id),
        )
        for command, values in statements:
            with self.subTest(command=command):
                parameters = values if isinstance(values, tuple) else (values,)
                with self.assertRaises(self.psycopg.Error) as caught:
                    self.statement(command, parameters)
                self.assertEqual(caught.exception.sqlstate, "23514")
        self.assertEqual(self.store.get_revision(original.revision_id), original)
        self.assertEqual(self.store.get_project(project.project_id).head_revision_id, original.revision_id)

    def test_other_projects_revision_cannot_be_used_as_base_or_head(self):
        project, _ = self.import_fixture("First")
        _, foreign_base = self.import_fixture("Second")
        self.assert_rejected(lambda: self.store.prepare_execution(
            uuid4(), project.project_id, foreign_base.revision_id, uuid4(), "a" * 64,
        ))
        with self.assertRaises(self.psycopg.Error):
            self.statement("UPDATE projects SET head_revision_id = %s WHERE project_id = %s",
                           (foreign_base.revision_id, project.project_id))
        with self.assertRaises(self.psycopg.Error) as caught:
            self.statement(
                "INSERT INTO execution_intents(execution_id, project_id, base_revision_id, "
                "proposal_id, payload_fingerprint, artifact_id) VALUES (%s, %s, %s, %s, %s, %s)",
                (uuid4(), project.project_id, foreign_base.revision_id, uuid4(), "a" * 64, uuid4()),
            )
        self.assertEqual(caught.exception.sqlstate, "23503")

    def test_same_execution_retry_returns_original_revision_without_duplicate_rows(self):
        project, base = self.import_fixture()
        intent, artifact = self.prepare_move(project, base)
        revision = self.commit(project, base, intent, artifact)
        replay = self.commit(project, base, intent, artifact, store=self.new_store())
        self.assertEqual(replay, revision)
        self.assertEqual(len(self.store.list_revisions(project.project_id)), 2)
        self.assertEqual(self.store.get_project(project.project_id).head_revision_id, revision.revision_id)
        self.assertEqual(self.store.get_execution(intent.execution_id).status, "COMMITTED")

    def test_committed_import_retry_returns_same_initial_revision(self):
        project = self.store.create_project("Import retry")
        payload = b"FULL SYNTHETIC V0"
        execution_id = uuid4()
        intent = self.store.prepare_execution(execution_id, project.project_id, None, None,
                                              hashlib.sha256(payload).hexdigest())
        artifact = self.artifacts.put_bytes(payload, artifact_id=intent.artifact_id)
        original = self.store.import_revision(project.project_id, artifact, execution_id)
        replay = self.new_store().import_revision(project.project_id, artifact, execution_id)
        self.assertEqual(original, replay)
        self.assertEqual(len(self.store.list_revisions(project.project_id)), 1)

    def test_execution_identifier_cannot_be_reused_for_different_payload_or_base(self):
        project, base = self.import_fixture()
        intent, artifact = self.prepare_move(project, base)
        revision = self.commit(project, base, intent, artifact)
        cases = (
            (base.revision_id, intent.proposal_id, "f" * 64),
            (revision.revision_id, intent.proposal_id, intent.payload_fingerprint),
            (base.revision_id, uuid4(), intent.payload_fingerprint),
        )
        for base_id, proposal_id, fingerprint in cases:
            with self.subTest(base=base_id, proposal=proposal_id, fingerprint=fingerprint):
                self.assert_rejected(lambda: self.store.prepare_execution(
                    intent.execution_id, project.project_id, base_id, proposal_id, fingerprint,
                ), "IDEMPOTENCY_CONFLICT")
        changed_metadata = replace(artifact, sha256="b" * 64)
        self.assert_rejected(lambda: self.commit(project, base, intent, changed_metadata))
        self.assertEqual(len(self.store.list_revisions(project.project_id)), 2)

    def test_same_proposal_cannot_create_another_execution(self):
        project, base = self.import_fixture()
        intent, _ = self.prepare_move(project, base)
        self.assert_rejected(lambda: self.store.prepare_execution(
            uuid4(), project.project_id, base.revision_id, intent.proposal_id, intent.payload_fingerprint,
        ), "IDEMPOTENCY_CONFLICT")

    def test_commit_requires_prepared_intent_and_its_reserved_artifact(self):
        project, base = self.import_fixture()
        intent, _ = self.prepare_move(project, base)
        other_artifact = self.artifacts.put_bytes(b"UNRESERVED SYNTHETIC SNAPSHOT")
        self.assert_rejected(lambda: self.commit(project, base, intent, other_artifact))
        self.assert_rejected(lambda: self.store.commit_revision(
            project.project_id, base.revision_id, other_artifact, uuid4(), uuid4(),
            payload_fingerprint="a" * 64,
        ), "EXECUTION_NOT_FOUND")
        self.assertEqual(self.store.get_project(project.project_id).head_revision_id, base.revision_id)

    def test_concurrent_same_base_commits_advance_head_exactly_once(self):
        project, base = self.import_fixture()
        attempts = (
            self.prepare_move(project, base, content=b"CONCURRENT PROPOSAL A"),
            self.prepare_move(project, base, content=b"CONCURRENT PROPOSAL B"),
        )
        barrier = Barrier(2, timeout=10)

        def apply_attempt(attempt):
            intent, artifact = attempt
            separate_store = self.new_store()
            barrier.wait()
            try:
                return "committed", self.commit(project, base, intent, artifact, store=separate_store)
            except DomainError as error:
                return "rejected", error.code

        with ThreadPoolExecutor(max_workers=2) as workers:
            futures = [workers.submit(apply_attempt, attempt) for attempt in attempts]
            results = [future.result(timeout=20) for future in futures]
        committed = [value for state, value in results if state == "committed"]
        rejected = [value for state, value in results if state == "rejected"]
        self.assertEqual(len(committed), 1)
        self.assertEqual(rejected, ["STALE_PROPOSAL"])
        self.assertEqual(self.store.get_project(project.project_id).head_revision_id, committed[0].revision_id)
        self.assertEqual(len(self.store.list_revisions(project.project_id)), 2)
        self.assertEqual(self.artifacts.read_bytes(base.artifact),
                         b"ISO-10303-21;\nSYNTHETIC V0\nEND-ISO-10303-21;\n")

    def test_database_failure_after_finalize_preserves_head_intent_and_orphan_for_retry(self):
        project, base = self.import_fixture()
        intent, artifact = self.prepare_move(project, base)
        finalized_path = self.artifacts.path_for(artifact)
        self.statement("ALTER TABLE revisions ADD CONSTRAINT nb_test_force_failure CHECK (number = 0)")
        try:
            self.assert_rejected(lambda: self.commit(project, base, intent, artifact), "PERSISTENCE_CONFLICT")
        finally:
            self.statement("ALTER TABLE revisions DROP CONSTRAINT nb_test_force_failure")
        self.assertTrue(finalized_path.is_file())
        self.artifacts.verify(artifact)
        self.assertEqual(self.store.get_project(project.project_id).head_revision_id, base.revision_id)
        self.assertEqual(self.store.get_execution(intent.execution_id).status, "PREPARED")
        self.assertEqual(len(self.store.list_revisions(project.project_id)), 1)
        self.assertEqual(self.statement("SELECT count(*) FROM artifacts WHERE artifact_id = %s",
                                        (artifact.artifact_id,)), [(0,)])
        recovered = self.commit(project, base, intent, artifact, store=self.new_store())
        self.assertEqual(recovered.number, 1)
        self.assertEqual(self.store.get_execution(intent.execution_id).result_revision_id, recovered.revision_id)

    def test_retry_after_caller_loses_commit_result_returns_durable_result(self):
        project, base = self.import_fixture()
        intent, artifact = self.prepare_move(project, base)
        # Deliberately discard the response; this is not an OS/PostgreSQL crash claim.
        self.commit(project, base, intent, artifact)
        known_revision_id = self.new_store().get_execution(intent.execution_id).result_revision_id
        replay = self.commit(project, base, intent, artifact, store=self.new_store())
        self.assertEqual(replay.revision_id, known_revision_id)
        self.assertEqual(len(self.new_store().list_revisions(project.project_id)), 2)

    def test_reopened_connections_retain_projects_revisions_and_execution_state(self):
        project, base = self.import_fixture()
        intent, artifact = self.prepare_move(project, base)
        revision = self.commit(project, base, intent, artifact)
        reopened = self.new_store()
        self.assertEqual(reopened.get_revision(base.revision_id), base)
        self.assertEqual(reopened.get_revision(revision.revision_id), revision)
        self.assertEqual(reopened.get_project(project.project_id).head_revision_id, revision.revision_id)
        self.assertEqual(reopened.get_execution(intent.execution_id).result_revision_id, revision.revision_id)
        self.assertEqual(self.artifacts.read_bytes(revision.artifact), b"SYNTHETIC V1")


if __name__ == "__main__":
    unittest.main()
