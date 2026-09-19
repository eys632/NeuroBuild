from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class BuildingParams:
    width_m: float = 10.0
    depth_m: float = 8.0
    height_m: float = 3.0
    wall_thickness_m: float = 0.2
    slab_thickness_m: float = 0.2
    windows_per_wall: int = 0
    windows_size_preset: str = "medium"  # small|medium|large
    avoid_bathroom_zone: bool = False
    exterior_door: bool = False


@dataclass(frozen=True)
class BuildingParamsDelta:
    width_m: float | None = None
    depth_m: float | None = None
    height_m: float | None = None
    wall_thickness_m: float | None = None
    slab_thickness_m: float | None = None
    windows_per_wall: int | None = None
    windows_size_preset: str | None = None
    avoid_bathroom_zone: bool | None = None
    exterior_door: bool | None = None

_NUMBER = r"(?P<val>\d+(?:[\.,]\d+)?)"
_UNIT = r"(?P<unit>mm|millimeter|millimeters|밀리미터|밀리|cm|centimeter|centimeters|센티미터|센치|m|meter|meters|미터)?"


def _to_meters(value: float, unit: str | None) -> float:
    if not unit:
        return value
    unit = unit.strip().lower()
    if unit in ("m", "meter", "meters", "미터"):
        return value
    if unit in ("cm", "centimeter", "centimeters", "센티미터", "센치"):
        return value / 100.0
    if unit in ("mm", "millimeter", "millimeters", "밀리미터", "밀리"):
        return value / 1000.0
    return value


def _parse_first_measure_m(prompt: str, keys: list[str]) -> float | None:
    # Accept patterns like: "width 12", "폭 12m", "가로=12.5미터", "벽두께 200mm"
    for key in keys:
        pattern = re.compile(rf"{key}\s*(?:=|:)?\s*{_NUMBER}\s*{_UNIT}", re.IGNORECASE)
        m = pattern.search(prompt)
        if m:
            raw = m.group("val").replace(",", ".")
            val = float(raw)
            unit = m.group("unit")
            return _to_meters(val, unit)
    return None


def parse_prompt(prompt: str) -> BuildingParams:
    """Very small MVP prompt parser.

    목표: LLM 없이도 "10x8x3" 같은 기본 치수 변경을 할 수 있게.
    - width/가로/폭
    - depth/세로/깊이
    - height/높이/층고
    - wall thickness/벽두께
    """

    prompt = prompt.strip()

    delta = parse_prompt_delta(prompt)

    width = delta.width_m
    depth = delta.depth_m
    height = delta.height_m
    wall_thickness = delta.wall_thickness_m
    slab_thickness = delta.slab_thickness_m
    windows_per_wall = delta.windows_per_wall
    windows_size_preset = delta.windows_size_preset
    avoid_bathroom_zone = delta.avoid_bathroom_zone
    exterior_door = delta.exterior_door

    params = BuildingParams(
        width_m=width if width is not None else BuildingParams.width_m,
        depth_m=depth if depth is not None else BuildingParams.depth_m,
        height_m=height if height is not None else BuildingParams.height_m,
        wall_thickness_m=wall_thickness if wall_thickness is not None else BuildingParams.wall_thickness_m,
        slab_thickness_m=slab_thickness if slab_thickness is not None else BuildingParams.slab_thickness_m,
        windows_per_wall=windows_per_wall if windows_per_wall is not None else BuildingParams.windows_per_wall,
        windows_size_preset=windows_size_preset if windows_size_preset is not None else BuildingParams.windows_size_preset,
        avoid_bathroom_zone=avoid_bathroom_zone if avoid_bathroom_zone is not None else BuildingParams.avoid_bathroom_zone,
        exterior_door=exterior_door if exterior_door is not None else BuildingParams.exterior_door,
    )

    # Basic sanity clamps for MVP
    return BuildingParams(
        width_m=max(1.0, min(200.0, params.width_m)),
        depth_m=max(1.0, min(200.0, params.depth_m)),
        height_m=max(2.0, min(50.0, params.height_m)),
        wall_thickness_m=max(0.05, min(2.0, params.wall_thickness_m)),
        slab_thickness_m=max(0.05, min(2.0, params.slab_thickness_m)),
        windows_per_wall=max(0, min(10, int(params.windows_per_wall))),
        windows_size_preset=(
            params.windows_size_preset
            if params.windows_size_preset in ("small", "medium", "large")
            else BuildingParams.windows_size_preset
        ),
        avoid_bathroom_zone=bool(params.avoid_bathroom_zone),
        exterior_door=bool(params.exterior_door),
    )


def parse_prompt_delta(prompt: str) -> BuildingParamsDelta:
    """Parse prompt as a *delta* (missing fields stay None).

    This enables multi-turn edits: apply only what user explicitly mentions.
    """

    prompt = (prompt or "").strip()

    width = _parse_first_measure_m(prompt, ["width", "가로", "폭"])
    depth = _parse_first_measure_m(prompt, ["depth", "세로", "깊이"])
    height = _parse_first_measure_m(prompt, ["height", "높이", "층고"])
    wall_thickness = _parse_first_measure_m(
        prompt,
        [
            "wall_thickness",
            "wall thickness",
            "wall",
            r"벽\s*두께",
            "벽두께",
            "thickness",
        ],
    )
    slab_thickness = _parse_first_measure_m(
        prompt,
        [
            "slab_thickness",
            "slab thickness",
            "slab",
            r"슬래브\s*두께",
            r"바닥\s*두께",
            "바닥",
            "슬래브",
            "floor",
        ],
    )

    # Also accept shorthand like "10x8x3" or "10m x 8m x 3m"
    m = re.search(
        r"(\d+(?:[\.,]\d+)?)\s*(mm|cm|m|밀리|센치|미터)?\s*[x×]\s*"
        r"(\d+(?:[\.,]\d+)?)\s*(mm|cm|m|밀리|센치|미터)?\s*[x×]\s*"
        r"(\d+(?:[\.,]\d+)?)\s*(mm|cm|m|밀리|센치|미터)?",
        prompt,
        re.IGNORECASE,
    )
    if m:
        w = _to_meters(float(m.group(1).replace(",", ".")), m.group(2))
        d = _to_meters(float(m.group(3).replace(",", ".")), m.group(4))
        h = _to_meters(float(m.group(5).replace(",", ".")), m.group(6))
        width = width or w
        depth = depth or d
        height = height or h

    if width is None and depth is None and height is None:
        m2 = re.search(r"(?:size|크기)\s*(?:=|:)?\s*(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)", prompt, re.IGNORECASE)
        if m2:
            width, depth, height = (float(m2.group(1)), float(m2.group(2)), float(m2.group(3)))

    windows_per_wall: int | None = None
    # Negative intent first: "창문 모두 제거", "창문 없애" 등
    if re.search(r"(창문|창)\s*(?:을|를)?\s*(?:전부|모두|다)\s*(?:제거|삭제|없애|없애줘|빼|빼줘|없애\s*줘)", prompt, re.IGNORECASE):
        windows_per_wall = 0

    # Explicit removal: "창문 제거", "창문 없애", "창문 다 빼" => 0
    if re.search(r"(창문|창)\s*(을|를)?\s*(전부|모두|다|전체)\s*(제거|삭제|없애|없애\s*줘|빼|빼\s*줘)", prompt, re.IGNORECASE) or re.search(
        r"(창문|창)\s*(제거|삭제|없애|없애\s*줘|빼|빼\s*줘)", prompt, re.IGNORECASE
    ):
        windows_per_wall = 0
    # Natural language: "모든 벽에 창문 1개", "각 외벽마다 창문 2개씩" 등
    mwin = re.search(
        r"(?:모든|각|외벽|벽)\s*.*?(?:마다|에)?\s*.*?(?:창문|창)\s*(?:을|를|이|가|은|는|에)?\s*"
        r"(?:(\d+)\s*개?\s*씩?|(\d+)|하나\s*씩?|한\s*개\s*씩?|1\s*개\s*씩?)",
        prompt,
        re.IGNORECASE,
    )
    if mwin and windows_per_wall is None:
        if mwin.group(1):
            windows_per_wall = int(mwin.group(1))
        elif mwin.group(2):
            windows_per_wall = int(mwin.group(2))
        else:
            windows_per_wall = 1

    windows_size_preset: str | None = None
    # Size/intent keywords
    if re.search(r"(큰\s*창|대형\s*창|크게\s*해|크게\s*해줘|크게\s*|통창)", prompt, re.IGNORECASE):
        windows_size_preset = "large"
    elif re.search(r"(작은\s*창|작게\s*해|작게\s*해줘|작게\s*|환기\s*창|환기창|환기용\s*창)", prompt, re.IGNORECASE):
        windows_size_preset = "small"
    elif re.search(r"(중간\s*크기\s*창|보통\s*창|기본\s*창)", prompt, re.IGNORECASE):
        windows_size_preset = "medium"

    avoid_bathroom_zone: bool | None = None
    # Bathroom side exclusion: "욕실 쪽 외벽 창문은 빼줘" 등
    if re.search(r"(욕실|화장실)", prompt) and re.search(r"(창문|창)", prompt):
        if re.search(r"(빼\s*줘|빼줘|제외|없애|없애\s*줘|두지\s*마|두지\s*말고|금지)", prompt):
            avoid_bathroom_zone = True
        elif re.search(r"(넣어\s*줘|넣어줘|허용|있어야|필요)", prompt):
            avoid_bathroom_zone = False

    exterior_door: bool | None = None
    # Exterior/entrance door intent: "현관문", "출입문", "밖으로 나갈 수 있는 문" 등
    if re.search(r"(현관\s*문|현관문|출입\s*문|출입문|외부\s*로\s*나가|밖\s*으로\s*나가|바깥\s*으로\s*나가|밖\s*으로\s*나갈\s*수\s*있는\s*문)", prompt, re.IGNORECASE):
        if re.search(r"(빼\s*줘|빼줘|제외|없애|없애\s*줘|두지\s*마|두지\s*말고|금지)", prompt):
            exterior_door = False
        else:
            exterior_door = True

    return BuildingParamsDelta(
        width_m=width,
        depth_m=depth,
        height_m=height,
        wall_thickness_m=wall_thickness,
        slab_thickness_m=slab_thickness,
        windows_per_wall=windows_per_wall,
        windows_size_preset=windows_size_preset,
        avoid_bathroom_zone=avoid_bathroom_zone,
        exterior_door=exterior_door,
    )
