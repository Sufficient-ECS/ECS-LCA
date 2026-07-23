#!/usr/bin/env -S PYTHONPATH=${PWD} uv run 

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import seaborn as sns
import numpy as np

results_dir = Path("./results")

dfs = []
for year in (2020, 2030, 2040, 2050):
    fp = next(
        results_dir.glob(
            f"ei_cutoff_3.*_remind_SSP1-NPi_{year} *_foreground_impacts.csv"
        )
    )

    df = pd.read_csv(fp, index_col=0)
    df["year"] = year
    dfs.append(df)

df = pd.concat(dfs)


# If the index contains the foreground names
df = df.reset_index(names="foreground")

# Pivot so rows = foreground, columns = year
pivot = df.pivot(index="foreground",
                 columns="year",
                 values="IPCC 2013 - climate change[kg CO2-Eq]")

years = pivot.columns.tolist()
groups = [
    "butanols production,\nhydroformylation of propylene\n- RoW - 1kg",
    "1,1-difluoroethane production\n- US - 1kg",
    ]

# Positions
x = np.arange(len(groups))
width = 0.18

fig, ax = plt.subplots(figsize=(8, 5))

# Plot one bar per year within each group
for i, year in enumerate(years):
    offset = (i - (len(years)-1)/2) * width
    ax.barh(
        x - offset,
        pivot[year],
        height=width,
        label=str(year)
    )

ax.set_yticks(x)
ax.set_yticklabels(groups)

ax.set_xlabel("kg CO2-Eq")

ax.grid(axis="x", linestyle="--")
ax.set_title("IPCC 2013 - climate change, GWP 100")
ax.legend(title="Year")

plt.tight_layout()
plt.savefig("./results/premise_example.pdf")