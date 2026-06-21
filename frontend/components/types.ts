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
  poblacion_est?: number;
  dist_escuela_m?: number;
  dist_salud_m?: number;
  deficit_servicios?: number;
  tiempo_huella_min?: number;
  tiempo_servicio_min?: number;
  en_oasis?: boolean;
  distrito?: string;
  flags: string[];
};

// --- Extracción on-demand (CAPA 1): PolygonContext del backend /api/extract ---
export type ExtractZona = {
  categoria?: string | null;
  uso_permitido?: string | string[] | null;
  fos?: number | null;
  fot?: number | null;
  altura_max_m?: number | null;
  densidad?: string | null;
  cobertura_pct?: number | null;
  source?: string | null;
  normativa_raw?: Record<string, unknown> | null;
};

export type ExtractEquipamiento = {
  tipo: string;
  nombre?: string | null;
  dist_m?: number | null;
};

export type ExtractContext = {
  schema_version: string;
  bbox: number[];
  area_ha: number;
  crs_metric: string;
  normativa: {
    modo?: "atributos" | "tabla" | null;
    zonas: ExtractZona[];
    restricciones: { tipo: string; geometria_afectada_pct?: number | null }[];
  };
  fisico: {
    pendiente_media_pct?: number | null;
    pendiente_max_pct?: number | null;
    riesgo_hidrico?: string | null;
    dem_source?: string | null;
  };
  hidrografia: { tipo: string; nombre?: string | null; dist_m?: number | null }[];
  accesibilidad: {
    dist_huella_urbana_m?: number | null;
    dist_vial_principal_m?: number | null;
    equipamiento: ExtractEquipamiento[];
  };
  parcelas: { id?: string | null; sup_m2?: number | null; source?: string | null }[];
  warnings: string[];
};

// --- Registro de proyectos (obras/desarrollos sobre el territorio) ---
export type ProyectoTipo =
  | "ruta"
  | "escuela"
  | "salud"
  | "agua"
  | "loteo"
  | "otro";
export type ProyectoEstado = "planeado" | "en_ejecucion" | "ejecutado";

export type Proyecto = {
  id: string;
  nombre: string;
  tipo: ProyectoTipo;
  estado: ProyectoEstado;
  descripcion?: string;
  anio?: number;
  coords: [number, number];
};

export const PROYECTO_TIPO_LABELS: Record<ProyectoTipo, string> = {
  ruta: "Ruta / vial",
  escuela: "Educación",
  salud: "Salud",
  agua: "Agua / saneamiento",
  loteo: "Loteo / vivienda",
  otro: "Otro",
};

export const PROYECTO_ESTADO_LABELS: Record<ProyectoEstado, string> = {
  planeado: "Planeado",
  en_ejecucion: "En ejecución",
  ejecutado: "Ejecutado",
};

export const PROYECTO_ESTADO_COLORS: Record<ProyectoEstado, string> = {
  planeado: "#22d3ee",
  en_ejecucion: "#eab308",
  ejecutado: "#22c55e",
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
