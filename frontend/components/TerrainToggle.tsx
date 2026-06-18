"use client";

import { useState, useCallback } from "react";

type TerrainToggleProps = {
  onToggle: (enabled: boolean) => void;
};

export function TerrainToggle({ onToggle }: TerrainToggleProps) {
  const [on, setOn] = useState(false);

  const handle = useCallback(() => {
    setOn((prev) => {
      const next = !prev;
      onToggle(next);
      return next;
    });
  }, [onToggle]);

  return (
    <button
      title="Vista 3D del terreno"
      onClick={handle}
      className="fixed left-3 z-20 flex h-8 w-8 items-center justify-center rounded-lg text-[11px] font-bold transition-colors"
      style={{
        top: 188,
        background: on ? "var(--accent-cyan)" : "var(--bg-elevated)",
        color: on ? "var(--bg-void)" : "var(--text-secondary)",
        border: "1px solid var(--border-subtle)",
        boxShadow: "0 4px 20px rgba(0, 0, 0, 0.3)",
      }}
    >
      3D
    </button>
  );
}
