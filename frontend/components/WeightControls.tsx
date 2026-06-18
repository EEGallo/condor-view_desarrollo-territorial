"use client";

import { useState, useCallback } from "react";

type Weights = {
  w_norm: number;
  w_fis: number;
  w_acc: number;
};

type WeightControlsProps = {
  onWeightsChange: (weights: Weights) => void;
};

const DEFAULT_WEIGHTS: Weights = { w_norm: 0.4, w_fis: 0.3, w_acc: 0.3 };

const LABELS: Record<keyof Weights, { name: string; color: string }> = {
  w_norm: { name: "Normativa", color: "var(--accent-cyan)" },
  w_fis: { name: "Físico", color: "var(--accent-yellow)" },
  w_acc: { name: "Accesibilidad", color: "#a78bfa" },
};

function normalizeWeights(weights: Weights, changedKey: keyof Weights): Weights {
  const newVal = weights[changedKey];
  const remaining = 1 - newVal;
  const otherKeys = (Object.keys(weights) as (keyof Weights)[]).filter(
    (k) => k !== changedKey
  );
  const otherSum = otherKeys.reduce((sum, k) => sum + weights[k], 0);

  if (otherSum === 0) {
    const share = remaining / otherKeys.length;
    return { ...weights, ...Object.fromEntries(otherKeys.map((k) => [k, share])) } as Weights;
  }

  const result = { ...weights };
  for (const k of otherKeys) {
    result[k] = (weights[k] / otherSum) * remaining;
  }
  return result;
}

export function WeightControls({ onWeightsChange }: WeightControlsProps) {
  const [weights, setWeights] = useState<Weights>(DEFAULT_WEIGHTS);
  const [isOpen, setIsOpen] = useState(false);

  const handleChange = useCallback(
    (key: keyof Weights, value: number) => {
      const clamped = Math.max(0, Math.min(1, value));
      const updated = normalizeWeights({ ...weights, [key]: clamped }, key);
      setWeights(updated);
      onWeightsChange(updated);
    },
    [weights, onWeightsChange]
  );

  const handleReset = useCallback(() => {
    setWeights(DEFAULT_WEIGHTS);
    onWeightsChange(DEFAULT_WEIGHTS);
  }, [onWeightsChange]);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
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
          <path d="M1 3h12M1 7h12M1 11h12" />
          <circle cx="4" cy="3" r="1.5" fill="currentColor" />
          <circle cx="9" cy="7" r="1.5" fill="currentColor" />
          <circle cx="6" cy="11" r="1.5" fill="currentColor" />
        </svg>
        Escenarios
      </button>

      {isOpen && (
        <div
          className="absolute right-0 top-full z-30 mt-2 flex flex-col gap-4 rounded-xl p-5"
          style={{
            background: "var(--bg-glass)",
            backdropFilter: "blur(24px) saturate(1.6)",
            WebkitBackdropFilter: "blur(24px) saturate(1.6)",
            border: "1px solid var(--border-subtle)",
            boxShadow: "0 20px 60px rgba(0, 0, 0, 0.4)",
            width: 260,
          }}
        >
          <div className="flex items-center justify-between">
            <span
              className="text-[10px] font-semibold uppercase tracking-[0.15em]"
              style={{ color: "var(--text-muted)" }}
            >
              Pesos del índice
            </span>
            <button
              onClick={handleReset}
              className="text-[10px] uppercase tracking-wider"
              style={{ color: "var(--text-muted)" }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = "var(--accent-cyan)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = "var(--text-muted)";
              }}
            >
              Reset
            </button>
          </div>

          {(Object.keys(LABELS) as (keyof Weights)[]).map((key) => (
            <WeightSlider
              key={key}
              label={LABELS[key].name}
              color={LABELS[key].color}
              value={weights[key]}
              onChange={(v) => handleChange(key, v)}
            />
          ))}

          <p
            className="text-center text-[10px] leading-relaxed"
            style={{ color: "var(--text-muted)" }}
          >
            Ajustá los pesos para simular distintos criterios de evaluación
          </p>
        </div>
      )}
    </div>
  );
}

function WeightSlider({
  label,
  color,
  value,
  onChange,
}: {
  label: string;
  color: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between">
        <span className="text-xs" style={{ color: "var(--text-secondary)" }}>
          {label}
        </span>
        <span className="font-mono text-xs font-semibold" style={{ color }}>
          {Math.round(value * 100)}%
        </span>
      </div>
      <input
        type="range"
        min={0}
        max={100}
        step={5}
        value={Math.round(value * 100)}
        onChange={(e) => onChange(Number(e.target.value) / 100)}
        className="weight-slider w-full"
        style={
          {
            "--slider-color": color,
            accentColor: color,
          } as React.CSSProperties
        }
      />
    </div>
  );
}
