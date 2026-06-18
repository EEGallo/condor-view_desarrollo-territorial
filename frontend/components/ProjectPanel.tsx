"use client";

import type { Proyecto } from "./types";
import {
  PROYECTO_TIPO_LABELS,
  PROYECTO_ESTADO_LABELS,
  PROYECTO_ESTADO_COLORS,
} from "./types";

type ProjectPanelProps = {
  project: Proyecto | null;
  onClose: () => void;
  onDelete: (id: string) => void;
};

export function ProjectPanel({ project, onClose, onDelete }: ProjectPanelProps) {
  if (!project) return null;
  const color = PROYECTO_ESTADO_COLORS[project.estado];
  const isLocal = project.id.startsWith("P-local");

  return (
    <div
      className="fixed z-40 flex w-[300px] flex-col gap-3 rounded-xl p-5"
      style={{
        top: 240,
        left: 12,
        background: "var(--bg-glass)",
        backdropFilter: "blur(24px) saturate(1.6)",
        WebkitBackdropFilter: "blur(24px) saturate(1.6)",
        border: "1px solid var(--border-accent)",
        boxShadow: "0 20px 60px rgba(0,0,0,0.45)",
      }}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>
          {project.nombre}
        </span>
        <button
          onClick={onClose}
          className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-lg"
          style={{ background: "var(--bg-surface)", color: "var(--text-secondary)", border: "1px solid var(--border-subtle)" }}
          aria-label="Cerrar"
        >
          <svg width="11" height="11" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M1 1l12 12M13 1L1 13" />
          </svg>
        </button>
      </div>

      <div className="flex items-center gap-2">
        <span
          className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold"
          style={{ background: `${color}18`, color, border: `1px solid ${color}30` }}
        >
          <span className="h-1.5 w-1.5 rounded-full" style={{ background: color }} />
          {PROYECTO_ESTADO_LABELS[project.estado]}
        </span>
        <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
          {PROYECTO_TIPO_LABELS[project.tipo]}
          {project.anio ? ` · ${project.anio}` : ""}
        </span>
      </div>

      {project.descripcion && (
        <p className="text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>
          {project.descripcion}
        </p>
      )}

      {isLocal && (
        <button
          onClick={() => onDelete(project.id)}
          className="self-start text-[11px] uppercase tracking-wider"
          style={{ color: "var(--accent-red)" }}
        >
          Eliminar
        </button>
      )}
    </div>
  );
}
