"""Lossy delayed neighbor-only transport, with explicit attempt accounting."""
from __future__ import annotations
from dataclasses import dataclass
from collections.abc import Mapping
from types import MappingProxyType
import numpy as np
import networkx as nx


def range_graph(positions: np.ndarray, alive: np.ndarray, radius: float,
                p_link: float, rng: np.random.Generator) -> nx.Graph:
    g = nx.Graph()
    g.add_nodes_from(np.flatnonzero(alive).tolist())
    for i in g:
        for j in g:
            if j > i and np.linalg.norm(positions[i]-positions[j]) <= radius and rng.random() >= p_link:
                g.add_edge(i, j)
    return g


def fiedler(g: nx.Graph) -> float:
    if len(g) < 2 or not nx.is_connected(g):
        return 0.0
    return float(np.linalg.eigvalsh(nx.laplacian_matrix(g).toarray())[1])


@dataclass(frozen=True)
class Message:
    sender: int
    recipient: int
    sent: int
    due: int
    payload: Mapping


def freeze(value):
    """Make one immutable snapshot per broadcast, safely shared by recipients.

    This preserves the per-recipient deep-copy semantics without copying a full
    map/vote matrix once for every edge. Policies cannot mutate cached messages.
    """
    if isinstance(value, np.ndarray):
        result = value.copy()
        result.setflags(write=False)
        return result
    if isinstance(value, dict):
        return MappingProxyType({key: freeze(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(value)
    return value


class MessageBus:
    """Only current edges can send or deliver; in-flight broken-link packets drop."""
    def __init__(self, seed: int, drop: float = .05, delay: int = 2):
        self.rng = np.random.default_rng(seed)
        self.drop, self.delay = drop, delay
        self.pending: list[Message] = []
        self.attempts = self.delivered = self.dropped = 0
        self.per_sender: dict[int, int] = {}

    def send(self, sender: int, payload: dict, t: int, graph: nx.Graph) -> None:
        if sender not in graph:
            return
        snapshot = freeze(payload)
        # A broadcast is one attempted directed transmission per neighbor.
        for receiver in sorted(graph[sender]):
            self.attempts += 1
            self.per_sender[sender] = self.per_sender.get(sender, 0)+1
            if self.rng.random() < self.drop:
                self.dropped += 1
            else:
                self.pending.append(Message(sender, receiver, t,
                                            t+int(self.rng.integers(self.delay+1)), snapshot))

    def receive(self, t: int, graph: nx.Graph) -> dict[int, list[Message]]:
        boxes = {i: [] for i in graph}
        future = []
        for msg in self.pending:
            if msg.due > t:
                future.append(msg)
            elif graph.has_edge(msg.sender, msg.recipient):
                boxes[msg.recipient].append(msg)
                self.delivered += 1
            else:
                self.dropped += 1
        self.pending = future
        return boxes
