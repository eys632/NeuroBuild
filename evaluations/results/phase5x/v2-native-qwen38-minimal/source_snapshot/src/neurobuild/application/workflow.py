"""Synchronous renovation slice with separate target and proposal decisions.

Review authority is held in this process only. Phase 7 will persist human review
and enqueue jobs; revision/artifact/execution intent persistence is already durable.
"""

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, replace
from enum import StrEnum
from hashlib import sha256
from threading import RLock
from uuid import UUID, uuid4

from neurobuild.domain.contracts import (
    ArtifactRef, Length, MoveFurniture, Proposal, ProposalApproval, RequirementStatus,
    Revision, SemanticRequirement, TargetConfirmation, require_apply_authorization,
)
from neurobuild.domain.errors import DomainError
from neurobuild.infrastructure.ifc_engine import IfcEngine, InventoryItem
from neurobuild.infrastructure.persistence import PostgresStore


class WorkflowStatus(StrEnum):
    WAIT_CLARIFICATION = "WAIT_CLARIFICATION"
    UNSUPPORTED = "UNSUPPORTED"
    WAIT_TARGET = "WAIT_TARGET"
    TARGET_CONFIRMED = "TARGET_CONFIRMED"
    WAIT_APPROVAL = "WAIT_APPROVAL"
    APPROVED = "APPROVED"
    APPLIED = "APPLIED"
    TARGET_REJECTED = "TARGET_REJECTED"
    PROPOSAL_REJECTED = "PROPOSAL_REJECTED"


@dataclass(frozen=True)
class Workflow:
    workflow_id: UUID
    requirement: SemanticRequirement
    status: WorkflowStatus
    inventory: tuple[InventoryItem, ...]
    confirmation: TargetConfirmation | None = None
    proposal: Proposal | None = None
    approval: ProposalApproval | None = None
    execution_id: UUID | None = None
    result_revision_id: UUID | None = None
    error_code: str | None = None


def _require(condition, code, message):
    if not condition:
        raise DomainError(code, message)


def _ids(*values):
    _require(all(isinstance(value, UUID) for value in values), "INVALID_ID", "Expected UUID values")


def _requirement_copy(requirement):
    _require(type(requirement) is SemanticRequirement, "INVALID_REQUIREMENT", "A SemanticRequirement is required")
    operation = requirement.operation
    if operation is not None:
        _require(type(operation) is MoveFurniture, "INVALID_REQUIREMENT", "A supported operation is required")
        _require(type(operation.dx) is Length and type(operation.dy) is Length,
                 "INVALID_REQUIREMENT", "Operation axes require validated Length values")
        operation = MoveFurniture(Length(operation.dx.value, operation.dx.unit),
                                  Length(operation.dy.value, operation.dy.unit),
                                  operation.coordinate_frame, operation.kind)
    return deepcopy(SemanticRequirement(requirement.requirement_id, requirement.project_id, requirement.base_revision_id,
                                        requirement.source_text, requirement.target_description, requirement.status,
                                        operation, requirement.reason))


class RenovationService:
    """Owns review records; callers pass identifiers and explicit decisions only."""

    def __init__(self, store: PostgresStore, engine: IfcEngine) -> None:
        self.store, self.engine = store, engine
        self._registry_lock = RLock()
        self._workflows: dict[UUID, Workflow] = {}
        self._locks: dict[UUID, RLock] = {}

    @contextmanager
    def _locked(self, workflow_id):
        _ids(workflow_id)
        with self._registry_lock:
            lock = self._locks.get(workflow_id)
        _require(lock is not None, "WORKFLOW_NOT_FOUND", "Workflow does not exist in this service instance")
        with lock:
            yield self._workflows[workflow_id]

    def _save(self, workflow, **changes):
        result = replace(workflow, **deepcopy(changes))
        with self._registry_lock:
            self._workflows[workflow.workflow_id] = result
        return result

    def _base(self, requirement, *, current=True):
        project = self.store.get_project(requirement.project_id)
        base = self.store.get_revision(requirement.base_revision_id)
        _require(base.project_id == project.project_id, "PROJECT_MISMATCH", "Base revision belongs to a different project")
        if current:
            _require(project.head_revision_id == base.revision_id, "STALE_PROPOSAL", "Requirement base no longer matches project head")
        return project, base

    def _finalize(self, data, artifact_id):
        expected = ArtifactRef(artifact_id, sha256(data).hexdigest(), len(data), f"objects/{artifact_id}.ifc")
        try:
            actual = self.store.artifacts.put_bytes(data, artifact_id=artifact_id)
        except DomainError as error:
            if error.code != "ARTIFACT_EXISTS":
                raise
        else:
            _require(actual == expected, "ARTIFACT_CORRUPT", "Artifact finalization returned unexpected metadata")
        # In particular, never derive expected bytes from orphan inventory.
        self.store.artifacts.verify(expected)
        return expected

    def import_ifc(self, project_id: UUID, source: bytes, execution_id: UUID) -> Revision:
        _ids(project_id, execution_id)
        # Invalid IFC must not reserve an execution or create a final artifact.
        self.engine.inventory(source)
        fingerprint = sha256(source).hexdigest()
        intent = self.store.prepare_execution(execution_id, project_id, None, None, fingerprint)
        artifact = self._finalize(source, intent.artifact_id)
        return self.store.import_revision(project_id, artifact, execution_id)

    def begin(self, requirement: SemanticRequirement) -> Workflow:
        requirement = _requirement_copy(requirement)
        _, base = self._base(requirement)
        inventory = ()
        if requirement.status is RequirementStatus.READY:
            inventory = self.engine.inventory(self.store.artifacts.read_bytes(base.artifact))
            status = WorkflowStatus.WAIT_TARGET
        elif requirement.status is RequirementStatus.CLARIFICATION:
            status = WorkflowStatus.WAIT_CLARIFICATION
        else:
            status = WorkflowStatus.UNSUPPORTED
        workflow = Workflow(uuid4(), requirement, status, inventory)
        with self._registry_lock:
            self._workflows[workflow.workflow_id] = workflow
            self._locks[workflow.workflow_id] = RLock()
        return deepcopy(workflow)

    def get(self, workflow_id: UUID) -> Workflow:
        with self._locked(workflow_id) as workflow:
            return deepcopy(workflow)

    def confirm_target(self, workflow_id: UUID, global_id: str, confirmed: bool) -> Workflow:
        _require(type(confirmed) is bool, "INVALID_CONFIRMATION", "Target confirmation must be an explicit boolean")
        with self._locked(workflow_id) as workflow:
            _require(workflow.status is WorkflowStatus.WAIT_TARGET, "INVALID_WORKFLOW_STATE", "Workflow is not waiting for a target decision")
            self._base(workflow.requirement)
            matches = [item.target for item in workflow.inventory if item.target.global_id == global_id]
            _require(len(matches) == 1, "IFC_TARGET_NOT_FOUND", "Select one target from the actual base revision inventory")
            req = workflow.requirement
            confirmation = TargetConfirmation(uuid4(), req.project_id, req.base_revision_id,
                                              req.requirement_id, matches[0], confirmed)
            status = WorkflowStatus.TARGET_CONFIRMED if confirmed else WorkflowStatus.TARGET_REJECTED
            return deepcopy(self._save(workflow, confirmation=confirmation, status=status, error_code=None))

    def create_proposal(self, workflow_id: UUID) -> Workflow:
        with self._locked(workflow_id) as workflow:
            _require(workflow.status is WorkflowStatus.TARGET_CONFIRMED, "INVALID_WORKFLOW_STATE", "A confirmed target is required before proposal creation")
            self._base(workflow.requirement)
            req, confirmation = workflow.requirement, workflow.confirmation
            _require(confirmation is not None and confirmation.confirmed, "TARGET_NOT_CONFIRMED", "Explicit target confirmation is required")
            proposal = Proposal(uuid4(), req.project_id, req.base_revision_id, req.requirement_id,
                                confirmation.confirmation_id, confirmation.target, req.operation)
            return deepcopy(self._save(workflow, proposal=proposal, status=WorkflowStatus.WAIT_APPROVAL, error_code=None))

    def approve_proposal(
        self, workflow_id: UUID, proposal_id: UUID, fingerprint: str, approved: bool,
    ) -> Workflow:
        _ids(proposal_id)
        _require(type(approved) is bool, "INVALID_APPROVAL", "Proposal approval must be an explicit boolean")
        with self._locked(workflow_id) as workflow:
            _require(workflow.status is WorkflowStatus.WAIT_APPROVAL, "INVALID_WORKFLOW_STATE", "Workflow is not waiting for proposal approval")
            self._base(workflow.requirement)
            proposal = workflow.proposal
            _require(proposal.proposal_id == proposal_id and proposal.fingerprint == fingerprint,
                     "APPROVAL_MISMATCH", "Approval must identify the exact stored proposal content")
            approval = ProposalApproval(uuid4(), proposal.project_id, proposal.base_revision_id,
                                        proposal.proposal_id, proposal.fingerprint, approved)
            status = WorkflowStatus.APPROVED if approved else WorkflowStatus.PROPOSAL_REJECTED
            return deepcopy(self._save(workflow, approval=approval, status=status, error_code=None))

    @staticmethod
    def _review_authority(workflow):
        """Content authorization independent of today's head, also for exact replay."""
        req, confirmation, proposal, approval = workflow.requirement, workflow.confirmation, workflow.proposal, workflow.approval
        _require(req.status is RequirementStatus.READY, "INVALID_WORKFLOW_STATE", "Only a ready requirement can be applied")
        _require(type(confirmation) is TargetConfirmation and confirmation.confirmed,
                 "TARGET_NOT_CONFIRMED", "Explicit target confirmation is required")
        _require(type(proposal) is Proposal and type(approval) is ProposalApproval and approval.approved,
                 "PROPOSAL_NOT_APPROVED", "Separate explicit proposal approval is required")
        _require(workflow.status in (WorkflowStatus.APPROVED, WorkflowStatus.APPLIED),
                 "INVALID_WORKFLOW_STATE", "Workflow cannot apply in its current state")
        expected = (req.project_id, req.base_revision_id, req.requirement_id)
        _require((proposal.project_id, proposal.base_revision_id, proposal.requirement_id) == expected
                 and (confirmation.project_id, confirmation.base_revision_id, confirmation.requirement_id) == expected
                 and proposal.operation == req.operation
                 and proposal.target_confirmation_id == confirmation.confirmation_id
                 and proposal.target == confirmation.target
                 and any(item.target == proposal.target for item in workflow.inventory),
                 "CONFIRMATION_MISMATCH", "Proposal differs from its original requirement and confirmed inventory target")
        _require((approval.project_id, approval.base_revision_id, approval.proposal_id, approval.proposal_fingerprint)
                 == (proposal.project_id, proposal.base_revision_id, proposal.proposal_id, proposal.fingerprint),
                 "APPROVAL_MISMATCH", "Stored approval does not match the exact proposal")

    def _existing_intent(self, workflow, execution_id):
        try:
            intent = self.store.get_execution(execution_id)
        except DomainError as error:
            if error.code == "EXECUTION_NOT_FOUND":
                return None
            raise
        proposal = workflow.proposal
        _require((intent.execution_id, intent.project_id, intent.base_revision_id, intent.proposal_id,
                  intent.payload_fingerprint, intent.artifact_id)
                 == (execution_id, proposal.project_id, proposal.base_revision_id, proposal.proposal_id,
                     proposal.fingerprint, execution_id),
                 "IDEMPOTENCY_CONFLICT", "Execution key belongs to different workflow content")
        return intent

    @staticmethod
    def _result_binding(workflow, base, expected, result):
        _require(result.project_id == base.project_id and result.parent_revision_id == base.revision_id
                 and result.number == base.number + 1 and (expected is None or result.artifact == expected)
                 and (workflow.result_revision_id is None or workflow.result_revision_id == result.revision_id),
                 "IDEMPOTENCY_CONFLICT", "Committed result does not match this exact approved operation")

    def apply(self, workflow_id: UUID, execution_id: UUID) -> Revision:
        _ids(execution_id)
        with self._locked(workflow_id) as workflow:
            self._review_authority(workflow)
            _require(workflow.execution_id is None or workflow.execution_id == execution_id,
                     "IDEMPOTENCY_CONFLICT", "Retry must use the workflow's original execution ID")
            workflow = self._save(workflow, execution_id=execution_id, error_code=None)
            try:
                return self._apply(workflow, execution_id)
            except DomainError as error:
                self._save(workflow, error_code=error.code)
                raise
            except Exception:
                self._save(workflow, error_code="WORKFLOW_EXECUTION_FAILED")
                raise DomainError("WORKFLOW_EXECUTION_FAILED", "Execution response unavailable; retry with the same execution ID") from None

    def _apply(self, workflow, execution_id):
        proposal = workflow.proposal
        project, base = self._base(workflow.requirement, current=False)
        intent = self._existing_intent(workflow, execution_id)
        committed = intent is not None and intent.status == "COMMITTED"
        if not committed:
            _require(workflow.status is not WorkflowStatus.APPLIED, "IDEMPOTENCY_CONFLICT", "Applied workflow is missing its committed execution")
            _require(project.head_revision_id is not None, "INVALID_HEAD", "Project no longer has a head revision")
            current_head = self.store.get_revision(project.head_revision_id)
            require_apply_authorization(project, current_head, workflow.confirmation, proposal, workflow.approval)
        if committed:
            # No fresh Apply: the immutable committed reference is authoritative.
            # Engine changes/failures must not block delivery of a known result.
            result = self.store.get_revision(intent.result_revision_id)
            self._result_binding(workflow, base, None, result)
            _require(result.artifact.artifact_id == intent.artifact_id,
                     "IDEMPOTENCY_CONFLICT", "Committed artifact does not match the execution reservation")
            self.store.artifacts.verify(result.artifact)
        else:
            source = self.store.artifacts.read_bytes(base.artifact)
            output = self.engine.move_furniture(source, proposal.target, proposal.operation)
            expected = ArtifactRef(execution_id, sha256(output).hexdigest(), len(output), f"objects/{execution_id}.ifc")
            intent = self.store.prepare_execution(execution_id, proposal.project_id, proposal.base_revision_id,
                                                  proposal.proposal_id, proposal.fingerprint)
            artifact = self._finalize(output, intent.artifact_id)
            result = self.store.commit_revision(proposal.project_id, proposal.base_revision_id, artifact,
                                                execution_id, proposal.proposal_id,
                                                payload_fingerprint=proposal.fingerprint)
            self._result_binding(workflow, base, expected, result)
        self._save(workflow, status=WorkflowStatus.APPLIED, result_revision_id=result.revision_id, error_code=None)
        return result
