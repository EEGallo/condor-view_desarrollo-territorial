"use client";

import { useState, useCallback } from "react";
import type { InterventionType, Intervention } from "./MapView";

type InterventionControlsProps = {
  interventions: Intervention[];
  onModeChange: (type: InterventionType | null) => void;
  onClear: () => void;
};

const TYPES: {
  key: InterventionType;
  name: string;
  color: string;
  hint: string;
}[] = [
  {
    key: "ruta",
    name: "Ruta",
    color: "#22d3ee",
    hint: "Click para marcar el trazado · doble click para cerrar",
  },
  {
    key: "hub",
    name: "Hub urbano",
    color: "#22c55e",
    hint: "Click para colocar un nuevo núcleo de servicios",
  },
  {
    key: "agua",
    name: "Traza de agua",
    color: "#3b82f6",
    hint: "Click para marcar la traza · doble click para cerrar",
  },
];

export function InterventionControls({
  interventions,
  onModeChange,
  onClear,
}: InterventionControlsProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeMode, setActiveMode] = useState<InterventionType | null>(null);

  const handleToggleOpen = useCallback(() => {
    setIsOpen((prev) => {
      const next = !prev;
      if (!next) {
        setActiveMode(null);
        onModeChange(null);
      }
      return next;
    });
  }, [onModeChange]);

  const handleSelectMode = useCallback(
    (type: InterventionType) => {
      const next = activeMode === type ? null : type;
      setActiveMode(next);
      onModeChange(next);
    },
    [activeMode, onModeChange]
  );

  const handleClear = useCallback(() => {
    setActiveMode(null);
    onModeChange(null);
    onClear();
  }, [onModeChange, onClear]);

  const activeHint = activeMode
    ? TYPES.find((t) => t.key === activeMode)?.hint
    : null;

  return (
    <div className="fixed top-6 z-20" style={{ right: 290 }}>
      <button
        onClick={handleToggleOpen}
        className="flex items-center gap-2 rounded-xl px-4 py-2.5 text-xs font-semibold uppercase tracking-wider transition-all"
        style={{
          background: isOpen ? "var(--bg-elevated)" : "var(--bg-glass)",
          backdropFilter: "blur(16px)",
          WebkitBackdropFilter: "blur(16px)",
          border: `1px solid ${isOpen ? "var(--border-accent)" : "var(--border-subtle)"}`,
          color: isOpen ? "var(--accent-cyan)" : "var(--text-secondary)",
          boxShadow: "0 8px 32px rgba(0, 0, 0, 0.3)",
        }}
      >
        <svg
          width="14"
          height="14"
          viewBox="0 0 14 14"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        >
          <path d="M7 1v12M1 7h12" />
        </svg>
        Simular
      </button>

      {isOpen && (
        <div
          className="mt-2 flex flex-col gap-4 rounded-xl p-5"
          style={{
            background: "var(--bg-glass)",
            backdropFilter: "blur(24px) saturate(1.6)",
            WebkitBackdropFilter: "blur(24px) saturate(1.6)",
            border: "1px solid var(--border-subtle)",
            boxShadow: "0 20px 60px rgba(0, 0, 0, 0.4)",
            width: 260,
          }}
        >
          <div className="flex items-center justify-between">
            <span
              className="text-[10px] font-semibold uppercase tracking-[0.15em]"
              style={{ color: "var(--text-muted)" }}
            >
              Intervención hipotética
            </span>
            {interventions.length > 0 && (
              <button
                onClick={handleClear}
                className="text-[10px] uppercase tracking-wider"
                style={{ color: "var(--text-muted)" }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = "var(--accent-cyan)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = "var(--text-muted)";
                }}
              >
                Limpiar
              </button>
            )}
          </div>

          <div className="flex flex-col gap-2">
            {TYPES.map((t) => (
              <button
                key={t.key}
                onClick={() => handleSelectMode(t.key)}
                className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-xs font-medium transition-all"
                style={{
                  background:
                    activeMode === t.key
                      ? "var(--bg-elevated)"
                      : "transparent",
                  border: `1px solid ${
                    activeMode === t.key ? t.color : "var(--border-subtle)"
                  }`,
                  color:
                    activeMode === t.key ? t.color : "var(--text-secondary)",
                }}
              >
                <span
                  className="inline-block h-2.5 w-2.5 rounded-full"
                  style={{ background: t.color }}
                />
                {t.name}
              </button>
            ))}
          </div>

          {activeHint && (
            <p
              className="text-center text-[10px] leading-relaxed"
              style={{ color: "var(--accent-cyan)" }}
            >
              {activeHint}
            </p>
          )}

          <p
            className="text-center text-[10px] leading-relaxed"
            style={{ color: "var(--text-muted)" }}
          >
            {interventions.length === 0
              ? "Colocá infraestructura y verás cómo cambia el potencial del territorio"
              : `${interventions.length} intervención${interventions.length > 1 ? "es" : ""} activa${interventions.length > 1 ? "s" : ""}`}
          </p>
        </div>
      )}
    </div>
  );
}
