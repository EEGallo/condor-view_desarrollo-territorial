"use client";

import { useState, useCallback, useRef } from "react";
import { MapView } from "@/components/MapView";
import { ZonePanel } from "@/components/ZonePanel";
import { Legend } from "@/components/Legend";
import { WeightControls } from "@/components/WeightControls";
import { FilterControls } from "@/components/FilterControls";
import { StatsBar } from "@/components/StatsBar";
import { MapTooltip } from "@/components/MapTooltip";
import { LayerToggle } from "@/components/LayerToggle";
import type { ZoneProperties, Categoria } from "@/components/types";
import type { MapViewHandle } from "@/components/MapView";
import type { FilterState } from "@/components/FilterControls";
import type { BasemapStyle } from "@/components/LayerToggle";

type HoverInfo = {
  x: number;
  y: number;
  id: string;
  iat: number;
  categoria: Categoria;
  uso: string;
};

export default function Home() {
  const [selectedZone, setSelectedZone] = useState<ZoneProperties | null>(null);
  const [hoverInfo, setHoverInfo] = useState<HoverInfo | null>(null);
  const mapRef = useRef<MapViewHandle>(null);

  const handleZoneSelect = useCallback((zone: ZoneProperties) => {
    setSelectedZone(zone);
    setHoverInfo(null);
  }, []);

  const handleClose = useCallback(() => {
    setSelectedZone(null);
  }, []);

  const handleWeightsChange = useCallback(
    (weights: { w_norm: number; w_fis: number; w_acc: number }) => {
      mapRef.current?.recalculateScores(weights);
    },
    []
  );

  const handleFiltersChange = useCallback((filters: FilterState) => {
    mapRef.current?.applyFilters(filters);
  }, []);

  const handleHover = useCallback(
    (info: { x: number; y: number; properties: Record<string, unknown> } | null) => {
      if (!info) {
        setHoverInfo(null);
        return;
      }
      setHoverInfo({
        x: info.x,
        y: info.y,
        id: String(info.properties.id),
        iat: Number(info.properties.iat),
        categoria: String(info.properties.categoria) as Categoria,
        uso: String(info.properties.uso_permitido),
      });
    },
    []
  );

  const handleStyleChange = useCallback((style: BasemapStyle) => {
    mapRef.current?.setBasemap(style);
  }, []);

  return (
    <main className="relative" style={{ width: "100vw", height: "100vh" }}>
      {/* Title */}
      <div className="pointer-events-none fixed top-6 left-6 z-20 flex flex-col gap-1">
        <h1
          className="text-lg font-bold tracking-tight"
          style={{ color: "var(--text-primary)" }}
        >
          Cóndor View
        </h1>
        <p
          className="text-[11px] tracking-wide"
          style={{ color: "var(--text-muted)" }}
        >
          Observatorio de Aptitud Territorial — San Rafael, Mendoza
        </p>
      </div>

      <MapView
        ref={mapRef}
        onZoneSelect={handleZoneSelect}
        onHover={handleHover}
      />

      {/* Controls */}
      <LayerToggle onStyleChange={handleStyleChange} />
      <FilterControls onFiltersChange={handleFiltersChange} />
      <WeightControls onWeightsChange={handleWeightsChange} />

      {/* Hover tooltip */}
      {hoverInfo && !selectedZone && (
        <MapTooltip
          x={hoverInfo.x}
          y={hoverInfo.y}
          id={hoverInfo.id}
          iat={hoverInfo.iat}
          categoria={hoverInfo.categoria}
          uso={hoverInfo.uso}
          visible
        />
      )}

      {/* Info panels */}
      <Legend />
      <StatsBar />

      {/* Detail panel */}
      <ZonePanel zone={selectedZone} onClose={handleClose} />
    </main>
  );
}
