"use client";

import { useState, useCallback } from "react";
import type { ColorMode } from "./MapView";

type ViewModeToggleProps = {
  onModeChange: (mode: ColorMode) => void;
};

const MODES: { key: ColorMode; label: string }[] = [
  { key: "aptitud", label: "Aptitud" },
  { key: "deficit", label: "Déficit" },
  { key: "isocronas", label: "Tiempo de viaje" },
];

export function ViewModeToggle({ onModeChange }: ViewModeToggleProps) {
  const [mode, setMode] = useState<ColorMode>("aptitud");

  const handleSelect = useCallback(
    (m: ColorMode) => {
      setMode(m);
      onModeChange(m);
    },
    [onModeChange]
  );

  return (
    <div
      className="fixed left-1/2 top-6 z-20 flex -translate-x-1/2 gap-1 rounded-xl p-1"
      style={{
        background: "var(--bg-glass)",
        backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
        border: "1px solid var(--border-subtle)",
        boxShadow: "0 8px 32px rgba(0, 0, 0, 0.3)",
      }}
    >
      {MODES.map((m) => (
        <button
          key={m.key}
          onClick={() => handleSelect(m.key)}
          className="rounded-lg px-3 py-1.5 text-xs font-semibold uppercase tracking-wider transition-all"
          style={{
            background: mode === m.key ? "var(--bg-elevated)" : "transparent",
            color:
              mode === m.key ? "var(--accent-cyan)" : "var(--text-secondary)",
          }}
        >
          {m.label}
        </button>
      ))}
    </div>
  );
}
