"""Pure local failure detector and seeded injection schedule."""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np


def failure_schedule(seed: int, n: int, fraction: float, horizon: int) -> dict[int, int]:
    rng = np.random.default_rng(seed+91417)
    ids = rng.choice(n, int(round(n*fraction)), replace=False)
    return {int(i): int(rng.integers(10, max(11, int(.6*horizon)))) for i in ids}


@dataclass
class Heartbeats:
    timeout: int = 5
    last: dict[int, int] = field(default_factory=dict)
    suspected: set[int] = field(default_factory=set)

    def hear(self, sender: int, sent: int) -> None:
        self.last[sender] = max(self.last.get(sender, -1), sent)
        self.suspected.discard(sender)

    def detect(self, t: int) -> set[int]:
        new = {i for i, last in self.last.items() if t-last >= self.timeout}-self.suspected
        self.suspected |= new
        return new
