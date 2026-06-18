"use client";

import { CATEGORY_COLORS, CATEGORY_LABELS } from "./types";
import type { Categoria } from "./types";
import type { ColorMode } from "./MapView";

const CATEGORIES: Categoria[] = ["alta", "media", "baja", "no_apto"];

const DEFICIT_SCALE: { color: string; label: string }[] = [
  { color: "#ef4444", label: "Déficit crítico" },
  { color: "#eab308", label: "Déficit medio" },
  { color: "#22c55e", label: "Bien servida" },
  { color: "#1f2937", label: "Sin población" },
];

const ISOCRONA_SCALE: { color: string; label: string }[] = [
  { color: "#22c55e", label: "< 8 min" },
  { color: "#eab308", label: "~15 min" },
  { color: "#ef4444", label: "~30 min" },
  { color: "#1f2937", label: "Sin acceso vial" },
];

const TITLES: Record<ColorMode, string> = {
  aptitud: "Aptitud territorial",
  deficit: "Déficit de servicios",
  isocronas: "Tiempo a servicios",
};

type LegendProps = {
  mode?: ColorMode;
};

export function Legend({ mode = "aptitud" }: LegendProps) {
  const items =
    mode === "deficit"
      ? DEFICIT_SCALE
      : mode === "isocronas"
        ? ISOCRONA_SCALE
        : CATEGORIES.map((cat) => ({
            color: CATEGORY_COLORS[cat],
            label: CATEGORY_LABELS[cat],
          }));

  return (
    <div
      className="fixed bottom-6 left-6 z-20 flex flex-col gap-2 rounded-xl px-4 py-3"
      style={{
        background: "var(--bg-glass)",
        backdropFilter: "blur(16px) saturate(1.4)",
        WebkitBackdropFilter: "blur(16px) saturate(1.4)",
        border: "1px solid var(--border-subtle)",
        boxShadow: "0 8px 32px rgba(0, 0, 0, 0.4)",
      }}
    >
      <span
        className="text-[10px] font-semibold uppercase tracking-[0.15em]"
        style={{ color: "var(--text-muted)" }}
      >
        {TITLES[mode]}
      </span>

      {items.map((item) => (
        <div key={item.label} className="flex items-center gap-2.5">
          <span
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={{
              background: item.color,
              boxShadow: `0 0 6px ${item.color}50`,
            }}
          />
          <span className="text-xs" style={{ color: "var(--text-secondary)" }}>
            {item.label}
          </span>
        </div>
      ))}
    </div>
  );
}
