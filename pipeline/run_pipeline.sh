#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "=== 00 Descarga DEM ==="
python 00_descarga/dem.py

echo "=== 00 Descarga OSM ==="
python 00_descarga/osm.py

echo "=== 01 Zonas ==="
python 01_zonas.py

echo "=== 02 Normativa ==="
python 02_normativa.py

echo "=== 03 Físico ==="
python 03_fisico.py

echo "=== 04 Accesibilidad ==="
python 04_accesibilidad.py

echo "=== 05 Scoring ==="
python 05_scoring.py

echo "=== 06 Export ==="
python 06_export.py

echo ""
echo "Pipeline completo. GeoJSON en frontend/public/data/zonas.geojson"
