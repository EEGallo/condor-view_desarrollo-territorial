"use client";

import { useState, useCallback } from "react";
import { CATEGORY_COLORS, CATEGORY_LABELS } from "./types";
import type { Categoria } from "./types";

type FilterState = {
  categories: Set<Categoria>;
  minIat: number;
  maxPendiente: number;
  hideRiesgoAlto: boolean;
};

type FilterControlsProps = {
  onFiltersChange: (filters: FilterState) => void;
};

const ALL_CATEGORIES: Categoria[] = ["alta", "media", "baja", "no_apto"];

const DEFAULT_FILTERS: FilterState = {
  categories: new Set(ALL_CATEGORIES),
  minIat: 0,
  maxPendiente: 100,
  hideRiesgoAlto: false,
};

export type { FilterState };

export function FilterControls({ onFiltersChange }: FilterControlsProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);

  const updateFilters = useCallback(
    (partial: Partial<FilterState>) => {
      const next = { ...filters, ...partial };
      setFilters(next);
      onFiltersChange(next);
    },
    [filters, onFiltersChange]
  );

  const toggleCategory = useCallback(
    (cat: Categoria) => {
      const next = new Set(filters.categories);
      if (next.has(cat)) {
        if (next.size > 1) next.delete(cat);
      } else {
        next.add(cat);
      }
      updateFilters({ categories: next });
    },
    [filters.categories, updateFilters]
  );

  const handleReset = useCallback(() => {
    setFilters(DEFAULT_FILTERS);
    onFiltersChange(DEFAULT_FILTERS);
  }, [onFiltersChange]);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
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
          <path d="M1 2h12L8 7.5V12L6 13V7.5L1 2Z" />
        </svg>
        Filtros
      </button>

      {isOpen && (
        <div
          className="absolute right-0 top-full z-30 mt-2 flex flex-col gap-4 rounded-xl p-5"
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
              Filtrar zonas
            </span>
            <button
              onClick={handleReset}
              className="text-[10px] uppercase tracking-wider"
              style={{ color: "var(--text-muted)" }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = "var(--accent-cyan)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = "var(--text-muted)";
              }}
            >
              Reset
            </button>
          </div>

          {/* Category toggles */}
          <div className="flex flex-col gap-2">
            <span
              className="text-[10px] uppercase tracking-wider"
              style={{ color: "var(--text-secondary)" }}
            >
              Categorías
            </span>
            <div className="flex flex-wrap gap-1.5">
              {ALL_CATEGORIES.map((cat) => {
                const active = filters.categories.has(cat);
                return (
                  <button
                    key={cat}
                    onClick={() => toggleCategory(cat)}
                    className="rounded-lg px-2.5 py-1.5 text-[11px] font-medium transition-all"
                    style={{
                      background: active
                        ? `${CATEGORY_COLORS[cat]}20`
                        : "var(--bg-void)",
                      color: active
                        ? CATEGORY_COLORS[cat]
                        : "var(--text-muted)",
                      border: `1px solid ${active ? `${CATEGORY_COLORS[cat]}40` : "var(--border-subtle)"}`,
                      opacity: active ? 1 : 0.5,
                    }}
                  >
                    {CATEGORY_LABELS[cat]}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Min IAT slider */}
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <span
                className="text-[10px] uppercase tracking-wider"
                style={{ color: "var(--text-secondary)" }}
              >
                IAT mínimo
              </span>
              <span
                className="font-mono text-xs font-semibold"
                style={{ color: "var(--accent-cyan)" }}
              >
                {filters.minIat}
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={filters.minIat}
              onChange={(e) =>
                updateFilters({ minIat: Number(e.target.value) })
              }
              className="weight-slider w-full"
              style={
                { "--slider-color": "var(--accent-cyan)" } as React.CSSProperties
              }
            />
          </div>

          {/* Max slope slider */}
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <span
                className="text-[10px] uppercase tracking-wider"
                style={{ color: "var(--text-secondary)" }}
              >
                Pendiente máxima
              </span>
              <span
                className="font-mono text-xs font-semibold"
                style={{ color: "var(--accent-yellow)" }}
              >
                {filters.maxPendiente}%
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={30}
              step={1}
              value={filters.maxPendiente}
              onChange={(e) =>
                updateFilters({ maxPendiente: Number(e.target.value) })
              }
              className="weight-slider w-full"
              style={
                {
                  "--slider-color": "var(--accent-yellow)",
                } as React.CSSProperties
              }
            />
          </div>

          {/* Flood risk toggle */}
          <label
            className="flex cursor-pointer items-center gap-3"
            style={{ color: "var(--text-secondary)" }}
          >
            <div
              className="flex h-5 w-9 items-center rounded-full p-0.5 transition-colors"
              style={{
                background: filters.hideRiesgoAlto
                  ? "var(--accent-red)"
                  : "var(--bg-void)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <div
                className="h-4 w-4 rounded-full bg-white transition-transform"
                style={{
                  transform: filters.hideRiesgoAlto
                    ? "translateX(14px)"
                    : "translateX(0)",
                  boxShadow: "0 1px 3px rgba(0,0,0,0.3)",
                }}
              />
            </div>
            <span className="text-xs">Ocultar riesgo hídrico alto</span>
          </label>
        </div>
      )}
    </div>
  );
}
