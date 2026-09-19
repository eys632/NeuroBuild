from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
OUTPUT_DIR = ROOT_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

if load_dotenv:
    load_dotenv(ROOT_DIR / ".env")


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class TeamModels:
    planning: str
    legal: str
    design: str
    budget: str
    architecture: str


USE_HF_LLM = _bool_env("USE_HF_LLM", False)
HF_TOKEN = os.getenv("HF_TOKEN", "").strip()
HF_ROUTER_URL = os.getenv("HF_ROUTER_URL", "https://router.huggingface.co/v1/chat/completions").strip()
LAW_OPEN_API_OC = os.getenv("LAW_OPEN_API_OC", "").strip()
NEUROBUILD_PORT = int(os.getenv("NEUROBUILD_PORT", "8502"))

TEAM_MODELS = TeamModels(
    planning=os.getenv("HF_MODEL_PLANNING", "Qwen/Qwen2.5-7B-Instruct"),
    legal=os.getenv("HF_MODEL_LEGAL", "Qwen/Qwen2.5-7B-Instruct"),
    design=os.getenv("HF_MODEL_DESIGN", "Qwen/Qwen2.5-7B-Instruct"),
    budget=os.getenv("HF_MODEL_BUDGET", "Qwen/Qwen2.5-7B-Instruct"),
    architecture=os.getenv("HF_MODEL_ARCHITECTURE", "Qwen/Qwen2.5-Coder-7B-Instruct"),
)

DEFAULT_BRIEF = (
    "남자 4명이서 살기 좋은 총 비용 3억원 이하의 집을 짓고자 해.\n"
    "방은 4개가 좋겠고 다같이 시간을 보낼 수 있도록 거실을 크게 만들어줘.\n"
    "1층집으로 넓게 만들어줘."
)
