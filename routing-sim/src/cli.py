"""
Command-line entry point for the routing simulator.

Supports two modes:

1. One-shot commands (good for scripting / demos), e.g.:
     python -m src.cli --random 12 --table R1
     python -m src.cli --load data/sample_topology.csv --send R1 R6
     python -m src.cli --random 10 --seed 1 --change R1 R9

2. Interactive menu (just run with no flags, or pass --interactive):
     python -m src.cli --random 12 --interactive
"""

from __future__ import annotations

import argparse
import random
import sys
from typing import Optional

from .network import Network
from .simulator import Simulator


def build_network(args: argparse.Namespace):
    if args.load:
        net = Network.from_csv(args.load)
        print(f"Loaded topology from {args.load}: {net}")
    else:
        n = args.random or 12
        net = Network.random_topology(n, seed=args.seed)
        print(f"Generated random topology with {n} routers (seed={args.seed}): {net}")
    return net


def print_topology(net: Network):
    print(f"\nRouters ({len(net)}): {', '.join(net.routers)}")
    print(f"Links ({len(net.edges())}):")
    for a, b, cost in sorted(net.edges()):
        print(f"  {a} - {b}   cost={cost:g}")


def cmd_table(sim: Simulator, router_id: str):
    if router_id not in sim.routers:
        print(f"Unknown router: {router_id}")
        return
    print()
    print(sim.routers[router_id].format_table())


def cmd_send(sim: Simulator, source: str, destination: str):
    try:
        packet = sim.forward_packet(source, destination)
    except (ValueError, RuntimeError) as exc:
        print(f"Error forwarding packet: {exc}")
        return
    print(f"\n{packet.label()}; Source: {source}; Destination: {destination}")
    print(packet.summary())


def cmd_change(
    sim: Simulator, source: str, destination: str, seed: Optional[int]
):
    rng = random.Random(seed)
    if source not in sim.network or destination not in sim.network:
        print("Both watched routers must exist in the topology.")
        return
    result = sim.apply_random_topology_change(source, destination, rng=rng)
    print()
    print(result.format())
    affected_router = sim.routers.get(source)
    if affected_router:
        print()
        print(affected_router.format_table())


def interactive_menu(sim: Simulator):
    net = sim.network
    print_topology(net)
    help_text = (
        "\nCommands:\n"
        "  table <RouterID>              - print routing table\n"
        "  send <Source> <Dest>          - forward a packet\n"
        "  change <Source> <Dest>        - trigger random topology change,\n"
        "                                   watch Source->Dest path\n"
        "  topology                      - reprint current topology\n"
        "  routers                       - list routers\n"
        "  help                          - show this help\n"
        "  quit                          - exit\n"
    )
    print(help_text)
    while True:
        try:
            line = input("routing-sim> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        parts = line.split()
        cmd = parts[0].lower()

        if cmd in ("quit", "exit"):
            break
        elif cmd == "help":
            print(help_text)
        elif cmd == "topology":
            print_topology(sim.network)
        elif cmd == "routers":
            print(", ".join(sim.network.routers))
        elif cmd == "table" and len(parts) == 2:
            cmd_table(sim, parts[1])
        elif cmd == "send" and len(parts) == 3:
            cmd_send(sim, parts[1], parts[2])
        elif cmd == "change" and len(parts) == 3:
            cmd_change(sim, parts[1], parts[2], seed=None)
        else:
            print("Unrecognized command. Type 'help' for usage.")


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Router network simulator (Dijkstra link-state routing)."
    )
    topo_group = parser.add_mutually_exclusive_group()
    topo_group.add_argument(
        "--load", metavar="CSV_PATH", help="Load topology from a CSV edge-list file"
    )
    topo_group.add_argument(
        "--random",
        type=int,
        metavar="N",
        help="Generate a random connected topology with N routers",
    )
    parser.add_argument(
        "--seed", type=int, default=None, help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--table", metavar="ROUTER_ID", help="Print the routing table for ROUTER_ID"
    )
    parser.add_argument(
        "--send",
        nargs=2,
        metavar=("SOURCE", "DEST"),
        help="Forward a packet from SOURCE to DEST",
    )
    parser.add_argument(
        "--change",
        nargs=2,
        metavar=("SOURCE", "DEST"),
        help="Trigger a random topology change, watching the SOURCE->DEST path",
    )
    parser.add_argument(
        "--save-csv", metavar="CSV_PATH", help="Save the (possibly generated) topology to CSV"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Drop into an interactive menu after running any one-shot commands",
    )
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    net = build_network(args)

    if args.save_csv:
        net.to_csv(args.save_csv)
        print(f"Saved topology to {args.save_csv}")

    sim = Simulator(net)

    did_one_shot = False

    if args.table:
        cmd_table(sim, args.table)
        did_one_shot = True

    if args.send:
        cmd_send(sim, args.send[0], args.send[1])
        did_one_shot = True

    if args.change:
        cmd_change(sim, args.change[0], args.change[1], seed=args.seed)
        did_one_shot = True

    if args.interactive or not did_one_shot:
        interactive_menu(sim)

    return 0


if __name__ == "__main__":
    sys.exit(main())
