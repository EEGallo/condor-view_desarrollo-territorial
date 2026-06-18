"use client";

import type { SimSummary } from "./MapView";

type InterventionSummaryProps = {
  summary: SimSummary | null;
};

export function InterventionSummary({ summary }: InterventionSummaryProps) {
  if (!summary) return null;

  const delta =
    summary.iatPromedioDespues - summary.iatPromedioAntes;

  return (
    <div
      className="fixed bottom-6 left-1/2 z-20 -translate-x-1/2 rounded-xl px-6 py-4"
      style={{
        background: "var(--bg-glass)",
        backdropFilter: "blur(24px) saturate(1.6)",
        WebkitBackdropFilter: "blur(24px) saturate(1.6)",
        border: "1px solid var(--border-accent)",
        boxShadow: "0 20px 60px rgba(0, 0, 0, 0.4)",
      }}
    >
      <div className="flex items-center gap-6">
        <div className="flex flex-col">
          <span
            className="text-[10px] font-semibold uppercase tracking-[0.15em]"
            style={{ color: "var(--text-muted)" }}
          >
            Impacto simulado
          </span>
          <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>
            {summary.totalIntervenciones}{" "}
            {summary.totalIntervenciones > 1
              ? "intervenciones"
              : "intervención"}
          </span>
        </div>

        <Metric
          label="Zonas que suben"
          value={summary.zonasMejoradas.toLocaleString("es-AR")}
          color="var(--accent-cyan)"
        />
        <Metric
          label="Hectáreas desbloqueadas"
          value={summary.hectareasDesbloqueadas.toLocaleString("es-AR")}
          color="#22c55e"
        />
        <Metric
          label="IAT del área"
          value={`${Math.round(summary.iatPromedioAntes)} → ${Math.round(
            summary.iatPromedioDespues
          )}`}
          color={delta > 0 ? "#22c55e" : "var(--text-secondary)"}
          sub={delta > 0 ? `+${delta.toFixed(1)}` : delta.toFixed(1)}
        />
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  color,
  sub,
}: {
  label: string;
  value: string;
  color: string;
  sub?: string;
}) {
  return (
    <div className="flex flex-col">
      <div className="flex items-baseline gap-1.5">
        <span className="font-mono text-lg font-bold" style={{ color }}>
          {value}
        </span>
        {sub && (
          <span className="font-mono text-xs font-semibold" style={{ color }}>
            {sub}
          </span>
        )}
      </div>
      <span
        className="text-[10px] uppercase tracking-wider"
        style={{ color: "var(--text-muted)" }}
      >
        {label}
      </span>
    </div>
  );
}
