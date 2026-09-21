"""Strict 3.0 facts projection, without reclassification or semantic proof.

Facts are model declarations. Exact quotes and internal consistency do not
prove completeness, currentness, target identity, or authorization. The caller
must still run the unchanged 2.0 adapter and canonical requirement parser.
"""

import json

from neurobuild.application.requirement_generation import _validate_source
from neurobuild.application.requirements import (
    MAX_RESPONSE_CHARS, _constant, _fail, _object, _pairs, _string,
)
from neurobuild.domain.errors import DomainError


_FIELDS = {"schema_version", "facts", "decision", "target_selection_quote",
           "current_instruction_quote", "dx_evidence", "dy_evidence", "reason"}
_ENUMS = {
    "intent": ("CURRENT_MOVE", "NEGATED_MOVE", "INFORMATION_ONLY", "NO_CURRENT_REQUEST", "AMBIGUOUS"),
    "condition": ("NONE", "UNRESOLVED", "AMBIGUOUS"),
    "target_class": ("FURNITURE", "NON_FURNITURE", "UNSPECIFIED"),
    "target_count": ("ONE", "MULTIPLE", "UNSPECIFIED"),
    "motion": ("ONE_RELATIVE_XY_VECTOR", "SEQUENTIAL_OR_MULTI_ACTION", "OTHER_CHANGE", "UNSPECIFIED"),
    "axis_completeness": ("EXPLICIT", "INCOMPLETE", "NOT_APPLICABLE"),
    "authority": ("NONE", "CURRENT_BYPASS_OR_OVERWRITE", "HISTORICAL_OR_QUOTED_ONLY", "AMBIGUOUS"),
}
_QUOTES = {"condition_quote": 512, "authority_quote": 512,
           "selection_scope_quote": 1024, "selection_exclusion_quote": 1024}
_READY_FACTS = {"intent": "CURRENT_MOVE", "condition": "NONE", "target_class": "FURNITURE",
                "target_count": "ONE", "motion": "ONE_RELATIVE_XY_VECTOR", "axis_completeness": "EXPLICIT"}


def _quote(value: object, maximum: int, source_text: str) -> str | None:
    if value is None:
        return None
    quote = _string(value, maximum)
    if quote.strip().lower() == "null":
        _fail()
    if quote not in source_text:
        _fail("UNGROUNDED_REQUIREMENT")
    return quote


def adapt_generation_v3(response_text: str, *, source_text: str) -> str:
    """Return 2.0 JSON with the six generated values unchanged.

    Reject contradictions in declarations; never synthesize or change the
    model's final decision. This projection does not replace 2.0 grounding.
    """
    _validate_source(source_text)
    if type(response_text) is not str or not response_text or len(response_text) > MAX_RESPONSE_CHARS:
        _fail()
    try:
        output = json.loads(response_text, object_pairs_hook=_pairs, parse_constant=_constant)
    except (ValueError, RecursionError) as exc:
        if isinstance(exc, DomainError):
            raise
        _fail()
    output = _object(output, _FIELDS)
    if (type(output["schema_version"]) is not str or output["schema_version"] != "3.0"
            or type(output["decision"]) is not str
            or output["decision"] not in ("READY", "CLARIFICATION", "UNSUPPORTED")):
        _fail()
    ready = output["decision"] == "READY"
    target = _string(output["target_selection_quote"], 1024, empty=not ready)
    if target and target not in source_text:
        _fail("UNGROUNDED_REQUIREMENT")
    if ready:
        _string(output["current_instruction_quote"], 4096)
        if output["reason"] is not None or (output["dx_evidence"] is None and output["dy_evidence"] is None):
            _fail()
        for name in ("dx_evidence", "dy_evidence"):
            if output[name] is not None:
                _string(output[name], 512)
    else:
        if any(output[name] is not None for name in ("current_instruction_quote", "dx_evidence", "dy_evidence")):
            _fail()
        _string(output["reason"], 512)
    facts = _object(output["facts"], set(_ENUMS) | set(_QUOTES))
    for name, values in _ENUMS.items():
        if type(facts[name]) is not str or facts[name] not in values:
            _fail()
    quotes = {name: _quote(facts[name], maximum, source_text) for name, maximum in _QUOTES.items()}
    for name in ("condition", "authority"):
        # NONE requires null; every other declared state needs actual evidence.
        if (facts[name] == "NONE") != (quotes[name + "_quote"] is None):
            _fail()
    for name in ("selection_scope_quote", "selection_exclusion_quote"):
        if quotes[name] is not None and quotes[name] not in target:
            _fail("UNGROUNDED_REQUIREMENT")
    if ready:
        if (any(facts[name] != expected for name, expected in _READY_FACTS.items())
                or facts["authority"] not in ("NONE", "HISTORICAL_OR_QUOTED_ONLY")):
            _fail()
    # No inverse promotion or non-READY priority engine. The original model
    # label survives projection even when later evaluation finds it incorrect.
    projected = {"schema_version": "2.0"}
    projected.update({name: output[name] for name in (
        "decision", "target_selection_quote", "current_instruction_quote", "dx_evidence", "dy_evidence", "reason",
    )})
    return json.dumps(projected, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
