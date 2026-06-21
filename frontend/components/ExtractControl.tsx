"use client";

type ExtractControlProps = {
  active: boolean;
  onToggle: (v: boolean) => void;
};

// Botón de la toolbar: activa el modo "dibujar polígono" para extracción
// on-demand (CAPA 1). Click en el mapa = vértice; doble click = cerrar y extraer.
export function ExtractControl({ active, onToggle }: ExtractControlProps) {
  return (
    <button
      onClick={() => onToggle(!active)}
      className="flex items-center gap-2 rounded-xl px-4 py-2.5 text-xs font-semibold uppercase tracking-wider transition-all"
      style={{
        background: active ? "var(--bg-elevated)" : "var(--bg-glass)",
        backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
        border: `1px solid ${active ? "#a78bfa" : "var(--border-subtle)"}`,
        color: active ? "#a78bfa" : "var(--text-secondary)",
        boxShadow: "0 8px 32px rgba(0, 0, 0, 0.3)",
      }}
      title="Dibujar polígono y extraer contexto territorial"
    >
      <svg
        width="14"
        height="14"
        viewBox="0 0 14 14"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      >
        <path d="M2 4l5-2.5L12 4v6l-5 2.5L2 10V4z" />
        <circle cx="2" cy="4" r="1.3" fill="currentColor" stroke="none" />
        <circle cx="12" cy="4" r="1.3" fill="currentColor" stroke="none" />
        <circle cx="7" cy="12.5" r="1.3" fill="currentColor" stroke="none" />
      </svg>
      {active ? "Dibujando…" : "Analizar área"}
    </button>
  );
}
