"""Edge-consensus ADMM for capacitated fractional task allocation.

Each vertex's objective contains only its own cost row. Every local copy lies
in the transportation polytope. Each edge has two scaled duals and one mean z.
The local proximal problem is a Euclidean projection after a linear shift.
"""
from __future__ import annotations
import numpy as np
import networkx as nx
from scipy.optimize import linprog


def centralized(cost: np.ndarray, capacity: np.ndarray) -> tuple[np.ndarray, float]:
    """Independent HiGHS LP optimum; integral by total unimodularity."""
    n, m = cost.shape
    if capacity.sum() < m:
        raise ValueError('Insufficient capacity')
    eq = np.zeros((m, n*m))
    ub = np.zeros((n, n*m))
    for i in range(n):
        ub[i, i*m:(i+1)*m] = 1
        eq[:, i*m:(i+1)*m] = np.eye(m)
    result = linprog(cost.ravel(), A_ub=ub, b_ub=capacity, A_eq=eq,
                     b_eq=np.ones(m), bounds=(0, 1), method='highs')
    if not result.success:
        raise RuntimeError(result.message)
    return result.x.reshape(n, m), float(result.fun)


def simplex(vector: np.ndarray, total: float = 1.) -> np.ndarray:
    u = np.sort(vector)[::-1]
    cssv = np.cumsum(u)-total
    rho = np.flatnonzero(u-cssv/np.arange(1, len(u)+1) > 0)[-1]
    return np.maximum(vector-cssv[rho]/(rho+1), 0)


def project(matrix: np.ndarray, capacity: np.ndarray, tol: float = 1e-8) -> np.ndarray:
    """Dykstra projection onto column simplices and nonnegative row capacity sets."""
    x = matrix.copy()
    p, q = np.zeros_like(x), np.zeros_like(x)
    for _ in range(400):
        v = x+p
        y = np.column_stack([simplex(v[:, j]) for j in range(x.shape[1])])
        p = v-y
        v = y+q
        nxt = np.maximum(v, 0)
        for i, cap in enumerate(capacity):
            if nxt[i].sum() > cap:
                nxt[i] = simplex(v[i], cap)
        q = v-nxt
        delta = np.max(abs(nxt-x))
        x = nxt
        if delta < tol and np.max(abs(x.sum(0)-1)) < 10*tol:
            return x
    return x


class EdgeADMM:
    """One agent's local optimizer; incoming values must be neighbor messages."""
    def __init__(self, row: int, cost: np.ndarray, capacity: np.ndarray,
                 peers: list[int], rho: float = 1.):
        self.row, self.cost, self.capacity = row, cost.copy(), capacity.copy()
        self.peers, self.rho = peers, rho
        n, m = len(capacity), len(cost)
        self.x = np.full((n, m), 1/n)
        self.z = {j: self.x.copy() for j in peers}
        self.u = {j: np.zeros((n, m)) for j in peers}

    def primal(self) -> np.ndarray:
        if not self.peers:
            c = np.zeros_like(self.x)
            c[self.row] = self.cost
            self.x = centralized(c, self.capacity)[0]
            return self.x.copy()
        v = sum(self.z[j]-self.u[j] for j in self.peers)/len(self.peers)
        v[self.row] -= self.cost/(self.rho*len(self.peers))
        self.x = project(v, self.capacity)
        return self.x.copy()

    def dual(self, received: dict[int, np.ndarray]) -> tuple[float, float]:
        primal, dual = 0., 0.
        for j, other in received.items():
            z = (self.x+other)/2
            primal += float(np.sum((self.x-z)**2))
            dual += float(np.sum((z-self.z[j])**2))*self.rho**2
            self.u[j] += self.x-z
            self.z[j] = z
        return primal, dual


def solve(cost: np.ndarray, capacity: np.ndarray, graph: nx.Graph,
          iterations: int = 1500, tol: float = 1e-4, rho: float = 1.) -> dict:
    """Synchronous neighbor-message reference driver, not a global x update."""
    if not nx.is_connected(graph):
        raise ValueError('Solve per connected component')
    agents = [EdgeADMM(i, row, capacity, sorted(graph[i]), rho) for i, row in enumerate(cost)]
    history = []
    for k in range(iterations):
        messages = [a.primal() for a in agents]
        residuals = [a.dual({j: messages[j] for j in graph[i]}) for i, a in enumerate(agents)]
        p, d = np.sqrt(np.sum(residuals, axis=0))
        mean = np.mean(messages, axis=0)
        history.append((p, d, float(np.sum(cost*mean))))
        if p < tol and d < tol:
            break
    return {'x': mean, 'history': np.array(history), 'converged': bool(p < tol and d < tol),
            'iterations': k+1, 'objective': float(np.sum(cost*mean))}
