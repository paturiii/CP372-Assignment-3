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
    """A single router in the network, capable of building its own
    link-state routing table via Dijkstra's algorithm.
    """

    def __init__(self, router_id: str, network: Network):
        self.router_id = router_id
        self.network = network
        self.routing_table: Dict[str, RouteEntry] = {}

    def build_routing_table(self):
        """Run Dijkstra's algorithm from this router and (re)build the
        routing table: {destination: RouteEntry(next_hop, cost, path)}.
        """
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
    """Classic Dijkstra shortest-path from `source` over `network`.

    Returns:
        distances: {router_id: shortest_cost_from_source}
        previous:  {router_id: predecessor_router_id_on_shortest_path}
    """
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
    """Convenience: build a Router (with routing table) for every router in
    the network. Returns {router_id: Router}.
    """
    routers = {}
    for rid in network.routers:
        r = Router(rid, network)
        r.build_routing_table()
        routers[rid] = r
    return routers
