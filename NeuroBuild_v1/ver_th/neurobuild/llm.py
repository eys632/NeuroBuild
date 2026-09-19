from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

from . import config


@dataclass
class LLMResponse:
    used: bool
    text: str
    error: Optional[str] = None
    model: Optional[str] = None


class HFChatClient:
    """Small REST client for Hugging Face Inference Providers router."""

    def __init__(self, token: Optional[str] = None, endpoint: Optional[str] = None):
        self.token = (token if token is not None else config.HF_TOKEN).strip()
        self.endpoint = endpoint or config.HF_ROUTER_URL

    @property
    def enabled(self) -> bool:
        return bool(config.USE_HF_LLM and self.token)

    def chat(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.25,
        max_tokens: int = 900,
        json_mode: bool = False,
    ) -> LLMResponse:
        if not self.enabled:
            return LLMResponse(False, "", "HF_TOKEN 또는 USE_HF_LLM이 설정되지 않았습니다.", model)

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": user_prompt.strip()},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            resp = requests.post(self.endpoint, headers=headers, json=payload, timeout=60)
            if resp.status_code >= 400:
                detail = resp.text[:500]
                if resp.status_code == 403 and "Inference Providers" in detail:
                    detail = (
                        "Hugging Face 토큰에 Inference Providers 호출 권한이 없습니다. "
                        "새 User Access Token을 만들 때 'Make calls to Inference Providers' 권한을 켜야 합니다. "
                        f"원문: {detail}"
                    )
                return LLMResponse(False, "", f"HF HTTP {resp.status_code}: {detail}", model)
            data = resp.json()
            text = _extract_chat_text(data)
            if not text:
                return LLMResponse(False, "", f"응답에서 content를 찾지 못했습니다. {str(data)[:500]}", model)
            return LLMResponse(True, text.strip(), None, model)
        except Exception as exc:  # noqa: BLE001
            return LLMResponse(False, "", str(exc), model)


def _extract_chat_text(data: Dict[str, Any]) -> str:
    choices = data.get("choices") or []
    if choices:
        msg = choices[0].get("message") or {}
        if isinstance(msg, dict) and msg.get("content"):
            return str(msg["content"])
        if choices[0].get("text"):
            return str(choices[0]["text"])
    if data.get("generated_text"):
        return str(data["generated_text"])
    if isinstance(data.get("data"), list) and data["data"]:
        return str(data["data"][0])
    return ""


def extract_json_object(text: str) -> Dict[str, Any]:
    """Extract the first JSON object from LLM text safely."""
    if not text:
        raise ValueError("empty text")
    clean = text.strip()
    clean = re.sub(r"^```(?:json)?", "", clean, flags=re.I).strip()
    clean = re.sub(r"```$", "", clean).strip()
    try:
        parsed = json.loads(clean)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    match = re.search(r"\{.*\}", clean, re.S)
    if not match:
        raise ValueError("No JSON object found")
    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("JSON root is not object")
    return parsed


def bulletize(text: str, max_items: int = 6) -> List[str]:
    lines = []
    for line in text.splitlines():
        stripped = line.strip(" \t-*•0123456789.)")
        if stripped:
            lines.append(stripped)
    if not lines and text.strip():
        lines = [text.strip()]
    return lines[:max_items]
