"""Isolated drone policy: own state, immutable geography, local sensor and messages.

No environment, simulator, drone collection or shared mutable mission state is
retained. Remote bids, maps and status can only enter through receive().
"""
from __future__ import annotations
import numpy as np
from .selfheal import Heartbeats
from .allocation import cost_row, auction
from .consensus import wmsr
from .search import waypoint, route
from .safety import local_safe_velocity
from .admm import EdgeADMM, centralized


class Drone:
    """Locally replicated auction state, coverage map and heartbeat monitor."""
    def __init__(self, identity: int, position: np.ndarray, battery: float,
                 geometry, config: dict):
        self.id, self.position, self.battery = identity, position.copy(), float(battery)
        self.velocity = np.zeros(2)
        self.geometry, self.cfg = geometry, config.copy()
        self.alive = True
        self.seen = np.zeros(len(geometry.free), bool)
        self.found: dict[int, np.ndarray] = {}
        self.completed: set[str] = set()
        self.neighbors: set[int] = set()
        self.status: dict[int, tuple] = {}
        self.detector = Heartbeats(config['h_timeout'])
        self.suspicions: dict[int, tuple[int, int]] = {}
        self.task: str | None = None
        self.owners: dict[str, int] = {}
        self.path: list[np.ndarray] = []
        self.goal = None
        self.estimate = 0.
        self.count_estimate = 0.
        self.work = 0.
        self.finished = 0
        self.distance = 0.
        self.dwell = 0
        self.detections: list[tuple[int, int]] = []
        self.rounds = self.fallbacks = 0
        self.optimizer = None
        self.signature = None
        self.admm_received = {}
        self.admm_converged = False
        self.admm_updates = 0
        self.reached: set[int] = set()
        self.relay_steps = 0

    def observe(self, observation: dict) -> None:
        self.seen[observation['seen']] = True
        self.found.update(observation['found'])
        for r in range(self.cfg['regions']):
            cells = self.geometry.free & (self.geometry.region == r)
            if cells.any() and self.seen[cells].mean() >= .95:
                self.completed.add(f'r{r}')

    def receive(self, messages: list, t: int) -> None:
        estimates, counts = [], []
        for msg in messages:
            p = msg.payload
            if p.get('signature') == self.signature and self.optimizer is not None:
                if msg.sender in self.optimizer.peers and p.get('x') is not None:
                    self.admm_received[msg.sender] = p['x']
            self.detector.hear(msg.sender, msg.sent)
            self.seen[p['seen']] = True
            self.found.update(p['found'])
            self.completed |= p['completed']
            for i, status in p['status'].items():
                if i != self.id and status[0] > self.status.get(i, (-1,))[0]:
                    self.status[i] = status
            for i, record in p['suspicions'].items():
                if record > self.suspicions.get(i, (-1, -1)):
                    self.suspicions[i] = record
            estimates.append(p['estimate'])
            counts.append(p['count_estimate'])
        if estimates:
            if self.cfg['resilient']:
                self.estimate = wmsr(self.estimate, estimates, self.cfg['f_local'])
                self.count_estimate = wmsr(self.count_estimate, counts, self.cfg['f_local'])
            else:
                # Convex equal-neighbor averaging handles variable degree.
                a = min(self.cfg['alpha'], .99/(len(estimates)+1))
                self.estimate += a*sum(v-self.estimate for v in estimates)
                self.count_estimate += a*sum(v-self.count_estimate for v in counts)
        if self.cfg['self_heal']:
            for identity in self.detector.detect(t):
                self.suspicions[identity] = (t, self.id)
                self.detections.append((t, identity))
        # Dynamic estimates: weak local innovation; not average-preserving consensus.
        own_coverage = float(self.seen[self.geometry.free].mean())
        self.estimate += .15*(own_coverage-self.estimate)
        self.count_estimate += .15*(len(self.found)-self.count_estimate)

    def payload(self, t: int) -> dict:
        self.status[self.id] = (t, self.position.copy(), self.battery, self.finished,
                                len(self.neighbors), self.task)
        return dict(seen=np.flatnonzero(self.seen), found=self.found.copy(),
                    completed=self.completed.copy(), status=self.status.copy(),
                    suspicions=self.suspicions.copy(), estimate=self.estimate,
                    count_estimate=self.count_estimate)

    def broadcast(self, t: int) -> dict:
        p = self.payload(t)
        p.update(signature=self.signature, x=None if self.optimizer is None else self.optimizer.x.copy())
        return p

    def optimize_step(self, t: int) -> None:
        if self.optimizer is None:
            return
        if self.admm_received:
            p, d = self.optimizer.dual(self.admm_received)
            if set(self.admm_received) == set(self.optimizer.peers) and np.sqrt(p) < self.cfg['admm_tol'] and np.sqrt(d) < self.cfg['admm_tol']:
                self.admm_converged = True
            self.admm_received = {}
        self.optimizer.primal()
        self.admm_updates += 1
        if self.admm_updates >= self.cfg['admm_k']:
            if not self.admm_converged:
                self.fallbacks += 1
            else:
                # Deterministic integral projection of the agreed fractional matrix.
                assignment = centralized(-self.optimizer.x, self.optimizer.capacity)[0]
                _, ids, keys = self.signature
                self.owners = {key: ids[int(np.argmax(assignment[:, j]))] for j, key in enumerate(keys)}
                mine = [k for k in keys if self.owners[k] == self.id and k not in self.completed]
                if self.task not in mine:
                    self.task = next(iter(mine), None)
            self.optimizer = None

    def tasks(self) -> tuple[list[str], np.ndarray, np.ndarray]:
        keys, points, priorities = [], [], []
        for r in range(self.cfg['regions']):
            key = f'r{r}'
            if key not in self.completed:
                cells = self.geometry.free & (self.geometry.region == r)
                if cells.any():
                    keys.append(key)
                    points.append(self.geometry.centers[cells].mean(0))
                    priorities.append(self.geometry.priority[r])
        for i, point in sorted(self.found.items()):
            key = f's{i}'
            if key not in self.completed:
                keys.append(key)
                points.append(point)
                priorities.append(8.)
        return keys, np.array(points).reshape(-1, 2), np.array(priorities)

    def allocate(self, t: int) -> None:
        keys, targets, priorities = self.tasks()
        if not keys:
            self.task = None
            return
        self.payload(t)
        known = {}
        for i, state in self.status.items():
            suspected = i in self.suspicions and self.suspicions[i][0] >= state[0]
            fresh = state[0] >= t-self.cfg['status_ttl'] or not self.cfg['self_heal']
            if i == self.id or (not suspected and fresh):
                known[i] = state
        ids = sorted(known)
        capacity = np.full(len(ids), int(np.ceil(len(keys)/len(ids)))+1)
        costs = np.array([cost_row(known[i][1], known[i][2], known[i][3], known[i][4],
                                   targets, priorities, self.cfg['cost_weights']) for i in ids])
        assignment = auction(costs, capacity)
        self.rounds += 1
        if self.cfg['method'] == 'admm':
            if self.optimizer is not None and not self.admm_converged:
                self.fallbacks += 1
            peers = sorted(self.neighbors & set(ids))
            # Edge IDs use physical identities; rows use the shared sorted identity list.
            self.optimizer = EdgeADMM(ids.index(self.id), costs[ids.index(self.id)], capacity,
                                      peers, self.cfg['admm_rho'])
            self.signature = (t//self.cfg['allocation_period'], tuple(ids), tuple(keys))
            self.admm_updates, self.admm_converged = 0, False
            self.admm_received = {}
        self.owners = {key: ids[int(np.argmax(assignment[:, j]))] for j, key in enumerate(keys)}
        mine = [key for key in keys if self.owners[key] == self.id]
        # Finish a rescue rather than switching target mid-dwell.
        if self.task in mine and self.task.startswith('s'):
            return
        response = [k for k in mine if k.startswith('s')]
        if response:
            self.task = min(response, key=lambda k: np.linalg.norm(self.found[int(k[1:])]-self.position))
        elif self.task not in mine:
            regions = [k for k in mine if k.startswith('r')]
            self.task = min(regions, key=lambda k: np.linalg.norm(targets[keys.index(k)]-self.position)) if regions else None

    def move(self) -> None:
        if not self.alive:
            return
        old = self.position.copy()
        if self.task and self.task.startswith('s'):
            goal = self.found[int(self.task[1:])]
            if np.linalg.norm(goal-self.position) <= 1.5:
                self.reached.add(int(self.task[1:]))
                self.dwell += 1
                if self.dwell >= 3:
                    self.completed.add(self.task)
                    self.finished += 1
                    self.task = None
                    self.dwell = 0
                return
        else:
            self.dwell = 0
            region = int(self.task[1:]) if self.task else None
            goal = waypoint(self.geometry, self.seen, self.position, region, self.id)
            if self.task is None and self.cfg['self_heal'] and len(self.neighbors) < 2:
                lost = [i for i in self.detector.suspected if i in self.status]
                if lost:
                    # A spare agent heads toward the last locally heard peer to
                    # bridge a gap. No component labels or global graph are read.
                    candidate = (self.position+self.status[min(lost)][1])/2
                    if self.geometry.valid(candidate):
                        goal = candidate
                        self.relay_steps += 1
        if self.goal is None or np.linalg.norm(goal-self.goal) > 1:
            self.goal = goal.copy()
            self.path = []
        delta = goal-self.position
        speed = self.cfg['v_max']
        desired = delta*min(1., speed/max(np.linalg.norm(delta), 1e-9))
        # Sample the segment so motion cannot tunnel through obstacles.
        def legal(step):
            return all(self.geometry.valid(self.position+f*step) for f in np.linspace(0, 1, 6))
        if not legal(desired):
            if not self.path:
                self.path = route(self.geometry, self.position, goal)
            while self.path and np.linalg.norm(self.path[0]-self.position) < .3:
                self.path.pop(0)
            if self.path:
                delta = self.path[0]-self.position
                desired = delta*min(1., speed/max(np.linalg.norm(delta), 1e-9))
        nearby = [state[1] for i, state in self.status.items() if i in self.neighbors]
        velocity = local_safe_velocity(self.position, desired, nearby, self.cfg['d_min'], speed)
        if legal(velocity):
            self.position += velocity
        elif legal(desired):
            self.position += desired
        self.velocity = self.position-old
        step_distance = float(np.linalg.norm(self.velocity))
        self.distance += step_distance
        self.work += step_distance

    def drain(self, messages: int) -> None:
        if self.alive:
            self.battery = max(0., self.battery-self.cfg['c_move']*np.linalg.norm(self.velocity)
                               -self.cfg['c_comm']*messages-self.cfg['c_sense'])
