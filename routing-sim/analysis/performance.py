"""
Part E - Performance Analysis

For random topologies of size 10, 20, 50, and 100 routers, measures:
  - Average shortest-path length (hops) across all router pairs
  - Average shortest-path routing cost across all router pairs
  - Number of routing table entries (total, across all routers)
  - Routing table computation time (ms) - time to build ALL routers'
    Dijkstra routing tables (a full link-state recomputation)
  - The effect of a random topology change: how many routing table
    entries change (next hop or cost) and how long recomputation takes

Outputs:
  - analysis/results/performance_results.csv  (raw data table)
  - analysis/results/performance_results.md    (Markdown table, matching
    the assignment's expected table format, ready to paste into a report)
  - analysis/results/*.png                     (matplotlib graphs)
"""

from __future__ import annotations

import csv
import os
import random
import sys
import time
from dataclasses import dataclass
from statistics import mean
from typing import List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import matplotlib

matplotlib.use("Agg")  # headless-safe backend for saving files
import matplotlib.pyplot as plt

from src.network import Network
from src.router import build_all_routing_tables
from src.simulator import Simulator

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
SIZES = [10, 20, 50, 100]
SEED = 2024


@dataclass
class SizeResult:
    size: int
    avg_path_length: float
    avg_routing_cost: float
    num_routing_table_entries: int
    computation_time_ms: float
    change_entries_affected: int
    change_recompute_time_ms: float


def measure_size(n: int, seed: int):
    net = Network.random_topology(n, seed=seed)

    # routing table computation time
    start = time.perf_counter()
    routers = build_all_routing_tables(net)
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    # aggregate stats across all router pairs
    path_lengths = []
    costs = []
    total_entries = 0

    for rid, router in routers.items():
        total_entries += len(router.routing_table)

        for entry in router.routing_table.values():
            path_lengths.append(len(entry.path) - 1)  # hop count
            costs.append(entry.cost)

    avg_path_length = mean(path_lengths) if path_lengths else 0.0
    avg_routing_cost = mean(costs) if costs else 0.0

    # effect of a topology change
    sim = Simulator(net)
    rng = random.Random(seed)
    src, dst = net.routers[0], net.routers[-1]

    before_tables = {
        rid: dict(r.routing_table) for rid, r in sim.routers.items()
    }

    start = time.perf_counter()
    sim.apply_random_topology_change(src, dst, rng=rng)
    recompute_ms = (time.perf_counter() - start) * 1000.0

    changed = 0

    for rid, before_table in before_tables.items():
        after_router = sim.routers.get(rid)
        after_table = after_router.routing_table if after_router else {}
        keys = set(before_table.keys()) | set(after_table.keys())

        for dest in keys:
            b = before_table.get(dest)
            a = after_table.get(dest)
            b_sig = (b.next_hop, b.cost) if b else None
            a_sig = (a.next_hop, a.cost) if a else None
            if b_sig != a_sig:
                changed += 1

    return SizeResult(
        size=n,
        avg_path_length=avg_path_length,
        avg_routing_cost=avg_routing_cost,
        num_routing_table_entries=total_entries,
        computation_time_ms=elapsed_ms,
        change_entries_affected=changed,
        change_recompute_time_ms=recompute_ms,
    )


def run_all(sizes: List[int] = SIZES, seed: int = SEED):
    results = []

    for n in sizes:
        print(f"Measuring performance for {n} routers...")
        results.append(measure_size(n, seed))
        
    return results


def write_csv(results: List[SizeResult], path: str):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Network Size",
                "Avg Path Length (hops)",
                "Avg Routing Cost",
                "Routing Table Entries",
                "Computation Time (ms)",
                "Entries Changed After Topology Change",
                "Recompute Time After Change (ms)",
            ]
        )

        for r in results:
            writer.writerow(
                [
                    r.size,
                    f"{r.avg_path_length:.2f}",
                    f"{r.avg_routing_cost:.2f}",
                    r.num_routing_table_entries,
                    f"{r.computation_time_ms:.3f}",
                    r.change_entries_affected,
                    f"{r.change_recompute_time_ms:.3f}",
                ]
            )


def write_markdown(results: List[SizeResult], path: str):
    lines = [
        "| Network Size | Avg Path Length (hops) | Avg Routing Cost | "
        "Routing Table Entries | Computation Time (ms) | "
        "Entries Changed After Topology Change | Recompute Time After Change (ms) |",
        "|---|---|---|---|---|---|---|",
    ]

    for r in results:
        lines.append(
            f"| {r.size} | {r.avg_path_length:.2f} | {r.avg_routing_cost:.2f} | "
            f"{r.num_routing_table_entries} | {r.computation_time_ms:.3f} | "
            f"{r.change_entries_affected} | {r.change_recompute_time_ms:.3f} |"
        )
        
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def plot_results(results: List[SizeResult], out_dir: str):
    sizes = [r.size for r in results]

    def _plot(ys, ylabel, title, filename):
        plt.figure(figsize=(6, 4))
        plt.plot(sizes, ys, marker="o")
        plt.xlabel("Network Size (number of routers)")
        plt.ylabel(ylabel)
        plt.title(title)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, filename), dpi=150)
        plt.close()

    _plot(
        [r.computation_time_ms for r in results],
        "Computation Time (ms)",
        "Routing Table Computation Time vs Network Size",
        "computation_time_vs_size.png",
    )
    _plot(
        [r.avg_path_length for r in results],
        "Average Path Length (hops)",
        "Average Path Length vs Network Size",
        "avg_path_length_vs_size.png",
    )
    _plot(
        [r.avg_routing_cost for r in results],
        "Average Routing Cost",
        "Average Routing Cost vs Network Size",
        "avg_routing_cost_vs_size.png",
    )
    _plot(
        [r.num_routing_table_entries for r in results],
        "Total Routing Table Entries",
        "Routing Table Entries vs Network Size",
        "routing_table_entries_vs_size.png",
    )
    _plot(
        [r.change_recompute_time_ms for r in results],
        "Recompute Time After Topology Change (ms)",
        "Topology Change Recompute Time vs Network Size",
        "recompute_time_vs_size.png",
    )


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    results = run_all()

    csv_path = os.path.join(RESULTS_DIR, "performance_results.csv")
    md_path = os.path.join(RESULTS_DIR, "performance_results.md")
    write_csv(results, csv_path)
    write_markdown(results, md_path)
    plot_results(results, RESULTS_DIR)

    print(f"\nSaved results table to:\n  {csv_path}\n  {md_path}")
    print(f"Saved plots to: {RESULTS_DIR}\n")

    print(open(md_path).read())
    return 0


if __name__ == "__main__":
    sys.exit(main())
