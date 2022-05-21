from typing import Generic, List, TypeVar, Union

from simple_rtree.geometry import RtreeBoundingRectangle, RtreeGeometry


MBRBounded = TypeVar("MBRBounded", RtreeGeometry, "RtreeNode")


class RtreeNode(Generic[MBRBounded]):

    def __init__(self, mbr: RtreeBoundingRectangle,
                 children: List[MBRBounded],
                 level: int):
        self.children: List[MBRBounded] = children
        self.mbr = mbr
        self.level = level
        self.is_leaf = (level == 0)

    def __str__(self):
        return f"Node with MBR: {self.mbr.bounds}"

    def add_child(self, child: MBRBounded) -> None:
        self.children.append(child)
        self.mbr = self.mbr.union(child.mbr)

    def find_mbr_union(self, other_node: "RtreeNode") -> RtreeBoundingRectangle:
        return self.mbr.union(other_node.mbr)
