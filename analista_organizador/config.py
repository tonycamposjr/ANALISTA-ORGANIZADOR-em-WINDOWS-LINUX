"""Gerenciamento centralizado de configurações e persistência."""

import json
import os
from pathlib import Path
from typing import Any, Dict

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "analista-organizador")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG: Dict[str, Any] = {
    "last_path": "",
    "threshold_mb": 50,
    "dup_mode": "rapido",
    "csv_export": True,
    "organize_dry_run": True,
    "organize_por_data": False,
    "organize_duplicados": False,
    "custom_categories_file": "",
}


def get_config_dir() -> Path:
    p = Path(CONFIG_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_config_file() -> Path:
    return get_config_dir() / "config.json"


def load_config() -> Dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    fpath = get_config_file()
    if fpath.is_file():
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if isinstance(saved, dict):
                    cfg.update(saved)
        except (OSError, json.JSONDecodeError):
            pass
    return cfg


def save_config(cfg: Dict[str, Any]) -> None:
    fpath = get_config_file()
    try:
        current = load_config()
        current.update(cfg)
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
    except OSError:
        pass
