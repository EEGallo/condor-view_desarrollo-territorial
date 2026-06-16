"use client";

import { CATEGORY_COLORS, CATEGORY_LABELS } from "./types";
import type { Categoria } from "./types";

const CATEGORIES: Categoria[] = ["alta", "media", "baja", "no_apto"];

export function Legend() {
  return (
    <div
      className="fixed bottom-6 left-6 z-20 flex flex-col gap-2 rounded-xl px-4 py-3"
      style={{
        background: "var(--bg-glass)",
        backdropFilter: "blur(16px) saturate(1.4)",
        WebkitBackdropFilter: "blur(16px) saturate(1.4)",
        border: "1px solid var(--border-subtle)",
        boxShadow: "0 8px 32px rgba(0, 0, 0, 0.4)",
      }}
    >
      <span
        className="text-[10px] font-semibold uppercase tracking-[0.15em]"
        style={{ color: "var(--text-muted)" }}
      >
        Aptitud territorial
      </span>

      {CATEGORIES.map((cat) => (
        <div key={cat} className="flex items-center gap-2.5">
          <span
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={{
              background: CATEGORY_COLORS[cat],
              boxShadow: `0 0 6px ${CATEGORY_COLORS[cat]}50`,
            }}
          />
          <span
            className="text-xs"
            style={{ color: "var(--text-secondary)" }}
          >
            {CATEGORY_LABELS[cat]}
          </span>
        </div>
      ))}
    </div>
  );
}
