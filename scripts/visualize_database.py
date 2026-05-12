#!/usr/bin/env -S PYTHONPATH=${PWD} uv run 

import networkx as nx
from pyvis.network import Network
from src.acts.custom_activities import load_custom_activities

all_data = load_custom_activities("./yaml/custom")
custom_nodes = set()
modified_nodes = set()
smart_nodes = ["chip smart act"]
data = []

for activity in all_data:
    relat = []
    for value in activity.get("inputs", {}).values():
        if "type" in value: 
            if value["type"] == "chip":
                relat.append(("chip smart act", 1, "unit"))
            continue
        acts = value["act_name"]
        if not isinstance(acts, list):
            acts = [acts]
        for act in acts:
            a = (act, value["amount"]["value"], value["amount"]["unit"]) 
            relat.append(a)


    if "source_act" in activity.keys():
        modified_nodes.add(activity["id"])

        relat.append((activity["source_act"]["act_name"], 1, "unit"))
    else:
        custom_nodes.add(activity["id"])
    data.append((activity["id"], {}, relat))

data.append(("chip smart act", {}, [("mod_waf", 1, "unit")]))
data.append(("chip smart act", {}, [("market_circ_logic_no_waf", 1, "unit")]))
data.append(("chip smart act", {}, [("market_circ_memory_no_waf", 1, "unit")]))
data.append(("chip smart act", {}, [("market group for electricity, medium voltage", 1, "unit")]))

# ----------------------------
# BUILD GRAPH
# ----------------------------
G = nx.DiGraph()

for node, meta, children in data:
    # add node with metadata
    G.add_node(node, **meta)

    # add edges with weight + unit
    for child, weight, unit in children:
        G.add_edge(
            node,
            child,
            weight=weight,
            unit=unit,
            label=f"{weight} {unit}"  # optional convenience label
        )

# ----------------------------
# VISUALIZATION (PYVIS)
# ----------------------------
net = Network(
    directed=True,
    height="750px",
    width="100%",
    bgcolor="#ffffff"
)

net.from_nx(G)

# ----------------------------
# EDGE FORMATTING (IMPORTANT)
# ----------------------------
for edge in net.edges:
    src = edge["from"]
    dst = edge["to"]

    edge_data = G.get_edge_data(src, dst)

    if edge_data:
        weight = edge_data.get("weight", "")
        unit = edge_data.get("unit", "")

        edge["title"] = edge["label"]#f"{weight} {unit}"
        edge["label"] = ""

        # FIX: constant arrow styling
        edge["arrows"] = "to"
        edge["arrowsize"] = 8
        edge["arrowStrikethrough"] = False
        edge["width"] = 1.5

# ----------------------------
# NODE TOOLTIP FORMATTING
# ----------------------------
for node in net.nodes:
    node_id = node["id"]
    node["title"] = str(G.nodes[node_id])  # show metadata on hover

    if node_id in custom_nodes:
        node["color"] = "#1f77b4"   # blue
    elif node_id in smart_nodes:
        node["color"] = "#b42217"   # red
    elif node_id in modified_nodes:
        node["color"] = "#22b417"   # grene
    else:
        # implicit / discovered-only node
        node["color"] = "#ffcc00"   # yellow
net.set_options('''
{
  "edges": {
    "arrows": {
      "to": {
        "enabled": true,
        "scaleFactor": 1
      }
    }
  }
}
''')
# ----------------------------
# OUTPUT HTML
# ----------------------------
net.write_html("graph.html", open_browser=True, notebook=False)