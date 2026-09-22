import lca_algebraic as agb
import pandas as pd

def compute_impacts(ref_flow, impacts):
    df_impacts_axis = agb.compute_impacts(ref_flow[0], impacts)

    new_cols = pd.DataFrame.from_dict(ref_flow[1], orient="index")

    new_cols.index = new_cols.index.astype(df_impacts_axis.index.dtype)
    df_impacts_axis = df_impacts_axis.join(new_cols)
    
    return df_impacts_axis