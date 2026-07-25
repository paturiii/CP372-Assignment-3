"""
Part A - Network Topology

Models a network of routers as a weighted, undirected graph. Supports:
  - Loading a topology from a CSV edge-list file.
  - Generating a random, guaranteed-connected topology (spanning tree +
    extra redundant edges).
  - Adding/removing routers and links.
  - Saving a topology to a CSV edge-list file.

The topology is stored internally as a weighted adjacency dict (a sparse
adjacency-list representation), which also supports being viewed as a full
adjacency matrix via `to_matrix()`.
"""

from __future__ import annotations

import csv
import math
import random
from typing import Dict, Optional

INF = math.inf


class Network:

    def __init__(self):
        self._adj: Dict[str, Dict[str, float]] = {}

    def add_router(self, router_id: str):
        self._adj.setdefault(router_id, {})

    def remove_router(self, router_id: str):
        if router_id not in self._adj:
            return
        for neighbor in list(self._adj[router_id].keys()):
            del self._adj[neighbor][router_id]
        del self._adj[router_id]

    def add_link(self, a: str, b: str, cost: float):
        if a == b:
            raise ValueError("Cannot create a link from a router to itself")
        self.add_router(a)
        self.add_router(b)
        self._adj[a][b] = cost
        self._adj[b][a] = cost

    def remove_link(self, a: str, b: str):
        self._adj.get(a, {}).pop(b, None)
        self._adj.get(b, {}).pop(a, None)

    def set_link_cost(self, a: str, b: str, cost: float):
        if not self.has_link(a, b):
            raise ValueError(f"No link between {a} and {b} to update")
        self._adj[a][b] = cost
        self._adj[b][a] = cost

    def has_link(self, a: str, b: str):
        return b in self._adj.get(a, {})

    def link_cost(self, a: str, b: str):
        return self._adj.get(a, {}).get(b, INF)

    @property
    def routers(self):
        return sorted(self._adj.keys(), key=_router_sort_key)

    def neighbors(self, router_id: str):
        return dict(self._adj.get(router_id, {}))

    def edges(self):
        seen = set()
        result = []
        for a in self._adj:
            for b, cost in self._adj[a].items():
                key = tuple(sorted((a, b)))
                if key not in seen:
                    seen.add(key)
                    result.append((key[0], key[1], cost))
        return result

    def __len__(self):
        return len(self._adj)

    def __contains__(self, router_id: str):
        return router_id in self._adj

    def copy(self):
        net = Network()
        net._adj = {r: dict(links) for r, links in self._adj.items()}
        return net

    def is_connected(self):
        if not self._adj:
            return True
        start = next(iter(self._adj))
        visited = {start}
        stack = [start]
        while stack:
            node = stack.pop()
            for neighbor in self._adj[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)
        return len(visited) == len(self._adj)

    def to_matrix(self):
        ids = self.routers
        index = {r: i for i, r in enumerate(ids)}
        n = len(ids)
        matrix = [[0.0 if i == j else INF for j in range(n)] for i in range(n)]
        for a, b, cost in self.edges():
            i, j = index[a], index[b]
            matrix[i][j] = cost
            matrix[j][i] = cost
        return ids, matrix

    @classmethod
    def from_csv(cls, path: str):
        net = cls()
        with open(path, newline="") as f:
            reader = csv.reader(f)
            rows = list(reader)
        if not rows:
            return net
        start_idx = 0
        header = [c.strip().lower() for c in rows[0]]
        if header[:3] == ["router1", "router2", "cost"]:
            start_idx = 1
        for row in rows[start_idx:]:
            if not row or row[0].strip().startswith("#"):
                continue
            a, b, cost = row[0].strip(), row[1].strip(), float(row[2].strip())
            net.add_link(a, b, cost)
        return net

    def to_csv(self, path: str):
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["router1", "router2", "cost"])
            for a, b, cost in self.edges():
                writer.writerow([a, b, cost])

    @classmethod
    def random_topology(
        cls,
        num_routers: int,
        min_cost: int = 1,
        max_cost: int = 20,
        extra_edge_ratio: float = 0.5,
        seed: Optional[int] = None,
    ):
        rng = random.Random(seed)
        net = cls()
        ids = [f"R{i}" for i in range(1, num_routers + 1)]
        for r in ids:
            net.add_router(r)

        shuffled = ids[:]
        rng.shuffle(shuffled)
        connected = [shuffled[0]]
        for node in shuffled[1:]:
            other = rng.choice(connected)
            cost = rng.randint(min_cost, max_cost)
            net.add_link(node, other, cost)
            connected.append(node)

        num_extra = max(1, int((num_routers - 1) * extra_edge_ratio))
        attempts = 0
        added = 0
        while added < num_extra and attempts < num_extra * 20:
            attempts += 1
            a, b = rng.sample(ids, 2)
            if not net.has_link(a, b):
                cost = rng.randint(min_cost, max_cost)
                net.add_link(a, b, cost)
                added += 1

        return net

    def __repr__(self):
        return f"Network(routers={len(self)}, links={len(self.edges())})"


def _router_sort_key(router_id: str):
    digits = "".join(ch for ch in router_id if ch.isdigit())
    prefix = "".join(ch for ch in router_id if not ch.isdigit())
    return (prefix, int(digits) if digits else 0, router_id)
