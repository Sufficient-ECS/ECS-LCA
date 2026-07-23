import bw2data as bd
import bw2io as bi
from collections.abc import Iterable
from functools import cache
import json
import lca_algebraic as agb
import logging
from pathlib import Path

from premise import NewDatabase
from premise.utils import eidb_label
from premise_gwp import add_premise_gwp

from src.ei_access import EI_Access
from src.ei_access.setup import setup_ecoinvent_database
from src.acts.custom_activities import generate_activities
from src.utils.utils import export_all_db_as_enum, folder_changed, load_tuple_file

agb.Settings.units_enabled = True
agb.unit_registry.auto_scale = True

OS_database = "OS_database"

ei_acc = EI_Access()

def setup_project(custom_act_path, project_name, premise_file = None):
    """
    custom_act_path can be either a list of paths or a single path
    """

    if not isinstance(custom_act_path, Iterable) or isinstance(custom_act_path, (str, bytes)):
        custom_act_path = [custom_act_path]

    setup_project_ei(project_name, premise_file)

    generate_activities(Path(__file__).resolve().parent/"smart_acts/yaml", OS_database)

    for path in custom_act_path:
        generate_activities(path, OS_database)

    if folder_changed("yaml/custom", "results/.snapshot"):
        export_all_db_as_enum("schemas/all_activities_enum.yaml")


def setup_project_ei(project_name, premise_file = None):
    bd.projects.set_current(project_name) # Set the current project, can be any name
    agb.resetDb(OS_database)
    agb.resetParams()   
    agb.setForeground(OS_database) #Create one database where all custom and modified activities will be added.
    
    logging.debug("Setup ecoinvent")

    setup_ecoinvent_database(ei_acc)

    if premise_file != None:
        logging.debug(f"Setup premise with {premise_file}")
        init_premise(ei_acc, premise_file)



def _newPremise_Database(scenarios):
    scenarios = json.loads(scenarios)
    add_premise_gwp()
    ndb = NewDatabase(
        scenarios=scenarios,
        source_db=agb.database._listTechBackgroundDbs()[0],
        source_version=ei_acc.version,
        key=ei_acc.premise_decryption_key,
        biosphere_name=agb.database._find_biosphere_db()
    )

    ndb.update()
    ndb.write_db_to_brightway()

def check_equal_premise_db(db1, already_existing):

    for db_name in already_existing:
        if db1.split(" ")[0] == db_name.split(" ")[0]:
            return db_name
    return False

def init_premise(ei_acc, premise_file):
    scenarios_tuple = load_tuple_file(premise_file, sep=',')

    scenarios = []

    already_existing = [db for db in agb.list_databases().index if db.startswith("ei_")]
        
    for scenario in scenarios_tuple:
        logging.debug(scenario)

        scenario_dic = {
            "model": scenario[0],
            "pathway": scenario[1],
            "year": scenario[2],
        }
        expected_label = eidb_label(
                    scenario_dic,
                    version=ei_acc.version,
                    system_model=ei_acc.system_model,
                )

        logging.debug(f"> {expected_label}")

        res = check_equal_premise_db(expected_label, already_existing)
        if res != False:
            already_existing.remove(res)
            continue

        scenarios.append(scenario_dic)

    if len(scenarios) == 0:
        return

    _newPremise_Database(json.dumps(scenarios, sort_keys=True))
