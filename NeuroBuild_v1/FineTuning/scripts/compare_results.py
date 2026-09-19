#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import progress_runtime as pr


def _load_jsonl(path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception as e:
            raise ValueError(f"{path}:{line_no}: JSON 파싱 실패: {e}") from e
        rec_id = obj.get("id")
        if not isinstance(rec_id, str) or not rec_id:
            raise ValueError(f"{path}:{line_no}: id 없음")
        out[rec_id] = obj
    return out


def _aggregate(records: dict[str, dict]) -> dict:
    total = len(records)
    if total == 0:
        return {
            "total_examples": 0,
            "json_parse_success_rate": 0.0,
            "schema_valid_rate": 0.0,
            "op_exact_match_rate": 0.0,
            "slot_accuracy_avg": 0.0,
        }

    parse_ok = 0
    schema_ok = 0
    op_ok = 0
    acc_sum = 0.0

    for rec in records.values():
        if rec.get("parse_success"):
            parse_ok += 1
        if rec.get("schema_valid"):
            schema_ok += 1
        if rec.get("op_exact_match"):
            op_ok += 1
        acc_sum += float(rec.get("slot_accuracy") or 0.0)

    return {
        "total_examples": total,
        "json_parse_success_rate": parse_ok / total,
        "schema_valid_rate": schema_ok / total,
        "op_exact_match_rate": op_ok / total,
        "slot_accuracy_avg": acc_sum / total,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(description="베이스 vs 파인튜닝 결과 비교")
    parser.add_argument("--base", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--output", default=str(root / "results" / "compare_base_vs_ft_smoke.json"))
    args = parser.parse_args()

    base_path = Path(args.base)
    cand_path = Path(args.candidate)
    out_path = Path(args.output)

    pr.log_event("compare_start", message="compare_results 시작")
    pr.log_event("loading_base", message=str(base_path))

    if not base_path.exists():
        print(f"base 결과 없음: {base_path}", file=sys.stderr)
        return 2
    pr.log_event("loading_candidate", message=str(cand_path))

    if not cand_path.exists():
        print(f"candidate 결과 없음: {cand_path}", file=sys.stderr)
        return 2

    base = _load_jsonl(base_path)
    cand = _load_jsonl(cand_path)

    pr.log_event("comparing", message="지표 비교 중")

    common_ids = sorted(set(base.keys()) & set(cand.keys()))
    improvement = 0
    regression = 0
    tie = 0

    for rec_id in common_ids:
        b = base[rec_id]
        c = cand[rec_id]
        b_acc = float(b.get("slot_accuracy") or 0.0)
        c_acc = float(c.get("slot_accuracy") or 0.0)
        if c_acc > b_acc:
            improvement += 1
        elif c_acc < b_acc:
            regression += 1
        else:
            tie += 1

    result = {
        "base": _aggregate(base),
        "candidate": _aggregate(cand),
        "compare": {
            "total_compared": len(common_ids),
            "improvement_count": improvement,
            "regression_count": regression,
            "tie_count": tie,
        },
        "inputs": {
            "base": str(base_path),
            "candidate": str(cand_path),
        },
    }

    pr.log_event("writing_output", message=str(out_path))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    pr.log_event("compare_done", message="compare_results 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
