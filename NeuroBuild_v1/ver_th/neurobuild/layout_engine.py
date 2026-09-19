from __future__ import annotations

import math

from .models import LayoutPlan, Opening, Room, UserBrief, Wall


def create_layout(brief: UserBrief) -> LayoutPlan:
    """Deterministic conceptual layout engine.

    The LLM interprets requirements, while this engine keeps geometry stable and
    reproducible for IFC export.
    """
    rooms_requested = max(1, brief.room_count)
    occupants = max(1, brief.occupants)
    budget = max(50_000_000, brief.budget_krw)
    floors = max(1, min(10, brief.floors))

    base_cost_per_sqm = 2_450_000
    if "프리미엄" in brief.style_keywords:
        base_cost_per_sqm += 350_000
    if "친환경" in brief.style_keywords or "태양광" in brief.special_requirements:
        base_cost_per_sqm += 180_000

    max_buildable_by_budget = budget / base_cost_per_sqm * 0.94
    min_area = 54 + rooms_requested * 9.5 + max(0, occupants - 2) * 3
    desired_area = 88 + rooms_requested * 8.5
    if brief.living_room_preference == "large":
        desired_area += 12
    target_gross_area = max(min_area, min(desired_area, max_buildable_by_budget))
    floorplate_area = max(48.0, target_gross_area / floors)

    if floors > 1:
        depth = 7.0 if floorplate_area >= 70 else 6.6
        min_width = 8.8
    else:
        depth = 8.4 if floorplate_area >= 100 else 7.8
        min_width = 10.8
    width = round(max(min_width, floorplate_area / depth), 2)
    if floors == 1 and width < 12.6 and rooms_requested >= 4:
        width = 13.8
        depth = round(max(7.8, floorplate_area / width), 2)
    gross_area = round(width * depth * floors, 2)

    if rooms_requested == 4 and floors == 1:
        rooms = _four_bed_co_living(width, depth)
        walls = _four_bed_walls(width, depth)
        openings = _four_bed_openings(width, depth)
    elif floors > 1:
        rooms, walls, openings = _multi_floor_layout(width, depth, rooms_requested, floors)
    else:
        rooms = _generic_rooms(width, depth, rooms_requested)
        walls = _generic_walls(width, depth, rooms, floor=1)
        openings = _generic_openings(width, depth, rooms, floor=1)

    net_room_area = round(sum(r.area for r in rooms), 2)
    estimated_cost = int(round(gross_area * base_cost_per_sqm))
    budget_status = "예산 이내" if estimated_cost <= budget else "예산 초과 위험"

    notes = [
        "개념설계 자동 생성안입니다. 실시설계, 구조, 설비, 인허가 검토 전에는 시공 도면으로 사용할 수 없습니다.",
        "대지 주소, 용도지역, 도로 접도 조건을 입력하면 법무팀 RAG 검토 정확도가 올라갑니다.",
    ]
    if brief.living_room_preference == "large":
        notes.append("공용 생활을 위해 거실, 다이닝, 키친을 하나의 공유 라운지로 계획했습니다.")
    if floors > 1:
        notes.append(f"{floors}층 주택 요청을 반영해 1층 공용부와 상층 침실/라운지를 층별 평면으로 분리했습니다.")
    if estimated_cost > budget:
        notes.append("예산 초과 위험이 있어 면적 축소, 마감 조정, 습식공간 단순화가 필요합니다.")

    metrics = {
        "occupants": brief.occupants,
        "bedrooms": brief.room_count,
        "area_per_person_sqm": round(gross_area / max(1, occupants), 1),
        "budget_krw": brief.budget_krw,
        "estimated_cost_krw": estimated_cost,
        "budget_delta_krw": brief.budget_krw - estimated_cost,
        "floors": floors,
    }

    return LayoutPlan(
        title=f"Neurobuild Co-living {floors}-story Concept",
        width=width,
        depth=depth,
        floors=floors,
        rooms=rooms,
        walls=walls,
        openings=openings,
        gross_area=gross_area,
        net_room_area=net_room_area,
        estimated_cost_krw=estimated_cost,
        cost_per_sqm_krw=base_cost_per_sqm,
        budget_status=budget_status,
        notes=notes,
        metrics=metrics,
    )


def _four_bed_co_living(width: float, depth: float) -> list[Room]:
    margin = 0.24
    left_w = round(max(5.6, width * 0.47), 2)
    right_x = round(left_w + 0.18, 2)
    right_w = round(width - right_x - margin, 2)
    bed_col_gap = 0.18
    bed_w = round((right_w - bed_col_gap) / 2, 2)
    row_gap = 0.18
    service_d = round(max(1.55, depth * 0.21), 2)
    bed_d = round((depth - margin * 2 - service_d - row_gap * 2) / 2, 2)
    living_d = round(depth * 0.66, 2)

    return [
        Room("living", "공유 라운지 / 거실", "living", margin, margin, left_w - margin, living_d - margin),
        Room("kitchen", "다이닝 키친", "kitchen", margin, living_d + 0.12, left_w - margin, depth - living_d - margin - 0.12),
        Room("bed1", "개인 침실 1", "bedroom", right_x, margin, bed_w, bed_d),
        Room("bed2", "개인 침실 2", "bedroom", right_x + bed_w + bed_col_gap, margin, bed_w, bed_d),
        Room("bed3", "개인 침실 3", "bedroom", right_x, margin + bed_d + row_gap, bed_w, bed_d),
        Room("bed4", "개인 침실 4", "bedroom", right_x + bed_w + bed_col_gap, margin + bed_d + row_gap, bed_w, bed_d),
        Room("entry", "현관 / 수납", "service", right_x, depth - service_d - margin, round(bed_w * 0.65, 2), service_d),
        Room("bath1", "공용 화장실", "bath", right_x + round(bed_w * 0.65, 2) + 0.12, depth - service_d - margin, round(bed_w * 0.75, 2), service_d),
        Room("bath2", "샤워 / 세탁", "bath", right_x + bed_w + bed_col_gap, depth - service_d - margin, right_w - bed_w - bed_col_gap, service_d),
    ]


def _four_bed_walls(width: float, depth: float) -> list[Wall]:
    t_ext = 0.24
    t_int = 0.16
    left_w = round(max(5.6, width * 0.47), 2)
    x_main = round(left_w + 0.09, 2)
    right_x = round(left_w + 0.18, 2)
    right_w = round(width - right_x - 0.24, 2)
    bed_col_gap = 0.18
    bed_w = round((right_w - bed_col_gap) / 2, 2)
    service_d = round(max(1.55, depth * 0.21), 2)
    bed_d = round((depth - 0.24 * 2 - service_d - 0.18 * 2) / 2, 2)
    y_row = round(0.24 + bed_d + 0.09, 2)
    y_service = round(depth - service_d - 0.24 - 0.09, 2)
    y_living_split = round(depth * 0.66 + 0.06, 2)
    x_bed_split = round(right_x + bed_w + 0.09, 2)
    x_service_1 = round(right_x + bed_w * 0.65 + 0.06, 2)
    x_service_2 = round(right_x + bed_w + bed_col_gap / 2, 2)

    return [
        Wall("외벽 남측", 0, 0, width, 0, t_ext, 2.8, "external"),
        Wall("외벽 동측", width, 0, width, depth, t_ext, 2.8, "external"),
        Wall("외벽 북측", width, depth, 0, depth, t_ext, 2.8, "external"),
        Wall("외벽 서측", 0, depth, 0, 0, t_ext, 2.8, "external"),
        Wall("공용부-개인실 분리벽", x_main, 0, x_main, depth, t_int, 2.7, "internal"),
        Wall("거실-키친 가변벽", 0, y_living_split, x_main, y_living_split, t_int, 2.7, "internal"),
        Wall("침실 세로 분리벽", x_bed_split, 0, x_bed_split, y_service, t_int, 2.7, "internal"),
        Wall("침실 가로 분리벽", x_main, y_row, width, y_row, t_int, 2.7, "internal"),
        Wall("침실-서비스 분리벽", x_main, y_service, width, y_service, t_int, 2.7, "internal"),
        Wall("현관-화장실 분리벽", x_service_1, y_service, x_service_1, depth, t_int, 2.7, "internal"),
        Wall("화장실-세탁실 분리벽", x_service_2, y_service, x_service_2, depth, t_int, 2.7, "internal"),
    ]


def _four_bed_openings(width: float, depth: float) -> list[Opening]:
    left_w = round(max(5.6, width * 0.47), 2)
    x_main = round(left_w + 0.09, 2)
    right_x = round(left_w + 0.18, 2)
    right_w = round(width - right_x - 0.24, 2)
    bed_col_gap = 0.18
    bed_w = round((right_w - bed_col_gap) / 2, 2)
    service_d = round(max(1.55, depth * 0.21), 2)
    bed_d = round((depth - 0.24 * 2 - service_d - 0.18 * 2) / 2, 2)
    y_row = round(0.24 + bed_d + 0.09, 2)
    y_service = round(depth - service_d - 0.24 - 0.09, 2)
    y_living_split = round(depth * 0.66 + 0.06, 2)
    x_bed_split = round(right_x + bed_w + 0.09, 2)
    return [
        Opening("메인 현관문", "door", 1.2, 0.0, 1.05, 2.15, 0.0, 0),
        Opening("라운지 파노라마 창", "window", left_w * 0.48, 0.0, 3.8, 1.35, 0.75, 0),
        Opening("키친 북측 창", "window", left_w * 0.50, depth, 2.4, 1.1, 0.9, 0),
        Opening("침실1 창", "window", right_x + bed_w * 0.5, 0.0, 1.25, 1.05, 0.9, 0),
        Opening("침실2 창", "window", right_x + bed_w + bed_col_gap + bed_w * 0.5, 0.0, 1.25, 1.05, 0.9, 0),
        Opening("침실3 고측 창", "window", right_x + bed_w * 0.5, depth, 1.15, 0.9, 1.05, 0),
        Opening("침실4 동측 창", "window", width, 0.24 + bed_d + 0.18 + bed_d * 0.5, 1.25, 1.05, 0.9, 90),
        Opening("거실-키친 포켓도어", "door", left_w * 0.52, y_living_split, 1.35, 2.15, 0.0, 0),
        Opening("침실1 문", "door", x_main, 1.55, 0.86, 2.1, 0.0, 90),
        Opening("침실3 문", "door", x_main, y_row + 1.25, 0.86, 2.1, 0.0, 90),
        Opening("침실2 문", "door", x_bed_split, 1.55, 0.86, 2.1, 0.0, 90),
        Opening("침실4 문", "door", x_bed_split, y_row + 1.25, 0.86, 2.1, 0.0, 90),
        Opening("서비스 문", "door", x_main + 1.0, y_service, 0.9, 2.1, 0.0, 0),
    ]


def _multi_floor_layout(width: float, depth: float, room_count: int, floors: int) -> tuple[list[Room], list[Wall], list[Opening]]:
    bedrooms_by_floor = _split_bedrooms(room_count, floors)
    rooms: list[Room] = []
    walls: list[Wall] = []
    openings: list[Opening] = []
    bedroom_start = 1

    for floor, bedroom_count in enumerate(bedrooms_by_floor, 1):
        floor_rooms = _generic_rooms(
            width,
            depth,
            bedroom_count,
            floor=floor,
            bedroom_start=bedroom_start,
            upper=floor > 1,
        )
        bedroom_start += bedroom_count
        rooms.extend(floor_rooms)
        walls.extend(_generic_walls(width, depth, floor_rooms, floor=floor))
        openings.extend(_generic_openings(width, depth, floor_rooms, floor=floor))

    return rooms, walls, openings


def _split_bedrooms(room_count: int, floors: int) -> list[int]:
    base = room_count // floors
    remainder = room_count % floors
    return [base + (1 if idx < remainder else 0) for idx in range(floors)]


def _generic_rooms(
    width: float,
    depth: float,
    room_count: int,
    floor: int = 1,
    bedroom_start: int = 1,
    upper: bool = False,
) -> list[Room]:
    margin = 0.24
    left_w = width * 0.52
    prefix = "" if floor == 1 else f"{floor}층 "
    if upper:
        rooms = [
            Room(f"lounge_f{floor}", f"{prefix}가족 라운지", "living", margin, margin, left_w - margin, depth * 0.56 - margin, floor),
            Room(f"stair_f{floor}", f"{prefix}계단 홀", "service", margin, depth * 0.59, left_w * 0.48, depth * 0.35, floor),
            Room(f"bath_f{floor}", f"{prefix}욕실", "bath", margin + left_w * 0.52, depth * 0.59, left_w * 0.43, depth * 0.35, floor),
        ]
    else:
        rooms = [
            Room("living", "공유 라운지 / 거실", "living", margin, margin, left_w - margin, depth * 0.62 - margin, floor),
            Room("kitchen", "다이닝 키친", "kitchen", margin, depth * 0.64, left_w - margin, depth * 0.34 - margin, floor),
        ]
    right_x = left_w + 0.18
    right_w = width - right_x - margin
    rows = max(1, math.ceil(room_count / 2))
    bed_d = (depth * 0.72 - margin) / rows
    bed_w = (right_w - 0.18) / 2
    for i in range(room_count):
        col = i % 2
        row = i // 2
        bedroom_number = bedroom_start + i
        rooms.append(
            Room(
                f"bed{bedroom_number}",
                f"{prefix}개인 침실 {bedroom_number}",
                "bedroom",
                right_x + col * (bed_w + 0.18),
                margin + row * bed_d,
                bed_w,
                bed_d - 0.12,
                floor,
            )
        )
    if not upper:
        rooms.extend(
            [
                Room("bath1", "공용 화장실", "bath", right_x, depth * 0.74, right_w * 0.48, depth * 0.22, floor),
                Room("entry", "현관 / 수납", "service", right_x + right_w * 0.52, depth * 0.74, right_w * 0.45, depth * 0.22, floor),
            ]
        )
    return rooms


def _generic_walls(width: float, depth: float, rooms: list[Room], floor: int = 1) -> list[Wall]:
    walls = [
        Wall(f"{floor}층 외벽 남측", 0, 0, width, 0, 0.24, 2.8, "external", floor),
        Wall(f"{floor}층 외벽 동측", width, 0, width, depth, 0.24, 2.8, "external", floor),
        Wall(f"{floor}층 외벽 북측", width, depth, 0, depth, 0.24, 2.8, "external", floor),
        Wall(f"{floor}층 외벽 서측", 0, depth, 0, 0, 0.24, 2.8, "external", floor),
    ]
    seen = set()
    for room in rooms:
        edges = [
            (room.x, room.y, room.x + room.width, room.y),
            (room.x + room.width, room.y, room.x + room.width, room.y + room.depth),
            (room.x + room.width, room.y + room.depth, room.x, room.y + room.depth),
            (room.x, room.y + room.depth, room.x, room.y),
        ]
        for x1, y1, x2, y2 in edges:
            if min(x1, x2) < 0.35 or min(y1, y2) < 0.35 or max(x1, x2) > width - 0.35 or max(y1, y2) > depth - 0.35:
                continue
            key = tuple(round(v, 1) for v in (x1, y1, x2, y2))
            rkey = tuple(round(v, 1) for v in (x2, y2, x1, y1))
            if key in seen or rkey in seen:
                continue
            seen.add(key)
            walls.append(Wall(f"{floor}층 실내벽 {len(walls)}", x1, y1, x2, y2, 0.16, 2.7, "internal", floor))
    return walls


def _generic_openings(width: float, depth: float, rooms: list[Room], floor: int = 1) -> list[Opening]:
    openings = [
        Opening("메인 현관문" if floor == 1 else f"{floor}층 계단실 창", "door" if floor == 1 else "window", 1.15, 0, 1.0, 2.1 if floor == 1 else 1.0, 0 if floor == 1 else 0.9, 0, floor),
        Opening(f"{floor}층 라운지 남측 창", "window", width * 0.25, 0, 2.8, 1.3, 0.75, 0, floor),
        Opening(f"{floor}층 북측 창", "window", width * 0.30, depth, 2.0, 1.1, 0.9, 0, floor),
    ]
    for idx, room in enumerate([r for r in rooms if r.kind == "bedroom"][:6], 1):
        openings.append(Opening(f"{room.name} 창", "window", min(width, room.x + room.width / 2), 0, 1.2, 1.0, 0.9, 0, floor))
    return openings
