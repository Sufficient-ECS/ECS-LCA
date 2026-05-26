from src.acts.composite_activities import composite_activity
from src.utils.utils import find_activity, get_param, act_name_sanit
from src.smart_acts import smart_activity

from pathlib import Path
import lca_algebraic as agb
import yaml
import logging

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

def input_to_activity(param_name, input_value, db):
    if "type" in input_value:
        return smart_activity(input_value, param_name, db)

    if "composition" in input_value:
        return composite_activity(param_name, input_value, db)
    
    param = get_param(param_name, input_value["amount"])

    # Resolve mapping
    ei_names = input_value["act_name"]
    location = input_value.get("location", "GLO")
    ref_prod = input_value.get("ref_prod", None)

    if not isinstance(ei_names, list):
        ei_names = [ei_names]

    return [(find_activity(ei_name, location, ref_prod, db), param) for ei_name in ei_names]

def create_custom_activities(activities, foreground_db):
    inputs, updates = [],[]
    for activity in activities:
        if "source_act" in activity:
            to_copy = find_activity(
                activity["source_act"]["act_name"],
                activity["source_act"].get("location", "GLO"),
                activity["source_act"].get("ref_prod", None),
                foreground_db
            )
            act = agb.activity.copyActivity(foreground_db, to_copy, code= activity['id'])
            logging.debug(f"Modified activity {activity['source_act']['act_name']} at {activity['source_act']['location']}\
 copied with code {activity['id']}")
        else:
            # Create new custom activity
            act = agb.newActivity(
                foreground_db,
                activity['id'],
                amount= activity["output"]["amount"]["value"],
                unit = activity["output"]["amount"]["unit"],
                exchanges={}
            )
            logging.debug(f"Activity {activity['id']} created")
        inputs.append((act,activity.get("inputs", {})))
        updates.append((act,activity.get("to_update", {})))
    return inputs, updates

def add_all_exchanges(all_acts, foreground_db):
    for act, input_data in all_acts:
        exchanges = {}

        for input_name, input_value in input_data.items():
            param_name = act_name_sanit(f"{act['name']}_{input_name}")

            logging.debug(f"Treating {param_name}")

            for child_act, param in input_to_activity(param_name, input_value, foreground_db):
                #Need to do the get in case where multiple inputs link to the same activity
                exchanges[child_act] =  exchanges.get(child_act,0) + param

        act.addExchanges(exchanges)

def update_all_exchanges(all_acts, foreground_db):
    for act, update_data in all_acts:
        exchanges = {}
        for ex_name, ex_value in update_data.items():
            param_name = f"{act['name']}_{ex_name}"

            param = get_param(param_name, ex_value["amount"])
            #Need to do the get in case where multiple inputs link to the same activity
            exchanges[ex_name] =  param

        act.updateExchanges(exchanges)

def generate_activities(path, db):

    logging.debug("Loading custom activities in memory")
    custom_activities = load_custom_activities(path)

    logging.debug("Create custom activities")
    inputs, updates = create_custom_activities(custom_activities, foreground_db=db)

    logging.debug("Adding exchange to all activities")
    add_all_exchanges(inputs, foreground_db=db)

    logging.debug("Updating all echances for modified activities")
    update_all_exchanges(updates, foreground_db=db)
