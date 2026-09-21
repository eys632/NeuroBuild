"""Synthetic quote-adapter boundary tests; no model accuracy claim.

AUTO-GENERATED / NOT HUMAN VERIFIED. Natural-language completeness remains a
separate semantic evaluation; these tests exercise deterministic validation.
"""

from copy import deepcopy
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4

from jsonschema import Draft202012Validator

from neurobuild.application.requirement_generation import (
    GenerationContract, adapt_generation_v2, parse_generated_requirement,
)
from neurobuild.application.requirements import parse_requirement
from neurobuild.domain.errors import DomainError


ROOT = Path(__file__).resolve().parents[1]


def quoted(*, target="회의실 책상", instruction=None, dx="X축 +1m", dy=None):
    if instruction is None:
        instruction = target + "을 " + ", ".join(item for item in (dx, dy) if item is not None) + " 옮겨줘."
    return {"schema_version": "2.0", "decision": "READY",
            "target_selection_quote": target, "current_instruction_quote": instruction,
            "dx_evidence": dx, "dy_evidence": dy, "reason": None}


def encoded(output):
    return json.dumps(output, ensure_ascii=False)


class RequirementGenerationTests(unittest.TestCase):
    def setUp(self):
        self.ids = {"requirement_id": uuid4(), "project_id": uuid4(), "base_revision_id": uuid4()}
        self.output = quoted()
        self.source = self.output["current_instruction_quote"]

    def adapt(self, output=None, *, source=None):
        return json.loads(adapt_generation_v2(
            encoded(self.output if output is None else output),
            source_text=self.source if source is None else source))

    def parse(self, output=None, *, source=None, context="project_xy", **ids):
        return parse_generated_requirement(
            encoded(self.output if output is None else output),
            generation_contract=GenerationContract.QUOTES,
            source_text=self.source if source is None else source,
            axis_convention=context, **(self.ids | ids))

    def rejected(self, output, *, source=None, code=None):
        with self.assertRaises(DomainError) as caught:
            self.parse(output, source=source)
        if code is not None:
            self.assertEqual(caught.exception.code, code)
        self.assertNotIn("SENSITIVE_SENTINEL", str(caught.exception))

    def test_projection_and_wrapper_equal_direct_legacy_parse(self):
        legacy = self.adapt()
        self.assertEqual(legacy["schema_version"], "1.0")
        self.assertEqual(legacy["operation"]["dx"],
                         {"value": "+1", "unit": "m", "evidence": "X축 +1m"})
        self.assertIsNone(legacy["operation"]["dy"])
        direct = parse_requirement(encoded(legacy), source_text=self.source,
                                   axis_convention="project_xy", **self.ids)
        self.assertEqual(self.parse(), direct)
        self.assertEqual(direct.operation.dy.metres, Decimal("0"))
        self.assertEqual(direct.source_text, self.source)
        self.assertFalse(hasattr(direct, "approval"))

    def test_numeric_spelling_sign_and_original_unit_survive_projection(self):
        for evidence, lexical, unit in (
            ("X축 +0001.2500mm", "+0001.2500", "mm"),
            ("-X축으로 125.0mm", "-125.0", "mm"),
            ("X축 음의 방향으로 000125.00밀리미터", "-000125.00", "mm"),
            ("X축 -12.500센티미터", "-12.500", "cm"),
            ("+X축으로 0.50미터", "0.50", "m"),
            ("X axis positive 1미터", "1", "m"),
            ("(-X축)으로 12mm", "-12", "mm"),
            ("'X축' +12mm", "+12", "mm"),
        ):
            output = quoted(dx=evidence)
            with self.subTest(evidence=evidence), localcontext() as context:
                context.prec = 1
                result = self.adapt(output, source=output["current_instruction_quote"])
                self.assertEqual(result["operation"]["dx"]["value"], lexical)
                self.assertEqual(result["operation"]["dx"]["unit"], unit)
                parsed = self.parse(output, source=output["current_instruction_quote"])
                self.assertEqual(parsed.operation.dx.value.as_tuple(), Decimal(lexical).as_tuple())

    def test_null_empty_and_signed_zero_have_distinct_meanings(self):
        output = quoted(dx="X축 -0.00mm", dy="Y축 +2cm")
        source = output["current_instruction_quote"]
        projected = self.adapt(output, source=source)
        self.assertEqual(projected["operation"]["dx"]["value"], "-0.00")
        self.assertEqual(self.parse(output, source=source).operation.dx.value.as_tuple(),
                         Decimal("-0.00").as_tuple())
        for dx, dy in ((None, None), ("", "Y축 +2cm"), ("X축 +0m", None),
                       ("X축 -0mm", "Y축 +0cm")):
            item = quoted(dx=dx, dy=dy)
            self.rejected(item, source=item["current_instruction_quote"])

    def test_absent_conflicting_or_double_negative_sign_is_not_guessed(self):
        for evidence in ("X축 1m", "+X축 -1m", "-X축 +1m", "X축 양의 음의 방향으로 1m",
                         "X축 음의 방향으로 +1m", "X축 --1m"):
            output = quoted(dx=evidence)
            with self.subTest(evidence=evidence):
                self.rejected(output, source=output["current_instruction_quote"])

    def test_axis_quantity_multiplicity_and_wrong_axis_are_rejected(self):
        for evidence in ("Y축 +1m", "X축 +1m 또는 +2m", "X축 Y축 +1m", "X축 +1m, 2번"):
            output = quoted(dx=evidence)
            self.rejected(output, source=output["current_instruction_quote"])

    def test_original_source_numeric_boundaries_are_not_truncated_to_evidence(self):
        bad_tokens = (
            "1,250m", "1e2m", "1/2m", "1+2m", "1⁄2m", "1×2m", "1'250m",
            "1’250m", "1·2m", "1:2m", "1/(2m)", "1\u00a0250m", "1\u03382m",
            "1\u03012m", "1\u200b2m", "1%2m", "１２2m",
        )
        for token in bad_tokens:
            source = "회의실 책상을 +X축으로 " + token + " 옮겨줘."
            output = quoted(dx="+X축으로 " + token, instruction=source)
            with self.subTest(token=token):
                self.rejected(output, source=source)
        # A superficially valid suffix is still invalid in its complete source.
        source = "회의실 책상을 X축 양의 방향으로 1+2m 옮겨줘."
        output = quoted(dx="X축 양의 방향으로 1+2m", instruction=source)
        self.rejected(output, source=source)

    def test_axis_sign_clipping_is_rejected_in_complete_original_source(self):
        for prefix in ("-", "−", "＋", "—"):
            source = "회의실 책상을 " + prefix + "X축 +1m 옮겨줘."
            output = quoted(dx="X축 +1m", instruction=source)
            with self.subTest(prefix=prefix):
                self.rejected(output, source=source)
        source = "회의실 책상을 -(X축) +1m 옮겨줘."
        self.rejected(quoted(dx="X축) +1m", instruction=source), source=source)

    def test_clipped_unit_or_instruction_cannot_hide_original_token(self):
        source = "회의실 책상을 X축 +1mm 옮겨줘."
        self.rejected(quoted(dx="X축 +1m", instruction=source), source=source)
        target = "회의실 책상"
        source = target + "을 X축 +1mm 옮겨줘."
        clipped = target + "을 X축 +1m"
        self.rejected(quoted(dx="X축 +1m", instruction=clipped), source=source)

    def test_historical_axis_can_be_excluded_but_historical_evidence_not_reused(self):
        current = "회의실 책상을 Y축 +30cm 옮겨줘."
        source = "이전 X축 -2m 지시는 취소했다. " + current
        output = quoted(dx=None, dy="Y축 +30cm", instruction=current)
        self.assertEqual(self.parse(output, source=source).operation.dy.metres, Decimal("0.30"))
        output["dx_evidence"] = "X축 -2m"
        self.rejected(output, source=source, code="UNGROUNDED_REQUIREMENT")

    def test_missing_current_axis_is_not_zero_filled(self):
        source = "회의실 책상을 X축 +1m, Y축 -2m 옮겨줘."
        self.rejected(quoted(instruction=source), source=source, code="UNGROUNDED_REQUIREMENT")

    def test_repeated_occurrences_use_same_complete_axis_and_quantity_span(self):
        current = "회의실 책상을 X축 +1m 옮겨줘."
        source = "이전 초안: " + current + " 현재 지시: " + current
        self.assertEqual(self.parse(quoted(instruction=current), source=source).operation.dx.metres, Decimal("1"))
        # Repeating only clipped tokens never supplies a valid complete source span.
        source = "회의실 책상을 X축 +1mm; 회의실 책상을 X축 +1mm"
        clipped = "회의실 책상을 X축 +1m"
        self.rejected(quoted(instruction=clipped), source=source)

    def test_full_target_quote_preserved_without_normalization_or_repair(self):
        target = "회의실 입구 쪽 책상 말고 창가 쪽 책상"
        output = quoted(target=target)
        source = output["current_instruction_quote"]
        self.assertEqual(self.parse(output, source=source).target_description, target)
        for field, value in (("target_selection_quote", "회의실  입구 쪽 책상"),
                             ("current_instruction_quote", "회의실 책상을 X축 +1m 옮겨줘."),
                             ("dx_evidence", "X축 +2m")):
            self.rejected(dict(output, **{field: value}), source=source)
        # Semantic completeness is not deterministically proven: a shorter
        # exact target is preserved, never expanded using source or test gold.
        shorter = dict(output, target_selection_quote="창가 쪽 책상")
        self.assertEqual(self.parse(shorter, source=source).target_description, "창가 쪽 책상")

    def test_nonready_shape_and_target_match_legacy_contract(self):
        for decision in ("CLARIFICATION", "UNSUPPORTED"):
            for target in ("회의실 책상", ""):
                item = {"schema_version": "2.0", "decision": decision,
                        "target_selection_quote": target, "current_instruction_quote": None,
                        "dx_evidence": None, "dy_evidence": None, "reason": "확인이 필요합니다."}
                parsed = self.parse(item, context=None)
                self.assertEqual(parsed.status.value, decision)
                self.assertIsNone(parsed.operation)
                self.assertEqual(parsed.target_description, target)
                for field in ("current_instruction_quote", "dx_evidence", "dy_evidence"):
                    self.rejected(dict(item, **{field: "X축 +1m"}))
                for reason in (None, "", " ", False, "x" * 513):
                    self.rejected(dict(item, reason=reason))

    def test_json_parser_rejects_duplicate_keys_constants_and_wrappers(self):
        raw = encoded(self.output)
        for malformed in (
            raw.replace('"decision": "READY"', '"decision":"UNSUPPORTED","decision":"READY"'),
            raw.replace('"reason": null', '"reason":NaN'),
            raw.replace('"reason": null', '"reason":Infinity'),
            "```json\n" + raw + "\n```", raw + "{}", "[]", "null", "", "\ufeff" + raw,
            "[" * 1500 + "]" * 1500, "x" * 16385, b"{}", None, True,
        ):
            with self.subTest(raw=str(malformed)[:60]), self.assertRaises(DomainError) as caught:
                adapt_generation_v2(malformed, source_text=self.source)
            self.assertEqual(caught.exception.code, "INVALID_MODEL_OUTPUT")

    def test_exact_seven_keys_types_and_limits_reject_untrusted_fields(self):
        for key in self.output:
            item = deepcopy(self.output)
            del item[key]
            self.rejected(item)
        for key in ("GlobalId", "approval", "operation", "value", "unit", "raw_ifc", "reasoning"):
            self.rejected(dict(self.output, **{key: "SENSITIVE_SENTINEL"}))
        for key, value in (
            ("schema_version", "1.0"), ("schema_version", 2), ("decision", []),
            ("decision", True), ("target_selection_quote", None), ("target_selection_quote", ""),
            ("target_selection_quote", "x" * 1025), ("current_instruction_quote", "x" * 4097),
            ("current_instruction_quote", None), ("dx_evidence", "x" * 513),
            ("dx_evidence", True), ("dy_evidence", {}), ("reason", "SENSITIVE_SENTINEL"),
            ("target_selection_quote", "\x00"), ("dx_evidence", "\ud800"),
        ):
            with self.subTest(key=key, value=str(value)[:40]):
                self.rejected(dict(self.output, **{key: value}))

    def test_numeric_limits_are_existing_legacy_limits(self):
        valid = quoted(dx="X축 +1234567890123456.123456789012mm")
        self.assertEqual(self.adapt(valid, source=valid["current_instruction_quote"])
                         ["operation"]["dx"]["value"], "+1234567890123456.123456789012")
        for token in ("12345678901234567mm", "1.1234567890123mm", "1e999m", "NaNm", "Infinitym"):
            item = quoted(dx="X축 +" + token)
            self.rejected(item, source=item["current_instruction_quote"])

    def test_source_and_code_owned_context_ids_are_validated(self):
        for source in (None, b"text", True, "", " ", "x" * 16001, "\x00", "\ud800"):
            with self.subTest(source=str(source)[:40]), self.assertRaises(DomainError) as caught:
                adapt_generation_v2(encoded(self.output), source_text=source)
            self.assertEqual(caught.exception.code, "INVALID_REQUIREMENT_INPUT")
        for key in self.ids:
            with self.subTest(key=key), self.assertRaises(DomainError) as caught:
                self.parse(**{key: str(self.ids[key])})
            self.assertEqual(caught.exception.code, "INVALID_REQUIREMENT_INPUT")
        for context, code in ((None, "UNGROUNDED_REQUIREMENT"), ("camera_xy", "INVALID_REQUIREMENT_INPUT")):
            with self.assertRaises(DomainError) as caught:
                self.parse(context=context)
            self.assertEqual(caught.exception.code, code)

    def test_contract_selection_is_explicit_and_never_output_driven(self):
        for contract in (None, "1.0", "2.0", "auto", True, 2, {}):
            with self.subTest(contract=contract), self.assertRaises(DomainError) as caught:
                parse_generated_requirement(encoded(self.output), generation_contract=contract,
                                            source_text=self.source, **self.ids)
            self.assertEqual(caught.exception.code, "INVALID_REQUIREMENT_INPUT")
        legacy = encoded(self.adapt())
        for raw, contract in ((legacy, GenerationContract.QUOTES),
                              (encoded(self.output), GenerationContract.LEGACY)):
            with self.assertRaises(DomainError):
                parse_generated_requirement(raw, generation_contract=contract,
                                            source_text=self.source, axis_convention="project_xy", **self.ids)
        with self.assertRaises(TypeError):
            parse_generated_requirement(legacy, source_text=self.source, **self.ids)

    def test_legacy_route_does_not_adapt_or_rewrite_response(self):
        raw = encoded(self.adapt())
        expected = parse_requirement(raw, source_text=self.source, axis_convention="project_xy", **self.ids)
        with patch("neurobuild.application.requirement_generation.adapt_generation_v2",
                   side_effect=AssertionError("legacy must not adapt")):
            actual = parse_generated_requirement(raw, generation_contract=GenerationContract.LEGACY,
                                                 source_text=self.source, axis_convention="project_xy", **self.ids)
        self.assertEqual(actual, expected)

    def test_projection_is_canonical_and_rejection_does_not_reclassify_ready(self):
        before = deepcopy(self.output)
        forward = adapt_generation_v2(encoded(self.output), source_text=self.source)
        reverse = adapt_generation_v2(encoded(dict(reversed(list(self.output.items())))), source_text=self.source)
        self.assertEqual(forward, reverse)
        self.assertEqual(self.output, before)
        bad = dict(self.output, dx_evidence="X축 +2m")
        self.rejected(bad)
        self.assertEqual(bad["decision"], "READY")

    def test_new_schema_has_only_generation_shape_backend_remains_mandatory(self):
        schema = json.loads((ROOT / "schemas/requirement_generation_v2.schema.json").read_text())
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        self.assertTrue(validator.is_valid(self.output))
        self.assertFalse(validator.is_valid(dict(self.output, approval=True)))
        self.assertFalse(validator.is_valid(dict(self.output, schema_version="1.0")))
        backend_invalid = dict(self.output, dx_evidence=None)
        self.assertTrue(validator.is_valid(backend_invalid))
        self.rejected(backend_invalid)

    def test_frozen_v1_parser_and_schema_bytes_are_preserved(self):
        expected = {
            "src/neurobuild/application/requirements.py": "a940f3952c0c4133ab51732f6abf76516d8ff66617470545222b52adfa49fb4a",
            "schemas/semantic_requirement.schema.json": "dd131db08fe9087e795059445b075f22876e44b42481201cc0ea70608a708f94",
        }
        for path, digest in expected.items():
            with self.subTest(path=path):
                self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), digest)


if __name__ == "__main__":
    unittest.main()
