#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "=== 00 Descarga DEM (SRTM) ==="
python 00_descarga/dem.py

echo "=== 00 Descarga OSM ==="
python 00_descarga/osm.py

echo "=== 00 Descarga INDEC (censo 2022) ==="
python 00_descarga/indec.py

echo "=== 01 Zonas (grilla 2km) ==="
python 01_zonas.py

echo "=== 02 Normativa (S_norm) ==="
python 02_normativa.py

echo "=== 03 Físico (S_fis) ==="
python 03_fisico.py

echo "=== 04 Accesibilidad (S_acc) ==="
python 04_accesibilidad.py

echo "=== 07 Servicios (población + déficit) ==="
python 07_servicios.py

echo "=== 08 Isócronas (tiempo de viaje) ==="
python 08_isocronas.py

echo "=== 05 Scoring (IAT + flags) ==="
python 05_scoring.py

echo "=== 06 Export (GeoJSON) ==="
python 06_export.py

echo ""
echo "Pipeline completo. GeoJSON en frontend/public/data/zonas.geojson"
