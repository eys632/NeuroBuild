"""Synthetic contract tests; no model run or human-verified gold is claimed.

AUTO-GENERATED / NOT HUMAN VERIFIED. These tests exercise a hostile model-output
boundary, not the model's accuracy on natural-language conditions or negation.
"""

from copy import deepcopy
from decimal import Decimal, localcontext
import json
from pathlib import Path
import unittest
from uuid import uuid4

from neurobuild.application.requirements import parse_requirement
from neurobuild.domain.contracts import RequirementStatus
from neurobuild.domain.errors import DomainError


ROOT = Path(__file__).resolve().parents[1]


def ready(target="회의실 책상", *, dx=None, dy=None, instruction=None):
    if instruction is None:
        instruction = target + "을 " + ", ".join(item["evidence"] for item in (dx, dy) if item is not None) + " 옮겨줘."
    return {"schema_version": "1.0", "decision": "READY", "target_text": target,
            "operation": {"kind": "MOVE_FURNITURE", "coordinate_frame": "PROJECT_WORLD_XY",
                          "instruction_text": instruction, "dx": dx, "dy": dy}, "reason": None}


def axis(value="1", unit="m", evidence="X축 양의 방향으로 1m"):
    return {"value": value, "unit": unit, "evidence": evidence}


def nonready(decision="CLARIFICATION", target="회의실 책상"):
    return {"schema_version": "1.0", "decision": decision, "target_text": target,
            "operation": None, "reason": "명확한 지원 범위의 이동 요청이 필요합니다."}


class RequirementContractTests(unittest.TestCase):
    def setUp(self):
        self.ids = {"requirement_id": uuid4(), "project_id": uuid4(), "base_revision_id": uuid4()}
        self.source = "회의실 책상을 X축 양의 방향으로 1m 옮겨줘."
        self.output = ready(dx=axis())

    def parse(self, output=None, *, source=None, context="project_xy"):
        return parse_requirement(json.dumps(self.output if output is None else output, ensure_ascii=False),
                                 source_text=self.source if source is None else source,
                                 axis_convention=context, **self.ids)

    def rejected(self, output, *, source=None, context="project_xy", code=None):
        with self.assertRaises(DomainError) as caught:
            self.parse(output, source=source, context=context)
        if code:
            self.assertEqual(caught.exception.code, code)

    def test_single_explicit_axis_creates_exact_domain_units_and_zero_other_axis(self):
        result = self.parse()
        self.assertEqual(result.status, RequirementStatus.READY)
        self.assertEqual(result.source_text, self.source)
        self.assertEqual(result.target_description, "회의실 책상")
        self.assertEqual(result.requirement_id, self.ids["requirement_id"])
        self.assertEqual(result.project_id, self.ids["project_id"])
        self.assertEqual(result.base_revision_id, self.ids["base_revision_id"])
        self.assertEqual(result.operation.dx.value, Decimal("1"))
        self.assertEqual(result.operation.dx.unit.value, "m")
        self.assertEqual(result.operation.dy.metres, Decimal("0"))
        self.assertIsNone(result.reason)
        self.assertFalse(hasattr(result, "approval"))
        self.assertFalse(hasattr(result, "global_id"))

    def test_signed_unit_conversion_and_original_numeric_spelling(self):
        cases = [
            ("0.50", "m", "X축 양의 방향으로 0.50m", Decimal("0.50")),
            ("-250", "mm", "X축 음의 방향으로 250mm", Decimal("-0.250")),
            ("+30", "cm", "X축 +30cm", Decimal("0.30")),
            ("-12.500", "cm", "-X축으로 12.500센티미터", Decimal("-0.12500")),
            ("1", "m", "X axis positive 1미터", Decimal("1")),
        ]
        for lexical, unit, evidence, expected in cases:
            with self.subTest(evidence=evidence), localcontext() as context:
                context.prec = 1
                result = self.parse(ready(dx=axis(lexical, unit, evidence)),
                                    source="회의실 책상을 " + evidence + " 옮겨줘.")
                self.assertEqual(result.operation.dx.value.as_tuple(), Decimal(lexical).as_tuple())
                self.assertEqual(result.operation.dx.metres, expected)

    def test_two_explicit_axes_are_one_relative_move(self):
        x = axis("-25", "cm", "X축 -25cm")
        y = axis("150", "mm", "Y축 양의 방향으로 150mm")
        result = self.parse(ready(dx=x, dy=y), source="회의실 책상을 X축 -25cm, Y축 양의 방향으로 150mm 옮겨줘.")
        self.assertEqual(result.operation.dx.metres, Decimal("-0.25"))
        self.assertEqual(result.operation.dy.metres, Decimal("0.15"))

    def test_missing_axis_cannot_zero_fill_an_explicit_second_current_axis(self):
        source = "회의실 책상을 X축 양의 방향으로 1m, Y축 음의 방향으로 2m 옮겨줘."
        output = ready(dx=axis(), instruction=source)
        self.rejected(output, source=source, code="UNGROUNDED_REQUIREMENT")

    def test_historical_axis_is_not_confused_with_current_instruction(self):
        source = "이전 X축 +2m 지시는 취소했다. 회의실 책상을 Y축 양의 방향으로 30cm 옮겨줘."
        output = ready(dy=axis("30", "cm", "Y축 양의 방향으로 30cm"))
        result = self.parse(output, source=source)
        self.assertEqual(result.operation.dx.metres, Decimal("0"))
        self.assertEqual(result.operation.dy.metres, Decimal("0.30"))

    def test_target_label_is_not_mistaken_for_an_additional_axis(self):
        target = "회의실 X1 책상"
        source = target + "을 Y축 양의 방향으로 30cm 옮겨줘."
        output = ready(target, dy=axis("30", "cm", "Y축 양의 방향으로 30cm"))
        result = self.parse(output, source=source)
        self.assertEqual(result.operation.dx.metres, Decimal("0"))
        self.assertEqual(result.target_description, target)

    def test_evidence_cannot_come_from_superseded_instruction(self):
        current = "회의실 책상을 X축 양의 방향으로 1m 옮겨줘."
        source = "회의실 책상을 X축 양의 방향으로 2m 옮기려던 안은 폐기했다. " + current
        output = ready(dx=axis("2", "m", "X축 양의 방향으로 2m"), instruction=current)
        self.rejected(output, source=source, code="UNGROUNDED_REQUIREMENT")

    def test_full_target_span_preserves_scope_and_exclusion(self):
        target = "회의실 입구 쪽 책상 말고 창가 쪽 책상"
        source = target + "을 Y축 양의 방향으로 30cm 옮겨줘."
        output = ready(target, dy=axis("30", "cm", "Y축 양의 방향으로 30cm"))
        result = self.parse(output, source=source)
        self.assertEqual(result.target_description, target)

    def test_nonready_decisions_have_no_executable_operation(self):
        for status in ("CLARIFICATION", "UNSUPPORTED"):
            with self.subTest(status=status):
                result = self.parse(nonready(status), context=None)
                self.assertEqual(result.status.value, status)
                self.assertIsNone(result.operation)
                self.assertTrue(result.reason)

    def test_missing_target_allowed_only_for_nonready_request(self):
        result = self.parse(nonready("UNSUPPORTED", ""), source="새 설계안을 세 개 생성해 줘.", context=None)
        self.assertEqual(result.target_description, "")
        self.rejected(ready("", dx=axis()))

    def test_strict_json_rejects_duplicates_constants_fences_and_trailing_content(self):
        normal = json.dumps(self.output)
        payloads = [
            normal.replace('"decision": "READY"', '"decision":"UNSUPPORTED","decision":"READY"'),
            normal.replace('"value": "1"', '"value":"1","value":"2"'),
            normal.replace('"reason": null', '"reason": NaN'),
            normal.replace('"reason": null', '"reason": Infinity'),
            normal.replace('"reason": null', '"reason": -Infinity'),
            "```json\n" + normal + "\n```", normal + "{}", "[]", "null", "", "\ufeff" + normal,
            "[" * 1500 + "]" * 1500, "0" * 16385,
        ]
        for raw in payloads:
            with self.subTest(raw=raw[:70]), self.assertRaises(DomainError) as caught:
                parse_requirement(raw, source_text=self.source, axis_convention="project_xy", **self.ids)
            self.assertEqual(caught.exception.code, "INVALID_MODEL_OUTPUT")

    def test_unknown_keys_at_every_level_cannot_smuggle_ids_approval_or_ifc(self):
        for level, key in (("root", "GlobalId"), ("root", "approval"), ("root", "reasoning"),
                           ("root", "requirement_id"), ("operation", "raw_ifc"), ("axis", "tool_call")):
            output = deepcopy(self.output)
            target = output if level == "root" else output["operation"] if level == "operation" else output["operation"]["dx"]
            target[key] = "DO_NOT_ECHO_SECRET_SENTINEL"
            with self.subTest(level=level, key=key):
                self.rejected(output, code="INVALID_MODEL_OUTPUT")

    def test_required_shape_version_and_scalar_types_are_strict(self):
        malformed = []
        for key in self.output:
            item = deepcopy(self.output)
            del item[key]
            malformed.append(item)
        for key, value in (("schema_version", 1), ("schema_version", "2.0"), ("decision", "ready"),
                           ("decision", []), ("target_text", 2), ("target_text", "x" * 1025),
                           ("operation", []), ("reason", False)):
            item = deepcopy(self.output)
            item[key] = value
            malformed.append(item)
        for field, value in (("value", 1), ("value", True), ("unit", []), ("unit", "ft"),
                             ("evidence", []), ("evidence", "x" * 513)):
            item = deepcopy(self.output)
            item["operation"]["dx"][field] = value
            malformed.append(item)
        for item in malformed:
            with self.subTest(output=item):
                self.rejected(item)

    def test_nonready_cannot_carry_operation_and_ready_cannot_carry_reason(self):
        for status in ("CLARIFICATION", "UNSUPPORTED"):
            item = deepcopy(self.output)
            item["decision"] = status
            item["reason"] = "조건 확인이 필요합니다."
            self.rejected(item)
            for reason in (None, "", " " * 3, 5, "x" * 513):
                item = nonready(status)
                item["reason"] = reason
                self.rejected(item)
        self.rejected(dict(self.output, reason="이미 승인했다고 가정합니다."))

    def test_no_guessed_axis_context_or_movement(self):
        self.rejected(self.output, context=None, code="UNGROUNDED_REQUIREMENT")
        self.rejected(self.output, context="camera_xy", code="INVALID_REQUIREMENT_INPUT")
        self.rejected(ready())
        self.rejected(ready(dx=axis("0", "m", "X축 +0m")), source="회의실 책상을 X축 +0m 옮겨줘.")
        for field, value in (("kind", "ROTATE"), ("coordinate_frame", "LOCAL_XY")):
            item = deepcopy(self.output)
            item["operation"][field] = value
            self.rejected(item)

    def test_exact_target_and_evidence_spans_cannot_be_invented_or_normalized(self):
        for target in ("로비 책상", "회의실  책상", "회의실 책상\ud800"):
            self.rejected(ready(target, dx=axis()))
        self.rejected(ready(dx=axis(evidence="X축 양의 방향으로 2m")), code="UNGROUNDED_REQUIREMENT")

    def test_grounding_rejects_arithmetic_converted_units_and_changed_spelling(self):
        source = "회의실 책상을 X축 음의 방향으로 250.0mm 옮겨줘."
        for value, unit in (("-0.2500", "m"), ("-250", "mm"), ("-500.0", "mm"), ("-250.0", "cm")):
            with self.subTest(value=value, unit=unit):
                self.rejected(ready(dx=axis(value, unit, "X축 음의 방향으로 250.0mm")), source=source,
                              code="UNGROUNDED_REQUIREMENT")

    def test_numeric_suffix_of_unsupported_source_notation_never_becomes_a_move(self):
        cases = [("1,250mm", "250", "mm"), ("1e-3m", "3", "m"), ("1e-3m", "-3", "m"),
                 ("1/2m", "2", "m"), ("1+2m", "2", "m"), ("1 + 2m", "2", "m"),
                 ("1 250mm", "250", "mm"), ("1 - 2m", "2", "m"), ("1 * 2m", "2", "m"),
                 ("1m/s", "1", "m"), ("1m²", "1", "m"), ("1미터제곱", "1", "m")]
        for notation, value, unit in cases:
            evidence = "X축 양의 방향으로 " + notation
            source = "회의실 책상을 " + evidence + " 옮겨줘."
            with self.subTest(notation=notation, value=value):
                self.rejected(ready(dx=axis(value, unit, evidence)), source=source, code="UNGROUNDED_REQUIREMENT")

    def test_cut_evidence_cannot_hide_source_unit_suffix_or_spaced_arithmetic(self):
        cases = [
            ("회의실 책상을 X축 +1mm 옮겨줘.", "X축 +1m", "1", "m"),
            ("회의실 책상을 X축 +1m/s 옮겨줘.", "X축 +1m", "1", "m"),
            ("회의실 책상을 1 + 2m X축 양의 방향으로 옮겨줘.", "2m X축 양의 방향으로", "2", "m"),
            ("회의실 책상을 1,250mm X축 양의 방향으로 옮겨줘.", "250mm X축 양의 방향으로", "250", "mm"),
            ("회의실 책상을 1e-3m X축 양의 방향으로 옮겨줘.", "3m X축 양의 방향으로", "3", "m"),
            ("회의실 책상을 X축 +1m + 2m 옮겨줘.", "X축 +1m", "1", "m"),
        ]
        for source, evidence, value, unit in cases:
            with self.subTest(source=source):
                self.rejected(ready(dx=axis(value, unit, evidence), instruction=source), source=source,
                              code="UNGROUNDED_REQUIREMENT")

    def test_cut_instruction_still_checks_full_original_numeric_boundaries(self):
        instruction = "회의실 책상을 X축 +1m"
        output = ready(dx=axis("1", "m", "X축 +1m"), instruction=instruction)
        for source in (instruction + "m 옮겨줘.", instruction + "/s 속도로 옮겨줘.",
                       instruction + " + 2m 옮겨줘."):
            with self.subTest(source=source):
                self.rejected(output, source=source, code="UNGROUNDED_REQUIREMENT")

    def test_direction_and_axis_are_grounded_without_implicit_positive_default(self):
        cases = [
            ("1", "Y축 양의 방향으로 1m"), ("1", "X축으로 1m"),
            ("1", "X축 음의 방향으로 1m"), ("-1", "X축 양의 방향으로 1m"),
            ("1", "X축 양의 음의 방향으로 1m"), ("-1", "X축 음의 방향으로 +1m"),
            ("1", "X축 양의 방향으로 1m Y축 양의 방향으로 2m"),
            ("1", "오른쪽으로 1m"), ("1", "X축 양의 방향으로 1m 또는 2m"),
        ]
        for value, evidence in cases:
            with self.subTest(evidence=evidence):
                self.rejected(ready(dx=axis(value, "m", evidence)), source="회의실 책상을 " + evidence + " 옮겨줘.",
                              code="UNGROUNDED_REQUIREMENT")

    def test_nonfinite_exponent_expression_and_unbounded_decimal_are_rejected(self):
        for value in ("NaN", "Infinity", "-Infinity", "1e3", ".5", "1.", "1+1", "1,000", " 1", "1 ",
                      "１２", "1" * 17, "0." + "1" * 13):
            with self.subTest(value=value):
                self.rejected(ready(dx=axis(value)), code="INVALID_MODEL_OUTPUT")

    def test_invalid_source_and_code_owned_ids_fail_safely(self):
        for source in (None, "", "  ", "x" * 16001, "text\x00", "text\udfff"):
            with self.subTest(source=repr(source)[:30]), self.assertRaises(DomainError) as caught:
                parse_requirement(json.dumps(self.output), source_text=source, **self.ids)
            self.assertEqual(caught.exception.code, "INVALID_REQUIREMENT_INPUT")
        ids = dict(self.ids, project_id=str(self.ids["project_id"]))
        with self.assertRaises(DomainError) as caught:
            parse_requirement(json.dumps(self.output), source_text=self.source, **ids)
        self.assertEqual(caught.exception.code, "INVALID_REQUIREMENT_INPUT")

    def test_error_message_does_not_echo_untrusted_model_content(self):
        item = dict(self.output, reasoning="DO_NOT_ECHO_SECRET_SENTINEL")
        with self.assertRaises(DomainError) as caught:
            self.parse(item)
        self.assertNotIn("DO_NOT_ECHO_SECRET_SENTINEL", str(caught.exception))

    def test_seed20_can_be_represented_without_claiming_model_accuracy(self):
        seeds = [json.loads(line) for line in (ROOT / "evaluations/requirement_seed.jsonl").read_text().splitlines()]
        evidence = {
            "A01": ("x", "1", "m", "X축 양의 방향으로 1m"),
            "A02": ("y", "-250", "mm", "Y축 음의 방향으로 250mm"),
            "E01": ("x", "1", "m", "X축 양의 방향으로 1m"),
            "F01": ("x", "-0.5", "m", "X축 음의 방향으로 0.5m"),
            "F02": ("y", "30", "cm", "Y축 양의 방향으로 30cm"),
            "G01": ("x", "1", "m", "X축 양의 방향으로 1m"),
            "H01": ("x", "0.2", "m", "X축 양의 방향으로 0.2m"),
            "I01": ("x", "-750", "mm", "X축 음의 방향으로 750mm"),
            "I02": ("y", "40", "cm", "Y축 양의 방향으로 40cm"),
        }
        self.assertEqual(len(seeds), 20)
        for seed in seeds:
            with self.subTest(seed=seed["id"]):
                gold = seed["gold"]
                target = gold.get("target_text", "")
                if seed["id"] in evidence:
                    selected, value, unit, span = evidence[seed["id"]]
                    if seed["id"] == "F02":
                        target = "회의실 입구 쪽 책상 말고 창가 쪽 책상"
                    current = seed["input"]
                    if seed["id"] == "I02":
                        current = "최신 확정 요청은 회의실 책상을 Y축 양의 방향으로 40cm 이동하는 것 하나다."
                    payload = ready(target, instruction=current, **{"d" + selected: axis(value, unit, span)})
                    result = self.parse(payload, source=seed["input"], context=seed["context"].get("axis_convention"))
                    self.assertEqual(result.operation.dx.metres, Decimal(str(gold["dx_m"])))
                    self.assertEqual(result.operation.dy.metres, Decimal(str(gold["dy_m"])))
                else:
                    status = "CLARIFICATION" if gold["decision"] in ("clarify", "needs_context") else "UNSUPPORTED"
                    result = self.parse(nonready(status, target), source=seed["input"], context=seed["context"].get("axis_convention"))
                    self.assertIsNone(result.operation)
                    self.assertEqual(result.status.value, status)

    def test_checked_in_schema_and_prompt_are_versioned_and_do_not_grant_approval(self):
        schema = json.loads((ROOT / "schemas/semantic_requirement.schema.json").read_text())
        self.assertEqual(schema["properties"]["schema_version"]["enum"], ["1.0"])
        self.assertFalse(schema["additionalProperties"])
        prompt = (ROOT / "prompts/requirement_v1.txt").read_text()
        self.assertIn("AUTO-GENERATED / NOT HUMAN VERIFIED", prompt)
        self.assertIn("별도로", prompt)
        self.assertIn("조건부", prompt)
        self.assertIn("이동 자체가 부정", prompt)

    def test_schema_validates_shape_but_backend_adds_semantic_grounding(self):
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            self.skipTest("Backend jsonschema dependency not installed yet")
        schema = json.loads((ROOT / "schemas/semantic_requirement.schema.json").read_text())
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        for output in (self.output, nonready(), nonready("UNSUPPORTED")):
            validator.validate(output)
            self.parse(output)
        for output in (dict(self.output, approval=True), dict(self.output, decision="APPLIED"),
                       dict(self.output, schema_version=1), ready(dx=axis(unit="ft"))):
            self.assertFalse(validator.is_valid(output))
            self.rejected(output)
        ungrounded = ready(dx=axis("2"))
        validator.validate(ungrounded)
        self.rejected(ungrounded, code="UNGROUNDED_REQUIREMENT")


if __name__ == "__main__":
    unittest.main()
