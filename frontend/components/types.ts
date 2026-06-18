export type Categoria = "alta" | "media" | "baja" | "no_apto";

export type ZoneProperties = {
  id: string;
  iat: number;
  categoria: Categoria;
  s_norm: number;
  s_fis: number;
  s_acc: number;
  uso_permitido: string;
  pendiente_pct: number;
  riesgo_hidrico: string;
  elevacion_m?: number;
  dist_huella_m: number;
  dist_vial_m: number;
  dist_agua_m?: number;
  en_oasis?: boolean;
  distrito?: string;
  flags: string[];
};

export const CATEGORY_COLORS: Record<Categoria, string> = {
  alta: "#22c55e",
  media: "#eab308",
  baja: "#ef4444",
  no_apto: "#374151",
} as const;

export const CATEGORY_LABELS: Record<Categoria, string> = {
  alta: "Alta aptitud",
  media: "Aptitud media",
  baja: "Baja aptitud",
  no_apto: "No apto",
} as const;

export const FLAG_LABELS: Record<string, string> = {
  pendiente_elevada: "Pendiente elevada",
  pendiente_critica: "Pendiente crítica",
  riesgo_hidrico_alto: "Riesgo hídrico alto",
  riesgo_hidrico_moderado: "Riesgo hídrico moderado",
  lejos_de_huella: "Lejos de huella urbana",
  sin_acceso_vial: "Sin acceso vial",
  uso_no_permitido: "Uso no permitido",
  zona_montanosa: "Zona montañosa",
  altitud_extrema: "Altitud extrema",
  zona_desertica: "Zona desértica",
  reserva_natural: "Reserva natural",
  reserva_hidrica: "Reserva hídrica",
  zona_embalse: "Zona de embalse",
} as const;
