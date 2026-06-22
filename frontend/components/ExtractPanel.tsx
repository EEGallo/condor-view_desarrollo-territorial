"use client";

import type { ExtractContext, SceneModel, DiagnosticReport } from "./types";

type ExtractPanelProps = {
  context: ExtractContext | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
  onGenerate?: () => void;
  scene?: SceneModel | null;
  sceneLoading?: boolean;
  sceneError?: string | null;
  onDiagnose?: () => void;
  diag?: DiagnosticReport | null;
  diagLoading?: boolean;
  diagError?: string | null;
};

const RESULTADO_COLOR: Record<string, string> = {
  cumple: "var(--accent-green)",
  observacion: "var(--accent-yellow)",
  no_cumple: "var(--accent-red)",
  no_aplica: "var(--text-muted)",
};
const ESTADO_LABEL: Record<string, string> = {
  cumple: "Cumple",
  cumple_con_observaciones: "Cumple con observaciones",
  no_cumple: "No cumple",
  no_apto: "No apto",
};

function fmtDist(m: number | null | undefined): string {
  if (m == null) return "s/d";
  if (m >= 1000) return `${(m / 1000).toFixed(1)} km`;
  return `${Math.round(m)} m`;
}

function fmtNum(n: number | null | undefined, suffix = ""): string {
  if (n == null) return "s/d";
  return `${n}${suffix}`;
}

function usoText(u: string | string[] | null | undefined): string {
  if (u == null) return "s/d";
  return Array.isArray(u) ? u.join(", ") : u;
}

const riesgoColor: Record<string, string> = {
  bajo: "var(--accent-green)",
  moderado: "var(--accent-yellow)",
  alto: "var(--accent-red)",
};

export function ExtractPanel({
  context,
  loading,
  error,
  onClose,
  onGenerate,
  scene,
  sceneLoading,
  sceneError,
  onDiagnose,
  diag,
  diagLoading,
  diagError,
}: ExtractPanelProps) {
  const isOpen = loading || error !== null || context !== null;

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
            Extracción on-demand
          </span>
          <span
            className="text-lg font-bold"
            style={{ color: "#a78bfa" }}
          >
            Área analizada
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

      <div
        className="flex flex-1 flex-col gap-6 overflow-y-auto px-6 py-5"
        style={{ scrollbarGutter: "stable" }}
      >
        {loading && (
          <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
            Extrayendo contexto territorial…
          </p>
        )}

        {error && (
          <div
            className="rounded-xl px-4 py-3 text-xs"
            style={{
              background: "rgba(239, 68, 68, 0.1)",
              color: "var(--accent-red)",
              border: "1px solid rgba(239, 68, 68, 0.2)",
            }}
          >
            {error}
          </div>
        )}

        {context && !loading && (
          <>
            {/* Resumen del polígono */}
            <Section title="Polígono">
              <DetailRow
                label="Superficie"
                value={`${context.area_ha.toLocaleString("es-AR")} ha`}
              />
              <DetailRow label="CRS métrico" value={context.crs_metric} isLast />
            </Section>

            {/* Normativa */}
            <Section
              title={`Normativa ${
                context.normativa.modo ? `(${context.normativa.modo})` : ""
              }`}
            >
              {context.normativa.zonas.length === 0 ? (
                <DetailRow label="Zonas" value="Sin datos de zonificación" isLast />
              ) : (
                context.normativa.zonas.map((z, i) => (
                  <div
                    key={i}
                    className="flex flex-col gap-0"
                    style={{
                      borderBottom:
                        i < context.normativa.zonas.length - 1
                          ? "1px solid var(--border-subtle)"
                          : "none",
                    }}
                  >
                    <DetailRow
                      label="Categoría"
                      value={z.categoria ?? "s/d"}
                    />
                    <DetailRow label="Uso" value={usoText(z.uso_permitido)} />
                    <DetailRow label="FOS" value={fmtNum(z.fos)} />
                    <DetailRow label="FOT" value={fmtNum(z.fot)} />
                    <DetailRow
                      label="Altura máx."
                      value={fmtNum(z.altura_max_m, " m")}
                    />
                    {z.cobertura_pct != null && (
                      <DetailRow
                        label="Cobertura"
                        value={`${z.cobertura_pct}%`}
                      />
                    )}
                  </div>
                ))
              )}
            </Section>

            {/* Restricciones */}
            {context.normativa.restricciones.length > 0 && (
              <Section title="Restricciones">
                {context.normativa.restricciones.map((r, i, arr) => (
                  <DetailRow
                    key={i}
                    label={r.tipo.replace(/_/g, " ")}
                    value={
                      r.geometria_afectada_pct != null
                        ? `${r.geometria_afectada_pct}% afectado`
                        : "s/d"
                    }
                    valueColor="var(--accent-orange)"
                    isLast={i === arr.length - 1}
                  />
                ))}
              </Section>
            )}

            {/* Físico */}
            <Section title="Físico">
              <DetailRow
                label="Pendiente media"
                value={fmtNum(context.fisico.pendiente_media_pct, "%")}
              />
              <DetailRow
                label="Pendiente máx."
                value={fmtNum(context.fisico.pendiente_max_pct, "%")}
              />
              <DetailRow
                label="Riesgo hídrico"
                value={context.fisico.riesgo_hidrico ?? "s/d"}
                valueColor={
                  context.fisico.riesgo_hidrico
                    ? riesgoColor[context.fisico.riesgo_hidrico]
                    : undefined
                }
              />
              <DetailRow
                label="Fuente DEM"
                value={context.fisico.dem_source ?? "s/d"}
                isLast
              />
            </Section>

            {/* Accesibilidad */}
            <Section title="Accesibilidad">
              <DetailRow
                label="Dist. vial principal"
                value={fmtDist(context.accesibilidad.dist_vial_principal_m)}
              />
              {context.accesibilidad.equipamiento.length === 0 ? (
                <DetailRow label="Equipamiento" value="Sin datos" isLast />
              ) : (
                context.accesibilidad.equipamiento.map((eq, i, arr) => (
                  <DetailRow
                    key={`${eq.tipo}-${i}`}
                    label={eq.tipo}
                    value={fmtDist(eq.dist_m)}
                    isLast={i === arr.length - 1}
                  />
                ))
              )}
            </Section>

            {/* Hidrografía */}
            {context.hidrografia.length > 0 && (
              <Section title="Hidrografía">
                {context.hidrografia.map((h, i, arr) => (
                  <DetailRow
                    key={i}
                    label={h.nombre || h.tipo}
                    value={fmtDist(h.dist_m)}
                    isLast={i === arr.length - 1}
                  />
                ))}
              </Section>
            )}

            {/* Parcelas */}
            {context.parcelas.length > 0 && (
              <Section title={`Parcelas (${context.parcelas.length})`}>
                {context.parcelas.slice(0, 8).map((p, i, arr) => (
                  <DetailRow
                    key={p.id ?? i}
                    label={p.id ?? "s/d"}
                    value={
                      p.sup_m2 != null
                        ? `${p.sup_m2.toLocaleString("es-AR")} m²`
                        : "s/d"
                    }
                    isLast={i === arr.length - 1 && context.parcelas.length <= 8}
                  />
                ))}
                {context.parcelas.length > 8 && (
                  <DetailRow
                    label="…"
                    value={`+${context.parcelas.length - 8} más`}
                    isLast
                  />
                )}
              </Section>
            )}

            {/* Escenario 3D (CAPA 2) */}
            {onGenerate && (
              <div className="flex flex-col gap-3">
                <span
                  className="text-[10px] font-semibold uppercase tracking-[0.2em]"
                  style={{ color: "var(--text-muted)" }}
                >
                  Escenario 3D
                </span>
                <button
                  onClick={onGenerate}
                  disabled={sceneLoading}
                  className="rounded-lg px-3 py-2.5 text-xs font-semibold uppercase tracking-wider transition-all"
                  style={{
                    background: sceneLoading ? "var(--bg-surface)" : "#a78bfa18",
                    border: "1px solid #a78bfa",
                    color: "#a78bfa",
                    cursor: sceneLoading ? "wait" : "pointer",
                  }}
                >
                  {sceneLoading
                    ? "Generando…"
                    : scene
                      ? "Regenerar escenario 3D"
                      : "Generar escenario 3D"}
                </button>
                {sceneError && (
                  <p className="text-[11px]" style={{ color: "var(--accent-red)" }}>
                    {sceneError}
                  </p>
                )}
                {scene && scene.metricas.n_lotes === 0 && (
                  <div
                    className="flex flex-col gap-2 rounded-xl px-4 py-3"
                    style={{
                      background: "rgba(234, 179, 8, 0.08)",
                      border: "1px solid rgba(234, 179, 8, 0.25)",
                    }}
                  >
                    <span className="text-xs font-semibold" style={{ color: "var(--accent-yellow)" }}>
                      No se generaron masas en esta área
                    </span>
                    <span className="text-[11px] leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                      {scene.warnings.length
                        ? scene.warnings.join(" · ")
                        : "El área no es urbanizable (muy chica, pendiente excesiva o sobre una restricción). Probá un polígono más grande sobre el oasis o en terreno llano."}
                    </span>
                  </div>
                )}
                {scene && scene.metricas.n_lotes > 0 && (
                  <>
                    <div
                      className="flex flex-col gap-0 overflow-hidden rounded-xl"
                      style={{
                        background: "var(--bg-surface)",
                        border: "1px solid var(--border-subtle)",
                      }}
                    >
                      <DetailRow label="Lotes" value={`${scene.metricas.n_lotes}`} />
                      <DetailRow
                        label="Ocupación propuesta"
                        value={`${(scene.metricas.ocupacion_propuesta * 100).toFixed(0)}%`}
                      />
                      <DetailRow
                        label="FOT propuesto"
                        value={scene.metricas.fot_propuesto.toFixed(2)}
                      />
                      <DetailRow
                        label="Verde"
                        value={`${(scene.metricas.sup_verde_pct * 100).toFixed(1)}%`}
                        valueColor="var(--accent-green)"
                      />
                      <DetailRow
                        label="Densidad"
                        value={`${scene.metricas.densidad_lotes_ha} lotes/ha`}
                      />
                      <DetailRow
                        label="Restricciones"
                        value={
                          scene.restricciones_respetadas.length
                            ? scene.restricciones_respetadas.join(", ")
                            : "ninguna"
                        }
                        isLast
                      />
                    </div>
                    {scene.warnings.length > 0 && (
                      <p
                        className="text-[10px] leading-relaxed"
                        style={{ color: "var(--text-muted)" }}
                      >
                        {scene.warnings.join(" · ")}
                      </p>
                    )}
                  </>
                )}
              </div>
            )}

            {/* Diagnóstico normativo (CAPA 3) */}
            {onDiagnose && (
              <div className="flex flex-col gap-3">
                <span
                  className="text-[10px] font-semibold uppercase tracking-[0.2em]"
                  style={{ color: "var(--text-muted)" }}
                >
                  Diagnóstico normativo
                </span>
                <button
                  onClick={onDiagnose}
                  disabled={diagLoading}
                  className="rounded-lg px-3 py-2.5 text-xs font-semibold uppercase tracking-wider transition-all"
                  style={{
                    background: diagLoading ? "var(--bg-surface)" : "var(--accent-cyan)18",
                    border: "1px solid var(--accent-cyan)",
                    color: "var(--accent-cyan)",
                    cursor: diagLoading ? "wait" : "pointer",
                  }}
                >
                  {diagLoading
                    ? "Diagnosticando…"
                    : diag
                      ? "Re-diagnosticar"
                      : "Diagnosticar normativa"}
                </button>
                {diagError && (
                  <p className="text-[11px]" style={{ color: "var(--accent-red)" }}>
                    {diagError}
                  </p>
                )}
                {diag && (
                  <div className="flex flex-col gap-3">
                    {/* Estado + aptitud (ejes separados) */}
                    <div
                      className="flex items-center justify-between rounded-xl px-4 py-3"
                      style={{
                        background: "var(--bg-surface)",
                        border: `1px solid ${
                          diag.estado_global.startsWith("cumple")
                            ? "var(--accent-green)40"
                            : "var(--accent-red)40"
                        }`,
                      }}
                    >
                      <span
                        className="text-xs font-bold uppercase tracking-wide"
                        style={{
                          color: diag.estado_global.startsWith("cumple")
                            ? "var(--accent-green)"
                            : "var(--accent-red)",
                        }}
                      >
                        {ESTADO_LABEL[diag.estado_global] ?? diag.estado_global}
                      </span>
                      <span className="text-xs" style={{ color: "var(--text-secondary)" }}>
                        Aptitud{" "}
                        <b style={{ color: "var(--text-primary)" }}>
                          {diag.indice_aptitud}/100
                        </b>
                      </span>
                    </div>

                    {/* Resumen ejecutivo */}
                    <p
                      className="rounded-xl px-4 py-3 text-[11px] leading-relaxed"
                      style={{
                        background: "var(--bg-surface)",
                        border: "1px solid var(--border-subtle)",
                        color: "var(--text-secondary)",
                      }}
                    >
                      {diag.resumen_ejecutivo}
                    </p>

                    {/* Checks */}
                    <div className="flex flex-col gap-2">
                      {diag.checks.map((c) => (
                        <div
                          key={c.regla}
                          className="flex flex-col gap-1 rounded-lg px-3 py-2"
                          style={{
                            background: "var(--bg-surface)",
                            borderLeft: `2px solid ${RESULTADO_COLOR[c.resultado]}`,
                          }}
                        >
                          <div className="flex items-center justify-between">
                            <span
                              className="text-[11px] font-semibold capitalize"
                              style={{ color: "var(--text-primary)" }}
                            >
                              {c.regla.replace(/_/g, " ")}
                              {c.es_regla_dura && (
                                <span style={{ color: "var(--text-muted)" }}> · dura</span>
                              )}
                            </span>
                            <span
                              className="text-[10px] font-bold uppercase"
                              style={{ color: RESULTADO_COLOR[c.resultado] }}
                            >
                              {c.resultado.replace(/_/g, " ")}
                            </span>
                          </div>
                          <span
                            className="text-[11px] leading-snug"
                            style={{ color: "var(--text-secondary)" }}
                          >
                            {c.explicacion || c.detalle_tecnico}
                          </span>
                          {c.fuente && (
                            <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                              {c.fuente.norma} · {c.fuente.articulo}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>

                    <p className="text-[10px] italic" style={{ color: "var(--text-muted)" }}>
                      {diag.disclaimer}
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Warnings */}
            {context.warnings.length > 0 && (
              <div className="flex flex-col gap-2">
                <span
                  className="text-[10px] font-semibold uppercase tracking-[0.2em]"
                  style={{ color: "var(--text-muted)" }}
                >
                  Advertencias ({context.warnings.length})
                </span>
                {context.warnings.map((w, i) => (
                  <p
                    key={i}
                    className="rounded-lg px-3 py-2 text-[11px] leading-relaxed"
                    style={{
                      background: "rgba(234, 179, 8, 0.08)",
                      color: "var(--accent-yellow)",
                      border: "1px solid rgba(234, 179, 8, 0.15)",
                    }}
                  >
                    {w}
                  </p>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      <div
        className="px-6 py-4"
        style={{ borderTop: "1px solid var(--border-subtle)" }}
      >
        <p
          className="text-[10px] leading-relaxed"
          style={{ color: "var(--text-muted)" }}
        >
          Cóndor View — CAPA 1 (extracción) · schema {context?.schema_version ?? "1.1"}
        </p>
      </div>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3">
      <span
        className="text-[10px] font-semibold uppercase tracking-[0.2em]"
        style={{ color: "var(--text-muted)" }}
      >
        {title}
      </span>
      <div
        className="flex flex-col gap-0 overflow-hidden rounded-xl"
        style={{
          background: "var(--bg-surface)",
          border: "1px solid var(--border-subtle)",
        }}
      >
        {children}
      </div>
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
      style={{ borderBottom: isLast ? "none" : "1px solid var(--border-subtle)" }}
    >
      <span className="text-xs capitalize" style={{ color: "var(--text-secondary)" }}>
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
