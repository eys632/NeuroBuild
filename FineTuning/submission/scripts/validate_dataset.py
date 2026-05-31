#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            yield line_no, line


def validate_dataset(dataset_path: Path, schema_path: Path) -> int:
    schema = _load_json(schema_path)
    validator = Draft202012Validator(schema)

    errors: list[str] = []
    seen_ids: set[str] = set()
    total = 0

    for line_no, line in _iter_jsonl(dataset_path):
        total += 1
        try:
            obj = json.loads(line)
        except Exception as e:
            errors.append(f"line {line_no}: invalid JSON: {e}")
            continue

        for key in ("id", "category", "prompt_ko", "gold"):
            if key not in obj:
                errors.append(f"line {line_no}: missing key '{key}'")

        if not isinstance(obj.get("id"), str) or not obj.get("id"):
            errors.append(f"line {line_no}: id must be non-empty string")
        if not isinstance(obj.get("category"), str) or not obj.get("category"):
            errors.append(f"line {line_no}: category must be non-empty string")
        if not isinstance(obj.get("prompt_ko"), str) or not obj.get("prompt_ko"):
            errors.append(f"line {line_no}: prompt_ko must be non-empty string")

        if isinstance(obj.get("id"), str):
            if obj["id"] in seen_ids:
                errors.append(f"line {line_no}: duplicate id '{obj['id']}'")
            seen_ids.add(obj["id"])

        gold = obj.get("gold")
        if not isinstance(gold, dict):
            errors.append(f"line {line_no}: gold must be an object")
            continue

        for err in validator.iter_errors(gold):
            path = "/".join([str(p) for p in err.path])
            where = f"{path}" if path else "<root>"
            errors.append(f"line {line_no}: schema error at {where}: {err.message}")

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        print(f"Checked {total} records, {len(errors)} errors", file=sys.stderr)
        return 1

    print(f"Checked {total} records, 0 errors")
    return 0


def main() -> int:
    root = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(description="Validate delta ops dataset against schema")
    parser.add_argument("--dataset", default=str(root / "data" / "seed_test.jsonl"))
    parser.add_argument("--schema", default=str(root / "configs" / "delta_ops_schema.json"))
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    schema_path = Path(args.schema)

    if not dataset_path.exists():
        print(f"Dataset not found: {dataset_path}", file=sys.stderr)
        return 2
    if not schema_path.exists():
        print(f"Schema not found: {schema_path}", file=sys.stderr)
        return 2

    return validate_dataset(dataset_path, schema_path)


if __name__ == "__main__":
    raise SystemExit(main())
