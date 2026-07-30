#!/usr/bin/env -S PYTHONPATH=${PWD} uv run 

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
pd.set_option('display.max_rows', None)
X = pd.read_csv(f"./results/foreground_temp_time.csv")

X["date"] = pd.to_datetime(X["date"])
X["year"] = X["date"].dt.year
# Aggregate in case there are multiple rows per year/activity
df = (
    X
    .dropna(subset=["dynamic_GWP"])
    .groupby(["year", "activity"], as_index=False)["dynamic_GWP"]
    .sum()
)

years = sorted(df["year"].unique())
activities = sorted(df["activity"].unique())

palette = dict(zip(activities, sns.color_palette("tab10", len(activities))))

fig, ax = plt.subplots(figsize=(10, 6))

cumulative = 0

for year in years:
    year_df = df[df["year"] == year]

    bottom = cumulative
    for _, row in year_df.iterrows():
        ax.bar(
            year,
            row["dynamic_GWP"],
            bottom=bottom,
            color=palette[row["activity"]],
            edgecolor="black",
            label=row["activity"],
        )
        bottom += row["dynamic_GWP"]

    cumulative = bottom

results_dir = Path("./results")

dfs = []
for year in (2020, 2030, 2040):
    fp = next(
        results_dir.glob(
            f"ei_cutoff_3.*_remind-eu_SSP2-NDC_{year} *_foreground_impacts.csv"
        )
    )

    df = pd.read_csv(fp, index_col=0)
    df["year"] = year
    dfs.append(df)

df = pd.concat(dfs)

if True:
    df_2020 = df[df["year"]==2020]

    bottom = 0
    for index, row in df_2020.iterrows():
        ax.bar(
            2020,
            row["EF v3.1 - climate change[kg CO2-Eq]"],
            bottom=bottom,
            color=palette[index],
            edgecolor="black",
            label=index,
        )
        bottom += row["EF v3.1 - climate change[kg CO2-Eq]"]

    df_2040 = df[df["year"]==2040]

    bottom = 0
    for index, row in df_2040.iterrows():
        ax.bar(
            2040,
            row["EF v3.1 - climate change[kg CO2-Eq]"],
            bottom=bottom,
            color=palette[index],
            edgecolor="black",
            label=index,
        )
        bottom += row["EF v3.1 - climate change[kg CO2-Eq]"]


# Remove duplicate legend entries
handles, labels = ax.get_legend_handles_labels()
by_label = dict(zip(labels, handles))
ax.legend(by_label.values(), by_label.keys(), title="Activity")


ax.set_xticks([
    2020,
    2025,
    2030,
    2035,
    2040,
    2045
])
ax.set_xticklabels([
    "Premise\n2020",
    2025,
    2030,
    2035,
    "Premise\n2040",
    2045,
])
ax.set_yticks(range(0, 26000, 2000))

ax.grid(axis='y')

ax.set_xlabel("Year")
ax.set_ylabel("Amount")
ax.set_title("Stacked Waterfall by Year")
ax.axhline(0, color="black", linewidth=0.8)

plt.tight_layout()
plt.savefig("results/bw_timex_example.pdf")