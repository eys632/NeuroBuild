#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import requests
from jsonschema import Draft202012Validator

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import progress_runtime as pr


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            yield line_no, line


def _remove_fence_markers(text: str) -> str:
    if "```" not in text:
        return text
    lines = [ln for ln in text.splitlines() if not ln.strip().startswith("```")]
    return "\n".join(lines)


def _extract_best_json(text: str) -> tuple[dict[str, Any] | None, str | None]:
    cleaned = _remove_fence_markers(text)
    decoder = json.JSONDecoder()
    best_start = None
    best_end = None

    for i, ch in enumerate(cleaned):
        if ch != "{":
            continue
        try:
            _, end = decoder.raw_decode(cleaned[i:])
        except json.JSONDecodeError:
            continue
        end_abs = i + end
        if best_start is None or (end_abs - i) > (best_end - best_start):
            best_start, best_end = i, end_abs

    if best_start is None or best_end is None:
        return None, None

    raw = cleaned[best_start:best_end]
    try:
        obj = json.loads(raw)
    except Exception:
        return None, raw

    if not isinstance(obj, dict):
        return None, raw

    return obj, raw


def _count_jsonl(path: Path) -> int:
    count = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def _canonicalize_edits(edits: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in edits or []:
        if not isinstance(item, dict):
            continue
        op = item.get("op") or item.get("type")
        if not isinstance(op, str) or not op:
            continue
        if "value" in item:
            out.append({"op": op, "value": item.get("value")})
        else:
            out.append({"op": op})
    return out


def _sorted_edit_signatures(edits: list[Any]) -> list[str]:
    canonical = _canonicalize_edits(edits)
    sigs = [json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")) for x in canonical]
    return sorted(sigs)


def _ops_exact_match(gold_ops: list[Any], pred_ops: list[Any]) -> bool:
    return _sorted_edit_signatures(gold_ops) == _sorted_edit_signatures(pred_ops)


def _slot_value_accuracy(gold_ops: list[Any], pred_ops: list[Any]) -> float:
    gold_items = _canonicalize_edits(gold_ops)
    pred_items = _canonicalize_edits(pred_ops)
    if not gold_items:
        return 1.0 if not pred_items else 0.0

    def _sig(item: dict[str, Any]) -> str:
        return json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    gold_counter = Counter([_sig(x) for x in gold_items])
    pred_counter = Counter([_sig(x) for x in pred_items])
    matched = sum((gold_counter & pred_counter).values())
    return matched / max(1, len(gold_items))


def _call_vllm(*, base_url: str, model: str, system_prompt: str, user_prompt: str, max_tokens: int, timeout: float) -> str:
    url = base_url.rstrip("/") + "/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.0,
        "max_tokens": int(max_tokens),
    }
    resp = requests.post(url, json=payload, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"vLLM HTTP {resp.status_code}: {resp.text[:1000]}")
    data = resp.json()
    content = (((data.get("choices") or [{}])[0]).get("message") or {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("vLLM response missing content")
    return content


def _load_hf_model(*, model_id_or_path: str, adapter_path: str | None, device: str):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch_dtype = torch.bfloat16 if device.startswith("cuda") and torch.cuda.is_available() else torch.float32
    tokenizer = AutoTokenizer.from_pretrained(model_id_or_path, trust_remote_code=True)

    model = AutoModelForCausalLM.from_pretrained(
        model_id_or_path,
        torch_dtype=torch_dtype,
        trust_remote_code=True,
    )

    if adapter_path:
        try:
            from peft import PeftModel
        except Exception as e:
            raise RuntimeError(f"peft import 실패: {e}") from e
        model = PeftModel.from_pretrained(model, adapter_path)

    if device.startswith("cuda") and torch.cuda.is_available():
        model = model.to(device)

    model.eval()
    return model, tokenizer


def _call_hf(
    *,
    model,
    tokenizer,
    system_prompt: str,
    user_prompt: str,
    device: str,
    max_tokens: int,
) -> str:
    import torch

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt")

    if device.startswith("cuda") and torch.cuda.is_available():
        inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=int(max_tokens),
            do_sample=False,
            temperature=0.0,
            pad_token_id=tokenizer.eos_token_id,
        )

    input_len = inputs["input_ids"].shape[-1]
    gen_tokens = out[0][input_len:]
    return tokenizer.decode(gen_tokens, skip_special_tokens=True)


def run_eval(
    *,
    dataset_path: Path,
    schema_path: Path,
    system_prompt_path: Path,
    output_path: Path,
    mode: str,
    model_id_or_path: str | None,
    adapter_path: str | None,
    vllm_base_url: str | None,
    vllm_model: str | None,
    device: str,
    max_tokens: int,
    timeout: float,
    max_samples: int | None,
) -> int:
    schema = _load_json(schema_path)
    validator = Draft202012Validator(schema)
    system_prompt = _load_text(system_prompt_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path = output_path.with_suffix(".summary.json")

    total = 0
    parse_ok = 0
    schema_ok = 0
    exact_ok = 0
    acc_sum = 0.0

    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass

    total_available = _count_jsonl(dataset_path)
    total_target = total_available
    if max_samples is not None:
        total_target = min(total_available, max_samples)

    pr.start_run(
        run_type="eval",
        stage="loading_model" if mode == "hf" else "loading_dataset",
        model_id_or_path=model_id_or_path,
        adapter_path=adapter_path,
        dataset_path=str(dataset_path),
        total_examples=total_target,
        device=device,
    )

    hf_model = None
    hf_tokenizer = None
    if mode == "hf":
        if not model_id_or_path:
            raise ValueError("hf 모드는 --model-id-or-path가 필요함")
        hf_model, hf_tokenizer = _load_hf_model(
            model_id_or_path=model_id_or_path,
            adapter_path=adapter_path,
            device=device,
        )

    pr.update_stage("loading_dataset")

    pr.update_stage("evaluating")

    with output_path.open("w", encoding="utf-8") as out_f:
        for _, line in _iter_jsonl(dataset_path):
            if max_samples is not None and total >= max_samples:
                break

            total += 1
            item = json.loads(line)
            gold = item.get("gold") or {}
            gold_ops = (gold.get("edits") or []) if isinstance(gold, dict) else []

            pred_raw = None
            pred_obj = None
            pred_error = None

            if mode == "gold":
                pred_obj = gold
                pred_raw = json.dumps(gold, ensure_ascii=False)
            elif mode == "hf":
                try:
                    text = _call_hf(
                        model=hf_model,
                        tokenizer=hf_tokenizer,
                        system_prompt=system_prompt,
                        user_prompt=item.get("prompt_ko", ""),
                        device=device,
                        max_tokens=max_tokens,
                    )
                    pred_obj, pred_raw = _extract_best_json(text)
                except Exception as e:
                    pred_error = f"{type(e).__name__}: {e}"
            elif mode == "vllm":
                if not vllm_base_url or not vllm_model:
                    raise ValueError("vllm mode requires --vllm-base-url and --vllm-model")
                try:
                    text = _call_vllm(
                        base_url=vllm_base_url,
                        model=vllm_model,
                        system_prompt=system_prompt,
                        user_prompt=item.get("prompt_ko", ""),
                        max_tokens=max_tokens,
                        timeout=timeout,
                    )
                    pred_obj, pred_raw = _extract_best_json(text)
                except Exception as e:
                    pred_error = f"{type(e).__name__}: {e}"
            else:
                raise ValueError(f"Unknown mode: {mode}")

            json_ok = pred_obj is not None
            if json_ok:
                parse_ok += 1

            is_schema_ok = False
            if json_ok:
                errs = list(validator.iter_errors(pred_obj))
                is_schema_ok = len(errs) == 0
                if is_schema_ok:
                    schema_ok += 1

            pred_ops = []
            if json_ok and isinstance(pred_obj, dict):
                pred_ops = pred_obj.get("edits") or []

            exact = False
            acc = 0.0
            if json_ok:
                exact = _ops_exact_match(gold_ops, pred_ops)
                acc = _slot_value_accuracy(gold_ops, pred_ops)
            if exact:
                exact_ok += 1
            acc_sum += acc

            pr.update_eval(
                model_id_or_path=model_id_or_path,
                adapter_path=adapter_path,
                dataset_path=str(dataset_path),
                current_example_idx=total,
                total_examples=total_target,
                parse_success_count=parse_ok,
                schema_valid_count=schema_ok,
                op_exact_match_count=exact_ok,
                slot_accuracy_running_avg=(acc_sum / max(1, total)),
            )

            record = {
                "id": item.get("id"),
                "category": item.get("category"),
                "prompt_ko": item.get("prompt_ko"),
                "gold": gold,
                "raw_output": pred_raw,
                "parsed_output": pred_obj,
                "parse_success": json_ok,
                "schema_valid": is_schema_ok,
                "op_exact_match": exact,
                "slot_accuracy": acc,
                "error_message": pred_error,
            }
            out_f.write(json.dumps(record, ensure_ascii=False) + "\n")

    pr.update_stage("writing_results")

    summary = {
        "metadata": {
            "mode": mode,
            "model_id_or_path": model_id_or_path,
            "adapter_path": adapter_path,
            "max_samples": max_samples,
            "dataset_path": str(dataset_path),
            "system_prompt_path": str(system_prompt_path),
        },
        "total_examples": total,
        "json_parse_success_rate": (parse_ok / total) if total else 0.0,
        "schema_valid_rate": (schema_ok / total) if total else 0.0,
        "op_exact_match_rate": (exact_ok / total) if total else 0.0,
        "slot_accuracy_avg": (acc_sum / total) if total else 0.0,
        "output": str(output_path),
    }

    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    pr.finish_run()
    return 0


def main() -> int:
    root = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(description="Run baseline evaluation for delta ops dataset")
    parser.add_argument("--dataset", default=str(root / "data" / "seed_test.jsonl"))
    parser.add_argument("--schema", default=str(root / "configs" / "delta_ops_schema.json"))
    parser.add_argument("--system-prompt", default=str(root / "configs" / "delta_system_prompt.txt"))
    parser.add_argument("--output", default=str(root / "results" / "baseline_eval.jsonl"))
    parser.add_argument("--mode", choices=["gold", "hf", "vllm"], default="gold")
    parser.add_argument("--model-id-or-path", default=None)
    parser.add_argument("--adapter-path", default=None)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--vllm-base-url", default=None)
    parser.add_argument("--vllm-model", default=None)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--max-samples", type=int, default=None)
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    schema_path = Path(args.schema)
    system_prompt_path = Path(args.system_prompt)
    output_path = Path(args.output)

    if not dataset_path.exists():
        print(f"Dataset not found: {dataset_path}", file=sys.stderr)
        return 2
    if not schema_path.exists():
        print(f"Schema not found: {schema_path}", file=sys.stderr)
        return 2
    if not system_prompt_path.exists():
        print(f"System prompt not found: {system_prompt_path}", file=sys.stderr)
        return 2

    device = args.device
    if device == "auto":
        try:
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            device = "cpu"

    try:
        return run_eval(
            dataset_path=dataset_path,
            schema_path=schema_path,
            system_prompt_path=system_prompt_path,
            output_path=output_path,
            mode=args.mode,
            model_id_or_path=args.model_id_or_path,
            adapter_path=args.adapter_path,
            vllm_base_url=args.vllm_base_url,
            vllm_model=args.vllm_model,
            device=device,
            max_tokens=args.max_tokens,
            timeout=args.timeout,
            max_samples=args.max_samples,
        )
    except Exception as e:
        pr.fail_run(f"평가 실패: {type(e).__name__}: {e}")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
