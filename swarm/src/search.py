"""Local coverage planning on a public static map, with no hidden mission data."""
from __future__ import annotations
from heapq import heappop, heappush
import numpy as np
from .geometry import Geometry


def waypoint(geometry: Geometry, seen: np.ndarray, position: np.ndarray,
             region: int | None, identity: int) -> np.ndarray:
    candidates = geometry.free & ~seen
    if region is not None:
        restricted = candidates & (geometry.region == region)
        if restricted.any():
            candidates = restricted
    indexes = np.flatnonzero(candidates)
    if not len(indexes):
        return position.copy()
    distance = np.linalg.norm(geometry.centers[indexes]-position, axis=1)
    # Small deterministic identity tie break avoids identical paths from ties.
    score = distance + .02*((indexes*(identity+1)) % 17)
    return geometry.centers[indexes[np.argmin(score)]].copy()


def route(geometry: Geometry, start: np.ndarray, goal: np.ndarray) -> list[np.ndarray]:
    """A* fallback prevents the local obstacle potential getting stuck at corners."""
    side = int(round(geometry.size/geometry.cell))
    def index(p):
        xy = np.clip((p/geometry.cell).astype(int), 0, side-1)
        return int(xy[1]*side+xy[0])
    a, b = index(start), index(goal)
    if not geometry.free[b]:
        return []
    heap = [(0., a)]
    dist, parent = {a: 0.}, {}
    while heap:
        _, u = heappop(heap)
        if u == b:
            path = []
            while u != a:
                path.append(geometry.centers[u].copy())
                u = parent[u]
            return path[::-1]
        x, y = u % side, u//side
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            xx, yy = x+dx, y+dy
            if not (0 <= xx < side and 0 <= yy < side):
                continue
            v = yy*side+xx
            if not geometry.free[v] or not geometry.valid(geometry.centers[v]):
                continue
            nd = dist[u]+geometry.cell
            if nd < dist.get(v, float('inf')):
                dist[v], parent[v] = nd, u
                heappush(heap, (nd+np.linalg.norm(geometry.centers[v]-goal), v))
    return []
