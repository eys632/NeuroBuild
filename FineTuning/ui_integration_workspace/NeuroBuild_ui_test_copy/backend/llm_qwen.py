from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


MODEL_ID_DEFAULT = "Qwen/Qwen2.5-7B-Instruct"
VLLM_BASE_URL_ENV = "VLLM_BASE_URL"
VLLM_MODEL_ENV = "VLLM_MODEL"
VLLM_TIMEOUT_SEC_ENV = "VLLM_TIMEOUT_SEC"

NB_LLM_MODE_ENV = "NB_LLM_MODE"
NB_MODEL_ID_ENV = "NB_MODEL_ID"
NB_ADAPTER_PATH_ENV = "NB_ADAPTER_PATH"
NB_VLLM_BASE_URL_ENV = "NB_VLLM_BASE_URL"
NB_VLLM_MODEL_ENV = "NB_VLLM_MODEL"
NB_VLLM_TIMEOUT_SEC_ENV = "NB_VLLM_TIMEOUT_SEC"


@dataclass(frozen=True)
class LlmOutput:
    data: dict[str, Any]
    raw_text: str


_model_lock = threading.Lock()
_model = None
_tokenizer = None
_loaded_info: dict[str, Any] = {
    "mode": None,
    "model_id": None,
    "adapter_path": None,
    "device": None,
    "loaded": False,
}


def _get_llm_mode() -> str:
    mode = (os.environ.get(NB_LLM_MODE_ENV) or "base").strip().lower()
    if mode not in ("base", "lora", "vllm"):
        mode = "base"
    return mode


def _get_model_id() -> str:
    return (os.environ.get(NB_MODEL_ID_ENV) or MODEL_ID_DEFAULT).strip()


def _get_adapter_path() -> str | None:
    val = (os.environ.get(NB_ADAPTER_PATH_ENV) or "").strip()
    return val or None


def _get_vllm_base_url() -> str | None:
    val = (os.environ.get(NB_VLLM_BASE_URL_ENV) or os.environ.get(VLLM_BASE_URL_ENV) or "").strip()
    return val or None


def _get_vllm_model() -> str | None:
    val = (os.environ.get(NB_VLLM_MODEL_ENV) or os.environ.get(VLLM_MODEL_ENV) or "").strip()
    return val or None


def _get_cache_dir() -> str | None:
    env = os.environ.get("HF_HOME")
    if env:
        Path(env).mkdir(parents=True, exist_ok=True)
        return env
    default_dir = Path(__file__).resolve().parents[1] / "models"
    default_dir.mkdir(parents=True, exist_ok=True)
    return str(default_dir)


def load_model(model_id: str | None = None):
    global _model, _tokenizer
    with _model_lock:
        mode = _get_llm_mode()
        if mode == "vllm":
            raise RuntimeError("NB_LLM_MODE=vllm에서는 로컬 모델을 로딩하지 않습니다")

        if not model_id:
            model_id = _get_model_id()

        adapter_path = _get_adapter_path() if mode == "lora" else None

        if (
            _model is not None
            and _tokenizer is not None
            and _loaded_info.get("mode") == mode
            and _loaded_info.get("model_id") == model_id
            and _loaded_info.get("adapter_path") == adapter_path
        ):
            return _model, _tokenizer

        _model = None
        _tokenizer = None

        cache_dir = _get_cache_dir()
        tokenizer = AutoTokenizer.from_pretrained(model_id, cache_dir=cache_dir, trust_remote_code=True)

        dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
        common_kwargs = dict(
            cache_dir=cache_dir,
            device_map={"": 0} if torch.cuda.is_available() else None,
            trust_remote_code=True,
        )
        try:
            model = AutoModelForCausalLM.from_pretrained(model_id, dtype=dtype, **common_kwargs)
        except TypeError:
            model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=dtype, **common_kwargs)

        if mode == "lora":
            if not adapter_path:
                raise RuntimeError(f"NB_LLM_MODE=lora인데 {NB_ADAPTER_PATH_ENV}가 비어 있습니다")
            try:
                from peft import PeftModel
            except Exception as e:
                raise RuntimeError(f"peft import 실패: {e}") from e
            model = PeftModel.from_pretrained(model, adapter_path)

        model.eval()

        device = "cuda" if torch.cuda.is_available() else "cpu"
        _loaded_info.update(
            {
                "mode": mode,
                "model_id": model_id,
                "adapter_path": adapter_path,
                "device": device,
                "loaded": True,
            }
        )

        _model, _tokenizer = model, tokenizer
        return model, tokenizer


def _vllm_enabled() -> bool:
    return _get_llm_mode() == "vllm"


def _call_vllm_chat(*, messages: list[dict[str, str]], max_tokens: int) -> str:
    base_url = (_get_vllm_base_url() or "").strip().rstrip("/")
    if not base_url:
        raise ValueError(f"{NB_VLLM_BASE_URL_ENV} 또는 {VLLM_BASE_URL_ENV}가 설정되지 않았습니다")

    model_name = (_get_vllm_model() or "").strip()
    if not model_name:
        raise ValueError(
            f"{NB_VLLM_MODEL_ENV} 또는 {VLLM_MODEL_ENV}가 설정되지 않았습니다. 예: export {NB_VLLM_MODEL_ENV}=a100-qwen"
        )

    timeout = float(
        os.environ.get(NB_VLLM_TIMEOUT_SEC_ENV, os.environ.get(VLLM_TIMEOUT_SEC_ENV, "600"))
    )

    url = f"{base_url}/v1/chat/completions"
    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": 0.0,
        "max_tokens": int(max_tokens),
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            err_body = ""
        raise RuntimeError(f"vLLM HTTP {e.code}: {err_body or e.reason}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to call vLLM at {url}: {type(e).__name__}: {e}") from e

    parsed = json.loads(body)
    content = (((parsed.get("choices") or [{}])[0]).get("message") or {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError(f"vLLM response missing content: {body[:5000]}")
    return content


_SCHEMA_INSTRUCTIONS = """너는 건축 설계 요구사항을 구조화하는 도우미다.
사용자가 입력한 한국어 프롬프트에서 공간/요구사항/인접관계/우선순위를 추출해 JSON으로만 답변해라.

반드시 아래 JSON 스키마 형태로 출력한다. 다른 텍스트를 절대 포함하지 않는다.

중요: spaces[].type은 아래 중 '하나의 값'만 사용한다. (파이프(|)로 연결된 선택지 문자열을 그대로 출력하지 말 것)
- bedroom
- living
- kitchen
- bathroom
- balcony
- storage
- entrance
- other

{
    "spaces": [
        {"type": "bedroom", "count": 1, "notes": "..."}
    ],
    "constraints": {
        "open_plan": ["living+kitchen"],
        "bathroom_count": 2,
        "exterior_door": true,
        "balcony": {"style": "long", "connects": ["living", "bedroom"]}
    },
    "windows": {
        "perimeter_windows_per_wall": 0,
        "size_preset": "medium",
        "avoid_bathroom_zone": false,
        "notes": "예: 모든 외벽에 창문 1개씩"
    },
    "adjacency": [
        {"a": "living", "b": "kitchen", "relation": "open"},
        {"a": "living", "b": "balcony", "relation": "connect"}
    ],
    "priorities": {
        "must": ["..."],
        "should": ["..."],
        "optional": ["..."]
    },
    "assumptions": ["..."],
    "proposed_dimensions_m": {
        "width_m": 12.0,
        "depth_m": 9.0,
        "height_m": 3.0
    }
}

치수가 명시되지 않으면 proposed_dimensions_m는 합리적으로 제안하되, 확신이 없으면 기본값(12,9,3)을 유지한다.
"""


def interpret_prompt(prompt: str, *, model_id: str | None = None, max_new_tokens: int = 512) -> LlmOutput:
    messages = [
        {"role": "system", "content": _SCHEMA_INSTRUCTIONS},
        {"role": "user", "content": prompt.strip()},
    ]

    if _vllm_enabled():
        generated_text = _call_vllm_chat(messages=messages, max_tokens=max_new_tokens)
        raw = _extract_best_json(generated_text)
        data = json.loads(raw)
        return LlmOutput(data=data, raw_text=raw)

    model, tokenizer = load_model(model_id)

    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([text], return_tensors="pt")

    if torch.cuda.is_available():
        inputs = {k: v.to(model.device) for k, v in inputs.items()}

    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            repetition_penalty=1.05,
        )

    input_len = inputs["input_ids"].shape[-1]
    generated_tokens = out[0][input_len:]
    generated_text = tokenizer.decode(generated_tokens, skip_special_tokens=True)

    raw = _extract_best_json(generated_text)
    data = json.loads(raw)
    return LlmOutput(data=data, raw_text=raw)


_DELTA_SCHEMA_INSTRUCTIONS = """너는 건축 설계 편집(수정) 요청을 '작업 목록(Ops)'으로 변환하는 도우미다.
사용자가 입력한 한국어 프롬프트는 '기존 설계에 대한 변경 요청'이다.

반드시 아래 JSON 스키마 형태로만 출력한다. 다른 텍스트를 절대 포함하지 않는다.

중요 규칙:
- edits는 '지원되는 op'만 포함한다.
- 애매하면 op를 만들지 말고 notes에 짧게 이유를 남긴다.
- value가 필요한 op는 value를 반드시 채운다.

지원 op 목록:
- set_windows_per_wall (value: int)
- remove_all_windows
- set_windows_size_preset (value: small|medium|large)
- set_avoid_bathroom_zone (value: bool)
- set_exterior_door (value: bool)
- add_exterior_door (value: bool)  # alias
- set_bathroom_count (value: int)
- add_bathroom (value: int, default 1)

출력 JSON:
{
  "edits": [
    {"op": "remove_all_windows"}
  ],
  "notes": ""
}

예:
- "창문을 모두 제거해" -> {"op":"remove_all_windows"}
- "모든 벽에 창문 1개씩" -> {"op":"set_windows_per_wall","value":1}
- "창문을 벽마다 2개" -> {"op":"set_windows_per_wall","value":2}
- "창문 크게" -> {"op":"set_windows_size_preset","value":"large"}
- "환기창만" / "작게" -> {"op":"set_windows_size_preset","value":"small"}
- "욕실 쪽 외벽 창문은 빼줘" -> {"op":"set_avoid_bathroom_zone","value":true}
- "외벽에 밖으로 나갈 수 있는 문 만들어줘" -> {"op":"set_exterior_door","value":true}
- "화장실 1개로 해" -> {"op":"set_bathroom_count","value":1}
- "화장실 하나 추가해줘" / "화장실 더 만들어줘" -> {"op":"add_bathroom"}
"""


def interpret_delta_prompt(
    prompt: str,
    *,
    model_id: str | None = None,
    max_new_tokens: int = 256,
    current_state: dict[str, Any] | None = None,
) -> LlmOutput:
    messages = [{"role": "system", "content": _DELTA_SCHEMA_INSTRUCTIONS}]
    if current_state:
        # Give the model grounding so it can decide between set_* vs add_* (increment) operations.
        # Keep it as machine-readable JSON.
        messages.append(
            {
                "role": "system",
                "content": "현재 설계 상태(참고용 JSON):\n" + json.dumps(current_state, ensure_ascii=False),
            }
        )
    messages.append({"role": "user", "content": prompt.strip()})

    if _vllm_enabled():
        generated_text = _call_vllm_chat(messages=messages, max_tokens=max_new_tokens)
        raw = _extract_best_json(generated_text)
        data = json.loads(raw)
        return LlmOutput(data=data, raw_text=raw)

    model, tokenizer = load_model(model_id)

    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([text], return_tensors="pt")

    if torch.cuda.is_available():
        inputs = {k: v.to(model.device) for k, v in inputs.items()}

    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            repetition_penalty=1.05,
        )

    input_len = inputs["input_ids"].shape[-1]
    generated_tokens = out[0][input_len:]
    generated_text = tokenizer.decode(generated_tokens, skip_special_tokens=True)

    raw = _extract_best_json(generated_text)
    data = json.loads(raw)
    return LlmOutput(data=data, raw_text=raw)


def _extract_best_json(text: str) -> str:
    decoder = json.JSONDecoder()
    best_start: int | None = None
    best_end: int | None = None

    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            _, end = decoder.raw_decode(text[i:])
        except json.JSONDecodeError:
            continue

        end_abs = i + end
        if best_start is None or (end_abs - i) > (best_end - best_start):
            best_start, best_end = i, end_abs

    if best_start is None or best_end is None:
        raise ValueError("No JSON object found in model output")

    return text[best_start:best_end]


def get_llm_status() -> dict[str, Any]:
    mode = _get_llm_mode()
    info = dict(_loaded_info)
    info["mode"] = mode
    info["model_id"] = _get_model_id()
    info["adapter_path"] = _get_adapter_path() if mode == "lora" else None
    info["loaded"] = bool(info.get("loaded"))
    return info
