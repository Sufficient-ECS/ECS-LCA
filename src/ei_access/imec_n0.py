import bw2data as bd
import bw2io as bi
from functools import wraps, lru_cache
import hashlib
import json
import logging
import msal
from openpyxl import load_workbook
import os
import pandas as pd
from pathlib import Path
import pickle
import requests
import re
from tempfile import NamedTemporaryFile
import time
import yaml
import lca_algebraic as agb

tech_n_avail = []

CACHE_DIR = Path(".cache/")
_cache = {"key": None, "exp": 0}
_file = CACHE_DIR / "api_key.yaml"

def get_api_key(eia):
    now = time.time()

    # memory
    if _cache["key"] and _cache["exp"] > now:
        return _cache["key"]

    # file
    if _file.exists():
        try:
            _cache.update(yaml.safe_load(_file.read_text()) or {})
            if _cache["exp"] > now:
                return _cache["key"]
        except:
            pass

    key, exp = create_api_key(eia)
    _cache.update({"key": key, "exp": exp})
    _file.parent.mkdir(exist_ok=True)
    _file.write_text(yaml.safe_dump(_cache))

    return key


def create_api_key(eia):
    TENANT_ID = eia.tenant_id
    API_SCOPE = f"api://{eia.api_id}/.default"
    
    app = msal.ConfidentialClientApplication(
        client_id=eia.client_id,
        client_credential=eia.client_secret,
        authority=f"https://login.microsoftonline.com/{TENANT_ID}"
    )
    
    response = app.acquire_token_for_client(scopes=[API_SCOPE])
    return response.get("access_token"), time.time() + response.get("expires_in")

def send_request(request, params, eia):
    API_BASE_URL = eia.api_base_url  # Production API URL
 
    response = requests.post(
        f"{API_BASE_URL}{request}",
        headers={"Authorization": f"Bearer {get_api_key(eia)}"},
        json=params
    )

    response.raise_for_status()
    return response.content

def _make_cache_key(technology):
    key_str = f"{technology}"
    return hashlib.md5(key_str.encode()).hexdigest()

def cache_get_die_data(func):
    @wraps(func)
    def wrapper(technology, eia):
        os.makedirs(CACHE_DIR, exist_ok=True)

        cache_key = _make_cache_key(technology)
        cache_path = os.path.join(CACHE_DIR, f"{cache_key}.pkl")

        if os.path.exists(cache_path):
            with open(cache_path, "rb") as f:
                return pickle.load(f)

        result = func(technology, eia)

        with open(cache_path, "wb") as f:
            pickle.dump(result, f)

        return result

    return wrapper

@cache_get_die_data
def get_die_data(technology, eia):
    logging.debug(f"Getting data for {technology}")
    analysis_settings = {
        "tech_nodes": [technology],
    }

    params = {
        "analysis_settings": analysis_settings,
        "setup_type": "die"
    }
    response = send_request("/die/run", params, eia)
    run_id = json.loads(response.decode())["id"]

    params = {
    "analysis_settings": analysis_settings,
    "plot_settings": analysis_settings,
    "type": "bw2",
    }
    response = send_request(f"//plotting/export/die/{run_id}", params, eia)

    return response


def get_die_act(technology, area, eia):
    return get_die_act_tech(technology, eia)

@lru_cache(maxsize=None)
def get_die_act_tech(technology, eia):
    response = get_die_data(technology, eia)

    with NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(response)
        tmp_path = tmp.name

    imp = bi.ExcelImporter(tmp_path)
    imp.db_name = "exchange_mapping_database"
    imp.data[0]["database"] = "exchange_mapping_database"
    act = imp.data[0]

    try:
        # If it exists, return it directly
        return agb.findActivity(act["name"], loc="GLO", db_name = "exchange_mapping_database")
    except:
        # Otherwise import and return newly created activity
        imp.apply_strategies()
        imp.match_database('exchange_mapping_database')

        for exc in imp.unlinked:
            for k, v in exc.items():
                logging.debug(f"imec net0: unlinked exchange: {k}: {v}")
        imp.write_database(delete_existing=False)
        return agb.findActivity(act["name"], loc="GLO", db_name = "exchange_mapping_database")