#!/usr/bin/env python3
"""
Condor View — Generador de zonas sinteticas para el Departamento de San Rafael.

Lee config.yaml con datos geograficos reales del departamento (~31,000 km2),
genera una grilla de 2km sobre el bounding box completo, calcula sub-indices
sinteticos (normativo, fisico, accesibilidad) y exporta zonas.geojson con el
IAT final.

Produce ~25,000-30,000 zonas con datos realistas basados en:
- Perfil de elevacion interpolado (gradiente oeste-este)
- Rios Diamante y Atuel como polilíneas
- Oasis irrigado, localidades, embalses, rutas viales
"""

from pathlib import Path

import geopandas as gpd
import numpy as np
import yaml
from pyproj import Transformer
from shapely.geometry import LineString, Point, box
from shapely.ops import transform as shapely_transform

# ---------------------------------------------------------------------------
# 1. Cargar configuracion
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

bbox_cfg = cfg["piloto"]["bbox"]
CRS_WORK = cfg["piloto"]["crs_trabajo"]
CRS_OUT = cfg["piloto"]["crs_salida"]
CELL_SIZE = cfg["grilla"]["tamano_m"]

W_NORM = cfg["pesos"]["w_norm"]
W_FIS = cfg["pesos"]["w_fis"]
W_ACC = cfg["pesos"]["w_acc"]

SLOPE_IDEAL = cfg["umbrales"]["pendiente"]["ideal_pct"]
SLOPE_MAX = cfg["umbrales"]["pendiente"]["max_pct"]
D0_HUELLA = cfg["umbrales"]["accesibilidad"]["d0_huella_m"]
D0_VIAL = cfg["umbrales"]["accesibilidad"]["d0_vial_m"]
D0_AGUA = cfg["umbrales"]["accesibilidad"]["d0_agua_m"]

CAT_ALTA = cfg["categorias"]["alta"]
CAT_MEDIA = cfg["categorias"]["media"]

OUTPUT_REL = cfg["rutas"]["salida_geojson"]
OUTPUT_PATH = (SCRIPT_DIR / OUTPUT_REL).resolve()

# Geography
geo = cfg["geografia"]
oasis_bbox = geo["oasis"]
localidades = geo["localidades"]
rios_cfg = geo["rios"]
rutas_viales_cfg = geo["rutas_viales"]
elevacion_perfiles = geo["elevacion"]["perfiles"]
embalses_cfg = geo["embalses"]

# Reproducible randomness
RNG = np.random.default_rng(seed=42)

# ---------------------------------------------------------------------------
# 2. Crear grilla proyectada
# ---------------------------------------------------------------------------

to_metric = Transformer.from_crs(CRS_OUT, CRS_WORK, always_xy=True)
to_geo = Transformer.from_crs(CRS_WORK, CRS_OUT, always_xy=True)

# Project bbox corners to metric CRS
x_min, y_min = to_metric.transform(bbox_cfg["west"], bbox_cfg["south"])
x_max, y_max = to_metric.transform(bbox_cfg["east"], bbox_cfg["north"])

print(f"Bbox metrico: x=[{x_min:.0f}, {x_max:.0f}], y=[{y_min:.0f}, {y_max:.0f}]")
print(f"Extension: {(x_max - x_min) / 1000:.0f} x {(y_max - y_min) / 1000:.0f} km")

# Generate grid cell centroids first (vectorized)
xs = np.arange(x_min, x_max, CELL_SIZE)
ys = np.arange(y_min, y_max, CELL_SIZE)
n_cols = len(xs)
n_rows = len(ys)

print(f"Grilla: {n_cols} x {n_rows} = {n_cols * n_rows} celdas")

# Create meshgrid of cell origins (lower-left corner)
xx, yy = np.meshgrid(xs, ys, indexing="ij")
origins_x = xx.ravel()
origins_y = yy.ravel()
n_cells = len(origins_x)

# Centroids in metric space
cx_m = origins_x + CELL_SIZE / 2.0
cy_m = origins_y + CELL_SIZE / 2.0

# Convert centroids to geographic coordinates for geographic calculations
cx_geo = np.empty(n_cells)
cy_geo = np.empty(n_cells)

# Transform in chunks for performance
CHUNK = 5000
for i in range(0, n_cells, CHUNK):
    end = min(i + CHUNK, n_cells)
    lngs, lats = to_geo.transform(cx_m[i:end], cy_m[i:end])
    cx_geo[i:end] = lngs
    cy_geo[i:end] = lats

print(f"Rango geografico: lon=[{cx_geo.min():.3f}, {cx_geo.max():.3f}], "
      f"lat=[{cy_geo.min():.3f}, {cy_geo.max():.3f}]")

# ---------------------------------------------------------------------------
# 3. Modelo de elevacion
# ---------------------------------------------------------------------------

print("Calculando elevacion...")

# Build interpolation from longitude-based profiles
prof_lngs = np.array([p["lng"] for p in elevacion_perfiles])
prof_alts = np.array([p["alt_m"] for p in elevacion_perfiles])

# Base elevation: interpolate from longitude profiles
elev_base = np.interp(cx_geo, prof_lngs, prof_alts)

# Latitude variation: higher to the south-southwest (near Andes)
# Reference latitude: the center of the department is ~-35.1
# Southern areas have slightly higher elevations due to Andes proximity
lat_center = -35.1
lat_factor = np.clip((cy_geo - lat_center) / 1.0, -1.0, 1.0)
# Negative lat_factor means south of center -> add elevation
# But only meaningful in mountainous west
mountain_mask = cx_geo < -68.5
lat_elev_adj = np.where(
    mountain_mask,
    -lat_factor * 300.0,  # +300m for southern mountain zones
    -lat_factor * 50.0,   # +50m subtle effect in plains
)

# Harmonic noise for realism
noise = (
    80.0 * np.sin(cx_geo * 12.0) * np.cos(cy_geo * 10.0)
    + 40.0 * np.sin(cx_geo * 25.0 + 1.7) * np.cos(cy_geo * 18.0 + 0.9)
    + 20.0 * np.sin(cx_geo * 50.0 + 3.1) * np.cos(cy_geo * 40.0 + 2.1)
    + RNG.normal(0, 15.0, n_cells)
)

# Scale noise by elevation — more noise in mountains, less in plains
noise_scale = np.clip((elev_base - 400.0) / 2000.0, 0.1, 1.0)
elevacion_m = np.clip(elev_base + lat_elev_adj + noise * noise_scale, 300.0, 5000.0)
elevacion_m_int = np.round(elevacion_m).astype(int)

# ---------------------------------------------------------------------------
# 4. Pendiente (slope)
# ---------------------------------------------------------------------------

print("Calculando pendiente...")

# Derive slope from elevation model using geographic gradient
# Mountains (west): steep slopes 15-40%
# Oasis (center): flat 1-5%
# Plains (east): gentle 2-8%

# Approximate slope from elevation gradient (finite differences)
# Using the elevation grid reshaped to compute gradients
elev_grid = elevacion_m.reshape(n_cols, n_rows)

# Gradient in x (columns) and y (rows) direction
grad_x = np.zeros_like(elev_grid)
grad_y = np.zeros_like(elev_grid)

grad_x[1:-1, :] = (elev_grid[2:, :] - elev_grid[:-2, :]) / (2.0 * CELL_SIZE)
grad_x[0, :] = (elev_grid[1, :] - elev_grid[0, :]) / CELL_SIZE
grad_x[-1, :] = (elev_grid[-1, :] - elev_grid[-2, :]) / CELL_SIZE

grad_y[:, 1:-1] = (elev_grid[:, 2:] - elev_grid[:, :-2]) / (2.0 * CELL_SIZE)
grad_y[:, 0] = (elev_grid[:, 1] - elev_grid[:, 0]) / CELL_SIZE
grad_y[:, -1] = (elev_grid[:, -1] - elev_grid[:, -2]) / CELL_SIZE

slope_fraction = np.sqrt(grad_x**2 + grad_y**2)
slope_pct_grid = slope_fraction * 100.0

slope_pct = slope_pct_grid.ravel()

# Add a zone-based correction to ensure correct ranges
# Mountain zones get boosted slope, oasis dampened
for_mountain = cx_geo < -69.0
for_foothills = (cx_geo >= -69.0) & (cx_geo < -68.5)
for_oasis = (
    (cx_geo >= oasis_bbox["west"]) & (cx_geo <= oasis_bbox["east"])
    & (cy_geo >= oasis_bbox["south"]) & (cy_geo <= oasis_bbox["north"])
)
for_plains = cx_geo > -67.5

slope_pct = np.where(for_mountain, np.clip(slope_pct * 2.5 + 10.0, 15.0, 45.0), slope_pct)
slope_pct = np.where(for_foothills, np.clip(slope_pct * 1.5 + 5.0, 5.0, 25.0), slope_pct)
slope_pct = np.where(for_oasis, np.clip(slope_pct * 0.3 + 1.0, 1.0, 5.0), slope_pct)
slope_pct = np.where(for_plains, np.clip(slope_pct * 0.5 + 2.0, 2.0, 8.0), slope_pct)

# Add small noise
slope_pct = slope_pct + RNG.normal(0, 0.3, n_cells)
slope_pct = np.clip(slope_pct, 0.5, 50.0)
slope_pct = np.round(slope_pct, 1)

# ---------------------------------------------------------------------------
# 5. Pre-compute geographic features (rivers, roads, localidades, embalses)
# ---------------------------------------------------------------------------

print("Pre-calculando distancias a features geograficos...")

# --- Rivers as metric LineStrings ---
def make_metric_linestring(points: list) -> LineString:
    """Convert list of [lng, lat] to a metric LineString."""
    metric_pts = [to_metric.transform(p[0], p[1]) for p in points]
    return LineString(metric_pts)

rio_diamante_line = make_metric_linestring(rios_cfg["diamante"]["puntos"])
rio_atuel_line = make_metric_linestring(rios_cfg["atuel"]["puntos"])
rio_diamante_ancho = rios_cfg["diamante"]["ancho_riesgo_m"]
rio_atuel_ancho = rios_cfg["atuel"]["ancho_riesgo_m"]

# --- Roads as metric LineStrings ---
road_lines = []
for ruta_name, ruta_pts in rutas_viales_cfg.items():
    road_lines.append(make_metric_linestring(ruta_pts))

# --- Localidades in metric ---
loc_data = []
for loc in localidades:
    mx, my = to_metric.transform(loc["coords"][0], loc["coords"][1])
    loc_data.append({
        "nombre": loc["nombre"],
        "x": mx,
        "y": my,
        "lng": loc["coords"][0],
        "lat": loc["coords"][1],
        "poblacion": loc["poblacion"],
        "radio_urbano_m": loc["radio_urbano_m"],
    })

loc_xs = np.array([l["x"] for l in loc_data])
loc_ys = np.array([l["y"] for l in loc_data])
loc_pobs = np.array([l["poblacion"] for l in loc_data], dtype=float)
loc_radios = np.array([l["radio_urbano_m"] for l in loc_data], dtype=float)

# --- Embalses in metric ---
emb_data = []
for emb in embalses_cfg:
    mx, my = to_metric.transform(emb["coords"][0], emb["coords"][1])
    emb_data.append({
        "nombre": emb["nombre"],
        "x": mx,
        "y": my,
        "radio_m": emb["radio_m"],
    })

emb_xs = np.array([e["x"] for e in emb_data])
emb_ys = np.array([e["y"] for e in emb_data])
emb_radios = np.array([e["radio_m"] for e in emb_data])

# --- Oasis bbox in metric ---
oasis_west_m, oasis_south_m = to_metric.transform(oasis_bbox["west"], oasis_bbox["south"])
oasis_east_m, oasis_north_m = to_metric.transform(oasis_bbox["east"], oasis_bbox["north"])

# ---------------------------------------------------------------------------
# 5a. Vectorized distance calculations
# ---------------------------------------------------------------------------

print("  Distancia a localidades...")

# Distance to each localidad (vectorized via broadcasting)
# Shape: (n_cells,) for each localidad
dx_loc = cx_m[:, np.newaxis] - loc_xs[np.newaxis, :]  # (n_cells, n_loc)
dy_loc = cy_m[:, np.newaxis] - loc_ys[np.newaxis, :]
dist_to_locs = np.sqrt(dx_loc**2 + dy_loc**2)  # (n_cells, n_loc)

# Nearest localidad
nearest_loc_idx = np.argmin(dist_to_locs, axis=1)
dist_nearest_loc = dist_to_locs[np.arange(n_cells), nearest_loc_idx]

# Population-weighted distance to nearest localidad (for accessibility)
# Weight by sqrt(population) so bigger cities have more pull
pop_weights = np.sqrt(loc_pobs)
weighted_dists = dist_to_locs / pop_weights[np.newaxis, :]
dist_huella_weighted = np.min(weighted_dists, axis=1)
# Normalize back to approximate meters
dist_huella_m = dist_huella_weighted * np.sqrt(np.median(loc_pobs))

# Is within urban radius of any localidad?
within_urban = np.any(dist_to_locs <= loc_radios[np.newaxis, :], axis=1)

print("  Distancia a embalses...")

# Distance to embalses
dx_emb = cx_m[:, np.newaxis] - emb_xs[np.newaxis, :]
dy_emb = cy_m[:, np.newaxis] - emb_ys[np.newaxis, :]
dist_to_embs = np.sqrt(dx_emb**2 + dy_emb**2)  # (n_cells, n_emb)
near_embalse = np.any(dist_to_embs <= emb_radios[np.newaxis, :], axis=1)

print("  Distancia a rios (segmentos)...")

# Distance to rivers — approximate using segment-based approach
def dist_to_linestring_vectorized(cx: np.ndarray, cy: np.ndarray,
                                   line: LineString) -> np.ndarray:
    """Compute distance from each point to a LineString using segments."""
    coords = np.array(line.coords)
    n_seg = len(coords) - 1
    min_dist = np.full(len(cx), np.inf)

    for s in range(n_seg):
        ax, ay = coords[s]
        bx, by = coords[s + 1]

        # Vector from a to b
        abx = bx - ax
        aby = by - ay
        ab_len_sq = abx**2 + aby**2

        if ab_len_sq < 1e-10:
            continue

        # Project points onto segment
        t = ((cx - ax) * abx + (cy - ay) * aby) / ab_len_sq
        t = np.clip(t, 0.0, 1.0)

        # Closest point on segment
        px = ax + t * abx
        py = ay + t * aby

        d = np.sqrt((cx - px)**2 + (cy - py)**2)
        min_dist = np.minimum(min_dist, d)

    return min_dist

dist_diamante = dist_to_linestring_vectorized(cx_m, cy_m, rio_diamante_line)
dist_atuel = dist_to_linestring_vectorized(cx_m, cy_m, rio_atuel_line)
dist_rio_min = np.minimum(dist_diamante, dist_atuel)

print("  Distancia a rutas viales...")

# Distance to roads
dist_vial = np.full(n_cells, np.inf)
for road in road_lines:
    d = dist_to_linestring_vectorized(cx_m, cy_m, road)
    dist_vial = np.minimum(dist_vial, d)

# Distance to water bodies (rivers + embalses)
dist_agua = dist_rio_min.copy()
for j in range(len(emb_data)):
    d_emb = np.sqrt((cx_m - emb_xs[j])**2 + (cy_m - emb_ys[j])**2)
    dist_agua = np.minimum(dist_agua, d_emb)

# ---------------------------------------------------------------------------
# 6. Riesgo hidrico (flood risk)
# ---------------------------------------------------------------------------

print("Calculando riesgo hidrico...")

# Risk from Diamante
riesgo_diamante = np.where(
    dist_diamante <= rio_diamante_ancho, 2,  # alto
    np.where(dist_diamante <= rio_diamante_ancho * 2, 1, 0)  # medio / bajo
)

# Risk from Atuel
riesgo_atuel = np.where(
    dist_atuel <= rio_atuel_ancho, 2,
    np.where(dist_atuel <= rio_atuel_ancho * 2, 1, 0)
)

# Near embalse = alto
riesgo_embalse = np.where(near_embalse, 2, 0)

# Combined: take maximum risk
riesgo_score = np.maximum(np.maximum(riesgo_diamante, riesgo_atuel), riesgo_embalse)

riesgo_hidrico = np.where(
    riesgo_score == 2, "alto",
    np.where(riesgo_score == 1, "medio", "bajo")
)

# Flood scores for S_fis
s_flood = np.where(riesgo_score == 2, 0.0, np.where(riesgo_score == 1, 0.5, 1.0))

# ---------------------------------------------------------------------------
# 7. Zonificacion (S_norm) — uso_permitido
# ---------------------------------------------------------------------------

print("Calculando S_norm (zonificacion)...")

# Boolean masks for geographic zones
in_oasis = (
    (cx_geo >= oasis_bbox["west"]) & (cx_geo <= oasis_bbox["east"])
    & (cy_geo >= oasis_bbox["south"]) & (cy_geo <= oasis_bbox["north"])
)

is_mountain = elevacion_m > 1500.0

# Canon del Atuel area
in_canon_atuel = (
    (cx_geo >= -68.7) & (cx_geo <= -68.5)
    & (cy_geo >= -35.1) & (cy_geo <= -34.8)
)

# Near localidades (within 5km of any)
near_localidad_5km = dist_nearest_loc <= 5000.0
# Near localidades (within 10km)
near_localidad_10km = dist_nearest_loc <= 10000.0

# Initialize
uso = np.full(n_cells, "rural", dtype=object)
s_norm = np.full(n_cells, 0.3)

# Apply zoning rules (order matters — later rules override)

# 1. Desert/arid outside oasis: "rural" (0.3) — already default

# 2. Near localidades outside oasis: "condicionado" (0.5)
mask_condicionado = near_localidad_10km & ~in_oasis
uso[mask_condicionado] = "condicionado"
s_norm[mask_condicionado] = 0.5

# 3. Inside oasis but far from localidades: "agricola" (0.7)
mask_agricola = in_oasis & ~near_localidad_5km
uso[mask_agricola] = "agricola"
s_norm[mask_agricola] = 0.7

# 4. Inside oasis AND near a localidad: "residencial" or "mixto" (1.0)
mask_urban_oasis = in_oasis & within_urban
uso[mask_urban_oasis] = "residencial"
s_norm[mask_urban_oasis] = 1.0

mask_near_oasis = in_oasis & near_localidad_5km & ~within_urban
uso[mask_near_oasis] = "mixto"
s_norm[mask_near_oasis] = 1.0

# 5. Mountain zone: "reserva_natural" (0.0)
mask_mountain = is_mountain
uso[mask_mountain] = "reserva_natural"
s_norm[mask_mountain] = 0.0

# 6. Near embalses: "reserva_hidrica" (0.0)
mask_embalse = near_embalse
uso[mask_embalse] = "reserva_hidrica"
s_norm[mask_embalse] = 0.0

# 7. Canon del Atuel: "reserva_turistica" (0.0)
mask_canon = in_canon_atuel
uso[mask_canon] = "reserva_turistica"
s_norm[mask_canon] = 0.0

# ---------------------------------------------------------------------------
# 8. Sub-indice Fisico (S_fis)
# ---------------------------------------------------------------------------

print("Calculando S_fis (fisico)...")

# Slope score: 1.0 if <= ideal, linear decay to 0 at max, 0 beyond
s_slope = np.where(
    slope_pct <= SLOPE_IDEAL,
    1.0,
    np.clip(1.0 - (slope_pct - SLOPE_IDEAL) / (SLOPE_MAX - SLOPE_IDEAL), 0.0, 1.0),
)

# Altitude penalty: above 2000m
altitude_penalty = np.where(elevacion_m > 2000.0, 0.5, 1.0)

# Combined physical score: slope * flood * altitude_penalty
s_fis = s_slope * s_flood * altitude_penalty
s_fis = np.round(s_fis, 2)

# ---------------------------------------------------------------------------
# 9. Sub-indice Accesibilidad (S_acc)
# ---------------------------------------------------------------------------

print("Calculando S_acc (accesibilidad)...")

# Exponential decay scores
score_huella = np.exp(-dist_huella_m / D0_HUELLA)
score_vial = np.exp(-dist_vial / D0_VIAL)
score_agua = np.exp(-dist_agua / D0_AGUA)

# Combined accessibility score
s_acc = 0.45 * score_huella + 0.35 * score_vial + 0.20 * score_agua
s_acc = np.round(s_acc, 2)

# ---------------------------------------------------------------------------
# 10. Calcular IAT y categorias
# ---------------------------------------------------------------------------

print("Calculando IAT...")

iat_raw = 100.0 * (W_NORM * s_norm + W_FIS * s_fis + W_ACC * s_acc)
iat = np.round(iat_raw).astype(int)

# Hard overrides
# Any "reserva*" -> IAT=0, no_apto
is_reserva = np.char.startswith(uso.astype(str), "reserva")
iat = np.where(is_reserva, 0, iat)

# Elevation > 3000m -> IAT=0, no_apto (permanent snow/rock)
above_3000 = elevacion_m > 3000.0
iat = np.where(above_3000, 0, iat)

# Clamp
iat = np.clip(iat, 0, 100)

# Categories
categoria = np.where(
    is_reserva | above_3000, "no_apto",
    np.where(iat >= CAT_ALTA, "alta",
             np.where(iat >= CAT_MEDIA, "media", "baja"))
)

# Flags
flags_list = []
for i in range(n_cells):
    cell_flags = []
    if is_reserva[i]:
        cell_flags.append("uso_reserva")
    if above_3000[i]:
        cell_flags.append("elevacion_extrema")
    if riesgo_hidrico[i] == "alto":
        cell_flags.append("riesgo_hidrico_alto")
    if slope_pct[i] > SLOPE_MAX:
        cell_flags.append("pendiente_excesiva")
    flags_list.append(cell_flags)

# ---------------------------------------------------------------------------
# 11. Distrito (nearest localidad name) and en_oasis
# ---------------------------------------------------------------------------

print("Asignando distritos...")

distrito = np.array([loc_data[idx]["nombre"] for idx in nearest_loc_idx])

# ---------------------------------------------------------------------------
# 12. Construir geometrias y exportar
# ---------------------------------------------------------------------------

print("Construyendo geometrias...")

# Create box geometries vectorized
cells = [
    box(origins_x[i], origins_y[i],
        origins_x[i] + CELL_SIZE, origins_y[i] + CELL_SIZE)
    for i in range(n_cells)
]

# Build GeoDataFrame
gdf = gpd.GeoDataFrame(
    {
        "id": [f"Z-{i + 1:05d}" for i in range(n_cells)],
        "iat": iat,
        "categoria": categoria,
        "s_norm": s_norm,
        "s_fis": s_fis,
        "s_acc": s_acc,
        "uso_permitido": uso,
        "pendiente_pct": slope_pct,
        "riesgo_hidrico": riesgo_hidrico,
        "elevacion_m": elevacion_m_int,
        "dist_huella_m": np.round(dist_huella_m, 0).astype(int),
        "dist_vial_m": np.round(dist_vial, 0).astype(int),
        "en_oasis": in_oasis,
        "distrito": distrito,
        "flags": flags_list,
    },
    geometry=cells,
    crs=CRS_WORK,
)

# Reproject to EPSG:4326
print("Reproyectando a WGS84...")
gdf = gdf.to_crs(CRS_OUT)

# Simplify geometries (~20m tolerance in degrees at lat -35)
# At lat -35, 1 deg lon ~ 92km, 1 deg lat ~ 111km
# 20m ~ 20/92000 ~ 0.00022 degrees
SIMPLIFY_TOL = 0.00022
gdf["geometry"] = gdf["geometry"].simplify(SIMPLIFY_TOL, preserve_topology=True)


# Round coordinates to 5 decimals
def round_coords(geom, decimals: int = 5):
    """Round all coordinates in a geometry."""
    def _round(x, y, z=None):
        if z is not None:
            return (round(x, decimals), round(y, decimals), round(z, decimals))
        return (round(x, decimals), round(y, decimals))
    return shapely_transform(_round, geom)


gdf["geometry"] = gdf["geometry"].apply(round_coords)

# Round sub-indices
gdf["s_norm"] = gdf["s_norm"].round(2)
gdf["s_fis"] = gdf["s_fis"].round(2)
gdf["s_acc"] = gdf["s_acc"].round(2)

# Select and order columns for output
output_cols = [
    "id", "iat", "categoria", "s_norm", "s_fis", "s_acc",
    "uso_permitido", "pendiente_pct", "riesgo_hidrico",
    "elevacion_m", "dist_huella_m", "dist_vial_m",
    "en_oasis", "distrito", "flags", "geometry",
]
gdf_out = gdf[output_cols].copy()

# ---------------------------------------------------------------------------
# 13. Exportar GeoJSON
# ---------------------------------------------------------------------------

print("Exportando GeoJSON...")
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

gdf_out.to_file(OUTPUT_PATH, driver="GeoJSON")

file_size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
print(f"\nExportado: {OUTPUT_PATH}")
print(f"Tamano: {file_size_mb:.2f} MB")
print(f"Features: {len(gdf_out)}")

# ---------------------------------------------------------------------------
# 14. Estadisticas y verificacion
# ---------------------------------------------------------------------------

print("\n--- Distribucion de categorias ---")
for cat in ["alta", "media", "baja", "no_apto"]:
    count = (gdf_out["categoria"] == cat).sum()
    pct = count / len(gdf_out) * 100
    print(f"  {cat:>8s}: {count:5d} ({pct:5.1f}%)")

print("\n--- Distribucion de uso_permitido ---")
for uso_val in sorted(gdf_out["uso_permitido"].unique()):
    count = (gdf_out["uso_permitido"] == uso_val).sum()
    pct = count / len(gdf_out) * 100
    print(f"  {uso_val:>20s}: {count:5d} ({pct:5.1f}%)")

print("\n--- Distribucion de riesgo_hidrico ---")
for r in ["alto", "medio", "bajo"]:
    count = (gdf_out["riesgo_hidrico"] == r).sum()
    pct = count / len(gdf_out) * 100
    print(f"  {r:>6s}: {count:5d} ({pct:5.1f}%)")

print(f"\n--- IAT stats ---")
print(f"  Media:   {gdf_out['iat'].mean():.1f}")
print(f"  Mediana: {gdf_out['iat'].median():.0f}")
print(f"  Min:     {gdf_out['iat'].min()}")
print(f"  Max:     {gdf_out['iat'].max()}")

print(f"\n--- Elevacion stats ---")
print(f"  Media:   {gdf_out['elevacion_m'].mean():.0f} m")
print(f"  Min:     {gdf_out['elevacion_m'].min()} m")
print(f"  Max:     {gdf_out['elevacion_m'].max()} m")

print(f"\n--- Pendiente stats ---")
print(f"  Media:   {gdf_out['pendiente_pct'].mean():.1f}%")
print(f"  Min:     {gdf_out['pendiente_pct'].min():.1f}%")
print(f"  Max:     {gdf_out['pendiente_pct'].max():.1f}%")

# Sample features from different areas
print("\n--- Muestras por zona ---")

# Oasis sample
oasis_sample = gdf_out[gdf_out["en_oasis"]].head(1)
if len(oasis_sample) > 0:
    s = oasis_sample.iloc[0]
    print(f"\n  OASIS: {s['id']} | IAT={s['iat']} | cat={s['categoria']} | "
          f"uso={s['uso_permitido']} | elev={s['elevacion_m']}m | "
          f"slope={s['pendiente_pct']}% | distrito={s['distrito']}")

# Mountain sample
mtn_sample = gdf_out[gdf_out["elevacion_m"] > 2000].head(1)
if len(mtn_sample) > 0:
    s = mtn_sample.iloc[0]
    print(f"  MONTANA: {s['id']} | IAT={s['iat']} | cat={s['categoria']} | "
          f"uso={s['uso_permitido']} | elev={s['elevacion_m']}m | "
          f"slope={s['pendiente_pct']}% | distrito={s['distrito']}")

# Desert/plain sample
desert_sample = gdf_out[
    (~gdf_out["en_oasis"]) & (gdf_out["elevacion_m"] < 600)
    & (gdf_out["uso_permitido"] == "rural")
].head(1)
if len(desert_sample) > 0:
    s = desert_sample.iloc[0]
    print(f"  DESIERTO: {s['id']} | IAT={s['iat']} | cat={s['categoria']} | "
          f"uso={s['uso_permitido']} | elev={s['elevacion_m']}m | "
          f"slope={s['pendiente_pct']}% | distrito={s['distrito']}")

# Reserva sample
reserva_sample = gdf_out[gdf_out["uso_permitido"].str.startswith("reserva")].head(1)
if len(reserva_sample) > 0:
    s = reserva_sample.iloc[0]
    print(f"  RESERVA: {s['id']} | IAT={s['iat']} | cat={s['categoria']} | "
          f"uso={s['uso_permitido']} | elev={s['elevacion_m']}m | "
          f"slope={s['pendiente_pct']}% | distrito={s['distrito']}")

print(f"\n--- En oasis ---")
print(f"  Zonas en oasis: {gdf_out['en_oasis'].sum()} "
      f"({gdf_out['en_oasis'].sum() / len(gdf_out) * 100:.1f}%)")

print("\nPipeline completado.")
