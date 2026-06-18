"use client";

import { useState, useCallback } from "react";

type ProjectsControlProps = {
  count: number;
  visible: boolean;
  adding: boolean;
  onToggleVisible: (v: boolean) => void;
  onToggleAdd: (v: boolean) => void;
};

export function ProjectsControl({
  count,
  visible,
  adding,
  onToggleVisible,
  onToggleAdd,
}: ProjectsControlProps) {
  const [isOpen, setIsOpen] = useState(false);

  const handleOpen = useCallback(() => {
    setIsOpen((prev) => {
      if (prev && adding) onToggleAdd(false);
      return !prev;
    });
  }, [adding, onToggleAdd]);

  return (
    <div className="fixed top-6 z-20" style={{ right: 410 }}>
      <button
        onClick={handleOpen}
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
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M7 1L1 4v6l6 3 6-3V4L7 1zM1 4l6 3 6-3M7 7v6" />
        </svg>
        Proyectos
      </button>

      {isOpen && (
        <div
          className="mt-2 flex flex-col gap-3 rounded-xl p-5"
          style={{
            background: "var(--bg-glass)",
            backdropFilter: "blur(24px) saturate(1.6)",
            WebkitBackdropFilter: "blur(24px) saturate(1.6)",
            border: "1px solid var(--border-subtle)",
            boxShadow: "0 20px 60px rgba(0, 0, 0, 0.4)",
            width: 240,
          }}
        >
          <span
            className="text-[10px] font-semibold uppercase tracking-[0.15em]"
            style={{ color: "var(--text-muted)" }}
          >
            Obras y desarrollos ({count})
          </span>

          <label className="flex items-center justify-between text-xs" style={{ color: "var(--text-secondary)" }}>
            Ver en el mapa
            <input
              type="checkbox"
              checked={visible}
              onChange={(e) => onToggleVisible(e.target.checked)}
              style={{ accentColor: "var(--accent-cyan)" }}
            />
          </label>

          <button
            onClick={() => onToggleAdd(!adding)}
            className="rounded-lg px-3 py-2 text-xs font-medium transition-all"
            style={{
              background: adding ? "var(--bg-elevated)" : "transparent",
              border: `1px solid ${adding ? "var(--accent-cyan)" : "var(--border-subtle)"}`,
              color: adding ? "var(--accent-cyan)" : "var(--text-secondary)",
            }}
          >
            {adding ? "Click en el mapa para ubicar…" : "+ Agregar proyecto"}
          </button>

          <p className="text-center text-[10px] leading-relaxed" style={{ color: "var(--text-muted)" }}>
            Registrá obras planeadas, en ejecución o ejecutadas sobre el territorio.
          </p>
        </div>
      )}
    </div>
  );
}
