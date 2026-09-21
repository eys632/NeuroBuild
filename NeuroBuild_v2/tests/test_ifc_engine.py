"""Real IfcOpenShell acceptance tests; fixtures are NOT HUMAN VERIFIED."""

from decimal import Decimal
import hashlib
import re
import unittest

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.placement
import ifcopenshell.validate

from neurobuild.domain.contracts import Length, LengthUnit, MoveFurniture, Target
from neurobuild.domain.errors import DomainError
from neurobuild.infrastructure.ifc_engine import IfcEngine
from tests.ifc_fixtures import build_fixture, direction, global_id, placement, point


def operation(dx="1", dy="-0.25", unit=LengthUnit.M):
    return MoveFurniture(Length(Decimal(dx), unit), Length(Decimal(dy), unit))


def reopen(source):
    return ifcopenshell.file.from_string(source.decode("utf-8"))


def matrix(model, object_id):
    # Independent official placement utility, not the engine's transform helper.
    return ifcopenshell.util.placement.get_local_placement(model.by_guid(object_id).ObjectPlacement)


class IfcEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = IfcEngine()

    def target(self, fixture):
        return Target(fixture.target_id, fixture.storey_id)

    def assert_refused(self, fixture, code, target=None):
        source = fixture.source()
        original_hash = hashlib.sha256(source).hexdigest()
        with self.assertRaises(DomainError) as caught:
            self.engine.move_furniture(source, target or self.target(fixture), operation())
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(hashlib.sha256(source).hexdigest(), original_hash)

    def assert_move(self, fixture, move):
        source = fixture.source()
        original_hash = hashlib.sha256(source).hexdigest()
        before = reopen(source)
        output = self.engine.move_furniture(source, self.target(fixture), move)
        after = reopen(output)
        self.assertIsInstance(output, bytes)
        self.assertEqual(hashlib.sha256(source).hexdigest(), original_hash)
        self.assertNotEqual(source, output)
        before_matrix, after_matrix = matrix(before, fixture.target_id), matrix(after, fixture.target_id)
        for axis, expected in enumerate((float(move.dx.metres), float(move.dy.metres), 0.0)):
            self.assertAlmostEqual((after_matrix[axis, 3] - before_matrix[axis, 3]) * fixture.metres_per_unit,
                                   expected, places=8)
        for row in range(3):
            for column in range(3):
                self.assertAlmostEqual(after_matrix[row, column], before_matrix[row, column], places=12)
        other_before, other_after = matrix(before, fixture.other_id), matrix(after, fixture.other_id)
        for row in range(4):
            for column in range(4):
                self.assertEqual(other_before[row, column], other_after[row, column])
        moved_before, moved_after = before.by_guid(fixture.target_id), after.by_guid(fixture.target_id)
        self.assertEqual(moved_before.GlobalId, moved_after.GlobalId)
        self.assertEqual(moved_before.ContainedInStructure[0].RelatingStructure.GlobalId,
                         moved_after.ContainedInStructure[0].RelatingStructure.GlobalId)
        self.assertEqual(str(moved_before.Representation), str(moved_after.Representation))
        # Every pre-existing entity except the target's placement reference must survive untouched.
        for entity in before:
            if entity.id() != moved_before.id():
                with self.subTest(unchanged_entity=entity.id()):
                    self.assertEqual(str(after.by_id(entity.id())), str(entity))
        before_info = moved_before.get_info()
        after_info = moved_after.get_info()
        before_info.pop("ObjectPlacement")
        after_info.pop("ObjectPlacement")
        self.assertEqual({key: str(value) for key, value in before_info.items()},
                         {key: str(value) for key, value in after_info.items()})
        return before, after, output

    def test_synthetic_fixture_passes_ifc_schema_validation(self):
        for unit in ("m", "cm", "mm"):
            with self.subTest(unit=unit):
                logger = ifcopenshell.validate.json_logger()
                ifcopenshell.validate.validate(reopen(build_fixture(unit).source()), logger)
                self.assertEqual(logger.statements, [])

    def test_inventory_exposes_only_actual_furniture_ids_and_names(self):
        fixture = build_fixture()
        inventory = self.engine.inventory(fixture.source())
        self.assertIsInstance(inventory, tuple)
        self.assertEqual({item.target.global_id for item in inventory}, {fixture.target_id, fixture.other_id})
        self.assertEqual({item.target.storey_global_id for item in inventory}, {fixture.storey_id})
        self.assertEqual({item.name for item in inventory}, {"창가 파란 책상", "입구 회색 책상"})

    def test_metre_centimetre_millimetre_files_produce_the_same_world_movement(self):
        for unit in ("m", "cm", "mm"):
            with self.subTest(unit=unit):
                self.assert_move(build_fixture(unit), operation("1000", "-250", LengthUnit.MM))

    def test_rotated_translated_parent_respects_world_xy_not_local_axes(self):
        for angle in (90, -90, 33):
            with self.subTest(parent_angle=angle):
                fixture = build_fixture("mm", storey_translation=(10, -20, 7), storey_angle_degrees=angle)
                self.assert_move(fixture, operation("0.4", "1.1"))

    def test_shared_placement_is_cloned_without_moving_other_furniture(self):
        fixture = build_fixture(share_placement=True)
        before, after, _ = self.assert_move(fixture, operation())
        self.assertEqual(before.by_guid(fixture.target_id).ObjectPlacement.id(),
                         before.by_guid(fixture.other_id).ObjectPlacement.id())
        self.assertNotEqual(after.by_guid(fixture.target_id).ObjectPlacement.id(),
                            after.by_guid(fixture.other_id).ObjectPlacement.id())

    def test_headless_mesh_vertices_confirm_world_metre_displacement(self):
        fixture = build_fixture("mm", storey_translation=(10, -20, 7), storey_angle_degrees=37)
        before, after, _ = self.assert_move(fixture, operation("0.75", "-0.2"))
        settings = ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS, True)
        for object_id, delta in ((fixture.target_id, (0.75, -0.2, 0.0)),
                                 (fixture.other_id, (0.0, 0.0, 0.0))):
            with self.subTest(object_id=object_id):
                old_shape = ifcopenshell.geom.create_shape(settings, before.by_guid(object_id))
                new_shape = ifcopenshell.geom.create_shape(settings, after.by_guid(object_id))
                old_vertices, new_vertices = tuple(old_shape.geometry.verts), tuple(new_shape.geometry.verts)
                self.assertGreater(len(old_vertices), 0)
                self.assertEqual(len(old_vertices), len(new_vertices))
                for index, (old, new) in enumerate(zip(old_vertices, new_vertices)):
                    self.assertAlmostEqual(new - old, delta[index % 3], places=7)

    def test_other_product_relative_to_old_target_placement_stays_put(self):
        fixture = build_fixture()
        fixture.other.ObjectPlacement.PlacementRelTo = fixture.target.ObjectPlacement
        self.assert_move(fixture, operation())

    def test_serialized_result_can_be_moved_again_and_schema_remains_valid(self):
        fixture = build_fixture("cm", storey_angle_degrees=45)
        _, after, output = self.assert_move(fixture, operation())
        restored = reopen(self.engine.move_furniture(output, self.target(fixture), operation("-1", "0.25")))
        initial = matrix(fixture.model, fixture.target_id)
        final = matrix(restored, fixture.target_id)
        for row in range(4):
            for column in range(4):
                self.assertAlmostEqual(initial[row, column], final[row, column], places=9)
        logger = ifcopenshell.validate.json_logger()
        ifcopenshell.validate.validate(after, logger)
        self.assertEqual(logger.statements, [])

    def test_invalid_source_and_unsupported_schema_are_rejected(self):
        fixture = build_fixture()
        for source in (b"", b"not an IFC document", b"\xff\xfe"):
            with self.subTest(source=source):
                with self.assertRaises(DomainError) as caught:
                    self.engine.inventory(source)
                self.assertEqual(caught.exception.code, "IFC_INVALID")
        other_schema = ifcopenshell.file(schema="IFC2X3").to_string().encode("utf-8")
        with self.assertRaises(DomainError) as caught:
            self.engine.move_furniture(other_schema, self.target(fixture), operation())
        self.assertEqual(caught.exception.code, "IFC_UNSUPPORTED_SCHEMA")

    def test_invalid_spf_records_or_missing_data_terminator_are_rejected(self):
        fixture = build_fixture()
        data, footer = fixture.source().rsplit(b"ENDSEC;", 1)
        malformed = {
            "unparsed_record": data + b"garbage!!;\nENDSEC;" + footer,
            "missing_data_endsec": data + footer,
        }
        for name, source in malformed.items():
            with self.subTest(case=name):
                for action in (
                    lambda: self.engine.inventory(source),
                    lambda: self.engine.move_furniture(source, self.target(fixture), operation()),
                ):
                    with self.assertRaises(DomainError) as caught:
                        action()
                    self.assertEqual(caught.exception.code, "IFC_INVALID")

    def test_legitimate_quoted_punctuation_and_comments_do_not_confuse_spf_guard(self):
        fixture = build_fixture()
        name = "회의실; #999=IFCWALL(); O'Brien /* quoted text */"
        fixture.target.Name = name
        source = fixture.source()
        self.assertIn(b"O''Brien", source)
        source = source.replace(b"DATA;\n", b"DATA;\n/* legal comment: ; #999='text'; ENDSEC; */\n", 1)
        inventory = self.engine.inventory(source)
        self.assertEqual(next(item.name for item in inventory if item.target.global_id == fixture.target_id), name)
        output = self.engine.move_furniture(source, self.target(fixture), operation())
        self.assertEqual(reopen(output).by_guid(fixture.target_id).Name, name)

    def test_missing_object_wrong_ifc_type_and_wrong_storey_are_rejected(self):
        fixture = build_fixture()
        self.assert_refused(fixture, "IFC_TARGET_NOT_FOUND", Target(global_id(999), fixture.storey_id))
        self.assert_refused(fixture, "IFC_TARGET_MISMATCH", Target(fixture.project_id, fixture.storey_id))
        self.assert_refused(fixture, "IFC_TARGET_MISMATCH", Target(fixture.target_id, global_id(998)))

    def test_tilted_parent_and_two_dimensional_or_grid_placements_are_rejected(self):
        fixture = build_fixture()
        fixture.storey.ObjectPlacement.RelativePlacement.Axis = direction(fixture.model, (0, 1, 1))
        self.assert_refused(fixture, "IFC_UNSUPPORTED_PLACEMENT")
        fixture = build_fixture()
        fixture.target.ObjectPlacement.RelativePlacement = fixture.model.create_entity(
            "IfcAxis2Placement2D", Location=point(fixture.model, (1, 2)))
        self.assert_refused(fixture, "IFC_UNSUPPORTED_PLACEMENT")
        fixture = build_fixture()
        axes = []
        for name, coordinates in (("A", ((0, 0, 0), (1, 0, 0))),
                                   ("1", ((0, 0, 0), (0, 1, 0)))):
            curve = fixture.model.create_entity("IfcPolyline", Points=[point(fixture.model, p) for p in coordinates])
            axes.append(fixture.model.create_entity("IfcGridAxis", AxisTag=name, AxisCurve=curve, SameSense=True))
        fixture.model.create_entity("IfcGrid", GlobalId=global_id(70), Name="Synthetic grid",
                                    ObjectPlacement=placement(fixture.model), UAxes=[axes[0]], VAxes=[axes[1]])
        intersection = fixture.model.create_entity("IfcVirtualGridIntersection", IntersectingAxes=axes,
                                                    OffsetDistances=(0.0, 0.0))
        fixture.target.ObjectPlacement = fixture.model.create_entity("IfcGridPlacement", PlacementLocation=intersection)
        logger = ifcopenshell.validate.json_logger()
        ifcopenshell.validate.validate(reopen(fixture.source()), logger)
        self.assertEqual(logger.statements, [], "Grid rejection must exercise valid unsupported geometry")
        self.assert_refused(fixture, "IFC_UNSUPPORTED_PLACEMENT")

    def test_nonidentity_or_2d_world_context_is_explicitly_rejected(self):
        fixture = build_fixture()
        context = fixture.model.by_type("IfcGeometricRepresentationContext")[0]
        context.WorldCoordinateSystem.Location.Coordinates = (100.0, 0.0, 0.0)
        self.assert_refused(fixture, "IFC_UNSUPPORTED_PLACEMENT")
        fixture = build_fixture()
        context = fixture.model.by_type("IfcGeometricRepresentationContext")[0]
        context.CoordinateSpaceDimension = 2
        context.WorldCoordinateSystem = fixture.model.create_entity("IfcAxis2Placement2D",
                                                                     Location=point(fixture.model, (0, 0)))
        self.assert_refused(fixture, "IFC_UNSUPPORTED_PLACEMENT")

    def test_partial_axes_and_nonhorizontal_reference_direction_are_rejected(self):
        fixture = build_fixture()
        fixture.target.ObjectPlacement.RelativePlacement.RefDirection = None
        self.assert_refused(fixture, "IFC_UNSUPPORTED_PLACEMENT")
        fixture = build_fixture()
        fixture.target.ObjectPlacement.RelativePlacement.RefDirection = direction(fixture.model, (1, 0, 0.1))
        self.assert_refused(fixture, "IFC_UNSUPPORTED_PLACEMENT")

    def test_cycles_and_missing_placements_are_rejected_without_recursive_failure(self):
        fixture = build_fixture()
        fixture.target.ObjectPlacement.PlacementRelTo = fixture.target.ObjectPlacement
        self.assert_refused(fixture, "IFC_UNSUPPORTED_PLACEMENT")
        fixture = build_fixture()
        fixture.target.ObjectPlacement = None
        self.assert_refused(fixture, "IFC_UNSUPPORTED_PLACEMENT")

    def test_missing_or_ambiguous_length_units_are_rejected(self):
        fixture = build_fixture()
        fixture.model.by_guid(fixture.project_id).UnitsInContext = None
        self.assert_refused(fixture, "IFC_UNSUPPORTED_UNIT")
        fixture = build_fixture()
        project = fixture.model.by_guid(fixture.project_id)
        second_length = fixture.model.create_entity("IfcSIUnit", UnitType="LENGTHUNIT", Prefix="MILLI", Name="METRE")
        project.UnitsInContext.Units = tuple(project.UnitsInContext.Units) + (second_length,)
        self.assert_refused(fixture, "IFC_UNSUPPORTED_UNIT")

    def test_duplicate_global_ids_are_rejected_before_selection(self):
        fixture = build_fixture()
        fixture.other.GlobalId = fixture.target_id
        self.assert_refused(fixture, "IFC_DUPLICATE_GLOBAL_ID")

    def test_duplicate_step_entity_numbers_are_not_silently_discarded(self):
        fixture = build_fixture()
        source = fixture.source()
        entity_line = re.search(rb"(?m)^#\d+=IFCCARTESIANPOINT\([^\n]+\);$", source)
        self.assertIsNotNone(entity_line)
        data, footer = source.rsplit(b"ENDSEC;", 1)
        invalid = data + entity_line.group() + b"\nENDSEC;" + footer
        with self.assertRaises(DomainError):
            self.engine.move_furniture(invalid, self.target(fixture), operation())

    def test_multiple_containment_relations_are_rejected(self):
        fixture = build_fixture()
        second_storey = fixture.model.create_entity(
            "IfcBuildingStorey", GlobalId=global_id(50), Name="Other floor",
            ObjectPlacement=placement(fixture.model), CompositionType="ELEMENT")
        fixture.model.create_entity("IfcRelContainedInSpatialStructure", GlobalId=global_id(51),
                                    RelatedElements=[fixture.target], RelatingStructure=second_storey)
        self.assert_refused(fixture, "IFC_UNSUPPORTED_STRUCTURE")

    def test_spatially_uncontained_or_nested_furniture_is_rejected(self):
        fixture = build_fixture()
        fixture.model.remove(fixture.target.ContainedInStructure[0])
        self.assert_refused(fixture, "IFC_UNSUPPORTED_STRUCTURE")
        fixture = build_fixture()
        fixture.model.create_entity("IfcRelAggregates", GlobalId=global_id(52),
                                    RelatingObject=fixture.target, RelatedObjects=[fixture.other])
        self.assert_refused(fixture, "IFC_UNSUPPORTED_STRUCTURE")

    def test_nonfinite_placement_is_rejected(self):
        fixture = build_fixture()
        # The STEP parser or placement validator must reject this; never emit a new IFC.
        source = fixture.source().replace(b"IFCCARTESIANPOINT((1.,2.,0.5))", b"IFCCARTESIANPOINT((1.E309,2.,0.5))")
        self.assertNotEqual(source, fixture.source())
        with self.assertRaises(DomainError):
            self.engine.move_furniture(source, self.target(fixture), operation())

    def test_unrepresentable_decimal_displacements_are_rejected(self):
        fixture = build_fixture()
        for displacement in ("1e999", "1e-999"):
            with self.subTest(displacement=displacement):
                with self.assertRaises(DomainError):
                    self.engine.move_furniture(fixture.source(), self.target(fixture), operation(displacement, "0"))

    def test_decimal_to_float_conversion_cannot_discard_metres_before_validation(self):
        fixture = build_fixture(storey_translation=(0, 0, 0))
        fixture.target.ObjectPlacement.RelativePlacement.Location.Coordinates = (0.0, 0.0, 0.0)
        with self.assertRaises(DomainError):
            self.engine.move_furniture(fixture.source(), self.target(fixture),
                                       operation("10000000000000000.25", "0"))

    def test_world_coordinates_cannot_silently_round_away_requested_movement(self):
        fixture = build_fixture(storey_translation=(1e16, 0, 3))
        for displacement in ("0.25", "1000000001.25"):
            with self.subTest(displacement=displacement):
                with self.assertRaises(DomainError):
                    self.engine.move_furniture(fixture.source(), self.target(fixture), operation(displacement, "0"))


if __name__ == "__main__":
    unittest.main()
