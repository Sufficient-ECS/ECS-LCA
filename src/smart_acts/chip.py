import logging
from functools import lru_cache

import lca_algebraic as agb
import numpy as np

from src.ei_access import EI_Access
from src.ei_access.imec_n0 import get_die_act, tech_n_avail
from src.utils.utils import clean_param_name, find_activity

eia = EI_Access()
agb.unit_registry.define("Wafer = []")

# List of variables:
variables = [
    "d_area",
    "d_elec",
    "d_elec_int",
    "d_tech",
    "n_chip",
    "p_area",
    "p_type",
    "p_weight",
    "type",
    "tot_d_elec",
    "tot_p_weight",
    "tot_d_area",
    "wafer_per_d",
    "tot_wafer_per_d",
]

# Dictionary for how to fetch variables from user
# Can have less variables than node has if some
# variables cannot be given by the user
fetch_map = {
    "d_area"    : ("die", "area", "amount"),
    "d_tech"    : ("die", "technology", "value"),
    "n_chip"    : ("amount", "value"),
    "p_area"    : ("package", "area", "amount"),
    "p_type"    : ("packe", "type", "value"),
    "p_weight"  : ("package", "weight", "amount"),
    "type"      : ("type", "value")
}

defaults = {
    "d_elec_int" : 2.76 * agb.unit_registry("kWh/cm²"), #Ecoinvent default value
    "n_chip"     : 1,
    "p_type"     : "BGA",
    "type"       : "logic",
    "d_tech"     : "N90",
}

def die_area_pred(varis, param_name):
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

    a, beta = param_die_pred[varis["p_type"]]

    result = a * varis["p_area"].to("mm²")**beta

    uncertainty = agb.newFloatParam(
            clean_param_name(f"{param_name}_da_perr"),
            default=1,
            unit="mm²",
            std=0.3,
            distrib="lognormal",
        )

    return result.magnitude * uncertainty

def package_area_pred(varis, param_name):
    # Inverse of die_area_pred
    # https://anncollin.github.io/DieAreaPrediction/

    param_die_pred = {
        "BGA": (0.822, 0.73),
        "WLP": (0.759, 0.99),
        "SOP": (0.063, 1.1),
        "QFN": (0.214, 0.99),
        "DFN": (0.214, 0.99),
        "QFP": (0.724, 0.6)
    }

    a, beta = param_die_pred[varis["p_type"]]

    uncertainty = agb.newFloatParam(
            clean_param_name(f"{param_name}_da_perr"),
            default=1,
            unit="mm²",
            std=0.3,
            distrib="lognormal",
        )

    result = (varis["d_area"] / uncertainty / a) ** (1 / beta)
    return result * agb.unit_registry("mm²")

def pack_weight_pred(varis, param_name):
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

    if varis["p_type"] not in param_pack_weight:
        raise ValueError(f"Package type {varis["p_type"]} not supported")

    a_t_w = param_pack_weight[varis["p_type"]] * agb.unit_registry("mg/mm²")
    return varis["p_area"] * a_t_w

def waf_elec_int(varis, param_name):
    # Based on
    # returns factor in kWh/cm² of wafer
    param_type_int = {
        # Boakes, Lizzie, et al. "Cradle-to-gate life cycle assessment of CMOS logic technologies." 2023
        "A14": 4.10,
        "N2": 3.75,
        "N3": 3.77,
        "N5": 3.18,
        "N7_EUV": 2.72,
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


    if varis["d_tech"] not in param_type_int:
        logging.warning(f"Technology node {varis["d_tech"]} not supported, using default Ecoinvent value")
        return 2.76 * agb.unit_registry("kWh/cm²")

    return param_type_int[varis["d_tech"]] * agb.unit_registry("kWh/cm²")

def de_vries_estimator(varis, param_name):
    # Die per Wafer = (pi * R² - F_corr * 2 * pi *R * L_D)/A_D
    # We actually want Wafer per die 
    # we do the inverse in the return with the division

    side_kerf = varis["d_area"]**0.5 + agb.unit_registry.Quantity(60, "μm")
    die_area = side_kerf**2

    R = agb.unit_registry.Quantity(150, "mm")
    R -= agb.unit_registry.Quantity(3, "mm") #  wafer edge exclusion of 3mm
    de_vries = np.pi * R**2  #pi * R²

    # Supposing L_D = sqrt(R) and F_corr = 0.51
    # F_corr * 2 * pi *R * L_D
    de_vries -= 0.51 * 2 * np.pi * R * side_kerf
    return die_area/de_vries * agb.unit_registry("Wafer")

def waf_elec(data, d_area):
    return d_area * waf_elec_int(data.get("die",{}).get("technology"))

relations = {
    (frozenset(["p_area", "p_type"]), "d_area")         : (die_area_pred, 4),
    (frozenset(["d_area", "p_type"]), "p_area")         : (package_area_pred, 4),
    (frozenset(["p_area", "p_type"]), "p_weight")       : (pack_weight_pred, 3),
    (frozenset(["d_tech"]), "d_elec_int")               : (waf_elec_int, 2),
    (frozenset(["d_area"]), "wafer_per_d")              : (de_vries_estimator, 1),
    (frozenset(["d_area", "d_elec_int"]), "d_elec")     : (lambda data, _: data["d_area"] * data["d_elec_int"], 0),
    (frozenset(["d_area", "n_chip"]), "tot_d_area")     : (lambda data, _: data["d_area"] * data["n_chip"], 0),
    (frozenset(["d_elec", "n_chip"]), "tot_d_elec")     : (lambda data, _: data["d_elec"] * data["n_chip"], 0),
    (frozenset(["p_weight", "n_chip"]), "tot_p_weight") : (lambda data, _: data["p_weight"] * data["n_chip"], 0),
    (frozenset(["wafer_per_d", "n_chip"]), "tot_wafer_per_d") : (lambda data, _: data["wafer_per_d"] * data["n_chip"], 0),
}

@lru_cache(maxsize=1)
def get_acts():
    from src import BG_DB
    # import can't be moved to the start of the file because of circular import
    return (
        find_activity("mod_waf", "GLO", custom_db=BG_DB),
        find_activity("market_circ_logic_no_waf", "GLO", custom_db=BG_DB),
        find_activity("market_circ_memory_no_waf", "GLO", custom_db=BG_DB),
        find_activity("market group for electricity, medium voltage", "GLO")
    )
    
def get_used_acts(data):
    ind_type = 2 if data["type"] == "memory" else 1
    acts = get_acts()
    if eia.use_imec_net_zero:# and data.get("d_tech") in tech_n_avail:
        act = get_die_act(data.get("d_tech"), data["d_area"], eia)
        return [
            (act, "tot_wafer_per_d"),
            (acts[ind_type], "tot_p_weight"),
        ]
    else:

        return [
            (acts[0], "tot_d_area"),
            (acts[ind_type], "tot_p_weight"),
            (acts[3], "tot_d_elec"),
        ]

chip_model = {
    "variables" : variables,
    "fetch_map" : fetch_map,
    "relations" : relations,
    "defaults"  : defaults,
    "get_acts"  : get_used_acts,
}
