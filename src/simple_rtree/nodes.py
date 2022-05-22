from typing import Generic, List, TypeVar

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
        return f"Node with MBR: {self.mbr.bounds} at level {self.level}"

    def add_child(self, child: MBRBounded) -> None:
        self.children.append(child)
        self.mbr = self.mbr.union(child.mbr)

    def drop_child(self, pos: int) -> MBRBounded:
        dropped = self.children.pop(pos)
        dropped_bounds = dropped.mbr.bounds

        for idx, coord in enumerate(dropped_bounds):
            if coord == self.mbr.bounds[idx]:
                # Perform reduce
                children_mbrs = (child.mbr for child in self.children[1:])
                current_mbr = self.children[0].mbr
                for mbr in children_mbrs:  # with 1st mbr excluded
                    current_mbr = current_mbr.union(mbr)
                self.mbr = current_mbr
                break  # Stop as we've already shrinked the mbr
        return dropped

    def find_mbr_union(self, other_node: "RtreeNode") -> RtreeBoundingRectangle:
        return self.mbr.union(other_node.mbr)
