from __future__ import annotations

from dataclasses import dataclass

import numpy as np

import ifcopenshell
import ifcopenshell.api.aggregate
import ifcopenshell.api.context
import ifcopenshell.api.feature
import ifcopenshell.api.geometry
import ifcopenshell.api.project
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.unit


@dataclass(frozen=True)
class IfcResult:
    file: ifcopenshell.file
    project: ifcopenshell.entity_instance
    body_context: ifcopenshell.entity_instance
    storey: ifcopenshell.entity_instance


def _setup_project(name: str = "MVP Project") -> IfcResult:
    model = ifcopenshell.api.project.create_file("IFC4")

    project = ifcopenshell.api.root.create_entity(model, ifc_class="IfcProject", name=name)
    ifcopenshell.api.unit.assign_unit(model)

    model3d = ifcopenshell.api.context.add_context(model, context_type="Model")
    body = ifcopenshell.api.context.add_context(
        model,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=model3d,
    )

    site = ifcopenshell.api.root.create_entity(model, ifc_class="IfcSite", name="Site")
    building = ifcopenshell.api.root.create_entity(model, ifc_class="IfcBuilding", name="Building")
    storey = ifcopenshell.api.root.create_entity(model, ifc_class="IfcBuildingStorey", name="Storey 0")

    ifcopenshell.api.aggregate.assign_object(model, products=[site], relating_object=project)
    ifcopenshell.api.aggregate.assign_object(model, products=[building], relating_object=site)
    ifcopenshell.api.aggregate.assign_object(model, products=[storey], relating_object=building)

    # Place spatial structure at origin
    ifcopenshell.api.geometry.edit_object_placement(model, product=site)
    ifcopenshell.api.geometry.edit_object_placement(model, product=building)
    ifcopenshell.api.geometry.edit_object_placement(model, product=storey)

    return IfcResult(file=model, project=project, body_context=body, storey=storey)


def generate_simple_box_building(
    *,
    width_m: float,
    depth_m: float,
    height_m: float,
    wall_thickness_m: float,
    slab_thickness_m: float,
    windows_per_wall: int = 0,
    windows_size_preset: str = "medium",
    avoid_bathroom_zone: bool = False,
    exterior_door: bool = False,
    layout_spec: dict | None = None,
    name: str = "Generated Building",
) -> ifcopenshell.file:
    """Create a minimal but viewable IFC: 1 slab + 4 walls (rectangle)."""

    ctx = _setup_project(name)
    model = ctx.file
    body = ctx.body_context

    # Slab
    slab = ifcopenshell.api.root.create_entity(model, ifc_class="IfcSlab", name="Slab")
    slab_poly = [
        (0.0, 0.0),
        (width_m, 0.0),
        (width_m, depth_m),
        (0.0, depth_m),
        (0.0, 0.0),
    ]
    slab_rep = ifcopenshell.api.geometry.add_slab_representation(
        model,
        context=body,
        depth=slab_thickness_m,
        polyline=slab_poly,
    )
    ifcopenshell.api.geometry.assign_representation(model, product=slab, representation=slab_rep)
    ifcopenshell.api.geometry.edit_object_placement(model, product=slab)

    # Walls
    walls: list[ifcopenshell.entity_instance] = []
    wall_segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
    wall_points = [
        ((0.0, 0.0), (width_m, 0.0)),
        ((width_m, 0.0), (width_m, depth_m)),
        ((width_m, depth_m), (0.0, depth_m)),
        ((0.0, depth_m), (0.0, 0.0)),
    ]
    for idx, (p1, p2) in enumerate(wall_points, start=1):
        wall = ifcopenshell.api.root.create_entity(model, ifc_class="IfcWallStandardCase", name=f"Wall {idx}")
        rep = ifcopenshell.api.geometry.create_2pt_wall(
            model,
            element=wall,
            context=body,
            p1=p1,
            p2=p2,
            elevation=0.0,
            height=height_m,
            thickness=wall_thickness_m,
            is_si=True,
        )
        ifcopenshell.api.geometry.assign_representation(model, product=wall, representation=rep)
        walls.append(wall)
        wall_segments.append((p1, p2))

    products: list[ifcopenshell.entity_instance] = [slab, *walls]

    skip_window_walls: set[int] = set()
    if exterior_door:
        # MVP: place one exterior door on the south wall (Wall 1).
        # To avoid overlap, skip perimeter windows on that wall.
        widx = 1
        if 1 <= widx <= len(walls):
            p1, p2 = wall_points[widx - 1]
            door_products = _add_door_in_wall(
                model=model,
                context=body,
                wall=walls[widx - 1],
                p1=p1,
                p2=p2,
                wall_thickness_m=wall_thickness_m,
                door_width_m=1.0,
                door_height_m=min(2.1, max(2.0, height_m - 0.6)),
                along_m=float(width_m) / 2.0,
                name="Exterior Door",
            )
            products.extend(door_products)
            skip_window_walls.add(widx)

    if windows_per_wall and windows_per_wall > 0:
        bathroom_zone = None
        if avoid_bathroom_zone:
            bathroom_zone = _infer_bathroom_zone_bounds_m(spec=layout_spec, width_m=width_m, depth_m=depth_m)
        new_products = _add_perimeter_windows(
            model=model,
            context=body,
            walls=walls,
            wall_segments=wall_segments,
            wall_thickness_m=wall_thickness_m,
            storey_height_m=height_m,
            windows_per_wall=int(windows_per_wall),
            size_preset=windows_size_preset,
            avoid_zone_bounds_xy=bathroom_zone,
            skip_wall_indices=skip_window_walls,
        )
        products.extend(new_products)

    if layout_spec:
        products.extend(
            _add_layout_from_spec(
                model=model,
                context=body,
                width_m=width_m,
                depth_m=depth_m,
                height_m=height_m,
                wall_thickness_m=wall_thickness_m,
                slab_thickness_m=slab_thickness_m,
                spec=layout_spec,
            )
        )

    # Containment (storey)
    ifcopenshell.api.spatial.assign_container(model, products=products, relating_structure=ctx.storey)

    return model


def _infer_bathroom_zone_bounds_m(*, spec: dict | None, width_m: float, depth_m: float) -> tuple[float, float, float, float] | None:
    """Infer a rough bathroom zone rectangle (xmin, xmax, ymin, ymax) in plan.

    This mirrors the deterministic layout heuristic: bathrooms cluster at south-west.
    If we cannot infer bathrooms from the spec, return None.
    """

    if not spec:
        return None

    constraints = (spec or {}).get("constraints") or {}
    spaces = (spec or {}).get("spaces") or []

    def _space_count(space_type: str) -> int:
        total = 0
        for s in spaces:
            if (s or {}).get("type") == space_type:
                try:
                    total += int((s or {}).get("count") or 0)
                except Exception:
                    total += 0
        return total

    bathroom_count = constraints.get("bathroom_count")
    if bathroom_count is None:
        bathroom_count = _space_count("bathroom")
    try:
        bathroom_count = int(bathroom_count or 0)
    except Exception:
        bathroom_count = 0

    if bathroom_count <= 0:
        return None

    private_w = max(2.8, min(width_m * 0.4, width_m - 3.0))
    bath_depth = min(2.4, max(2.0, depth_m * 0.28))
    bath_depth = min(bath_depth, max(0.0, depth_m - 2.0))

    if bath_depth <= 0.0 or private_w <= 0.0:
        return None

    return (0.0, float(private_w), 0.0, float(bath_depth))


def _add_layout_from_spec(
    *,
    model: ifcopenshell.file,
    context: ifcopenshell.entity_instance,
    width_m: float,
    depth_m: float,
    height_m: float,
    wall_thickness_m: float,
    slab_thickness_m: float,
    spec: dict,
) -> list[ifcopenshell.entity_instance]:
    """Very small deterministic layout MVP.

    Supports prompts like:
    - 침실 1
    - 화장실 2
    - 거실+주방 오픈
    - 긴 발코니(거실/침실 연결)

    Output: internal partition walls, basic doors, and (optional) balcony slab.
    """

    constraints = (spec or {}).get("constraints") or {}
    spaces = (spec or {}).get("spaces") or []

    def _space_count(space_type: str) -> int:
        total = 0
        for s in spaces:
            if (s or {}).get("type") == space_type:
                try:
                    total += int((s or {}).get("count") or 0)
                except Exception:
                    total += 0
        return total

    bedroom_count = max(0, _space_count("bedroom"))
    bathroom_count = constraints.get("bathroom_count")
    if bathroom_count is None:
        bathroom_count = _space_count("bathroom")
    try:
        bathroom_count = int(bathroom_count or 0)
    except Exception:
        bathroom_count = 0

    open_plan = constraints.get("open_plan") or []
    has_open_living_kitchen = any(str(x).replace(" ", "").lower() in ("living+kitchen", "kitchen+living") for x in open_plan)

    products: list[ifcopenshell.entity_instance] = []

    # Balcony (long): add an external slab strip along the "north" edge.
    balcony = constraints.get("balcony") or {}
    if isinstance(balcony, dict) and str(balcony.get("style") or "").lower() == "long":
        bal_depth = min(2.0, max(1.2, depth_m * 0.2))
        balcony_slab = ifcopenshell.api.root.create_entity(model, ifc_class="IfcSlab", name="Balcony")
        poly = [
            (0.0, depth_m),
            (width_m, depth_m),
            (width_m, depth_m + bal_depth),
            (0.0, depth_m + bal_depth),
            (0.0, depth_m),
        ]
        rep = ifcopenshell.api.geometry.add_slab_representation(
            model,
            context=context,
            depth=slab_thickness_m,
            polyline=poly,
        )
        ifcopenshell.api.geometry.assign_representation(model, product=balcony_slab, representation=rep)
        ifcopenshell.api.geometry.edit_object_placement(model, product=balcony_slab)
        products.append(balcony_slab)

    # Internal layout: only if we have at least 1 bedroom or 2 bathrooms.
    if bedroom_count <= 0 and bathroom_count <= 0:
        return products

    # Heuristic: left strip is "private" (bedrooms/bathrooms), right is "public" (living+kitchen open).
    private_w = max(2.8, min(width_m * 0.4, width_m - 3.0))
    bath_depth = min(2.4, max(2.0, depth_m * 0.28))
    bath_depth = min(bath_depth, max(0.0, depth_m - 2.0))

    internal_walls: list[tuple[ifcopenshell.entity_instance, tuple[float, float], tuple[float, float]]] = []

    def _create_internal_wall(name: str, p1: tuple[float, float], p2: tuple[float, float]):
        wall = ifcopenshell.api.root.create_entity(model, ifc_class="IfcWallStandardCase", name=name)
        rep = ifcopenshell.api.geometry.create_2pt_wall(
            model,
            element=wall,
            context=context,
            p1=p1,
            p2=p2,
            elevation=0.0,
            height=height_m,
            thickness=wall_thickness_m,
            is_si=True,
        )
        ifcopenshell.api.geometry.assign_representation(model, product=wall, representation=rep)
        internal_walls.append((wall, p1, p2))
        products.append(wall)
        return wall

    # Main partition between private/public
    main_split = _create_internal_wall("Partition Main", (private_w, 0.0), (private_w, depth_m))

    # Bathrooms cluster at the south-west corner if we need >=1
    bath_wall = None
    bath_cell_count = 0
    if bathroom_count >= 1 and bath_depth > 0.0:
        # Clamp to something that can fit visually.
        # If we make cells too thin, doors/partitions overlap and become confusing.
        min_cell_w = 1.1
        max_cells_fit = max(1, int(private_w / min_cell_w))
        bath_cell_count = max(1, min(int(bathroom_count), max_cells_fit))

        bath_wall = _create_internal_wall("Partition Bath", (0.0, bath_depth), (private_w, bath_depth))

        # Split the bathroom strip into N cells with vertical partitions.
        # x = private_w * i/N for i=1..N-1
        if bath_cell_count >= 2:
            for i in range(1, bath_cell_count):
                x = private_w * (i / bath_cell_count)
                _create_internal_wall(f"Partition Bath {i+1}", (x, 0.0), (x, bath_depth))

    # Doors
    # 1) Door between public and private (living-bedroom connection)
    _add_door_in_wall(
        model=model,
        context=context,
        wall=main_split,
        p1=(private_w, 0.0),
        p2=(private_w, depth_m),
        wall_thickness_m=wall_thickness_m,
        door_width_m=0.9,
        door_height_m=min(2.1, max(2.0, height_m - 0.6)),
        along_m=min(depth_m - 1.2, max(1.2, bath_depth + 1.0)),
        name="Door Public-Private",
    )

    # 2) Bathroom doors on the bath wall, if present
    if bath_wall is not None and bath_cell_count >= 1:
        # One door per bathroom cell, centered in each cell.
        for i in range(1, bath_cell_count + 1):
            x_center = private_w * ((i - 0.5) / bath_cell_count)
            along = max(0.6, min(private_w - 0.6, x_center))
            _add_door_in_wall(
                model=model,
                context=context,
                wall=bath_wall,
                p1=(0.0, bath_depth),
                p2=(private_w, bath_depth),
                wall_thickness_m=wall_thickness_m,
                door_width_m=0.75,
                door_height_m=min(2.05, max(2.0, height_m - 0.6)),
                along_m=along,
                name=f"Door Bath {i}",
            )

    # Note: living+kitchen open plan is implicitly satisfied by not adding a wall.
    _ = has_open_living_kitchen

    return products


def _add_door_in_wall(
    *,
    model: ifcopenshell.file,
    context: ifcopenshell.entity_instance,
    wall: ifcopenshell.entity_instance,
    p1: tuple[float, float],
    p2: tuple[float, float],
    wall_thickness_m: float,
    door_width_m: float,
    door_height_m: float,
    along_m: float,
    name: str,
) -> list[ifcopenshell.entity_instance]:
    x1, y1 = p1
    x2, y2 = p2
    dx = x2 - x1
    dy = y2 - y1
    length = float((dx * dx + dy * dy) ** 0.5)
    if length <= 0.01:
        return []

    # Clamp along position to keep door inside the wall segment.
    along_m = float(max(0.2, min(length - 0.2, along_m)))
    door_width_m = float(max(0.6, min(1.2, door_width_m)))
    door_height_m = float(max(1.9, min(2.4, door_height_m)))

    x_dir = np.array([dx / length, dy / length, 0.0], dtype=np.float64)
    z_dir = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    y_dir = np.cross(z_dir, x_dir)

    origin = np.array([x1, y1, 0.0], dtype=np.float64) + x_dir * (along_m - door_width_m / 2.0)
    opening_thickness = max(0.05, wall_thickness_m * 3.0)

    opening = ifcopenshell.api.root.create_entity(model, ifc_class="IfcOpeningElement", name=f"Opening {name}")
    opening_rep = ifcopenshell.api.geometry.add_wall_representation(
        model,
        context=context,
        length=door_width_m,
        height=door_height_m,
        thickness=opening_thickness,
    )
    ifcopenshell.api.geometry.assign_representation(model, product=opening, representation=opening_rep)
    opening_origin = origin + y_dir * (-wall_thickness_m)
    opening_matrix = _matrix_from_axes(opening_origin, x_dir, z_dir)
    ifcopenshell.api.geometry.edit_object_placement(model, product=opening, matrix=opening_matrix, is_si=True)
    ifcopenshell.api.feature.add_feature(model, feature=opening, element=wall)

    door = ifcopenshell.api.root.create_entity(model, ifc_class="IfcDoor", name=name)
    door_rep = ifcopenshell.api.geometry.add_door_representation(
        model,
        context=context,
        overall_height=door_height_m,
        overall_width=door_width_m,
    )
    if door_rep is not None:
        ifcopenshell.api.geometry.assign_representation(model, product=door, representation=door_rep)
    door_matrix = _matrix_from_axes(origin, x_dir, z_dir)
    ifcopenshell.api.geometry.edit_object_placement(model, product=door, matrix=door_matrix, is_si=True)
    ifcopenshell.api.feature.add_filling(model, opening=opening, element=door)

    return [opening, door]


def _add_perimeter_windows(
    *,
    model: ifcopenshell.file,
    context: ifcopenshell.entity_instance,
    walls: list[ifcopenshell.entity_instance],
    wall_segments: list[tuple[tuple[float, float], tuple[float, float]]],
    wall_thickness_m: float,
    storey_height_m: float,
    windows_per_wall: int,
    size_preset: str = "medium",
    avoid_zone_bounds_xy: tuple[float, float, float, float] | None = None,
    skip_wall_indices: set[int] | None = None,
) -> list[ifcopenshell.entity_instance]:
    # Basic defaults in meters
    sill_height_m = 0.9
    head_clearance_m = 0.3
    edge_margin_m = 0.5
    default_window_w = 1.2
    default_window_h = 1.2

    preset = (size_preset or "medium").strip().lower()
    if preset == "small":
        default_window_w = 0.6
        default_window_h = 0.6
        sill_height_m = 1.2
    elif preset == "large":
        default_window_w = 2.0
        default_window_h = 1.4
        sill_height_m = 0.7

    if windows_per_wall <= 0:
        return []

    products: list[ifcopenshell.entity_instance] = []

    max_window_h = max(0.0, storey_height_m - sill_height_m - head_clearance_m)
    if max_window_h < 0.4:
        return []
    window_h = min(default_window_h, max_window_h)

    opening_thickness = max(0.05, wall_thickness_m * 3.0)

    def _is_in_avoid_zone(xy: np.ndarray) -> bool:
        if avoid_zone_bounds_xy is None:
            return False
        xmin, xmax, ymin, ymax = avoid_zone_bounds_xy
        # Small tolerance: avoid borderline placements
        tol = 0.2
        x, y = float(xy[0]), float(xy[1])
        return (xmin - tol) <= x <= (xmax + tol) and (ymin - tol) <= y <= (ymax + tol)

    skip_wall_indices = skip_wall_indices or set()
    for wall_idx, (wall, (p1, p2)) in enumerate(zip(walls, wall_segments), start=1):
        if wall_idx in skip_wall_indices:
            continue
        x1, y1 = p1
        x2, y2 = p2
        dx = x2 - x1
        dy = y2 - y1
        length = float((dx * dx + dy * dy) ** 0.5)
        if length < (edge_margin_m * 2 + 0.4):
            continue

        usable = max(0.0, length - 2 * edge_margin_m)
        if usable < 0.4:
            continue

        # Window width cannot exceed available segment per window.
        segment = usable / windows_per_wall
        window_w = min(default_window_w, max(0.4, segment * 0.8))

        x_dir = np.array([dx / length, dy / length, 0.0], dtype=np.float64)
        z_dir = np.array([0.0, 0.0, 1.0], dtype=np.float64)
        y_dir = np.cross(z_dir, x_dir)

        for win_idx in range(windows_per_wall):
            # place windows evenly within the usable length
            center_along = edge_margin_m + (win_idx + 0.5) * segment
            along = center_along - window_w / 2.0
            origin = np.array([x1, y1, 0.0], dtype=np.float64) + x_dir * along + z_dir * sill_height_m

            if _is_in_avoid_zone(origin[0:2]):
                continue

            opening = ifcopenshell.api.root.create_entity(
                model, ifc_class="IfcOpeningElement", name=f"Opening W{wall_idx}-{win_idx + 1}"
            )
            opening_rep = ifcopenshell.api.geometry.add_wall_representation(
                model,
                context=context,
                length=window_w,
                height=window_h,
                thickness=opening_thickness,
            )
            ifcopenshell.api.geometry.assign_representation(model, product=opening, representation=opening_rep)

            # Shift opening to ensure it intersects wall thickness.
            opening_origin = origin + y_dir * (-wall_thickness_m)
            opening_matrix = _matrix_from_axes(opening_origin, x_dir, z_dir)
            ifcopenshell.api.geometry.edit_object_placement(model, product=opening, matrix=opening_matrix, is_si=True)
            ifcopenshell.api.feature.add_feature(model, feature=opening, element=wall)

            window = ifcopenshell.api.root.create_entity(model, ifc_class="IfcWindow", name=f"Window {wall_idx}-{win_idx + 1}")
            window_rep = ifcopenshell.api.geometry.add_window_representation(
                model,
                context=context,
                overall_height=window_h,
                overall_width=window_w,
            )
            ifcopenshell.api.geometry.assign_representation(model, product=window, representation=window_rep)
            window_matrix = _matrix_from_axes(origin, x_dir, z_dir)
            ifcopenshell.api.geometry.edit_object_placement(model, product=window, matrix=window_matrix, is_si=True)
            ifcopenshell.api.feature.add_filling(model, opening=opening, element=window)

            products.extend([opening, window])

    return products


def _matrix_from_axes(origin: np.ndarray, x_axis: np.ndarray, z_axis: np.ndarray) -> np.ndarray:
    x = x_axis / (np.linalg.norm(x_axis) or 1.0)
    z = z_axis / (np.linalg.norm(z_axis) or 1.0)
    y = np.cross(z, x)
    y = y / (np.linalg.norm(y) or 1.0)
    m = np.eye(4, dtype=np.float64)
    m[0:3, 0] = x
    m[0:3, 1] = y
    m[0:3, 2] = z
    m[0:3, 3] = origin[0:3]
    return m
