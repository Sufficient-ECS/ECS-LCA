import logging

import numpy as np

from src.smart_acts.chip import chip_model
from src.smart_acts.pcb import pcb_model
from src.utils.utils import get_param


def smart_activity(activity, param_name, db_store):
    if activity["type"] == "chip":
        model = chip_model
    elif activity["type"] == "pcb":
        model = pcb_model
    else:
        raise ValueError("Activity type not supported")

    data = fetch_vars(activity["data"], model["variables"], model["fetch_map"], model["defaults"], param_name, db_store)
    data = find_best_vars(data, model["relations"], param_name)

    result = []
    for act, var in model["get_acts"](data):
        if data[var] == None:
            return ValueError(f"Missing input variables to determine variable {var}")
        result.append((act, data[var]))

    return result

def fetch_vars(data, varis, fm, defaults, param_name, db_store):
    ret = {var : (np.infty, None) for var in varis}

    for var in defaults:
        ret[var] = (451e67, defaults[var])

    for var, mapping in fm.items():
        current = data
        for i in range(len(mapping)):
            if i < len(mapping) - 1:
                if mapping[i] not in current:
                    break
                current = current[mapping[i]]
            else:
                if mapping[-1] == "amount":
                    ret[var] = (0, get_param(f"{param_name}_{var}", current, db_store))
                elif mapping[-1] == "value":
                    ret[var] = (0, current)
                else:
                    raise ValueError
    return ret

def find_best_vars(state, relations, param_name):
    there_is_change = True
    while there_is_change:
        there_is_change = False
        for rel_key, rel_value in relations.items():
            input_vars, output_var = rel_key
            func, weight = rel_value 
            total = sum(state[inp][0] for inp in input_vars) + weight
            if total < state[output_var][0]:
                state[output_var] = (total, func({k : state[k][1] for k in input_vars}, param_name))
                there_is_change = True
        logging.debug(state)
    return {key : value[1] for key, value in state.items()}