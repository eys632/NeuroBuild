#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import progress_runtime as pr


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception as e:
            raise ValueError(f"{path}:{line_no}: JSON 파싱 실패: {e}") from e
        items.append(obj)
    return items


def _build_text_dataset(items: list[dict[str, Any]], tokenizer, max_samples: int | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    count = 0
    for item in items:
        if max_samples is not None and count >= max_samples:
            break
        msgs = item.get("messages")
        if not isinstance(msgs, list):
            continue
        text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)
        out.append({"text": text})
        count += 1
    return out


def _dtype_from_str(name: str):
    import torch

    name = (name or "").lower()
    if name == "bfloat16":
        return torch.bfloat16
    if name == "float16":
        return torch.float16
    return torch.float32


def _load_model_and_tokenizer(
    *,
    model_id_or_path: str,
    device: str,
    quant_cfg: dict[str, Any],
    smoke: bool,
) -> tuple[Any, Any, dict[str, Any]]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    fallback_info: dict[str, Any] = {"used": False, "reason": None, "mode": None}

    tokenizer = AutoTokenizer.from_pretrained(model_id_or_path, trust_remote_code=True)

    def _load(use_4bit: bool):
        kwargs: dict[str, Any] = {"trust_remote_code": True}
        if use_4bit:
            try:
                import bitsandbytes as _bnb
                from bitsandbytes.cextension import CUDASetup
                from transformers import BitsAndBytesConfig
            except Exception as e:
                raise RuntimeError(f"BitsAndBytesConfig import 실패: {e}") from e

            try:
                _ = _bnb
                if not CUDASetup.get_instance().cuda_available:
                    raise RuntimeError("bitsandbytes CUDA 지원 없음")
            except Exception as e:
                raise RuntimeError(f"bitsandbytes CUDA 사용 불가: {e}") from e

            compute_dtype = _dtype_from_str(quant_cfg.get("bnb_4bit_compute_dtype", "bfloat16"))
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type=quant_cfg.get("bnb_4bit_quant_type", "nf4"),
                bnb_4bit_compute_dtype=compute_dtype,
            )
            kwargs["quantization_config"] = bnb_config

        torch_dtype = torch.bfloat16 if device.startswith("cuda") and torch.cuda.is_available() else torch.float32
        model = AutoModelForCausalLM.from_pretrained(
            model_id_or_path,
            torch_dtype=torch_dtype,
            **kwargs,
        )
        if device.startswith("cuda") and torch.cuda.is_available():
            model = model.to(device)
        return model

    use_4bit = bool(quant_cfg.get("load_in_4bit", False))
    try:
        model = _load(use_4bit)
        if use_4bit:
            fallback_info["mode"] = "qlora"
        else:
            fallback_info["mode"] = "lora"
        return model, tokenizer, fallback_info
    except Exception as e:
        if not smoke:
            raise
        fallback_info["used"] = True
        fallback_info["reason"] = f"4bit 로딩 실패: {type(e).__name__}: {e}"
        model = _load(False)
        fallback_info["mode"] = "lora"
        return model, tokenizer, fallback_info


def _resolve_model_id(cfg: dict[str, Any], override: str | None) -> str:
    if override:
        return override
    model_cfg = cfg.get("model") or {}
    name = model_cfg.get("name_or_path")
    if isinstance(name, str) and name:
        return name
    fallback = model_cfg.get("fallback_name_or_path")
    if isinstance(fallback, str) and fallback:
        return fallback
    raise ValueError("model.name_or_path가 필요함")


def _maybe_limit(items: list[dict[str, Any]], max_samples: int | None) -> list[dict[str, Any]]:
    if max_samples is None:
        return items
    return items[: max(0, int(max_samples))]


def main() -> int:
    root = Path(__file__).resolve().parents[1]

    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="SFT smoke 학습")
    parser.add_argument("--config", default=str(root / "configs" / "train_qlora.yaml"))
    parser.add_argument("--train-dataset", default=str(root / "data" / "train_messages.jsonl"))
    parser.add_argument("--valid-dataset", default=str(root / "data" / "valid_messages.jsonl"))
    parser.add_argument("--output-dir", default=str(root / "checkpoints" / "qlora_smoke"))
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--max-train-samples", type=int, default=None)
    parser.add_argument("--max-eval-samples", type=int, default=None)
    parser.add_argument("--num-train-epochs", type=float, default=None)
    parser.add_argument("--model-id", default=None)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.exists():
        print(f"설정 파일 없음: {cfg_path}", file=sys.stderr)
        return 2

    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}

    device = args.device
    if device == "auto":
        try:
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            device = "cpu"

    if args.smoke:
        if args.max_train_samples is None:
            args.max_train_samples = 40
        if args.max_eval_samples is None:
            args.max_eval_samples = 20

    model_id = _resolve_model_id(cfg, args.model_id)
    quant_cfg = cfg.get("quantization") or {}

    output_dir = args.output_dir or (cfg.get("training") or {}).get("output_dir") or str(root / "checkpoints" / "qlora_smoke")

    pr.start_run(
        run_type="train",
        stage="loading_model",
        model_id=model_id,
        adapter_output_dir=output_dir,
        device=device,
    )

    try:
        model, tokenizer, fallback_info = _load_model_and_tokenizer(
            model_id_or_path=model_id,
            device=device,
            quant_cfg=quant_cfg,
            smoke=args.smoke,
        )
    except Exception as e:
        pr.fail_run(f"모델 로딩 실패: {type(e).__name__}: {e}")
        print(f"모델 로딩 실패: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        return 1

    try:
        from peft import LoraConfig
    except Exception as e:
        pr.fail_run(f"peft import 실패: {e}")
        print(f"peft import 실패: {e}", file=sys.stderr, flush=True)
        return 1

    try:
        from trl import SFTTrainer
    except Exception as e:
        pr.fail_run(f"trl import 실패: {e}")
        print(f"trl import 실패: {e}", file=sys.stderr, flush=True)
        return 1

    from transformers import TrainingArguments
    from datasets import Dataset

    train_path = Path(args.train_dataset)
    valid_path = Path(args.valid_dataset)
    pr.update_stage("loading_dataset")

    if not train_path.exists():
        pr.fail_run(f"train 데이터 없음: {train_path}")
        print(f"train 데이터 없음: {train_path}", file=sys.stderr, flush=True)
        return 2

    train_items = _load_jsonl(train_path)
    valid_items = _load_jsonl(valid_path) if valid_path.exists() else []

    train_texts = _build_text_dataset(train_items, tokenizer, args.max_train_samples)
    valid_texts = _build_text_dataset(valid_items, tokenizer, args.max_eval_samples) if valid_items else []

    train_ds = Dataset.from_list(train_texts)
    eval_ds = Dataset.from_list(valid_texts) if valid_texts else None

    peft_cfg = cfg.get("peft") or {}
    lora_cfg = LoraConfig(
        r=int(peft_cfg.get("r", 16)),
        lora_alpha=int(peft_cfg.get("lora_alpha", 32)),
        lora_dropout=float(peft_cfg.get("lora_dropout", 0.05)),
        target_modules=peft_cfg.get("target_modules") or ["q_proj", "k_proj", "v_proj", "o_proj"],
        bias="none",
        task_type="CAUSAL_LM",
    )

    train_cfg = cfg.get("training") or {}
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    max_steps = int(train_cfg.get("max_steps", -1))
    num_train_epochs = float(train_cfg.get("num_train_epochs", 1))
    if args.num_train_epochs is not None:
        num_train_epochs = float(args.num_train_epochs)
        max_steps = -1
    if args.smoke and max_steps <= 0:
        max_steps = 30

    training_args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=int(train_cfg.get("per_device_train_batch_size", 1)),
        gradient_accumulation_steps=int(train_cfg.get("gradient_accumulation_steps", 4)),
        num_train_epochs=num_train_epochs,
        max_steps=max_steps,
        learning_rate=float(train_cfg.get("learning_rate", 2.0e-4)),
        warmup_ratio=float(train_cfg.get("warmup_ratio", 0.03)),
        logging_steps=int(train_cfg.get("logging_steps", 10)),
        save_steps=int(train_cfg.get("save_steps", 50)),
        eval_steps=int(train_cfg.get("eval_steps", 50)),
        save_total_limit=int(train_cfg.get("save_total_limit", 2)),
        bf16=bool(train_cfg.get("bf16", True)),
        tf32=bool(train_cfg.get("tf32", True)),
        gradient_checkpointing=bool(train_cfg.get("gradient_checkpointing", True)),
        evaluation_strategy="steps" if eval_ds is not None else "no",
        save_strategy="steps",
        report_to=[],
    )

    from transformers import TrainerCallback

    class LiveTrainCallback(TrainerCallback):
        def __init__(self):
            super().__init__()

        def on_log(self, args, state, control, logs=None, **kwargs):
            if not logs:
                return
            loss = logs.get("loss")
            pr.update_train(
                model_id=model_id,
                adapter_output_dir=output_dir,
                device=device,
                epoch=state.epoch,
                num_train_epochs=training_args.num_train_epochs,
                global_step=state.global_step,
                max_steps=state.max_steps,
                loss=float(loss) if loss is not None else None,
            )

    pr.update_stage("training")

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        dataset_text_field="text",
        peft_config=lora_cfg,
        packing=bool((cfg.get("sft") or {}).get("packing", False)),
        max_seq_length=int((cfg.get("sft") or {}).get("max_seq_len", 2048)),
        callbacks=[LiveTrainCallback()],
    )

    try:
        train_result = trainer.train()
    except Exception as e:
        pr.fail_run(f"학습 실패: {type(e).__name__}: {e}")
        raise

    pr.update_stage("saving_adapter")

    adapter_dir = Path(output_dir) / "adapter"
    adapter_dir.mkdir(parents=True, exist_ok=True)
    trainer.model.save_pretrained(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))

    summary = {
        "model_id_or_path": model_id,
        "train_dataset": str(train_path),
        "valid_dataset": str(valid_path),
        "train_samples": len(train_ds),
        "valid_samples": len(eval_ds) if eval_ds is not None else 0,
        "output_dir": str(output_dir),
        "adapter_dir": str(adapter_dir),
        "smoke": bool(args.smoke),
        "fallback": fallback_info,
        "train_metrics": train_result.metrics if hasattr(train_result, "metrics") else {},
    }
    summary_path = Path(output_dir) / "train_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    pr.finish_run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
