#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import requests


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except Exception as e:
            raise ValueError(f"{path}:{line_no} JSON 파싱 실패: {e}") from e
    return items


def _post_json(url: str, payload: dict[str, Any], timeout: float) -> tuple[int, dict[str, Any] | None, str | None]:
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
    except Exception as e:
        return 0, None, f"요청 실패: {type(e).__name__}: {e}"
    if resp.status_code != 200:
        return resp.status_code, None, resp.text[:2000]
    try:
        return resp.status_code, resp.json(), None
    except Exception as e:
        return resp.status_code, None, f"응답 JSON 파싱 실패: {e}"


def _get_status(base_url: str, timeout: float) -> dict[str, Any] | None:
    try:
        resp = requests.get(base_url.rstrip("/") + "/api/llm/status", timeout=timeout)
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception:
        return None


def _extract_edits(resp: dict[str, Any] | None) -> list[dict[str, Any]] | None:
    if not isinstance(resp, dict):
        return None
    llm = resp.get("llm")
    if isinstance(llm, dict) and isinstance(llm.get("edits"), list):
        return llm.get("edits")
    return None


def _judge(item: dict[str, Any], edits: list[dict[str, Any]] | None) -> str:
    if edits is None:
        return "no_edits"
    if item.get("expected_empty_edits") is True:
        return "pass" if len(edits) == 0 else "fail"
    expected_op = item.get("expected_op")
    if isinstance(expected_op, str):
        found = any((e.get("op") == expected_op) for e in edits if isinstance(e, dict))
        return "pass" if found else "fail"
    return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description="base vs lora API 비교")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--lora-url", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--base-prompt", default="12x9x3")
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"데이터셋 없음: {dataset_path}", file=sys.stderr)
        return 2

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cases = _load_jsonl(dataset_path)

    base_status = _get_status(args.base_url, args.timeout)
    lora_status = _get_status(args.lora_url, args.timeout)

    # base_file_id 준비 (각 서버에서 1회 생성)
    base_id = None
    lora_id = None

    base_status_code, base_resp, base_err = _post_json(
        args.base_url.rstrip("/") + "/api/generate",
        {"prompt": args.base_prompt, "use_llm": True, "base_file_id": None},
        args.timeout,
    )
    if base_resp and isinstance(base_resp.get("file_id"), str):
        base_id = base_resp.get("file_id")

    lora_status_code, lora_resp, lora_err = _post_json(
        args.lora_url.rstrip("/") + "/api/generate",
        {"prompt": args.base_prompt, "use_llm": True, "base_file_id": None},
        args.timeout,
    )
    if lora_resp and isinstance(lora_resp.get("file_id"), str):
        lora_id = lora_resp.get("file_id")

    if not base_id or not lora_id:
        print("base/lora 초기 file_id 생성 실패", file=sys.stderr)

    base_out_path = out_dir / "ui_base_results.jsonl"
    lora_out_path = out_dir / "ui_lora_results.jsonl"

    base_pass = 0
    lora_pass = 0

    with base_out_path.open("w", encoding="utf-8") as bf, lora_out_path.open("w", encoding="utf-8") as lf:
        for case in cases:
            prompt = case.get("prompt_ko", "")

            b_status, b_resp, b_err = _post_json(
                args.base_url.rstrip("/") + "/api/generate",
                {"prompt": prompt, "use_llm": True, "base_file_id": base_id},
                args.timeout,
            )
            l_status, l_resp, l_err = _post_json(
                args.lora_url.rstrip("/") + "/api/generate",
                {"prompt": prompt, "use_llm": True, "base_file_id": lora_id},
                args.timeout,
            )

            b_edits = _extract_edits(b_resp)
            l_edits = _extract_edits(l_resp)

            b_judge = _judge(case, b_edits)
            l_judge = _judge(case, l_edits)
            if b_judge == "pass":
                base_pass += 1
            if l_judge == "pass":
                lora_pass += 1

            base_row = {
                "id": case.get("id"),
                "prompt_ko": prompt,
                "expected_behavior": case.get("expected_behavior"),
                "expected_op": case.get("expected_op"),
                "expected_empty_edits": case.get("expected_empty_edits"),
                "base_response_status": b_status,
                "base_parsed_edits": b_edits,
                "base_file_id": (b_resp or {}).get("file_id") if isinstance(b_resp, dict) else None,
                "base_file_url": (b_resp or {}).get("file_url") if isinstance(b_resp, dict) else None,
                "base_error": b_err,
                "judge": b_judge,
            }
            lora_row = {
                "id": case.get("id"),
                "prompt_ko": prompt,
                "expected_behavior": case.get("expected_behavior"),
                "expected_op": case.get("expected_op"),
                "expected_empty_edits": case.get("expected_empty_edits"),
                "lora_response_status": l_status,
                "lora_parsed_edits": l_edits,
                "lora_file_id": (l_resp or {}).get("file_id") if isinstance(l_resp, dict) else None,
                "lora_file_url": (l_resp or {}).get("file_url") if isinstance(l_resp, dict) else None,
                "lora_error": l_err,
                "judge": l_judge,
            }

            bf.write(json.dumps(base_row, ensure_ascii=False) + "\n")
            lf.write(json.dumps(lora_row, ensure_ascii=False) + "\n")

    summary = {
        "base_status": base_status,
        "lora_status": lora_status,
        "base_initial": {
            "status": base_status_code,
            "error": base_err,
            "file_id": base_id,
        },
        "lora_initial": {
            "status": lora_status_code,
            "error": lora_err,
            "file_id": lora_id,
        },
        "counts": {
            "total": len(cases),
            "base_pass": base_pass,
            "lora_pass": lora_pass,
        },
        "outputs": {
            "base": str(base_out_path),
            "lora": str(lora_out_path),
        },
    }

    compare_path = out_dir / "ui_compare_results.json"
    compare_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_md = out_dir / "ui_api_compare_summary.md"
    summary_md.write_text(
        "# UI/API 비교 요약\n\n"
        f"- total: {len(cases)}\n"
        f"- base_pass: {base_pass}\n"
        f"- lora_pass: {lora_pass}\n"
        f"- base_status: {base_status}\n"
        f"- lora_status: {lora_status}\n",
        encoding="utf-8",
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
