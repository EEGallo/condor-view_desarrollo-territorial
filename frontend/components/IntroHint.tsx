"use client";

import { useState } from "react";

const STEPS = [
  {
    n: "1",
    title: "Elegí una capa",
    desc: "Aptitud territorial o déficit de servicios, arriba.",
  },
  {
    n: "2",
    title: "Explorá una zona",
    desc: "Click en cualquier celda para ver su desglose y el porqué.",
  },
  {
    n: "3",
    title: "Simulá una intervención",
    desc: "Colocá una ruta o servicio y mirá qué potencial se desbloquea.",
  },
];

export function IntroHint() {
  const [dismissed, setDismissed] = useState(false);
  if (dismissed) return null;

  return (
    <div
      className="fixed bottom-6 left-1/2 z-40 flex w-[440px] max-w-[90vw] -translate-x-1/2 flex-col gap-3 rounded-xl px-5 py-4"
      style={{
        background: "var(--bg-glass)",
        backdropFilter: "blur(24px) saturate(1.6)",
        WebkitBackdropFilter: "blur(24px) saturate(1.6)",
        border: "1px solid var(--border-accent)",
        boxShadow: "0 20px 60px rgba(0, 0, 0, 0.45)",
      }}
    >
      <div className="flex items-start justify-between">
        <div className="flex flex-col">
          <span
            className="text-sm font-bold"
            style={{ color: "var(--text-primary)" }}
          >
            Decisión territorial, explicable
          </span>
          <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
            Dónde crece la ciudad, qué falta, qué desbloquea cada obra.
          </span>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="flex h-7 w-7 items-center justify-center rounded-lg transition-colors"
          style={{
            background: "var(--bg-surface)",
            color: "var(--text-secondary)",
            border: "1px solid var(--border-subtle)",
          }}
          aria-label="Cerrar"
        >
          <svg
            width="12"
            height="12"
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

      <div className="flex flex-col gap-2">
        {STEPS.map((s) => (
          <div key={s.n} className="flex items-center gap-3">
            <span
              className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full text-[11px] font-bold"
              style={{
                background: "var(--bg-elevated)",
                color: "var(--accent-cyan)",
                border: "1px solid var(--border-accent)",
              }}
            >
              {s.n}
            </span>
            <div className="flex flex-col">
              <span
                className="text-xs font-semibold"
                style={{ color: "var(--text-secondary)" }}
              >
                {s.title}
              </span>
              <span
                className="text-[11px] leading-snug"
                style={{ color: "var(--text-muted)" }}
              >
                {s.desc}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
