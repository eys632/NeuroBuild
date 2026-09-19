"""Strict, source-grounded boundary for local-model semantic extraction.

The model classifies meaning; this module validates evidence and converts units.
Grounding does not prove semantic correctness or authorize target selection/apply.
JSON Schema constrains generation shape; the cross-field/source checks here are
additional mandatory checks. No model response or reasoning is logged.
"""

from decimal import Decimal
import json
import re
import unicodedata
from uuid import UUID

from neurobuild.domain.contracts import (
    Length, LengthUnit, MoveFurniture, RequirementStatus, SemanticRequirement,
)
from neurobuild.domain.errors import DomainError


SCHEMA_VERSION = "1.0"
MAX_SOURCE_CHARS = 16000
MAX_RESPONSE_CHARS = 16384
_DECIMAL = re.compile(r"[+-]?[0-9]{1,16}(?:\.[0-9]{1,12})?", re.ASCII)
_QUANTITY = re.compile(
    r"(?<![\dA-Za-z_.,/+\-])([+-]?[0-9]+(?:\.[0-9]+)?)\s*"
    r"(mm|cm|m|밀리미터|센티미터|미터)(?![A-Za-z0-9_/²³^*]|제곱)",
)
_UNIT = {"m": "m", "미터": "m", "cm": "cm", "센티미터": "cm", "mm": "mm", "밀리미터": "mm"}
_AXIS = re.compile(
    r"(?<![A-Za-z0-9_])([+-]?)([XY])(?:\s*(?:축|axis)(?![A-Za-z])|(?!\w))",
    re.IGNORECASE,
)
_POSITIVE = re.compile(r"양의|양수|\bpositive\b", re.IGNORECASE)
_NEGATIVE = re.compile(r"음의|음수|\bnegative\b", re.IGNORECASE)


def _fail(code: str = "INVALID_MODEL_OUTPUT") -> None:
    messages = {
        "INVALID_MODEL_OUTPUT": "Model output does not satisfy the requirement contract",
        "INVALID_REQUIREMENT_INPUT": "Requirement input or context is invalid",
        "UNGROUNDED_REQUIREMENT": "Requirement evidence does not match the original request",
    }
    raise DomainError(code, messages[code])


def _object(value: object, keys: set[str]) -> dict:
    if type(value) is not dict or set(value) != keys:
        _fail()
    return value


def _string(value: object, maximum: int, *, empty: bool = False) -> str:
    if (type(value) is not str or len(value) > maximum
            or (not empty and not value.strip())
            or any(ord(char) == 0 or 0xD800 <= ord(char) <= 0xDFFF for char in value)):
        _fail()
    return value


def _pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            _fail()
        result[key] = value
    return result


def _constant(_: str) -> None:
    _fail()


def _numeric_component(char: str) -> bool:
    # Recognize unsupported typography as a boundary, never normalize it into
    # the supported ASCII decimal grammar. Marks/control characters cannot
    # split a numeric expression into apparently independent ASCII numbers.
    category = unicodedata.category(char)
    return (char.isnumeric() or char.isspace() or char in "+-/*^eE"
            or category[0] in "PSMC")


def _punctuation_delimiter(char: str) -> bool:
    # Punctuation is scanned generically but only known harmless delimiters
    # are allowed outside a numeric token. Po includes modifiers such as %.
    return (char in ".,:;!?\"'、。"
            or unicodedata.category(char) in ("Ps", "Pe", "Pi", "Pf"))


def _quantity_boundary(source: str, start: int, end: int) -> bool:
    left, right = start, end
    while left > 0 and _numeric_component(source[left - 1]):
        left -= 1
    while right < len(source) and _numeric_component(source[right]):
        right += 1
    outside = source[left:start] + source[end:right]
    # Commas/periods/whitespace can delimit clauses, but a second number,
    # arithmetic operator or unsupported sign cannot be silently discarded.
    # A terminal e/E can be the end of an ordinary word such as 'positive'.
    # An exponent's coefficient or sign is still rejected by this same scan.
    return all(char.isspace() or char in "eE" or _punctuation_delimiter(char)
               for char in outside)


def _axis_boundary(source: str, start: int, end: int, quantity_start: int) -> bool:
    # Walk wrappers and whitespace too: cutting '-(X축)' down to 'X축' must
    # not discard the sign. Ordinary quote/parenthesis delimiters are allowed.
    left = start
    while left > 0:
        previous = source[left - 1]
        if previous.isspace():
            left -= 1
            continue
        category = unicodedata.category(previous)
        if (previous in "+-/*^" or category[0] in "SMC"
                or (category[0] == "P" and not _punctuation_delimiter(previous))
                or (left == start and previous.isnumeric())):
            return False
        if not (previous.isspace() or category[0] == "P"):
            break
        left -= 1
    # A non-ASCII sign after the axis is unsupported too. An ASCII sign may
    # legitimately begin the following complete quantity (e.g. X축 +1m).
    right = end
    while right < len(source) and right != quantity_start:
        following = source[right]
        if following.isspace():
            right += 1
            continue
        category = unicodedata.category(following)
        if (following in "+-/*^" or category[0] in "SMC"
                or (category[0] == "P" and not _punctuation_delimiter(following))):
            return False
        if not (following.isspace() or category[0] == "P"):
            break
        right += 1
    return True


def _whole_source_tokens(evidence: str, quantity: re.Match, axis: re.Match,
                         instruction: str, source: str) -> bool:
    """The same original evidence occurrence must contain whole axis/quantity tokens."""
    source_quantities = {candidate.span() for candidate in _QUANTITY.finditer(source)}
    source_axes = {candidate.span() for candidate in _AXIS.finditer(source)}
    instruction_offset = source.find(instruction)
    while instruction_offset >= 0:
        evidence_offset = instruction.find(evidence)
        while evidence_offset >= 0:
            offset = instruction_offset + evidence_offset
            quantity_span = offset + quantity.start(), offset + quantity.end()
            axis_span = offset + axis.start(), offset + axis.end()
            if (quantity_span in source_quantities and axis_span in source_axes
                    and _quantity_boundary(source, *quantity_span)
                    and _axis_boundary(source, *axis_span, quantity_span[0])):
                return True
            evidence_offset = instruction.find(evidence, evidence_offset + 1)
        instruction_offset = source.find(instruction, instruction_offset + 1)
    return False


def _axis_length(value: object, axis: str, source: str, original_source: str) -> Length:
    item = _object(value, {"value", "unit", "evidence"})
    lexical = _string(item["value"], 30)
    if _DECIMAL.fullmatch(lexical) is None or item["unit"] not in ("m", "cm", "mm"):
        _fail()
    evidence = _string(item["evidence"], 512)
    if evidence not in source:
        _fail("UNGROUNDED_REQUIREMENT")
    axes = list(_AXIS.finditer(evidence))
    quantities = list(_QUANTITY.finditer(evidence))
    if len(axes) != 1 or axes[0][2].lower() != axis or len(quantities) != 1:
        _fail("UNGROUNDED_REQUIREMENT")
    quantity = quantities[0]
    if (any(char.isnumeric() for char in evidence[:quantity.start()] + evidence[quantity.end():])
            or not _whole_source_tokens(evidence, quantity, axes[0], source, original_source)):
        _fail("UNGROUNDED_REQUIREMENT")
    original, source_unit = quantity.groups()
    # A sign may be expressed in words. The original numeric spelling and unit
    # must otherwise survive unchanged: e.g. 250mm must never become 0.25m here.
    if original.lstrip("+-") != lexical.lstrip("+-") or _UNIT[source_unit] != item["unit"]:
        _fail("UNGROUNDED_REQUIREMENT")
    signs = set()
    if original.startswith(("+", "-")):
        signs.add(original[0])
    if axes[0][1]:
        signs.add(axes[0][1])
    if _POSITIVE.search(evidence):
        signs.add("+")
    if _NEGATIVE.search(evidence):
        signs.add("-")
    # Unsigned 'X축 1m' is deliberately not proof of the positive direction.
    # A missing/contradictory direction must be clarified, never guessed.
    expected_sign = "-" if lexical.startswith("-") else "+"
    if signs != {expected_sign}:
        _fail("UNGROUNDED_REQUIREMENT")
    decimal = Decimal(lexical)
    if not decimal.is_finite():
        _fail()
    return Length(decimal, LengthUnit(item["unit"]))


def parse_requirement(
    response_text: str, *, source_text: str, requirement_id: UUID,
    project_id: UUID, base_revision_id: UUID, axis_convention: str | None = None,
) -> SemanticRequirement:
    """Decode one final JSON object into a non-authorizing domain requirement.

    IDs and original text are supplied by trusted application code. The only
    accepted coordinate context is ``project_xy``; None allows non-READY output.
    For READY, each non-null axis needs exact source evidence containing that
    explicit axis, numeric spelling, unit and direction. A null axis becomes 0m
    only when the other axis has passed those checks. Arbitrary natural-language
    entailment (conditions, exclusions, negation, multiple changes) remains the
    model's separately evaluated responsibility; this validator is not an NLP
    classifier. The later human target confirmation and exact proposal approval
    remain mandatory regardless of this result.
    """
    if (type(source_text) is not str or not source_text.strip()
            or len(source_text) > MAX_SOURCE_CHARS
            or any(ord(char) == 0 or 0xD800 <= ord(char) <= 0xDFFF for char in source_text)
            or axis_convention not in (None, "project_xy")
            or not all(type(value) is UUID for value in (requirement_id, project_id, base_revision_id))):
        _fail("INVALID_REQUIREMENT_INPUT")
    if type(response_text) is not str or not response_text or len(response_text) > MAX_RESPONSE_CHARS:
        _fail()
    try:
        output = json.loads(response_text, object_pairs_hook=_pairs, parse_constant=_constant)
    except (ValueError, RecursionError) as exc:
        if isinstance(exc, DomainError):
            raise
        _fail()
    output = _object(output, {"schema_version", "decision", "target_text", "operation", "reason"})
    if output["schema_version"] != SCHEMA_VERSION or output["decision"] not in ("READY", "CLARIFICATION", "UNSUPPORTED"):
        _fail()
    status = RequirementStatus(output["decision"])
    target = _string(output["target_text"], 1024, empty=status is not RequirementStatus.READY)
    if target and target not in source_text:
        _fail("UNGROUNDED_REQUIREMENT")
    if status is not RequirementStatus.READY:
        if output["operation"] is not None:
            _fail()
        reason = _string(output["reason"], 512)
        return SemanticRequirement(requirement_id, project_id, base_revision_id, source_text, target, status, reason=reason)
    if output["reason"] is not None:
        _fail()
    if axis_convention != "project_xy":
        _fail("UNGROUNDED_REQUIREMENT")
    operation = _object(output["operation"], {"kind", "coordinate_frame", "instruction_text", "dx", "dy"})
    if operation["kind"] != "MOVE_FURNITURE" or operation["coordinate_frame"] != "PROJECT_WORLD_XY":
        _fail()
    instruction = _string(operation["instruction_text"], 4096)
    if instruction not in source_text or target not in instruction:
        _fail("UNGROUNDED_REQUIREMENT")
    if operation["dx"] is None and operation["dy"] is None:
        _fail()
    lengths = {
        axis: _axis_length(operation[field], axis, instruction, source_text)
        for axis, field in (("x", "dx"), ("y", "dy")) if operation[field] is not None
    }
    # Work on the model's explicitly selected *current whole instruction*, not
    # every axis in historical/background text. The model must not omit a second
    # current axis and rely on our zero-fill to silently drop that component.
    if {match[2].lower() for match in _AXIS.finditer(instruction)} != set(lengths):
        _fail("UNGROUNDED_REQUIREMENT")
    if all(value.value.is_zero() for value in lengths.values()):
        _fail()
    movement = MoveFurniture(lengths.get("x", Length(Decimal("0"), LengthUnit.M)),
                             lengths.get("y", Length(Decimal("0"), LengthUnit.M)))
    return SemanticRequirement(requirement_id, project_id, base_revision_id, source_text, target, status, operation=movement)
