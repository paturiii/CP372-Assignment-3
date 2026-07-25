"""
Part C - Packet Forwarding Simulation
Part D - Topology Change Simulation

`Simulator` ties a Network together with a live set of Router objects and
provides:
  - forward_packet(): hand a Packet router-to-router along the shortest
    path computed by Dijkstra, exactly like a real link-state network would
    forward it hop by hop.
  - apply_random_topology_change(): trigger a random link failure, new
    link, link-cost change, or router failure; recompute all routing
    tables; and report a before/after path comparison.
"""

from __future__ import annotations

import itertools
import math
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .network import Network
from .packet import Packet
from .router import Router, build_all_routing_tables

INF = math.inf


@dataclass
class TopologyChangeResult:
    change_type: str
    description: str
    before_path: List[str]
    before_cost: float
    after_path: List[str]
    after_cost: float
    watched_source: str
    watched_destination: str

    def format(self):
        before = " \u2192 ".join(self.before_path) if self.before_path else "(unreachable)"
        after = " \u2192 ".join(self.after_path) if self.after_path else "(unreachable)"
        return (
            f"Topology change: {self.description}\n"
            f"Before: {before}   Cost = {_fmt_cost(self.before_cost)}\n"
            f"After {self.description}: {after}   Cost = {_fmt_cost(self.after_cost)}"
        )


class Simulator:
    def __init__(self, network: Network):
        self.network = network
        self.routers: Dict[str, Router] = build_all_routing_tables(network)
        self._packet_counter = itertools.count(1)

    def rebuild_all_routing_tables(self):
        """Recompute routing tables for every router (called after any
        topology change)."""
        self.routers = build_all_routing_tables(self.network)

    def next_packet_id(self):
        return next(self._packet_counter)

    def forward_packet(
        self, source: str, destination: str, packet_id: Optional[int] = None
    ):
        """Simulate a packet travelling hop-by-hop from source to
        destination along the shortest path, as computed by each router's
        Dijkstra routing table.
        """
        if source not in self.network:
            raise ValueError(f"Unknown source router: {source}")
        if destination not in self.network:
            raise ValueError(f"Unknown destination router: {destination}")

        pid = packet_id if packet_id is not None else self.next_packet_id()
        packet = Packet(id=pid, source=source, destination=destination)

        current = source
        packet.visit(current)  # originating router stamps itself, no cost yet

        if source == destination:
            return packet

        visited_guard = {current}
        while current != destination:
            router = self.routers[current]
            nxt = router.next_hop(destination)
            if nxt is None:
                raise RuntimeError(
                    f"Router {current} has no route to {destination}; "
                    "destination may be unreachable."
                )
            link_cost = self.network.link_cost(current, nxt)
            packet.visit(nxt, link_cost)
            current = nxt
            if current in visited_guard:
                raise RuntimeError("Routing loop detected while forwarding packet")
            visited_guard.add(current)

        return packet

    def apply_random_topology_change(
        self,
        watch_source: str,
        watch_destination: str,
        rng: Optional[random.Random] = None,
    ):
        """Trigger one randomly chosen topology change (link failure, new
        link, link cost change, or router failure), recompute routing
        tables, and return a before/after comparison for the watched
        source/destination pair.
        """
        rng = rng or random.Random()

        before_path = self.routers[watch_source].path_to(watch_destination)
        before_cost = self.routers[watch_source].cost_to(watch_destination)

        change_type, description = self._apply_one_random_change(rng)

        self.rebuild_all_routing_tables()

        if watch_source in self.network and watch_destination in self.network:
            after_router = self.routers.get(watch_source)
            after_path = after_router.path_to(watch_destination) if after_router else []
            after_cost = after_router.cost_to(watch_destination) if after_router else INF
        else:
            after_path, after_cost = [], INF

        return TopologyChangeResult(
            change_type=change_type,
            description=description,
            before_path=before_path,
            before_cost=before_cost,
            after_path=after_path,
            after_cost=after_cost,
            watched_source=watch_source,
            watched_destination=watch_destination,
        )

    def _apply_one_random_change(self, rng: random.Random):
        choices = ["link_failure", "new_link", "link_cost_change", "router_failure"]
        rng.shuffle(choices)

        for choice in choices:
            result = self._try_change(choice, rng)
            if result is not None:
                return result
        # Fallback: should not normally happen with >=3 routers
        return "noop", "no change (topology too small)"

    def _try_change(self, choice: str, rng: random.Random):
        edges = self.network.edges()
        routers = self.network.routers

        if choice == "link_failure" and edges:
            a, b, cost = rng.choice(edges)
            if self._is_bridge(a, b):
                return None  # don't disconnect the network
            self.network.remove_link(a, b)
            return "link_failure", f"link {a}-{b} fails"

        if choice == "new_link" and len(routers) >= 2:
            existing = {tuple(sorted((a, b))) for a, b, _ in edges}
            candidates = [
                (a, b)
                for a, b in itertools.combinations(routers, 2)
                if tuple(sorted((a, b))) not in existing
            ]
            if not candidates:
                return None
            a, b = rng.choice(candidates)
            cost = rng.randint(1, 20)
            self.network.add_link(a, b, cost)
            return "new_link", f"new link {a}-{b} added (cost {cost})"

        if choice == "link_cost_change" and edges:
            a, b, old_cost = rng.choice(edges)
            new_cost = rng.randint(1, 30)
            self.network.set_link_cost(a, b, new_cost)
            return (
                "link_cost_change",
                f"link {a}-{b} cost changes from {old_cost:g} to {new_cost}",
            )

        if choice == "router_failure" and len(routers) > 2:
            candidate_routers = [
                r for r in routers if not self._router_is_critical(r)
            ]
            if not candidate_routers:
                return None
            r = rng.choice(candidate_routers)
            self.network.remove_router(r)
            self.routers.pop(r, None)
            return "router_failure", f"router {r} fails"

        return None

    def _is_bridge(self, a: str, b: str):
        """Return True if removing edge (a,b) would disconnect the graph."""
        test_net = self.network.copy()
        test_net.remove_link(a, b)
        return not test_net.is_connected()

    def _router_is_critical(self, router_id: str):
        """Return True if removing this router would disconnect the graph."""
        test_net = self.network.copy()
        test_net.remove_router(router_id)
        return not test_net.is_connected()


def _fmt_cost(cost: float):
    if cost == INF:
        return "inf"
    return f"{cost:g}"
