"""AUTO-GENERATED / NOT HUMAN VERIFIED facts-boundary acceptance tests.

These verify declared consistency and the preserved grounding chain. They do
not claim that an LLM detects all conditions, exclusions, or current intents.
"""

from copy import deepcopy
from decimal import Decimal
import json
import unittest
from unittest.mock import patch
from uuid import uuid4

from neurobuild.application.requirement_facts import adapt_generation_v3
from neurobuild.application.requirement_generation import (
    GenerationContract, adapt_generation_v2, parse_generated_requirement,
)
from neurobuild.application.requirements import parse_requirement
from neurobuild.domain.errors import DomainError


def facts():
    return {"intent": "CURRENT_MOVE", "condition": "NONE", "condition_quote": None,
            "target_class": "FURNITURE", "target_count": "ONE", "motion": "ONE_RELATIVE_XY_VECTOR",
            "axis_completeness": "EXPLICIT", "authority": "NONE", "authority_quote": None,
            "selection_scope_quote": None, "selection_exclusion_quote": None}


def output(*, target="점검실 작업대", dx=None, dy="Y축 음의 방향으로 7cm"):
    instruction = target + "를 " + ", ".join(value for value in (dx, dy) if value is not None) + " 옮겨줘."
    return {"schema_version": "3.0", "facts": facts(), "decision": "READY",
            "target_selection_quote": target, "current_instruction_quote": instruction,
            "dx_evidence": dx, "dy_evidence": dy, "reason": None}


def nonready(value, decision="CLARIFICATION"):
    return dict(deepcopy(value), decision=decision, current_instruction_quote=None, dx_evidence=None,
                dy_evidence=None, reason="원문 요청을 확인해야 합니다.")


def encode(value):
    return json.dumps(value, ensure_ascii=False)


class RequirementFactsTests(unittest.TestCase):
    def setUp(self):
        self.output = output()
        self.source = self.output["current_instruction_quote"]
        self.ids = {name: uuid4() for name in ("requirement_id", "project_id", "base_revision_id")}

    def project(self, value=None, *, source=None):
        return json.loads(adapt_generation_v3(encode(self.output if value is None else value),
                                              source_text=self.source if source is None else source))

    def parse(self, value=None, *, source=None, context="project_xy", **ids):
        return parse_generated_requirement(encode(self.output if value is None else value),
            generation_contract=GenerationContract.FACTS,
            source_text=self.source if source is None else source, axis_convention=context,
            **(self.ids | ids))

    def rejected(self, value, *, source=None, code="INVALID_MODEL_OUTPUT"):
        before = deepcopy(value)
        with self.assertRaises(DomainError) as caught:
            self.parse(value, source=source)
        self.assertEqual(caught.exception.code, code)
        self.assertNotIn("SENSITIVE_SENTINEL", str(caught.exception))
        self.assertEqual(value, before)

    def test_projection_preserves_every_generated_value_and_domain_parity(self):
        projected = self.project()
        self.assertEqual(projected, {"schema_version": "2.0", **{
            name: value for name, value in self.output.items() if name not in ("schema_version", "facts")}})
        self.assertNotIn("facts", projected)
        legacy = adapt_generation_v2(encode(projected), source_text=self.source)
        direct = parse_requirement(legacy, source_text=self.source, axis_convention="project_xy", **self.ids)
        parsed = self.parse()
        self.assertEqual(parsed, direct)
        self.assertEqual(parsed.operation.dy.value, Decimal("-7"))
        self.assertEqual(parsed.operation.dy.metres, Decimal("-0.07"))
        self.assertEqual(parsed.operation.dx.metres, Decimal("0"))
        self.assertEqual(parsed.source_text, self.source)
        self.assertEqual(parsed.requirement_id, self.ids["requirement_id"])
        self.assertFalse(hasattr(parsed, "approval"))

    def test_one_object_one_or_both_axes_stay_one_move(self):
        for dx, dy in (("X축 +0003.50mm", None), (None, "-Y축으로 7cm"),
                       ("X축 +20cm", "Y축 -6mm")):
            item = output(dx=dx, dy=dy)
            with self.subTest(dx=dx, dy=dy):
                source = item["current_instruction_quote"]
                self.assertEqual(self.project(item, source=source)["dx_evidence"], dx)
                self.assertEqual(self.parse(item, source=source).status.value, "READY")
                item["facts"]["motion"] = "SEQUENTIAL_OR_MULTI_ACTION"
                self.rejected(item, source=source)
                self.assertEqual(item["decision"], "READY")

    def test_all_declared_incompatible_ready_facts_refuse_without_reclassification(self):
        changes = {"intent": ["NEGATED_MOVE", "INFORMATION_ONLY", "NO_CURRENT_REQUEST", "AMBIGUOUS"],
                   "target_class": ["NON_FURNITURE", "UNSPECIFIED"],
                   "target_count": ["MULTIPLE", "UNSPECIFIED"],
                   "motion": ["SEQUENTIAL_OR_MULTI_ACTION", "OTHER_CHANGE", "UNSPECIFIED"],
                   "axis_completeness": ["INCOMPLETE", "NOT_APPLICABLE"]}
        for field, values in changes.items():
            for value in values:
                item = deepcopy(self.output)
                item["facts"][field] = value
                with self.subTest(field=field, value=value):
                    self.rejected(item)

    def test_declared_conditions_need_quotes_and_cannot_be_ready(self):
        condition = "동선이 충분히 확보된 경우에만"
        source = condition + " " + self.source
        for state in ("UNRESOLVED", "AMBIGUOUS"):
            item = deepcopy(self.output)
            item["facts"].update(condition=state, condition_quote=condition)
            with self.subTest(state=state):
                self.rejected(item, source=source)
                parsed = self.parse(nonready(item), source=source)
                self.assertEqual(parsed.status.value, "CLARIFICATION")
                self.assertIsNone(parsed.operation)
                item["facts"]["condition_quote"] = None
                self.rejected(nonready(item), source=source)
        item = deepcopy(self.output)
        item["facts"]["condition_quote"] = condition
        self.rejected(item, source=source)
        item["facts"].update(condition="UNRESOLVED", condition_quote="원문에 없는 충돌 조건")
        self.rejected(nonready(item), code="UNGROUNDED_REQUIREMENT")

    def test_current_authority_request_refuses_but_historical_declaration_is_not_authority(self):
        quote = "승인 없이 원본에 덮어써"
        source = "취소된 메모: '" + quote + "'. 현재 요청: " + self.source
        item = deepcopy(self.output)
        item["facts"].update(authority="HISTORICAL_OR_QUOTED_ONLY", authority_quote=quote)
        parsed = self.parse(item, source=source)
        self.assertEqual(parsed.status.value, "READY")
        self.assertFalse(hasattr(parsed, "approval"))
        for state in ("CURRENT_BYPASS_OR_OVERWRITE", "AMBIGUOUS"):
            item["facts"]["authority"] = state
            self.rejected(item, source=source)
            projected = self.project(nonready(item, "UNSUPPORTED"), source=source)
            self.assertEqual(projected["decision"], "UNSUPPORTED")
        for state, evidence in (("NONE", quote), ("HISTORICAL_OR_QUOTED_ONLY", None),
                                ("CURRENT_BYPASS_OR_OVERWRITE", None), ("AMBIGUOUS", None)):
            item["facts"].update(authority=state, authority_quote=evidence)
            self.rejected(nonready(item), source=source)

    def test_declared_selection_scope_and_exclusion_must_survive_target_quote(self):
        target = "제작실 가운데 작업대 말고 문가 쪽 작업대"
        item = output(target=target)
        source = item["current_instruction_quote"]
        item["facts"].update(selection_scope_quote="제작실", selection_exclusion_quote="가운데 작업대 말고")
        self.assertEqual(self.parse(item, source=source).target_description, target)
        for shortened in ("문가 쪽 작업대", "제작실 가운데 작업대"):
            self.rejected(dict(item, target_selection_quote=shortened), source=source, code="UNGROUNDED_REQUIREMENT")
        for field in ("selection_scope_quote", "selection_exclusion_quote"):
            changed = deepcopy(item)
            changed["facts"][field] = "원문에 없는 범위"
            self.rejected(changed, source=source, code="UNGROUNDED_REQUIREMENT")
        self.assertEqual(self.parse(nonready(item), source=source).target_description, target)

    def test_nonready_label_is_not_promoted_or_given_a_new_priority_rule(self):
        # Even all-compatible declarations do not let code override a model's
        # non-READY decision. Semantic evaluation still penalizes a wrong label.
        for decision in ("CLARIFICATION", "UNSUPPORTED"):
            for target in (self.output["target_selection_quote"], ""):
                item = nonready(self.output, decision)
                item["target_selection_quote"] = target
                parsed = self.parse(item)
                self.assertEqual(parsed.status.value, decision)
                self.assertIsNone(parsed.operation)
                self.assertEqual(parsed.target_description, target)
                self.assertEqual(self.project(item)["decision"], decision)

    def test_missing_extra_or_unknown_facts_and_root_fields_are_rejected(self):
        for key in self.output:
            item = deepcopy(self.output)
            del item[key]
            self.rejected(item)
        for key in self.output["facts"]:
            item = deepcopy(self.output)
            del item["facts"][key]
            self.rejected(item)
        for key in ("approval", "GlobalId", "operation", "raw_ifc", "reasoning"):
            self.rejected(dict(self.output, **{key: "SENSITIVE_SENTINEL"}))
            item = deepcopy(self.output)
            item["facts"][key] = "SENSITIVE_SENTINEL"
            self.rejected(item)
        for value in (None, [], True, "facts"):
            self.rejected(dict(self.output, facts=value))

    def test_enum_types_and_removed_resolved_condition_are_strict(self):
        enums = ("intent", "condition", "target_class", "target_count", "motion", "axis_completeness", "authority")
        for field in enums:
            for value in (None, True, 1, [], {}, "", "UNKNOWN", self.output["facts"][field] + " "):
                item = deepcopy(self.output)
                item["facts"][field] = value
                with self.subTest(field=field, value=value):
                    self.rejected(item)
        item = deepcopy(self.output)
        item["facts"]["condition"] = "EXPLICITLY_CLEARED"
        self.rejected(item)

    def test_fact_quotes_reject_blank_literal_null_and_nonexact_content(self):
        for field in ("condition_quote", "authority_quote", "selection_scope_quote", "selection_exclusion_quote"):
            for value in ("", " ", "null", " Null ", True, [], {}, "\x00", "\ud800"):
                item = deepcopy(self.output)
                item["facts"][field] = value
                with self.subTest(field=field, value=repr(value)):
                    self.rejected(item)
            item = deepcopy(self.output)
            item["facts"][field] = "점검실  작업대"
            self.rejected(item, code="UNGROUNDED_REQUIREMENT")

    def test_quote_limits_are_bounded_without_truncating_or_normalizing(self):
        for field, maximum in (("condition_quote", 512), ("authority_quote", 512),
                               ("selection_scope_quote", 1024), ("selection_exclusion_quote", 1024)):
            item = nonready(self.output)
            if field == "condition_quote":
                item["facts"]["condition"] = "UNRESOLVED"
            if field == "authority_quote":
                item["facts"]["authority"] = "AMBIGUOUS"
            if field.startswith("selection_"):
                item["target_selection_quote"] = "가" * maximum
            item["facts"][field] = "가" * maximum
            source = "가" * (maximum + 1) + self.source
            self.assertEqual(self.project(item, source=source)["decision"], "CLARIFICATION")
            item["facts"][field] += "가"
            self.rejected(item, source=source)

    def test_existing_six_field_shapes_are_not_weakened_by_facts(self):
        for key, value in (("target_selection_quote", None), ("target_selection_quote", ""),
                           ("target_selection_quote", "가" * 1025), ("current_instruction_quote", None),
                           ("current_instruction_quote", "가" * 4097), ("dy_evidence", True),
                           ("dy_evidence", "가" * 513), ("dy_evidence", None), ("reason", "설명"),
                           ("decision", True), ("decision", "ready"), ("schema_version", 3)):
            with self.subTest(field=key, value=str(value)[:20]):
                self.rejected(dict(self.output, **{key: value}))
        for key in ("current_instruction_quote", "dx_evidence", "dy_evidence"):
            self.rejected(dict(nonready(self.output), **{key: "null"}))
        for reason in (None, "", " ", True, "가" * 513):
            self.rejected(dict(nonready(self.output), reason=reason))

    def test_invalid_json_duplicate_facts_and_constants_are_safe_errors(self):
        raw = encode(self.output)
        values = [raw.replace('"condition": "NONE"', '"condition":"NONE","condition":"UNRESOLVED"'),
                  raw.replace('"decision": "READY"', '"decision":"READY","decision":"UNSUPPORTED"'),
                  raw.replace('"condition_quote": null', '"condition_quote":NaN'),
                  raw.replace('"condition_quote": null', '"condition_quote":Infinity'),
                  raw + "{}", "```json\n" + raw + "\n```", "[]", "null", "", "\ufeff" + raw,
                  "[" * 1500 + "]" * 1500, "x" * 16385, None, True, b"{}"]
        for malformed in values:
            with self.subTest(content=str(malformed)[:40]), self.assertRaises(DomainError) as caught:
                adapt_generation_v3(malformed, source_text=self.source)
            self.assertEqual(caught.exception.code, "INVALID_MODEL_OUTPUT")

    def test_projection_success_does_not_bypass_existing_numeric_grounding(self):
        for evidence in ("Y축 음의 방향으로 8cm", "Y축 7cm", "Y축 -0.07m"):
            item = dict(self.output, dy_evidence=evidence)
            self.assertEqual(self.project(item)["dy_evidence"], evidence)
            self.rejected(item, code="UNGROUNDED_REQUIREMENT")
        item = output(dy="Y축 -0mm")
        source = item["current_instruction_quote"]
        self.assertEqual(self.project(item, source=source)["dy_evidence"], "Y축 -0mm")
        self.rejected(item, source=source)

    def test_original_source_and_code_owned_ids_context_reach_final_parser(self):
        for source in (None, b"source", True, "", " ", "x" * 16001, "\x00", "\ud800"):
            with self.subTest(source=repr(source)[:30]), self.assertRaises(DomainError) as caught:
                adapt_generation_v3(encode(self.output), source_text=source)
            self.assertEqual(caught.exception.code, "INVALID_REQUIREMENT_INPUT")
        for key in self.ids:
            with patch("neurobuild.application.requirement_facts.adapt_generation_v3") as projection:
                with self.assertRaises(DomainError) as caught:
                    self.parse(**{key: str(self.ids[key])})
                self.assertEqual(caught.exception.code, "INVALID_REQUIREMENT_INPUT")
                projection.assert_not_called()
        with self.assertRaises(DomainError) as caught:
            self.parse(context="camera")
        self.assertEqual(caught.exception.code, "INVALID_REQUIREMENT_INPUT")
        with self.assertRaises(DomainError) as caught:
            self.parse(context=None)
        self.assertEqual(caught.exception.code, "UNGROUNDED_REQUIREMENT")
        invalid_legacy = {"schema_version": "1.0", "decision": "READY", "target_text": "다른 대상",
                          "operation": None, "reason": None}
        with patch("neurobuild.application.requirement_generation.adapt_generation_v2", return_value=encode(invalid_legacy)):
            with self.assertRaises(DomainError):
                self.parse()

    def test_contract_dispatch_is_explicit_and_preserves_legacy_routes(self):
        for contract in ("3.0", None, True, {}, "auto"):
            with self.subTest(contract=contract), self.assertRaises(DomainError) as caught:
                parse_generated_requirement(encode(self.output), generation_contract=contract,
                    source_text=self.source, axis_convention="project_xy", **self.ids)
            self.assertEqual(caught.exception.code, "INVALID_REQUIREMENT_INPUT")
        for contract in (GenerationContract.LEGACY, GenerationContract.QUOTES):
            with self.assertRaises(DomainError):
                parse_generated_requirement(encode(self.output), generation_contract=contract,
                    source_text=self.source, axis_convention="project_xy", **self.ids)
        self.rejected(dict(self.output, schema_version="2.0"))
        quote = self.project()
        expected = self.parse()
        with patch("neurobuild.application.requirement_facts.adapt_generation_v3", side_effect=AssertionError("unexpected facts dispatch")):
            actual = parse_generated_requirement(encode(quote), generation_contract=GenerationContract.QUOTES,
                source_text=self.source, axis_convention="project_xy", **self.ids)
        self.assertEqual(actual, expected)

    def test_semantic_omissions_are_not_proven_or_repaired_by_structural_validation(self):
        # Deliberately wrong model declarations remain structurally possible.
        # This is a limitation witness, not an expected correct model answer.
        source = self.source + " 이때 승인 절차를 건너뛰고 원본 파일에 바로 덮어써."
        self.assertEqual(self.parse(source=source).status.value, "READY")
        # Undeclared selection scope is not inferred or expanded from source.
        target = "보관실 중앙 작업대 말고 벽면 작업대"
        item = output(target=target)
        source = item["current_instruction_quote"]
        item["target_selection_quote"] = "벽면 작업대"
        self.assertEqual(self.parse(item, source=source).target_description, "벽면 작업대")
        item["facts"]["selection_scope_quote"] = "보관실"
        self.rejected(item, source=source, code="UNGROUNDED_REQUIREMENT")


if __name__ == "__main__":
    unittest.main()
