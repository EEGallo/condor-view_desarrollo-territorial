"use client";

type ScoreBarProps = {
  label: string;
  value: number;
  color: string;
};

export function ScoreBar({ label, value, color }: ScoreBarProps) {
  const percentage = Math.round(value * 100);

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between">
        <span
          className="text-xs tracking-wide uppercase"
          style={{ color: "var(--text-secondary)" }}
        >
          {label}
        </span>
        <span
          className="text-xs font-mono font-semibold"
          style={{ color }}
        >
          {percentage}%
        </span>
      </div>
      <div
        className="relative h-2 w-full overflow-hidden rounded-full"
        style={{ background: "var(--bg-void)" }}
      >
        <div
          className="absolute inset-y-0 left-0 rounded-full"
          style={{
            width: `${percentage}%`,
            background: `linear-gradient(90deg, ${color}cc, ${color})`,
            transition: "width var(--duration-slow) var(--ease-out-expo)",
            boxShadow: `0 0 12px ${color}40`,
          }}
        />
      </div>
    </div>
  );
}
