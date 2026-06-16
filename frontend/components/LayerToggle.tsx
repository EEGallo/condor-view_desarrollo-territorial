"use client";

import { useState } from "react";

type BasemapStyle = "dark" | "satellite" | "streets";

type LayerToggleProps = {
  onStyleChange: (style: BasemapStyle) => void;
};

const STYLES: { key: BasemapStyle; label: string; icon: string }[] = [
  { key: "dark", label: "Oscuro", icon: "M" },
  { key: "satellite", label: "Satélite", icon: "S" },
  { key: "streets", label: "Calles", icon: "C" },
];

export type { BasemapStyle };

export function LayerToggle({ onStyleChange }: LayerToggleProps) {
  const [active, setActive] = useState<BasemapStyle>("dark");

  return (
    <div
      className="fixed top-20 left-3 z-20 flex flex-col overflow-hidden rounded-lg"
      style={{
        background: "var(--bg-elevated)",
        border: "1px solid var(--border-subtle)",
        boxShadow: "0 4px 20px rgba(0, 0, 0, 0.3)",
      }}
    >
      {STYLES.map((s) => (
        <button
          key={s.key}
          title={s.label}
          onClick={() => {
            setActive(s.key);
            onStyleChange(s.key);
          }}
          className="flex h-8 w-8 items-center justify-center text-[11px] font-bold transition-colors"
          style={{
            background:
              active === s.key ? "var(--accent-cyan)" : "transparent",
            color:
              active === s.key ? "var(--bg-void)" : "var(--text-secondary)",
            borderBottom:
              s.key !== "streets"
                ? "1px solid var(--border-subtle)"
                : "none",
          }}
        >
          {s.icon}
        </button>
      ))}
    </div>
  );
}
