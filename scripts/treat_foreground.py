#!/usr/bin/env -S PYTHONPATH=${PWD} uv run

import os
import click

from scripts.method_selector import MenuApp
from src import setup_project
from src.utils.utils import set_logging_level, load_tuple_file
from src.acts.foreground import get_reference_flow
from src.impacts.contribution import compute_impacts
from src.impacts.monte_carlo import stoch_impacts

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
@click.option("-v", "--verbose", count=True, help="Increase verbosity (-v, -vv, -vvv)")
def run_lca(input_files, cdb_path, output_folder, method_file, verbose):
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
    setup_project(cdb_path, 'ECS-LCA')
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
        df_stoch = stoch_impacts(reference_flow, meth, n = 2**8)

        df_stoch.to_csv(stoch_path)
        click.echo(f"Saved: {stoch_path}")


if __name__ == "__main__":
    run_lca()
