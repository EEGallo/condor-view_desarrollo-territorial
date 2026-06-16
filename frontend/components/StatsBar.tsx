"use client";

import { useEffect, useState } from "react";
import { CATEGORY_COLORS } from "./types";
import type { Categoria } from "./types";

type ZoneStats = {
  total: number;
  avgIat: number;
  distribution: Record<Categoria, number>;
  avgPendiente: number;
  riesgoAlto: number;
};

function computeStats(features: GeoJSON.Feature[]): ZoneStats {
  const distribution: Record<Categoria, number> = {
    alta: 0,
    media: 0,
    baja: 0,
    no_apto: 0,
  };

  let sumIat = 0;
  let sumPendiente = 0;
  let riesgoAlto = 0;

  for (const f of features) {
    const p = f.properties!;
    distribution[p.categoria as Categoria] =
      (distribution[p.categoria as Categoria] || 0) + 1;
    sumIat += p.iat;
    sumPendiente += p.pendiente_pct;
    if (p.riesgo_hidrico === "alto") riesgoAlto++;
  }

  return {
    total: features.length,
    avgIat: Math.round(sumIat / features.length),
    distribution,
    avgPendiente: Math.round((sumPendiente / features.length) * 10) / 10,
    riesgoAlto,
  };
}

export function StatsBar() {
  const [stats, setStats] = useState<ZoneStats | null>(null);

  useEffect(() => {
    fetch("/data/zonas.geojson")
      .then((r) => r.json())
      .then((geojson) => {
        setStats(computeStats(geojson.features));
      })
      .catch(() => {});
  }, []);

  if (!stats) return null;

  const catOrder: Categoria[] = ["alta", "media", "baja", "no_apto"];
  const catLabels: Record<Categoria, string> = {
    alta: "Alta",
    media: "Media",
    baja: "Baja",
    no_apto: "N/A",
  };

  return (
    <div
      className="fixed bottom-6 right-6 z-20 flex items-center gap-4 rounded-xl px-5 py-3"
      style={{
        background: "var(--bg-glass)",
        backdropFilter: "blur(16px) saturate(1.4)",
        WebkitBackdropFilter: "blur(16px) saturate(1.4)",
        border: "1px solid var(--border-subtle)",
        boxShadow: "0 8px 32px rgba(0, 0, 0, 0.4)",
      }}
    >
      <StatCell label="Zonas" value={stats.total.toLocaleString("es-AR")} />
      <Divider />
      <StatCell
        label="IAT promedio"
        value={String(stats.avgIat)}
        color={
          stats.avgIat >= 70
            ? "var(--cat-alta)"
            : stats.avgIat >= 40
              ? "var(--cat-media)"
              : "var(--cat-baja)"
        }
      />
      <Divider />

      <div className="flex flex-col gap-1">
        <span
          className="text-[9px] font-semibold uppercase tracking-[0.15em]"
          style={{ color: "var(--text-muted)" }}
        >
          Distribución
        </span>
        <div className="flex h-2 w-32 overflow-hidden rounded-full">
          {catOrder.map((cat) => {
            const pct = (stats.distribution[cat] / stats.total) * 100;
            if (pct === 0) return null;
            return (
              <div
                key={cat}
                title={`${catLabels[cat]}: ${stats.distribution[cat]} (${Math.round(pct)}%)`}
                style={{
                  width: `${pct}%`,
                  background: CATEGORY_COLORS[cat],
                  transition: "width 0.3s ease",
                }}
              />
            );
          })}
        </div>
      </div>

      <Divider />
      <StatCell
        label="Riesgo hídrico"
        value={`${Math.round((stats.riesgoAlto / stats.total) * 100)}%`}
        color={
          stats.riesgoAlto / stats.total > 0.2
            ? "var(--accent-red)"
            : "var(--accent-green)"
        }
      />
    </div>
  );
}

function StatCell({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <span
        className="text-[9px] font-semibold uppercase tracking-[0.15em]"
        style={{ color: "var(--text-muted)" }}
      >
        {label}
      </span>
      <span
        className="font-mono text-sm font-bold"
        style={{ color: color ?? "var(--text-primary)" }}
      >
        {value}
      </span>
    </div>
  );
}

function Divider() {
  return (
    <div
      className="h-8 w-px"
      style={{ background: "var(--border-subtle)" }}
    />
  );
}
