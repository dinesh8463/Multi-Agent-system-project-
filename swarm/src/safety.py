"""Local motion filter and observer-only temporal-logic monitors."""
from __future__ import annotations
import numpy as np


def local_safe_velocity(position: np.ndarray, desired: np.ndarray,
                        neighbors: list[np.ndarray], d_min: float, vmax: float,
                        ages: list[int] | None = None) -> np.ndarray:
    """Projected robust barrier halfspaces with packet-age uncertainty margin.

    The next position lies outside the peer's reachable ball of radius
    d_min + vmax*(age+1). A supporting halfspace is conservative and convex.
    A strict 0.05 clearance protects the open STL predicate.
    Arbitrarily long outages still preclude an absolute safety guarantee.
    """
    norm = np.linalg.norm(desired)
    velocity = desired*min(1., vmax/max(norm, 1e-12))
    ages = ages if ages is not None else [0]*len(neighbors)
    constraints = []
    for other, age in zip(neighbors, ages):
        delta = position-other
        d = np.linalg.norm(delta)
        if 1e-8 < d <= d_min+.05+2*vmax+age*vmax:
            constraints.append((delta/d, d_min+.05+(age+1)*vmax-d))
    for _ in range(20):
        previous = velocity.copy()
        for normal, bound in constraints:
            velocity += max(0., bound-float(velocity@normal))*normal
        norm = np.linalg.norm(velocity)
        velocity *= min(1., vmax/max(norm, 1e-12))
        if np.linalg.norm(velocity-previous) < 1e-8:
            break
    if any(float(velocity@normal) < bound-1e-5 for normal, bound in constraints):
        return np.zeros(2)  # infeasible stale-observation envelope: hold position
    return velocity


def separation_robustness(positions: np.ndarray, d_min: float) -> float:
    if len(positions) < 2:
        return float('inf')
    distances = np.linalg.norm(positions[:, None]-positions[None, :], axis=2)
    np.fill_diagonal(distances, np.inf)
    return float(distances.min()-d_min)


def response_robustness(distances: list[float], radius: float = 1.5) -> float:
    """Robustness of eventually reach within the supplied finite time window."""
    return radius-min(distances) if distances else -float('inf')
