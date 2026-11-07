"""Metropolis consensus, W-MSR filtering and numerical robustness checks."""
from __future__ import annotations
from itertools import product
import numpy as np
import networkx as nx


def metropolis(g: nx.Graph) -> np.ndarray:
    nodes = sorted(g)
    w = np.zeros((len(nodes), len(nodes)))
    index = {v: k for k, v in enumerate(nodes)}
    for u, v in g.edges:
        a, b = index[u], index[v]
        w[a, b] = w[b, a] = 1/(1+max(g.degree(u), g.degree(v)))
    np.fill_diagonal(w, 1-w.sum(1))
    return w


def spectral_rate(g: nx.Graph) -> float:
    vals = np.linalg.eigvalsh(metropolis(g))
    return float(sorted(abs(vals))[-2])


def wmsr(own: float, received: list[float], f: int) -> float:
    lower = sorted(x for x in received if x < own)[f:]
    upper = sorted((x for x in received if x > own), reverse=True)[f:]
    equal = [x for x in received if x == own]
    return float(np.mean([own]+lower+upper+equal))


def robust_rs(g: nx.Graph, r: int, s: int) -> bool:
    """Exact (r,s)-robustness enumeration; exponential, restricted to small graphs."""
    if len(g) > 11:
        raise ValueError('Exact robustness check supports at most 11 vertices')
    nodes = sorted(g)
    for labels in product(range(3), repeat=len(nodes)):
        a = {nodes[i] for i, x in enumerate(labels) if x == 1}
        b = {nodes[i] for i, x in enumerate(labels) if x == 2}
        if not a or not b:
            continue
        ar = sum(len(set(g[v])-a) >= r for v in a)
        br = sum(len(set(g[v])-b) >= r for v in b)
        if ar != len(a) and br != len(b) and ar+br < s:
            return False
    return True


def faulty_trial(seed: int, method: str, steps: int = 100, n: int = 7,
                 f: int = 1, attack: str = 'bias') -> dict:
    """Complete graph is checked exactly; F Byzantine nodes satisfy F-local bound."""
    g = nx.complete_graph(n)
    if not robust_rs(g, f+1, f+1):
        raise ValueError('Graph lacks the requested robustness')
    rng = np.random.default_rng(seed)
    x = rng.uniform(.2, .8, n)
    reference = float(x[f:].mean())
    history = [x.copy()]
    for _ in range(steps):
        nxt = x.copy()
        for i in range(f, n):
            values = [(10.0 if attack == 'bias' else float(rng.uniform(-20, 20)))
                      if j < f else x[j] for j in g[i]]
            nxt[i] = wmsr(x[i], values, f) if method == 'wmsr' else float(np.mean([x[i]]+values))
        x = nxt
        history.append(x.copy())
    h = np.array(history)
    return {'history': h, 'error': float(np.max(abs(x[f:]-reference))),
            'spread': float(np.ptp(x[f:])), 'reference': reference,
            'initial_min': float(h[0, f:].min()), 'initial_max': float(h[0, f:].max())}
