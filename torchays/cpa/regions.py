from collections import deque
from math import floor
from typing import Deque, Iterable, List, Tuple

import torch

from .handler import BaseHandler


class RegionSet:
    def __init__(self) -> None:
        self._regions: Deque[Tuple[torch.Tensor, torch.Tensor, torch.Tensor, int]] = deque()

    def __iter__(self):
        return self

    def __next__(self):
        try:
            return self._regions.popleft()
        except:
            raise StopIteration

    def __len__(self) -> int:
        return len(self._regions)

    def register(
        self,
        functions: torch.Tensor,
        region: torch.Tensor,
        inner_point: torch.Tensor,
        depth: int,
    ):
        self._regions.append((functions, region, inner_point, depth))

    def extend(self, regions: Iterable[Tuple[torch.Tensor, torch.Tensor, torch.Tensor, int]]):
        self._regions.extend(regions)

    def __str__(self):
        return self._regions.__str__()


class WapperRegion:
    """
    Get the region of the function list.
    *  1 : f(x) > 0
    * -1 : f(x) <= 0
    """

    # The maximum capacity of a tensor.
    # If this value is reached, the calculation speed will slow down.
    _upper = 32767

    def __init__(self, region: torch.Tensor):
        self.filters: Deque[torch.Tensor] = deque()
        self.filters.appendleft(torch.Tensor().type(torch.int8))
        self.regions: Deque[torch.Tensor] = deque()
        self._up_size = floor(self._upper / region.size(0))
        self.register(region)

    def __iter__(self):
        return self

    def __next__(self) -> torch.Tensor:
        try:
            region = self.regions.popleft()
            while self._check(region):
                region = self.regions.popleft()
            return region
        except:
            raise StopIteration

    def _update_list(self):
        self.output: torch.Tensor = self.regions.popleft()

    def _check(self, region: torch.Tensor):
        """Check if the region has been used."""
        try:
            including = False
            for filter in self.filters:
                res = ((filter.abs() * region) - filter).abs().sum(dim=1)
                if 0 in res:
                    including = True
                    break
            return including
        except:
            return False

    def update_filter(self, region: torch.Tensor):
        if self._check(region):
            return
        if self.filters[0].size(0) == self._up_size:
            self.filters.appendleft(torch.Tensor().type(torch.int8))
        self.filters[0] = torch.cat([self.filters[0], region.unsqueeze(0)], dim=0)

    def register(self, region: torch.Tensor):
        if not self._check(region):
            self.regions.append(region)

    def extend(self, regions: List[torch.Tensor]):
        for region in regions:
            self.register(region)


class CPACache(object):
    def __init__(self):
        self.cpas: Deque[Tuple[torch.Tensor, torch.Tensor, torch.Tensor]] = deque()
        self.hyperplanes: Deque[Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, int, int]] = deque()

    def cpa(self, funcs: torch.Tensor, region: torch.Tensor, inner_point: torch.Tensor):
        self.cpas.append((funcs, region, inner_point))

    def hyperplane(
        self,
        p_funcs: torch.Tensor,
        p_region: torch.Tensor,
        c_funcs: torch.Tensor,
        intersection_funcs: torch.Tensor,
        n_regions: int,
        depth: int,
    ):
        self.hyperplanes.append((p_funcs, p_region, c_funcs, intersection_funcs, n_regions, depth))

    def handler(self, handler: BaseHandler):
        for funcs, region, inner_point in self.cpas:
            handler.region(funcs, region, inner_point)
        self.cpas.clear()
        for args in self.hyperplanes:
            handler.inner_hyperplanes(*args)
        self.hyperplanes.clear()

    def extend(self, cache):
        self.cpas.extend(cache.cpas)
        self.hyperplanes.extend(cache.hyperplanes)