#!/usr/bin/env -S PYTHONPATH=${PWD} uv run 

import os
import click
import re
import bw2data as bd
import yaml

CONFIG_FILE = ".cache/access.yaml"


def config_exists():
    return os.path.exists(CONFIG_FILE)


def read_existing_config():
    if not config_exists():
        return {}

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        content = yaml.safe_load(f)

    return content


def write_config(data):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f)


def reset_brightway_project():
    click.echo("\n🔄 Resetting Brightway project...")

    if "ECS-LCA-1" in bd.projects:
        bd.projects.delete_project(name='ECS-LCA-1', delete_dir=True)

    OS_database = "OS database"

    from ecs_lca import setup_project
    setup_project([], 'ECS-LCA-1')

    click.echo("✅ Project successfully rebuilt.\n")


@click.command()
def main():
    click.echo("=== EI Access Configuration ===")

    existing = read_existing_config() if config_exists() else {}

    version_changed = False
    model_changed = False

    if existing:
        click.echo("Existing configuration found.\n")

        # 1. Définir les descriptions d'aide pour chaque option
        help_text = (
            "\nAvailable choices description:\n"
            "  all           - Update every single configuration setting\n"
            "  credentials   - ecoinvent: Update API keys, usernames, or password\n"
            "  database_path - ecoinvent: Change the path for a local database\n"
            "  version       - ecoinvent: Change version (e.g. 3.12)\n"
            "  model         - ecoinvent: Change model (e.g. cutoff)\n"
            "  imec          - imec.netzero: set credentials and URLs\n"
            "  premise       - premise: Add decryption key\n"
            "  nothing       - Exit without making any changes\n"
        )

        # 2. Boucler pour permettre d'afficher l'aide sans quitter l'invite
        while True:
            change = click.prompt(
                "What do you want to change? (type 'help' for details)",
                type=click.Choice(
                    ["all", "credentials", "database_path", "version", "model", "imec", "premise", "nothing", "help"]
                ),
                default="help",
            )

            if change != "help":
                break
            
            click.echo(help_text)


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

    if not existing or change in ["all", "premise"]:
        data["premise_decryption_key"] = click.prompt("Premise decryption key (string)")

    # --- Model ---
    if not existing or change in ["all", "imec"]:
        use_imec_net_zero = click.confirm("Do you want to use imec net zero?")
        data["use_imec_net_zero"] = use_imec_net_zero
        if click.confirm("Do you want to update credentials?"):
            data["api_id"] = click.prompt("API Client ID (string)")
            data["client_id"] = click.prompt("Client ID (string)")
            data["client_secret"] = click.prompt("Client secret (string)")
            data["imec_custom_db_path"] = click.prompt("Path to imec databases")
            data["tenant_id"] = click.prompt("Tenant ID (string)")
            data["api_base_url"] = click.prompt("API base url (string)")

    write_config(data)

    click.echo("\n✅ Configuration saved successfully!")

    # --- Trigger project reset if needed ---
    if not existing or version_changed or model_changed:
        reset_brightway_project()


if __name__ == "__main__":
    main()