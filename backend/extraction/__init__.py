"""Extracción on-demand (CAPA 1) para el backend FastAPI.

Reutiliza la librería del pipeline (pipeline/lib) y su config.yaml.
"""

import sys
from pathlib import Path

# Wire la librería compartida del pipeline al path.
PIPELINE_DIR = Path(__file__).resolve().parent.parent.parent / "pipeline"
if str(PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(PIPELINE_DIR))
