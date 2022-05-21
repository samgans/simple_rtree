from typing import Iterable, Tuple, Union

from simple_rtree.geometry import RtreeGeometry
from simple_rtree.nodes import RtreeNode
from simple_rtree.split.base import NodeChildren, NodeInfo, RtreeSplitMethod


class DimensionStatistics:

    def __init__(self):
        # Lower left rect corner
        self.min_low = None
        self.max_low = None

        # Higher right rect corner
        self.min_high = None
        self.max_high = None

        # Idxs of the objects having the highest distance
        self.min_high_idx = None
        self.max_low_idx = None

    @property
    def width(self):
        return abs(self.min_low - self.max_high)

    @property
    def norm_distance(self):
        width = self.width
        if width == 0:
            width = 1
        return abs(self.max_low - self.min_high) / width

    @classmethod
    def compute_statistics(
        cls,
        source_coords: Iterable[Tuple[float, float]]
    ) -> "DimensionStatistics":

        """Compute statistics based on (low_coord, high_coord) tuples."""
        dim_stats = cls()
        for idx, coords in enumerate(source_coords):
            low, high = coords

            if (dim_stats.min_low is None) or (low < dim_stats.min_low):
                dim_stats.min_low = low

            if (dim_stats.max_high is None) or (high > dim_stats.max_high):
                dim_stats.max_high = high

            if (dim_stats.max_low is None) or (low < dim_stats.max_low):
                dim_stats.max_low = low
                dim_stats.max_low_idx = idx
            elif (dim_stats.min_high is None) or (high < dim_stats.min_high):
                dim_stats.min_high = high
                dim_stats.min_high_idx = idx
        return dim_stats


class RtreeLinearSplit(RtreeSplitMethod):

    @classmethod
    def _pick_seeds(cls, source: NodeChildren) -> Tuple[int, int]:
        source_mbrs = tuple(entry.mbr for entry in source)
        x_dimension = (
            (entry.bounds[0], entry.bounds[2]) for entry in source_mbrs
        )
        y_dimension = (
            (entry.bounds[1], entry.bounds[3]) for entry in source_mbrs
        )

        stat_x = DimensionStatistics.compute_statistics(x_dimension)
        stat_y = DimensionStatistics.compute_statistics(y_dimension)

        dim_for_use = (
            stat_x if stat_x.norm_distance > stat_y.norm_distance else stat_y
        )
        f1, f2 = dim_for_use.max_low_idx, dim_for_use.min_high_idx

        # seed 2 always has the bigger index
        if f1 != f2:
            return (f1, f2) if f1 < f2 else (f2, f1)
        elif f1 == 0:
            return (0, 1)
        else:
            return (0, f2)

    @classmethod
    def _distribute_children(cls, seed_1: Union[RtreeNode, RtreeGeometry],
                             seed_2: Union[RtreeNode, RtreeGeometry],
                             to_distribute: NodeChildren,
                             min_per_node: int) -> Tuple[NodeInfo, NodeInfo]:
        first_mbr = seed_1.mbr
        second_mbr = seed_2.mbr

        group_1, group_2 = [seed_1], [seed_2]
        while len(to_distribute) + 1 != min_per_node:
            entry = to_distribute.pop()
            first_mbr = first_mbr.union(entry.mbr)
            group_1.append(entry)

        while len(to_distribute) > 0:
            entry = to_distribute.pop()
            second_mbr = second_mbr.union(entry.mbr)
            group_2.append(entry)

        return ((first_mbr, group_1), (second_mbr, group_2))

    @classmethod
    def split(cls, to_split: NodeChildren,
              min_per_node: int) -> Tuple[NodeInfo, NodeInfo]:
        seed_1_idx, seed_2_idx = cls._pick_seeds(source=to_split)
        seed_2, seed_1 = to_split.pop(seed_2_idx), to_split.pop(seed_1_idx)
        return cls._distribute_children(seed_1=seed_1, seed_2=seed_2,
                                        to_distribute=to_split,
                                        min_per_node=min_per_node)
