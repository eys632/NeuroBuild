"""AUTO-GENERATED / NOT HUMAN VERIFIED synthetic IFC4 acceptance fixtures.

No customer/building data is used. Low-level authoring follows the official API:
https://docs.ifcopenshell.org/ifcopenshell-python/hello_world.html
"""

from dataclasses import dataclass
import math
from uuid import UUID

import ifcopenshell
import ifcopenshell.guid


def global_id(number: int) -> str:
    return ifcopenshell.guid.compress(UUID(int=number).hex)


def point(model, coordinates):
    return model.create_entity("IfcCartesianPoint", Coordinates=tuple(float(v) for v in coordinates))


def direction(model, values):
    return model.create_entity("IfcDirection", DirectionRatios=tuple(float(v) for v in values))


def placement(model, parent=None, location=(0, 0, 0), angle_degrees=0):
    angle = math.radians(angle_degrees)
    axis = model.create_entity(
        "IfcAxis2Placement3D", Location=point(model, location),
        Axis=direction(model, (0, 0, 1)),
        RefDirection=direction(model, (math.cos(angle), math.sin(angle), 0)),
    )
    return model.create_entity("IfcLocalPlacement", PlacementRelTo=parent, RelativePlacement=axis)


@dataclass
class SyntheticIfc:
    model: ifcopenshell.file
    project_id: str
    storey_id: str
    target_id: str
    other_id: str
    metres_per_unit: float

    def source(self) -> bytes:
        return self.model.to_string().encode("utf-8")

    @property
    def target(self):
        return self.model.by_guid(self.target_id)

    @property
    def other(self):
        return self.model.by_guid(self.other_id)

    @property
    def storey(self):
        return self.model.by_guid(self.storey_id)


def build_fixture(
    unit="m", *, storey_translation=(0, 0, 3), storey_angle_degrees=0,
    target_angle_degrees=30, share_placement=False,
) -> SyntheticIfc:
    """A project/site/building/storey and two boxed furniture with known placement."""
    prefix, scale = {"m": (None, 1.0), "cm": ("CENTI", 0.01), "mm": ("MILLI", 0.001)}[unit]
    model = ifcopenshell.file(schema="IFC4")
    model.header.file_description.description = (
        "AUTO-GENERATED / NOT HUMAN VERIFIED; NeuroBuild synthetic acceptance fixture",
    )
    length = model.create_entity("IfcSIUnit", UnitType="LENGTHUNIT", Prefix=prefix, Name="METRE")
    units = model.create_entity("IfcUnitAssignment", Units=[length])
    world = model.create_entity("IfcAxis2Placement3D", Location=point(model, (0, 0, 0)))
    context = model.create_entity(
        "IfcGeometricRepresentationContext", ContextType="Model", CoordinateSpaceDimension=3,
        Precision=1e-8, WorldCoordinateSystem=world,
    )
    project = model.create_entity("IfcProject", GlobalId=global_id(1), Name="Synthetic project",
                                  UnitsInContext=units, RepresentationContexts=[context])
    site = model.create_entity("IfcSite", GlobalId=global_id(2), Name="Synthetic site",
                               ObjectPlacement=placement(model), CompositionType="ELEMENT")
    building = model.create_entity("IfcBuilding", GlobalId=global_id(3), Name="Synthetic building",
                                   ObjectPlacement=placement(model, site.ObjectPlacement),
                                   CompositionType="ELEMENT")
    storey = model.create_entity(
        "IfcBuildingStorey", GlobalId=global_id(4), Name="Synthetic storey",
        ObjectPlacement=placement(model, building.ObjectPlacement,
                                  tuple(v / scale for v in storey_translation), storey_angle_degrees),
        CompositionType="ELEMENT", Elevation=storey_translation[2] / scale,
    )
    for index, parent, child in ((20, project, site), (21, site, building), (22, building, storey)):
        model.create_entity("IfcRelAggregates", GlobalId=global_id(index),
                            RelatingObject=parent, RelatedObjects=[child])

    furniture = []
    for index, name, location, angle in (
        (5, "창가 파란 책상", (1, 2, 0.5), target_angle_degrees),
        (6, "입구 회색 책상", (4, 5, 0.5), 0),
    ):
        object_placement = placement(model, storey.ObjectPlacement,
                                     tuple(v / scale for v in location), angle)
        box_profile = model.create_entity("IfcRectangleProfileDef", ProfileType="AREA",
                                           XDim=1.2 / scale, YDim=0.6 / scale)
        solid = model.create_entity(
            "IfcExtrudedAreaSolid", SweptArea=box_profile,
            Position=model.create_entity("IfcAxis2Placement3D", Location=point(model, (0, 0, 0))),
            ExtrudedDirection=direction(model, (0, 0, 1)), Depth=0.75 / scale,
        )
        representation = model.create_entity("IfcShapeRepresentation", ContextOfItems=context,
                                              RepresentationIdentifier="Body", RepresentationType="SweptSolid",
                                              Items=[solid])
        definition = model.create_entity("IfcProductDefinitionShape", Representations=[representation])
        furniture.append(model.create_entity("IfcFurniture", GlobalId=global_id(index), Name=name,
                                              ObjectPlacement=object_placement, Representation=definition,
                                              PredefinedType="NOTDEFINED"))
    if share_placement:
        furniture[1].ObjectPlacement = furniture[0].ObjectPlacement
    model.create_entity("IfcRelContainedInSpatialStructure", GlobalId=global_id(23),
                        RelatedElements=furniture, RelatingStructure=storey)
    return SyntheticIfc(model, project.GlobalId, storey.GlobalId,
                        furniture[0].GlobalId, furniture[1].GlobalId, scale)
