"""Explicit quote-only generation adapter; the 1.0 domain boundary is unchanged.

Quotes are never repaired or expanded. Numeric spelling comes from one exact
evidence span; existing 1.0 helpers decide whether its sign/unit are grounded.
This module does not classify meaning, select an IFC target or grant approval.
"""

from enum import StrEnum
import json
from uuid import UUID

from neurobuild.application.requirements import (
    MAX_RESPONSE_CHARS, MAX_SOURCE_CHARS, _AXIS, _QUANTITY, _UNIT,
    _axis_length, _constant, _fail, _object, _pairs, _string, parse_requirement,
)
from neurobuild.domain.contracts import Length, SemanticRequirement
from neurobuild.domain.errors import DomainError


class GenerationContract(StrEnum):
    LEGACY = "1.0"
    QUOTES = "2.0"


_KEYS = {
    "schema_version", "decision", "target_selection_quote",
    "current_instruction_quote", "dx_evidence", "dy_evidence", "reason",
}


def _validate_source(source_text: str) -> None:
    if (type(source_text) is not str or not source_text.strip()
            or len(source_text) > MAX_SOURCE_CHARS
            or any(ord(char) == 0 or 0xD800 <= ord(char) <= 0xDFFF for char in source_text)):
        _fail("INVALID_REQUIREMENT_INPUT")


def _quoted_axis(evidence: object, axis: str, instruction: str,
                 source_text: str) -> tuple[dict, Length]:
    quote = _string(evidence, 512)
    quantities = list(_QUANTITY.finditer(quote))
    if len(quantities) != 1:
        _fail("UNGROUNDED_REQUIREMENT")
    original, original_unit = quantities[0].groups()
    magnitude = original.lstrip("+-")
    # Preserve the magnitude's exact spelling and an original explicit '+'.
    # A word/axis sign may require '-' on an otherwise unsigned magnitude.
    candidates = (("+" if original.startswith("+") else "") + magnitude,
                  "-" + magnitude)
    accepted = []
    errors = []
    for lexical in candidates:
        item = {"value": lexical, "unit": _UNIT[original_unit], "evidence": quote}
        try:
            length = _axis_length(item, axis, instruction, source_text)
        except DomainError as exc:
            errors.append(exc)
        else:
            accepted.append((item, length))
    if len(accepted) != 1:
        if errors:
            raise errors[0]
        _fail("UNGROUNDED_REQUIREMENT")
    return accepted[0]


def adapt_generation_v2(response_text: str, *, source_text: str) -> str:
    """Validate 2.0 quotes and return canonical 1.0 JSON, without authority.

    The caller must still run ``parse_requirement`` with the original source,
    code-owned IDs and coordinate context. Prefer ``parse_generated_requirement``
    when a domain requirement is needed. No response-driven version selection.
    """
    _validate_source(source_text)
    if (type(response_text) is not str or not response_text
            or len(response_text) > MAX_RESPONSE_CHARS):
        _fail()
    try:
        output = json.loads(response_text, object_pairs_hook=_pairs, parse_constant=_constant)
    except (ValueError, RecursionError) as exc:
        if isinstance(exc, DomainError):
            raise
        _fail()
    output = _object(output, _KEYS)
    if (output["schema_version"] != GenerationContract.QUOTES.value
            or output["decision"] not in ("READY", "CLARIFICATION", "UNSUPPORTED")):
        _fail()
    is_ready = output["decision"] == "READY"
    target = _string(output["target_selection_quote"], 1024, empty=not is_ready)
    if target and target not in source_text:
        _fail("UNGROUNDED_REQUIREMENT")
    projected = {"schema_version": "1.0", "decision": output["decision"],
                 "target_text": target, "operation": None, "reason": None}
    if not is_ready:
        if any(output[key] is not None for key in
               ("current_instruction_quote", "dx_evidence", "dy_evidence")):
            _fail()
        projected["reason"] = _string(output["reason"], 512)
    else:
        if output["reason"] is not None:
            _fail()
        instruction = _string(output["current_instruction_quote"], 4096)
        if instruction not in source_text or target not in instruction:
            _fail("UNGROUNDED_REQUIREMENT")
        if output["dx_evidence"] is None and output["dy_evidence"] is None:
            _fail()
        values = {
            axis: _quoted_axis(output[field], axis, instruction, source_text)
            for axis, field in (("x", "dx_evidence"), ("y", "dy_evidence"))
            if output[field] is not None
        }
        if {match[2].lower() for match in _AXIS.finditer(instruction)} != set(values):
            _fail("UNGROUNDED_REQUIREMENT")
        if all(length.value.is_zero() for _, length in values.values()):
            _fail()
        projected["operation"] = {
            "kind": "MOVE_FURNITURE", "coordinate_frame": "PROJECT_WORLD_XY",
            "instruction_text": instruction,
            "dx": values["x"][0] if "x" in values else None,
            "dy": values["y"][0] if "y" in values else None,
        }
    return json.dumps(projected, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def parse_generated_requirement(
    response_text: str, *, generation_contract: GenerationContract,
    source_text: str, requirement_id: UUID, project_id: UUID,
    base_revision_id: UUID, axis_convention: str | None = None,
) -> SemanticRequirement:
    """Explicitly route one configured generation contract into the 1.0 parser."""
    if type(generation_contract) is not GenerationContract:
        _fail("INVALID_REQUIREMENT_INPUT")
    if generation_contract is GenerationContract.QUOTES:
        _validate_source(source_text)
        if (axis_convention not in (None, "project_xy")
                or not all(type(value) is UUID for value in
                           (requirement_id, project_id, base_revision_id))):
            _fail("INVALID_REQUIREMENT_INPUT")
        response_text = adapt_generation_v2(response_text, source_text=source_text)
    return parse_requirement(
        response_text, source_text=source_text, requirement_id=requirement_id,
        project_id=project_id, base_revision_id=base_revision_id,
        axis_convention=axis_convention,
    )
