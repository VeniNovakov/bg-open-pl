from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI

from ..models import Lifter
from .api import mount_api
from .routes import mount_routes
from .store import Store

SEX_CHOICES = {"F": "Women", "M": "Men"}
DEFAULT_FRONTEND = Path(__file__).resolve().parents[3] / "frontend" / "dist" / "frontend" / "browser"

def athlete_url(lifter: Lifter) -> str:
    return f"/athletes/{lifter.sex or 'U'}/{quote(lifter.name)}"

def create_app(data_dir: str | Path | None = None,
               suppress_file: str | Path | None = None) -> FastAPI:
    data_dir = data_dir or os.environ.get("BGOPL_DATA_DIR", "data")
    suppress_file = suppress_file or os.environ.get("BGOPL_SUPPRESS_FILE")
    store = Store.load_dir(data_dir, suppress_file)

    app = FastAPI(title="BG Open Powerlifting (proof of concept)",
                  description="Results of Bulgarian powerlifting meets, parsed from the "
                              "federation's spreadsheets.")    
    app.state.store = Store.load_dir(data_dir, suppress_file)

    mount_api(app, store)
    mount_routes(app)
    return app