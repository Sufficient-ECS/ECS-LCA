from pathlib import Path
import yaml


class EI_Access:
    def __init__(self, path=".cache/access.yaml"):
        access_file = Path(path)

        if not access_file.exists():
            logging.warning("Please run manage_database to setup credentials.")
            return

        with access_file.open("r") as f:
            data = yaml.safe_load(f) or {}

        if not isinstance(data, dict):
            raise ValueError(f"{path} must contain a YAML mapping")

        for key, value in data.items():
            setattr(self, key, value)