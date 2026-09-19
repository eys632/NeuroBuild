#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SUPPORTED_OPS = {
    "set_windows_per_wall",
    "remove_all_windows",
    "set_windows_size_preset",
    "set_avoid_bathroom_zone",
    "set_exterior_door",
    "add_exterior_door",
    "set_bathroom_count",
    "add_bathroom",
    "increment_bathroom_count",
}

REQUIRED_VALUE_OPS = {
    "set_windows_per_wall",
    "set_windows_size_preset",
    "set_avoid_bathroom_zone",
    "set_exterior_door",
    "set_bathroom_count",
}

OPTIONAL_VALUE_OPS = {
    "add_exterior_door",
    "add_bathroom",
    "increment_bathroom_count",
}

NO_VALUE_OPS = {
    "remove_all_windows",
}


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            yield line_no, line


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _is_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _validate_value(op: str, value: Any) -> str | None:
    if op == "set_windows_per_wall":
        if not _is_int(value):
            return "value는 int여야 함"
        if not (0 <= value <= 10):
            return "value 범위는 0..10"
        return None

    if op == "set_windows_size_preset":
        if not isinstance(value, str):
            return "value는 문자열이어야 함"
        if value not in ("small", "medium", "large"):
            return "value는 small|medium|large"
        return None

    if op == "set_avoid_bathroom_zone":
        if not isinstance(value, bool):
            return "value는 bool이어야 함"
        return None

    if op == "set_exterior_door":
        if not isinstance(value, bool):
            return "value는 bool이어야 함"
        return None

    if op == "add_exterior_door":
        if value is None:
            return None
        if not isinstance(value, bool):
            return "value는 bool이어야 함"
        return None

    if op == "set_bathroom_count":
        if not _is_int(value):
            return "value는 int여야 함"
        if not (0 <= value <= 10):
            return "value 범위는 0..10"
        return None

    if op in ("add_bathroom", "increment_bathroom_count"):
        if value is None:
            return None
        if not _is_int(value):
            return "value는 int여야 함"
        if not (1 <= value <= 10):
            return "value 범위는 1..10"
        return None

    return "지원하지 않는 op"


def _canonicalize_gold(gold: dict[str, Any], ctx: str, errors: list[str]) -> dict[str, Any] | None:
    edits = gold.get("edits")
    notes = gold.get("notes", "")

    if not isinstance(edits, list):
        errors.append(f"{ctx}: gold.edits는 배열이어야 함")
        return None
    if not isinstance(notes, str):
        errors.append(f"{ctx}: gold.notes는 문자열이어야 함")
        return None

    out_edits: list[dict[str, Any]] = []
    for idx, item in enumerate(edits, start=1):
        if not isinstance(item, dict):
            errors.append(f"{ctx}: edits[{idx}]는 객체여야 함")
            return None

        op = item.get("op") or item.get("type")
        if not isinstance(op, str) or not op:
            errors.append(f"{ctx}: edits[{idx}]에 op/type이 필요함")
            return None
        if op not in SUPPORTED_OPS:
            errors.append(f"{ctx}: 지원하지 않는 op: {op}")
            return None

        has_value = "value" in item
        value = item.get("value") if has_value else None

        if op in REQUIRED_VALUE_OPS and not has_value:
            errors.append(f"{ctx}: {op}는 value가 필요함")
            return None
        if op in NO_VALUE_OPS and has_value:
            errors.append(f"{ctx}: {op}는 value를 가지면 안 됨")
            return None

        if op in REQUIRED_VALUE_OPS or op in OPTIONAL_VALUE_OPS:
            err = _validate_value(op, value)
            if err:
                errors.append(f"{ctx}: {op} value 오류: {err}")
                return None

        out_item: dict[str, Any] = {"op": op}
        if has_value:
            out_item["value"] = value
        out_edits.append(out_item)

    return {"edits": out_edits, "notes": notes}


def _build_messages(
    *,
    input_path: Path,
    output_path: Path,
    system_prompt: str,
    errors: list[str],
) -> int:
    count = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as out_f:
        for line_no, line in _iter_jsonl(input_path):
            try:
                obj = json.loads(line)
            except Exception as e:
                errors.append(f"{input_path}:{line_no}: JSON 파싱 실패: {e}")
                continue

            rec_id = obj.get("id")
            category = obj.get("category")
            prompt_ko = obj.get("prompt_ko")
            gold = obj.get("gold")

            if not isinstance(rec_id, str) or not rec_id:
                errors.append(f"{input_path}:{line_no}: id가 비어있음")
                continue
            if not isinstance(category, str) or not category:
                errors.append(f"{input_path}:{line_no}: category가 비어있음")
                continue
            if not isinstance(prompt_ko, str) or not prompt_ko:
                errors.append(f"{input_path}:{line_no}: prompt_ko가 비어있음")
                continue
            if not isinstance(gold, dict):
                errors.append(f"{input_path}:{line_no}: gold가 객체가 아님")
                continue

            ctx = f"{input_path}:{line_no} ({rec_id})"
            canonical_gold = _canonicalize_gold(gold, ctx, errors)
            if canonical_gold is None:
                continue

            assistant_content = json.dumps(
                canonical_gold,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )

            row = {
                "id": rec_id,
                "category": category,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt_ko},
                    {"role": "assistant", "content": assistant_content},
                ],
            }
            out_f.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1

    return count


def main() -> int:
    root = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(description="SFT용 messages JSONL 생성")
    parser.add_argument("--system-prompt", default=str(root / "configs" / "delta_system_prompt.txt"))
    parser.add_argument("--train-in", default=str(root / "data" / "seed_train.jsonl"))
    parser.add_argument("--valid-in", default=str(root / "data" / "seed_valid.jsonl"))
    parser.add_argument("--test-in", default=str(root / "data" / "seed_test.jsonl"))
    parser.add_argument("--train-out", default=str(root / "data" / "train_messages.jsonl"))
    parser.add_argument("--valid-out", default=str(root / "data" / "valid_messages.jsonl"))
    parser.add_argument("--test-out", default=str(root / "data" / "test_messages.jsonl"))
    args = parser.parse_args()

    system_prompt_path = Path(args.system_prompt)
    train_in = Path(args.train_in)
    valid_in = Path(args.valid_in)
    test_in = Path(args.test_in)
    train_out = Path(args.train_out)
    valid_out = Path(args.valid_out)
    test_out = Path(args.test_out)

    if not system_prompt_path.exists():
        print(f"시스템 프롬프트 파일 없음: {system_prompt_path}", file=sys.stderr)
        return 2
    if not train_in.exists():
        print(f"train 데이터 파일 없음: {train_in}", file=sys.stderr)
        return 2
    if not valid_in.exists():
        print(f"valid 데이터 파일 없음: {valid_in}", file=sys.stderr)
        return 2

    system_prompt = _load_text(system_prompt_path)

    errors: list[str] = []

    train_count = _build_messages(
        input_path=train_in,
        output_path=train_out,
        system_prompt=system_prompt,
        errors=errors,
    )
    valid_count = _build_messages(
        input_path=valid_in,
        output_path=valid_out,
        system_prompt=system_prompt,
        errors=errors,
    )

    test_count = 0
    if test_in.exists():
        test_count = _build_messages(
            input_path=test_in,
            output_path=test_out,
            system_prompt=system_prompt,
            errors=errors,
        )

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        print(f"오류 {len(errors)}건 발생", file=sys.stderr)
        return 1

    print(f"train 변환: {train_count}건 -> {train_out}")
    print(f"valid 변환: {valid_count}건 -> {valid_out}")
    if test_in.exists():
        print(f"test 변환: {test_count}건 -> {test_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
