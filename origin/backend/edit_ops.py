from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OpResult:
    applied: list[dict[str, Any]]
    skipped: list[dict[str, Any]]


_SUPPORTED_OPS = {
    "set_windows_per_wall",
    "remove_all_windows",
    "set_windows_size_preset",
    "set_avoid_bathroom_zone",
    "set_exterior_door",
    "add_exterior_door",
    "set_bathroom_count",
    "add_bathroom",
    "increment_bathroom_count",
}


def apply_ops(*, params: Any, layout_spec: dict | None, ops: list[dict[str, Any]]) -> tuple[Any, dict | None, OpResult]:
    """Apply validated edit operations to params/layout.

    `params` is expected to be a BuildingParams-like object (frozen dataclass) so we rebuild it via type(params)(...).
    """

    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    if layout_spec is None:
        layout_spec = None

    def _skip(op: dict[str, Any], reason: str):
        skipped.append({"op": op, "reason": reason})

    def _apply(op: dict[str, Any]):
        applied.append(op)

    def _get_bathroom_count_from_layout(spec: dict | None) -> int:
        if not spec or not isinstance(spec, dict):
            return 0
        constraints = spec.get("constraints") if isinstance(spec.get("constraints"), dict) else {}
        spaces = spec.get("spaces") if isinstance(spec.get("spaces"), list) else []
        val = None
        if isinstance(constraints, dict):
            val = constraints.get("bathroom_count")
        if val is not None:
            try:
                return max(0, int(val))
            except Exception:
                return 0
        total = 0
        for s in spaces:
            if not isinstance(s, dict):
                continue
            if (s.get("type") or "") == "bathroom":
                try:
                    total += int(s.get("count") or 0)
                except Exception:
                    total += 0
        return max(0, total)

    for op in ops or []:
        if not isinstance(op, dict):
            _skip({"raw": op}, "op must be an object")
            continue
        op_type = (op.get("op") or op.get("type") or "").strip()
        if op_type not in _SUPPORTED_OPS:
            _skip(op, f"unsupported op: {op_type}")
            continue

        if op_type in ("set_windows_per_wall",):
            value = op.get("value")
            try:
                value_int = int(value)
            except Exception:
                _skip(op, "value must be int")
                continue
            value_int = max(0, min(10, value_int))
            params = type(params)(
                width_m=params.width_m,
                depth_m=params.depth_m,
                height_m=params.height_m,
                wall_thickness_m=params.wall_thickness_m,
                slab_thickness_m=params.slab_thickness_m,
                windows_per_wall=value_int,
                windows_size_preset=getattr(params, "windows_size_preset", "medium"),
                avoid_bathroom_zone=getattr(params, "avoid_bathroom_zone", False),
                exterior_door=getattr(params, "exterior_door", False),
            )
            _apply({"op": "set_windows_per_wall", "value": value_int})
            continue

        if op_type == "remove_all_windows":
            params = type(params)(
                width_m=params.width_m,
                depth_m=params.depth_m,
                height_m=params.height_m,
                wall_thickness_m=params.wall_thickness_m,
                slab_thickness_m=params.slab_thickness_m,
                windows_per_wall=0,
                windows_size_preset=getattr(params, "windows_size_preset", "medium"),
                avoid_bathroom_zone=getattr(params, "avoid_bathroom_zone", False),
                exterior_door=getattr(params, "exterior_door", False),
            )
            _apply({"op": "remove_all_windows"})
            continue

        if op_type == "set_windows_size_preset":
            value = str(op.get("value") or "").strip().lower()
            if value not in ("small", "medium", "large"):
                _skip(op, "value must be one of small|medium|large")
                continue
            params = type(params)(
                width_m=params.width_m,
                depth_m=params.depth_m,
                height_m=params.height_m,
                wall_thickness_m=params.wall_thickness_m,
                slab_thickness_m=params.slab_thickness_m,
                windows_per_wall=getattr(params, "windows_per_wall", 0),
                windows_size_preset=value,
                avoid_bathroom_zone=getattr(params, "avoid_bathroom_zone", False),
                exterior_door=getattr(params, "exterior_door", False),
            )
            _apply({"op": "set_windows_size_preset", "value": value})
            continue

        if op_type == "set_avoid_bathroom_zone":
            value = op.get("value")
            if not isinstance(value, bool):
                _skip(op, "value must be bool")
                continue
            params = type(params)(
                width_m=params.width_m,
                depth_m=params.depth_m,
                height_m=params.height_m,
                wall_thickness_m=params.wall_thickness_m,
                slab_thickness_m=params.slab_thickness_m,
                windows_per_wall=getattr(params, "windows_per_wall", 0),
                windows_size_preset=getattr(params, "windows_size_preset", "medium"),
                avoid_bathroom_zone=value,
                exterior_door=getattr(params, "exterior_door", False),
            )
            _apply({"op": "set_avoid_bathroom_zone", "value": value})
            continue

        if op_type in ("set_exterior_door", "add_exterior_door"):
            # add_exterior_door is an alias (MVP only supports boolean)
            value = op.get("value")
            if value is None:
                value = True
            if not isinstance(value, bool):
                _skip(op, "value must be bool")
                continue
            params = type(params)(
                width_m=params.width_m,
                depth_m=params.depth_m,
                height_m=params.height_m,
                wall_thickness_m=params.wall_thickness_m,
                slab_thickness_m=params.slab_thickness_m,
                windows_per_wall=getattr(params, "windows_per_wall", 0),
                windows_size_preset=getattr(params, "windows_size_preset", "medium"),
                avoid_bathroom_zone=getattr(params, "avoid_bathroom_zone", False),
                exterior_door=value,
            )
            _apply({"op": "set_exterior_door", "value": value})
            continue

        if op_type == "set_bathroom_count":
            value = op.get("value")
            try:
                value_int = int(value)
            except Exception:
                _skip(op, "value must be int")
                continue
            value_int = max(0, min(10, value_int))

            base = dict(layout_spec or {})
            constraints = dict((base.get("constraints") or {}) if isinstance(base.get("constraints"), dict) else {})
            constraints["bathroom_count"] = value_int
            base["constraints"] = constraints
            layout_spec = base
            _apply({"op": "set_bathroom_count", "value": value_int})
            continue

        if op_type in ("add_bathroom", "increment_bathroom_count"):
            raw_inc = op.get("value")
            if raw_inc is None:
                inc = 1
            else:
                try:
                    inc = int(raw_inc)
                except Exception:
                    _skip(op, "value must be int")
                    continue
            inc = max(1, min(10, inc))

            base = dict(layout_spec or {})
            constraints = dict((base.get("constraints") or {}) if isinstance(base.get("constraints"), dict) else {})
            current = _get_bathroom_count_from_layout(base)
            new_val = max(0, min(10, int(current + inc)))
            constraints["bathroom_count"] = new_val
            base["constraints"] = constraints
            layout_spec = base
            _apply({"op": "add_bathroom", "value": inc, "result": new_val})
            continue

        _skip(op, "unhandled op")

    return params, layout_spec, OpResult(applied=applied, skipped=skipped)
