"""Assignment costs, deterministic auction rounding, and labeled global baseline."""
from __future__ import annotations
from typing import Protocol
import numpy as np
from .admm import centralized


class Allocator(Protocol):
    def assign(self, cost: np.ndarray, capacity: np.ndarray) -> np.ndarray: ...


def cost_row(position: np.ndarray, battery: float, load: int, degree: int,
             targets: np.ndarray, priorities: np.ndarray, weights: list[float]) -> np.ndarray:
    distance = np.linalg.norm(targets-position, axis=1)
    w1, w2, w3, w4, w5 = weights
    return w1*distance+w2*distance/max(battery, 1)+w3*load+w4/(degree+1)-w5*priorities


def auction(cost: np.ndarray, capacity: np.ndarray) -> np.ndarray:
    """Deterministic capacitated greedy auction on locally known bids."""
    n, m = cost.shape
    answer = np.zeros((n, m))
    left = capacity.copy()
    # Strongest best-vs-second-best preference first, deterministic ties.
    sorted_cost = np.sort(cost, axis=0)
    margin = sorted_cost[1]-sorted_cost[0] if n > 1 else np.ones(m)
    order = sorted(range(m), key=lambda j: (-margin[j], j))
    for j in order:
        eligible = [i for i in range(n) if left[i] > 0]
        if not eligible:
            break
        winner = min(eligible, key=lambda i: (cost[i, j], i))
        answer[winner, j] = 1
        left[winner] -= 1
    return answer


class CentralizedAllocator:
    """Global allocation-cost lower bound; only baseline sees every cost row."""
    def assign(self, cost: np.ndarray, capacity: np.ndarray) -> np.ndarray:
        return centralized(cost, capacity)[0]
