"""Tests use independent analytic or optimizer references and explicit counterexamples."""
from __future__ import annotations
import ast
from pathlib import Path
import numpy as np
import networkx as nx
import pytest
import yaml
from swarm.src.env import Environment
from swarm.src.comms import MessageBus, range_graph, fiedler
from swarm.src.selfheal import Heartbeats, failure_schedule
from swarm.src.consensus import metropolis, spectral_rate, faulty_trial, robust_rs
from swarm.src.admm import solve, centralized, project
from swarm.src.allocation import auction
from swarm.src.drone import Drone
from swarm.src.safety import separation_robustness, response_robustness, local_safe_velocity
from swarm.src.sim import simulate


@pytest.fixture
def cfg():
    return yaml.safe_load(Path('swarm/config/default.yaml').read_text())


def test_connected_free_map_and_spawns(cfg):
    from scipy.ndimage import label
    for seed in range(12):
        env = Environment(seed, 20, cfg)
        assert label(env.geometry.free.reshape(50, 50))[1] == 1
        assert .08 <= 1-env.geometry.free.mean() <= .12
        assert all(env.geometry.valid(p) for p in env.positions)
        assert all(env.geometry.valid(p) for p in env.survivors)


def test_graph_and_fiedler():
    p = np.array([[0, 0], [1, 0], [2, 0]])
    g = range_graph(p, np.ones(3, bool), 1.1, 0., np.random.default_rng(1))
    assert nx.is_connected(g)
    assert fiedler(g) == pytest.approx(1.)
    assert fiedler(nx.empty_graph(3)) == 0


def test_bus_delivers_only_existing_edges_and_counts():
    g = nx.path_graph(3)
    bus = MessageBus(1, 0., 0)
    bus.send(1, {'seen': [2]}, 0, g)
    assert bus.attempts == 2 == sum(bus.per_sender.values())
    g.remove_edge(1, 2)
    received = bus.receive(0, g)
    assert len(received[0]) == 1 and not received[2]
    assert bus.dropped == 1


def test_bus_broadcast_snapshot_is_immutable_and_isolated():
    graph = nx.complete_graph(3)
    bus = MessageBus(8, 0, 0)
    payload = {'array': np.array([1., 2.]), 'nested': {'set': {2}}}
    bus.send(0, payload, 0, graph)
    payload['array'][0] = 9
    payload['nested']['set'].add(4)
    boxes = bus.receive(0, graph)
    assert boxes[1][0].payload['array'][0] == 1
    assert boxes[2][0].payload['nested']['set'] == {2}
    with pytest.raises(ValueError):
        boxes[1][0].payload['array'][0] = 4
    with pytest.raises(TypeError):
        boxes[1][0].payload['bad'] = 5


def test_consensus_rate_matches_spectral_prediction():
    g = nx.cycle_graph(9)
    w = metropolis(g)
    assert np.allclose(w.sum(0), 1) and np.allclose(w.sum(1), 1)
    vals, vecs = np.linalg.eigh(w)
    k = np.argsort(abs(vals))[-2]
    x = vecs[:, k]
    error = []
    for _ in range(35):
        error.append(np.linalg.norm(x-x.mean()))
        x = w@x
    measured = np.median(np.array(error)[1:]/np.array(error)[:-1])
    lambda2 = np.linalg.eigvalsh(nx.laplacian_matrix(g).toarray())[1]
    assert measured == pytest.approx(1-lambda2/3, abs=1e-8)
    assert measured == pytest.approx(spectral_rate(g), abs=1e-8)
    assert error[-1] < error[0]*.01


@pytest.mark.parametrize('seed', [11, 12, 13])
def test_edge_admm_matches_independent_lp(seed):
    rng = np.random.default_rng(seed)
    c = rng.uniform(0, 5, (3, 4))
    cap = np.array([2., 2., 2.])
    result = solve(c, cap, nx.path_graph(3), iterations=1800, tol=1e-4, rho=1)
    _, optimum = centralized(c, cap)
    assert result['converged']
    assert abs(result['objective']-optimum) <= .005
    assert np.allclose(result['x'].sum(0), 1, atol=1e-6)
    assert np.all(result['x'].sum(1) <= cap+1e-6)


def test_infeasible_capacity_rejected():
    with pytest.raises(ValueError):
        centralized(np.ones((2, 4)), np.ones(2))


def test_auction_capacity_and_optimal_bound():
    rng = np.random.default_rng(2)
    c = rng.uniform(0, 20, (5, 12))
    cap = np.full(5, 3)
    x = auction(c, cap)
    assert np.all(x.sum(0) == 1) and np.all(x.sum(1) <= cap)
    assert np.sum(x*c) >= centralized(c, cap)[1]-1e-8


def test_heartbeat_timeout_and_revival():
    h = Heartbeats(5)
    h.hear(2, 10)
    assert not h.detect(14)
    assert h.detect(15) == {2}
    assert not h.detect(16)
    h.hear(2, 17)
    assert 2 not in h.suspected


def test_failure_seed_varies_identity_and_schedule():
    a = failure_schedule(1, 20, .3, 600)
    b = failure_schedule(2, 20, .3, 600)
    assert len(a) == 6 and set(a) != set(b)
    assert a == failure_schedule(1, 20, .3, 600)
    assert all(10 <= t < 360 for t in a.values())


def test_local_redistribution_after_suspicion(cfg):
    env = Environment(3, 2, cfg)
    d = Drone(0, env.positions[0], 80, env.geometry, cfg)
    d.status[1] = (0, env.positions[1], 90, 0, 1, 'r0')
    d.allocate(0)
    d.suspicions[1] = (6, 0)
    d.allocate(6)
    assert set(d.proposals.values()) == {0}


def test_wmsr_validity_and_byzantine_counterexample():
    g = nx.complete_graph(7)
    assert robust_rs(g, 2, 2)
    assert not robust_rs(nx.path_graph(5), 2, 2)
    robust = faulty_trial(3, 'wmsr')
    ordinary = faulty_trial(3, 'ordinary')
    assert np.all(robust['history'][:, 1:] >= robust['initial_min']-1e-10)
    assert np.all(robust['history'][:, 1:] <= robust['initial_max']+1e-10)
    assert robust['spread'] < 1e-8
    assert ordinary['error'] > 5 and robust['error'] < 1


def test_stl_known_signs_and_local_repulsion():
    assert separation_robustness(np.array([[0., 0.], [3., 0.]]), 2) == 1
    assert separation_robustness(np.array([[0., 0.], [1., 0.]]), 2) == -1
    assert response_robustness([4, 2, 1]) > 0
    assert response_robustness([4, 3, 2]) < 0
    velocity = local_safe_velocity(np.zeros(2), np.array([2., 0.]), [np.array([3., 0.])], 2, 2)
    assert velocity[0] < 0


def test_decentralization_ast_and_object_isolation(cfg):
    forbidden = {'env', 'sim', 'Environment', 'world', 'drones'}
    for module in ['drone', 'search', 'selfheal', 'allocation', 'admm', 'consensus']:
        tree = ast.parse(Path(f'swarm/src/{module}.py').read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (set((node.module or '').split('.')) & forbidden)
            if isinstance(node, ast.Attribute):
                assert node.attr not in {'world', 'drones', 'survivors'}
    env = Environment(4, 2, cfg)
    d = Drone(0, env.positions[0], 80, env.geometry, cfg)
    assert not any(isinstance(v, Environment) for v in vars(d).values())
    assert not hasattr(d.geometry, 'survivors')
    # Shared geography is immutable and contains no dynamic state.
    with pytest.raises(ValueError):
        d.geometry.free[0] = False


def test_determinism_and_step_invariants(cfg):
    local = cfg | {'steps': 75, 'debug': True, 'failure_fraction': .2}
    a, b = simulate(local, 17), simulate(local, 17)
    am, bm = a['metrics'].copy(), b['metrics'].copy()
    am.pop('runtime_seconds'); bm.pop('runtime_seconds')
    assert am == bm
    assert [r['coverage'] for r in a['history']] == sorted(r['coverage'] for r in a['history'])


def test_capture_contains_actual_failures_and_serializable_trace(cfg):
    local = cfg | {'steps': 100, 'failure_fraction': .3, 'frame_stride': 3, 'debug': True}
    run = simulate(local, 42, capture=True)
    assert run['snapshots'] and run['failures']
    assert run['metrics']['failures'] <= run['metrics']['scheduled_failures']
    for snapshot in run['snapshots']:
        assert snapshot['positions'].shape == (20, 2)
        assert isinstance(snapshot['detected'], list)
        assert isinstance(snapshot['alive'], np.ndarray)


def test_settled_assignment_unique_on_common_neighbor_information(cfg):
    cfg = cfg | {'n': 5}
    env = Environment(23, 5, cfg)
    drones = [Drone(i, p, 80, env.geometry, cfg) for i, p in enumerate(env.positions)]
    graph = nx.complete_graph(5)
    bus = MessageBus(0, 0, 0)
    for drone in drones:
        drone.neighbors = set(graph[drone.id])
        bus.send(drone.id, drone.broadcast(0), 0, graph)
    received = bus.receive(0, graph)
    for drone in drones:
        drone.receive(received[drone.id], 0)
        drone.allocate(0)
        drone.certify(10)
    for drone in drones:
        bus.send(drone.id, drone.broadcast(11), 11, graph)
    received = bus.receive(11, graph)
    for drone in drones:
        drone.receive(received[drone.id], 11)
        drone.certify(20)
    assert all(d.owners == drones[0].owners for d in drones)
    assert drones[0].owners
    tasks = [d.task for d in drones if d.task]
    assert len(tasks) == len(set(tasks))


def test_majority_leases_reject_partition_split_brain(cfg):
    local = cfg | {'n': 5}
    env = Environment(24, 5, local)
    a = Drone(0, env.positions[0], 80, env.geometry, local)
    b = Drone(1, env.positions[1], 80, env.geometry, local)
    a.votes = {(0, 'r0', i): 0 for i in [0, 2, 3]}
    b.votes = {(0, 'r0', i): 1 for i in [1, 4]}
    a.certify(22); b.certify(22)
    assert a.owners['r0'] == 0 and 'r0' not in b.owners
    a.certify(40)
    assert 'r0' not in a.owners  # old certificates expire


def test_reciprocal_barrier_prevents_fresh_pair_crossing():
    for distance in [2.1, 2.5, 3., 3.5, 4., 5., 6., 8.]:
        left, right = np.array([0., 0.]), np.array([distance, 0.])
        for _ in range(10):
            a = local_safe_velocity(left, np.array([2., 0.]), [right], 2, 2)
            b = local_safe_velocity(right, np.array([-2., 0.]), [left], 2, 2)
            left, right = left+a, right+b
            assert np.linalg.norm(right-left) > 2.


def test_recent_positions_remain_safety_constraints_when_link_drops(cfg):
    env = Environment(24, 2, cfg)
    a = Drone(0, np.array([50., 50.]), 80, env.geometry, cfg)
    b = Drone(1, np.array([54., 50.]), 80, env.geometry, cfg)
    a.time = b.time = 5
    a.found[0], b.found[1] = np.array([58., 50.]), np.array([46., 50.])
    a.task, b.task = 's0', 's1'
    a.status[1] = (5, b.position.copy(), 80, 0, 1, 's1')
    b.status[0] = (5, a.position.copy(), 80, 0, 1, 's0')
    assert not a.neighbors and not b.neighbors
    a.move(); b.move()
    assert np.linalg.norm(a.position-b.position) > 2


def test_barrier_covers_delayed_peer_reachable_ball():
    rng = np.random.default_rng(731)
    for age in [0, 1, 2, 3]:
        p, q = np.zeros(2), np.array([10., 0.])
        v = local_safe_velocity(p, np.array([2., 1.]), [q], 2, 2, [age])
        for _ in range(200):
            angle = rng.uniform(0, 2*np.pi)
            displacement = (age+1)*2*np.sqrt(rng.random())*np.array([np.cos(angle), np.sin(angle)])
            assert np.linalg.norm(p+v-q-displacement) > 2


def test_proximity_is_bounded_own_sensor_state(cfg):
    positions = np.array([[50., 50.], [53., 50.], [65., 50.]])
    sensed = Environment.proximity(0, positions[0], positions, np.ones(3, bool), 6)
    assert set(sensed) == {1}
    sensed[1][0] = 0
    assert positions[1, 0] == 53  # local observation does not reference world arrays
    env = Environment(24, 2, cfg)
    a = Drone(0, np.array([50., 50.]), 80, env.geometry, cfg)
    b = Drone(1, np.array([54., 50.]), 80, env.geometry, cfg)
    a.time = b.time = 5
    a.found[0], b.found[1] = np.array([58., 50.]), np.array([46., 50.])
    a.task, b.task = 's0', 's1'
    a.observe({'seen': [], 'found': {}, 'proximity': {1: b.position.copy()}})
    b.observe({'seen': [], 'found': {}, 'proximity': {0: a.position.copy()}})
    a.move(); b.move()
    assert np.linalg.norm(a.position-b.position) > 2


def test_onboard_safety_survives_total_radio_outage(cfg):
    run = simulate(cfg | {'steps': 45, 'p_link': 1., 'drop': 1., 'debug': True}, 43)
    assert run['metrics']['messages'] == 0
    assert run['metrics']['safety_violations'] == 0
    assert run['metrics']['ownership_conflict_steps'] == 0
    assert run['metrics']['success'] == 0  # minority/no-quorum availability is not hidden
