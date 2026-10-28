import type {
  GraphtecChartPreviewResponse,
  GraphtecChartSettings,
  GraphtecInspectionResponse,
  GraphtecSeriesId,
} from "../types/graphtec";

/** Longitud máxima admitida para el título. */
export const MAX_GRAPHTEC_TITLE_LENGTH = 200;

/** Título utilizado cuando el contenido no proporciona uno. */
export const GENERIC_GRAPHTEC_TITLE = "Graphtec chart";

/**
 * Valores editables del formulario. Los tiempos se guardan como texto para
 * permitir campos vacíos (intervalo completo).
 */
export interface GraphtecChartForm {
  series: GraphtecSeriesId[];
  title: string;
  showLegend: boolean;
  showPhaseSeparators: boolean;
  timeMin: string;
  timeMax: string;
}

/** Estado de la previsualización. */
export interface GraphtecPreviewState {
  status: "idle" | "loading" | "ready" | "error";
  /** Identificador de la última petición enviada. */
  requestId: number;
  /** Configuración (serializada) de la última petición enviada. */
  formKey: string | null;
  response: GraphtecChartPreviewResponse | null;
  error: string | null;
}

/** Estado del guardado. */
export interface GraphtecSaveState {
  status: "idle" | "saving" | "saved" | "error";
  message: string | null;
}

/** Estado completo del panel de gráficas Graphtec. */
export interface GraphtecPanelState {
  form: GraphtecChartForm;
  preview: GraphtecPreviewState;
  save: GraphtecSaveState;
  /**
   * Se activa tras la primera previsualización para regenerarla al cambiar
   * las series, el intervalo u otras opciones.
   */
  autoRefresh: boolean;
}

/** Acciones admitidas por {@link graphtecPanelReducer}. */
export type GraphtecPanelAction =
  | { type: "formChanged"; patch: Partial<GraphtecChartForm> }
  | { type: "seriesToggled"; seriesId: GraphtecSeriesId; selected: boolean }
  | { type: "reset"; inspection: GraphtecInspectionResponse }
  | { type: "previewRequested"; requestId: number; formKey: string }
  | {
      type: "previewSucceeded";
      requestId: number;
      response: GraphtecChartPreviewResponse;
    }
  | { type: "previewFailed"; requestId: number; message: string }
  | { type: "saveStarted" }
  | { type: "saveSucceeded"; chartName: string }
  | { type: "saveFailed"; message: string };

/**
 * Configuración inicial: series por defecto (tensión y corriente o
 * resistencia), leyenda y separadores visibles, intervalo completo y título
 * obtenido del contenido.
 */
export function defaultGraphtecForm(
  inspection: GraphtecInspectionResponse,
): GraphtecChartForm {
  return {
    series: inspection.available_series
      .filter((series) => series.default_selected !== false)
      .map((series) => series.id),
    title: inspection.default_title?.trim() || GENERIC_GRAPHTEC_TITLE,
    showLegend: true,
    showPhaseSeparators: true,
    timeMin: "",
    timeMax: "",
  };
}

/** Estado inicial del panel para un análisis concreto. */
export function initialGraphtecPanelState(
  inspection: GraphtecInspectionResponse,
): GraphtecPanelState {
  return {
    form: defaultGraphtecForm(inspection),
    preview: {
      status: "idle",
      requestId: 0,
      formKey: null,
      response: null,
      error: null,
    },
    save: { status: "idle", message: null },
    autoRefresh: false,
  };
}

function parseSeconds(text: string): number | null | "invalid" {
  const value = text.trim();
  if (value === "") {
    return null;
  }
  const number = Number(value);
  if (!Number.isFinite(number) || number < 0) {
    return "invalid";
  }
  return number;
}

/**
 * Valida el formulario.
 *
 * @returns Un mensaje en inglés o `null` si la configuración es válida.
 */
export function validateGraphtecForm(
  form: GraphtecChartForm,
  inspection: GraphtecInspectionResponse,
): string | null {
  if (form.series.length === 0) {
    return "Select at least one series.";
  }
  const available = new Set(inspection.available_series.map((s) => s.id));
  if (form.series.some((series) => !available.has(series))) {
    return "One of the selected series is not available for this file.";
  }
  if (form.title.length > MAX_GRAPHTEC_TITLE_LENGTH) {
    return `The title cannot exceed ${MAX_GRAPHTEC_TITLE_LENGTH} characters.`;
  }
  const start = parseSeconds(form.timeMin);
  const end = parseSeconds(form.timeMax);
  if (start === "invalid" || end === "invalid") {
    return "Start and end must be non-negative numbers of seconds.";
  }
  const effectiveStart = start ?? inspection.elapsed_time_start ?? 0;
  const effectiveEnd = end ?? inspection.elapsed_time_end ?? 0;
  if (effectiveStart >= effectiveEnd) {
    return "The start time must be lower than the end time.";
  }
  return null;
}

/** Convierte el formulario en la configuración enviada al backend. */
export function graphtecFormToSettings(
  form: GraphtecChartForm,
): GraphtecChartSettings {
  const start = parseSeconds(form.timeMin);
  const end = parseSeconds(form.timeMax);
  return {
    series: [...form.series],
    title: form.title.trim(),
    show_legend: form.showLegend,
    show_phase_separators: form.showPhaseSeparators,
    time_min: typeof start === "number" ? start : null,
    time_max: typeof end === "number" ? end : null,
  };
}

/** Clave estable de una configuración para detectar cambios. */
export function graphtecFormKey(form: GraphtecChartForm): string {
  return JSON.stringify(graphtecFormToSettings(form));
}

/**
 * Actualiza el estado del panel.
 *
 * Las respuestas de previsualización que no corresponden a la última
 * petición se descartan.
 */
export function graphtecPanelReducer(
  state: GraphtecPanelState,
  action: GraphtecPanelAction,
): GraphtecPanelState {
  switch (action.type) {
    case "formChanged":
      return {
        ...state,
        form: { ...state.form, ...action.patch },
        save: { status: "idle", message: null },
      };
    case "seriesToggled": {
      const selected = new Set(state.form.series);
      if (action.selected) {
        selected.add(action.seriesId);
      } else {
        selected.delete(action.seriesId);
      }
      const order: GraphtecSeriesId[] = ["voltage", "current", "resistance"];
      return graphtecPanelReducer(state, {
        type: "formChanged",
        patch: { series: order.filter((id) => selected.has(id)) },
      });
    }
    case "reset":
      return initialGraphtecPanelState(action.inspection);
    case "previewRequested":
      return {
        ...state,
        autoRefresh: true,
        preview: {
          ...state.preview,
          status: "loading",
          requestId: action.requestId,
          formKey: action.formKey,
          error: null,
        },
      };
    case "previewSucceeded":
      if (action.requestId !== state.preview.requestId) {
        return state;
      }
      return {
        ...state,
        preview: {
          ...state.preview,
          status: "ready",
          response: action.response,
          error: null,
        },
      };
    case "previewFailed":
      if (action.requestId !== state.preview.requestId) {
        return state;
      }
      return {
        ...state,
        preview: {
          ...state.preview,
          status: "error",
          response: null,
          error: action.message,
        },
      };
    case "saveStarted":
      return { ...state, save: { status: "saving", message: null } };
    case "saveSucceeded":
      return {
        ...state,
        save: { status: "saved", message: `Chart saved as ${action.chartName}.` },
      };
    case "saveFailed":
      return { ...state, save: { status: "error", message: action.message } };
    default:
      return state;
  }
}

/** Indica si la previsualización mostrada corresponde a la configuración actual. */
export function isGraphtecPreviewCurrent(state: GraphtecPanelState): boolean {
  return (
    state.preview.status === "ready" &&
    state.preview.formKey === graphtecFormKey(state.form)
  );
}

/**
 * Indica si debe regenerarse la previsualización automáticamente: ya se ha
 * solicitado una antes, la configuración es válida y ha cambiado.
 */
export function shouldAutoRefreshPreview(
  state: GraphtecPanelState,
  inspection: GraphtecInspectionResponse,
): boolean {
  return (
    state.autoRefresh &&
    state.preview.status !== "loading" &&
    validateGraphtecForm(state.form, inspection) === null &&
    state.preview.formKey !== graphtecFormKey(state.form)
  );
}

/** Indica si puede solicitarse una previsualización. */
export function canPreviewGraphtec(
  state: GraphtecPanelState,
  inspection: GraphtecInspectionResponse,
  disabled: boolean,
): boolean {
  return (
    !disabled &&
    state.preview.status !== "loading" &&
    state.save.status !== "saving" &&
    validateGraphtecForm(state.form, inspection) === null
  );
}

/**
 * Indica si puede guardarse la gráfica: solo cuando la previsualización
 * visible corresponde a la configuración actual.
 */
export function canSaveGraphtec(
  state: GraphtecPanelState,
  inspection: GraphtecInspectionResponse,
  disabled: boolean,
): boolean {
  return (
    !disabled &&
    state.save.status !== "saving" &&
    validateGraphtecForm(state.form, inspection) === null &&
    isGraphtecPreviewCurrent(state)
  );
}

/** Formatea segundos para la interfaz. */
export function formatSeconds(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "Not available";
  }
  return `${Number(value.toFixed(3))} s`;
}

/**
 * Resume las unidades originales y normalizadas, por ejemplo
 * `Resistance: Mohm, Gohm → Mohm`.
 */
export function graphtecUnitsSummary(
  inspection: GraphtecInspectionResponse,
): string[] {
  return Object.entries(inspection.original_units).map(([quantity, units]) => {
    const label = quantity.charAt(0).toUpperCase() + quantity.slice(1);
    const normalized = inspection.normalized_units[quantity];
    const original = units.join(", ");
    return normalized && units.some((unit) => unit !== normalized)
      ? `${label}: ${original} → ${normalized}`
      : `${label}: ${original}`;
  });
}
