"use client";

import { useState } from "react";
import type { ProyectoTipo, ProyectoEstado } from "./types";
import { PROYECTO_TIPO_LABELS, PROYECTO_ESTADO_LABELS } from "./types";

export type ProjectFormData = {
  nombre: string;
  tipo: ProyectoTipo;
  estado: ProyectoEstado;
  descripcion: string;
  anio: number;
};

type ProjectFormProps = {
  onSave: (data: ProjectFormData) => void;
  onCancel: () => void;
};

export function ProjectForm({ onSave, onCancel }: ProjectFormProps) {
  const [nombre, setNombre] = useState("");
  const [tipo, setTipo] = useState<ProyectoTipo>("otro");
  const [estado, setEstado] = useState<ProyectoEstado>("planeado");
  const [descripcion, setDescripcion] = useState("");
  const [anio, setAnio] = useState(2026);

  const submit = () => {
    if (!nombre.trim()) return;
    onSave({ nombre: nombre.trim(), tipo, estado, descripcion: descripcion.trim(), anio });
  };

  const fieldStyle: React.CSSProperties = {
    background: "var(--bg-surface)",
    border: "1px solid var(--border-subtle)",
    color: "var(--text-primary)",
    borderRadius: 8,
    padding: "8px 10px",
    fontSize: 13,
    width: "100%",
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: "rgba(0,0,0,0.5)" }}
      onClick={onCancel}
    >
      <div
        className="flex w-[360px] max-w-[92vw] flex-col gap-3 rounded-2xl p-6"
        style={{
          background: "var(--bg-glass)",
          backdropFilter: "blur(24px) saturate(1.6)",
          WebkitBackdropFilter: "blur(24px) saturate(1.6)",
          border: "1px solid var(--border-accent)",
          boxShadow: "0 30px 80px rgba(0,0,0,0.5)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <span className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>
          Nuevo proyecto
        </span>

        <input
          autoFocus
          placeholder="Nombre de la obra"
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          style={fieldStyle}
        />

        <div className="flex gap-2">
          <select value={tipo} onChange={(e) => setTipo(e.target.value as ProyectoTipo)} style={fieldStyle}>
            {(Object.keys(PROYECTO_TIPO_LABELS) as ProyectoTipo[]).map((t) => (
              <option key={t} value={t}>{PROYECTO_TIPO_LABELS[t]}</option>
            ))}
          </select>
          <select value={estado} onChange={(e) => setEstado(e.target.value as ProyectoEstado)} style={fieldStyle}>
            {(Object.keys(PROYECTO_ESTADO_LABELS) as ProyectoEstado[]).map((s) => (
              <option key={s} value={s}>{PROYECTO_ESTADO_LABELS[s]}</option>
            ))}
          </select>
        </div>

        <textarea
          placeholder="Descripción (opcional)"
          value={descripcion}
          onChange={(e) => setDescripcion(e.target.value)}
          rows={3}
          style={{ ...fieldStyle, resize: "vertical" }}
        />

        <input
          type="number"
          value={anio}
          onChange={(e) => setAnio(Number(e.target.value))}
          style={fieldStyle}
        />

        <div className="mt-1 flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="rounded-lg px-4 py-2 text-xs font-semibold"
            style={{ color: "var(--text-secondary)", border: "1px solid var(--border-subtle)" }}
          >
            Cancelar
          </button>
          <button
            onClick={submit}
            disabled={!nombre.trim()}
            className="rounded-lg px-4 py-2 text-xs font-semibold"
            style={{
              background: nombre.trim() ? "var(--accent-cyan)" : "var(--bg-surface)",
              color: nombre.trim() ? "var(--bg-void)" : "var(--text-muted)",
            }}
          >
            Guardar
          </button>
        </div>
      </div>
    </div>
  );
}
