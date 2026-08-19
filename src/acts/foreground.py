from bw_temporalis import TemporalDistribution
from datetime import datetime
import lca_algebraic as agb
import logging
import numpy as np
from pathlib import Path

import lca_algebraic as agb
import yaml as yml

from src import DB
from src.acts.custom_activities import input_to_activity
from src.utils.utils import act_name_sanit, parse_time

def process_fground(fground, name):
    ret, rep = [], {}

    global_attr = {}
    for i in fground:
        if i[:2] == "c_":
            global_attr[i[2:]] = fground[i]

    if "inputs" in fground:
        fground = fground["inputs"]

    for input_name, input_value in fground.items():

        new_activity_name = f"fg_{name}_{input_name}"
        new_activity_name = act_name_sanit(new_activity_name)

        rep[new_activity_name] = {}
        for i in input_value:
            if i[:2] == "c_":
                rep[new_activity_name][i[2:]] = input_value[i]

        for attr, val in global_attr.items():
            rep[new_activity_name][attr] = val

        td = None
        if "year" in input_value:
            td = parse_time(input_value["year"])

        try:
            exchs = dict(input_to_activity(new_activity_name, input_value, DB, f"fg_{name}"))
            if td != None:
                exchs = {
                    k: {"amount": v, "temporal_distribution": td}
                    for k, v in exchs.items()
                }
            act = agb.newActivity(DB, 
                                new_activity_name,
                                "unit",
                                exchanges=exchs,
                                act_id_name = new_activity_name)
            ret.append(act)
        except Exception as e:
            raise ValueError(f"Error creating activity '{new_activity_name}': {e}")
    return ret, rep

def get_reference_flow(path):

    with open(path, "r") as f:
        fground = yml.safe_load(f)

    exchanges_foreground, rep = process_fground(fground, Path(path).stem)

    return exchanges_foreground, rep

def clean_reference_flow(ref_flow):
    for act in ref_flow[0]:
        act.delete()