"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { MapView } from "@/components/MapView";
import { ZonePanel } from "@/components/ZonePanel";
import { Legend } from "@/components/Legend";
import { WeightControls } from "@/components/WeightControls";
import { FilterControls } from "@/components/FilterControls";
import { StatsBar } from "@/components/StatsBar";
import { MapTooltip } from "@/components/MapTooltip";
import { LayerToggle } from "@/components/LayerToggle";
import { InterventionControls } from "@/components/InterventionControls";
import { InterventionSummary } from "@/components/InterventionSummary";
import { ViewModeToggle } from "@/components/ViewModeToggle";
import { TerrainToggle } from "@/components/TerrainToggle";
import { LoadingOverlay } from "@/components/LoadingOverlay";
import { IntroHint } from "@/components/IntroHint";
import { ProjectsControl } from "@/components/ProjectsControl";
import { ProjectForm } from "@/components/ProjectForm";
import type { ProjectFormData } from "@/components/ProjectForm";
import { ProjectPanel } from "@/components/ProjectPanel";
import { ExtractControl } from "@/components/ExtractControl";
import { ExtractPanel } from "@/components/ExtractPanel";
import type {
  ZoneProperties,
  Categoria,
  Proyecto,
  ExtractContext,
} from "@/components/types";
import type {
  MapViewHandle,
  Intervention,
  InterventionType,
  SimSummary,
  ColorMode,
} from "@/components/MapView";
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

const PROJECTS_KEY = "condor_proyectos_v1";

export default function Home() {
  const [selectedZone, setSelectedZone] = useState<ZoneProperties | null>(null);
  const [hoverInfo, setHoverInfo] = useState<HoverInfo | null>(null);
  const [interventions, setInterventions] = useState<Intervention[]>([]);
  const [simSummary, setSimSummary] = useState<SimSummary | null>(null);
  const [colorMode, setColorMode] = useState<ColorMode>("aptitud");
  const [loading, setLoading] = useState(true);
  const [projects, setProjects] = useState<Proyecto[]>([]);
  const [projectsVisible, setProjectsVisible] = useState(true);
  const [addingProject, setAddingProject] = useState(false);
  const [pendingCoords, setPendingCoords] = useState<[number, number] | null>(
    null
  );
  const [selectedProject, setSelectedProject] = useState<Proyecto | null>(null);
  const [drawing, setDrawing] = useState(false);
  const [extractCtx, setExtractCtx] = useState<ExtractContext | null>(null);
  const [extractLoading, setExtractLoading] = useState(false);
  const [extractError, setExtractError] = useState<string | null>(null);
  const mapRef = useRef<MapViewHandle>(null);

  const handleReady = useCallback(() => setLoading(false), []);

  const API_BASE =
    process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  const handleToggleDraw = useCallback((v: boolean) => {
    setDrawing(v);
    mapRef.current?.setDrawPolygonMode(v);
    if (v) {
      setSelectedZone(null);
      setSelectedProject(null);
    }
  }, []);

  const handlePolygonComplete = useCallback(
    async (polygon: GeoJSON.Polygon) => {
      setDrawing(false);
      mapRef.current?.setDrawPolygonMode(false);
      setExtractError(null);
      setExtractLoading(true);
      setExtractCtx(null);
      try {
        const res = await fetch(`${API_BASE}/api/extract`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ polygon }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        setExtractCtx((await res.json()) as ExtractContext);
      } catch (err) {
        setExtractError(
          `No se pudo extraer el contexto (${
            err instanceof Error ? err.message : "error"
          }). ¿Está corriendo el backend en ${API_BASE}?`
        );
      } finally {
        setExtractLoading(false);
      }
    },
    [API_BASE]
  );

  const handleExtractClose = useCallback(() => {
    setExtractCtx(null);
    setExtractError(null);
    setExtractLoading(false);
    mapRef.current?.clearDrawPolygon();
  }, []);

  // Cargar proyectos: seed estático + altas locales (localStorage)
  useEffect(() => {
    let local: Proyecto[] = [];
    try {
      local = JSON.parse(localStorage.getItem(PROJECTS_KEY) || "[]");
    } catch {
      local = [];
    }
    fetch("/data/proyectos.json")
      .then((r) => r.json())
      .then((seed: Proyecto[]) => setProjects([...seed, ...local]))
      .catch(() => setProjects(local));
  }, []);

  const persistLocal = useCallback((all: Proyecto[]) => {
    const local = all.filter((p) => p.id.startsWith("P-local"));
    try {
      localStorage.setItem(PROJECTS_KEY, JSON.stringify(local));
    } catch {
      /* ignore */
    }
  }, []);

  const handleToggleAddProject = useCallback((v: boolean) => {
    setAddingProject(v);
    mapRef.current?.setProjectMode(v);
  }, []);

  const handleProjectPlaced = useCallback((coords: [number, number]) => {
    setPendingCoords(coords);
    setAddingProject(false);
    mapRef.current?.setProjectMode(false);
  }, []);

  const handleSaveProject = useCallback(
    (data: ProjectFormData) => {
      if (!pendingCoords) return;
      const nuevo: Proyecto = {
        id: `P-local-${Date.now()}`,
        coords: pendingCoords,
        ...data,
      };
      setProjects((prev) => {
        const all = [...prev, nuevo];
        persistLocal(all);
        return all;
      });
      setPendingCoords(null);
    },
    [pendingCoords, persistLocal]
  );

  const handleDeleteProject = useCallback(
    (id: string) => {
      setProjects((prev) => {
        const all = prev.filter((p) => p.id !== id);
        persistLocal(all);
        return all;
      });
      setSelectedProject(null);
    },
    [persistLocal]
  );

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

  const handleSimModeChange = useCallback((type: InterventionType | null) => {
    mapRef.current?.setSimMode(type);
  }, []);

  const handleClearInterventions = useCallback(() => {
    mapRef.current?.clearInterventions();
  }, []);

  const handleColorModeChange = useCallback((mode: ColorMode) => {
    setColorMode(mode);
    mapRef.current?.setColorMode(mode);
  }, []);

  const handleTerrainToggle = useCallback((enabled: boolean) => {
    mapRef.current?.set3D(enabled);
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
          Potencial de Desarrollo Territorial — San Rafael, Mendoza
        </p>
      </div>

      <MapView
        ref={mapRef}
        onZoneSelect={handleZoneSelect}
        onHover={handleHover}
        onInterventionsChange={setInterventions}
        onSimSummary={setSimSummary}
        onReady={handleReady}
        projects={projects}
        projectsVisible={projectsVisible}
        onProjectPlaced={handleProjectPlaced}
        onProjectSelect={setSelectedProject}
        onPolygonComplete={handlePolygonComplete}
      />

      {/* Controls */}
      <LayerToggle onStyleChange={handleStyleChange} />
      <TerrainToggle onToggle={handleTerrainToggle} />

      {/* Toolbar superior derecha — fila flex para que no se superpongan */}
      <div className="fixed top-6 right-6 z-20 flex flex-wrap items-start justify-end gap-2">
        <FilterControls onFiltersChange={handleFiltersChange} />
        <WeightControls onWeightsChange={handleWeightsChange} />
        <InterventionControls
          interventions={interventions}
          onModeChange={handleSimModeChange}
          onClear={handleClearInterventions}
        />
        <ProjectsControl
          count={projects.length}
          visible={projectsVisible}
          adding={addingProject}
          onToggleVisible={setProjectsVisible}
          onToggleAdd={handleToggleAddProject}
        />
        <ExtractControl active={drawing} onToggle={handleToggleDraw} />
      </div>

      <InterventionSummary summary={simSummary} />
      <ViewModeToggle onModeChange={handleColorModeChange} />
      <ProjectPanel
        project={selectedProject}
        onClose={() => setSelectedProject(null)}
        onDelete={handleDeleteProject}
      />
      {pendingCoords && (
        <ProjectForm
          onSave={handleSaveProject}
          onCancel={() => setPendingCoords(null)}
        />
      )}

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
      <Legend mode={colorMode} />
      <StatsBar />

      {/* Detail panel */}
      <ZonePanel zone={selectedZone} onClose={handleClose} />

      {/* Extracción on-demand (CAPA 1) */}
      <ExtractPanel
        context={extractCtx}
        loading={extractLoading}
        error={extractError}
        onClose={handleExtractClose}
      />

      {/* Hint mientras dibuja */}
      {drawing && (
        <div
          className="pointer-events-none fixed bottom-24 left-1/2 z-30 -translate-x-1/2 rounded-xl px-4 py-2.5 text-xs font-medium"
          style={{
            background: "var(--bg-glass)",
            backdropFilter: "blur(16px)",
            WebkitBackdropFilter: "blur(16px)",
            border: "1px solid #a78bfa",
            color: "#a78bfa",
            boxShadow: "0 8px 32px rgba(0, 0, 0, 0.3)",
          }}
        >
          Click para agregar vértices · doble click para cerrar y analizar
        </div>
      )}

      {/* Onboarding + carga */}
      {!loading && !selectedZone && interventions.length === 0 && <IntroHint />}
      <LoadingOverlay visible={loading} />
    </main>
  );
}
