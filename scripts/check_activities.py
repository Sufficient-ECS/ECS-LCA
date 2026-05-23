#!/usr/bin/env -S PYTHONPATH=${PWD} uv run 

import click
from src import setup_project_ei
from src.utils.utils import find_activity
from pathlib import Path
import pandas as pd
import logging
import bw2data as bd
import yaml

def treat_act(index, act_name, loc):
    if filename_exists("./yaml/custom", act_name):
        return
    loc = "GLO" if pd.isna(loc) else loc

    try:
        act = find_activity(act_name, loc)
        if type(act) == list:
            logging.warning(f"{act_name} at {loc} not found has the following possibilities:")
            logging.warning(act)
    except:
        logging.warning(f"{index}: {act_name} at {loc} not found")

def filename_exists(folder, target_name):
    return any(
        p.is_file() and p.stem == target_name
        for p in Path(folder).rglob("*")
    )


def treat_input(dic):
    for i in dic:
        inp = dic[i]
        if "type" in inp:
            continue
        if "composition" in inp:
            treat_input(inp["composition"])
            continue
        if isinstance(inp["act_name"], list):
            for an in inp["act_name"]: 
                treat_act(i, an, inp.get("location", None))
        else:
            treat_act(i, inp["act_name"], inp.get("location", None))

def treat_yaml(file_path):
    with open(file_path, "r") as f:
        data = yaml.safe_load(f)

        if "inputs" in data: # modified activity or custom
            treat_input(data["inputs"])

def treat_csv(file_path, act_name_col, loc_col):
   df = pd.read_csv(file_path, header=0)
   df = df.dropna(subset=[act_name_col])

   for index, r in df.iterrows():
        act_name = r[act_name_col]
        loc = r[loc_col]
        treat_act(index, act_name, loc)


@click.command()
@click.argument("input_file", default="./yaml", type=click.Path(exists=True))
@click.option("--act_name", required=False, help="If CSV, column for activity name")
@click.option("--loc", required=False, help="Column for location")
@click.option("-v", "--verbose", count=True, help="Increase verbosity (-v, -vv, -vvv)")
def main(input_file, act_name, loc, verbose):

    level = logging.WARNING  # default
    if verbose == 1:
        level = logging.INFO
    elif verbose >= 2:
        level = logging.DEBUG

    logging.basicConfig(level=level)
    logging.getLogger("peewee").setLevel(logging.WARNING)  # or INFO if you prefer

    setup_project_ei("ECS-LCA")

    # input file should be either
    # file .csv
    # file .yaml
    # folder containing yaml

    file = Path(input_file)
    logging.debug(f"Input: {file}")

    if file.is_dir():
        logging.debug(f"Treating the folder of yamls")

        for i in file.rglob("*.yaml"):
            logging.debug(f"Treating the yaml {i}")
            treat_yaml(i)
    elif file.suffix == ".yaml":
        logging.debug(f"Treating the yaml")

        treat_yaml(file)
    elif file.suffix == ".csv":
        if act_name is None or loc is None:
            raise ValueError("Column names should be passed for csv input")
        logging.debug(f"Treating the csv {file}")
        treat_csv(file, act_name, loc)
    else:
        raise ValueError(f"file input {file} is invalid")
if __name__ == "__main__":
    main()