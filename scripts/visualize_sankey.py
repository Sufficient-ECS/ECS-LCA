#!/usr/bin/env -S PYTHONPATH=${PWD} uv run 

#README
#

import bw2calc
import bw2data
try:
    from bw2data.backends.peewee import Activity
except ImportError:
    from bw2data.backends import Activity
import click
from d3blocks import D3Blocks
from io import StringIO
import json
from pandas import DataFrame
import pandas as pd
from polyviz.dataframe import find_downstream_emissions
from polyviz.utils import check_filepath, identify_waste_process
from packaging.version import Version
from src.utils.utils import find_activity
from typing import List, Optional


def ECS_LCA_CUSTOM_recursive_calculation(
    activity,
    lcia_method,
    amount=1,
    max_level=3,
    cutoff=1e-2,
    lca_obj=None,
    total_score=None,
    level=0,
    previous_activity=None,
    db_to_highlight= None,
    results=None,
):
    """
    ADAPTED FROM POLIVYZ, UTILS, recursive_calculation
    Modificaton highlighted with the #ECS_LCA_CUSTOM comment

    ADAPTED FROM BRIGHTWAY2-ANALYZER:
    https://github.com/brightway-lca/brightway2-analyzer/blob/0d2b14a13d631cba7537793670ea87361b349c64/bw2analyzer/utils.py#L88

    Traverse a supply chain graph, and calculate the LCA scores of each component.
    Return the results as a list of lists.

    Args:
        activity: ``Activity``. The starting point of the supply chain graph.
        lcia_method: tuple. LCIA method to use when traversing supply chain graph.
        amount: int. Amount of ``activity`` to assess.
        max_level: int. Maximum depth to traverse.
        cutoff: float. Fraction of total score to use as cutoff when deciding whether to traverse deeper.
        lca_obj: ``LCA``. Internal argument (used during recursion, do not touch).
        total_score: float. Internal argument (used during recursion, do not touch).
        level: int. Internal argument (used during recursion, do not touch).
        #ECS_LCA_CUSTOM db_to_highlight dictionnary with database to highlight in the sankey
    Internal args (used during recursion, do not touch);
        level: int.
        lca_obj: ``LCA``.
        total_score: float.
        first: bool.

    Returns:
        A list of lists, where each list is a row in the output table.

    """

    if lca_obj is None:
        lca_obj = bw2calc.LCA({activity: amount}, lcia_method)
        lca_obj.lci()
        lca_obj.lcia()
        total_score = lca_obj.score
        results = []
    elif total_score is None:
        raise ValueError
    elif total_score == 0:
        return results
    else:
        bw2calc_version = (
            ".".join(map(str, bw2calc.__version__))
            if isinstance(bw2calc.__version__, tuple)
            else bw2calc.__version__
        )
        if Version(bw2calc_version) >= Version("2.0.DEV1") and not getattr(
            lca_obj, "_remapped", False
        ):
            lca_obj.remap_inventory_dicts()
        lca_obj.redo_lcia({activity: amount})
        if abs(lca_obj.score) <= abs(total_score * cutoff):
            results.append(
                [
                    level,
                    lca_obj.score / total_score,
                    lca_obj.score,
                    float(amount),
                    "activities below cutoff",
                    None,
                    None,
                    ("Undefined",None), #ECS_LCA_CUSTOM, key to label each node with its database as key contain (database,UUID)
                ]
            )
            return results

    if (
        activity["name"],
        activity["reference product"],
        activity["location"],
    ) == previous_activity:
        results.append(
            [
                level,
                lca_obj.score / total_score,
                lca_obj.score,
                float(amount),
                "loss",
                None,
                None,
                activity.key, #ECS_LCA_CUSTOM, key to label each node with its database as key contain (database,UUID)
            ]
        )
        return results

    results.append(
        [
            level,
            lca_obj.score / total_score,
            lca_obj.score,
            float(amount),
            activity["name"],
            activity["location"],
            activity["unit"],
            activity.key, #ECS_LCA_CUSTOM, key to label each node with its database as key contain (database,UUID)
        ]
    )
    if activity.key[0] in db_to_highlight and level<max_level:  #ECS_LCA_CUSTOM, limit the iteration on the activities in the database we want to highlight
        for exc in activity.technosphere():
            ECS_LCA_CUSTOM_recursive_calculation(
                activity=exc.input,
                lcia_method=lcia_method,
                amount=amount * exc["amount"],
                max_level=max_level,
                cutoff=cutoff,
                lca_obj=lca_obj,
                total_score=total_score,
                level=level + 1,
                previous_activity=(
                    activity["name"],
                    activity["reference product"],
                    activity["location"],
                ),
                db_to_highlight= db_to_highlight,
                results=results,
            )

    return results

def ECS_LCA_CUSTOM_calculate_supply_chain(
    activity: Activity,
    method: tuple,
    level: int = 3,
    cutoff: float = 0.01,
    amount: int = 1,
    db_to_highlight: dict[str, str] = None,
) -> [StringIO, int]:
    """
    ADAPTED FROM POLIVYZ, UTILS, calculate_supply_chain
    Modificaton highlighted with the #ECS_LCA_CUSTOM comment
    
    Calculate the supply chain of an activity.
    :param activity: a brightway2 activity
    :param method: a tuple representing a brightway2 method
    :param level: the maximum level of the supply chain
    :param cutoff: the cutoff value for the supply chain
    :return: a StringIO object and the reference amount
    """

    assert isinstance(activity, Activity), "`activity` should be a brightway2 activity."

    amount = amount * -1 if identify_waste_process(activity) else amount

    print("Calculating supply chain score...")

    try:
        results = ECS_LCA_CUSTOM_recursive_calculation(
            activity,
            method or list(bw2data.methods)[0],
            cutoff=cutoff,
            max_level=level,
            amount=amount,
            db_to_highlight=db_to_highlight #ECS_LCA_CUSTOM
        )
    except ZeroDivisionError as err:
        raise ZeroDivisionError(
            "Could not compute the recursive calculation because "
            "one of the flows has a null impact value."
        ) from err

    return results, amount

def ECS_LCA_CUSTOM_format_supply_chain_dataframe(
    results: List[List], amount: int = 1, flow_type: str = None
) -> pd.DataFrame:
    """
    ADAPTED FROM POLIVYZ, datatframe, format_supply_chain_dataframe
    Modificaton highlighted with the #ECS_LCA_CUSTOM comment

        
    Format the result of the recursive calculation into a pandas dataframe.
    :param result: string containing the result of the recursive calculation
    :param amount: reference amount
    :param flow_type: if not None, only keep flows with a matching unit
    :return: a pandas dataframe
    """

    list_res = []
    last_supplier = {}

    for result in results:
        level, _, impact, amount, name, location, unit, key= result
        last_supplier[level] = f"{name} ({location})"

        db_name=key[0]

        if not flow_type:
            list_res.append(
                [
                    f"{name} ({location})" if location else name,
                    f"{name} ({location})" if level == 0 else last_supplier[level - 1],
                    impact,
                    level,
                    db_name, #ECS_LCA_CUSTOM: add db_name to each node
                ]
            )
        else:
            if unit == flow_type:
                list_res.append(
                    [
                        f"{name} ({location})" if location else name,
                        (
                            f"{name} ({location})"
                            if level == 0
                            else last_supplier[level - 1]
                        ),
                        amount,
                        level,
                        db_name, #ECS_LCA_CUSTOM: add db_name to each node
                    ]
                )

    dataframe = pd.DataFrame(list_res, columns=["source", "target", "weight", "level","db_name"]) #ECS_LCA_CUSTOM: add db_name to each node
    dataframe = dataframe.replace("market for", "m. for", regex=True)
    dataframe = dataframe.replace("market group for", "m. gr. for", regex=True)

    # sum duplicate rows
    dataframe = dataframe.groupby(["source", "target", "level"]).sum().reset_index()

    # reorder by level and target
    dataframe = dataframe.sort_values(by=["level", "target"])

    # remove negative values
    if amount > 0:
        dataframe = dataframe[dataframe["weight"] > 0]
    else:
        dataframe.loc[dataframe["weight"] < 0, "weight"] *= -1

    #ECS_LCA_CUSTOM: add "other_activities_and_emissions" to fill the gaps in the various level of the sankey as we didn't stop at the same level for each activity
    #This is used because the emissions in POLIVYZ are added to fill the gaps.
    if not flow_type:
        for level in dataframe["level"].unique():
            for i, row in dataframe.loc[dataframe["level"] == level].iterrows():
                if (
                    row["source"]
                    not in ["loss", "activities below cutoff", "emissions","other_activities_and_emissions"] #ECS_LCA_CUSTOM
                    and level + 1 in dataframe["level"].unique()
                ):
                    if len(dataframe.loc[(dataframe["level"] == level + 1) & (dataframe["target"] == row["source"])])==0: #ECS_LCA_CUSTOM
                        dataframe = pd.concat(
                            [
                                dataframe,
                                pd.DataFrame(
                                    {
                                        "source": "other_activities_and_emissions", #ECS_LCA_CUSTOM
                                        "target": row["source"],
                                        "weight": row["weight"],
                                        "level": level + 1,
                                        "db_name": "other_databases", #ECS_LCA_CUSTOM
                                    },
                                    index=[0],
                                ),
                            ],
                            ignore_index=True,
                        )
                    elif len(dataframe.loc[(dataframe["target"] == row["source"]) & (dataframe["level"] == level + 1) & (dataframe["source"] == "other_activities_and_emissions")])!=0: #ECS_LCA_CUSTOM
                        dataframe.loc[
                            (dataframe["target"] == row["source"]) & (dataframe["level"] == level + 1) & (dataframe["source"] == "other_activities_and_emissions"), "weight" #ECS_LCA_CUSTOM
                        ]+= row["weight"]

        # reorder by level and target
        dataframe = dataframe.sort_values(by=["level", "target"])
        
    # add rows representing emissions
    if not flow_type:
        for level in dataframe["level"].unique():
            for i, row in dataframe.loc[dataframe["level"] == level].iterrows():
                if (
                    row["source"]
                    not in ["loss", "activities below cutoff", "emissions","other_activities_and_emissions"]
                    and level + 1 in dataframe["level"].unique()
                ):
                    sum_emissions = row["weight"]
                    downstream_emissions = find_downstream_emissions(
                        dataframe, row["source"], level
                    )

                    if downstream_emissions < sum_emissions:
                        # insert a row with the missing emissions
                        dataframe = pd.concat(
                            [
                                dataframe,
                                pd.DataFrame(
                                    {
                                        "source": "emissions",
                                        "target": row["source"],
                                        "weight": sum_emissions - downstream_emissions,
                                        "level": level + 1,
                                    },
                                    index=[0],
                                ),
                            ],
                            ignore_index=True,
                        )

        # reorder by level and target
        dataframe = dataframe.sort_values(by=["level", "target"])

    # drop the `level` column
    dataframe = dataframe.drop(labels="level", axis=1)

    return dataframe




def ECS_LCA_CUSTOM_sankey(
    activity: Activity,
    db_to_highlight: dict[str, str],
    method: tuple = None,
    flow_type: str = None,
    amount: int = 1,
    level: int = 3,
    cutoff: float = 0.01,
    relative_contribution_label_cutoff: float = 0.0,
    filepath: str = None,
    title: str = None,
    notebook: bool = False,
    labels_swap: dict = None,
    figsize: tuple = None,
) -> Optional[tuple[str, DataFrame]]:
    """
    ADAPTED FROM POLIVYZ, sankey, sankey

    Recreates the Sankey using D3Blocks built-in property setters.
    """

    if level < 2:
        raise ValueError("The level of recursion should be at least 2.")

    title = title or f"{activity['name']} ({activity['unit']}, {activity['location']})"
    filepath = check_filepath(filepath, title, "sankey", method, flow_type)

    # 1. Calculate and format data
    result, amount = ECS_LCA_CUSTOM_calculate_supply_chain(
        activity=activity, method=method, level=level, cutoff=cutoff, amount=amount,db_to_highlight=db_to_highlight #ECS_LCA_CUSTOM
    )

    if method:
        dataframe = ECS_LCA_CUSTOM_format_supply_chain_dataframe(result, amount)
        unit = bw2data.Method(method).metadata["unit"]
    else:
        dataframe = ECS_LCA_CUSTOM_format_supply_chain_dataframe(result, amount, flow_type)
        unit = flow_type

    dataframe["unit"] = unit
    if len(dataframe) < 3:
        print("Not enough data to generate a Sankey diagram. Attention, this script can't be used for actities that are not stored in the database that you seek to highlight")
        return

    if labels_swap:
        dataframe = dataframe.replace(labels_swap, regex=True)


    # 2. Initialize D3Blocks specifically for Sankey
    d3 = D3Blocks(chart='Sankey', frame=True)
    
    # Define working data (excluding the root row if polyviz standard requires it)
    df_working = dataframe[1:].copy()

    # 3. Helper functions for label cleaning
    def shorten_label_V1(s: str) -> str:
        s = s.replace("market for", "m. for")
        s = s.replace("market group for", "m. gr. for")
        return s

    def shorten_label_V2(s: str) -> str:
        s = shorten_label_V1(s)
        s = s.replace(" ", "_")
        return s

    # 4. Determine Properties
    unique_nodes = list(set(df_working['source'].unique()) | set(df_working['target'].unique()))

    node_colors = {}
    node_labels = {}
    node_fontsize = {}
    total_weight = df_working['weight'].sum()

    database_act_list_dic={}
    for database_name, hex_color in db_to_highlight.items():
        database_act_list_dic[database_name]=[row['source'] for _,row in df_working.iterrows() if row['db_name']==database_name]

    for node in unique_nodes:
        clean_node_name = shorten_label_V2(node)
        
        # Default visuals
        chosen_color = "#D3D3D3"
        is_highlight = False
        
        # Check node against highlight dictionary
        for database_name, hex_color in db_to_highlight.items():
            database_act_list=database_act_list_dic[database_name]
            if node in database_act_list:
                chosen_color = hex_color
                is_highlight = True
                break
        
        node_colors[node] = chosen_color
        
        # Label Formatting: Bold if it's a highlight
        #current_label = f"<b>{clean_node_name}</b>" if is_highlight else clean_node_name
        current_label = clean_node_name if is_highlight else clean_node_name

        # Visibility Logic based on contribution
        node_weight = df_working[(df_working['source'] == node) | (df_working['target'] == node)]['weight'].sum()
        
        if is_highlight:
            node_fontsize[clean_node_name] = 14
            node_labels[clean_node_name] = current_label
        elif (node_weight / total_weight) < relative_contribution_label_cutoff:
            node_fontsize[clean_node_name] = 0
            node_labels[clean_node_name] = clean_node_name # Keep unique name to avoid ID errors
        else:
            node_fontsize[clean_node_name] = 10
            node_labels[clean_node_name] = clean_node_name

    # 5. Apply properties using D3Blocks methods
    # First set colors based on original node names
    d3.set_node_properties(df_working, color=node_colors)
    
    # Update visual properties using the cleaned labels as keys
    for clean_name, fs in node_fontsize.items():
        d3.node_properties.loc[d3.node_properties['label'] == clean_name, 'fontsize'] = fs

    for clean_name, lbl in node_labels.items():
        d3.node_properties.loc[d3.node_properties['label'] == clean_name, 'label'] = lbl

    # Set edge properties to follow the target color for consistency
    d3.set_edge_properties(df_working, color='target', opacity=0.4)

    # 6. Show/Save
    # Passing figsize and title through config
    d3.config['figsize'] = figsize or (800, 600)
    d3.config['title'] = title
    d3.config['notebook'] = notebook

    d3.show(filepath=filepath)

    return str(filepath), dataframe

class TupleParamType(click.ParamType):
    name = "tuple"

    def convert(self, value, param, ctx):
        # Remove parentheses if present, then split by comma
        clean_value = value.replace("'", "").replace('"', "")
        parts = [p.strip() for p in clean_value.split(",")]
        return tuple(parts)


@click.command()
@click.option("--act_name", required=True, help="Exact name of the activity")
@click.option("--act_location", required=False, help="Location of the activity")
@click.option("--act_db", required=True, help="Name of the Brightway database")
@click.option(
    "--method", 
    type=TupleParamType(), 
    help="LCIA method (e.g., 'ecoinvent-3.11,EF v3.1,climate change,global warming potential (GWP100)')"
)
@click.option("--db_highlighted", help="JSON string of dbs to highlight (e.g., {'OS_database':'green'})")
@click.option("--cutoff", default=0.01, type=float, help="Contribution cutoff")
@click.option("--level", default=3, type=int, help="Recursion level")
@click.option("--figsize", default="(800, 600)", type=str, help="Figure size for the Sankey diagram (tuple in string format, e.g., '(1200,600)')")
    
def main(act_name, act_location,act_db, method, db_highlighted, cutoff, level, figsize):
    """
    CLI to generate a Custom Supply Chain Sankey for a Brightway activity.
    """
    # 1. Setup Brightway Project
    from src import setup_project
    setup_project("yaml/custom", 'ECS-LCA')

    # 2. Retrieve the Activity
    activity = find_activity(act_name, act_location, act_db)
    # 3. Parse inputs
    
    if figsize:
        # This regex/string clean handles: (1200,600), "1200,600", or (1200, 600)
        clean_str = figsize.replace("(", "").replace(")", "").replace(" ", "").replace("'", "").replace('"', "")
        try:
            width, height = map(int, clean_str.split(','))
            figsize_tuple = (width, height)
        except ValueError:
            click.echo("Error: --figsize must be in format '(1200,600)'")
            return
    else:
        figsize_tuple = None

    try:
        highlight_dict = json.loads(db_highlighted) if db_highlighted else {}
        # Extract just the database names (the keys)
    except json.JSONDecodeError:
        click.echo("Error: --db_highlighted must be a valid JSON string (e.g., '{\"OS_database\": \"green\"}')")
        return

    # 4. Generate Sankey
    click.echo(f"Generating Sankey for: {act_name}...")
    ECS_LCA_CUSTOM_sankey(
        activity=activity,
        db_to_highlight=highlight_dict if highlight_dict else None,
        method=method,
        level=level,
        cutoff=cutoff,
        notebook=False,
        figsize=figsize_tuple,
    )
    click.echo("Done.")

if __name__ == "__main__":
    main()