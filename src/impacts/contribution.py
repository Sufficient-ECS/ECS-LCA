import lca_algebraic as agb
import pandas as pd

def compute_impacts(ref_flow, impacts):
    dfs = [agb.compute_impacts(act, impacts, functional_unit=1) for act in ref_flow[0]]

    df_impacts_axis = pd.concat(dfs)

    new_cols = pd.DataFrame.from_dict(ref_flow[1], orient="index")

    new_cols.index = new_cols.index.astype(df_impacts_axis.index.dtype)
    df_impacts_axis = df_impacts_axis.join(new_cols)
    
    return df_impacts_axis