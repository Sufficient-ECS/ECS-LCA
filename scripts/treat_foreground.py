#!/usr/bin/env -S PYTHONPATH=${PWD} uv run

import os
import re
from datetime import datetime
from pathlib import Path

import click
import lca_algebraic as agb
from tqdm import tqdm

from scripts.method_selector import MenuApp
from src import FG_DB, setup_project
from src.acts.foreground import clean_reference_flow, get_reference_flow
from src.ei_access import EI_Access
from src.impacts.contribution import compute_impacts
from src.impacts.monte_carlo import stoch_impacts
from src.impacts.temporal import compute_temp_impacts
from src.utils.db import make_main_tech
from src.utils.utils import load_tuple_file, set_logging_level

ei_acc = EI_Access()

@click.command()
@click.argument("input_files", nargs=-1, type=click.Path(exists=True))
@click.option(
    "-c",
    "--cdb_path",
    multiple=True,
    type=click.Path(exists=True),
    help="Custom database paths. Can be given multiple times.",
)
@click.option("-o", "--output_folder", default="./results", help="Output folder for results")
@click.option("-m", "--method_file", default="./results/method_list.txt", help="File of impact methods used")
@click.option("-p", "--premise_scenario_file", default=None, help="File of premise scenarios used for static LCA")
@click.option("-t", "--timex_scenario_file", default=None, help="File of premise scenarios used for Timex")
@click.option("-i", "--index", default=1, help="Project index")
@click.option("-e", "--existing", default=False, help="If present, only treat elements without an existing result")
@click.option("-v", "--verbose", count=True, help="Increase verbosity (-v, -vv, -vvv)")
def run_lca(input_files, cdb_path, output_folder, method_file, premise_scenario_file, timex_scenario_file, index, existing, verbose):
    """
    Run LCA impacts on one or multiple YAML foreground files.
    """

    if not os.path.isfile(method_file):
        MenuApp(method_file).run()

    meth = load_tuple_file(method_file, sep=',')

    if len(meth) == 0:
        raise ValueError("Selected at least one impact method. Please run method_selector.py to regenerate file.")

    set_logging_level(verbose)
    if not input_files:
        raise click.UsageError("You must provide at least one input file.")

    # Ensure output directory exists
    os.makedirs(output_folder, exist_ok=True)

    output_folder = Path(output_folder)

    setup_project(cdb_path, f"ECS-LCA-{index}", [premise_scenario_file, timex_scenario_file])

    for filepath in tqdm(input_files, position=index):
        # Build output filenames
        base_name = Path(filepath).stem
        impacts_path = output_folder / f"{base_name}_impacts.csv"
        stoch_path = output_folder / f"{base_name}_stochastic.csv"

        lock_path = impacts_path.with_suffix(".lock")
        if existing:
            # Already completed
            if impacts_path.exists():
                continue

            # Atomically claim this input
            try:
                lock_path.touch(exist_ok=False)
            except FileExistsError:
                continue

        # Get reference flow
        reference_flow = get_reference_flow(filepath)

        # Deterministic impacts
        df_impacts = compute_impacts(reference_flow, meth)
        df_impacts.to_csv(impacts_path)

        # Stochastic impacts
        try:
            df_stoch = stoch_impacts(reference_flow, meth, n = 2**8)

            df_stoch.to_csv(stoch_path)
        except Exception as e:
            click.echo(f"Could not run stochastic, likely because no random variable, {e}")

        if timex_scenario_file != None:
            scenarios_tuple = load_tuple_file(timex_scenario_file, sep=',')
            name = (
                f"ei_{ei_acc.system_model}_{ei_acc.version}_{scenarios_tuple[0][0]}_{scenarios_tuple[0][1]}"
            )
            filtered = [
                db for db in agb.database.list_databases().index
                if db.startswith(name)
            ]
            filtered.sort()

            year_to_db = {
                db : datetime.strptime(re.search(r"_(\d{4})", db).group(1), "%Y")
                for db in filtered
            }

            make_main_tech(filtered[0])

            time_path = os.path.join(output_folder, f"{base_name}_temp_time.csv")
            metrics_path = os.path.join(output_folder, f"{base_name}_temp_metrics.csv")

            time_data, metrics_data = compute_temp_impacts(reference_flow, meth, year_to_db, meth)

            time_data.to_csv(time_path)
            click.echo(f"Saved: {time_path}")

            metrics_data.to_csv(metrics_path)
            click.echo(f"Saved: {metrics_path}")

            make_main_tech()

        if premise_scenario_file != None:
            scenarios_tuple = load_tuple_file(premise_scenario_file, sep=',')

            filtered = []
            for sc in scenarios_tuple:
                name = (
                    f"ei_{ei_acc.system_model}_{ei_acc.version}_{sc[0]}_{sc[1]}_{sc[2]}"
                )
                filtered.append(next((s for s in agb.database.list_databases().index if s.startswith(name)), None))


            for db in filtered:
                click.echo(f"Computing for database {db}")

                impacts_path = os.path.join(output_folder, f"{db}_{base_name}_impacts.csv")
                stoch_path = os.path.join(output_folder, f"{db}_{base_name}_stochastic.csv")

                make_main_tech(db)

                df_impacts = compute_impacts(reference_flow, meth)
                df_impacts.to_csv(impacts_path)

                try:
                    df_stoch = stoch_impacts(reference_flow, meth, n = 2**8)
                    df_stoch.to_csv(stoch_path)
                except Exception as e:
                    click.echo(f"Could not run stochastic, likely because no random variable, {e}")   

            make_main_tech()
        clean_reference_flow(reference_flow)
        agb.params.resetParams(FG_DB)
        if existing:
            lock_path.unlink(missing_ok=True)

if __name__ == "__main__":
    run_lca()
