"""Phase 4 real-PostgreSQL/IFC workflow acceptance; no durable review claim."""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import hashlib
import os
from pathlib import Path
import tempfile
from threading import Barrier
import unittest
from unittest.mock import patch
from uuid import uuid4

from neurobuild.domain.contracts import (
    Length, LengthUnit, MoveFurniture, ProposalApproval, RequirementStatus, SemanticRequirement,
)
from neurobuild.domain.errors import DomainError
from tests.ifc_fixtures import build_fixture, global_id


TEST_DSN = os.environ.get("NEUROBUILD_TEST_DSN")
PROJECT_ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(TEST_DSN, "NEUROBUILD_TEST_DSN is required for real workflow integration")
class WorkflowIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        from psycopg import sql
        from psycopg.conninfo import conninfo_to_dict, make_conninfo
        from neurobuild.application.workflow import RenovationService, WorkflowStatus
        from neurobuild.infrastructure.artifacts import LocalArtifactStore
        from neurobuild.infrastructure.ifc_engine import IfcEngine
        from neurobuild.infrastructure.persistence import PostgresStore

        connection = conninfo_to_dict(TEST_DSN)
        host = connection.get("host", "")
        if (not host.startswith("/") or connection.get("hostaddr") or connection.get("service")
                or not Path(host).resolve().is_relative_to((PROJECT_ROOT / "var").resolve())):
            raise RuntimeError("Workflow tests require this project's private Unix socket")
        if not connection.get("dbname") or not connection.get("user"):
            raise RuntimeError("Workflow tests require explicit database and user names")
        cls.psycopg, cls.sql = psycopg, sql
        cls.service_type, cls.status = RenovationService, WorkflowStatus
        cls.store_type, cls.artifact_type, cls.engine_type = PostgresStore, LocalArtifactStore, IfcEngine
        cls.dsn = make_conninfo(TEST_DSN, connect_timeout="5", options="-c statement_timeout=10000")

    def setUp(self):
        self.schema = "nb_test_" + uuid4().hex
        self.created_schema = False
        with self.psycopg.connect(self.dsn, autocommit=True) as connection:
            connection.execute(self.sql.SQL("CREATE SCHEMA {}").format(self.sql.Identifier(self.schema)))
        self.created_schema = True
        self.addCleanup(self.drop_owned_schema)
        parent = PROJECT_ROOT / "var" / "tests" / "workflow"
        parent.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix="nb_test_", dir=parent)
        self.addCleanup(temporary.cleanup)
        self.artifacts = self.artifact_type(Path(temporary.name) / "artifacts")
        self.store = self.store_type(self.dsn, self.artifacts, schema=self.schema)
        self.store.migrate()
        self.engine = self.engine_type()
        self.service = self.service_type(self.store, self.engine)
        self.fixture = build_fixture("mm", storey_translation=(10, -20, 3), storey_angle_degrees=25)
        self.source = self.fixture.source()

    def drop_owned_schema(self):
        if not self.created_schema or not self.schema.startswith("nb_test_") or len(self.schema) != 40:
            raise RuntimeError("Refusing to drop a schema not created by this test")
        with self.psycopg.connect(self.dsn, autocommit=True) as connection:
            connection.execute(self.sql.SQL("DROP SCHEMA {} CASCADE").format(self.sql.Identifier(self.schema)))
        self.created_schema = False

    def statement(self, query, values=()):
        with self.psycopg.connect(self.dsn, autocommit=True) as connection:
            connection.execute(self.sql.SQL("SET search_path TO {}, pg_catalog").format(self.sql.Identifier(self.schema)))
            cursor = connection.execute(query, values)
            return cursor.fetchall() if cursor.description else None

    def imported_project(self):
        project = self.store.create_project("Synthetic workflow project")
        revision = self.service.import_ifc(project.project_id, self.source, uuid4())
        return self.store.get_project(project.project_id), revision

    def requirement(self, project, base, **changes):
        values = {
            "requirement_id": uuid4(), "project_id": project.project_id,
            "base_revision_id": base.revision_id,
            "source_text": "창가 파란 책상을 X축 양의 방향으로 1m, Y축 음의 방향으로 25cm 옮겨줘.",
            "target_description": "창가 파란 책상", "status": RequirementStatus.READY,
            "operation": MoveFurniture(Length(Decimal("1"), LengthUnit.M),
                                       Length(Decimal("-25"), LengthUnit.CM)),
        }
        values.update(changes)
        return SemanticRequirement(**values)

    def approved_workflow(self, project=None, base=None):
        if project is None:
            project, base = self.imported_project()
        workflow = self.service.begin(self.requirement(project, base))
        workflow = self.service.confirm_target(workflow.workflow_id, self.fixture.target_id, True)
        workflow = self.service.create_proposal(workflow.workflow_id)
        workflow = self.service.approve_proposal(workflow.workflow_id, workflow.proposal.proposal_id,
                                                 workflow.proposal.fingerprint, True)
        return project, base, workflow

    def assert_rejected(self, callback, code=None):
        with self.assertRaises(DomainError) as caught:
            callback()
        if code is not None:
            self.assertEqual(caught.exception.code, code)

    def test_real_ifc_to_separate_reviews_to_v1_preserves_source_snapshot(self):
        project, base = self.imported_project()
        workflow = self.service.begin(self.requirement(project, base))
        self.assertEqual(workflow.status, self.status.WAIT_TARGET)
        self.assertEqual({item.target.global_id for item in workflow.inventory},
                         {self.fixture.target_id, self.fixture.other_id})
        workflow = self.service.confirm_target(workflow.workflow_id, self.fixture.target_id, True)
        self.assertEqual(workflow.status, self.status.TARGET_CONFIRMED)
        self.assertIsNone(workflow.approval)
        workflow = self.service.create_proposal(workflow.workflow_id)
        self.assertEqual(workflow.status, self.status.WAIT_APPROVAL)
        self.assertIsNone(workflow.approval)
        workflow = self.service.approve_proposal(workflow.workflow_id, workflow.proposal.proposal_id,
                                                 workflow.proposal.fingerprint, True)
        self.assertEqual(workflow.status, self.status.APPROVED)
        result = self.service.apply(workflow.workflow_id, uuid4())
        self.assertEqual(result.number, 1)
        self.assertEqual(result.parent_revision_id, base.revision_id)
        self.assertEqual(self.store.get_project(project.project_id).head_revision_id, result.revision_id)
        self.assertEqual(self.service.get(workflow.workflow_id).status, self.status.APPLIED)
        self.assertEqual(self.artifacts.read_bytes(base.artifact), self.source)
        self.assertEqual(base.artifact.sha256, hashlib.sha256(self.source).hexdigest())
        expected_output = self.engine.move_furniture(self.source, workflow.proposal.target, workflow.proposal.operation)
        self.assertEqual(self.artifacts.read_bytes(result.artifact), expected_output)

    def test_target_confirmation_and_proposal_creation_do_not_authorize_apply(self):
        project, base = self.imported_project()
        workflow = self.service.begin(self.requirement(project, base))
        self.assert_rejected(lambda: self.service.apply(workflow.workflow_id, uuid4()), "TARGET_NOT_CONFIRMED")
        workflow = self.service.confirm_target(workflow.workflow_id, self.fixture.target_id, True)
        self.assert_rejected(lambda: self.service.apply(workflow.workflow_id, uuid4()), "PROPOSAL_NOT_APPROVED")
        workflow = self.service.create_proposal(workflow.workflow_id)
        self.assert_rejected(lambda: self.service.apply(workflow.workflow_id, uuid4()), "PROPOSAL_NOT_APPROVED")
        forged = ProposalApproval(uuid4(), project.project_id, base.revision_id,
                                  workflow.proposal.proposal_id, workflow.proposal.fingerprint, True)
        object.__setattr__(workflow, "approval", forged)
        object.__setattr__(workflow, "status", self.status.APPROVED)
        self.assert_rejected(lambda: self.service.apply(workflow.workflow_id, uuid4()), "PROPOSAL_NOT_APPROVED")
        self.assertEqual(self.store.get_project(project.project_id).head_revision_id, base.revision_id)
        self.assertEqual(len(self.store.list_revisions(project.project_id)), 1)

    def test_only_inventory_targets_can_be_confirmed(self):
        project, base = self.imported_project()
        workflow = self.service.begin(self.requirement(project, base))
        for target_id in (global_id(999), self.fixture.project_id, "invented-id"):
            with self.subTest(target_id=target_id):
                self.assert_rejected(lambda: self.service.confirm_target(workflow.workflow_id, target_id, True))
        self.assertIsNone(self.service.get(workflow.workflow_id).confirmation)

    def test_non_ready_requirements_cannot_create_executable_workflows(self):
        project, base = self.imported_project()
        for requirement_status, expected_status in (
            (RequirementStatus.CLARIFICATION, self.status.WAIT_CLARIFICATION),
            (RequirementStatus.UNSUPPORTED, self.status.UNSUPPORTED),
        ):
            with self.subTest(status=requirement_status):
                workflow = self.service.begin(self.requirement(project, base, status=requirement_status,
                                                                 operation=None, reason="NEEDS_REVIEW"))
                self.assertEqual(workflow.status, expected_status)
                self.assert_rejected(lambda: self.service.confirm_target(workflow.workflow_id, self.fixture.target_id, True))
                self.assert_rejected(lambda: self.service.create_proposal(workflow.workflow_id))
                self.assert_rejected(lambda: self.service.apply(workflow.workflow_id, uuid4()))
        self.assertEqual(len(self.store.list_revisions(project.project_id)), 1)

    def test_review_rejection_is_terminal_without_implicit_approval(self):
        project, base = self.imported_project()
        workflow = self.service.begin(self.requirement(project, base))
        rejected = self.service.confirm_target(workflow.workflow_id, self.fixture.target_id, False)
        self.assertEqual(rejected.status, self.status.TARGET_REJECTED)
        self.assert_rejected(lambda: self.service.create_proposal(workflow.workflow_id))
        workflow = self.service.begin(self.requirement(project, base))
        workflow = self.service.confirm_target(workflow.workflow_id, self.fixture.target_id, True)
        workflow = self.service.create_proposal(workflow.workflow_id)
        rejected = self.service.approve_proposal(workflow.workflow_id, workflow.proposal.proposal_id,
                                                 workflow.proposal.fingerprint, False)
        self.assertEqual(rejected.status, self.status.PROPOSAL_REJECTED)
        self.assert_rejected(lambda: self.service.apply(workflow.workflow_id, uuid4()))

    def test_approval_binds_exact_proposal_identity_and_content(self):
        project, base = self.imported_project()
        workflow = self.service.begin(self.requirement(project, base))
        workflow = self.service.confirm_target(workflow.workflow_id, self.fixture.target_id, True)
        workflow = self.service.create_proposal(workflow.workflow_id)
        for proposal_id, fingerprint in ((uuid4(), workflow.proposal.fingerprint),
                                         (workflow.proposal.proposal_id, "f" * 64)):
            with self.subTest(proposal_id=proposal_id, fingerprint=fingerprint):
                self.assert_rejected(lambda: self.service.approve_proposal(
                    workflow.workflow_id, proposal_id, fingerprint, True), "APPROVAL_MISMATCH")
        self.assertIsNone(self.service.get(workflow.workflow_id).approval)

    def test_mutated_returned_snapshots_cannot_forge_service_authority(self):
        project, base, workflow = self.approved_workflow()
        original = self.service.get(workflow.workflow_id)
        object.__setattr__(workflow.proposal.operation.dx, "value", Decimal("999"))
        object.__setattr__(workflow.approval, "proposal_fingerprint", workflow.proposal.fingerprint)
        authority = self.service.get(workflow.workflow_id)
        self.assertEqual(authority.proposal.operation.dx.metres, Decimal("1"))
        self.assertEqual(authority.proposal.fingerprint, original.proposal.fingerprint)
        result = self.service.apply(workflow.workflow_id, uuid4())
        expected = self.engine.move_furniture(self.source, original.proposal.target, original.proposal.operation)
        self.assertEqual(self.artifacts.read_bytes(result.artifact), expected)
        self.assertEqual(len(self.store.list_revisions(project.project_id)), 2)

    def test_mutating_original_requirement_after_begin_does_not_change_proposal(self):
        project, base = self.imported_project()
        requirement = self.requirement(project, base)
        workflow = self.service.begin(requirement)
        object.__setattr__(requirement.operation.dx, "value", Decimal("999"))
        self.service.confirm_target(workflow.workflow_id, self.fixture.target_id, True)
        proposal = self.service.create_proposal(workflow.workflow_id).proposal
        self.assertEqual(proposal.operation.dx.metres, Decimal("1"))

    def test_requirement_identity_objects_are_detached_from_caller(self):
        project, base = self.imported_project()
        requirement = self.requirement(project, base)
        identity = str(requirement.requirement_id)
        workflow = self.service.begin(requirement)
        object.__setattr__(requirement.requirement_id, "int", uuid4().int)
        self.assertEqual(str(self.service.get(workflow.workflow_id).requirement.requirement_id), identity)

    def test_forged_nested_requirement_values_fail_with_safe_domain_error(self):
        project, base = self.imported_project()
        requirement = self.requirement(project, base)
        object.__setattr__(requirement.operation, "dx", True)
        self.assert_rejected(lambda: self.service.begin(requirement))

    def test_project_base_binding_is_checked_before_workflow_creation(self):
        first, _ = self.imported_project()
        _, other_base = self.imported_project()
        self.assert_rejected(lambda: self.service.begin(self.requirement(first, other_base)))

    def test_repeated_apply_returns_same_revision_and_rejects_another_execution_key(self):
        project, base, workflow = self.approved_workflow()
        execution_id = uuid4()
        original = self.service.apply(workflow.workflow_id, execution_id)
        repeated = self.service.apply(workflow.workflow_id, execution_id)
        self.assertEqual(original, repeated)
        self.assert_rejected(lambda: self.service.apply(workflow.workflow_id, uuid4()), "IDEMPOTENCY_CONFLICT")
        self.assertEqual(len(self.store.list_revisions(project.project_id)), 2)

    def test_stale_workflow_cannot_advance_head(self):
        project, base, first = self.approved_workflow()
        _, _, second = self.approved_workflow(project, base)
        result = self.service.apply(first.workflow_id, uuid4())
        self.assert_rejected(lambda: self.service.apply(second.workflow_id, uuid4()), "STALE_PROPOSAL")
        self.assertEqual(self.store.get_project(project.project_id).head_revision_id, result.revision_id)
        self.assertEqual(len(self.store.list_revisions(project.project_id)), 2)

    def test_old_import_and_apply_retries_never_rollback_advanced_head(self):
        project = self.store.create_project("Advanced head retry")
        import_id = uuid4()
        initial = self.service.import_ifc(project.project_id, self.source, import_id)
        project = self.store.get_project(project.project_id)
        _, _, first = self.approved_workflow(project, initial)
        first_execution = uuid4()
        middle = self.service.apply(first.workflow_id, first_execution)
        self.assertEqual(self.service.import_ifc(project.project_id, self.source, import_id), initial)
        self.assertEqual(self.store.get_project(project.project_id).head_revision_id, middle.revision_id)
        _, _, second = self.approved_workflow(self.store.get_project(project.project_id), middle)
        latest = self.service.apply(second.workflow_id, uuid4())
        self.assertEqual(self.service.apply(first.workflow_id, first_execution), middle)
        self.assertEqual(self.store.get_project(project.project_id).head_revision_id, latest.revision_id)
        self.assertEqual(len(self.store.list_revisions(project.project_id)), 3)

    def test_two_same_base_workflows_concurrently_publish_one_revision(self):
        project, base, first = self.approved_workflow()
        _, _, second = self.approved_workflow(project, base)
        barrier = Barrier(2, timeout=10)

        def apply(workflow):
            barrier.wait()
            try:
                return "committed", self.service.apply(workflow.workflow_id, uuid4())
            except DomainError as error:
                return "rejected", error.code

        with ThreadPoolExecutor(max_workers=2) as workers:
            futures = [workers.submit(apply, workflow) for workflow in (first, second)]
            results = [future.result(timeout=20) for future in futures]
        self.assertEqual(sum(state == "committed" for state, _ in results), 1)
        self.assertEqual([value for state, value in results if state == "rejected"], ["STALE_PROPOSAL"])
        self.assertEqual(len(self.store.list_revisions(project.project_id)), 2)
        self.assertEqual(self.artifacts.read_bytes(base.artifact), self.source)

    def test_invalid_import_is_rejected_before_intent_or_artifact_creation(self):
        project = self.store.create_project("Invalid import")
        self.assert_rejected(lambda: self.service.import_ifc(project.project_id, b"not an IFC document", uuid4()),
                             "IFC_INVALID")
        self.assertIsNone(self.store.get_project(project.project_id).head_revision_id)
        self.assertEqual(self.store.list_revisions(project.project_id), [])
        self.assertEqual(self.artifacts.list_artifacts(), [])
        self.assertEqual(self.statement("SELECT count(*) FROM execution_intents"), [(0,)])

    def test_import_retry_requires_same_source_for_same_execution(self):
        project = self.store.create_project("Import retry")
        execution_id = uuid4()
        original = self.service.import_ifc(project.project_id, self.source, execution_id)
        self.assertEqual(self.service.import_ifc(project.project_id, self.source, execution_id), original)
        changed = build_fixture("cm").source()
        self.assert_rejected(lambda: self.service.import_ifc(project.project_id, changed, execution_id),
                             "IDEMPOTENCY_CONFLICT")
        self.assertEqual(len(self.store.list_revisions(project.project_id)), 1)

    def test_bim_failure_preserves_head_and_retries_with_same_execution(self):
        project, base, workflow = self.approved_workflow()
        execution_id = uuid4()
        with patch.object(self.engine, "move_furniture", side_effect=DomainError("IFC_INVARIANT_VIOLATION", "Synthetic failure")):
            self.assert_rejected(lambda: self.service.apply(workflow.workflow_id, execution_id), "IFC_INVARIANT_VIOLATION")
        self.assertEqual(self.store.get_project(project.project_id).head_revision_id, base.revision_id)
        self.assertEqual(len(self.artifacts.list_artifacts()), 1)
        current = self.service.get(workflow.workflow_id)
        self.assertEqual(current.execution_id, execution_id)
        self.assertEqual(current.error_code, "IFC_INVARIANT_VIOLATION")
        self.assert_rejected(lambda: self.service.apply(workflow.workflow_id, uuid4()), "IDEMPOTENCY_CONFLICT")
        result = self.service.apply(workflow.workflow_id, execution_id)
        self.assertEqual(result.number, 1)

    def test_database_failure_retains_finalized_artifact_and_retry_reuses_it(self):
        project, base, workflow = self.approved_workflow()
        execution_id = uuid4()
        self.statement("ALTER TABLE revisions ADD CONSTRAINT nb_test_failure CHECK (number = 0)")
        try:
            self.assert_rejected(lambda: self.service.apply(workflow.workflow_id, execution_id), "PERSISTENCE_CONFLICT")
        finally:
            self.statement("ALTER TABLE revisions DROP CONSTRAINT nb_test_failure")
        self.assertEqual(self.store.get_project(project.project_id).head_revision_id, base.revision_id)
        self.assertEqual(self.store.get_execution(execution_id).status, "PREPARED")
        before_retry = self.artifacts.list_artifacts()
        self.assertEqual(len(before_retry), 2)
        result = self.service.apply(workflow.workflow_id, execution_id)
        self.assertEqual(result.number, 1)
        self.assertEqual(self.artifacts.list_artifacts(), before_retry)
        self.assertEqual(self.store.get_execution(execution_id).result_revision_id, result.revision_id)

    def test_lost_database_response_recovers_committed_revision(self):
        project, base, workflow = self.approved_workflow()
        execution_id = uuid4()
        actual_commit = self.store.commit_revision

        def lose_response(*args, **kwargs):
            actual_commit(*args, **kwargs)
            raise DomainError("PERSISTENCE_ERROR", "Synthetic loss after successful commit")

        with patch.object(self.store, "commit_revision", side_effect=lose_response):
            self.assert_rejected(lambda: self.service.apply(workflow.workflow_id, execution_id), "PERSISTENCE_ERROR")
        durable = self.store.get_execution(execution_id)
        self.assertEqual(durable.status, "COMMITTED")
        committed_result = self.store.get_revision(durable.result_revision_id)
        _, _, later_workflow = self.approved_workflow(self.store.get_project(project.project_id), committed_result)
        later_result = self.service.apply(later_workflow.workflow_id, uuid4())
        with patch.object(self.engine, "move_furniture", side_effect=DomainError("IFC_INVALID", "Engine unavailable")) as engine:
            recovered = self.service.apply(workflow.workflow_id, execution_id)
            engine.assert_not_called()
        self.assertEqual(recovered.revision_id, durable.result_revision_id)
        self.assertEqual(self.store.get_project(project.project_id).head_revision_id, later_result.revision_id)
        self.assertEqual(len(self.store.list_revisions(project.project_id)), 3)
        self.assertEqual(self.service.get(workflow.workflow_id).status, self.status.APPLIED)

    def test_new_service_does_not_claim_durable_human_reviews(self):
        _, _, workflow = self.approved_workflow()
        restarted_service = self.service_type(self.store, self.engine)
        self.assert_rejected(lambda: restarted_service.get(workflow.workflow_id), "WORKFLOW_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
