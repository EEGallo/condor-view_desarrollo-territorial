"use client";

type LoadingOverlayProps = {
  visible: boolean;
};

export function LoadingOverlay({ visible }: LoadingOverlayProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-4"
      style={{
        background: "var(--bg-void)",
        opacity: visible ? 1 : 0,
        pointerEvents: visible ? "auto" : "none",
        transition: "opacity 0.5s ease",
      }}
    >
      <div
        className="h-10 w-10 rounded-full"
        style={{
          border: "3px solid var(--border-subtle)",
          borderTopColor: "var(--accent-cyan)",
          animation: "condor-spin 0.8s linear infinite",
        }}
      />
      <span
        className="text-xs uppercase tracking-[0.2em]"
        style={{ color: "var(--text-muted)" }}
      >
        Cargando territorio…
      </span>
      <style>{`@keyframes condor-spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
