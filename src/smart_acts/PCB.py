import lca_algebraic as agb
import sympy
from functools import lru_cache
from src.utils.utils import find_activity, get_param

def PCB_smart_activity(activity, param_name, db):

    data = activity["data"]

    pcb_area = get_param(f"{param_name}_pcb_area", data.get("area", None))

    copper_layer_thickness = get_param(f"{param_name}_copper_layer_thickness", data.get("copper_layer", {}).get("thickness", None))
    copper_layer_density = get_param(f"{param_name}_copper_layer_density", data.get("copper_layer", {}).get("density", None))
    copper_layer_number = get_param(f"{param_name}_copper_layer_number", data.get("copper_layer", {}).get("number", None))

    unit_area_gold_fingers = get_param(f"{param_name}_connectors_gold_fingers_unit_area", data.get("connectors", {}).get("gold_fingers", {}).get("unit_area", None))
    number_gold_fingers = get_param(f"{param_name}_connectors_gold_fingers_number", data.get("connectors", {}).get("gold_fingers", {}).get("number", None))
    unit_area_circular_connectors = get_param(f"{param_name}_connectors_circular_connectors_unit_area", data.get("connectors", {}).get("circular_connectors", {}).get("unit_area", None))
    number_circular_connectors = get_param(f"{param_name}_connectors_circular_connectors_number", data.get("connectors", {}).get("circular_connectors", {}).get("number", None))
    
    thickness = get_param(f"{param_name}_connectors_gold_thickness", data.get("connectors", {}).get("thickness", None))
    
    acts = get_acts()

    a0 = (acts[0], pcb_area*copper_layer_thickness*copper_layer_density*copper_layer_number*8960*agb.unit_registry("kg/m³")) 
    a1 = (acts[1], (unit_area_gold_fingers*number_gold_fingers + unit_area_circular_connectors*number_circular_connectors)*thickness*19320*agb.unit_registry("kg/m³"))
    a2 = (acts[2], pcb_area)

    return [a0, a1, a2]


@lru_cache(maxsize=1)
def get_acts():
    from src import OS_database
    # import can't be moved to the start of the file because of circular import
    return (
        agb.findTechAct("market for copper, cathode", "GLO"),
        agb.findTechAct("market for gold", "GLO"),
        find_activity("pcb_no_copper_no_gold", "GLO", custom_db=OS_database),
    )
