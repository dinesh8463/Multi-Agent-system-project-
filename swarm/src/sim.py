"""Observer-driven physical simulation; observer metrics never feed distributed policies."""
from __future__ import annotations
from time import perf_counter
import numpy as np
import networkx as nx
from scipy.spatial.distance import pdist
from .env import Environment
from .drone import Drone
from .comms import MessageBus, range_graph, fiedler
from .selfheal import failure_schedule
from .safety import separation_robustness, response_robustness
from .metrics import jain, recovery_ready
from .allocation import CentralizedAllocator, cost_row


def simulate(cfg: dict, seed: int, capture: bool = False) -> dict:
    """Execute one complete seeded episode and return real metrics plus optional trace."""
    started = perf_counter()
    n, horizon = cfg['n'], cfg['steps']
    env = Environment(seed, n, cfg)
    geom = env.geometry
    drones = [Drone(i, env.positions[i], env.batteries[i], geom, cfg) for i in range(n)]
    bus = MessageBus(seed+171, cfg['drop'], cfg['delay'])
    link_rng = np.random.default_rng(seed+371)
    fault_rng = np.random.default_rng(seed+1371)
    sensing = [np.random.default_rng(seed+17171+i) for i in range(n)]
    schedule = failure_schedule(seed, n, cfg['failure_fraction'], horizon)
    coverage = np.zeros(len(geom.free), bool)
    detected, rescued = {}, set()
    response_distances = {}
    failures, snapshots, trajectory = [], [], []
    history = []
    fp = tp = fn = safety_violations = conflicts = 0
    minimum_separation = float('inf')
    total_fallbacks = 0
    completion = horizon
    success = False
    for t in range(horizon):
        previous_battery = np.array([d.battery for d in drones])
        previous_positions = np.array([d.position.copy() for d in drones])
        previously_dead = [not d.alive for d in drones]
        for d in drones:
            if d.alive and (schedule.get(d.id) == t or d.battery <= 0):
                tasks = sorted(k for k, owner in d.owners.items() if owner == d.id and k not in d.completed)
                failures.append(dict(drone=d.id, time=t, tasks=tasks, detection=None,
                                     recovered=t if not tasks else None))
                d.alive, d.task = False, None
                d.velocity[:] = 0
        alive = np.array([d.alive for d in drones])
        positions = np.array([d.position for d in drones])
        graph = range_graph(positions, alive, cfg['comm_range'], cfg['p_link'], link_rng)
        for d in drones:
            if d.alive:
                d.neighbors = set(graph[d.id])
                observation = env.sense(d.position, sensing[d.id], cfg['sense_radius'])
                observation['proximity'] = env.proximity(d.id, d.position, positions, alive,
                    max(cfg['sense_radius'], cfg['d_min']+2*cfg['v_max']+.05))
                d.observe(observation)
                coverage[observation['seen']] = True
                for survivor in observation['found']:
                    detected.setdefault(survivor, t)
        before = bus.per_sender.copy()
        for d in drones:
            if d.alive:
                payload = d.broadcast(t)
                if d.id < cfg.get('fault_count', 0):
                    # Byzantine equivocation would require per-recipient values;
                    # this mission intervention is a broadcast bias/random fault.
                    payload['estimate'] = 10. if cfg.get('attack') == 'bias' else float(fault_rng.uniform(-20, 20))
                    payload['count_estimate'] = 100.*payload['estimate']
                bus.send(d.id, payload, t, graph)
        boxes = bus.receive(t, graph)
        for d in drones:
            if not d.alive:
                continue
            d.receive(boxes[d.id], t)
            for when, suspected in d.detections:
                if when == t:
                    if drones[suspected].alive:
                        fp += 1
                    else:
                        tp += 1
                        for failure in failures:
                            if failure['drone'] == suspected and failure['detection'] is None:
                                failure['detection'] = t
            event = bool(set(d.tasks()[0])-d.known_allocation_tasks)
            if t % cfg['allocation_period'] == 0 or event or d.task in d.completed or d.new_allocation_event:
                if cfg['method'] != 'centralized':
                    d.allocate(t)
            d.optimize_step(t)
            if cfg['method'] != 'centralized':
                d.certify(t)
        if cfg['method'] == 'centralized' and (t % cfg['allocation_period'] == 0 or t == 0):
            # Deliberately global baseline: map/detections fused at an ideal controller.
            live = [d for d in drones if d.alive]
            if live:
                done = set.union(*(d.completed for d in live))
                for d in live:
                    d.seen |= coverage
                    d.found.update({i: env.survivors[i] for i in detected})
                    d.completed |= done
                keys, targets, priorities = live[0].tasks()
                if keys:
                    costs = np.array([cost_row(d.position, d.battery, d.finished, len(d.neighbors), targets,
                                               priorities, cfg['cost_weights']) for d in live])
                    cap = np.full(len(live), int(np.ceil(len(keys)/len(live)))+1)
                    assignment = CentralizedAllocator().assign(costs, cap)
                    for i, d in enumerate(live):
                        d.owners = {key: live[int(np.argmax(assignment[:, j]))].id for j, key in enumerate(keys)}
                        mine = [k for j, k in enumerate(keys) if assignment[i, j] > .5]
                        responses = [k for k in mine if k.startswith('s')]
                        pool = responses or mine
                        d.task = min(pool, key=lambda k: np.linalg.norm(targets[keys.index(k)]-d.position)) if pool else None
        for d in drones:
            if d.alive:
                d.move()
                d.drain(bus.per_sender.get(d.id, 0)-before.get(d.id, 0))
                for key in d.completed:
                    if key.startswith('s'):
                        rescued.add(int(key[1:]))
        live = [d for d in drones if d.alive]
        live_positions = np.array([d.position for d in live])
        robustness = separation_robustness(live_positions, cfg['d_min'])
        minimum_separation = min(minimum_separation, robustness)
        if len(live) > 1:
            safety_violations += int(np.sum(pdist(live_positions) <= cfg['d_min']))
        active_tasks = [d.task for d in live if d.task]
        conflicts += len(active_tasks)-len(set(active_tasks))
        for survivor, when in detected.items():
            if t-when <= cfg['t_response']:
                response_distances.setdefault(survivor, []).append(
                    min((float(np.linalg.norm(d.position-env.survivors[survivor])) for d in live
                         if d.task == f's{survivor}' or survivor in d.reached), default=1e6))
        for failure in failures:
            if failure['recovered'] is None and recovery_ready(failure['tasks'], active_tasks, failure['time'], t):
                failure['recovered'] = t
        fraction = float(coverage[geom.free].mean())
        consensus_error = max((abs(d.estimate-fraction) for d in live), default=0.)
        messages = bus.attempts-sum(row['messages'] for row in history) if not history else bus.attempts-last_messages
        last_messages = bus.attempts
        history.append(dict(t=t, coverage=fraction, detected=len(detected), rescued=len(rescued),
                            alive=len(live), messages=messages, consensus_error=consensus_error,
                            separation_robustness=robustness,
                            fiedler=fiedler(graph) if capture or t % 20 == 0 else np.nan))
        if cfg.get('debug', False):
            assert all(geom.valid(d.position) for d in drones)
            assert np.all(np.array([d.battery for d in drones]) <= previous_battery+1e-9)
            assert all(np.array_equal(d.position, previous_positions[d.id]) for d in drones if previously_dead[d.id])
            assert all(bus.per_sender.get(d.id, 0) == before.get(d.id, 0) for d in drones if not d.alive)
            assert bus.attempts == sum(bus.per_sender.values())
            assert len(active_tasks) == len(set(active_tasks)), 'Conflicting live task leases'
            if t:
                assert fraction >= history[-2]['coverage']
        if capture:
            trajectory.append(np.array([d.position.copy() for d in drones]))
            if t % cfg['frame_stride'] == 0 or t in schedule.values():
                snapshot = history[-1].copy()
                snapshot.update(positions=np.array([d.position.copy() for d in drones]),
                                alive=alive.copy(), battery=np.array([d.battery for d in drones]),
                                edges=list(graph.edges), tasks=[d.task for d in drones],
                                detected=sorted(detected), rescued=sorted(rescued))
                snapshots.append(snapshot)
        complete = len(rescued) == cfg['survivors'] and (fraction >= .95 or cfg['mission_mode'] == 'rescue_only')
        if complete:
            success, completion = True, t+1
            break
    for failure in failures:
        if failure['detection'] is None:
            fn += 1
    recovery = [(f['recovered'] if f['recovered'] is not None else horizon)-f['time'] for f in failures]
    response = [response_robustness(v) for v in response_distances.values()]
    metrics = dict(seed=seed, n=n, completion_time=completion, success=int(success), timeout=int(not success),
                   coverage=history[-1]['coverage'], detection_rate=len(detected)/cfg['survivors'],
                   rescue_rate=len(rescued)/cfg['survivors'], fairness=jain(np.array([d.work for d in drones])),
                   energy=float(sum(env.batteries)-sum(d.battery for d in drones)),
                   messages=bus.attempts, messages_per_step=bus.attempts/(t+1), delivered=bus.delivered,
                   consensus_error=history[-1]['consensus_error'],
                   recovery_time=float(np.mean(recovery)) if recovery else 0.,
                   recovery_rate=float(np.mean([f['recovered'] is not None for f in failures])) if failures else 1.,
                   false_positives=fp, true_positives=tp, false_negatives=fn,
                   safety_violations=safety_violations, separation_robustness=minimum_separation,
                   response_violations=sum(response_robustness(v) < 0 and t-detected[s] >= cfg['t_response']
                                           for s, v in response_distances.items()),
                   response_robustness=min(response, default=0.),
                   pending_response_windows=sum(t-when < cfg['t_response'] for when in detected.values()),
                   ownership_conflict_steps=conflicts, failures=len(failures),
                   scheduled_failures=len(schedule),
                   admm_fallbacks=sum(d.fallbacks for d in drones), allocation_rounds=sum(d.rounds for d in drones),
                   relay_steps=sum(d.relay_steps for d in drones),
                   runtime_seconds=perf_counter()-started)
    return dict(metrics=metrics, history=history, snapshots=snapshots, failures=failures,
                geometry=geom if capture else None, survivors=env.survivors if capture else None,
                trajectories=np.array(trajectory) if capture else None)
