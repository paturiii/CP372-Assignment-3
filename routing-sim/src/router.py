"""
Part B - Dijkstra Routing

Each Router knows about the shared Network topology and can compute (and
cache) its own routing table using Dijkstra's Shortest Path Algorithm:

    routing_table[destination] = (next_hop, cost)

It also stores the full shortest path to every destination so the packet
forwarding simulation (Part C) can walk it hop by hop.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .network import Network

INF = math.inf


@dataclass
class RouteEntry:
    next_hop: Optional[str]
    cost: float
    path: List[str]


class Router:

    def __init__(self, router_id: str, network: Network):
        self.router_id = router_id
        self.network = network
        self.routing_table: Dict[str, RouteEntry] = {}

    def build_routing_table(self):
        distances, previous = dijkstra(self.network, self.router_id)

        table: Dict[str, RouteEntry] = {}
        for dest in self.network.routers:
            if dest == self.router_id:
                continue
            cost = distances.get(dest, INF)
            if cost == INF:
                continue  # unreachable (shouldn't happen in a connected net)
            path = _reconstruct_path(previous, self.router_id, dest)
            next_hop = path[1] if len(path) > 1 else None
            table[dest] = RouteEntry(next_hop=next_hop, cost=cost, path=path)

        self.routing_table = table
        return table

    def forward(self, packet, verbose: bool = True):
        """Process a packet that has arrived at this router (Part C).

        This is the router's own action on the packet, as required by the
        assignment: the router stamps its label onto `packet.path`, bumps
        `packet.hop_count`, and adds the cost of the link it arrived on to
        `packet.total_cost` (all via `Packet.visit`) - then optionally
        displays what it just did. It finally returns the next hop toward
        the packet's destination, or None if this router IS the
        destination (forwarding is complete).
        """
        previous_hop = packet.path[-1] if packet.path else None
        link_cost = self.network.link_cost(previous_hop, self.router_id) if previous_hop else 0.0

        packet.visit(self.router_id, link_cost)

        if verbose:
            print(
                f"  [{self.router_id}] forwarding {packet.label()}: "
                f"path so far = {packet.path_str()}, "
                f"hop_count = {packet.hop_count}, total_cost = {packet.total_cost:g}"
            )

        if self.router_id == packet.destination:
            return None

        nxt = self.next_hop(packet.destination)
        if nxt is None:
            raise RuntimeError(
                f"Router {self.router_id} has no route to {packet.destination}; "
                "destination may be unreachable."
            )
        return nxt

    def next_hop(self, destination: str):
        entry = self.routing_table.get(destination)
        return entry.next_hop if entry else None

    def cost_to(self, destination: str):
        entry = self.routing_table.get(destination)
        return entry.cost if entry else INF

    def path_to(self, destination: str):
        entry = self.routing_table.get(destination)
        return list(entry.path) if entry else []

    def format_table(self):
        """Return the routing table formatted as a Markdown-style table:

            | Destination | Next Hop | Cost |
            |---|---|---|
        """

        lines = [
            f"Routing table for {self.router_id}:",
            "| Destination | Next Hop | Cost |",
            "|---|---|---|",
        ]
        for dest in sorted(self.routing_table.keys(), key=_dest_sort_key):
            entry = self.routing_table[dest]
            lines.append(f"| {dest} | {entry.next_hop} | {entry.cost:g} |")
        return "\n".join(lines)

    def __repr__(self):
        return f"Router({self.router_id})"


def dijkstra(
    network: Network, source: str
):
    distances: Dict[str, float] = {r: INF for r in network.routers}
    previous: Dict[str, Optional[str]] = {r: None for r in network.routers}
    distances[source] = 0.0

    visited = set()
    heap: List[Tuple[float, str]] = [(0.0, source)]

    while heap:
        dist_u, u = heapq.heappop(heap)
        if u in visited:
            continue
        visited.add(u)

        for v, weight in network.neighbors(u).items():
            if v in visited:
                continue
            candidate = dist_u + weight
            if candidate < distances.get(v, INF):
                distances[v] = candidate
                previous[v] = u
                heapq.heappush(heap, (candidate, v))

    return distances, previous


def _reconstruct_path(
    previous: Dict[str, Optional[str]], source: str, dest: str
):
    path = [dest]
    node = dest
    while node != source:
        node = previous.get(node)
        if node is None:
            return []  # unreachable
        path.append(node)
    path.reverse()
    return path


def _dest_sort_key(router_id: str):
    digits = "".join(ch for ch in router_id if ch.isdigit())
    prefix = "".join(ch for ch in router_id if not ch.isdigit())
    return (prefix, int(digits) if digits else 0, router_id)


def build_all_routing_tables(
    network: Network,
):
    #Convenience: build a Router (with routing table) for every router in
    #the network. Returns {router_id: Router}.
    
    routers = {}
    for rid in network.routers:
        r = Router(rid, network)
        r.build_routing_table()
        routers[rid] = r
    return routers
