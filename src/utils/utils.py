import lca_algebraic as agb
import bw2data as bd
import yaml as yml
import os
import hashlib
from functools import lru_cache
import logging
import re
import ast

def load_tuple_file(filename, sep="|"):
    """
    Reads a file and returns a list of (str, str) tuples.
    Returns [] if file does not exist.
    """
    result = []
    try:
        
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:  # skip empty lines
                    result.append(ast.literal_eval(line))
    except FileNotFoundError:
        return []

    return result

@lru_cache(maxsize=None)
def find_activity(activity_name, location, ref_prod = None, ef_cat = None, custom_db = None):
    if ef_cat != None:
        # Should be an elementary flow
        try:
            return agb.findBioAct(activity_name, loc=location, categories=ef_cat)
        except:
            raise ValueError(f"No elementary flow found in biosphere for {activity_name} {ef_cat} at {location}")

    if custom_db != None:
        try:
            return agb.findActivity(activity_name, db_name=custom_db)
        except Exception:
            pass

    try:
        return agb.findTechAct(activity_name, loc=location, reference_product=ref_prod)
    except Exception as e:
        if str(e).startswith("Several activity found in"):
            logging.warning("Please add a reference product to eliminate uncertainty")
            raise e

    # We already know this has failed, just check if user should have passed a category
    try:
        return agb.findBioAct(activity_name, loc=location)
    except Exception as e:
        if str(e).startswith("Several activity found in"):
            logging.warning("Please add a category to your elementary flow")
            raise e
        raise ValueError(f"Activity not found: {activity_name} at {location} (custom_db = {custom_db})")

def get_param_type(value):
    if isinstance(value, bool):
        return "boolean"
    elif isinstance(value, float):
        return "float"
    elif isinstance(value, int):
        return "float"
    elif isinstance(value, str):
        return "enum"
    else:
        raise ValueError(f"Unsupported type: {typenum_capa(value)}")

def get_param(name,amount):
    """
        Returns the parameter for the given amount
        amount MUST have a value and a unit field
    """

    if amount == None:
        return None

    param_type = get_param_type(amount["value"]).strip().lower()
    param_name = f"{name}_{amount['unit']}"
    param_name = param_name.translate(str.maketrans(
        {
            '²': '2',
            '³': '3',
            '-': '_',
            ' ': '_'
        }
    ))
    try:
        if param_type == "float":
            unc = amount.get("uncertainty",{})

            if "distribution" not in unc:
                return agb.unit_registry.Quantity(amount["value"], amount['unit'])

            distrib = unc.get("distribution", "FIXED").upper()

            fac = amount["value"]/100 if unc.get("relative_vals", False) else 1

            return agb.newFloatParam(
                param_name,
                default=amount["value"],
                unit=amount["unit"],
                min=unc.get("min") * fac if unc.get("min") is not None else None,
                max=unc.get("max") * fac if unc.get("max") is not None else None,
                std=unc.get("std") * fac if unc.get("std") is not None else None,
                distrib=getattr(agb.DistributionType, distrib, None),
            )
        else:
            raise ValueError(f"Unsupported parameter type: {param_type}")
        
    except Exception as e:
        logging.WARNING(f"Error creating parameter '{param_name}': {e}")

def export_all_db_as_enum(path):
    all_names = sorted({key['name'] for db_name in bd.databases for key in bd.Database(db_name)})

    with open(path, "w", encoding="utf-8") as f:
        yml.dump({"enum": all_names}, f, allow_unicode=True, sort_keys=False)

import hashlib

def folder_changed(folder: str, state_file: str) -> bool:
    """
    Return True if the folder has changed since last run.
    Always updates the saved folder hash.
    Only saves a single hash of the folder.
    """
    def hash_file(path: str) -> str:
        """Compute SHA256 hash of a file."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()

    # Build a deterministic combined hash of all files
    hashes = []
    for root, dirs, files in os.walk(folder):
        for name in sorted(files):
            path = os.path.join(root, name)
            rel_path = os.path.relpath(path, folder)
            file_hash = hash_file(path)
            hashes.append(f"{rel_path}:{file_hash}")

    # Combine all file hashes into a single folder hash
    folder_hash = hashlib.sha256("\n".join(sorted(hashes)).encode()).hexdigest()

    # Load previous hash
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            prev_hash = f.read().strip()
    else:
        prev_hash = None

    # Always update saved hash
    os.makedirs(os.path.dirname(state_file) or ".", exist_ok=True)
    with open(state_file, "w") as f:
        f.write(folder_hash)

    return prev_hash != folder_hash

def unit_trans(base_unit, new_unit):
    return (1 *  agb.unit_registry(base_unit)).to(new_unit).magnitude

def act_name_sanit(name):
    return re.sub(r"[ \-\(\)?+-]", "_", name)

def set_logging_level(n=2):
    level = logging.WARNING  # default
    if n == 1:
        level = logging.INFO
    elif n >= 2:
        level = logging.DEBUG

    logging.basicConfig(level=level)
    logging.getLogger("peewee").setLevel(logging.WARNING)  # or INFO if you prefer