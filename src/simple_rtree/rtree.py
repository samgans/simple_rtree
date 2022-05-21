from typing import List, Optional, Tuple, Union

from simple_rtree.geometry import RtreeBoundingRectangle, RtreeGeometry
from simple_rtree.nodes import RtreeNode


class Rtree:

    def __init__(self, max_entries: int, min_entries: int,
                 split_method, root: Optional[RtreeNode] = None):
        self.root = root
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
            self.split_method.split(node.children, min_per_node=self.min_entries)
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

        current.mbr = current.mbr.union(node_to_insert.mbr)

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

        current.mbr = current.mbr.union(geometry.mbr)

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
        return res

    def _stringify_tree(self, tree_obj: Union[RtreeGeometry, RtreeNode],
                        prefix: str, separator: str) -> str:
        base_str = f"{prefix}{separator}{tree_obj}\n"

        if type(tree_obj) == RtreeNode:
            if tree_obj.level == 0:
                separator = "└── "
            else:
                separator = "├── "

            for child in tree_obj.children:
                base_str += self._stringify_tree(
                    tree_obj=child,
                    prefix=f"{prefix}│   ",
                    separator=separator
                )
        return base_str

    def insert(self, geometry: RtreeGeometry) -> None:
        if self.root is None:
            self.root = RtreeNode(mbr=geometry.mbr,
                                  children=[geometry], level=0)
        else:
            res = self._insert(self.root, geometry)

            if res is not None:  # Create new root
                new_node_a, new_node_b = res
                new_mbr = new_node_a.find_mbr_union(new_node_b)
                new_level = new_node_a.level + 1
                self.root = RtreeNode(
                    mbr=new_mbr,
                    children=[new_node_a, new_node_b],
                    level=new_level
                )

    def print_tree(self) -> None:
        if self.root is not None:
            print(
                self._stringify_tree(
                    tree_obj=self.root,
                    prefix="",
                    separator=""
                )
            )
        else:
            print()
