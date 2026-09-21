"""Acceptance tests for Phase 1 contracts; no DB, IFC engine, or GPU needed."""

from dataclasses import replace
from decimal import Decimal, localcontext
import unittest
from uuid import UUID

from neurobuild.domain.contracts import (
    ArtifactRef,
    Execution,
    ExecutionStatus,
    Length,
    LengthUnit,
    MoveFurniture,
    Project,
    Proposal,
    ProposalApproval,
    RequirementStatus,
    Revision,
    SemanticRequirement,
    Target,
    TargetConfirmation,
    require_apply_authorization,
    validate_project_head,
)
from neurobuild.domain.errors import DomainError


def identifier(number: int) -> UUID:
    return UUID(int=number)


def move(dx: str = "1", dy: str = "0") -> MoveFurniture:
    return MoveFurniture(Length(Decimal(dx), LengthUnit.M), Length(Decimal(dy), LengthUnit.M))


class LengthAndOperationTests(unittest.TestCase):
    def test_unit_conversion_is_exact_and_signed(self):
        cases = (
            ("1.25", LengthUnit.M, "1.25"),
            ("30", LengthUnit.CM, "0.30"),
            ("-250", LengthUnit.MM, "-0.250"),
            ("0.001", LengthUnit.MM, "0.000001"),
            ("123456789012345678901234567890", LengthUnit.MM,
             "123456789012345678901234567.890"),
        )
        for value, unit, expected in cases:
            with self.subTest(value=value, unit=unit):
                self.assertEqual(Length(Decimal(value), unit).metres, Decimal(expected))

    def test_conversion_does_not_depend_on_ambient_decimal_precision(self):
        with localcontext() as context:
            context.prec = 6
            length = Length(Decimal("12345.6789"), LengthUnit.MM)
            self.assertEqual(length.metres, Decimal("12.3456789"))

    def test_only_explicit_finite_decimal_inputs_are_accepted(self):
        invalid = (
            True, False, 1, 0.25, "1", None,
            Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"), Decimal("-Infinity"),
        )
        for value in invalid:
            with self.subTest(value=repr(value)):
                with self.assertRaises(DomainError):
                    Length(value, LengthUnit.M)

    def test_unsupported_unit_is_rejected(self):
        with self.assertRaises(DomainError):
            Length(Decimal("1"), "foot")

    def test_xy_move_requires_a_real_displacement(self):
        for dx, dy in (("0", "0"), ("-0", "0.000")):
            with self.subTest(dx=dx, dy=dy):
                with self.assertRaises(DomainError):
                    move(dx, dy)
        self.assertEqual(move("0", "-0.25").dy.metres, Decimal("-0.25"))

    def test_scope_cannot_be_widened_by_operation_or_coordinate_frame(self):
        for override in ({"kind": "ROTATE_FURNITURE"}, {"coordinate_frame": "VIEWER_RIGHT"}):
            with self.subTest(override=override):
                with self.assertRaises(DomainError):
                    replace(move(), **override)


class RequirementTests(unittest.TestCase):
    def requirement(self, **overrides):
        values = {
            "requirement_id": identifier(1),
            "project_id": identifier(2),
            "base_revision_id": identifier(3),
            "source_text": "  회의실 입구 책상 말고 창가의 파란 책상을 X축 양의 방향으로 1m 옮겨줘.  ",
            "target_description": "회의실 입구 책상 말고 창가의 파란 책상",
            "status": RequirementStatus.READY,
            "operation": move(),
        }
        values.update(overrides)
        return SemanticRequirement(**values)

    def test_source_and_target_description_are_preserved_verbatim(self):
        source = "  회의실 입구 책상 말고 창가의 파란 책상을 X축 양의 방향으로 1m 옮겨줘.  "
        target = "  회의실 입구 책상 말고 창가의 파란 책상  "
        requirement = self.requirement(source_text=source, target_description=target)
        self.assertEqual(requirement.source_text, source)
        self.assertEqual(requirement.target_description, target)

    def test_ready_requirement_needs_target_and_operation_without_rejection_reason(self):
        for override in ({"operation": None}, {"target_description": " \t"}, {"reason": "unknown"}):
            with self.subTest(override=override):
                with self.assertRaises(DomainError):
                    self.requirement(**override)

    def test_ambiguous_and_unsupported_requirements_never_carry_executable_operations(self):
        for status in (RequirementStatus.CLARIFICATION, RequirementStatus.UNSUPPORTED):
            with self.subTest(status=status):
                requirement = self.requirement(status=status, operation=None, reason="DIRECTION_UNSPECIFIED")
                self.assertIsNone(requirement.operation)
                with self.assertRaises(DomainError):
                    self.requirement(status=status, operation=move(), reason="DIRECTION_UNSPECIFIED")
                with self.assertRaises(DomainError):
                    self.requirement(status=status, operation=None, reason=None)


class ReviewAndApplyTests(unittest.TestCase):
    def setUp(self):
        self.artifact = ArtifactRef(identifier(10), "a" * 64, 120, "ifc/v0.ifc")
        self.head = Revision(identifier(11), identifier(12), 0, self.artifact)
        self.project = Project(identifier(12), "Synthetic review project", self.head.revision_id)
        self.target = Target("0" + "a" * 21, "1" + "b" * 21)
        self.confirmation = TargetConfirmation(
            identifier(13), self.project.project_id, self.head.revision_id,
            identifier(14), self.target, True,
        )
        self.proposal = Proposal(
            identifier(15), self.project.project_id, self.head.revision_id,
            identifier(14), self.confirmation.confirmation_id, self.target, move(),
        )
        self.approval = ProposalApproval(
            identifier(16), self.project.project_id, self.head.revision_id,
            self.proposal.proposal_id, self.proposal.fingerprint, True,
        )

    def authorize(self, **overrides):
        values = {
            "project": self.project,
            "current_head": self.head,
            "confirmation": self.confirmation,
            "proposal": self.proposal,
            "approval": self.approval,
        }
        values.update(overrides)
        return require_apply_authorization(**values)

    def assert_denied(self, code, **overrides):
        with self.assertRaises(DomainError) as caught:
            self.authorize(**overrides)
        self.assertEqual(caught.exception.code, code)

    def test_bound_confirmation_and_separate_approval_allow_apply(self):
        self.assertIsNone(self.authorize())

    def test_confirmation_never_substitutes_for_proposal_approval(self):
        self.assert_denied("PROPOSAL_NOT_APPROVED", approval=None)
        self.assert_denied("PROPOSAL_NOT_APPROVED", approval=replace(self.approval, approved=False))

    def test_unconfirmed_target_cannot_be_applied_even_with_approval(self):
        self.assert_denied("TARGET_NOT_CONFIRMED", confirmation=None)
        self.assert_denied("TARGET_NOT_CONFIRMED", confirmation=replace(self.confirmation, confirmed=False))

    def test_review_flags_require_booleans_instead_of_truthy_inputs(self):
        for value in (1, "true", "false", None):
            with self.subTest(value=value):
                with self.assertRaises(DomainError):
                    replace(self.confirmation, confirmed=value)
                with self.assertRaises(DomainError):
                    replace(self.approval, approved=value)

    def test_project_binding_is_checked_for_every_record(self):
        records = {
            "current_head": self.head,
            "confirmation": self.confirmation,
            "proposal": self.proposal,
            "approval": self.approval,
        }
        for name, record in records.items():
            with self.subTest(record=name):
                self.assert_denied("PROJECT_MISMATCH", **{name: replace(record, project_id=identifier(99))})

    def test_target_confirmation_is_bound_to_base_requirement_identity_and_target(self):
        changes = (
            {"confirmation_id": identifier(91)},
            {"base_revision_id": identifier(92)},
            {"requirement_id": identifier(93)},
            {"target": Target("2" + "c" * 21, self.target.storey_global_id)},
            {"target": Target(self.target.global_id, "2" + "c" * 21)},
        )
        for change in changes:
            with self.subTest(change=change):
                self.assert_denied("CONFIRMATION_MISMATCH", confirmation=replace(self.confirmation, **change))

    def test_approval_is_bound_to_base_proposal_and_exact_content(self):
        changes = (
            {"base_revision_id": identifier(92)},
            {"proposal_id": identifier(93)},
            {"proposal_fingerprint": "f" * 64},
        )
        for change in changes:
            with self.subTest(change=change):
                self.assert_denied("APPROVAL_MISMATCH", approval=replace(self.approval, **change))
        self.assert_denied("APPROVAL_MISMATCH", proposal=replace(self.proposal, operation=move("2")))

    def test_changed_head_makes_previously_approved_proposal_stale(self):
        new_head = Revision(identifier(20), self.project.project_id, 1,
                            replace(self.artifact, artifact_id=identifier(21), storage_key="ifc/v1.ifc"),
                            self.head.revision_id)
        new_project = replace(self.project, head_revision_id=new_head.revision_id)
        self.assert_denied("STALE_PROPOSAL", project=new_project, current_head=new_head)

    def test_missing_or_wrong_project_head_is_rejected(self):
        for head_id in (None, identifier(99)):
            with self.subTest(head_id=head_id):
                self.assert_denied("INVALID_HEAD", project=replace(self.project, head_revision_id=head_id))

    def test_duplicate_apply_is_rejected(self):
        self.assert_denied("ALREADY_APPLIED", already_applied=True)

    def test_content_fingerprint_survives_decimal_context_changes(self):
        operation = move("12345.67890123456789", "-0.001")
        proposal = replace(self.proposal, operation=operation)
        expected = proposal.fingerprint
        with localcontext() as context:
            context.prec = 6
            self.assertEqual(proposal.fingerprint, expected)


class ArtifactRevisionAndExecutionTests(unittest.TestCase):
    def artifact(self, **overrides):
        values = {"artifact_id": identifier(1), "sha256": "a" * 64,
                  "size_bytes": 120, "storage_key": "ifc/example.ifc"}
        values.update(overrides)
        return ArtifactRef(**values)

    def test_artifact_paths_cannot_escape_or_alias_storage_root(self):
        for key in ("../outside.ifc", "/tmp/outside.ifc", "ifc/../outside.ifc", "./ifc/file.ifc",
                    "ifc//file.ifc", "ifc\\file.ifc", "", "ifc/file.ifc/", "ifc/\x00file.ifc"):
            with self.subTest(key=key):
                with self.assertRaises(DomainError):
                    self.artifact(storage_key=key)

    def test_snapshot_metadata_requires_valid_hash_and_positive_integer_size(self):
        for change in ({"sha256": "a" * 63}, {"sha256": "g" * 64},
                       {"size_bytes": 0}, {"size_bytes": -1},
                       {"size_bytes": True}, {"size_bytes": 1.5}):
            with self.subTest(change=change):
                with self.assertRaises(DomainError):
                    self.artifact(**change)

    def test_finalized_metadata_and_revision_cannot_be_mutated(self):
        artifact = self.artifact()
        revision = Revision(identifier(2), identifier(3), 0, artifact)
        with self.assertRaises(AttributeError):
            artifact.sha256 = "b" * 64
        with self.assertRaises(AttributeError):
            revision.artifact = self.artifact(artifact_id=identifier(99))

    def test_initial_and_child_revision_lineage_are_explicit(self):
        cases = (
            {"number": -1}, {"number": True},
            {"number": 0, "parent_revision_id": identifier(8)},
            {"number": 1, "parent_revision_id": None},
            {"number": 1, "parent_revision_id": identifier(2)},
            {"ifc_schema": "IFC2X3"},
        )
        for change in cases:
            with self.subTest(change=change):
                values = {"revision_id": identifier(2), "project_id": identifier(3),
                          "number": 0, "artifact": self.artifact()}
                values.update(change)
                with self.assertRaises(DomainError):
                    Revision(**values)

    def test_project_head_cannot_reference_another_project(self):
        head = Revision(identifier(2), identifier(3), 0, self.artifact())
        project = Project(identifier(3), "Test", head.revision_id)
        self.assertIsNone(validate_project_head(project, head))
        with self.assertRaises(DomainError):
            validate_project_head(replace(project, project_id=identifier(9)), head)
        with self.assertRaises(DomainError):
            validate_project_head(project, None)
        self.assertIsNone(validate_project_head(replace(project, head_revision_id=None), None))

    def test_execution_has_explicit_transitions_and_terminal_results(self):
        pending = Execution(identifier(1), identifier(2), identifier(3), identifier(4))
        running = pending.transition(ExecutionStatus.RUNNING)
        succeeded = running.transition(ExecutionStatus.SUCCEEDED, result_revision_id=identifier(5))
        self.assertEqual(pending.status, ExecutionStatus.PENDING)
        self.assertEqual(succeeded.result_revision_id, identifier(5))
        for status in ExecutionStatus:
            with self.subTest(terminal_next=status):
                with self.assertRaises(DomainError):
                    succeeded.transition(status)
        with self.assertRaises(DomainError):
            pending.transition(ExecutionStatus.SUCCEEDED, result_revision_id=identifier(5))
        with self.assertRaises(DomainError):
            running.transition(ExecutionStatus.SUCCEEDED)

    def test_failed_execution_carries_error_without_result_revision(self):
        pending = Execution(identifier(1), identifier(2), identifier(3), identifier(4))
        failed = pending.transition(ExecutionStatus.FAILED, error_code="UNSUPPORTED_PLACEMENT")
        self.assertIsNone(failed.result_revision_id)
        self.assertEqual(failed.error_code, "UNSUPPORTED_PLACEMENT")
        with self.assertRaises(DomainError):
            failed.transition(ExecutionStatus.RUNNING)
        with self.assertRaises(DomainError):
            pending.transition(ExecutionStatus.FAILED)

    def test_domain_errors_do_not_echo_untrusted_inputs(self):
        sentinel = "PRIVATE_SENTINEL_739a"
        with self.assertRaises(DomainError) as caught:
            self.artifact(storage_key="../" + sentinel)
        self.assertNotIn(sentinel, str(caught.exception))
        self.assertNotIn("Traceback", str(caught.exception))
        self.assertTrue(caught.exception.code)

    def test_target_requires_ifc_furniture_and_valid_compressed_identifiers(self):
        for args in (("invented", "1" + "b" * 21),
                     ("4" + "a" * 21, "1" + "b" * 21),
                     ("0" + "a" * 21, "invalid-storey")):
            with self.subTest(args=args):
                with self.assertRaises(DomainError):
                    Target(*args)
        with self.assertRaises(DomainError):
            Target("0" + "a" * 21, "1" + "b" * 21, ifc_type="IfcWall")


if __name__ == "__main__":
    unittest.main()
