import math
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.network import Network

INF = math.inf


def test_add_router_and_link():
    net = Network()
    net.add_link("R1", "R2", 5)
    assert "R1" in net
    assert "R2" in net
    assert net.has_link("R1", "R2")
    assert net.link_cost("R1", "R2") == 5
    assert net.link_cost("R2", "R1") == 5  # undirected


def test_no_link_is_infinite_cost():
    net = Network()
    net.add_router("R1")
    net.add_router("R2")
    assert not net.has_link("R1", "R2")
    assert net.link_cost("R1", "R2") == INF


def test_remove_link():
    net = Network()
    net.add_link("R1", "R2", 3)
    net.remove_link("R1", "R2")
    assert not net.has_link("R1", "R2")
    assert net.link_cost("R1", "R2") == INF


def test_remove_router_removes_incident_links():
    net = Network()
    net.add_link("R1", "R2", 1)
    net.add_link("R1", "R3", 2)
    net.remove_router("R1")
    assert "R1" not in net
    assert not net.has_link("R2", "R1")
    assert "R2" in net and "R3" in net


def test_set_link_cost():
    net = Network()
    net.add_link("R1", "R2", 4)
    net.set_link_cost("R1", "R2", 9)
    assert net.link_cost("R1", "R2") == 9
    assert net.link_cost("R2", "R1") == 9


def test_set_link_cost_requires_existing_link():
    net = Network()
    net.add_router("R1")
    net.add_router("R2")
    with pytest.raises(ValueError):
        net.set_link_cost("R1", "R2", 9)


def test_self_link_rejected():
    net = Network()
    with pytest.raises(ValueError):
        net.add_link("R1", "R1", 1)


def test_edges_returns_each_edge_once():
    net = Network()
    net.add_link("R1", "R2", 1)
    net.add_link("R2", "R3", 2)
    edges = net.edges()
    assert len(edges) == 2
    pairs = {tuple(sorted((a, b))) for a, b, _ in edges}
    assert pairs == {("R1", "R2"), ("R2", "R3")}


def test_is_connected_true_for_connected_graph():
    net = Network()
    net.add_link("R1", "R2", 1)
    net.add_link("R2", "R3", 1)
    assert net.is_connected()


def test_is_connected_false_for_disconnected_graph():
    net = Network()
    net.add_link("R1", "R2", 1)
    net.add_router("R3")  # isolated
    assert not net.is_connected()


def test_random_topology_is_connected_and_has_redundant_edges():
    net = Network.random_topology(12, seed=1)
    assert len(net) == 12
    assert net.is_connected()
    # more edges than a spanning tree (n-1) means redundant paths exist
    assert len(net.edges()) > 11


def test_random_topology_reproducible_with_seed():
    net_a = Network.random_topology(10, seed=42)
    net_b = Network.random_topology(10, seed=42)
    assert sorted(net_a.edges()) == sorted(net_b.edges())


def test_csv_round_trip():
    net = Network.random_topology(8, seed=3)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "topo.csv")
        net.to_csv(path)
        loaded = Network.from_csv(path)
    assert sorted(loaded.routers) == sorted(net.routers)
    assert sorted(loaded.edges()) == sorted(net.edges())


def test_to_matrix_shape_and_diagonal():
    net = Network()
    net.add_link("R1", "R2", 3)
    net.add_link("R2", "R3", 4)
    ids, matrix = net.to_matrix()
    assert ids == ["R1", "R2", "R3"]
    for i in range(len(ids)):
        assert matrix[i][i] == 0
    assert matrix[0][1] == 3
    assert matrix[1][2] == 4
    assert matrix[0][2] == INF
