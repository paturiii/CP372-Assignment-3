import math
import os
import random
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.network import Network
from src.simulator import Simulator

INF = math.inf


def make_sample_network():
    net = Network()
    net.add_link("R1", "R2", 1)
    net.add_link("R1", "R3", 4)
    net.add_link("R2", "R3", 2)
    net.add_link("R2", "R4", 5)
    net.add_link("R3", "R4", 1)
    return net


def test_forward_packet_follows_shortest_path():
    sim = Simulator(make_sample_network())
    packet = sim.forward_packet("R1", "R4")
    assert packet.path == ["R1", "R2", "R3", "R4"]
    assert packet.hop_count == 3
    assert packet.total_cost == 4


def test_forward_packet_same_source_and_destination():
    sim = Simulator(make_sample_network())
    packet = sim.forward_packet("R2", "R2")
    assert packet.path == ["R2"]
    assert packet.hop_count == 0
    assert packet.total_cost == 0


def test_forward_packet_unknown_router_raises():
    sim = Simulator(make_sample_network())
    with pytest.raises(ValueError):
        sim.forward_packet("R1", "R99")
    with pytest.raises(ValueError):
        sim.forward_packet("R99", "R1")


def test_packet_ids_increment_automatically():
    sim = Simulator(make_sample_network())
    p1 = sim.forward_packet("R1", "R2")
    p2 = sim.forward_packet("R1", "R2")
    assert p2.id == p1.id + 1


def test_link_failure_updates_routing_table():
    net = Network()
    net.add_link("R1", "R2", 1)
    net.add_link("R2", "R3", 1)
    net.add_link("R1", "R3", 10)  # redundant, more expensive alternative
    sim = Simulator(net)

    assert sim.routers["R1"].cost_to("R3") == 2  # via R2

    net.remove_link("R1", "R2")
    sim.rebuild_all_routing_tables()

    assert sim.routers["R1"].cost_to("R3") == 10  # now must go direct


def test_apply_random_topology_change_produces_valid_result():
    net = Network.random_topology(10, seed=5)
    sim = Simulator(net)
    rng = random.Random(0)
    result = sim.apply_random_topology_change("R1", "R5", rng=rng)

    assert result.change_type in {
        "link_failure",
        "new_link",
        "link_cost_change",
        "router_failure",
        "noop",
    }
    # after the change, routing tables must reflect the new topology
    if "R1" in sim.network and "R5" in sim.network:
        assert sim.routers["R1"].cost_to("R5") == result.after_cost


def test_link_failure_never_disconnects_network():
    # Run many trials to make sure the bridge-detection guard holds.
    for seed in range(20):
        net = Network.random_topology(10, seed=seed)
        sim = Simulator(net)
        rng = random.Random(seed)
        sim.apply_random_topology_change("R1", "R2", rng=rng)
        assert net.is_connected()


def test_router_failure_removes_router_from_network():
    net = Network.random_topology(15, seed=11, extra_edge_ratio=0.6)
    sim = Simulator(net)
    initial_count = len(net)

    # Force many attempts; at least one router-failure event should occur
    # across seeds without breaking invariants.
    found_router_failure = False
    for seed in range(30):
        net2 = Network.random_topology(15, seed=11, extra_edge_ratio=0.6)
        sim2 = Simulator(net2)
        result = sim2.apply_random_topology_change(
            "R1", "R2", rng=random.Random(seed)
        )
        if result.change_type == "router_failure":
            found_router_failure = True
            assert len(net2) == initial_count - 1
            break
    assert found_router_failure, "Expected at least one router_failure across trials"
