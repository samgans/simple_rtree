import abc
from typing import List, Tuple, Union

from simple_rtree.geometry import RtreeBoundingRectangle, RtreeGeometry
from simple_rtree.nodes import RtreeNode


NodeInfo = Tuple[RtreeBoundingRectangle, List[RtreeNode]]
NodeChildren = Union[List[RtreeNode], List[RtreeGeometry]]


class RtreeSplitMethod(abc.ABC):

    @classmethod
    @abc.abstractmethod
    def split(cls, nodes: List[RtreeNode]) -> Tuple[NodeInfo, NodeInfo]:
        raise NotImplementedError
