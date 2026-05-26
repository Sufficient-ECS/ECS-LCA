from src.utils.utils import find_activity, get_param, unit_trans

from maxent_disaggregation import sample_shares
import lca_algebraic as agb
import numpy as np

class ParamDisagg(agb.stats.ParamDef):
    shares = {}
    samples = {}
    locks = {}

    def __init__(self, group_name, name, total, share, std_share, **argv):
        if group_name not in self.shares or self.locks.get(group_name, False):
            self.shares[group_name] = {"shares": [], "std_shares":[]}
        if self.locks.get(group_name, False):
            self.samples.pop(group_name)
            self.locks[group_name] = False

        self.id = len(self.shares[group_name]["shares"])
        self.shares[group_name]["shares"].append(share/total["value"])
        self.shares[group_name]["std_shares"].append(std_share)
        self.group_name = group_name
        self.total = total["value"]

        super(ParamDisagg, self).__init__(name, agb.params.ParamType.FLOAT, distrib="SHEEEEESH", **argv)

    def rand(self, alpha):

        if self.group_name not in self.samples or len(self.samples[self.group_name][self.id]) != len(alpha):
            samples, _ = sample_shares(
                n=len(alpha),
                shares=np.array(self.shares[self.group_name]["shares"]),
                sds=np.array(self.shares[self.group_name]["std_shares"]),
            )
            self.samples[self.group_name] = samples.T

        return self.samples[self.group_name][self.id]

    def lock(self):
        self.locks[self.group_name] = True

def composite_activity(param_name, input_value, db):

    total = input_value["amount"]
    param = get_param(param_name, total)
    exchanges = {}

    share_sum = 0
    n_empty = 0
    for elem_name, element in input_value["composition"].items():
            el_amount = element.get("amount", {"unit": total["unit"]})
            share_sum += el_amount.get("value", 0) * unit_trans(el_amount["unit"], total["unit"])
            n_empty += "value" not in el_amount
    def_unk = share_sum / n_empty

    for elem_name, element in input_value["composition"].items():
        full_name = f"{param_name}_{elem_name}"

        el_amount = element.get("amount", {"unit": total["unit"]})
        
        u_f= unit_trans(el_amount["unit"], total["unit"])

        param_comp = ParamDisagg(
            group_name=param_name, 
            name = full_name,
            total = total, 
            share = el_amount.get("value", np.nan) * u_f, 
            default = el_amount.get("value", def_unk),
            std_share = el_amount.get("uncertainty", {}).get("std", np.nan) * u_f, 
            db_name = db,
            unit = el_amount["unit"],
        )
        agb.params._param_registry()[full_name] = param_comp
        ei_name = element["act_name"]
        location = element.get("location", "GLO")
        ref_prod = element.get("ref_prod", None)

        # Find background activity
        activity = find_activity(ei_name, location, ref_prod, db)
        exchanges[activity] = param_comp.with_unit()

    param_comp.lock()

    activity = agb.newActivity(
            db,
            f"{param_name}_group",
            total["unit"],
            exchanges=exchanges,
    )
    return [(activity, param)]