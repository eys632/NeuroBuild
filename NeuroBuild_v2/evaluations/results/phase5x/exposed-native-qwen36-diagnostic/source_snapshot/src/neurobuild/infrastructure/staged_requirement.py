"""Explicit classification then decision-bound extraction; no correction or retry.

Completions are ephemeral evaluation traces, not logs or persisted model output.
Only extract() returns domain data, through the unchanged quote adapter/parser.
"""

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from uuid import UUID

from jsonschema import Draft202012Validator

from neurobuild.application.requirement_generation import GenerationContract, parse_generated_requirement
from neurobuild.domain.contracts import SemanticRequirement
from neurobuild.domain.errors import DomainError
from neurobuild.infrastructure.local_model import (
    Completion, LocalJSONCompletionClient, SamplingProfile, StructuredOutputProtocol, _error,
)


_ROOT = Path(__file__).resolve().parents[3]
_DECISIONS = ("READY", "CLARIFICATION", "UNSUPPORTED")
_FIELDS = {"schema_version", "decision", "target_selection_quote", "current_instruction_quote",
           "dx_evidence", "dy_evidence", "reason"}


def _invalid() -> None:
    raise DomainError("INVALID_MODEL_OUTPUT", "Model output does not satisfy the selected stage contract") from None


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _invalid()
        result[key] = value
    return result


def _strict_output(content: str, validator: Draft202012Validator) -> dict:
    try:
        value = json.loads(content, object_pairs_hook=_pairs, parse_constant=lambda _: _invalid())
        if type(value) is not dict or not validator.is_valid(value):
            _invalid()
        return value
    except (ValueError, TypeError, RecursionError):
        _invalid()


def canonical_schema_sha256(schema: dict) -> str:
    """Hash exact canonical schema bytes: UTF-8, sorted keys, compact JSON."""
    return sha256(json.dumps(schema, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def bind_extraction_schema(template: dict, decision: str) -> dict:
    """Restrict the fixed 2.0 branch contract before making the second request.

Reject weakened or differently shaped templates instead of accidentally
allowing a branch to repair the classifier's decision. Annotations are inert.
"""
    if type(decision) is not str or decision not in _DECISIONS or type(template) is not dict:
        _error("LOCAL_MODEL_CONFIG_INVALID")
    allowed = {"$schema", "title", "description", "type", "properties", "anyOf"}
    if (set(template) - allowed or template.get("type") != "object"
            or template.get("properties") != {"schema_version": {"type": "string", "enum": ["2.0"]}}
            or type(template.get("anyOf")) is not list or len(template["anyOf"]) != 4):
        _error("LOCAL_MODEL_CONFIG_INVALID")
    seen = set()
    selected = []
    for branch in template["anyOf"]:
        if (type(branch) is not dict or set(branch) != {"type", "additionalProperties", "required", "properties"}
                or branch["type"] != "object" or branch["additionalProperties"] is not False
                or type(branch["required"]) is not list or len(branch["required"]) != 7
                or set(branch["required"]) != _FIELDS or type(branch["properties"]) is not dict
                or set(branch["properties"]) != _FIELDS):
            _error("LOCAL_MODEL_CONFIG_INVALID")
        props = branch["properties"]
        enum = props.get("decision", {}).get("enum") if type(props.get("decision")) is dict else None
        ready = enum == ["READY"]
        if not ready and enum != ["CLARIFICATION", "UNSUPPORTED"]:
            _error("LOCAL_MODEL_CONFIG_INVALID")
        expected = {
            "schema_version": {"type": "string", "enum": ["2.0"]},
            "decision": {"type": "string", "enum": enum},
            "target_selection_quote": {"type": "string"},
            "current_instruction_quote": {"type": "string" if ready else "null"},
            "reason": {"type": "null" if ready else "string"},
        }
        if any(props[key] != value for key, value in expected.items()):
            _error("LOCAL_MODEL_CONFIG_INVALID")
        axes = tuple(props[key].get("type") if type(props[key]) is dict else None
                     for key in ("dx_evidence", "dy_evidence"))
        allowed_axes = (("string", "null"), ("null", "string"), ("string", "string")) if ready else (("null", "null"),)
        if axes not in allowed_axes:
            _error("LOCAL_MODEL_CONFIG_INVALID")
        if any(props[key] != {"type": kind} for key, kind in zip(("dx_evidence", "dy_evidence"), axes)):
            _error("LOCAL_MODEL_CONFIG_INVALID")
        if axes in seen:
            _error("LOCAL_MODEL_CONFIG_INVALID")
        seen.add(axes)
        if decision in enum:
            bound = deepcopy(branch)
            bound["properties"]["decision"]["enum"] = [decision]
            selected.append(bound)
    if len(selected) != (3 if decision == "READY" else 1):
        _error("LOCAL_MODEL_CONFIG_INVALID")
    result = deepcopy(template)
    result["anyOf"] = selected
    return result


@dataclass(frozen=True)
class StagedCompletion:
    classification: Completion | None
    extraction: Completion | None
    error_code: str | None


class LocalStagedRequirementClient:
    """Two explicit requests sharing the same safe transport configuration."""

    def __init__(
        self, base_url: str, model: str, *, timeout: float = 60.0, max_tokens: int = 768,
        classification_max_tokens: int = 128,
        prompt_path: Path | None = None, schema_path: Path | None = None,
        classification_prompt_path: Path | None = None, classification_schema_path: Path | None = None,
        protocol: StructuredOutputProtocol | str = StructuredOutputProtocol.LEGACY_GUIDED_JSON,
        sampling_profile: SamplingProfile | str = SamplingProfile.LEGACY_GREEDY,
    ) -> None:
        if type(classification_max_tokens) is not int or not 1 <= classification_max_tokens <= 128:
            _error("LOCAL_MODEL_CONFIG_INVALID")
        common = dict(timeout=timeout, protocol=protocol, sampling_profile=sampling_profile)
        self._classifier = LocalJSONCompletionClient(
            base_url, model, **common, max_tokens=classification_max_tokens,
            prompt_path=classification_prompt_path or _ROOT / "prompts/requirement_classification_v1.txt",
            schema_path=classification_schema_path or _ROOT / "schemas/requirement_classification.schema.json",
            expected_schema_version="classification-1.0",
        )
        self._extractor = LocalJSONCompletionClient(
            base_url, model, **common, max_tokens=max_tokens,
            prompt_path=prompt_path or _ROOT / "prompts/requirement_extraction_v1.txt",
            schema_path=schema_path or _ROOT / "schemas/requirement_generation_v2_decision_branches.schema.json",
            expected_schema_version="2.0",
        )
        classification = self._classifier.schema
        expected = {"schema_version": {"type": "string", "enum": ["classification-1.0"]},
                    "decision": {"type": "string", "enum": list(_DECISIONS)}}
        if (set(classification) - {"$schema", "title", "description", "type", "properties", "required", "additionalProperties"}
                or classification.get("type") != "object" or classification.get("properties") != expected
                or classification.get("required") != ["schema_version", "decision"]
                or classification.get("additionalProperties") is not False):
            _error("LOCAL_MODEL_CONFIG_INVALID")
        self._bound = {decision: bind_extraction_schema(self._extractor.schema, decision) for decision in _DECISIONS}
        self._classification_validator = Draft202012Validator(classification)
        self._validators = {decision: Draft202012Validator(schema) for decision, schema in self._bound.items()}

    @property
    def pipeline(self): return "staged_v1"

    @property
    def generation_contract(self): return GenerationContract.QUOTES

    @property
    def model(self): return self._extractor.model

    @property
    def endpoint(self): return self._extractor.endpoint

    @property
    def protocol(self): return self._extractor.protocol

    @property
    def sampling_profile(self): return self._extractor.sampling_profile

    @property
    def sampling_parameters(self): return self._extractor.sampling_parameters

    @property
    def enable_thinking(self): return self._extractor.enable_thinking

    @property
    def timeout(self): return self._extractor.timeout

    @property
    def max_tokens(self): return self._extractor.max_tokens

    @property
    def classification_max_tokens(self): return self._classifier.max_tokens

    @property
    def prompt_sha256(self): return self._extractor.prompt_sha256

    @property
    def schema_sha256(self): return self._extractor.schema_sha256

    @property
    def classification_prompt_sha256(self): return self._classifier.prompt_sha256

    @property
    def classification_schema_sha256(self): return self._classifier.schema_sha256

    @property
    def classification_schema(self): return self._classifier.schema

    @property
    def effective_schema_sha256(self):
        return {decision: canonical_schema_sha256(schema) for decision, schema in self._bound.items()}

    def schema_for_decision(self, decision: str) -> dict:
        if type(decision) is not str or decision not in _DECISIONS:
            _error("LOCAL_MODEL_CONFIG_INVALID")
        return deepcopy(self._bound[decision])

    def complete_staged(self, source_text: str, *, axis_convention: str | None = None) -> StagedCompletion:
        """Retain the first final response even if the second stage fails.

        Shape validation never changes a decision or repairs quotes. Malformed
        final content is ephemeral for metric accounting; callers must persist
        only independently schema-valid output. Interrupts are not swallowed.
        """
        classification = extraction = None
        try:
            classification = self._classifier.complete(source_text, axis_convention=axis_convention)
            decision = _strict_output(classification.content, self._classification_validator)["decision"]
            extraction = self._extractor._complete(
                source_text, axis_convention=axis_convention,
                classified_decision=decision, schema_override=self._bound[decision],
            )
            _strict_output(extraction.content, self._validators[decision])
        except DomainError as exc:
            return StagedCompletion(classification, extraction, exc.code)
        except Exception:
            # Unexpected ordinary failures must not erase an already observed
            # classifier READY. BaseException (including interrupts) propagates.
            return StagedCompletion(classification, extraction, "LOCAL_MODEL_RESPONSE_INVALID")
        return StagedCompletion(classification, extraction, None)

    def extract(
        self, source_text: str, *, requirement_id: UUID, project_id: UUID,
        base_revision_id: UUID, axis_convention: str | None = None,
    ) -> SemanticRequirement:
        if not all(type(value) is UUID for value in (requirement_id, project_id, base_revision_id)):
            _error("LOCAL_MODEL_INPUT_INVALID")
        result = self.complete_staged(source_text, axis_convention=axis_convention)
        if result.error_code is not None:
            raise DomainError(result.error_code, "Staged requirement extraction failed") from None
        if result.extraction is None:
            _invalid()
        return parse_generated_requirement(
            result.extraction.content, generation_contract=self.generation_contract,
            source_text=source_text, requirement_id=requirement_id, project_id=project_id,
            base_revision_id=base_revision_id, axis_convention=axis_convention,
        )
