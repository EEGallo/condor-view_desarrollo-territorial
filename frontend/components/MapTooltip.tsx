"use client";

import { CATEGORY_COLORS, CATEGORY_LABELS } from "./types";
import type { Categoria } from "./types";

type MapTooltipProps = {
  x: number;
  y: number;
  id: string;
  iat: number;
  categoria: Categoria;
  uso: string;
  visible: boolean;
};

export function MapTooltip({
  x,
  y,
  id,
  iat,
  categoria,
  uso,
  visible,
}: MapTooltipProps) {
  if (!visible) return null;

  const color = CATEGORY_COLORS[categoria];

  return (
    <div
      className="pointer-events-none fixed z-40 flex items-center gap-3 rounded-lg px-3 py-2"
      style={{
        left: x + 16,
        top: y - 20,
        background: "var(--bg-elevated)",
        border: "1px solid var(--border-subtle)",
        boxShadow: "0 8px 24px rgba(0, 0, 0, 0.5)",
        transform: "translateY(-50%)",
      }}
    >
      <div
        className="flex h-10 w-10 items-center justify-center rounded-lg"
        style={{
          background: `${color}15`,
          border: `1px solid ${color}30`,
        }}
      >
        <span className="font-mono text-sm font-black" style={{ color }}>
          {Math.round(iat)}
        </span>
      </div>
      <div className="flex flex-col gap-0.5">
        <span
          className="font-mono text-[11px] font-semibold"
          style={{ color: "var(--text-primary)" }}
        >
          {id}
        </span>
        <span className="text-[10px] capitalize" style={{ color }}>
          {CATEGORY_LABELS[categoria]}
        </span>
        <span
          className="text-[10px] capitalize"
          style={{ color: "var(--text-muted)" }}
        >
          {uso.replace(/_/g, " ")}
        </span>
      </div>
    </div>
  );
}
