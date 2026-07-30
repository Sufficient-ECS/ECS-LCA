from bw_timex import TimexLCA
from bw_temporalis import TemporalDistribution
from datetime import datetime
import lca_algebraic as agb
import logging
import numpy as np
import pandas as pd
from bw_timex.utils import plot_characterized_inventory_as_waterfall

from src import OS_database

def compute_temp_impacts(ref_flow, impacts, year_to_db):


    time_dfs = []
    metrics_dfs = []

    exchs = {}

    year_to_db[OS_database] = "dynamic"
    year_to_db["exchange_mapping_database"] = 'dynamic'

    for act in ref_flow[0]:

        #for act in ref_flow[0]:
        lca = TimexLCA(
            demand={act : 1},
            method=('ecoinvent-3.11', 'EF v3.1', 'climate change', 'global warming potential (GWP100)'),
            database_dates = year_to_db,
        )

        timeline = lca.build_timeline()

        timeline.to_csv("./debug_timeline_csv.csv")
        lca.lci(expand_technosphere=True)
        lca.static_lcia()
        lca.dynamic_lcia(metric="radiative_forcing", fixed_time_horizon=False, time_horizon=100)
        r_forcing = lca.dynamic_score
        lca.dynamic_lcia(metric="GWP", fixed_time_horizon=False, time_horizon=100)

        df = pd.DataFrame({
#            "static_score" :      [lca.static_score],
            "base_lca" :          [lca.base_lca.score],
            "radiative_forcing" : [r_forcing],
            "dynamic_GWP" :       [lca.dynamic_score],
            "activity" :          [act["name"]]
        })

        metrics_dfs.append(df)

        plot_data = lca.characterized_inventory.copy().groupby(["date", "activity"]).sum().reset_index()

        date = plot_data["date"]
        amount = plot_data["amount"]
        df = pd.DataFrame({
            "date": date,
            "amount": amount,
        })
        df["activity"] = act["name"]
        time_dfs.append(df)

    time_df = pd.concat(time_dfs, ignore_index=True)
    metrics_df = pd.concat(metrics_dfs, ignore_index=True)
    return time_df, metrics_df