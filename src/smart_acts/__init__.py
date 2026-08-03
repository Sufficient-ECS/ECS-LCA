from src.smart_acts.chip import chip_smart_activity
from src.smart_acts.pcb import pcb_smart_activity

def smart_activity(activity, param_name, db):
    if activity["type"] == "chip":
        return chip_smart_activity(activity, param_name, db)
    if activity["type"] == "pcb":
        return pcb_smart_activity(activity, param_name, db)
    raise Exception("Activity type not supported")
