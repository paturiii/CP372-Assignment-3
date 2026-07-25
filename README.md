# Routing Simulator — CP372 Assignment 3

A simulation of a router network that uses **Dijkstra's Shortest Path
Algorithm (Link-State Routing)** to build routing tables, forward packets
hop-by-hop, and adapt to topology changes (link/router failures, new
links, cost changes) — plus a performance analysis and a Tkinter GUI.

## Project structure

```
routing-sim/
├── README.md
├── requirements.txt
├── src/
│   ├── network.py        # Part A: Topology / graph model, CSV + random generation
│   ├── router.py         # Part B: Router class, routing table, Dijkstra
│   ├── packet.py         # Part C: Packet class
│   ├── simulator.py       # Part C+D: Packet forwarding + topology-change simulation
│   ├── gui.py             # GUI bonus (Tkinter)
│   └── cli.py             # Command-line entry point
├── data/
│   └── sample_topology.csv   # 10-router sample topology (edge list CSV)
├── analysis/
│   ├── performance.py     # Part E experiments
│   └── results/           # generated tables (.csv/.md) and plots (.png)
├── tests/                 # pytest unit tests for graph, Dijkstra, packets, topology changes
└── screenshots/
```

## Setup

```bash
cd routing-sim
python3 -m venv .venv
source .venv/bin/activate        # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Tkinter ships with standard Python installations on macOS/Windows/most
Linux distros, so no extra install is needed for the GUI. On some Linux
distros you may need `sudo apt install python3-tk`.

## Topology file format

Topologies are stored as an **edge-list CSV**:

```csv
router1,router2,cost
R1,R2,4
R1,R3,2
...
```

Each row is one bidirectional link. A ready-made 10-router example with
redundant paths lives at `data/sample_topology.csv`.

## Part A–D: Command-line simulator

Run everything through `src/cli.py`. You can either pass one-shot flags,
or drop into an interactive menu.

### Load or generate a topology

```bash
# Load an existing topology
python -m src.cli --load data/sample_topology.csv --interactive

# Or generate a random, guaranteed-connected topology (10-20 routers)
python -m src.cli --random 15 --seed 42 --interactive
```

### One-shot commands

```bash
# Print router R1's routing table (Part B)
python -m src.cli --load data/sample_topology.csv --table R1

# Forward a packet from R1 to R6 (Part C)
python -m src.cli --load data/sample_topology.csv --send R1 R6

# Trigger a random topology change and watch the R1->R6 path change (Part D)
python -m src.cli --load data/sample_topology.csv --change R1 R6 --seed 1

# Combine everything, then drop into the interactive menu
python -m src.cli --random 12 --seed 7 --table R1 --send R1 R6 --change R1 R6 --interactive
```

Example output:

```
Routing table for R1:
| Destination | Next Hop | Cost |
|---|---|---|
| R2 | R3 | 3 |
| R3 | R3 | 2 |
...

Packet.1; Source: R1; Destination: R6
Forwarding Path for Packet.1: R1 → R3 → R7 → R9 → R6
Hop Count: 4
Total Cost: 18

Topology change: link R4-R5 cost changes from 2 to 8
Before: R1 → R3 → R7 → R9 → R6   Cost = 18
After link R4-R5 cost changes from 2 to 8: R1 → R3 → R7 → R9 → R6   Cost = 18
```

### Interactive menu

Once inside the interactive menu (`--interactive`, or just run with no
flags), you get a small REPL:

```
routing-sim> table R1
routing-sim> send R1 R6
routing-sim> change R1 R6
routing-sim> topology
routing-sim> routers
routing-sim> help
routing-sim> quit
```

### Running the tests

```bash
python -m pytest tests/ -v
```

This covers: graph mutation & connectivity, Dijkstra correctness against
hand-computed shortest paths, routing table construction, packet
forwarding (including edge cases like source==destination and unreachable
destinations), and topology-change behavior (link failure never
disconnects the graph, routing tables update correctly, router failure
removes the router).

## Part E: Performance analysis

```bash
python analysis/performance.py
```

This generates random topologies at **10, 20, 50, and 100** routers and
measures, for each size:

- Average shortest-path length (hops)
- Average shortest-path routing cost
- Total routing table entries across all routers
- Routing table computation time (ms)
- Number of routing table entries affected by a random topology change
- Recompute time after that topology change (ms)

- `performance_results.csv` — raw data
- `performance_results.md` — the same table in Markdown, copy-paste ready
- `computation_time_vs_size.png`
- `avg_path_length_vs_size.png`
- `avg_routing_cost_vs_size.png`
- `routing_table_entries_vs_size.png`
- `recompute_time_vs_size.png`

## GUI bonus

```bash
python -m src.gui
```

The GUI lets you:

- **Generate** a random topology (choose router count) or **load/save**
  one from/to CSV.
- Pick a **source/destination** and click **Send Packet** — the shortest
  path animates hop-by-hop on the graph, and the hop count / total cost
  update live.
- View any router's **routing table** in a table view.
- Trigger a **random topology change** (watching how the current
  source→destination path is affected), or manually **fail a specific
  link** or **fail a specific router** — the graph, routing tables, and
  event log all update in real time.


**Not**e: The GUI is a bit laggy due to TKinters version, you may need to press a button multiple times for it to work properly