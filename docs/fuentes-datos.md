# Fuentes de Datos — Cóndor View MVP

## Área de Análisis

- **Departamento:** San Rafael, Mendoza, Argentina
- **Superficie:** 31,235 km²
- **Población:** ~215,000 habitantes
- **Bounding Box:** W -70.17, S -36.00, E -66.92, N -34.25
- **Grilla:** 2 km (14,136 zonas)
- **Oasis irrigado:** 6.5% del territorio (~916 zonas)

## Geografía Clave

### Localidades (11)
San Rafael (118k hab), Villa Atuel (8k), Real del Padre (6.3k), Monte Comán (5k), Cuadro Benegas (3k), Rama Caída (2.5k), Las Malvinas (2k), Goudge (1.5k), Salto de las Rosas (1k), El Nihuil (600), El Sosneado (500)

### Ríos
- **Diamante**: Agua del Toro → Los Reyunos → San Rafael → Este
- **Atuel**: El Nihuil → Valle Grande → Oasis → Este

### Embalses
El Nihuil (-35.083, -68.750), Valle Grande (-34.845, -68.520), Los Reyunos (-34.602, -68.642), Agua del Toro (-34.584, -69.036)

### Rutas Nacionales
RN40 (N-S precordillera), RN143 (SE-NW atraviesa oasis), RN144 (San Rafael-El Sosneado), RN146 (San Luis-San Rafael)

### Elevación
400m (llanura este) → 750m (oasis/ciudad) → 1300m (embalses) → 4000m+ (Andes oeste)

## Capas de Datos

| Capa | Fuente MVP | Fuente Real | Estado |
|------|-----------|-------------|--------|
| Basemap | CARTO Dark Matter | Igual | Listo |
| Elevación | Sintético (interpolado) | IGN MDE-Ar 5m / SRTM 30m | Pendiente |
| Pendiente | Derivada de elevación sintética | Derivada de DEM real | Pendiente |
| Red vial | 4 rutas sintéticas | OpenStreetMap (Geofabrik) | Pendiente |
| Huella urbana | 11 localidades sintéticas | OSM + Sentinel-2 | Pendiente |
| Ríos | 2 polilíneas sintéticas | OSM + hídricos provinciales | Pendiente |
| Catastro | Grilla 2km | IDE Mendoza / Catastro provincial | Pendiente |
| Zonificación | Reglas por ubicación | Ordenanza municipal San Rafael | Pendiente |
| Inundabilidad | Buffer de ríos | DEM + hídricos + mapas INA | Pendiente |

## CRS

- **Trabajo:** POSGAR 2007 faja 3 (EPSG:5343) — cálculos métricos
- **Salida:** WGS84 (EPSG:4326) — frontend

## Distribución de Zonas (MVP sintético)

| Categoría | Zonas | % |
|-----------|-------|---|
| Alta | 264 | 1.9% |
| Media | 7,854 | 55.6% |
| Baja | 743 | 5.3% |
| No apto | 5,275 | 37.3% |

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
