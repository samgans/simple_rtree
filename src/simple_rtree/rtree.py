from typing import List, Optional, Tuple, Union

from simple_rtree.geometry import RtreeBoundingRectangle, RtreeGeometry
from simple_rtree.nodes import RtreeNode


TreeObject = Union[RtreeNode, RtreeGeometry]


class RtreeException(Exception):
    pass


class Rtree:

    def __init__(self, max_entries: int, min_entries: int,
                 split_method, root: Optional[RtreeNode] = None):
        self.root = root
        self.max_entries = max_entries
        self.min_entries = min_entries
        self.split_method = split_method

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

    def _find_min_enlarged(self, mbr: RtreeBoundingRectangle,
                           nodes: List[RtreeNode]) -> Tuple[RtreeBoundingRectangle, int]:
        if not nodes:
            raise ValueError("Nodes list can't be empty.")

        min_enlargement = None
        min_enlarged_idx = None
        enlarged_mbr = None

        for idx, node in enumerate(nodes):
            candidate = node.mbr
            if candidate.covers(mbr):
                return (candidate, idx)
            else:
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

        while not current.level == (node_to_insert.level + 1):
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
                geometry.mbr,
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

    def _insert_at_root(self, obj: Union[RtreeGeometry, RtreeNode]) -> None:
        if self.root is None:
            if type(obj) == RtreeNode:
                self.root = obj
            else:
                self.root = RtreeNode(mbr=obj.mbr, children=[obj], level=0)
        else:
            if type(obj) == RtreeGeometry:
                res = self._insert_geometry(self.root, obj)
            else:
                if obj.level > self.root.level:
                    prev_root = self.root
                    self.root = obj
                    res = self._insert_node(self.root, prev_root)
                elif obj.level == self.root.level:
                    res = (self.root, obj)
                else:
                    res = self._insert_node(self.root, obj)

            if res is not None:  # Grow the tree upwards
                new_node_a, new_node_b = res
                new_mbr = new_node_a.find_mbr_union(new_node_b)
                new_level = new_node_a.level + 1
                self.root = RtreeNode(
                    mbr=new_mbr,
                    children=[new_node_a, new_node_b],
                    level=new_level
                )

    def _range_delete(
        self,
        node: RtreeNode,
        rm_range: RtreeGeometry
    ) -> Tuple[List[RtreeGeometry], List[TreeObject]]:

        to_drop = []
        dropped = []

        if node.is_leaf:
            for idx, geom in enumerate(node.children):
                if rm_range.covers(geom):
                    to_drop.append(idx)
            for idx in to_drop[::-1]:
                dropped.append(node.drop_child(pos=idx))
            return (dropped, [])  # Empty as we don't condense tree there
        else:
            to_reinsert = []

            for idx, child in enumerate(node.children):
                if rm_range.covers(child.mbr):
                    to_drop.append(idx)
                    dropped.extend(
                        self._range_search(
                            node=child,
                            search_range=child.mbr,
                            return_all=True
                        )
                    )
                elif rm_range.intersects(child.mbr):
                    new_dropped, new_to_reinsert = self._range_delete(
                        node=child,
                        rm_range=rm_range
                    )
                    # If node is under minimum capacity, we will drop it
                    if len(child.children) < self.min_entries:
                        to_reinsert.extend(child.children)
                        to_drop.append(idx)

                    dropped.extend(new_dropped)
                    to_reinsert.extend(new_to_reinsert)

            for idx in to_drop[::-1]:
                node.children.pop(idx)

            return (dropped, to_reinsert)

    def _range_search(self, node: RtreeNode,
                      search_range: RtreeGeometry,
                      return_all: bool = False) -> List[RtreeGeometry]:
        if node.is_leaf:
            if return_all:
                return node.children
            else:
                to_return = []
                for child in node.children:
                    if search_range.covers(child):
                        to_return.append(child)
                return to_return
        else:
            to_return = []
            for child in node.children:
                if return_all:
                    to_return.extend(
                        self._range_search(
                            node=child,
                            search_range=search_range,
                            return_all=return_all
                        )
                    )
                else:
                    if search_range.covers(child.mbr):
                        to_return.extend(
                            self._range_search(
                                node=child,
                                search_range=search_range,
                                return_all=True
                            )
                        )
                    elif search_range.intersects(child.mbr):
                        to_return.extend(
                            self._range_search(node=child,
                                               search_range=search_range)
                        )
            return to_return

    @property
    def height(self):
        if self.root is not None:
            return self.root.level
        else:
            return 0

    def insert(self, geometry: RtreeGeometry) -> None:
        self._insert_at_root(obj=geometry)

    def range_delete(self, rm_range: RtreeGeometry) -> List[RtreeGeometry]:
        deleted = []
        if self.root:
            if rm_range.covers(self.root.mbr):
                deleted = self.range_search(search_range=rm_range)
                self.root = None
            elif rm_range.intersects(self.root.mbr):
                to_delete = []
                to_reinsert = []
                deleted, new_to_reinsert = self._range_delete(
                    node=self.root,
                    rm_range=rm_range
                )
                for idx, child in enumerate(self.root.children):
                    if len(child.children) < self.min_entries:
                        to_delete.append(idx)

                for idx in to_delete[::-1]:
                    deleted = self.root.children.pop(idx)
                    to_reinsert.extend(deleted.children)
                to_reinsert.extend(new_to_reinsert)

                if len(self.root.children) == 1 and not self.root.is_leaf:
                    self.root = self.root.children[0]
                if len(self.root.children) == 0:
                    self.root = None

                for entry in to_reinsert:
                    self._insert_at_root(obj=entry)

        return deleted

    def range_search(self, search_range: RtreeGeometry) -> List[RtreeGeometry]:
        to_return = []
        if self.root:
            if search_range.covers(self.root.mbr):
                to_return = self._range_search(
                    node=self.root,
                    search_range=search_range,
                    return_all=True
                )
            elif search_range.intersects(self.root.mbr):
                to_return = self._range_search(
                    node=self.root,
                    search_range=search_range
                )
        return to_return

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
