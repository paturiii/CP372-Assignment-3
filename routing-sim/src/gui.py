"""
GUI Bonus - Tkinter desktop app

Visualizes the router network (via networkx + matplotlib embedded in a
Tkinter canvas), lets the user:
  - Generate a random topology or load one from CSV.
  - Pick a source/destination router and click "Send Packet" - the path
    is highlighted/animated on the graph and hop count / total cost are
    shown live.
  - View any router's routing table.
  - Trigger a topology change (random change, or manually fail a specific
    link/router) and watch the graph + routing table update in real time.

Run with:  python -m src.gui
"""

from __future__ import annotations

import random
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional, Tuple

import matplotlib

matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import networkx as nx  # pyright: ignore[reportMissingModuleSource]
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from .network import Network
from .simulator import Simulator

DEFAULT_SIZE = 12
NODE_COLOR = "#8ecae6"
NODE_HIGHLIGHT_COLOR = "#ffb703"
EDGE_COLOR = "#adb5bd"
EDGE_HIGHLIGHT_COLOR = "#fb8500"
FAILED_COLOR = "#e63946"


class RoutingSimGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CP372 Routing Simulator - Dijkstra Link-State Routing")
        self.geometry("1200x760")

        self.network = Network.random_topology(DEFAULT_SIZE, seed=1)
        self.simulator = Simulator(self.network)
        self.pos: Dict[str, Tuple[float, float]] = {}
        self._animation_job: Optional[str] = None

        self._build_layout()
        self._recompute_positions()
        self.refresh_router_dropdowns()
        self.draw_graph()

    def _build_layout(self):
        main = ttk.Frame(self)
        main.pack(fill=tk.BOTH, expand=True)

        graph_frame = ttk.Frame(main)
        graph_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.fig, self.ax = plt.subplots(figsize=(7, 7))
        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        panel = ttk.Frame(main, padding=10)
        panel.pack(side=tk.RIGHT, fill=tk.Y)
        panel.configure(width=380)

        self._build_topology_section(panel)
        ttk.Separator(panel).pack(fill=tk.X, pady=8)
        self._build_packet_section(panel)
        ttk.Separator(panel).pack(fill=tk.X, pady=8)
        self._build_routing_table_section(panel)
        ttk.Separator(panel).pack(fill=tk.X, pady=8)
        self._build_topology_change_section(panel)
        ttk.Separator(panel).pack(fill=tk.X, pady=8)
        self._build_log_section(panel)

    def _build_topology_section(self, parent: ttk.Frame):
        box = ttk.LabelFrame(parent, text="Topology", padding=8)
        box.pack(fill=tk.X)

        row = ttk.Frame(box)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Routers:").pack(side=tk.LEFT)

        self.size_var = tk.IntVar(value=DEFAULT_SIZE)

        ttk.Spinbox(
            row, from_=3, to=50, textvariable=self.size_var, width=6
        ).pack(side=tk.LEFT, padx=4)
        
        ttk.Button(row, text="Generate Random", command=self.on_generate_random).pack(
            side=tk.LEFT, padx=4
        )

        row2 = ttk.Frame(box)
        row2.pack(fill=tk.X, pady=2)
        ttk.Button(row2, text="Load CSV...", command=self.on_load_csv).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(row2, text="Save CSV...", command=self.on_save_csv).pack(
            side=tk.LEFT, padx=2
        )

        self.topology_info_var = tk.StringVar()
        ttk.Label(box, textvariable=self.topology_info_var, foreground="#495057").pack(
            anchor=tk.W, pady=(4, 0)
        )

    def _build_packet_section(self, parent: ttk.Frame):
        box = ttk.LabelFrame(parent, text="Send Packet", padding=8)
        box.pack(fill=tk.X)

        row = ttk.Frame(box)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Source:").grid(row=0, column=0, sticky=tk.W)
        self.source_var = tk.StringVar()
        self.source_combo = self._make_dropdown(row, self.source_var, width=6)
        self.source_combo.grid(row=0, column=1, padx=4)

        ttk.Label(row, text="Dest:").grid(row=0, column=2, sticky=tk.W)
        self.dest_var = tk.StringVar()
        self.dest_combo = self._make_dropdown(row, self.dest_var, width=6)
        self.dest_combo.grid(row=0, column=3, padx=4)

        ttk.Button(box, text="Send Packet", command=self.on_send_packet).pack(
            fill=tk.X, pady=(6, 2)
        )

        self.packet_result_var = tk.StringVar(value="Hop Count: -    Total Cost: -")
        ttk.Label(
            box, textvariable=self.packet_result_var, font=("TkDefaultFont", 10, "bold")
        ).pack(anchor=tk.W)

    def _build_routing_table_section(self, parent: ttk.Frame):
        box = ttk.LabelFrame(parent, text="Routing Table", padding=8)
        box.pack(fill=tk.BOTH)

        row = ttk.Frame(box)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Router:").pack(side=tk.LEFT)

        self.table_router_var = tk.StringVar()
        self.table_router_combo = self._make_dropdown(row, self.table_router_var, width=6)
        self.table_router_combo.pack(side=tk.LEFT, padx=4)

        ttk.Button(row, text="Show Table", command=self.on_show_table).pack(
            side=tk.LEFT, padx=4
        )

        self.table_tree = ttk.Treeview(
            box, columns=("dest", "next_hop", "cost"), show="headings", height=8
        )
        self.table_tree.heading("dest", text="Destination")
        self.table_tree.heading("next_hop", text="Next Hop")
        self.table_tree.heading("cost", text="Cost")

        for col in ("dest", "next_hop", "cost"):
            self.table_tree.column(col, width=100, anchor=tk.CENTER)

        self.table_tree.pack(fill=tk.BOTH, pady=(4, 0))

    def _build_topology_change_section(self, parent: ttk.Frame):
        box = ttk.LabelFrame(parent, text="Topology Change", padding=8)
        box.pack(fill=tk.X)

        ttk.Button(
            box,
            text="Trigger Random Change (watch Source->Dest)",
            command=self.on_random_change,
        ).pack(fill=tk.X, pady=2)

        row = ttk.Frame(box)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Link:").pack(side=tk.LEFT)

        self.link_var = tk.StringVar()
        self.link_combo = self._make_dropdown(row, self.link_var, width=12)
        self.link_combo.pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="Fail Link", command=self.on_fail_link).pack(
            side=tk.LEFT, padx=2
        )

        row2 = ttk.Frame(box)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="Router:").pack(side=tk.LEFT)
        self.fail_router_var = tk.StringVar()
        self.fail_router_combo = self._make_dropdown(row2, self.fail_router_var, width=6)
        self.fail_router_combo.pack(side=tk.LEFT, padx=4)
        ttk.Button(row2, text="Fail Router", command=self.on_fail_router).pack(
            side=tk.LEFT, padx=2
        )

    def _build_log_section(self, parent: ttk.Frame):
        box = ttk.LabelFrame(parent, text="Event Log", padding=8)
        box.pack(fill=tk.BOTH, expand=True)

        scroll = ttk.Scrollbar(box)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text = tk.Text(
            box, height=10, yscrollcommand=scroll.set, wrap=tk.WORD, state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        scroll.config(command=self.log_text.yview)

    def log(self, message: str):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _make_dropdown(self, parent, variable: tk.StringVar, width: int = 8) -> tk.OptionMenu:
        """A tk.OptionMenu-based dropdown.

        We deliberately avoid ttk.Combobox here: Tk 8.6.12 (bundled with
        several recent python.org macOS installers) has a known Aqua bug
        where clicks inside the combobox's popdown listbox are ignored, so
        users can open the list but can never actually select an item.
        tk.OptionMenu renders its list as a native menu instead, which
        isn't affected by that bug.
        """
        om = tk.OptionMenu(parent, variable, "")
        om.configure(width=width, anchor=tk.W)
        return om

    def _set_dropdown_values(self, dropdown: tk.OptionMenu, variable: tk.StringVar, values):
        menu = dropdown["menu"]
        menu.delete(0, "end")

        for v in values:
            menu.add_command(label=v, command=lambda val=v: variable.set(val))

    def refresh_router_dropdowns(self):
        routers = self.network.routers

        for combo, var in (
            (self.source_combo, self.source_var),
            (self.dest_combo, self.dest_var),
            (self.table_router_combo, self.table_router_var),
            (self.fail_router_combo, self.fail_router_var),
        ):
            self._set_dropdown_values(combo, var, routers)

        if routers:
            self.source_var.set(routers[0])
            self.dest_var.set(routers[-1])
            self.table_router_var.set(routers[0])
            self.fail_router_var.set(routers[-1])

        link_values = [f"{a}-{b}" for a, b, _ in sorted(self.network.edges())]
        self._set_dropdown_values(self.link_combo, self.link_var, link_values)

        if link_values:
            self.link_var.set(link_values[0])

        self.topology_info_var.set(
            f"{len(self.network)} routers, {len(self.network.edges())} links"
        )

    def _recompute_positions(self, seed: int = 42):
        g = nx.Graph()
        g.add_nodes_from(self.network.routers)
        g.add_edges_from((a, b) for a, b, _ in self.network.edges())
        self.pos = nx.spring_layout(g, seed=seed)

    def rebuild_after_topology_edit(self):
        self.simulator.rebuild_all_routing_tables()
        self._recompute_positions()
        self.refresh_router_dropdowns()
        self.draw_graph()

    def draw_graph(
        self,
        highlight_path: Optional[List[str]] = None,
        highlight_upto: Optional[int] = None,
    ):
        self.ax.clear()
        g = nx.Graph()
        g.add_nodes_from(self.network.routers)
        edge_costs = {}

        for a, b, cost in self.network.edges():
            g.add_edge(a, b, weight=cost)
            edge_costs[(a, b)] = cost

        for node in g.nodes():
            if node not in self.pos:
                self.pos[node] = (random.random(), random.random())

        highlight_edges = set()
        highlight_nodes = set()

        if highlight_path and len(highlight_path) > 1:
            n = highlight_upto if highlight_upto is not None else len(highlight_path)

            for i in range(min(n, len(highlight_path)) - 1):
                a, b = highlight_path[i], highlight_path[i + 1]
                highlight_edges.add(tuple(sorted((a, b))))

            highlight_nodes = set(highlight_path[: max(n, 1)])

        normal_edges = [
            (a, b) for a, b in g.edges() if tuple(sorted((a, b))) not in highlight_edges
        ]
        nx.draw_networkx_edges(
            g, self.pos, ax=self.ax, edgelist=normal_edges, edge_color=EDGE_COLOR, width=1.5
        )
        if highlight_edges:
            nx.draw_networkx_edges(
                g,
                self.pos,
                ax=self.ax,
                edgelist=list(highlight_edges),
                edge_color=EDGE_HIGHLIGHT_COLOR,
                width=3.0,
            )

        node_colors = [
            NODE_HIGHLIGHT_COLOR if n in highlight_nodes else NODE_COLOR
            for n in g.nodes()
        ]
        nx.draw_networkx_nodes(
            g, self.pos, ax=self.ax, node_color=node_colors, node_size=550
        )

        nx.draw_networkx_labels(g, self.pos, ax=self.ax, font_size=9, font_weight="bold")
        nx.draw_networkx_edge_labels(
            g,
            self.pos,
            ax=self.ax,
            edge_labels={(a, b): f"{c:g}" for (a, b), c in edge_costs.items()},
            font_size=7,
        )

        self.ax.set_title("Network Topology")
        self.ax.axis("off")
        self.canvas.draw_idle()

    def on_generate_random(self):
        n = self.size_var.get()
        self.network = Network.random_topology(n)
        self.simulator = Simulator(self.network)
        self.rebuild_after_topology_edit()
        self.packet_result_var.set("Hop Count: -    Total Cost: -")
        self.log(f"Generated random topology with {n} routers.")

    def on_load_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not path:
            return

        try:
            self.network = Network.from_csv(path)

        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Load failed", str(exc))
            return

        self.simulator = Simulator(self.network)
        self.rebuild_after_topology_edit()
        self.log(f"Loaded topology from {path}.")

    def on_save_csv(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV files", "*.csv")]
        )
        if not path:
            return

        self.network.to_csv(path)
        self.log(f"Saved topology to {path}.")

    def on_send_packet(self):
        source, dest = self.source_var.get(), self.dest_var.get()
        if not source or not dest:
            return

        try:
            packet = self.simulator.forward_packet(source, dest)

        except (ValueError, RuntimeError) as exc:
            messagebox.showerror("Forwarding error", str(exc))
            return

        self.log(f"{packet.label()}; Source: {source}; Destination: {dest}")
        self.log(packet.summary())
        self._animate_packet(packet.path, packet)

    def _animate_packet(self, path: List[str], packet):
        if self._animation_job is not None:
            self.after_cancel(self._animation_job)
            self._animation_job = None

        def step(i: int):
            self.draw_graph(highlight_path=path, highlight_upto=i)
            if i < len(path):
                self._animation_job = self.after(450, lambda: step(i + 1))
            else:
                self._animation_job = None
                self.packet_result_var.set(
                    f"Hop Count: {packet.hop_count}    Total Cost: {packet.total_cost:g}"
                )

        step(1)

    def on_show_table(self):
        router_id = self.table_router_var.get()
        router = self.simulator.routers.get(router_id)

        for row in self.table_tree.get_children():
            self.table_tree.delete(row)

        if not router:
            return

        for dest in sorted(router.routing_table.keys()):
            entry = router.routing_table[dest]
            self.table_tree.insert(
                "", tk.END, values=(dest, entry.next_hop, f"{entry.cost:g}")
            )

    def on_random_change(self):
        source, dest = self.source_var.get(), self.dest_var.get()
        if source not in self.network or dest not in self.network:
            messagebox.showwarning("Invalid pair", "Pick a valid source/destination first.")
            return

        result = self.simulator.apply_random_topology_change(source, dest)
        self._recompute_positions()
        self.refresh_router_dropdowns()
        self.draw_graph()
        self.log(result.format())
        self.on_show_table()

    def on_fail_link(self):
        value = self.link_var.get()
        if not value or "-" not in value:
            return

        a, b = value.split("-", 1)
        self.network.remove_link(a, b)
        self.rebuild_after_topology_edit()
        self.log(f"Manually failed link {a}-{b}.")
        self.on_show_table()

    def on_fail_router(self):
        router_id = self.fail_router_var.get()
        if not router_id:
            return

        self.network.remove_router(router_id)
        self.simulator.routers.pop(router_id, None)
        self.rebuild_after_topology_edit()
        self.log(f"Manually failed router {router_id}.")


def main():
    app = RoutingSimGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
