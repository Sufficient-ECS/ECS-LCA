from src.acts.composite_activities import composite_activity
from src.utils.utils import find_activity, get_param, act_name_sanit, get_location, parse_delta_time
from src.smart_acts import smart_activity

from pathlib import Path
import lca_algebraic as agb
import yaml
import logging
import numpy as np
from datetime import datetime

def load_custom_activities(yaml_path):
    activities = []

    for file in Path(yaml_path).rglob("*.yaml"):
        logging.debug(f"Loading {file}")
        with open(file, "r") as f:
            data = yaml.safe_load(f)
            if data == None:
                continue
            data["id"] = str(file.stem)
            activities.append(data)

    return activities

def input_to_activity(param_name, input_value, db, param_group):
    if input_value is None:
        raise ValueError(f"Input '{param_name}' has no value defined in YAML (parsed as None). Check for a missing or malformed entry.")
    if "type" in input_value:
        return smart_activity(input_value, param_name, db, param_group)

    if "composition" in input_value:
        return composite_activity(param_name, input_value, db, param_group)
    
    param = get_param(param_name, input_value["amount"], db, param_group)

    ef_cat = input_value.get("ef_cat", None)

    # Resolve mapping
    ei_names = input_value["act_name"]
    location = get_location(input_value, ef_cat)
    ref_prod = input_value.get("ref_prod", None)

    if ef_cat != None:
        if not isinstance(ef_cat,list):
            ef_cat = (ef_cat,)
        else:
            ef_cat = tuple(ef_cat)

    if not isinstance(ei_names, list):
        ei_names = [ei_names]

    if "t_delta" in input_value:
        td = parse_delta_time(input_value["t_delta"])
        
        param = {
            "amount" : param,
            "temporal_distribution" : td
        }

    return [(find_activity(ei_name, location, ref_prod, ef_cat, db), param) for ei_name in ei_names]

def create_custom_activities(activities, db):
    inputs, updates = [],[]
    for activity in activities:
        if "source_act" in activity:
            to_copy = find_activity(
                activity["source_act"]["act_name"],
                activity["source_act"].get("location", "GLO"),
                activity["source_act"].get("ref_prod", None),
                custom_db=db,
            )
            act = agb.activity.copyActivity(db, to_copy, code= activity['id'])
            logging.debug(f"Modified activity {activity['source_act']['act_name']} at {activity['source_act']['location']}\
 copied with code {activity['id']}")
        else:
            # Create new custom activity
            act = agb.newActivity(
                db,
                activity['id'],
                amount= activity["output"]["amount"]["value"],
                unit = activity["output"]["amount"]["unit"],
                exchanges={}
            )
            logging.debug(f"Activity {activity['id']} created")
        inputs.append((act,activity.get("inputs", {})))
        updates.append((act,activity.get("to_update", {})))
    return inputs, updates

def add_all_exchanges(all_acts, db, param_group):

    for act, input_data in all_acts:
        for input_name, input_value in input_data.items():
            param_name = act_name_sanit(f"{act['name']}_{input_name}")
            if input_value is None:
                raise ValueError(f"Input '{input_name}' in activity '{act['name']}' is None — check your YAML for a missing definition.")

            logging.debug(f"Treating {param_name}")
            for child_act, param in input_to_activity(param_name, input_value, db, param_group):
                act.addExchanges({child_act : param})

def update_all_exchanges(all_acts, db, param_group):
    for act, update_data in all_acts:
        exchanges = {}
        to_del_exchage = []
        for key, data in update_data.items():
            param_name = f"{act['name']}_{key}"
            param = get_param(param_name, data["amount"], db, param_group)

            if param == 0:
                to_del_exchage.append(data['ex_name'])
                continue

            #Need to do the get in case where multiple inputs link to the same activity
            try:
                if "location" in data:
                    exchanges[f"{data['ex_name']}#{data['location']}"] =  param
                else:
                    exchanges[f"{data['ex_name']}"] =  param
            except Exception as e:
                raise ValueError(f"Error occurred while updating exchange for activity {act}: {e}")

        act.updateExchanges(exchanges)
        for ex in to_del_exchage:
            act.deleteExchanges(name=ex)

def generate_activities(path, db, param_group):

    logging.debug(f"Loading custom activities from {path} in memory")
    custom_activities = load_custom_activities(path)

    logging.debug("Create custom activities")
    inputs, updates = create_custom_activities(custom_activities, db)

    logging.debug("Adding exchange to all activities")
    add_all_exchanges(inputs, db, param_group)

    logging.debug("Updating all echances for modified activities")
    update_all_exchanges(updates, db, param_group)
