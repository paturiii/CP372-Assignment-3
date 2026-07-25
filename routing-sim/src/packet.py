"""
Part C - Packet class

A Packet travels hop-by-hop across routers along a precomputed shortest
path. Each router it visits appends its own label to `path`, increments
`hop_count`, and adds the traversed link's cost to `total_cost`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Packet:
    id: int
    source: str
    destination: str
    path: List[str] = field(default_factory=list)
    hop_count: int = 0
    total_cost: float = 0.0

    def visit(self, router_id: str, link_cost: float = 0.0):
        first_visit = len(self.path) == 0
        self.path.append(router_id)

        if not first_visit:
            self.hop_count += 1
            self.total_cost += link_cost

    def label(self):
        return f"Packet.{self.id}"

    def path_str(self):
        return " \u2192 ".join(self.path)

    def summary(self):
        return (
            f"Forwarding Path for {self.label()}: {self.path_str()}\n"
            f"Hop Count: {self.hop_count}\n"
            f"Total Cost: {self.total_cost:g}"
        )

    def __repr__(self):
        return (
            f"Packet(id={self.id}, {self.source}->{self.destination}, "
            f"hops={self.hop_count}, cost={self.total_cost:g})"
        )
