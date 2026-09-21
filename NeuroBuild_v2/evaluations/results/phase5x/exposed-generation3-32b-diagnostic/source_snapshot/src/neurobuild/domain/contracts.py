"""Phase 1 value contracts. Internal lengths are metres in project-world XY."""

from dataclasses import dataclass, replace
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
import json
from pathlib import PurePosixPath
import re
from uuid import UUID

from .errors import DomainError


def _require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise DomainError(code, message)


def _ids(*values: UUID) -> None:
    _require(all(isinstance(value, UUID) for value in values), "INVALID_ID", "Entity IDs must be UUID values")


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _digest(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _decimal_key(value: Decimal) -> str:
    """Canonical without normalize()/arithmetic, which use ambient precision."""
    if value.is_zero():
        return "0"
    sign, digits, exponent = value.as_tuple()
    digits = list(digits)
    while digits[-1] == 0:
        digits.pop()
        exponent += 1
    return ("-" if sign else "") + "".join(map(str, digits)) + "e" + str(exponent)


class LengthUnit(StrEnum):
    M = "m"
    CM = "cm"
    MM = "mm"


@dataclass(frozen=True)
class Length:
    """Source numeric value/unit retained; conversion never delegates to an LLM."""

    value: Decimal
    unit: LengthUnit

    def __post_init__(self) -> None:
        _require(isinstance(self.value, Decimal) and self.value.is_finite(), "INVALID_LENGTH", "Length requires a finite Decimal")
        _require(isinstance(self.unit, LengthUnit), "UNSUPPORTED_UNIT", "Only m, cm and mm are supported")

    @property
    def metres(self) -> Decimal:
        sign, digits, exponent = self.value.as_tuple()
        shift = {LengthUnit.M: 0, LengthUnit.CM: -2, LengthUnit.MM: -3}[self.unit]
        return Decimal((sign, digits, exponent + shift))


@dataclass(frozen=True)
class MoveFurniture:
    """One target, same storey, project-world XY displacement; no Z/rotation/scale."""

    dx: Length
    dy: Length
    coordinate_frame: str = "PROJECT_WORLD_XY"
    kind: str = "MOVE_FURNITURE"

    def __post_init__(self) -> None:
        _require(type(self.dx) is Length and type(self.dy) is Length, "INVALID_LENGTH", "Both axes require Length values")
        _require(self.kind == "MOVE_FURNITURE" and self.coordinate_frame == "PROJECT_WORLD_XY", "UNSUPPORTED_OPERATION", "Only project-world XY MOVE_FURNITURE is supported")
        _require(not (self.dx.value.is_zero() and self.dy.value.is_zero()), "NO_MOVEMENT", "A movement must change at least one axis")


class RequirementStatus(StrEnum):
    READY = "READY"
    CLARIFICATION = "CLARIFICATION"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class SemanticRequirement:
    """Semantic output contains a description, never an invented IFC GlobalId."""

    requirement_id: UUID
    project_id: UUID
    base_revision_id: UUID
    source_text: str
    target_description: str
    status: RequirementStatus
    operation: MoveFurniture | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        _ids(self.requirement_id, self.project_id, self.base_revision_id)
        _require(_text(self.source_text) and isinstance(self.target_description, str), "INVALID_REQUIREMENT", "Source text and an unmodified target description are required")
        _require(isinstance(self.status, RequirementStatus), "INVALID_REQUIREMENT", "An explicit requirement status is required")
        if self.status is RequirementStatus.READY:
            valid = _text(self.target_description) and type(self.operation) is MoveFurniture and self.reason is None
        else:
            valid = self.operation is None and _text(self.reason)
        _require(valid, "INVALID_REQUIREMENT", "Only READY can carry an executable operation; other statuses require a reason")


@dataclass(frozen=True)
class Target:
    """Resolved inventory identity. Syntax validation does not prove IFC membership."""

    global_id: str
    storey_global_id: str
    ifc_type: str = "IfcFurniture"

    def __post_init__(self) -> None:
        for value in (self.global_id, self.storey_global_id):
            _require(isinstance(value, str) and re.fullmatch(r"[0-3][0-9A-Za-z_$]{21}", value) is not None, "INVALID_TARGET", "Target and storey require IFC compressed GlobalIds")
        _require(self.ifc_type == "IfcFurniture", "UNSUPPORTED_OPERATION", "Only IfcFurniture is supported")
        _require(self.global_id != self.storey_global_id, "INVALID_TARGET", "Furniture and storey identities must differ")


@dataclass(frozen=True)
class ArtifactRef:
    """Reference to an immutable full snapshot, not a filesystem write capability."""

    artifact_id: UUID
    sha256: str
    size_bytes: int
    storage_key: str

    def __post_init__(self) -> None:
        _ids(self.artifact_id)
        _require(_digest(self.sha256), "INVALID_ARTIFACT", "Artifact SHA256 must be lowercase hexadecimal")
        _require(type(self.size_bytes) is int and self.size_bytes > 0, "INVALID_ARTIFACT", "Artifact size must be a positive integer")
        _require(_text(self.storage_key), "INVALID_ARTIFACT", "A relative storage key is required")
        path = PurePosixPath(self.storage_key)
        _require(not path.is_absolute() and ".." not in path.parts and "\\" not in self.storage_key and str(path) == self.storage_key and path.parts != () and not any(ord(c) < 32 for c in self.storage_key), "INVALID_ARTIFACT", "Storage key must be a canonical relative POSIX path")


@dataclass(frozen=True)
class Revision:
    revision_id: UUID
    project_id: UUID
    number: int
    artifact: ArtifactRef
    parent_revision_id: UUID | None = None
    ifc_schema: str = "IFC4"

    def __post_init__(self) -> None:
        _ids(self.revision_id, self.project_id)
        if self.parent_revision_id is not None:
            _ids(self.parent_revision_id)
        _require(type(self.number) is int and self.number >= 0, "INVALID_REVISION", "Revision number must be a nonnegative integer")
        _require((self.number == 0) == (self.parent_revision_id is None) and self.parent_revision_id != self.revision_id, "INVALID_REVISION", "Only revision zero has no parent; self-parenting is forbidden")
        _require(type(self.artifact) is ArtifactRef and self.ifc_schema == "IFC4", "INVALID_REVISION", "Revision requires an IFC4 full snapshot reference")


@dataclass(frozen=True)
class Project:
    project_id: UUID
    name: str
    head_revision_id: UUID | None = None

    def __post_init__(self) -> None:
        _ids(self.project_id)
        if self.head_revision_id is not None:
            _ids(self.head_revision_id)
        _require(_text(self.name), "INVALID_PROJECT", "Project name is required")


def validate_project_head(project: Project, head: Revision | None) -> None:
    _require(type(project) is Project and (head is None or type(head) is Revision), "INVALID_HEAD", "Expected a project and its current revision")
    if head is None:
        _require(project.head_revision_id is None, "INVALID_HEAD", "Project head is missing")
    else:
        _require(head.project_id == project.project_id, "PROJECT_MISMATCH", "Head belongs to a different project")
        _require(project.head_revision_id == head.revision_id, "INVALID_HEAD", "Supplied head does not match project head")


@dataclass(frozen=True)
class TargetConfirmation:
    confirmation_id: UUID
    project_id: UUID
    base_revision_id: UUID
    requirement_id: UUID
    target: Target
    confirmed: bool

    def __post_init__(self) -> None:
        _ids(self.confirmation_id, self.project_id, self.base_revision_id, self.requirement_id)
        _require(type(self.target) is Target and type(self.confirmed) is bool, "INVALID_CONFIRMATION", "Target confirmation requires one inventory target and an explicit boolean")


@dataclass(frozen=True)
class Proposal:
    proposal_id: UUID
    project_id: UUID
    base_revision_id: UUID
    requirement_id: UUID
    target_confirmation_id: UUID
    target: Target
    operation: MoveFurniture

    def __post_init__(self) -> None:
        _ids(self.proposal_id, self.project_id, self.base_revision_id, self.requirement_id, self.target_confirmation_id)
        _require(type(self.target) is Target and type(self.operation) is MoveFurniture, "INVALID_PROPOSAL", "Proposal requires exactly one target and one supported operation")

    @property
    def fingerprint(self) -> str:
        payload = {
            "contract_version": 1,
            **{name: str(getattr(self, name)) for name in ("proposal_id", "project_id", "base_revision_id", "requirement_id", "target_confirmation_id")},
            "target": {"global_id": self.target.global_id, "storey_global_id": self.target.storey_global_id, "ifc_type": self.target.ifc_type},
            "operation": {"kind": self.operation.kind, "coordinate_frame": self.operation.coordinate_frame},
        }
        for axis in ("dx", "dy"):
            length = getattr(self.operation, axis)
            payload["operation"][axis] = {"value": _decimal_key(length.value), "unit": length.unit.value, "metres": _decimal_key(length.metres)}
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")).hexdigest()


@dataclass(frozen=True)
class ProposalApproval:
    approval_id: UUID
    project_id: UUID
    base_revision_id: UUID
    proposal_id: UUID
    proposal_fingerprint: str
    approved: bool

    def __post_init__(self) -> None:
        _ids(self.approval_id, self.project_id, self.base_revision_id, self.proposal_id)
        _require(_digest(self.proposal_fingerprint) and type(self.approved) is bool, "INVALID_APPROVAL", "Approval requires an exact proposal fingerprint and an explicit boolean")


def require_apply_authorization(
    project: Project,
    current_head: Revision,
    confirmation: TargetConfirmation | None,
    proposal: Proposal,
    approval: ProposalApproval | None,
    already_applied: bool = False,
) -> None:
    """Pure guard; repositories must recheck under a transaction/head CAS at Apply."""
    _require(type(already_applied) is bool, "INVALID_EXECUTION", "Duplicate state must be an explicit boolean")
    _require(not already_applied, "ALREADY_APPLIED", "This proposal has already been applied")
    validate_project_head(project, current_head)
    _require(type(current_head) is Revision and type(proposal) is Proposal, "INVALID_PROPOSAL", "Apply requires a current revision and a proposal")
    _require(proposal.project_id == project.project_id, "PROJECT_MISMATCH", "Proposal belongs to a different project")
    _require(proposal.base_revision_id == current_head.revision_id, "STALE_PROPOSAL", "Proposal base no longer matches project head")
    _require(type(confirmation) is TargetConfirmation and confirmation.confirmed, "TARGET_NOT_CONFIRMED", "Explicit target confirmation is required")
    _require(confirmation.project_id == project.project_id, "PROJECT_MISMATCH", "Target confirmation belongs to a different project")
    _require((confirmation.confirmation_id, confirmation.base_revision_id, confirmation.requirement_id, confirmation.target) == (proposal.target_confirmation_id, proposal.base_revision_id, proposal.requirement_id, proposal.target), "CONFIRMATION_MISMATCH", "Target confirmation does not match this proposal")
    _require(type(approval) is ProposalApproval and approval.approved, "PROPOSAL_NOT_APPROVED", "Separate explicit proposal approval is required")
    _require(approval.project_id == project.project_id, "PROJECT_MISMATCH", "Approval belongs to a different project")
    _require((approval.proposal_id, approval.base_revision_id, approval.proposal_fingerprint) == (proposal.proposal_id, proposal.base_revision_id, proposal.fingerprint), "APPROVAL_MISMATCH", "Approval does not match the exact proposal content and base")


class ExecutionStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class Execution:
    execution_id: UUID
    project_id: UUID
    proposal_id: UUID
    base_revision_id: UUID
    status: ExecutionStatus = ExecutionStatus.PENDING
    result_revision_id: UUID | None = None
    error_code: str | None = None

    def __post_init__(self) -> None:
        _ids(self.execution_id, self.project_id, self.proposal_id, self.base_revision_id)
        _require(isinstance(self.status, ExecutionStatus), "INVALID_EXECUTION", "An explicit execution status is required")
        if self.result_revision_id is not None:
            _ids(self.result_revision_id)
        if self.status is ExecutionStatus.SUCCEEDED:
            valid = self.result_revision_id is not None and self.result_revision_id != self.base_revision_id and self.error_code is None
        elif self.status is ExecutionStatus.FAILED:
            valid = self.result_revision_id is None and _text(self.error_code)
        else:
            valid = self.result_revision_id is None and self.error_code is None
        _require(valid, "INVALID_EXECUTION", "Execution outcome does not match its status")

    def transition(self, status: ExecutionStatus, *, result_revision_id: UUID | None = None, error_code: str | None = None) -> "Execution":
        allowed = {
            ExecutionStatus.PENDING: {ExecutionStatus.RUNNING, ExecutionStatus.FAILED},
            ExecutionStatus.RUNNING: {ExecutionStatus.SUCCEEDED, ExecutionStatus.FAILED},
            ExecutionStatus.SUCCEEDED: set(),
            ExecutionStatus.FAILED: set(),
        }
        _require(isinstance(status, ExecutionStatus) and status in allowed[self.status], "INVALID_STATE_TRANSITION", "Execution transition is not allowed")
        return replace(self, status=status, result_revision_id=result_revision_id, error_code=error_code)
