"use client";

import type { ZoneProperties } from "./types";
import {
  CATEGORY_COLORS,
  CATEGORY_LABELS,
  FLAG_LABELS,
} from "./types";
import { ScoreBar } from "./ScoreBar";
import { ExportButton } from "./ExportButton";

type ZonePanelProps = {
  zone: ZoneProperties | null;
  onClose: () => void;
};

function iatColor(iat: number): string {
  if (iat >= 70) return "var(--cat-alta)";
  if (iat >= 40) return "var(--cat-media)";
  if (iat > 0) return "var(--cat-baja)";
  return "var(--cat-no-apto)";
}

function formatDistance(meters: number): string {
  if (meters >= 1000) return `${(meters / 1000).toFixed(1)} km`;
  return `${Math.round(meters)} m`;
}

function formatServiceDist(meters: number): string {
  if (meters < 0) return "s/d";
  return formatDistance(meters);
}

function formatTiempo(min: number): string {
  if (min >= 180) return "Sin acceso vial";
  return `${min.toFixed(0)} min`;
}

function deficitColor(d: number): string {
  if (d >= 60) return "var(--accent-red)";
  if (d >= 35) return "var(--accent-yellow)";
  if (d > 0) return "var(--accent-green)";
  return "var(--text-muted)";
}

function riesgoColor(riesgo: string): string {
  const map: Record<string, string> = {
    bajo: "var(--accent-green)",
    medio: "var(--accent-yellow)",
    alto: "var(--accent-orange)",
    muy_alto: "var(--accent-red)",
  };
  return map[riesgo] ?? "var(--text-secondary)";
}

export function ZonePanel({ zone, onClose }: ZonePanelProps) {
  const isOpen = zone !== null;

  return (
    <div
      className="fixed top-0 right-0 z-30 flex h-full w-[380px] flex-col overflow-hidden"
      style={{
        transform: isOpen ? "translateX(0)" : "translateX(100%)",
        opacity: isOpen ? 1 : 0,
        transition: `transform var(--duration-slow) var(--ease-out-expo), opacity var(--duration-normal) ease`,
        background: "var(--bg-glass)",
        backdropFilter: "blur(24px) saturate(1.6)",
        WebkitBackdropFilter: "blur(24px) saturate(1.6)",
        borderLeft: "1px solid var(--border-subtle)",
        boxShadow: "-20px 0 60px rgba(0, 0, 0, 0.4)",
      }}
    >
      {zone && (
        <>
          {/* Header */}
          <div
            className="relative flex items-start justify-between px-6 pt-6 pb-4"
            style={{ borderBottom: "1px solid var(--border-subtle)" }}
          >
            <div className="flex flex-col gap-1">
              <span
                className="text-[10px] font-semibold uppercase tracking-[0.2em]"
                style={{ color: "var(--text-muted)" }}
              >
                Zona
              </span>
              <span
                className="font-mono text-lg font-bold"
                style={{ color: "var(--text-primary)" }}
              >
                {zone.id}
              </span>
            </div>

            <button
              onClick={onClose}
              className="flex h-8 w-8 items-center justify-center rounded-lg transition-colors"
              style={{
                background: "var(--bg-surface)",
                color: "var(--text-secondary)",
                border: "1px solid var(--border-subtle)",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "var(--bg-elevated)";
                e.currentTarget.style.color = "var(--text-primary)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "var(--bg-surface)";
                e.currentTarget.style.color = "var(--text-secondary)";
              }}
              aria-label="Cerrar panel"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 14 14"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              >
                <path d="M1 1l12 12M13 1L1 13" />
              </svg>
            </button>
          </div>

          {/* Scrollable content */}
          <div
            className="flex flex-1 flex-col gap-6 overflow-y-auto px-6 py-5"
            style={{ scrollbarGutter: "stable" }}
          >
            {/* IAT Score */}
            <div className="flex flex-col items-center gap-3 py-2">
              <span
                className="text-[10px] font-semibold uppercase tracking-[0.2em]"
                style={{ color: "var(--text-muted)" }}
              >
                Índice de Aptitud Territorial
              </span>
              <div
                className="flex h-24 w-24 items-center justify-center rounded-2xl"
                style={{
                  background: `${iatColor(zone.iat)}10`,
                  border: `2px solid ${iatColor(zone.iat)}30`,
                  boxShadow: `0 0 40px ${iatColor(zone.iat)}15, inset 0 0 20px ${iatColor(zone.iat)}08`,
                }}
              >
                <span
                  className="font-mono text-4xl font-black"
                  style={{ color: iatColor(zone.iat) }}
                >
                  {Math.round(zone.iat)}
                </span>
              </div>
              <span
                className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold"
                style={{
                  background: `${CATEGORY_COLORS[zone.categoria]}18`,
                  color: CATEGORY_COLORS[zone.categoria],
                  border: `1px solid ${CATEGORY_COLORS[zone.categoria]}30`,
                }}
              >
                <span
                  className="h-1.5 w-1.5 rounded-full"
                  style={{ background: CATEGORY_COLORS[zone.categoria] }}
                />
                {CATEGORY_LABELS[zone.categoria]}
              </span>
            </div>

            {/* Sub-scores */}
            <div className="flex flex-col gap-3">
              <span
                className="text-[10px] font-semibold uppercase tracking-[0.2em]"
                style={{ color: "var(--text-muted)" }}
              >
                Componentes del índice
              </span>
              <ScoreBar
                label="Normativa"
                value={zone.s_norm}
                color="var(--accent-cyan)"
              />
              <ScoreBar
                label="Físico"
                value={zone.s_fis}
                color="var(--accent-yellow)"
              />
              <ScoreBar
                label="Accesibilidad"
                value={zone.s_acc}
                color="#a78bfa"
              />
            </div>

            {/* Details */}
            <div className="flex flex-col gap-3">
              <span
                className="text-[10px] font-semibold uppercase tracking-[0.2em]"
                style={{ color: "var(--text-muted)" }}
              >
                Detalle territorial
              </span>

              <div
                className="flex flex-col gap-0 overflow-hidden rounded-xl"
                style={{
                  background: "var(--bg-surface)",
                  border: "1px solid var(--border-subtle)",
                }}
              >
                <DetailRow label="Uso permitido" value={zone.uso_permitido} />
                <DetailRow
                  label="Pendiente"
                  value={`${zone.pendiente_pct.toFixed(1)}%`}
                />
                <DetailRow
                  label="Riesgo hídrico"
                  value={zone.riesgo_hidrico.replace(/_/g, " ")}
                  valueColor={riesgoColor(zone.riesgo_hidrico)}
                />
                <DetailRow
                  label="Dist. huella urbana"
                  value={formatDistance(zone.dist_huella_m)}
                />
                <DetailRow
                  label="Dist. vial"
                  value={formatDistance(zone.dist_vial_m)}
                />
                {zone.elevacion_m != null && (
                  <DetailRow
                    label="Elevación"
                    value={`${zone.elevacion_m.toLocaleString("es-AR")} m`}
                  />
                )}
                {zone.distrito && (
                  <DetailRow
                    label="Distrito"
                    value={zone.distrito}
                  />
                )}
                {zone.en_oasis != null && (
                  <DetailRow
                    label="En oasis irrigado"
                    value={zone.en_oasis ? "Sí" : "No"}
                    valueColor={
                      zone.en_oasis
                        ? "var(--accent-green)"
                        : "var(--text-muted)"
                    }
                    isLast
                  />
                )}
              </div>
            </div>

            {/* Población y servicios */}
            {(zone.poblacion_est != null ||
              zone.deficit_servicios != null) && (
              <div className="flex flex-col gap-3">
                <span
                  className="text-[10px] font-semibold uppercase tracking-[0.2em]"
                  style={{ color: "var(--text-muted)" }}
                >
                  Población y servicios
                </span>
                <div
                  className="flex flex-col gap-0 overflow-hidden rounded-xl"
                  style={{
                    background: "var(--bg-surface)",
                    border: "1px solid var(--border-subtle)",
                  }}
                >
                  {zone.poblacion_est != null && (
                    <DetailRow
                      label="Población estimada"
                      value={
                        zone.poblacion_est > 0
                          ? `${zone.poblacion_est.toLocaleString("es-AR")} hab`
                          : "Sin población"
                      }
                    />
                  )}
                  {zone.dist_escuela_m != null && (
                    <DetailRow
                      label="Dist. escuela"
                      value={formatServiceDist(zone.dist_escuela_m)}
                    />
                  )}
                  {zone.dist_salud_m != null && (
                    <DetailRow
                      label="Dist. salud"
                      value={formatServiceDist(zone.dist_salud_m)}
                    />
                  )}
                  {zone.tiempo_servicio_min != null && (
                    <DetailRow
                      label="Tiempo a servicios"
                      value={formatTiempo(zone.tiempo_servicio_min)}
                    />
                  )}
                  {zone.deficit_servicios != null && (
                    <DetailRow
                      label="Déficit de servicios"
                      value={
                        zone.deficit_servicios > 0
                          ? `${zone.deficit_servicios} / 100`
                          : "—"
                      }
                      valueColor={deficitColor(zone.deficit_servicios)}
                      isLast
                    />
                  )}
                </div>
              </div>
            )}

            {/* Flags */}
            {zone.flags.length > 0 && (
              <div className="flex flex-col gap-3">
                <span
                  className="text-[10px] font-semibold uppercase tracking-[0.2em]"
                  style={{ color: "var(--text-muted)" }}
                >
                  Alertas
                </span>
                <div className="flex flex-wrap gap-2">
                  {zone.flags.map((flag) => (
                    <span
                      key={flag}
                      className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium"
                      style={{
                        background: "rgba(239, 68, 68, 0.1)",
                        color: "var(--accent-red)",
                        border: "1px solid rgba(239, 68, 68, 0.2)",
                      }}
                    >
                      <svg
                        width="10"
                        height="10"
                        viewBox="0 0 10 10"
                        fill="currentColor"
                      >
                        <path d="M5 0L6.12 3.88L10 5L6.12 6.12L5 10L3.88 6.12L0 5L3.88 3.88L5 0Z" />
                      </svg>
                      {FLAG_LABELS[flag] ?? flag}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div
            className="px-6 py-4"
            style={{ borderTop: "1px solid var(--border-subtle)" }}
          >
            <div className="flex items-center justify-between">
              <p
                className="text-[10px] leading-relaxed"
                style={{ color: "var(--text-muted)" }}
              >
                Cóndor View Pipeline
              </p>
              <ExportButton zone={zone} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function DetailRow({
  label,
  value,
  valueColor,
  isLast = false,
}: {
  label: string;
  value: string;
  valueColor?: string;
  isLast?: boolean;
}) {
  return (
    <div
      className="flex items-center justify-between px-4 py-3"
      style={{
        borderBottom: isLast ? "none" : "1px solid var(--border-subtle)",
      }}
    >
      <span
        className="text-xs"
        style={{ color: "var(--text-secondary)" }}
      >
        {label}
      </span>
      <span
        className="text-xs font-semibold capitalize"
        style={{ color: valueColor ?? "var(--text-primary)" }}
      >
        {value}
      </span>
    </div>
  );
}
