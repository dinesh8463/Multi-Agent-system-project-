"""Physical environment, accessible to the simulator and centralized baseline only."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from scipy.ndimage import label


from .geometry import Geometry


class Environment:
    """Seeded geometry and hidden survivor ground truth."""
    def __init__(self, seed: int, n: int, cfg: dict):
        rng = np.random.default_rng(seed)
        size, cell = cfg['size'], cfg['cell']
        xy = np.arange(cell/2, size, cell)
        centers = np.array(np.meshgrid(xy, xy)).reshape(2, -1).T
        # Separated interior rectangles leave boundary corridors connected.
        obstacles = []
        for x, y in [(20, 20), (60, 20), (20, 60), (60, 60)]:
            w, h = rng.uniform(13.5, 16.5, 2)
            obstacles.append((x+rng.uniform(-2, 2), y+rng.uniform(-2, 2), w, h))
        free = np.ones(len(centers), bool)
        for x, y, w, h in obstacles:
            free &= ~((centers[:, 0] >= x) & (centers[:, 0] <= x+w) &
                      (centers[:, 1] >= y) & (centers[:, 1] <= y+h))
        assert label(free.reshape(len(xy), len(xy)))[1] == 1
        blocks = int(np.sqrt(cfg['regions']))
        region = (centers[:, 0] * blocks/size).astype(int) + blocks*(centers[:, 1]*blocks/size).astype(int)
        hotspot = rng.uniform(0, size, 2)
        rc = np.array([centers[region == r].mean(0) for r in range(blocks**2)])
        priority = 1 + 2*np.exp(-np.linalg.norm(rc-hotspot, axis=1)/30)
        for arr in (centers, free, region, priority):
            arr.setflags(write=False)
        self.geometry = Geometry(size, cell, centers, free, region, priority, tuple(obstacles))
        cells = centers[free]
        # Independent streams ensure N changes do not change survivor positions.
        self.survivors = cells[rng.choice(len(cells), cfg['survivors'], replace=False)].copy()
        spawn_rng = np.random.default_rng(seed + 81291)
        chosen = []
        while len(chosen) < n:
            p = cells[spawn_rng.integers(len(cells))]
            if all(np.linalg.norm(p-q) > cfg['d_min']+0.5 for q in chosen):
                chosen.append(p.copy())
        self.positions = np.array(chosen)
        self.batteries = spawn_rng.uniform(60, 100, n)

    def sense(self, p: np.ndarray, rng: np.random.Generator, radius: float) -> dict:
        """A local sensor observation, with no identities of nonlocal drones."""
        seen = np.flatnonzero(self.geometry.free & (np.linalg.norm(self.geometry.centers-p, axis=1) <= radius))
        found = {int(i): q.copy() for i, q in enumerate(self.survivors)
                 if np.linalg.norm(q-p) <= radius and rng.random() < 0.9}
        return {'seen': seen, 'found': found}
