from __future__ import annotations

import os
import sys
from pathlib import Path


APP_NAME = "Riconfezionamento"
COMPANY_NAME = "SanVincenzo"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _bundle_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return _repo_root()


def _default_data_dir() -> Path:
    if getattr(sys, "frozen", False):
        local_appdata = os.getenv("LOCALAPPDATA")
        if local_appdata:
            return Path(local_appdata) / COMPANY_NAME / APP_NAME / "data"
        return Path.home() / "AppData" / "Local" / COMPANY_NAME / APP_NAME / "data"
    return _repo_root() / "data"


RESOURCE_ROOT = _bundle_root()
if getattr(sys, "frozen", False):
    APP_DIR = RESOURCE_ROOT / "app"
else:
    APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
TEMPLATES_DIR = APP_DIR / "templates"
DATA_DIR = Path(os.getenv("APP_RICONFEZIONAMENTO_DATA_DIR", _default_data_dir())).expanduser()
REPORTS_DIR = DATA_DIR / "reports"
DB_PATH = DATA_DIR / "repackaging.db"
PRODUCTS_CATALOG_PATH = Path(
    os.getenv(
        "APP_RICONFEZIONAMENTO_PRODUCTS_XLSX",
        str(DATA_DIR / "Prodotti.xlsx"),
    )
).expanduser()
