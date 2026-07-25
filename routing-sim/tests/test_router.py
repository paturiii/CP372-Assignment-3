import math
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.network import Network
from src.router import Router, build_all_routing_tables, dijkstra

INF = math.inf


def make_sample_network():
    """A small hand-computed network for verifying Dijkstra correctness.

    Topology:
        R1 -1- R2
        R1 -4- R3
        R2 -2- R3
        R2 -5- R4
        R3 -1- R4

    Shortest path R1->R4:
        via R1-R2-R4: 1+5=6
        via R1-R2-R3-R4: 1+2+1=4  <-- shortest
        via R1-R3-R4: 4+1=5
    """
    net = Network()
    net.add_link("R1", "R2", 1)
    net.add_link("R1", "R3", 4)
    net.add_link("R2", "R3", 2)
    net.add_link("R2", "R4", 5)
    net.add_link("R3", "R4", 1)
    return net


def test_dijkstra_known_shortest_paths():
    net = make_sample_network()
    distances, previous = dijkstra(net, "R1")
    assert distances["R1"] == 0
    assert distances["R2"] == 1
    assert distances["R3"] == 3  # via R2
    assert distances["R4"] == 4  # via R2->R3->R4


def test_router_routing_table_next_hop_and_cost():
    net = make_sample_network()
    router = Router("R1", net)
    table = router.build_routing_table()

    assert table["R2"].cost == 1
    assert table["R2"].next_hop == "R2"

    assert table["R3"].cost == 3
    assert table["R3"].next_hop == "R2"  # R1->R2->R3 beats direct R1->R3 (4)

    assert table["R4"].cost == 4
    assert table["R4"].next_hop == "R2"
    assert table["R4"].path == ["R1", "R2", "R3", "R4"]


def test_routing_table_excludes_self():
    net = make_sample_network()
    router = Router("R1", net)
    table = router.build_routing_table()
    assert "R1" not in table


def test_format_table_contains_markdown_header():
    net = make_sample_network()
    router = Router("R1", net)
    router.build_routing_table()
    text = router.format_table()
    assert "| Destination | Next Hop | Cost |" in text
    assert "R4" in text


def test_build_all_routing_tables_symmetry():
    net = make_sample_network()
    routers = build_all_routing_tables(net)
    # cost(R1->R4) should equal cost(R4->R1) since graph is undirected
    assert routers["R1"].cost_to("R4") == routers["R4"].cost_to("R1")


def test_dijkstra_on_disconnected_graph_reports_infinite_distance():
    net = Network()
    net.add_link("R1", "R2", 1)
    net.add_router("R3")  # isolated
    distances, _ = dijkstra(net, "R1")
    assert distances["R3"] == INF


def test_routing_table_skips_unreachable_destinations():
    net = Network()
    net.add_link("R1", "R2", 1)
    net.add_router("R3")
    router = Router("R1", net)
    table = router.build_routing_table()
    assert "R3" not in table
    assert "R2" in table


def test_router_forward_stamps_label_and_updates_packet():
    """Part C: the ROUTER object itself (not an external simulator) must
    stamp its label onto the packet and update hop_count/total_cost."""
    from src.packet import Packet

    net = make_sample_network()
    routers = build_all_routing_tables(net)
    packet = Packet(id=1, source="R1", destination="R4")

    nxt = routers["R1"].forward(packet, verbose=False)
    assert packet.path == ["R1"]
    assert packet.hop_count == 0
    assert packet.total_cost == 0
    assert nxt == "R2"

    nxt = routers["R2"].forward(packet, verbose=False)
    assert packet.path == ["R1", "R2"]
    assert packet.hop_count == 1
    assert packet.total_cost == 1
    assert nxt == "R3"


def test_router_forward_returns_none_at_destination():
    from src.packet import Packet

    net = make_sample_network()
    routers = build_all_routing_tables(net)
    packet = Packet(id=2, source="R1", destination="R1")

    nxt = routers["R1"].forward(packet, verbose=False)
    assert nxt is None
    assert packet.path == ["R1"]
    assert packet.hop_count == 0
