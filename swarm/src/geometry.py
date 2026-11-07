from __future__ import annotations
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class Geometry:
    """Immutable public geography, supplied before flight (no live world state)."""
    size: float
    cell: float
    centers: np.ndarray
    free: np.ndarray
    region: np.ndarray
    priority: np.ndarray
    obstacles: tuple

    def valid(self, p: np.ndarray) -> bool:
        if np.any(p < 0) or np.any(p >= self.size):
            return False
        return not any(x <= p[0] <= x+w and y <= p[1] <= y+h
                       for x, y, w, h in self.obstacles)


