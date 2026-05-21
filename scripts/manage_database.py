#!/usr/bin/env -S PYTHONPATH=${PWD} uv run 

import os
import click
import re
import bw2data as bd

CONFIG_FILE = "src/ei_access/__init__.py"


def config_exists():
    return os.path.exists(CONFIG_FILE)


def read_existing_config():
    if not config_exists():
        return {}

    with open(CONFIG_FILE, "r") as f:
        content = f.read()

    def extract(field):
        match = re.search(rf"self\.{field}\s*=\s*(.*)", content)
        if match:
            value = match.group(1).strip()
            return value.strip('"') if value != "None" else None
        return None

    return {
        "version": extract("version"),
        "system_model": extract("system_model"),
        "path": extract("path"),
        "username": extract("username"),
        "password": extract("password"),
    }


def write_config(data):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

    content = f'''class EI_Access:
    def __init__(self):

        self.version = "{data.get("version")}"
        self.system_model = "{data.get("system_model")}"

        # Fill if you have a local database
        self.path = "{data.get("path")}"

        # Fill if you want to download the database
        self.username = "{data.get("username")}"
        self.password = "{data.get("password")}"
'''

    with open(CONFIG_FILE, "w") as f:
        f.write(content)


def reset_brightway_project():
    click.echo("\n🔄 Resetting Brightway project...")

    if "ECS-LCA" in bd.projects:
        bd.projects.delete_project(name='ECS-LCA', delete_dir=True)

    OS_database = "OS database"

    from src import setup_project
    setup_project("yaml/custom", 'ECS-LCA')

    click.echo("✅ Project successfully rebuilt.\n")


@click.command()
def main():
    click.echo("=== EI Access Configuration ===")

    existing = read_existing_config() if config_exists() else {}

    version_changed = False
    model_changed = False

    if existing:
        click.echo("Existing configuration found.\n")

        change = click.prompt(
            "What do you want to change?",
            type=click.Choice(
                ["all", "credentials", "database_path", "version", "model", "nothing"]
            ),
            default="all",
        )

        if change == "nothing":
            click.echo("No changes made.")
            return

        data = existing.copy()
    else:
        click.echo("First-time setup.\n")
        data = {}

    # --- Access type ---
    if not existing or change in ["all", "credentials", "database_path"]:
        mode = click.prompt(
            "Use credentials or local database?",
            type=click.Choice(["credentials", "local"]),
        )

        if mode == "credentials":
            data["username"] = click.prompt("Username")
            data["password"] = click.prompt("Password", hide_input=True)
            data["path"] = None
        else:
            data["path"] = click.prompt("Path to local database")
            data["username"] = None
            data["password"] = None

    # --- Version ---
    if not existing or change in ["all", "version"]:
        new_version = click.prompt("Database version (string)")
        if existing and new_version != existing.get("version"):
            version_changed = True
        data["version"] = new_version

    # --- Model ---
    if not existing or change in ["all", "model"]:
        new_model = click.prompt("System model (string)")
        if existing and new_model != existing.get("system_model"):
            model_changed = True
        data["system_model"] = new_model

    write_config(data)

    click.echo("\n✅ Configuration saved successfully!")

    # --- Trigger project reset if needed ---
    if not existing or version_changed or model_changed:
        reset_brightway_project()


if __name__ == "__main__":
    main()