#!/usr/bin/env -S PYTHONPATH=${PWD} uv run

import os
import click
import lca_algebraic as agb

from scripts.method_selector import MenuApp
from src import setup_project
from src.ei_access import EI_Access
from src.utils.utils import set_logging_level, load_tuple_file
from src.utils.db import make_main_tech
from src.acts.foreground import get_reference_flow
from src.impacts.contribution import compute_impacts
from src.impacts.monte_carlo import stoch_impacts

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
@click.option("-s", "--scenario_file", default=None, help="File of premise scenarios used")
@click.option("-v", "--verbose", count=True, help="Increase verbosity (-v, -vv, -vvv)")
def run_lca(input_files, cdb_path, output_folder, method_file, scenario_file, verbose):
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

    # Setup project
    setup_project(cdb_path, 'ECS-LCA', scenario_file)
    # Ensure output directory exists
    os.makedirs(output_folder, exist_ok=True)

    for filepath in input_files:
        click.echo(f"Processing {filepath}...")

        # Build output filenames
        base_name = os.path.splitext(os.path.basename(filepath))[0]
        impacts_path = os.path.join(output_folder, f"{base_name}_impacts.csv")
        stoch_path = os.path.join(output_folder, f"{base_name}_stochastic.csv")

        # Get reference flow
        reference_flow = get_reference_flow(filepath)
        
        # Deterministic impacts
        df_impacts = compute_impacts(reference_flow, meth)
        df_impacts.to_csv(impacts_path)
        click.echo(f"Saved: {impacts_path}")

        # Stochastic impacts
        try:
            df_stoch = stoch_impacts(reference_flow, meth, n = 2**8)

            df_stoch.to_csv(stoch_path)
            click.echo(f"Saved: {stoch_path}")
        except Exception as e:
            click.echo(f"Could not run stochastic, likely because no random variable, {e}")

        if scenario_file != None:
            scenarios_tuple = load_tuple_file(scenario_file, sep=',')

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
                click.echo(f"Saved: {impacts_path}")

                try:
                    df_stoch = stoch_impacts(reference_flow, meth, n = 2**8)
                    df_stoch.to_csv(stoch_path)
                    click.echo(f"Saved: {stoch_path}")
                except Exception as e:
                    click.echo(f"Could not run stochastic, likely because no random variable, {e}")

            make_main_tech()

if __name__ == "__main__":
    run_lca()
