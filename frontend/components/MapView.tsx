"use client";

import {
  useRef,
  useEffect,
  useCallback,
  useImperativeHandle,
  forwardRef,
} from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { ZoneProperties, Categoria } from "./types";
import { CATEGORY_COLORS } from "./types";
import type { FilterState } from "./FilterControls";
import type { BasemapStyle } from "./LayerToggle";

// ---------------------------------------------------------------------------
// Tipos del simulador de intervención
// ---------------------------------------------------------------------------
export type InterventionType = "ruta" | "hub" | "agua";

export type Intervention =
  | { type: "hub"; coords: [number, number] }
  | { type: "ruta"; coords: [number, number][] }
  | { type: "agua"; coords: [number, number][] };

export type SimSummary = {
  zonasMejoradas: number;
  hectareasDesbloqueadas: number;
  iatPromedioAntes: number;
  iatPromedioDespues: number;
  totalIntervenciones: number;
};

type Weights = { w_norm: number; w_fis: number; w_acc: number };

type MapViewProps = {
  onZoneSelect: (zone: ZoneProperties) => void;
  onHover?: (
    info: { x: number; y: number; properties: Record<string, unknown> } | null
  ) => void;
  onInterventionsChange?: (list: Intervention[]) => void;
  onSimSummary?: (summary: SimSummary | null) => void;
  onReady?: () => void;
};

export type MapViewHandle = {
  recalculateScores: (weights: Weights) => void;
  applyFilters: (filters: FilterState) => void;
  setBasemap: (style: BasemapStyle) => void;
  setSimMode: (type: InterventionType | null) => void;
  clearInterventions: () => void;
  setColorMode: (mode: ColorMode) => void;
  set3D: (enabled: boolean) => void;
};

const BASEMAP_STYLES: Record<BasemapStyle, string> = {
  dark: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
  satellite: "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json",
  streets: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
};

const GEOJSON_PATH = "/data/zonas.geojson";
const SOURCE_ID = "zonas";
const FILL_LAYER_ID = "zonas-fill";
const STROKE_LAYER_ID = "zonas-stroke";
const HIGHLIGHT_LAYER_ID = "zonas-highlight";
const DRAW_SOURCE_ID = "sim-draw";
const DRAW_LINE_LAYER_ID = "sim-draw-line";
const DRAW_POINT_LAYER_ID = "sim-draw-point";
const TERRAIN_SOURCE_ID = "terrain-dem";
const HILLSHADE_LAYER_ID = "terrain-hillshade";
// Tiles terrain-RGB públicos (AWS Open Data, sin API key)
const TERRARIUM_TILES =
  "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png";

// San Rafael center
const DEFAULT_CENTER: [number, number] = [-68.333, -34.6];
const DEFAULT_ZOOM = 9;

const HA_POR_ZONA = 400; // grilla 2km × 2km = 4 km² = 400 ha

function categoryFillColor(): maplibregl.ExpressionSpecification {
  return [
    "match",
    ["get", "categoria"],
    "alta",
    CATEGORY_COLORS.alta,
    "media",
    CATEGORY_COLORS.media,
    "baja",
    CATEGORY_COLORS.baja,
    "no_apto",
    CATEGORY_COLORS.no_apto,
    "#374151",
  ];
}

export type ColorMode = "aptitud" | "deficit";

// Escala secuencial para déficit de servicios (0 = neutro, alto = crítico)
function deficitFillColor(): maplibregl.ExpressionSpecification {
  return [
    "interpolate",
    ["linear"],
    ["coalesce", ["get", "deficit_servicios"], 0],
    0,
    "#1f2937",
    1,
    "#22c55e",
    35,
    "#eab308",
    60,
    "#ef4444",
  ];
}

type Umbrales = { alta: number; media: number };
const DEFAULT_UMBRALES: Umbrales = { alta: 70, media: 40 };

type AccParams = {
  d0_huella_m: number;
  d0_vial_m: number;
  d0_agua_m: number;
  w_huella: number;
  w_vial: number;
  w_agua: number;
};
const DEFAULT_ACC: AccParams = {
  d0_huella_m: 8000,
  d0_vial_m: 5000,
  d0_agua_m: 6000,
  w_huella: 0.45,
  w_vial: 0.35,
  w_agua: 0.2,
};

function classifyIat(
  iat: number,
  isNoApto: boolean,
  umbrales: Umbrales
): Categoria {
  if (isNoApto) return "no_apto";
  if (iat >= umbrales.alta) return "alta";
  if (iat >= umbrales.media) return "media";
  return "baja";
}

const CAT_RANK: Record<Categoria, number> = {
  no_apto: 0,
  baja: 1,
  media: 2,
  alta: 3,
};

function parseFlags(raw: unknown): string[] {
  if (typeof raw === "string") {
    try {
      return JSON.parse(raw);
    } catch {
      return [];
    }
  }
  return Array.isArray(raw) ? raw : [];
}

// --- Geometría: distancias en metros (equirectangular alrededor de San Rafael) ---
const REF_LAT = -34.6;
const M_PER_DEG_LNG = 111320 * Math.cos((REF_LAT * Math.PI) / 180);
const M_PER_DEG_LAT = 110540;

function toXY(lng: number, lat: number): [number, number] {
  return [lng * M_PER_DEG_LNG, lat * M_PER_DEG_LAT];
}

function pointToPointM(a: [number, number], b: [number, number]): number {
  const [ax, ay] = toXY(a[0], a[1]);
  const [bx, by] = toXY(b[0], b[1]);
  return Math.hypot(ax - bx, ay - by);
}

function pointToSegmentM(
  p: [number, number],
  v: [number, number],
  w: [number, number]
): number {
  const [px, py] = toXY(p[0], p[1]);
  const [vx, vy] = toXY(v[0], v[1]);
  const [wx, wy] = toXY(w[0], w[1]);
  const l2 = (vx - wx) ** 2 + (vy - wy) ** 2;
  if (l2 === 0) return Math.hypot(px - vx, py - vy);
  let t = ((px - vx) * (wx - vx) + (py - vy) * (wy - vy)) / l2;
  t = Math.max(0, Math.min(1, t));
  const projx = vx + t * (wx - vx);
  const projy = vy + t * (wy - vy);
  return Math.hypot(px - projx, py - projy);
}

function distanceToIntervention(
  centroid: [number, number],
  itv: Intervention
): number {
  if (itv.type === "hub") return pointToPointM(centroid, itv.coords);
  let min = Infinity;
  for (let i = 0; i < itv.coords.length - 1; i++) {
    const d = pointToSegmentM(centroid, itv.coords[i], itv.coords[i + 1]);
    if (d < min) min = d;
  }
  return min;
}

function polygonCentroid(ring: number[][]): [number, number] {
  let sx = 0;
  let sy = 0;
  const n = ring.length - 1; // último punto repite el primero
  for (let i = 0; i < n; i++) {
    sx += ring[i][0];
    sy += ring[i][1];
  }
  return [sx / n, sy / n];
}

export const MapView = forwardRef<MapViewHandle, MapViewProps>(
  function MapView(
    { onZoneSelect, onHover, onInterventionsChange, onSimSummary, onReady },
    ref
  ) {
    const containerRef = useRef<HTMLDivElement>(null);
    const mapRef = useRef<maplibregl.Map | null>(null);
    const hoveredIdRef = useRef<string | null>(null);
    const geojsonRef = useRef<GeoJSON.FeatureCollection | null>(null);
    const currentFiltersRef = useRef<maplibregl.ExpressionSpecification | null>(
      null
    );

    // Simulador
    const weightsRef = useRef<Weights>({ w_norm: 0.4, w_fis: 0.3, w_acc: 0.3 });
    const interventionsRef = useRef<Intervention[]>([]);
    const drawPointsRef = useRef<[number, number][]>([]);
    const simModeRef = useRef<InterventionType | null>(null);
    const centroidsRef = useRef<Record<string, [number, number]>>({});
    const colorModeRef = useRef<ColorMode>("aptitud");
    const terrain3DRef = useRef(false);
    const onReadyRef = useRef(onReady);
    onReadyRef.current = onReady;

    // Activa/desactiva terreno 3D (terrarium) + hillshade + pitch.
    const applyTerrain = useCallback((enabled: boolean) => {
      const map = mapRef.current;
      if (!map) return;
      terrain3DRef.current = enabled;
      if (enabled) {
        map.setTerrain({ source: TERRAIN_SOURCE_ID, exaggeration: 1.4 });
        if (!map.getLayer(HILLSHADE_LAYER_ID)) {
          map.addLayer(
            {
              id: HILLSHADE_LAYER_ID,
              type: "hillshade",
              source: TERRAIN_SOURCE_ID,
              paint: { "hillshade-exaggeration": 0.45 },
            },
            FILL_LAYER_ID // debajo de las zonas
          );
        }
        map.easeTo({ pitch: 62, duration: 800 });
      } else {
        map.setTerrain(null);
        if (map.getLayer(HILLSHADE_LAYER_ID)) map.removeLayer(HILLSHADE_LAYER_ID);
        map.easeTo({ pitch: 0, duration: 800 });
      }
    }, []);

    const handleZoneSelect = useCallback(
      (zone: ZoneProperties) => onZoneSelect(zone),
      [onZoneSelect]
    );

    // Recálculo unificado: aplica pesos actuales + intervenciones activas.
    const recomputeAll = useCallback(() => {
      const map = mapRef.current;
      const geojson = geojsonRef.current;
      if (!map || !geojson) return;

      const w = weightsRef.current;
      const interventions = interventionsRef.current;
      const meta = (
        geojson as {
          metadata?: { umbrales?: Umbrales; accesibilidad?: AccParams };
        }
      ).metadata;
      const umbrales = meta?.umbrales ?? DEFAULT_UMBRALES;
      const acc = meta?.accesibilidad ?? DEFAULT_ACC;
      const hasItv = interventions.length > 0;

      let sumBefore = 0;
      let sumAfter = 0;
      let affected = 0;
      let mejoradas = 0;

      const features = geojson.features.map((f) => {
        const p = f.properties!;
        const isNoApto =
          String(p.uso_permitido).includes("reserva") ||
          (p.elevacion_m != null && Number(p.elevacion_m) > 3000);

        const sAccBase = Number(p.s_acc);
        let sAcc = sAccBase;

        if (hasItv && !isNoApto) {
          const c = centroidsRef.current[String(p.id)];
          if (c) {
            let dh = Number(p.dist_huella_m);
            let dv = Number(p.dist_vial_m);
            let da =
              p.dist_agua_m != null ? Number(p.dist_agua_m) : Infinity;
            let changed = false;
            for (const itv of interventions) {
              const d = distanceToIntervention(c, itv);
              if (itv.type === "hub" && d < dh) {
                dh = d;
                changed = true;
              } else if (itv.type === "ruta" && d < dv) {
                dv = d;
                changed = true;
              } else if (itv.type === "agua" && d < da) {
                da = d;
                changed = true;
              }
            }
            if (changed) {
              sAcc =
                acc.w_huella * Math.exp(-dh / acc.d0_huella_m) +
                acc.w_vial * Math.exp(-dv / acc.d0_vial_m) +
                acc.w_agua * Math.exp(-da / acc.d0_agua_m);
            }
          }
        }

        const base =
          w.w_norm * Number(p.s_norm) + w.w_fis * Number(p.s_fis);
        const iatBefore = isNoApto
          ? 0
          : Math.round(100 * (base + w.w_acc * sAccBase));
        const iatAfter = isNoApto
          ? 0
          : Math.round(100 * (base + w.w_acc * sAcc));
        const categoria = classifyIat(iatAfter, isNoApto, umbrales);

        if (hasItv && iatAfter !== iatBefore) {
          affected++;
          sumBefore += iatBefore;
          sumAfter += iatAfter;
          const catBefore = classifyIat(iatBefore, isNoApto, umbrales);
          if (CAT_RANK[categoria] > CAT_RANK[catBefore]) mejoradas++;
        }

        return { ...f, properties: { ...p, iat: iatAfter, categoria } };
      });

      const source = map.getSource(SOURCE_ID) as
        | maplibregl.GeoJSONSource
        | undefined;
      if (source)
        source.setData({ type: "FeatureCollection", features });

      if (onSimSummary) {
        onSimSummary(
          hasItv
            ? {
                zonasMejoradas: mejoradas,
                hectareasDesbloqueadas: mejoradas * HA_POR_ZONA,
                iatPromedioAntes: affected ? sumBefore / affected : 0,
                iatPromedioDespues: affected ? sumAfter / affected : 0,
                totalIntervenciones: interventions.length,
              }
            : null
        );
      }
    }, [onSimSummary]);

    // Dibuja las intervenciones colocadas + traza en progreso.
    const updateDrawLayer = useCallback(() => {
      const map = mapRef.current;
      if (!map) return;
      const source = map.getSource(DRAW_SOURCE_ID) as
        | maplibregl.GeoJSONSource
        | undefined;
      if (!source) return;

      const feats: GeoJSON.Feature[] = [];
      for (const itv of interventionsRef.current) {
        if (itv.type === "hub") {
          feats.push({
            type: "Feature",
            properties: { kind: "hub" },
            geometry: { type: "Point", coordinates: itv.coords },
          });
        } else {
          feats.push({
            type: "Feature",
            properties: { kind: itv.type },
            geometry: { type: "LineString", coordinates: itv.coords },
          });
        }
      }
      // Traza en progreso
      const pts = drawPointsRef.current;
      if (pts.length >= 2) {
        feats.push({
          type: "Feature",
          properties: { kind: "draft" },
          geometry: { type: "LineString", coordinates: pts },
        });
      }
      for (const pt of pts) {
        feats.push({
          type: "Feature",
          properties: { kind: "vertex" },
          geometry: { type: "Point", coordinates: pt },
        });
      }
      source.setData({ type: "FeatureCollection", features: feats });
    }, []);

    const addDataLayers = useCallback(
      (map: maplibregl.Map, geojson: GeoJSON.FeatureCollection) => {
        if (map.getSource(SOURCE_ID)) return;

        // Fuente de terreno (raster-dem terrarium) — siempre presente, se
        // usa solo cuando el 3D está activo.
        if (!map.getSource(TERRAIN_SOURCE_ID)) {
          map.addSource(TERRAIN_SOURCE_ID, {
            type: "raster-dem",
            tiles: [TERRARIUM_TILES],
            encoding: "terrarium",
            tileSize: 256,
            maxzoom: 14,
          });
        }

        map.addSource(SOURCE_ID, {
          type: "geojson",
          data: geojson,
          promoteId: "id",
        });

        map.addLayer({
          id: FILL_LAYER_ID,
          type: "fill",
          source: SOURCE_ID,
          paint: {
            "fill-color":
              colorModeRef.current === "deficit"
                ? deficitFillColor()
                : categoryFillColor(),
            "fill-opacity": [
              "case",
              ["boolean", ["feature-state", "hover"], false],
              0.8,
              0.55,
            ],
          },
        });

        map.addLayer({
          id: STROKE_LAYER_ID,
          type: "line",
          source: SOURCE_ID,
          paint: {
            "line-color": [
              "case",
              ["boolean", ["feature-state", "hover"], false],
              "#ffffff",
              "rgba(255, 255, 255, 0.15)",
            ],
            "line-width": [
              "case",
              ["boolean", ["feature-state", "hover"], false],
              2,
              0.5,
            ],
          },
        });

        map.addLayer({
          id: HIGHLIGHT_LAYER_ID,
          type: "line",
          source: SOURCE_ID,
          paint: {
            "line-color": "#22d3ee",
            "line-width": 3,
            "line-dasharray": [2, 2],
          },
          filter: ["==", "id", ""],
        });

        // Capas de dibujo del simulador
        if (!map.getSource(DRAW_SOURCE_ID)) {
          map.addSource(DRAW_SOURCE_ID, {
            type: "geojson",
            data: { type: "FeatureCollection", features: [] },
          });
          map.addLayer({
            id: DRAW_LINE_LAYER_ID,
            type: "line",
            source: DRAW_SOURCE_ID,
            paint: {
              "line-color": [
                "match",
                ["get", "kind"],
                "agua",
                "#3b82f6",
                "ruta",
                "#22d3ee",
                "#22d3ee",
              ],
              "line-width": 4,
              "line-opacity": 0.9,
            },
          });
          map.addLayer({
            id: DRAW_POINT_LAYER_ID,
            type: "circle",
            source: DRAW_SOURCE_ID,
            paint: {
              "circle-radius": [
                "match",
                ["get", "kind"],
                "hub",
                8,
                5,
              ],
              "circle-color": [
                "match",
                ["get", "kind"],
                "hub",
                "#22d3ee",
                "#ffffff",
              ],
              "circle-stroke-color": "#0a0e14",
              "circle-stroke-width": 2,
            },
          });
        }

        // Fit bounds to data
        const bounds = new maplibregl.LngLatBounds();
        for (const feature of geojson.features) {
          if (
            feature.geometry.type === "Polygon" &&
            feature.geometry.coordinates[0]
          ) {
            for (const coord of feature.geometry.coordinates[0]) {
              bounds.extend(coord as [number, number]);
            }
          }
        }
        if (!bounds.isEmpty()) {
          map.fitBounds(bounds, { padding: 40, maxZoom: 14 });
        }

        // Hover
        map.on("mousemove", FILL_LAYER_ID, (e) => {
          if (simModeRef.current) return;
          if (!e.features || e.features.length === 0) return;
          map.getCanvas().style.cursor = "pointer";

          const featureId = e.features[0].properties?.id as string;

          if (
            hoveredIdRef.current !== null &&
            hoveredIdRef.current !== featureId
          ) {
            map.setFeatureState(
              { source: SOURCE_ID, id: hoveredIdRef.current },
              { hover: false }
            );
          }

          hoveredIdRef.current = featureId;
          map.setFeatureState(
            { source: SOURCE_ID, id: featureId },
            { hover: true }
          );

          if (onHover) {
            onHover({
              x: e.point.x,
              y: e.point.y,
              properties: e.features[0].properties as Record<string, unknown>,
            });
          }
        });

        map.on("mouseleave", FILL_LAYER_ID, () => {
          if (!simModeRef.current) map.getCanvas().style.cursor = "";
          if (hoveredIdRef.current !== null) {
            map.setFeatureState(
              { source: SOURCE_ID, id: hoveredIdRef.current },
              { hover: false }
            );
            hoveredIdRef.current = null;
          }
          if (onHover) onHover(null);
        });

        // Click en zona (deshabilitado en modo simulación)
        map.on("click", FILL_LAYER_ID, (e) => {
          if (simModeRef.current) return;
          if (!e.features || e.features.length === 0) return;
          const props = e.features[0].properties;
          if (!props) return;

          const zoneData: ZoneProperties = {
            id: String(props.id),
            iat: Number(props.iat),
            categoria: String(props.categoria) as Categoria,
            s_norm: Number(props.s_norm),
            s_fis: Number(props.s_fis),
            s_acc: Number(props.s_acc),
            uso_permitido: String(props.uso_permitido),
            pendiente_pct: Number(props.pendiente_pct),
            riesgo_hidrico: String(props.riesgo_hidrico),
            elevacion_m:
              props.elevacion_m != null ? Number(props.elevacion_m) : undefined,
            dist_huella_m: Number(props.dist_huella_m),
            dist_vial_m: Number(props.dist_vial_m),
            dist_agua_m:
              props.dist_agua_m != null ? Number(props.dist_agua_m) : undefined,
            poblacion_est:
              props.poblacion_est != null
                ? Number(props.poblacion_est)
                : undefined,
            dist_escuela_m:
              props.dist_escuela_m != null
                ? Number(props.dist_escuela_m)
                : undefined,
            dist_salud_m:
              props.dist_salud_m != null
                ? Number(props.dist_salud_m)
                : undefined,
            deficit_servicios:
              props.deficit_servicios != null
                ? Number(props.deficit_servicios)
                : undefined,
            en_oasis:
              props.en_oasis != null ? Boolean(props.en_oasis) : undefined,
            distrito: props.distrito ? String(props.distrito) : undefined,
            flags: parseFlags(props.flags),
          };

          map.setFilter(HIGHLIGHT_LAYER_ID, ["==", "id", zoneData.id]);
          handleZoneSelect(zoneData);
        });

        // Click a nivel mapa: colocar intervención
        map.on("click", (e) => {
          const mode = simModeRef.current;
          if (!mode) return;
          const lngLat: [number, number] = [e.lngLat.lng, e.lngLat.lat];
          if (mode === "hub") {
            interventionsRef.current = [
              ...interventionsRef.current,
              { type: "hub", coords: lngLat },
            ];
            onInterventionsChange?.(interventionsRef.current);
            recomputeAll();
            updateDrawLayer();
          } else {
            drawPointsRef.current = [...drawPointsRef.current, lngLat];
            updateDrawLayer();
          }
        });

        // Doble click: cerrar la traza (ruta/agua)
        map.on("dblclick", (e) => {
          const mode = simModeRef.current;
          if (!mode || mode === "hub") return;
          e.preventDefault();
          const pts = drawPointsRef.current;
          if (pts.length >= 2) {
            interventionsRef.current = [
              ...interventionsRef.current,
              { type: mode, coords: [...pts] },
            ];
            onInterventionsChange?.(interventionsRef.current);
            recomputeAll();
          }
          drawPointsRef.current = [];
          updateDrawLayer();
        });

        // Reapply filters if they existed
        if (currentFiltersRef.current) {
          map.setFilter(FILL_LAYER_ID, currentFiltersRef.current);
          map.setFilter(STROKE_LAYER_ID, currentFiltersRef.current);
        }

        // Reaplicar terreno 3D tras cambio de basemap
        if (terrain3DRef.current) applyTerrain(true);
      },
      [
        handleZoneSelect,
        onHover,
        onInterventionsChange,
        recomputeAll,
        updateDrawLayer,
        applyTerrain,
      ]
    );

    useImperativeHandle(
      ref,
      () => ({
        recalculateScores(weights) {
          weightsRef.current = weights;
          recomputeAll();
        },

        applyFilters(filters: FilterState) {
          const map = mapRef.current;
          if (!map) return;

          const conditions: maplibregl.ExpressionSpecification[] = [];
          const cats = Array.from(filters.categories);
          if (cats.length < 4) {
            conditions.push(["in", ["get", "categoria"], ["literal", cats]]);
          }
          if (filters.minIat > 0) {
            conditions.push([">=", ["get", "iat"], filters.minIat]);
          }
          if (filters.maxPendiente < 100) {
            conditions.push([
              "<=",
              ["get", "pendiente_pct"],
              filters.maxPendiente,
            ]);
          }
          if (filters.hideRiesgoAlto) {
            conditions.push(["!=", ["get", "riesgo_hidrico"], "alto"]);
          }

          const filter: maplibregl.ExpressionSpecification | null =
            conditions.length === 0
              ? null
              : conditions.length === 1
                ? conditions[0]
                : ["all", ...conditions];

          currentFiltersRef.current = filter;

          if (map.getLayer(FILL_LAYER_ID)) map.setFilter(FILL_LAYER_ID, filter);
          if (map.getLayer(STROKE_LAYER_ID))
            map.setFilter(STROKE_LAYER_ID, filter);
        },

        setBasemap(style: BasemapStyle) {
          const map = mapRef.current;
          const geojson = geojsonRef.current;
          if (!map || !geojson) return;

          const center = map.getCenter();
          const zoom = map.getZoom();
          const pitch = map.getPitch();
          const bearing = map.getBearing();

          map.setStyle(BASEMAP_STYLES[style]);

          map.once("style.load", () => {
            map.setCenter(center);
            map.setZoom(zoom);
            map.setPitch(pitch);
            map.setBearing(bearing);
            addDataLayers(map, geojson);
            updateDrawLayer();
            recomputeAll();
          });
        },

        setSimMode(type: InterventionType | null) {
          const map = mapRef.current;
          simModeRef.current = type;
          drawPointsRef.current = [];
          updateDrawLayer();
          if (!map) return;
          if (type && type !== "hub") map.doubleClickZoom.disable();
          else map.doubleClickZoom.enable();
          map.getCanvas().style.cursor = type ? "crosshair" : "";
        },

        clearInterventions() {
          interventionsRef.current = [];
          drawPointsRef.current = [];
          onInterventionsChange?.([]);
          updateDrawLayer();
          recomputeAll();
        },

        setColorMode(mode: ColorMode) {
          colorModeRef.current = mode;
          const map = mapRef.current;
          if (!map || !map.getLayer(FILL_LAYER_ID)) return;
          map.setPaintProperty(
            FILL_LAYER_ID,
            "fill-color",
            mode === "deficit" ? deficitFillColor() : categoryFillColor()
          );
        },

        set3D(enabled: boolean) {
          applyTerrain(enabled);
        },
      }),
      [
        addDataLayers,
        recomputeAll,
        updateDrawLayer,
        onInterventionsChange,
        applyTerrain,
      ]
    );

    useEffect(() => {
      const container = containerRef.current;
      if (!container) return;

      const map = new maplibregl.Map({
        container,
        style: BASEMAP_STYLES.dark,
        center: DEFAULT_CENTER,
        zoom: DEFAULT_ZOOM,
        pitch: 0,
        bearing: 0,
        attributionControl: false,
        maxZoom: 18,
        minZoom: 6,
      });

      map.addControl(
        new maplibregl.NavigationControl({ showCompass: true }),
        "top-left"
      );
      map.addControl(new maplibregl.ScaleControl({}), "bottom-right");

      mapRef.current = map;

      map.on("load", async () => {
        try {
          const response = await fetch(GEOJSON_PATH);
          const geojson = await response.json();
          geojsonRef.current = geojson;
          // Precomputar centroides para el simulador
          const centroids: Record<string, [number, number]> = {};
          for (const f of geojson.features as GeoJSON.Feature[]) {
            if (
              f.geometry.type === "Polygon" &&
              f.properties?.id != null
            ) {
              centroids[String(f.properties.id)] = polygonCentroid(
                f.geometry.coordinates[0] as number[][]
              );
            }
          }
          centroidsRef.current = centroids;
          addDataLayers(map, geojson);
          onReadyRef.current?.();
        } catch (err) {
          console.error("Failed to load zonas.geojson:", err);
          onReadyRef.current?.();
        }
      });

      return () => {
        map.remove();
        mapRef.current = null;
      };
    }, [addDataLayers]);

    return (
      <div
        ref={containerRef}
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          width: "100%",
          height: "100%",
          background: "var(--bg-void)",
        }}
      />
    );
  }
);
