from src.smart_acts.chip import chip_smart_activity
from src.smart_acts.PCB import PCB_smart_activity

def smart_activity(activity, param_name, db):
    if activity["type"] == "chip":
        return chip_smart_activity(activity, param_name, db)
    if activity["type"] == "pcb":
        return PCB_smart_activity(activity, param_name, db)
    raise Exception("Activity type not supported")
