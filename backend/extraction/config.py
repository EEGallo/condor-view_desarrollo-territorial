"""Carga de config compartida (pipeline/config.yaml + sources.yaml)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from . import PIPELINE_DIR

PIPELINE_CONFIG = PIPELINE_DIR / "config.yaml"
DEM_PATH = PIPELINE_DIR / "data" / "raw" / "dem_san_rafael.tif"


@lru_cache(maxsize=1)
def pipeline_config() -> dict[str, Any]:
    with open(PIPELINE_CONFIG, encoding="utf-8") as f:
        return yaml.safe_load(f)


def crs_metric() -> str:
    return pipeline_config()["piloto"]["crs_trabajo"]


def crs_exchange() -> str:
    return pipeline_config()["piloto"]["crs_salida"]
