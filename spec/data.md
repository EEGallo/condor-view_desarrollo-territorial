# Fuentes de Datos

## Estado actual: datos reales

El pipeline usa datos reales descargados (DEM SRTM, OSM, INDEC). `config.yaml` mantiene geografía de respaldo (fallback) si una fuente no está disponible.

| Capa | Fuente actual | Estado |
|------|--------------|--------|
| Elevación / pendiente | DEM SRTM3 90m (reproyectado EPSG:5343) | ✅ Real |
| Red vial | OpenStreetMap (osmnx) | ✅ Real |
| Ríos / hídrico | OpenStreetMap waterways + embalses config | ✅ Real + config |
| Uso del suelo (S_norm) | OSM landuse (proxy de ordenanza) | ✅ Real (proxy) |
| Localidades / huella | OSM places | ✅ Real |
| Educación / salud | OSM amenities (161 / 69) | ✅ Real |
| **Población** | **INDEC Censo 2022 — radios censales** | ✅ Real |
| Isócronas | osmnx + networkx (red vial del oasis) | ✅ Real |
| Catastro | Grilla 2km regular | ⏳ Pendiente (IDE Mendoza) |
| Zonificación oficial | OSM landuse como proxy | ⏳ Pendiente (ordenanza San Rafael) |
| Basemap | CARTO Dark Matter | ✅ |

### Población — INDEC Censo 2022

Fuente: CONICET RI handle `11336/284095` (radios censales 2022 con población REDATAM). Descarga: `00_descarga/indec.py` → filtra departamento San Rafael → `data/raw/indec_radios.gpkg`.

- **228 radios censales** en San Rafael, **170.004 hab** asignados a 55 celdas de grilla.
- El dataset filtra radios con densidad > 1 hab/ha — excluye población rural dispersa (de ahí < ~215k del departamento total). Capta la población concentrada, que es la relevante para el gap servicios↔población.
- Columna población: `CA3`; cascada en `07_servicios.py` la usa como **nivel 1** (sobre OSM places y config).

---

## CRS

| Uso | EPSG | Nombre |
|-----|------|--------|
| Cálculos métricos | EPSG:5343 | POSGAR 2007 faja 3 |
| Salida frontend | EPSG:4326 | WGS84 |

---

## Área piloto: San Rafael, Mendoza

### Bounding box

```yaml
west:  -70.17
south: -36.00
east:  -66.92
north: -34.25
```

### Geografía clave

**Oasis irrigado** (~5.7% del departamento, 90% de la población)
```
north: -34.50 / south: -34.95 / west: -68.50 / east: -67.70
```

**Elevación** — gradiente oeste→este  
| Longitud | Altitud |
|----------|---------|
| -70.17 | 4,000 m (Andes) |
| -68.50 | 800 m |
| -68.33 | 750 m (ciudad San Rafael) |
| -67.00 | 400 m |
| -66.92 | 380 m (llanura este) |

### Localidades (11)

| Localidad | Coords (lng, lat) | Población | Radio urbano |
|-----------|------------------|-----------|-------------|
| San Rafael | -68.333, -34.600 | 118,000 | 6,000 m |
| Villa Atuel | -67.920, -34.831 | 8,000 | 2,000 m |
| Real del Padre | -67.766, -34.840 | 6,350 | 1,500 m |
| Monte Comán | -67.878, -34.592 | 5,000 | 1,500 m |
| Cuadro Benegas | -68.431, -34.623 | 3,000 | 1,200 m |
| Rama Caída | -68.382, -34.678 | 2,500 | 1,000 m |
| Las Malvinas | -68.250, -34.830 | 2,000 | 1,000 m |
| Goudge | -68.050, -34.610 | 1,500 | 800 m |
| Salto de las Rosas | -68.300, -34.660 | 1,000 | 800 m |
| El Nihuil | -68.667, -35.033 | 600 | 500 m |
| El Sosneado | -69.568, -35.079 | 500 | 500 m |

### Ríos

| Río | Ancho riesgo hídrico |
|-----|---------------------|
| Diamante | 3,000 m |
| Atuel | 2,500 m |

### Embalses

| Embalse | Coords (lng, lat) | Radio buffer |
|---------|------------------|-------------|
| El Nihuil | -68.750, -35.083 | 5,000 m |
| Valle Grande | -68.520, -34.845 | 2,000 m |
| Los Reyunos | -68.642, -34.602 | 3,000 m |
| Agua del Toro | -69.036, -34.584 | 2,000 m |

### Rutas nacionales sintéticas

- **RN40**: N-S por precordillera
- **RN143**: SE-NW, atraviesa el oasis, pasa por San Rafael
- **RN144**: San Rafael → El Sosneado
- **RN146**: San Luis → San Rafael (desde el este)

---

## Distribución de zonas (MVP sintético)

| Categoría | Zonas | % |
|-----------|-------|---|
| Alta (IAT ≥ 70) | 264 | 1.9% |
| Media (IAT ≥ 40) | 7,854 | 55.6% |
| Baja (IAT < 40) | 743 | 5.3% |
| No apto | 5,275 | 37.3% |
| **Total** | **14,136** | 100% |

| Uso del suelo | Zonas | % |
|---------------|-------|---|
| Rural (desierto) | 7,905 | 55.9% |
| Reserva natural (montaña) | 5,089 | 36.0% |
| Agrícola (oasis) | 744 | 5.3% |
| Reserva turística | 157 | 1.1% |
| Mixto (urbano) | 131 | 0.9% |
| Residencial | 41 | 0.3% |
| Condicionado | 40 | 0.3% |
| Reserva hídrica | 29 | 0.2% |

---

## Path a datos reales

Para reemplazar datos sintéticos por datos reales, en orden de prioridad:

1. **DEM (elevación + pendiente)** — descargar de IGN MDE-Ar (5m) o SRTM/Copernicus (30m). Reemplaza la interpolación lineal en `generate_zones.py` o el script `03_fisico.py`.
2. **OSM (rutas + huella urbana + ríos)** — descargar de Geofabrik pbf para Mendoza. Reemplaza polilíneas y radios sintéticos.
3. **Catastro** — IDE Mendoza (WFS) o shapefile provincial. Reemplaza grilla 2km por parcelas reales.
4. **Zonificación** — Digitalización manual en QGIS de la ordenanza municipal de San Rafael. Es el trabajo más pesado y el bloqueante principal para datos reales.

---

*Ver también: [pipeline.md](pipeline.md) para implementación · [scoring.md](scoring.md) para uso de datos en fórmulas*
