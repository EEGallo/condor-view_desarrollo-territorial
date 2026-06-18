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

type MapViewProps = {
  onZoneSelect: (zone: ZoneProperties) => void;
  onHover?: (
    info: { x: number; y: number; properties: Record<string, unknown> } | null
  ) => void;
};

export type MapViewHandle = {
  recalculateScores: (weights: {
    w_norm: number;
    w_fis: number;
    w_acc: number;
  }) => void;
  applyFilters: (filters: FilterState) => void;
  setBasemap: (style: BasemapStyle) => void;
};

const BASEMAP_STYLES: Record<BasemapStyle, string> = {
  dark: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
  satellite:
    "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json",
  streets:
    "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
};

const GEOJSON_PATH = "/data/zonas.geojson";
const SOURCE_ID = "zonas";
const FILL_LAYER_ID = "zonas-fill";
const STROKE_LAYER_ID = "zonas-stroke";
const HIGHLIGHT_LAYER_ID = "zonas-highlight";

// San Rafael center
const DEFAULT_CENTER: [number, number] = [-68.333, -34.600];
const DEFAULT_ZOOM = 9;

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

type Umbrales = { alta: number; media: number };
const DEFAULT_UMBRALES: Umbrales = { alta: 70, media: 40 };

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

export const MapView = forwardRef<MapViewHandle, MapViewProps>(
  function MapView({ onZoneSelect, onHover }, ref) {
    const containerRef = useRef<HTMLDivElement>(null);
    const mapRef = useRef<maplibregl.Map | null>(null);
    const hoveredIdRef = useRef<string | null>(null);
    const geojsonRef = useRef<GeoJSON.FeatureCollection | null>(null);
    const currentFiltersRef = useRef<maplibregl.ExpressionSpecification | null>(
      null
    );

    const handleZoneSelect = useCallback(
      (zone: ZoneProperties) => onZoneSelect(zone),
      [onZoneSelect]
    );

    const addDataLayers = useCallback(
      (map: maplibregl.Map, geojson: GeoJSON.FeatureCollection) => {
        if (map.getSource(SOURCE_ID)) return;

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
            "fill-color": categoryFillColor(),
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
          map.getCanvas().style.cursor = "";
          if (hoveredIdRef.current !== null) {
            map.setFeatureState(
              { source: SOURCE_ID, id: hoveredIdRef.current },
              { hover: false }
            );
            hoveredIdRef.current = null;
          }
          if (onHover) onHover(null);
        });

        // Click
        map.on("click", FILL_LAYER_ID, (e) => {
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
            elevacion_m: props.elevacion_m != null ? Number(props.elevacion_m) : undefined,
            dist_huella_m: Number(props.dist_huella_m),
            dist_vial_m: Number(props.dist_vial_m),
            en_oasis: props.en_oasis != null ? Boolean(props.en_oasis) : undefined,
            distrito: props.distrito ? String(props.distrito) : undefined,
            flags: parseFlags(props.flags),
          };

          map.setFilter(HIGHLIGHT_LAYER_ID, ["==", "id", zoneData.id]);
          handleZoneSelect(zoneData);
        });

        // Reapply filters if they existed
        if (currentFiltersRef.current) {
          map.setFilter(FILL_LAYER_ID, currentFiltersRef.current);
          map.setFilter(STROKE_LAYER_ID, currentFiltersRef.current);
        }
      },
      [handleZoneSelect, onHover]
    );

    useImperativeHandle(
      ref,
      () => ({
        recalculateScores(weights) {
          const map = mapRef.current;
          const geojson = geojsonRef.current;
          if (!map || !geojson) return;

          const umbrales =
            (geojson as { metadata?: { umbrales?: Umbrales } }).metadata
              ?.umbrales ?? DEFAULT_UMBRALES;

          const updated: GeoJSON.FeatureCollection = {
            type: "FeatureCollection",
            features: geojson.features.map((f) => {
              const p = f.properties!;
              const isNoApto =
                String(p.uso_permitido).includes("reserva") ||
                (p.elevacion_m != null && Number(p.elevacion_m) > 3000);
              const iat = isNoApto
                ? 0
                : Math.round(
                    100 *
                      (weights.w_norm * p.s_norm +
                        weights.w_fis * p.s_fis +
                        weights.w_acc * p.s_acc)
                  );
              const categoria = classifyIat(iat, isNoApto, umbrales);
              return { ...f, properties: { ...p, iat, categoria } };
            }),
          };

          const source = map.getSource(SOURCE_ID) as
            | maplibregl.GeoJSONSource
            | undefined;
          if (source) source.setData(updated);
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
          });
        },
      }),
      [addDataLayers]
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
          addDataLayers(map, geojson);
        } catch (err) {
          console.error("Failed to load zonas.geojson:", err);
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
