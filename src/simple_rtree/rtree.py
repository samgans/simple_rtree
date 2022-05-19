from typing import List, Optional, Tuple, Union

from simple_rtree.geometry import RtreeBoundingRectangle, RtreeGeometry
from simple_rtree.nodes import RtreeNode


class Rtree:

    root: Optional[RtreeNode]

    def __init__(self, max_entries: int, min_entries: int,
                 split_method):
        self.max_entries = max_entries
        self.min_entries = min_entries
        self.split_method = split_method

    def _find_min_enlarged(self, mbr: RtreeBoundingRectangle,
                           nodes: List[RtreeNode]) -> Tuple[RtreeBoundingRectangle, int]:
        if not nodes:
            raise ValueError("Nodes list can't be empty.")

        min_enlargement = None
        min_enlarged_idx = None
        enlarged_mbr = None

        for idx, node in enumerate(nodes):
            candidate = node.mbr
            candidate_enlarged = candidate.union(mbr)
            diff = candidate_enlarged.area - candidate.area
            if (min_enlargement is None) or (diff < min_enlargement):
                min_enlargement = diff
                enlarged_mbr = candidate_enlarged
                min_enlarged_idx = idx

        return (enlarged_mbr, min_enlarged_idx)  # type: ignore

    def _perform_node_split(self, node: RtreeNode) -> Tuple[RtreeNode, RtreeNode]:
        first_node_info, second_node_info = (
            self.split_method.split(node.children)
        )
        node.mbr, node.children = first_node_info
        new_node = RtreeNode(
            mbr=second_node_info[0],
            children=second_node_info[1],
            level=node.level
        )
        return (node, new_node)

    def _adjust_tree(self, traversed_path: List[RtreeNode],
                     to_split: RtreeNode) -> Optional[Tuple[RtreeNode, RtreeNode]]:
        while len(traversed_path) > 0:
            parent = traversed_path.pop()
            _, new_node = self._perform_node_split(to_split)
            parent.children.append(new_node)
            if len(parent.children) < self.max_entries:
                return None
            else:
                to_split = parent
        return self._perform_node_split(to_split)

    def _insert_node(self, node: RtreeNode,
                     node_to_insert: RtreeNode) -> Optional[Tuple[RtreeNode, RtreeNode]]:
        current = node
        traversed_path = []

        while not current.level == node_to_insert.level:
            enlarged_mbr, target_node_idx = self._find_min_enlarged(
                node_to_insert.mbr,
                current.children
            )
            traversed_path.append(current)
            current = current.children[target_node_idx]
            current.mbr = enlarged_mbr

        current.add_child(node_to_insert)
        if len(current.children) >= self.max_entries:
            return self._adjust_tree(traversed_path=traversed_path,
                                     to_split=current)
        else:
            return None

    def _insert_geometry(self, node: RtreeNode,
                         geometry: RtreeGeometry) -> Optional[Tuple[RtreeNode, RtreeNode]]:
        current = node
        traversed_path = []

        while not current.is_leaf:
            enlarged_mbr, target_node_idx = self._find_min_enlarged(
                node.mbr,
                current.children
            )
            traversed_path.append(current)
            current = current.children[target_node_idx]
            current.mbr = enlarged_mbr

        current.add_child(geometry)
        if len(current.children) >= self.max_entries:
            return self._adjust_tree(traversed_path=traversed_path,
                                     to_split=current)
        else:
            return None

    def _insert(self, node: RtreeNode, obj: Union[RtreeGeometry, RtreeNode]) -> None:
        if type(obj) == RtreeGeometry:
            res = self._insert_geometry(node=node, geometry=obj)
        else:
            # mypy can't infer that else == RtreeNode
            res = self._insert_node(node=node, node_to_insert=obj)  # type: ignore

        if res is not None:
            new_node_a, new_node_b = res
            new_mbr = new_node_a.find_mbr_union(new_node_b)
            new_level = new_node_a.level + 1
            self.root = RtreeNode(
                mbr=new_mbr,
                children=[new_node_a, new_node_b],
                level=new_level
            )

    def insert(self, geometry: RtreeGeometry) -> None:
        if self.root is None:
            self.root = RtreeNode(mbr=geometry.mbr,
                                  children=[geometry], level=0)
        else:
            self._insert(self.root, geometry)
