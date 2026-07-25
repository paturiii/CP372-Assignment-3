import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.packet import Packet


def test_packet_visit_first_hop_no_cost():
    p = Packet(id=1, source="R1", destination="R3")
    p.visit("R1")
    assert p.path == ["R1"]
    assert p.hop_count == 0
    assert p.total_cost == 0


def test_packet_visit_accumulates_hops_and_cost():
    p = Packet(id=1, source="R1", destination="R3")
    p.visit("R1")
    p.visit("R2", link_cost=4)
    p.visit("R3", link_cost=6)
    assert p.path == ["R1", "R2", "R3"]
    assert p.hop_count == 2
    assert p.total_cost == 10


def test_packet_summary_format():
    p = Packet(id=5, source="R1", destination="R3")
    p.visit("R1")
    p.visit("R3", link_cost=7)
    summary = p.summary()
    assert "Packet.5" in summary
    assert "R1 \u2192 R3" in summary
    assert "Hop Count: 1" in summary
    assert "Total Cost: 7" in summary
