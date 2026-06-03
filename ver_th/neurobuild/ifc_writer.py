from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass
from typing import Iterable, List, Tuple

from .models import LayoutPlan, Opening, Wall

IFC_GUID_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_$"
FLOOR_HEIGHT = 3.18


def ifc_guid() -> str:
    value = uuid.uuid4().int
    chars = []
    for _ in range(22):
        chars.append(IFC_GUID_CHARS[value & 0x3F])
        value >>= 6
    return "".join(chars)


def esc(value: str) -> str:
    return "'" + str(value).replace("\\", "\\\\").replace("'", "''") + "'"


@dataclass
class BoxElement:
    ifc_class: str
    name: str
    x: float
    y: float
    z: float
    length: float
    width: float
    height: float
    rotation_deg: float = 0.0
    color: Tuple[float, float, float] = (0.85, 0.85, 0.85)
    predefined_type: str | None = None


class IFCBuilder:
    def __init__(self):
        self.lines: List[str] = []
        self.next_id = 1

    def add(self, entity: str) -> str:
        ref = f"#{self.next_id}"
        self.next_id += 1
        self.lines.append(f"{ref}={entity};")
        return ref

    def point3d(self, x: float, y: float, z: float) -> str:
        return self.add(f"IFCCARTESIANPOINT(({fmt(x)},{fmt(y)},{fmt(z)}))")

    def dir3d(self, x: float, y: float, z: float) -> str:
        return self.add(f"IFCDIRECTION(({fmt(x)},{fmt(y)},{fmt(z)}))")

    def axis3d(self, x: float, y: float, z: float, rot_deg: float = 0.0) -> str:
        p = self.point3d(x, y, z)
        axis = self.dir3d(0, 0, 1)
        rad = math.radians(rot_deg)
        ref = self.dir3d(math.cos(rad), math.sin(rad), 0)
        return self.add(f"IFCAXIS2PLACEMENT3D({p},{axis},{ref})")

    def local_placement(self, parent: str | None, x: float, y: float, z: float, rot_deg: float = 0.0) -> str:
        axis = self.axis3d(x, y, z, rot_deg)
        return self.add(f"IFCLOCALPLACEMENT({parent or '$'},{axis})")

    def styled_box_representation(
        self,
        body_context: str,
        length: float,
        width: float,
        height: float,
        color: Tuple[float, float, float],
        name: str,
    ) -> str:
        profile = self.add(f"IFCRECTANGLEPROFILEDEF(.AREA.,{esc(name + ' profile')},$, {fmt(length)}, {fmt(width)})")
        zdir = self.dir3d(0, 0, 1)
        solid_pos = self.axis3d(0, 0, 0, 0)
        solid = self.add(f"IFCEXTRUDEDAREASOLID({profile},{solid_pos},{zdir},{fmt(height)})")

        colour = self.add(f"IFCCOLOURRGB({esc(name + ' colour')},{fmt(color[0])},{fmt(color[1])},{fmt(color[2])})")
        rendering = self.add(f"IFCSURFACESTYLERENDERING({colour},0.,$,$,$,$,$,$,.NOTDEFINED.)")
        surf_style = self.add(f"IFCSURFACESTYLE({esc(name + ' style')},.BOTH.,({rendering}))")
        pres = self.add(f"IFCPRESENTATIONSTYLEASSIGNMENT(({surf_style}))")
        self.add(f"IFCSTYLEDITEM({solid},({pres}),{esc(name + ' styled')})")

        shape = self.add(f"IFCSHAPEREPRESENTATION({body_context},{esc('Body')},{esc('SweptSolid')},({solid}))")
        return self.add(f"IFCPRODUCTDEFINITIONSHAPE($,$,({shape}))")


def fmt(value: float | int) -> str:
    if isinstance(value, int):
        return str(value)
    if abs(value) < 1e-9:
        value = 0.0
    return f"{float(value):.6f}".rstrip("0").rstrip(".") or "0"


def write_ifc(plan: LayoutPlan) -> str:
    b = IFCBuilder()

    origin = b.point3d(0, 0, 0)
    dir_z = b.dir3d(0, 0, 1)
    dir_x = b.dir3d(1, 0, 0)
    world_place = b.add(f"IFCAXIS2PLACEMENT3D({origin},{dir_z},{dir_x})")
    context = b.add(f"IFCGEOMETRICREPRESENTATIONCONTEXT($,{esc('Model')},3,1.E-05,{world_place},$)")
    body_context = b.add(f"IFCGEOMETRICREPRESENTATIONSUBCONTEXT({esc('Body')},{esc('Model')},*,*,*,*,{context},$,.MODEL_VIEW.,$)")

    unit_len = b.add("IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.)")
    unit_area = b.add("IFCSIUNIT(*,.AREAUNIT.,$,.SQUARE_METRE.)")
    unit_vol = b.add("IFCSIUNIT(*,.VOLUMEUNIT.,$,.CUBIC_METRE.)")
    unit_ang = b.add("IFCSIUNIT(*,.PLANEANGLEUNIT.,$,.RADIAN.)")
    units = b.add(f"IFCUNITASSIGNMENT(({unit_len},{unit_area},{unit_vol},{unit_ang}))")

    project = b.add(f"IFCPROJECT({esc(ifc_guid())},$,{esc('Neurobuild Project')},$,$,$,$,({context}),{units})")

    site_place = b.local_placement(None, 0, 0, 0, 0)
    site = b.add(f"IFCSITE({esc(ifc_guid())},$,{esc('Default Site')},$,$,{site_place},$,$,.ELEMENT.,$,$,$,$,$)")
    building_place = b.local_placement(site_place, 0, 0, 0, 0)
    building = b.add(f"IFCBUILDING({esc(ifc_guid())},$,{esc('Neurobuild AI House')},$,$,{building_place},$,$,.ELEMENT.,$,$,$)")
    storeys: dict[int, tuple[str, str]] = {}
    for floor in range(1, max(1, plan.floors) + 1):
        elevation = (floor - 1) * FLOOR_HEIGHT
        storey_place = b.local_placement(building_place, 0, 0, elevation, 0)
        storey_name = "Ground Floor" if floor == 1 else f"Floor {floor}"
        storey = b.add(f"IFCBUILDINGSTOREY({esc(ifc_guid())},$,{esc(storey_name)},$,$,{storey_place},$,$,.ELEMENT.,{fmt(elevation)})")
        storeys[floor] = (storey, storey_place)

    b.add(f"IFCRELAGGREGATES({esc(ifc_guid())},$,{esc('Project-Site')},$,{project},({site}))")
    b.add(f"IFCRELAGGREGATES({esc(ifc_guid())},$,{esc('Site-Building')},$,{site},({building}))")
    b.add(f"IFCRELAGGREGATES({esc(ifc_guid())},$,{esc('Building-Storeys')},$,{building},{tuple_refs([item[0] for item in storeys.values()])})")

    elements_by_floor: dict[int, list[str]] = {floor: [] for floor in storeys}
    slab_color = (0.36, 0.42, 0.50)
    roof_color = (0.55, 0.60, 0.68)

    def storey_place_for(floor: int) -> str:
        return storeys.get(max(1, min(max(storeys), floor)), storeys[1])[1]

    def append_element(floor: int, ref: str) -> None:
        elements_by_floor.setdefault(floor, []).append(ref)

    append_element(1, add_box(b, body_context, storey_place_for(1), BoxElement("IFCSLAB", "기초 슬래브", plan.width / 2, plan.depth / 2, -0.20, plan.width + 0.4, plan.depth + 0.4, 0.22, 0, slab_color, "BASESLAB")))
    for floor in storeys:
        append_element(floor, add_box(b, body_context, storey_place_for(floor), BoxElement("IFCSLAB", f"{floor}층 바닥 슬래브", plan.width / 2, plan.depth / 2, 0.0, plan.width, plan.depth, 0.16, 0, slab_color, "FLOOR")))
    top_floor = max(storeys)
    append_element(top_floor, add_box(b, body_context, storey_place_for(top_floor), BoxElement("IFCSLAB", "평지붕 매스", plan.width / 2, plan.depth / 2, 2.95, plan.width + 0.35, plan.depth + 0.35, 0.14, 0, roof_color, "ROOF")))

    for room in plan.rooms:
        color = room_color(room.kind)
        append_element(room.floor, add_box(b, body_context, storey_place_for(room.floor), BoxElement("IFCSPACE", room.name, room.x + room.width / 2, room.y + room.depth / 2, 0.03, room.width, room.depth, 0.04, 0, color, None)))

    for wall in plan.walls:
        floor_openings = [opening for opening in plan.openings if opening.floor == wall.floor]
        for box in wall_to_boxes(wall, floor_openings):
            append_element(wall.floor, add_box(b, body_context, storey_place_for(wall.floor), box))

    for opening in plan.openings:
        kind = "IFCDOOR" if opening.kind == "door" else "IFCWINDOW"
        color = (0.68, 0.38, 0.13) if opening.kind == "door" else (0.25, 0.78, 0.95)
        thickness = 0.10 if opening.kind == "window" else 0.08
        length = max(0.08, opening.width)
        if abs(opening.rotation_deg) % 180 == 90:
            box_len, box_wid = thickness, length
        else:
            box_len, box_wid = length, thickness
        append_element(
            opening.floor,
            add_box(
                b,
                body_context,
                storey_place_for(opening.floor),
                BoxElement(kind, opening.name, opening.x, opening.y, opening.sill_height, box_len, box_wid, opening.height, opening.rotation_deg, color, None),
            ),
        )

    for room in plan.rooms:
        if room.kind == "living":
            append_element(room.floor, add_box(b, body_context, storey_place_for(room.floor), BoxElement("IFCFURNISHINGELEMENT", f"{room.name} 소파", room.x + room.width * 0.45, room.y + room.depth * 0.62, 0.20, min(3.2, room.width * 0.55), 0.80, 0.42, 0, (0.42, 0.28, 0.80))))
            append_element(room.floor, add_box(b, body_context, storey_place_for(room.floor), BoxElement("IFCFURNISHINGELEMENT", f"{room.name} 테이블", room.x + room.width * 0.55, room.y + room.depth * 0.38, 0.38, 1.8, 0.95, 0.12, 0, (0.65, 0.38, 0.12))))
        if room.kind == "bedroom":
            append_element(room.floor, add_box(b, body_context, storey_place_for(room.floor), BoxElement("IFCFURNISHINGELEMENT", f"{room.name} 침대", room.x + room.width * 0.38, room.y + room.depth * 0.55, 0.25, 1.25, 1.95, 0.32, 0, (0.78, 0.82, 0.90))))
            append_element(room.floor, add_box(b, body_context, storey_place_for(room.floor), BoxElement("IFCFURNISHINGELEMENT", f"{room.name} 책상", room.x + room.width * 0.78, room.y + room.depth * 0.25, 0.42, 0.9, 0.48, 0.10, 0, (0.50, 0.31, 0.14))))

    for floor, elements in elements_by_floor.items():
        if elements:
            storey = storeys[floor][0]
            b.add(f"IFCRELCONTAINEDINSPATIALSTRUCTURE({esc(ifc_guid())},$,{esc(f'{floor}F containment')},$,{tuple_refs(elements)},{storey})")

    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
    header = f"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView_V2.0]'),'2;1');
FILE_NAME('Neurobuild.ifc','{timestamp}',('Neurobuild AI'),('Neurobuild'),'Neurobuild Real v2','Neurobuild IFC Writer','');
FILE_SCHEMA(('IFC4'));
ENDSEC;
DATA;
"""
    footer = "ENDSEC;\nEND-ISO-10303-21;\n"
    return header + "\n".join(b.lines) + "\n" + footer


def add_box(b: IFCBuilder, body_context: str, parent_placement: str, box: BoxElement) -> str:
    placement = b.local_placement(parent_placement, box.x, box.y, box.z, box.rotation_deg)
    rep = b.styled_box_representation(body_context, box.length, box.width, box.height, box.color, box.name)
    tag = esc(box.name.replace(" ", "_"))
    guid = esc(ifc_guid())
    name = esc(box.name)

    if box.ifc_class == "IFCSLAB":
        predefined = f".{box.predefined_type or 'FLOOR'}."
        return b.add(f"IFCSLAB({guid},$,{name},$,$,{placement},{rep},{tag},{predefined})")
    if box.ifc_class == "IFCWALL":
        return b.add(f"IFCWALL({guid},$,{name},$,$,{placement},{rep},{tag},.NOTDEFINED.)")
    if box.ifc_class == "IFCDOOR":
        return b.add(f"IFCDOOR({guid},$,{name},$,$,{placement},{rep},{tag},{fmt(box.height)},{fmt(max(box.length, box.width))},.DOOR.,.SINGLE_SWING_LEFT.,$)")
    if box.ifc_class == "IFCWINDOW":
        return b.add(f"IFCWINDOW({guid},$,{name},$,$,{placement},{rep},{tag},{fmt(box.height)},{fmt(max(box.length, box.width))},.WINDOW.,.SINGLE_PANEL.,$)")
    if box.ifc_class == "IFCSPACE":
        return b.add(f"IFCSPACE({guid},$,{name},$,$,{placement},{rep},$,.ELEMENT.,.INTERNAL.,$)")
    if box.ifc_class == "IFCFURNISHINGELEMENT":
        return b.add(f"IFCFURNISHINGELEMENT({guid},$,{name},$,$,{placement},{rep},{tag},.USERDEFINED.)")
    return b.add(f"IFCBUILDINGELEMENTPROXY({guid},$,{name},$,$,{placement},{rep},{tag},.USERDEFINED.)")


def room_color(kind: str) -> tuple[float, float, float]:
    if kind == "living":
        return (0.28, 0.78, 0.49)
    if kind == "bedroom":
        return (0.28, 0.55, 0.96)
    if kind == "bath":
        return (0.64, 0.48, 0.94)
    if kind == "kitchen":
        return (0.95, 0.66, 0.22)
    return (0.70, 0.75, 0.82)


def wall_to_boxes(wall: Wall, openings: Iterable[Opening]) -> list[BoxElement]:
    dx = wall.x2 - wall.x1
    dy = wall.y2 - wall.y1
    length = math.hypot(dx, dy)
    if length <= 0.01:
        return []
    angle = math.degrees(math.atan2(dy, dx))
    ux, uy = dx / length, dy / length
    wall_openings = []
    for op in openings:
        vx, vy = op.x - wall.x1, op.y - wall.y1
        s = vx * ux + vy * uy
        perp = abs(vx * (-uy) + vy * ux)
        if -0.3 <= s <= length + 0.3 and perp <= max(0.35, wall.thickness * 2.2):
            wall_openings.append((s, op))
    wall_openings.sort(key=lambda item: item[0])

    segments: list[BoxElement] = []
    cursor = 0.0
    for s, op in wall_openings:
        start = max(0.0, s - op.width / 2)
        end = min(length, s + op.width / 2)
        if start - cursor > 0.08:
            segments.append(_wall_segment_box(wall, cursor, start, angle, ux, uy, wall.height, 0, f"{wall.name} segment"))
        gap_len = end - start
        if gap_len > 0.08:
            if op.kind == "window" and op.sill_height > 0.05:
                segments.append(_wall_segment_box(wall, start, end, angle, ux, uy, op.sill_height, 0, f"{wall.name} window sill"))
                top_h = max(0.05, wall.height - op.sill_height - op.height)
                if top_h > 0.08:
                    segments.append(_wall_segment_box(wall, start, end, angle, ux, uy, top_h, op.sill_height + op.height, f"{wall.name} window header"))
            else:
                top_h = max(0.05, wall.height - op.height)
                if top_h > 0.08:
                    segments.append(_wall_segment_box(wall, start, end, angle, ux, uy, top_h, op.height, f"{wall.name} door header"))
        cursor = max(cursor, end)
    if length - cursor > 0.08:
        segments.append(_wall_segment_box(wall, cursor, length, angle, ux, uy, wall.height, 0, f"{wall.name} segment"))
    if not segments:
        segments.append(_wall_segment_box(wall, 0, length, angle, ux, uy, wall.height, 0, wall.name))
    return segments


def _wall_segment_box(wall: Wall, s0: float, s1: float, angle: float, ux: float, uy: float, height: float, zbase: float, name: str) -> BoxElement:
    center_s = (s0 + s1) / 2
    x = wall.x1 + ux * center_s
    y = wall.y1 + uy * center_s
    length = max(0.05, s1 - s0)
    color = (0.88, 0.90, 0.93) if wall.wall_type == "external" else (0.92, 0.89, 0.81)
    return BoxElement("IFCWALL", name, x, y, zbase, length, wall.thickness, height, angle, color, None)


def tuple_refs(refs: Iterable[str]) -> str:
    refs = list(refs)
    if len(refs) == 1:
        return f"({refs[0]})"
    return "(" + ",".join(refs) + ")"
