"""Conservative IFC4 adapter: one furniture, project-world XY, immutable source."""

from dataclasses import dataclass
from fractions import Fraction
import math
import re
from threading import RLock

import ifcopenshell
import ifcopenshell.validate

from neurobuild.domain.contracts import MoveFurniture, Target
from neurobuild.domain.errors import DomainError


# IfcOpenShell's parser log is process-global. Keep this adapter's parse/check paired.
_PARSE_LOCK = RLock()
_IDENTITY = (1.0, 0.0, 0.0, 0.0, 0.0)  # cos, sin, x, y, z in project units


@dataclass(frozen=True)
class InventoryItem:
    target: Target
    name: str | None


def _require(condition, code, message):
    if not condition:
        raise DomainError(code, message)


def _vector(value):
    _require(value is not None and len(value) == 3
             and all(type(number) in (int, float) and math.isfinite(number) for number in value),
             "IFC_UNSUPPORTED_PLACEMENT", "Placement requires three finite coordinates")
    return tuple(float(number) for number in value)


def _spf_record_ids(text):
    """Validate our simple SPF envelope/record subset before a permissive parser."""
    records, buffer, depth, quoted, index, complete = [], [], 0, False, 0, False
    while index < len(text):
        char = text[index]
        if not quoted and text[index:index + 2] == "/*":
            end = text.find("*/", index + 2)
            _require(end >= 0, "IFC_INVALID", "Unterminated IFC comment")
            buffer.append(" ")
            index = end + 2
            continue
        _require(not complete or char.isspace() or char == ";", "IFC_INVALID", "Unexpected text after IFC entity arguments")
        if char == "'":
            buffer.append(char)
            if quoted and text[index:index + 2] == "''":
                buffer.append("'")
                index += 2
                continue
            quoted = not quoted
        elif quoted:
            buffer.append(char)
        elif char == ";":
            _require(depth == 0 and bool("".join(buffer).strip()), "IFC_INVALID", "Invalid IFC record boundary")
            records.append("".join(buffer).strip())
            buffer = []
            complete = False
        else:
            depth += 1 if char == "(" else -1 if char == ")" else 0
            _require(depth >= 0, "IFC_INVALID", "Unbalanced IFC record")
            if char == ")" and depth == 0:
                complete = True
            buffer.append(char)
        index += 1
    _require(not quoted and depth == 0 and not "".join(buffer).strip(), "IFC_INVALID", "Incomplete IFC record")
    _require(len(records) >= 9 and records[:2] == ["ISO-10303-21", "HEADER"]
             and records[5:7] == ["ENDSEC", "DATA"] and records[-2:] == ["ENDSEC", "END-ISO-10303-21"],
             "IFC_INVALID", "Only one standard IFC header and DATA section are supported")
    for record, name in zip(records[2:5], ("FILE_DESCRIPTION", "FILE_NAME", "FILE_SCHEMA")):
        _require(re.fullmatch(name + r"\s*\(.*\)", record, re.DOTALL) is not None,
                 "IFC_INVALID", "Unsupported IFC header record")
    identifiers = set()
    for record in records[7:-2]:
        match = re.fullmatch(r"#([1-9][0-9]*)\s*=\s*[A-Z][A-Z0-9_]*\s*\(.*\)", record, re.DOTALL)
        _require(match is not None, "IFC_INVALID", "Unsupported or invalid IFC DATA record")
        identity = int(match.group(1))
        _require(identity not in identifiers, "IFC_INVALID", "Duplicate numeric IFC entity identifier")
        identifiers.add(identity)
    return identifiers


def _tolerance(value):
    return min(Fraction(1, 10**9), abs(value) / 10**9) if value else Fraction(1, 10**9)


def _metres_as_float(value):
    number = float(value)
    _require(math.isfinite(number) and (value.is_zero() or number != 0),
             "IFC_INVALID_OPERATION", "Movement is outside the representable IFC numeric range")
    exact = Fraction(value)
    _require(abs(Fraction(number) - exact) <= _tolerance(exact),
             "IFC_INVALID_OPERATION", "Movement loses precision at the IFC numeric boundary")
    return number


def _axis_transform(axis):
    _require(axis is not None and axis.is_a() == "IfcAxis2Placement3D",
             "IFC_UNSUPPORTED_PLACEMENT", "Only upright 3D axis placements are supported")
    x, y, z = _vector(axis.Location.Coordinates if axis.Location is not None else None)
    _require((axis.Axis is None) == (axis.RefDirection is None),
             "IFC_UNSUPPORTED_PLACEMENT", "Axis and reference direction must both be supplied or omitted")
    up = (0.0, 0.0, 1.0) if axis.Axis is None else _vector(axis.Axis.DirectionRatios)
    forward = (1.0, 0.0, 0.0) if axis.RefDirection is None else _vector(axis.RefDirection.DirectionRatios)
    _require(up[0] == 0 and up[1] == 0 and up[2] > 0 and forward[2] == 0,
             "IFC_UNSUPPORTED_PLACEMENT", "Tilted or inverted placement axes are unsupported")
    largest = max(abs(forward[0]), abs(forward[1]))
    _require(largest > 0, "IFC_UNSUPPORTED_PLACEMENT", "Reference direction must be nonzero")
    fx, fy = forward[0] / largest, forward[1] / largest
    norm = math.hypot(fx, fy)
    return fx / norm, fy / norm, x, y, z


def _world(placement):
    chain, seen = [], set()
    while placement is not None:
        _require(placement.is_a() == "IfcLocalPlacement" and placement.id() not in seen,
                 "IFC_UNSUPPORTED_PLACEMENT", "Only acyclic local placement chains are supported")
        seen.add(placement.id())
        chain.append(_axis_transform(placement.RelativePlacement))
        placement = placement.PlacementRelTo
    c, s, x, y, z = _IDENTITY
    for lc, ls, lx, ly, lz in reversed(chain):
        c, s, x, y, z = c * lc - s * ls, s * lc + c * ls, x + c * lx - s * ly, y + s * lx + c * ly, z + lz
    _require(all(math.isfinite(value) for value in (c, s, x, y, z)),
             "IFC_UNSUPPORTED_PLACEMENT", "Placement chain exceeds finite coordinate range")
    _require(math.isclose(c * c + s * s, 1.0, rel_tol=0, abs_tol=1e-12),
             "IFC_UNSUPPORTED_PLACEMENT", "Placement chain does not preserve a rigid rotation basis")
    return c, s, x, y, z


def _attribute(value):
    if isinstance(value, ifcopenshell.entity_instance):
        if value.id():
            return ("reference", value.id())
        return ("typed_value", value.is_a(), tuple(_attribute(part) for part in value))
    if isinstance(value, (tuple, list)):
        return tuple(_attribute(part) for part in value)
    if isinstance(value, float):
        _require(math.isfinite(value), "IFC_INVALID", "IFC attributes must contain finite numbers")
    return value


def _snapshot(model, target_id=None):
    result = {}
    for entity in model:
        attributes = tuple(
            "TARGET_PLACEMENT" if entity.id() == target_id and entity.attribute_name(index) == "ObjectPlacement"
            else _attribute(value)
            for index, value in enumerate(entity)
        )
        result[entity.id()] = (entity.is_a(), attributes)
    return result


class IfcEngine:
    """Stateless, headless byte-to-byte IFC operation; never touches artifact storage."""

    def inventory(self, source: bytes) -> tuple[InventoryItem, ...]:
        try:
            model = self._load(source)
            _, inventory, _ = self._inspect(model)
            _snapshot(model)
            return inventory
        except DomainError:
            raise
        except Exception:
            raise DomainError("IFC_INVALID", "IFC inventory could not be validated") from None

    def move_furniture(self, source: bytes, target: Target, operation: MoveFurniture) -> bytes:
        _require(type(target) is Target and type(operation) is MoveFurniture,
                 "IFC_INVALID_OPERATION", "A resolved target and MOVE_FURNITURE operation are required")
        try:
            return self._move(source, target, operation)
        except DomainError:
            raise
        except Exception:
            raise DomainError("IFC_INVALID", "IFC movement could not be validated") from None

    @staticmethod
    def _load(source):
        _require(type(source) is bytes and bool(source), "IFC_INVALID", "Nonempty IFC-SPF bytes are required")
        try:
            text = source.decode("utf-8-sig")
            expected_ids = _spf_record_ids(text)
            with _PARSE_LOCK:
                ifcopenshell.get_log()
                model = ifcopenshell.file.from_string(text)
                parse_log = ifcopenshell.get_log()
                _require(model.schema == "IFC4", "IFC_UNSUPPORTED_SCHEMA", "Only IFC4 is supported")
                global_ids = [root.GlobalId for root in model.by_type("IfcRoot")]
                _require(len(global_ids) == len(set(global_ids)), "IFC_DUPLICATE_GLOBAL_ID", "IFC GlobalIds must be unique")
                _require(not parse_log, "IFC_INVALID", "IFC parser reported invalid or unsupported input")
                _require({entity.id() for entity in model} == expected_ids, "IFC_INVALID", "IFC parsing dropped or changed a DATA record")
            return model
        except DomainError:
            raise
        except Exception:
            raise DomainError("IFC_INVALID", "IFC-SPF parsing failed") from None

    @staticmethod
    def _inspect(model):
        roots, ids = model.by_type("IfcRoot"), set()
        for root in roots:
            global_id = root.GlobalId
            _require(isinstance(global_id, str) and re.fullmatch(r"[0-3][0-9A-Za-z_$]{21}", global_id) is not None,
                     "IFC_INVALID", "IFC roots require valid compressed GlobalIds")
            _require(global_id not in ids, "IFC_DUPLICATE_GLOBAL_ID", "IFC GlobalIds must be unique")
            ids.add(global_id)
        projects = model.by_type("IfcProject")
        _require(len(projects) == 1, "IFC_UNSUPPORTED_STRUCTURE", "Exactly one IFC project is required")
        assignment = projects[0].UnitsInContext
        _require(assignment is not None, "IFC_UNSUPPORTED_UNIT", "Project length unit is required")
        units = [unit for unit in assignment.Units if getattr(unit, "UnitType", None) == "LENGTHUNIT"]
        _require(len(units) == 1 and units[0].is_a() == "IfcSIUnit" and units[0].Name == "METRE"
                 and units[0].Prefix in (None, "CENTI", "MILLI"),
                 "IFC_UNSUPPORTED_UNIT", "Only one SI metre, centimetre or millimetre length unit is supported")
        scale = {None: 1.0, "CENTI": 0.01, "MILLI": 0.001}[units[0].Prefix]
        _require(not model.by_type("IfcMapConversion"), "IFC_UNSUPPORTED_PLACEMENT", "Map conversion is outside the initial coordinate contract")
        contexts = tuple(projects[0].RepresentationContexts or ())
        _require(len(contexts) == 1 and contexts[0].is_a() == "IfcGeometricRepresentationContext",
                 "IFC_UNSUPPORTED_PLACEMENT", "Exactly one explicit project 3D representation context is required")
        for context in model.by_type("IfcGeometricRepresentationContext", include_subtypes=False):
            _require(context.CoordinateSpaceDimension == 3 and _axis_transform(context.WorldCoordinateSystem) == _IDENTITY,
                     "IFC_UNSUPPORTED_PLACEMENT", "Only identity 3D representation world coordinate systems are supported")
        for transform in model.by_type("IfcCartesianTransformationOperator"):
            _require(all(getattr(transform, name, None) in (None, 1.0) for name in ("Scale", "Scale2", "Scale3")),
                     "IFC_UNSUPPORTED_PLACEMENT", "Scaled mapped representations are outside the initial scope")
        world = {}
        for product in model.by_type("IfcProduct"):
            if product.ObjectPlacement is not None:
                world[product.id()] = _world(product.ObjectPlacement)
        inventory = []
        for furniture in model.by_type("IfcFurniture"):
            _require(furniture.ObjectPlacement is not None, "IFC_UNSUPPORTED_PLACEMENT", "Furniture requires an explicit placement")
            containers = tuple(furniture.ContainedInStructure)
            _require(len(containers) == 1 and containers[0].RelatingStructure.is_a() == "IfcBuildingStorey"
                     and tuple(containers[0].RelatedElements).count(furniture) == 1,
                     "IFC_UNSUPPORTED_STRUCTURE", "Furniture requires one direct building-storey containment")
            for relation in model.get_inverse(furniture):
                _require(not relation.is_a("IfcRelAggregates") and not relation.is_a("IfcRelNests")
                         and not relation.is_a("IfcRelVoidsElement") and not relation.is_a("IfcRelProjectsElement")
                         and not relation.is_a("IfcRelFillsElement"),
                         "IFC_UNSUPPORTED_STRUCTURE", "Furniture assemblies, nesting and attached features are unsupported")
            target = Target(furniture.GlobalId, containers[0].RelatingStructure.GlobalId)
            inventory.append(InventoryItem(target, furniture.Name))
        with _PARSE_LOCK:
            ifcopenshell.get_log()
            logger = ifcopenshell.validate.json_logger()
            ifcopenshell.validate.validate(model, logger, express_rules=False)
            _require(not logger.statements and not ifcopenshell.get_log(),
                     "IFC_INVALID", "IFC attributes or relationships failed schema validation")
        return scale, tuple(sorted(inventory, key=lambda item: item.target.global_id)), world

    def _move(self, source, target, operation):
        model = self._load(source)
        scale, inventory, before_world = self._inspect(model)
        matches = [item for item in inventory if item.target.global_id == target.global_id]
        if not matches:
            existing = any(root.GlobalId == target.global_id for root in model.by_type("IfcRoot"))
            raise DomainError("IFC_TARGET_MISMATCH" if existing else "IFC_TARGET_NOT_FOUND",
                              "Target is not present in the actual furniture inventory")
        _require(matches[0].target == target, "IFC_TARGET_MISMATCH", "Target storey/type differs from the actual inventory")
        furniture = model.by_guid(target.global_id)
        before = _snapshot(model, furniture.id())
        dx, dy = _metres_as_float(operation.dx.metres), _metres_as_float(operation.dy.metres)
        old_placement = furniture.ObjectPlacement
        axis = old_placement.RelativePlacement
        pc, ps, _, _, _ = _world(old_placement.PlacementRelTo)
        old_x, old_y, old_z = _vector(axis.Location.Coordinates)
        new_coordinates = (old_x + (pc * dx + ps * dy) / scale,
                           old_y + (-ps * dx + pc * dy) / scale, old_z)
        _require(all(math.isfinite(value) for value in new_coordinates),
                 "IFC_INVALID_OPERATION", "Movement would exceed finite IFC coordinates")
        location = model.create_entity("IfcCartesianPoint", Coordinates=new_coordinates)
        new_axis = model.create_entity("IfcAxis2Placement3D", Location=location, Axis=axis.Axis, RefDirection=axis.RefDirection)
        furniture.ObjectPlacement = model.create_entity("IfcLocalPlacement", PlacementRelTo=old_placement.PlacementRelTo,
                                                        RelativePlacement=new_axis)
        output = model.to_string().encode("utf-8")
        reopened = self._load(output)
        after_scale, after_inventory, after_world = self._inspect(reopened)
        after = _snapshot(reopened, furniture.id())
        _require(set(before) <= set(after) and len(after) == len(before) + 3
                 and all(after[identity] == values for identity, values in before.items()),
                 "IFC_INVARIANT_VIOLATION", "An original IFC entity changed beyond the target placement reference")
        _require(scale == after_scale and inventory == after_inventory and set(before_world) == set(after_world),
                 "IFC_INVARIANT_VIOLATION", "Units, inventory or product identity changed")
        for identity, previous in before_world.items():
            current = after_world[identity]
            if identity != furniture.id():
                _require(previous == current, "IFC_INVARIANT_VIOLATION", "A non-target product placement changed")
                continue
            _require(previous[:2] == current[:2] and previous[4] == current[4],
                     "IFC_INVARIANT_VIOLATION", "Target orientation or Z changed")
            for old, new, requested in zip(previous[2:4], current[2:4], (operation.dx.metres, operation.dy.metres)):
                actual = (Fraction(new) - Fraction(old)) * Fraction(str(scale))
                expected = Fraction(requested)
                _require(abs(actual - expected) <= _tolerance(expected),
                         "IFC_INVARIANT_VIOLATION", "Serialized target movement differs from the requested world XY delta")
        return output
