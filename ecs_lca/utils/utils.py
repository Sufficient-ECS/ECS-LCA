import ast
import logging
import re
from functools import cache

import bw2data as bd
import lca_algebraic as agb
import numpy as np
import yaml as yml
from bw_temporalis import (
    TemporalDistribution,
    easy_datetime_distribution,
    easy_timedelta_distribution,
)


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

@cache
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
        except Exception as e:
            logging.debug(e)

    try:
        return agb.findActivity(activity_name,
                               loc=location,
                               reference_product=ref_prod,
                               db_name = agb.database._listTechBackgroundDbs()[0]
                               )
    except Exception as e:
        if str(e).startswith("Several activity found in"):
            logging.warning("Please add a reference product to eliminate uncertainty")
            raise e
        else:
            logging.debug(e)

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
    elif isinstance(value, float) or isinstance(value, int):
        return "float"
    elif isinstance(value, str):
        return "enum"
    else:
        raise ValueError(f"Unsupported type: {typenum_capa(value)}")

def get_location(input_value, ef_cat):
    location = input_value.get("location", "GLO" if ef_cat == None else None)

    if isinstance(location, bool): # NO is read as boolean
        location = "NO"

    return location

def clean_param_name(name):
    return name.translate(str.maketrans(
        {
            '²': '2',
            '³': '3',
            '-': '_',
            ' ': '_',
            ':': '_'
        }
    ))

def get_param(name,amount, db, param_group = None):
    """
        Returns the parameter for the given amount
        amount MUST have a value and a unit field
    """

    if amount == None:
        return None

    param_type = get_param_type(amount["value"]).strip().lower()
    param_name = f"{name}_{amount['unit']}"
    param_name = clean_param_name(param_name)
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
                save=False,
                dbname=db,
                group = param_group,
            )
        else:
            raise ValueError(f"Unsupported parameter type: {param_type}")
        
    except Exception as e:
        logging.WARNING(f"Error creating parameter '{param_name}': {e}")

def export_all_db_as_enum(path):
    all_names = sorted({key['name'] for db_name in bd.databases for key in bd.Database(db_name)})

    with open(path, "w", encoding="utf-8") as f:
        yml.dump({"enum": all_names}, f, allow_unicode=True, sort_keys=False)

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

    logging.basicConfig(level=level, force=True)
    logging.getLogger("peewee").setLevel(logging.WARNING)  # or INFO if you prefer

def save_tuple_set(data_set, filename, sep="|"):
    """
    Saves a set of (str, str) tuples to a file, one per line.
    """
    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(f"{x}\n" for x in data_set)

def parse_year_month(value):
    year, month = map(int, value.split("/"))
    return year, month


def year_month_delta_to_months(value):
    """
    Convert a relative year/month delta to months.

    Examples:
        "-2/0" -> -24
        "0/0"  -> 0
        "1/6"  -> 18
    """
    year, month = parse_year_month(value)
    return year * 12 + month


def year_month_to_datetime64(value):
    """
    Convert a human calendar YYYY/MM to datetime64.

    Examples:
        "2026/01" -> 2026-01-01
        "2026/12" -> 2026-12-01
    """
    year, month = parse_year_month(value)

    if not 1 <= month <= 12:
        raise ValueError(f"Invalid calendar month: {month}")

    return np.datetime64(f"{year:04d}-{month:02d}-01")


def parse_delta_time(tv):

    if isinstance(tv, list) and isinstance(tv[0], list):
        # [(delta, amount), ...]
        dates, amounts = zip(*tv)

        td = TemporalDistribution(
            date=np.array(
                [year_month_delta_to_months(t) for t in dates],
                dtype="timedelta64[M]"
            ),
            amount=np.array(amounts),
        )

    elif isinstance(tv, list):
        # [start delta, end delta]
        td = easy_timedelta_distribution(
            start=year_month_delta_to_months(tv[0]),
            end=year_month_delta_to_months(tv[1]),
            resolution="M",
            kind="uniform",
        )

    else:
        td = TemporalDistribution(
            date=np.array(
                [year_month_delta_to_months(tv)],
                dtype="timedelta64[M]"
            ),
            amount=np.array([1.0]),
        )

    return td


def parse_time(tv):

    if isinstance(tv, list) and isinstance(tv[0], list):
        # [(date, amount), ...]
        dates, amounts = zip(*tv)

        td = TemporalDistribution(
            date=np.array(
                [year_month_to_datetime64(t) for t in dates]
            ),
            amount=np.array(amounts),
        )

    elif isinstance(tv, list):
        # [start date, end date]
        td = easy_datetime_distribution(
            start=str(year_month_to_datetime64(tv[0])),
            end=str(year_month_to_datetime64(tv[1])),
            kind="uniform",
        )

    else:
        td = TemporalDistribution(
            date=np.array(
                [year_month_to_datetime64(tv)]
            ),
            amount=np.array([1.0]),
        )

    return td

def resetParamsGroup(db_name, group):
    for param_name, db_params in list(agb.params._param_registry().params.items()):
        if db_name in db_params and db_params[db_name].group == group:
            del db_params[db_name]
        
        if not db_params:
            del agb.params._param_registry().params[param_name]

    agb.params.ActivityParameter.delete().where(agb.params.ActivityParameter.group == group).execute()