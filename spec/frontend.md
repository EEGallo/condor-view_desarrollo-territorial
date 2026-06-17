# Frontend

## Stack

- **Next.js** (App Router) — `frontend/`
- **MapLibre GL JS** — renderizado de mapa vectorial
- **Tailwind CSS** — estilos
- Sin login, sin estado servidor, sin API calls en runtime

Deploy: Vercel (archivos estáticos).

---

## Componentes (`frontend/components/`)

| Componente | Responsabilidad |
|------------|----------------|
| `MapView.tsx` | Carga `zonas.geojson`, pinta zonas coloreadas por `categoria`, basemap CARTO Dark Matter |
| `ZonePanel.tsx` | Panel lateral al clickear zona: IAT grande + barras de los 3 sub-índices + flags |
| `Legend.tsx` | Leyenda de la escala de colores (4 categorías) |
| `WeightControls.tsx` | Sliders para `w_norm`, `w_fis`, `w_acc` — recalcula IAT en cliente sin re-ejecutar pipeline |
| `FilterControls.tsx` | Filtrar zonas visibles por categoría y/o uso_permitido |
| `LayerToggle.tsx` | Activar/desactivar capas del mapa |
| `StatsBar.tsx` | Estadísticas agregadas del área visible (conteos por categoría, IAT promedio) |
| `MapTooltip.tsx` | Tooltip en hover: id + IAT + categoría |
| `ExportButton.tsx` | Exportar vista o datos filtrados |

### Interacciones mínimas

- **Hover** → `MapTooltip` con id, IAT, categoría
- **Click** → abre `ZonePanel` con desglose completo
- **Zoom/pan** → estándar MapLibre
- **Sliders** (`WeightControls`) → recalculan IAT en cliente: `Math.round(100 * (w_norm * s_norm + w_fis * s_fis + w_acc * s_acc))`

---

## GeoJSON Schema

Cada feature en `frontend/public/data/zonas.geojson`:

```json
{
  "type": "Feature",
  "geometry": { "type": "Polygon", "coordinates": [[...]] },
  "properties": {
    "id": "A-14",
    "iat": 78,
    "categoria": "alta",
    "s_norm": 1.0,
    "s_fis": 0.82,
    "s_acc": 0.55,
    "uso_permitido": "residencial",
    "pendiente_pct": 3.1,
    "riesgo_hidrico": "bajo",
    "elevacion_m": 750,
    "dist_huella_m": 600,
    "dist_vial_m": 120,
    "en_oasis": true,
    "distrito": "San Rafael",
    "flags": ["sin_acceso_pavimentado"]
  }
}
```

### Tipos (sync con `frontend/components/types.ts`)

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|------------|-------------|
| `id` | `string` | Sí | Identificador de zona |
| `iat` | `number` | Sí | Índice 0–100, entero |
| `categoria` | `Categoria` | Sí | `alta` \| `media` \| `baja` \| `no_apto` |
| `s_norm` | `number` | Sí | Sub-índice normativo [0, 1] |
| `s_fis` | `number` | Sí | Sub-índice físico [0, 1] |
| `s_acc` | `number` | Sí | Sub-índice accesibilidad [0, 1] |
| `uso_permitido` | `string` | Sí | Uso del suelo según ordenanza |
| `pendiente_pct` | `number` | Sí | Pendiente en % |
| `riesgo_hidrico` | `string` | Sí | `bajo` \| `moderado` \| `alto` |
| `elevacion_m` | `number` | No | Elevación media de la zona en metros |
| `dist_huella_m` | `number` | Sí | Distancia a huella urbana en metros |
| `dist_vial_m` | `number` | Sí | Distancia a red vial principal en metros |
| `en_oasis` | `boolean` | No | Zona dentro del oasis irrigado |
| `distrito` | `string` | No | Localidad/distrito más cercano |
| `flags` | `string[]` | Sí | Lista de advertencias (puede estar vacía) |

### Reglas de geometría

- CRS: EPSG:4326 (WGS84)
- Máximo 6 decimales en coordenadas
- Geometría simplificada (tolerancia ~1–2 m)
- `iat` redondeado a entero

---

## Categorías y colores

| Categoría | Label | Color hex |
|-----------|-------|-----------|
| `alta` | Alta aptitud | `#22c55e` |
| `media` | Aptitud media | `#eab308` |
| `baja` | Baja aptitud | `#ef4444` |
| `no_apto` | No apto | `#374151` |

---

## Flags — labels en español

| Flag | Label |
|------|-------|
| `pendiente_elevada` | Pendiente elevada |
| `pendiente_critica` | Pendiente crítica |
| `riesgo_hidrico_alto` | Riesgo hídrico alto |
| `riesgo_hidrico_moderado` | Riesgo hídrico moderado |
| `lejos_de_huella` | Lejos de huella urbana |
| `sin_acceso_vial` | Sin acceso vial |
| `uso_no_permitido` | Uso no permitido |
| `zona_montanosa` | Zona montañosa |
| `altitud_extrema` | Altitud extrema |
| `zona_desertica` | Zona desértica |
| `reserva_natural` | Reserva natural |
| `reserva_hidrica` | Reserva hídrica |
| `zona_embalse` | Zona de embalse |

---

## Diseño

**Tema:** Observatory Noir — dark, acentos cian/amarillo. Reusar tokens del sistema de diseño del sitio principal.

**Paleta base:**
- Fondo mapa: CARTO Dark Matter tiles
- Panel/UI: dark bg con tipografía clara
- Acentos: cian para datos activos, amarillo para alertas/flags

---

*Ver también: [scoring.md](scoring.md) para lógica IAT · [pipeline.md](pipeline.md) para cómo se genera el GeoJSON*
