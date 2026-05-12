import lca_algebraic as agb
import sympy as sp
from src import OS_database

def find_unused_params(root_act, db):
    visited = set()
    used_params = set()

    def traverse(act):
        if act in visited or act._data['database'] != db:
            return
        visited.add(act)

        for exch_name, target_act, amount in act.listExchanges():
            if isinstance(amount, sp.Expr):
                for sym in amount.free_symbols:
                    used_params.add(sym.name)

            if target_act is not None:
                traverse(target_act)

    traverse(root_act)

    all_params = agb.params.all_params()

    unused = {
        param.name: param.default
        for param in all_params.values()
        if param.name not in used_params
    }

    return unused


def stoch_impacts(ref_flow, impacts, n=2**4):
    # Fix unused params to avoid computation cost (if there is any?)
    # If there is no time saved by fixing them beforehand,
    # we could also just remove the columns 
    #unused = find_unused_params(ref_flow[0], db)

    total_ref_flow = agb.newActivity(OS_database,f"act_fg_stoch",  "unit", exchanges={x: 1 for x in ref_flow[0]})

    problem, params, Y = agb.stats._stochastics(total_ref_flow, impacts, n)#**unused
    return Y