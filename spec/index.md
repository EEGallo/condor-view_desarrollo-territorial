# Cóndor View — Índice de Aptitud Territorial

**Producto:** Mapa web interactivo que puntúa zonas no desarrolladas según aptitud para inversión inmobiliaria.  
**Enfoque:** Análisis multicriterio ponderado, sin ML, transparente y explicable.  
**Métrica de éxito:** Un desarrollador/inversor real dice *"esto cambiaría mi decisión de compra / pagaría por esto."*

---

## Arquitectura

```
┌──────────────────────────────────────────┐
│  PIPELINE OFFLINE (Python, corre 1 vez)   │
│  config.yaml + datos → generate_zones.py  │
│  Salida: zonas.geojson (estático)          │
└─────────────────┬────────────────────────┘
                  │  commit / deploy
                  ▼
┌──────────────────────────────────────────┐
│  FRONTEND (Next.js + MapLibre, Vercel)    │
│  Carga zonas.geojson → mapa interactivo   │
│  Click en zona → panel con desglose IAT   │
└──────────────────────────────────────────┘
```

Sin base de datos, sin API, sin login. El "modelo" es un archivo GeoJSON precalculado.

---

## Piloto: San Rafael, Mendoza

| Parámetro | Valor |
|-----------|-------|
| Departamento | San Rafael, Mendoza, Argentina |
| Superficie | 31,235 km² |
| Población | ~215,000 hab |
| Bounding box | W -70.17, S -36.00, E -66.92, N -34.25 |
| CRS trabajo | EPSG:5343 (POSGAR 2007 faja 3) |
| CRS salida | EPSG:4326 (WGS84) |
| Grilla | 2 km × 2 km |
| Zonas totales | ~14,136 |
| Oasis irrigado | ~6.5% del territorio (~916 zonas) |

---

## Estado de implementación

| Componente | Estado | Notas |
|------------|--------|-------|
| Pipeline sintético (`generate_zones.py`) | ✅ Listo | Genera desde config.yaml |
| GeoJSON exportado (`zonas.geojson`) | ✅ Listo | ~14,136 zonas San Rafael |
| Frontend — `MapView` | ✅ Listo | MapLibre + colores por categoría |
| Frontend — `ZonePanel` | ✅ Listo | Desglose IAT + flags |
| Frontend — `Legend` | ✅ Listo | |
| Frontend — `WeightControls` | ✅ Listo | Sliders recalculan IAT en cliente |
| Frontend — `FilterControls` | ✅ Listo | |
| Frontend — `LayerToggle` | ✅ Listo | |
| Frontend — `ExportButton` | ✅ Listo | |
| Frontend — `StatsBar` | ✅ Listo | |
| Frontend — `MapTooltip` | ✅ Listo | |
| DEM real (IGN MDE-Ar / SRTM) | ⏳ Pendiente | Reemplaza elevación sintética |
| OSM descarga real | ⏳ Pendiente | Rutas + huella urbana reales |
| Catastro / parcelas | ⏳ Pendiente | IDE Mendoza — compuerta |
| Zonificación municipal real | ⏳ Pendiente | Ordenanza San Rafael — trabajo pesado |
| Validación de pesos con urbanista | ⏳ Pendiente | Requisito antes de mostrar a clientes |

---

## Principios de diseño

1. **Sin backend.** Todo cómputo offline; frontend sirve archivos estáticos. Costo hosting ≈ 0.
2. **Explicabilidad = producto.** Cada puntaje auditable. El "por qué" se muestra siempre.
3. **Parámetros en config, no en código.** Pesos y umbrales en `pipeline/config.yaml`.
4. **Datos primero.** No se invierte en motor completo hasta confirmar fuentes reales.
5. **El demo es portfolio.** Embebible en `/condor-view`.

---

## Fuera de alcance (MVP)

Machine learning · predicción temporal · gemelo digital 3D · asistente conversacional · multi-ciudad · redes completas de infraestructura · cuentas de usuario · app móvil.

---

## Riesgos abiertos

| ID | Probabilidad | Descripción | Mitigación |
|----|-------------|-------------|------------|
| R1 | Alto | Catastro o zonificación no disponibles | Fallback a grilla 2km (ya implementado) |
| R2 | Medio | Acceso al MDE del IGN para uso no académico | Alternativa: SRTM / Copernicus global |
| R3 | Medio | Pesos del scoring arbitrarios sin validar | Validación con urbanista antes de clientes |

---

*Ver también: [scoring.md](scoring.md) · [data.md](data.md) · [frontend.md](frontend.md) · [pipeline.md](pipeline.md)*
