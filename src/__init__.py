import bw2data as bd
import bw2io as bi
import lca_algebraic as agb
import logging

from src.ei_access import EI_Access
from src.ei_access.setup import setup_ecoinvent_database
from src.acts.custom_activities import generate_activities
from src.utils.utils import export_all_db_as_enum, folder_changed

agb.Settings.units_enabled = True
agb.unit_registry.auto_scale = True

OS_database = "OS_database"

def setup_project(custom_act_path, project_name):
    ei_acc = EI_Access()
    bd.projects.set_current(project_name) # Set the current project, can be any name
    agb.resetDb(OS_database)
    agb.resetParams()   
    agb.setForeground(OS_database) #Create one database where all custom and modified activities will be added.
    
    logging.debug("Setup ecoinvent")
    setup_ecoinvent_database(ei_acc)

    logging.debug("Setup OS database")
    generate_activities(custom_act_path, OS_database)
    if folder_changed("yaml/custom", "results/.snapshot"):
        export_all_db_as_enum("schemas/all_activities_enum.yaml")