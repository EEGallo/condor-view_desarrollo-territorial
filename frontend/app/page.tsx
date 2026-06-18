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
import type { ZoneProperties, Categoria, Proyecto } from "@/components/types";
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
  const mapRef = useRef<MapViewHandle>(null);

  const handleReady = useCallback(() => setLoading(false), []);

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
      />

      {/* Controls */}
      <LayerToggle onStyleChange={handleStyleChange} />
      <TerrainToggle onToggle={handleTerrainToggle} />
      <FilterControls onFiltersChange={handleFiltersChange} />
      <WeightControls onWeightsChange={handleWeightsChange} />
      <InterventionControls
        interventions={interventions}
        onModeChange={handleSimModeChange}
        onClear={handleClearInterventions}
      />
      <InterventionSummary summary={simSummary} />
      <ViewModeToggle onModeChange={handleColorModeChange} />
      <ProjectsControl
        count={projects.length}
        visible={projectsVisible}
        adding={addingProject}
        onToggleVisible={setProjectsVisible}
        onToggleAdd={handleToggleAddProject}
      />
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

      {/* Onboarding + carga */}
      {!loading && !selectedZone && interventions.length === 0 && <IntroHint />}
      <LoadingOverlay visible={loading} />
    </main>
  );
}
