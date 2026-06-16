"use client";

import { useCallback, useState } from "react";
import type { ZoneProperties } from "./types";
import { CATEGORY_LABELS, FLAG_LABELS } from "./types";

type ExportButtonProps = {
  zone: ZoneProperties | null;
};

export function ExportButton({ zone }: ExportButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleExport = useCallback(() => {
    if (!zone) return;

    const lines = [
      "═══════════════════════════════════════════",
      "  CÓNDOR VIEW — Informe de Zona",
      "  Observatorio de Aptitud Territorial",
      "═══════════════════════════════════════════",
      "",
      `  Zona: ${zone.id}`,
      `  Fecha: ${new Date().toLocaleDateString("es-AR")}`,
      zone.distrito ? `  Distrito: ${zone.distrito}` : null,
      zone.en_oasis != null
        ? `  Oasis irrigado: ${zone.en_oasis ? "Sí" : "No"}`
        : null,
      "",
      "───────────────────────────────────────────",
      "  ÍNDICE DE APTITUD TERRITORIAL (IAT)",
      "───────────────────────────────────────────",
      "",
      `  Puntaje:    ${Math.round(zone.iat)} / 100`,
      `  Categoría:  ${CATEGORY_LABELS[zone.categoria]}`,
      "",
      "  Componentes:",
      `    Normativa:       ${(zone.s_norm * 100).toFixed(0)}%`,
      `    Físico:          ${(zone.s_fis * 100).toFixed(0)}%`,
      `    Accesibilidad:   ${(zone.s_acc * 100).toFixed(0)}%`,
      "",
      "───────────────────────────────────────────",
      "  DETALLE TERRITORIAL",
      "───────────────────────────────────────────",
      "",
      `  Uso permitido:     ${zone.uso_permitido.replace(/_/g, " ")}`,
      `  Pendiente:         ${zone.pendiente_pct.toFixed(1)}%`,
      `  Riesgo hídrico:    ${zone.riesgo_hidrico.replace(/_/g, " ")}`,
      zone.elevacion_m != null
        ? `  Elevación:         ${zone.elevacion_m} m`
        : null,
      `  Dist. huella:      ${zone.dist_huella_m} m`,
      `  Dist. vial:        ${zone.dist_vial_m} m`,
    ]
      .filter(Boolean)
      .join("\n");

    const flagSection =
      zone.flags.length > 0
        ? [
            "",
            "───────────────────────────────────────────",
            "  ALERTAS",
            "───────────────────────────────────────────",
            "",
            ...zone.flags.map(
              (f) => `  ⚠ ${FLAG_LABELS[f] ?? f}`
            ),
          ].join("\n")
        : "";

    const footer = [
      "",
      "",
      "═══════════════════════════════════════════",
      "  Generado por Cóndor View MVP",
      "  San Rafael, Mendoza — Argentina",
      "═══════════════════════════════════════════",
    ].join("\n");

    const report = lines + flagSection + footer;

    navigator.clipboard.writeText(report).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [zone]);

  if (!zone) return null;

  return (
    <button
      onClick={handleExport}
      className="flex items-center gap-2 rounded-lg px-3 py-2 text-[11px] font-medium uppercase tracking-wider transition-all"
      style={{
        background: copied ? "var(--accent-cyan)" : "var(--bg-surface)",
        color: copied ? "var(--bg-void)" : "var(--text-secondary)",
        border: "1px solid var(--border-subtle)",
      }}
    >
      <svg
        width="12"
        height="12"
        viewBox="0 0 12 12"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
      >
        {copied ? (
          <path d="M2 6l3 3 5-5" strokeLinecap="round" strokeLinejoin="round" />
        ) : (
          <>
            <path d="M4 1H2a1 1 0 00-1 1v8a1 1 0 001 1h8a1 1 0 001-1V8" />
            <path d="M8 1h3v3M5 7l6-6" />
          </>
        )}
      </svg>
      {copied ? "Copiado" : "Exportar"}
    </button>
  );
}
