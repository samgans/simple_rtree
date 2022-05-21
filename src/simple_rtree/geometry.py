from typing import Any, Dict, Optional, Tuple

from shapely.geometry import Polygon, box
from shapely.geometry.base import BaseGeometry


class RtreeBoundingRectangle:

    def __init__(self, geometry: Polygon):
        self.geometry = geometry

    @property
    def area(self) -> float:
        return self.geometry.area

    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        return self.geometry.bounds

    def union(self, mbr: "RtreeBoundingRectangle") -> "RtreeBoundingRectangle":
        return RtreeBoundingRectangle(
            box(*self.geometry.union(mbr.geometry).bounds)
        )


class RtreeGeometry:

    def __init__(self, geometry: BaseGeometry, mbr: RtreeBoundingRectangle,
                 attributes: Optional[Dict[str, Any]] = None):
        self.geometry = geometry
        self.mbr = mbr
        self.attributes = attributes

    def __str__(self):
        return f"Geometry with MBR: {self.mbr.bounds}"
