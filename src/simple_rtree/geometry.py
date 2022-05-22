import abc
from typing import Any, Dict, Optional, Tuple

from shapely.geometry import Polygon, box
from shapely.geometry.base import BaseGeometry


class RtreeSpatial(abc.ABC):
    """
    Interface representing any spatial object in the index.

    Has basic spatial objects' properties and predicates defined.
    """

    geometry: BaseGeometry

    @property
    def area(self) -> float:
        return self.geometry.area

    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        return self.geometry.bounds

    def contains(self, other: "RtreeSpatial") -> bool:
        return self.geometry.contains(other.geometry)

    def intersects(self, other: "RtreeSpatial") -> bool:
        return self.geometry.intersects(other.geometry)

    def covers(self, other: "RtreeSpatial") -> bool:
        return self.geometry.covers(other.geometry)


class RtreeBoundingRectangle(RtreeSpatial):

    def __init__(self, geometry: Polygon):
        self.geometry = geometry

    def union(self, mbr: "RtreeBoundingRectangle") -> "RtreeBoundingRectangle":
        unioned = self.geometry.union(mbr.geometry)

        # unioning two the same zero-area polygons results in empty polygon
        if unioned.is_empty:
            return self
        else:
            return RtreeBoundingRectangle(box(*unioned.bounds))


class RtreeGeometry(RtreeSpatial):

    def __init__(self, geometry: BaseGeometry, mbr: RtreeBoundingRectangle,
                 attributes: Optional[Dict[str, Any]] = None):
        self.geometry = geometry
        self.mbr = mbr
        self.attributes = attributes

    def __str__(self):
        return f"Geometry with MBR: {self.mbr.bounds}"
