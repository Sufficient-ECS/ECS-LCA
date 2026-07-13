import lca_algebraic as agb
import sympy
from functools import lru_cache
from src.utils.utils import find_activity, get_param, unit_trans
import logging

def die_area_pred(package_data, p_area, param_name):
    # Return predicted die area in mm² based on package size.
    # https://anncollin.github.io/DieAreaPrediction/

    param_die_pred = {
        "BGA": (0.822, 0.73),
        "WLP": (0.759, 0.99),
        "SOP": (0.063, 1.1),
        "QFN": (0.214, 0.99),
        "DFN": (0.214, 0.99),
        "QFP": (0.724, 0.6)
    }

    if package_data["type"] not in param_die_pred:
        raise Exception(f"Package type {package_data['type']} not supported")

    a, beta = param_die_pred[package_data["type"]]

    result = a * p_area.to("mm²")**beta

    uncertainty = agb.newFloatParam(
            f"{param_name}_da_perr",
            default=1,
            unit="mm²",
            std=0.3,
            distrib="lognormal",
        )

    return result.magnitude * uncertainty

def pack_weight_pred(data, d_area):
    # Temporary factor from Augustin Wattiez based on OSSDA dataset
    # waiting for more complete and precise measurements

    param_pack_weight = {
        "BGA": 2.93,
        "WLP": 1.11,
        "DFN": 4.07,
        "QFN": 4.07,
        "SOP": 5.60,
        "QFP": 4.49,
    }

    p_type = data['package']['type']

    if p_type not in param_pack_weight:
        raise Exception(f"Package type {p_type} not supported")

    a_t_w = param_pack_weight[p_type] * agb.unit_registry("mg/mm²")
    return d_area * a_t_w

def waf_elec_int(d_tech):
    # Based on
    # returns factor in kWh/cm² of wafer
    param_type_int = {
        # Boakes, Lizzie, et al. "Cradle-to-gate life cycle assessment of CMOS logic technologies." 2023
        "A14": 4.10,
        "N2": 3.75,
        "N3": 3.77,
        "N5": 3.18,
        "N7 EUV": 2.72,
        "N7": 2.77,
        "N10": 2.09,
        "N14": 1.83,
        "N20": 1.73,
        "N28": 1.56,
        # Boyd, S. B. (2011). Life-cycle assessment of semiconductors. Springer Science & Business Media.
        "N45": 1.4 / 1.11,
        "N65": 1.5 / 1.4,
        "N90": 1.5 / 1.4,
        "N130": 1.5 / 1.4,
        "N180": 1.6 / 1.25,
        "N250": 1.6 / 1.5,
        "N350": 1.8 / 1.96,

    }

    if d_tech == None:
        return 2.76 * agb.unit_registry("kWh/cm²")#Ecoinvent default value

    if d_tech not in param_type_int:
        logging.warning(f"Technology node {d_tech} not supported, using default Ecoinvent value")
        return 2.76 * agb.unit_registry("kWh/cm²")

    return param_type_int[d_tech] * agb.unit_registry("kWh/cm²")

def waf_elec(data, d_area):
    return d_area * waf_elec_int(data.get("die",{}).get("technology"))

@lru_cache(maxsize=1)
def get_acts():
    from src import OS_database
    # import can't be moved to the start of the file because of circular import
    return (
        find_activity("mod_waf", "GLO", custom_db=OS_database),
        find_activity("market_circ_logic_no_waf", "GLO", custom_db=OS_database),
        find_activity("market_circ_memory_no_waf", "GLO", custom_db=OS_database),
        agb.findTechAct("market group for electricity, medium voltage", "GLO")
    )

def chip_smart_activity(activity, param_name, db):
    data = activity["data"]

    die_area = data.get("die", {}).get("area", None)
    pack_weight = data.get("package", {}).get("weight", None)
    pack_area = get_param(f"{param_name}_pack_area", data.get("package", {}).get("area", None))

    if die_area != None:
        die_area = get_param(f"{param_name}_die_area", die_area)
    else:
        die_area = die_area_pred(data["package"], pack_area, param_name)

    if pack_weight != None:
        pack_weight = get_param(f"{param_name}_pack_weight", pack_weight)
    else:
        pack_weight = pack_weight_pred(data, die_area)

    waffer_elec = waf_elec(data, die_area)

    n_chips = data.get("amount", 1)

    acts = get_acts()

    if "type" in data:
        ind_type= 2 if data["type"] == "memory" else 1
    else:
        logging.warning(f"Chip type not explictely given for {param_name}, defaulting to logic")
        ind_type = 1

    a1 = (acts[0], die_area*n_chips)
    a2 = (acts[ind_type], pack_weight*n_chips)
    a3 = (acts[3], waffer_elec*n_chips)

    return [a1, a2, a3]
