from __future__ import annotations

import re
from dataclasses import replace
from typing import Any, Dict

from . import config
from .llm import HFChatClient, extract_json_object
from .models import UserBrief


KOREAN_NUMS = {
    "일": 1,
    "한": 1,
    "하나": 1,
    "이": 2,
    "두": 2,
    "둘": 2,
    "삼": 3,
    "세": 3,
    "셋": 3,
    "사": 4,
    "네": 4,
    "넷": 4,
    "오": 5,
    "다섯": 5,
    "육": 6,
    "여섯": 6,
    "칠": 7,
    "일곱": 7,
    "팔": 8,
    "여덟": 8,
    "구": 9,
    "아홉": 9,
    "십": 10,
    "열": 10,
}


def parse_brief(text: str, mode: str = "new") -> UserBrief:
    fallback = parse_brief_regex(text, mode=mode)
    if config.USE_HF_LLM and config.HF_TOKEN:
        return parse_brief_with_llm(text, fallback)
    return fallback


def parse_brief_update(text: str, previous: UserBrief, mode: str = "modify") -> UserBrief:
    fallback = parse_brief_update_regex(text, previous, mode=mode)
    if config.USE_HF_LLM and config.HF_TOKEN:
        return parse_brief_update_with_llm(text, previous, fallback)
    return fallback


def parse_brief_regex(text: str, mode: str = "new") -> UserBrief:
    t = text or ""
    brief = UserBrief(raw_text=t, mode=mode)

    people = _find_number_near(t, ["명", "사람", "인", "가구원"])
    if people:
        brief.occupants = max(1, min(30, people))

    rooms = _find_number_near(t, ["방", "침실", "룸"])
    if rooms:
        brief.room_count = max(1, min(20, rooms))

    floors = _parse_floor_count(t)
    if floors:
        brief.floors = max(1, min(10, floors))
        _normalize_floor_style(brief)

    budget = _parse_budget(t)
    if budget:
        brief.budget_krw = max(20_000_000, budget)

    if any(word in t for word in ["거실을 크게", "큰 거실", "넓은 거실", "다같이", "다 같이", "커뮤니티", "라운지"]):
        brief.living_room_preference = "large"

    styles = []
    for keyword in [
        "미래",
        "미니멀",
        "모던",
        "자연",
        "친환경",
        "코리빙",
        "공유",
        "복층",
        "단층",
        "가성비",
        "프리미엄",
    ]:
        if keyword in t:
            styles.append(keyword)
    if styles:
        brief.style_keywords = styles

    loc_match = re.search(r"([가-힣A-Za-z0-9]+(?:시|군|구|읍|면|동|리))", t)
    if loc_match:
        brief.location_hint = loc_match.group(1)

    special = []
    for token in ["주차", "테라스", "마당", "창고", "채광", "환기", "방음", "반려동물", "태양광", "무장애"]:
        if token in t:
            special.append(token)
    brief.special_requirements = special

    return brief


def parse_brief_update_regex(text: str, previous: UserBrief, mode: str = "modify") -> UserBrief:
    t = text or ""
    brief = replace(
        previous,
        raw_text=f"{previous.raw_text}\n\n[수정 요청]\n{t}".strip(),
        mode=mode,
        style_keywords=list(previous.style_keywords),
        special_requirements=list(previous.special_requirements),
        source="regex_update",
    )

    people = _find_number_near(t, ["명", "사람", "인", "가구원"])
    if people:
        brief.occupants = max(1, min(30, people))

    room_target = _find_number_near(t, ["방", "침실", "룸"]) or _find_number_after_prefix(t, ["방", "침실", "룸"])
    room_delta = _find_delta(t, ["방", "침실", "룸"])
    if room_target and _looks_like_target_count(t):
        brief.room_count = max(1, min(20, room_target))
    elif room_delta:
        brief.room_count = max(1, min(20, brief.room_count + room_delta))
    elif room_target:
        brief.room_count = max(1, min(20, room_target))

    floors = _parse_floor_count(t)
    if floors:
        brief.floors = max(1, min(10, floors))
        _normalize_floor_style(brief)

    budget = _parse_budget(t)
    if budget:
        brief.budget_krw = max(20_000_000, budget)

    if "거실" in t or "라운지" in t or "공용" in t:
        if any(word in t for word in ["작게", "줄", "축소", "보통", "평범"]):
            brief.living_room_preference = "normal"
        if any(word in t for word in ["크게", "넓", "확장", "키워", "큰"]):
            brief.living_room_preference = "large"

    for keyword in [
        "미래",
        "미니멀",
        "모던",
        "자연",
        "친환경",
        "코리빙",
        "공유",
        "복층",
        "단층",
        "가성비",
        "프리미엄",
    ]:
        if keyword in t and keyword not in brief.style_keywords:
            brief.style_keywords.append(keyword)

    loc_match = re.search(r"([가-힣A-Za-z0-9]+(?:시|군|구|읍|면|동|리))", t)
    if loc_match:
        brief.location_hint = loc_match.group(1)

    for token in ["주차", "테라스", "마당", "창고", "채광", "환기", "방음", "반려동물", "태양광", "무장애"]:
        if token in t and token not in brief.special_requirements:
            brief.special_requirements.append(token)

    return brief


def parse_brief_with_llm(text: str, fallback: UserBrief) -> UserBrief:
    client = HFChatClient()
    system = """
너는 Neurobuild 건축 기획팀 AI다. 사용자의 한국어 건축 요청을 실제 설계 파라미터 JSON으로 구조화한다.
반드시 JSON 객체 하나만 반환한다. 마크다운, 설명, 코드블록은 금지한다.
스키마:
{
  "occupants": number,
  "budget_krw": number,
  "room_count": number,
  "floors": number,
  "living_room_preference": "normal" | "large",
  "style_keywords": string[],
  "location_hint": string | null,
  "special_requirements": string[],
  "confidence": number
}
확실하지 않은 값은 fallback을 따른다. 한국어 금액 표현은 원 단위 정수로 변환한다.
"""
    user = f"""
사용자 원문:
{text}

fallback 해석:
{fallback.to_dict()}
"""
    resp = client.chat(config.TEAM_MODELS.planning, system, user, temperature=0.1, max_tokens=550, json_mode=True)
    if not resp.used:
        fallback.source = f"regex:llm_failed:{resp.error}"
        return fallback
    try:
        data = extract_json_object(resp.text)
        merged = merge_brief(fallback, data)
        merged.source = "huggingface_router"
        return merged
    except Exception as exc:  # noqa: BLE001
        fallback.source = f"regex:json_failed:{exc}"
        return fallback


def parse_brief_update_with_llm(text: str, previous: UserBrief, fallback: UserBrief) -> UserBrief:
    client = HFChatClient()
    system = """
너는 Neurobuild 건축 기획팀 AI다. 기존 도면 조건과 사용자의 수정 요청을 합쳐 최종 설계 파라미터 JSON을 만든다.
수정 요청에 없는 값은 반드시 기존 도면 조건을 유지한다.
반드시 JSON 객체 하나만 반환한다. 마크다운, 설명, 코드블록은 금지한다.
스키마:
{
  "occupants": number,
  "budget_krw": number,
  "room_count": number,
  "floors": number,
  "living_room_preference": "normal" | "large",
  "style_keywords": string[],
  "location_hint": string | null,
  "special_requirements": string[],
  "confidence": number
}
"""
    user = f"""
기존 도면 조건:
{previous.to_dict()}

사용자 수정 요청:
{text}

fallback 병합 결과:
{fallback.to_dict()}
"""
    resp = client.chat(config.TEAM_MODELS.planning, system, user, temperature=0.1, max_tokens=550, json_mode=True)
    if not resp.used:
        fallback.source = f"regex_update:llm_failed:{resp.error}"
        return fallback
    try:
        data = extract_json_object(resp.text)
        merged = merge_brief(fallback, data)
        merged.raw_text = fallback.raw_text
        merged.mode = "modify"
        merged.source = "huggingface_router_update"
        return merged
    except Exception as exc:  # noqa: BLE001
        fallback.source = f"regex_update:json_failed:{exc}"
        return fallback


def merge_brief(brief: UserBrief, data: Dict[str, Any]) -> UserBrief:
    def int_field(name: str, default: int, low: int, high: int) -> int:
        try:
            return max(low, min(high, int(float(data.get(name, default)))))
        except Exception:
            return default

    brief.occupants = int_field("occupants", brief.occupants, 1, 30)
    brief.budget_krw = int_field("budget_krw", brief.budget_krw, 20_000_000, 5_000_000_000)
    brief.room_count = int_field("room_count", brief.room_count, 1, 20)
    brief.floors = int_field("floors", brief.floors, 1, 10)

    living = str(data.get("living_room_preference", brief.living_room_preference)).lower()
    brief.living_room_preference = "large" if "large" in living or "크" in living or "넓" in living else "normal"

    styles = data.get("style_keywords")
    if isinstance(styles, list) and styles:
        brief.style_keywords = [str(x).strip() for x in styles if str(x).strip()][:10]

    loc = data.get("location_hint")
    if loc:
        brief.location_hint = str(loc)

    special = data.get("special_requirements")
    if isinstance(special, list):
        brief.special_requirements = [str(x).strip() for x in special if str(x).strip()][:12]

    try:
        brief.confidence = float(data.get("confidence", brief.confidence))
    except Exception:
        pass
    return brief


def _find_number_near(text: str, suffixes: list[str]) -> int | None:
    for suffix in suffixes:
        match = re.search(rf"(\d+)\s*{re.escape(suffix)}", text)
        if match:
            return int(match.group(1))
        for word, number in KOREAN_NUMS.items():
            if re.search(rf"{word}\s*{re.escape(suffix)}", text):
                return number
    return None


def _find_number_after_prefix(text: str, prefixes: list[str]) -> int | None:
    for prefix in prefixes:
        match = re.search(rf"{re.escape(prefix)}(?:을|를|은|는)?\s*(\d+)\s*(?:개|칸)?", text)
        if match:
            return int(match.group(1))
        for word, number in KOREAN_NUMS.items():
            if re.search(rf"{re.escape(prefix)}(?:을|를|은|는)?\s*{word}\s*(?:개|칸)?", text):
                return number
    return None


def _parse_floor_count(text: str) -> int | None:
    compact = text.replace(" ", "")
    explicit: list[tuple[int, int]] = []
    general: list[tuple[int, int]] = []

    number_pattern = r"(\d+|" + "|".join(sorted(map(re.escape, KOREAN_NUMS), key=len, reverse=True)) + r")"
    for match in re.finditer(rf"{number_pattern}(?:층집|층주택|층짜리|층건물|floor)", compact, flags=re.IGNORECASE):
        explicit.append((_number_token(match.group(1)), match.end()))
    for match in re.finditer(rf"{number_pattern}층", compact):
        general.append((_number_token(match.group(1)), match.end()))

    if "단층" in compact:
        explicit.append((1, compact.rfind("단층") + 2))
    if "복층" in compact:
        explicit.append((2, compact.rfind("복층") + 2))

    candidates = explicit or general
    if not candidates:
        return None
    if explicit:
        return max(explicit, key=lambda item: item[1])[0]
    return max(number for number, _ in general)


def _number_token(token: str) -> int:
    if token.isdigit():
        return int(token)
    return KOREAN_NUMS[token]


def _normalize_floor_style(brief: UserBrief) -> None:
    brief.style_keywords = [keyword for keyword in brief.style_keywords if keyword not in {"단층", "복층"}]
    if brief.floors == 1:
        if "단층" not in brief.style_keywords:
            brief.style_keywords.append("단층")
    else:
        keyword = f"{brief.floors}층"
        if keyword not in brief.style_keywords:
            brief.style_keywords.append(keyword)


def _looks_like_target_count(text: str) -> bool:
    return bool(re.search(r"\d+\s*(?:개|칸)?\s*(?:로|으로|까지)", text)) or any(
        re.search(rf"{word}\s*(?:개|칸)?\s*(?:로|으로|까지)", text) for word in KOREAN_NUMS
    )


def _find_delta(text: str, nouns: list[str]) -> int | None:
    if not any(noun in text for noun in nouns):
        return None
    number = _find_number_after_prefix(text, nouns)
    if number is None:
        number = _find_number_near(text, ["개", "칸"]) or 1
    if any(word in text for word in ["추가", "늘", "더", "많", "증가"]):
        return number
    if any(word in text for word in ["삭제", "줄", "빼", "감소", "축소"]):
        return -number
    return None


def _parse_budget(text: str) -> int | None:
    compact = text.replace(",", "").replace(" ", "")

    match = re.search(r"(\d+(?:\.\d+)?)억(?:원)?", compact)
    if match:
        return int(float(match.group(1)) * 100_000_000)

    match = re.search(r"(\d+(?:\.\d+)?)천만원", compact)
    if match:
        return int(float(match.group(1)) * 10_000_000)

    match = re.search(r"(\d+(?:\.\d+)?)백만원", compact)
    if match:
        return int(float(match.group(1)) * 1_000_000)

    match = re.search(r"(\d+(?:\.\d+)?)만원", compact)
    if match:
        return int(float(match.group(1)) * 10_000)

    match = re.search(r"(\d{7,})원?", compact)
    if match:
        return int(match.group(1))

    return None
