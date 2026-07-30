from bw_timex import TimexLCA
from bw_temporalis import TemporalDistribution
from datetime import datetime
import lca_algebraic as agb
import logging
import numpy as np
import pandas as pd
from bw_timex.utils import plot_characterized_inventory_as_waterfall

from src import FG_DB, BG_DB
from src.ei_access import EI_Access

ei_acc = EI_Access()

def compute_temp_impacts(ref_flow, impacts, year_to_db, methods):

    agb.freezeParams(FG_DB)
    agb.freezeParams(BG_DB)

    time_dfs = []
    metrics_dfs = []

    exchs = {}

    year_to_db[FG_DB] = "dynamic"
    year_to_db[BG_DB] = "dynamic"
    if ei_acc.use_imec_net_zero:
        year_to_db["exchange_mapping_database"] = 'dynamic'
    for meth in methods:
        for act in ref_flow[0]:
            lca = TimexLCA(
                demand={act : 1},
                method=meth,
                database_dates = year_to_db,
            )

            timeline = lca.build_timeline(temporal_grouping="month")

            lca.lci()
            lca.static_lcia()
            lca.dynamic_lcia(metric="radiative_forcing")
            r_forcing = lca.dynamic_score

            r_forcing_temp_data = (
                lca.characterized_inventory.copy()
                .groupby(["date", "activity"])
                .sum()
                .reset_index()
                .drop(columns=["flow"], errors="ignore")
                .rename(columns={"amount": "radiative_forcing"})
            )


            lca.dynamic_lcia(metric="GWP")

            df = pd.DataFrame({
                "static_score" :      [lca.static_score],
                "base_lca" :          [lca.base_lca.score],
                "radiative_forcing" : [r_forcing],
                "dynamic_GWP" :       [lca.dynamic_score],
                "activity" :          [act["name"]]
            })
            metrics_dfs.append(df)

            dyn_gwp_temp_data = (
                lca.characterized_inventory.copy()
                .groupby(["date", "activity"])
                .sum()
                .reset_index()
                .drop(columns=["flow"], errors="ignore")
                .rename(columns={"amount": "dynamic_GWP"})
            )



            merged = r_forcing_temp_data.merge(
                dyn_gwp_temp_data,
                on=["date", "activity"],
                how="outer",
            )

            merged["method"] = "-".join(meth[1:])
            merged["activity"] = act["name"]

            time_dfs.append(merged)

    time_df = pd.concat(time_dfs, ignore_index=True)
    metrics_df = pd.concat(metrics_dfs, ignore_index=True)
    return time_df, metrics_df