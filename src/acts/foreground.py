import lca_algebraic as agb
from pathlib import Path
import re
import yaml as yml

from src.acts.custom_activities import input_to_activity
from src.smart_acts import smart_activity
from src.utils.utils import get_param, find_activity
from src import OS_database

def process_fground(fground, foreground_db, name):
    ret, rep = [], {}

    if "inputs" in fground:
        fground = fground["inputs"]

    for input_name, input_value in fground.items():

        new_activity_name = f"fg_{name}_{input_name}"
        new_activity_name = re.sub(r"[ \-\(\)?]", "_", new_activity_name)

        rep[new_activity_name] = {}
        for i in input_value:
            if i[:2] == "c_":
                rep[new_activity_name][i[2:]] = input_value[i]

        try:
            exchs = dict(input_to_activity(new_activity_name, input_value, foreground_db))
            act = agb.newActivity(foreground_db, 
                                new_activity_name,
                                "unit",
                                exchanges=exchs,
                                act_id_name = new_activity_name)
            ret.append(act)
        except Exception as e:
            print(f"Error creating activity '{new_activity_name}': {e}")
    return ret, rep

def get_reference_flow(path):

    with open(path, "r") as f:
        fground = yml.safe_load(f)

    exchanges_foreground, rep = process_fground(fground, OS_database, Path(path).stem)

    return exchanges_foreground, rep

