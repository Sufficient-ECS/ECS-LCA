#!/usr/bin/env -S PYTHONPATH=${PWD} uv run 

import click
import pandas as pd
import yaml
from pathlib import Path


def safe_float(val):
    if pd.isna(val):
        return None
    if isinstance(val, str):
        val = val.replace(",", ".")
    try:
        return float(val)
    except ValueError:
        return None


def choose_sheets(file_path):
    """Ask user to select sheet(s) if multiple exist"""
    xls = pd.ExcelFile(file_path)
    sheets = xls.sheet_names

    if len(sheets) == 1:
        return sheets

    click.echo("Multiple sheets detected:")
    for i, name in enumerate(sheets):
        click.echo(f"{i}: {name}")

    choice = click.prompt(
        "Enter sheet indices or names (comma-separated)",
        type=str
    )

    selected = []
    for item in choice.split(","):
        item = item.strip()
        if item.isdigit():
            selected.append(sheets[int(item)])
        else:
            selected.append(item)

    return selected


def read_input_file(file_path):
    suffix = Path(file_path).suffix.lower()

    if suffix in [".xls", ".xlsx"]:
        selected_sheets = choose_sheets(file_path)
        dfs = [pd.read_excel(file_path, sheet_name=s) for s in selected_sheets]
        return pd.concat(dfs, ignore_index=True)

    elif suffix == ".csv":
        try:
            return pd.read_csv(file_path)
        except Exception:
            return pd.read_csv(file_path, sep=";")

    else:
        raise ValueError(f"Unsupported file type: {suffix}")


@click.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.argument("output_file", type=click.Path())
@click.option("--key", required=True, help="Column to use as input key")
@click.option("--value", required=False, help="Column for quantity value")
@click.option("--unit", required=False, help="Column for unit")
@click.option("--act_name", required=False, help="Column for activity name")
@click.option("--loc", required=False, help="Column for location")
@click.option("--dmin", required=False, help="Column for minimum of uncertainty")
@click.option("--dmax", required=False, help="Column for maximum of uncertainty")
@click.option("--dstd", required=False, help="Column for std of uncertainty")
@click.option("--distrib", required=False, help="Column for distribution of uncertainty")
def main(input_file, output_file, key, value, unit, act_name, loc, dmin, dmax, dstd, distrib):
    df = read_input_file(input_file)

    product_name = Path(input_file).stem

    inputs = {}
    commented_inputs = []

    for _, row in df.iterrows():
        k = str(row.get(key, "")).strip()
        if not k:
            continue

        entry = {}
        should_comment = False

        # VALUE
        if value:
            v = safe_float(row.get(value))
            if v is None:
                should_comment = True
            entry.setdefault("amount", {})["value"] = v if v is not None else 0
        else:
            entry.setdefault("amount", {})["value"] = 0

        # UNIT
        if unit:
            u = row.get(unit)
            if pd.isna(u):
                should_comment = True
            entry["amount"]["unit"] = u if pd.notna(u) else None

        # ACTIVITY NAME
        if act_name:
            act = row.get(act_name)
            if pd.isna(act):
                should_comment = True
            else:
                entry["act_name"] = act

        # LOCATION
        if loc:
            l = row.get(loc)
            if pd.isna(l):
                should_comment = True
            else:
                entry["location"] = l

        if distrib or dmin or dmax or dstd:
            entry["uncertainty"] = {}

        if distrib:
            l = row.get(distrib)
            if not pd.isna(l):
                entry["uncertainty"]["distribution"] = l

        if dmin:
            l = row.get(dmin)
            if not pd.isna(l):
                entry["uncertainty"]["min"] = l
        if dmax:
            l = row.get(dmax)
            if not pd.isna(l):
                entry["uncertainty"]["max"] = l
        if dstd:
            l = row.get(dstd)
            if not pd.isna(l):
                entry["uncertainty"]["std"] = l

        # Store
        if should_comment:
            commented_inputs.append((k, entry))
        else:
            inputs[k] = entry

    output_data = {
        "output": {
            "product": product_name,
            "amount": {
                "value": 1,
                "unit": "unit",
            },
        },
        "inputs": inputs,
    }

    yaml_str = yaml.dump(output_data, sort_keys=False, allow_unicode=True)

    # Add commented entries
    if commented_inputs:
        yaml_str += "\n"
        for k, entry in commented_inputs:
            block = yaml.dump({k: entry}, sort_keys=False)
            commented_block = "\n".join(
                f"# {line}" for line in block.split("\n") if line
            )
            yaml_str += commented_block + "\n"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(yaml_str)


if __name__ == "__main__":
    main()