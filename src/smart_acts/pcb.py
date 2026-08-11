from functools import lru_cache

import lca_algebraic as agb

from src.utils.utils import find_activity

variables = [
    "circ_conn_area",
    "circ_conn_number",
    "circ_conn_unit_area",
    "circ_conn_volume",
    "copper_layer_dens",
    "copper_layer_thick",
    "copper_layer_number",
    "copper_volume",
    "copper_weight",
    "gf_area",
    "gf_number",
    "gf_unit_area",
    "gf_volume",
    "gold_volume",
    "gold_weight",
    "pcb_area",
    "thickness",
]

# Dictionary for how to fetch variables from user
# Can have less variables than node has if some
# variables cannot be given by the user
fetch_map = {
    "pcb_area"               : ("area", "amount"),
    "copper_layer_thick" : ("copper_layer", "thickness", "amount"),
    "copper_layer_dens"   : ("copper_layer", "density", "amount"),
    "copper_layer_number"    : ("copper_layer", "number", "amount"),
    "gf_unit_area" : ("connectors", "gold_fingers", "unit_area", "amount"),
    "gf_number"    : ("connectors", "gold_fingers", "number", "amount"),
    "circ_conn_unit_area"    : ("connectors", "circular_connectors", "unit_area", "amount"),
    "circ_conn_number"       : ("connectors", "circular_connectors", "number", "amount"),
    "thickness"              : ("connectors", "thickness", "amount")
}

defaults = {
    # TODO
}

def copper_volume_est(varis, param_name):
    volume_per_layer = varis["pcb_area"]*varis["copper_layer_thick"]*varis["copper_layer_dens"]
    return volume_per_layer * varis["copper_layer_number"]

gold_vol_mass = agb.unit_registry.Quantity(19320, "kg/m³")
copper_vol_mass = agb.unit_registry.Quantity(8960, "kg/m³")

relations = {
    (frozenset(["pcb_area", "copper_layer_thick", "copper_layer_dens", "copper_layer_number"]), "copper_volume") : (copper_volume_est, 0),
    (frozenset(["copper_volume"]), "copper_weight") : (lambda data, _: data["copper_volume"] * copper_vol_mass, 0),
    (frozenset(["gf_unit_area", "gf_number"]), "gf_area") : (lambda data, _: data["gf_unit_area"] * data["gf_number"], 0),
    (frozenset(["gf_area", "thickness"]), "gf_volume") : (lambda data, _: data["gf_area"] * data["thickness"], 0),
    (frozenset(["circ_conn_unit_area", "circ_conn_number"]), "circ_conn_area") : (lambda data, _: data["circ_conn_unit_area"] * data["circ_conn_number"], 0),
    (frozenset(["circ_conn_area", "thickness"]), "circ_conn_volume") : (lambda data, _: data["circ_conn_area"] * data["thickness"], 0),
    (frozenset(["gf_volume", "circ_conn_volume"]), "gold_weight") : (lambda data, _: (data["gf_volume"] + data["circ_conn_volume"]) * gold_vol_mass, 0),
}

@lru_cache(maxsize=1)
def get_acts():
    from src import OS_database
    # import can't be moved to the start of the file because of circular import
    return (
        find_activity("market for copper, cathode", "GLO"),
        find_activity("market for gold", "GLO"),
        find_activity("pcb_no_copper_no_gold", "GLO", custom_db=OS_database),
    )


def get_used_acts(data):
    acts = get_acts()

    return [
        (acts[0], "copper_weight"), 
        (acts[1], "gold_weight"), 
        (acts[2], "pcb_area"),
    ]

pcb_model = {
    "variables" : variables,
    "fetch_map" : fetch_map,
    "relations" : relations,
    "defaults"  : defaults,
    "get_acts"  : get_used_acts,
}