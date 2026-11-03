import {
  classifyZoomSelection,
  clampToPlot,
  defaultValueRange,
  type PlotArea,
  type SvgPoint,
  type ValueRange,
} from "./chartZoom";
import type {
  GraphtecChartSettings,
  GraphtecInspectionResponse,
  GraphtecSeriesId,
  GraphtecValueRange,
} from "../types/graphtec";

/** Longitud máxima admitida para el título. */
export const MAX_GRAPHTEC_TITLE_LENGTH = 200;

/** Título utilizado cuando el contenido no proporciona uno. */
export const GENERIC_GRAPHTEC_TITLE = "Graphtec chart";

/** Estado de los registros de medida; el resto son registros de resultado. */
export const GRAPHTEC_STATUS_TEST = "TEST";

/**
 * Margen horizontal (proporción del intervalo visible) que el backend añade
 * a cada lado del eje X para que los marcadores extremos se vean enteros. El
 * visor usa el mismo margen para que la imagen guardada coincida con él.
 */
export const GRAPHTEC_TIME_MARGIN_RATIO = 0.015;

/** Número mínimo de registros dentro de un intervalo ampliado. */
export const MIN_ZOOM_RECORDS = 2;

/** Orden fijo de las series. */
const SERIES_ORDER: GraphtecSeriesId[] = ["voltage", "current", "resistance"];

/** Valores editables de la configuración de la gráfica. */
export interface GraphtecChartForm {
  series: GraphtecSeriesId[];
  title: string;
  showLegend: boolean;
  showPhaseSeparators: boolean;
}

/**
 * Fracción visible del rango Y por defecto: 0 es la parte inferior y 1 la
 * superior. Se aplica a la vez a los dos ejes Y (tensión a la izquierda,
 * corriente o resistencia a la derecha), igual que el zoom de una gráfica
 * con doble eje.
 */
export interface GraphtecYZoom {
  low: number;
  high: number;
}

/**
 * Vista visible de la gráfica Graphtec.
 *
 * `timeStart` y `timeEnd` son tiempos transcurridos en segundos. `yZoom`
 * es `null` mientras se muestra el rango Y por defecto, calculado con todos
 * los valores de la adquisición: ampliar el eje X nunca reajusta el eje Y.
 */
export interface GraphtecViewport {
  timeStart: number;
  timeEnd: number;
  yZoom: GraphtecYZoom | null;
}

/** Estado del guardado. */
export interface GraphtecSaveState {
  status: "idle" | "saving" | "saved" | "error";
  message: string | null;
}

/** Estado completo del panel de gráficas Graphtec. */
export interface GraphtecPanelState {
  form: GraphtecChartForm;
  viewport: GraphtecViewport;
  save: GraphtecSaveState;
}

/** Acciones admitidas por {@link graphtecPanelReducer}. */
export type GraphtecPanelAction =
  | { type: "formChanged"; patch: Partial<GraphtecChartForm> }
  | { type: "seriesToggled"; seriesId: GraphtecSeriesId; selected: boolean }
  | { type: "viewportChanged"; viewport: GraphtecViewport }
  | { type: "zoomReset"; inspection: GraphtecInspectionResponse }
  | { type: "reset"; inspection: GraphtecInspectionResponse }
  | { type: "saveStarted" }
  | { type: "saveSucceeded"; chartName: string }
  | { type: "saveFailed"; message: string };

/**
 * Configuración inicial: series por defecto (tensión y corriente o
 * resistencia), leyenda y separadores visibles y título obtenido del
 * contenido.
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
  };
}

/** Intervalo temporal completo de la adquisición. */
export function graphtecTimeBounds(
  inspection: GraphtecInspectionResponse,
): { start: number; end: number } {
  const times = inspection.chart_data.elapsed_time_seconds;
  const start = inspection.elapsed_time_start ?? times[0] ?? 0;
  const end = inspection.elapsed_time_end ?? times[times.length - 1] ?? start;
  return { start, end: end > start ? end : start + 1 };
}

/** Vista completa: toda la adquisición y rango Y por defecto. */
export function fullGraphtecViewport(
  inspection: GraphtecInspectionResponse,
): GraphtecViewport {
  const { start, end } = graphtecTimeBounds(inspection);
  return { timeStart: start, timeEnd: end, yZoom: null };
}

/** Indica si la vista coincide con la vista completa. */
export function isFullGraphtecViewport(
  viewport: GraphtecViewport,
  inspection: GraphtecInspectionResponse,
): boolean {
  const full = fullGraphtecViewport(inspection);
  return (
    viewport.yZoom === null &&
    viewport.timeStart <= full.timeStart &&
    viewport.timeEnd >= full.timeEnd
  );
}

/** Estado inicial del panel para un análisis concreto. */
export function initialGraphtecPanelState(
  inspection: GraphtecInspectionResponse,
): GraphtecPanelState {
  return {
    form: defaultGraphtecForm(inspection),
    viewport: fullGraphtecViewport(inspection),
    save: { status: "idle", message: null },
  };
}

/**
 * Valida la configuración.
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
  return null;
}

/** Valores de una serie alineados con `chart_data.elapsed_time_seconds`. */
export function graphtecSeriesValues(
  inspection: GraphtecInspectionResponse,
  seriesId: GraphtecSeriesId,
): number[] {
  return seriesId === "voltage"
    ? inspection.chart_data.voltage_kv
    : inspection.chart_data.measurement;
}

/**
 * Rango Y por defecto de una serie: todos sus valores en la adquisición
 * completa (incluidos umbrales limitados y registros de resultado) con un
 * margen del 8 %.
 */
export function defaultGraphtecSeriesRange(
  inspection: GraphtecInspectionResponse,
  seriesId: GraphtecSeriesId,
): ValueRange {
  return defaultValueRange([
    { values: graphtecSeriesValues(inspection, seriesId) },
  ]);
}

/** Aplica la fracción visible a un rango por defecto. */
export function zoomedRange(
  range: ValueRange,
  yZoom: GraphtecYZoom | null,
): ValueRange {
  if (yZoom === null) {
    return range;
  }
  const span = range.maximum - range.minimum;
  return {
    minimum: range.minimum + yZoom.low * span,
    maximum: range.minimum + yZoom.high * span,
  };
}

/** Rango Y visible de cada serie seleccionada. */
export function visibleGraphtecRanges(
  state: GraphtecPanelState,
  inspection: GraphtecInspectionResponse,
): Partial<Record<GraphtecSeriesId, ValueRange>> {
  const result: Partial<Record<GraphtecSeriesId, ValueRange>> = {};
  for (const seriesId of state.form.series) {
    result[seriesId] = zoomedRange(
      defaultGraphtecSeriesRange(inspection, seriesId),
      state.viewport.yZoom,
    );
  }
  return result;
}

/**
 * Dominio del eje X dibujado: el intervalo visible más el mismo margen que
 * aplica el backend al guardar.
 */
export function graphtecTimeDomain(
  viewport: GraphtecViewport,
): { minimum: number; maximum: number } {
  const span = Math.max(1e-9, viewport.timeEnd - viewport.timeStart);
  return {
    minimum: viewport.timeStart - span * GRAPHTEC_TIME_MARGIN_RATIO,
    maximum: viewport.timeEnd + span * GRAPHTEC_TIME_MARGIN_RATIO,
  };
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, value));
}

/** Tiempo correspondiente a una coordenada X del SVG. */
export function timeAtSvgX(
  svgX: number,
  viewport: GraphtecViewport,
  plot: PlotArea,
): number {
  const domain = graphtecTimeDomain(viewport);
  const ratio = clamp((svgX - plot.left) / plot.width, 0, 1);
  return domain.minimum + ratio * (domain.maximum - domain.minimum);
}

/** Número de registros con tiempo dentro de `[start, end]`. */
export function recordsInTimeRange(
  inspection: GraphtecInspectionResponse,
  start: number,
  end: number,
): number {
  let count = 0;
  for (const time of inspection.chart_data.elapsed_time_seconds) {
    if (time >= start && time <= end) {
      count += 1;
    }
  }
  return count;
}

/**
 * Calcula la vista resultante de una selección por arrastre.
 *
 * La forma de la selección decide los ejes, igual que en SIMPATI: horizontal
 * para el tiempo, vertical para los valores (ambos ejes Y a la vez) y
 * diagonal para ambos. El eje que la selección no ajusta conserva su rango.
 *
 * @returns La nueva vista o `null` si la selección no produce zoom (clic,
 *   menos de {@link MIN_ZOOM_RECORDS} registros o rango degenerado).
 */
export function applyGraphtecZoom(
  viewport: GraphtecViewport,
  start: SvgPoint,
  end: SvgPoint,
  plot: PlotArea,
  inspection: GraphtecInspectionResponse,
): GraphtecViewport | null {
  const from = clampToPlot(start, plot);
  const to = clampToPlot(end, plot);
  const mode = classifyZoomSelection(from, to);
  if (mode === null) {
    return null;
  }

  let { timeStart, timeEnd, yZoom } = viewport;

  if (mode === "x" || mode === "xy") {
    const bounds = graphtecTimeBounds(inspection);
    const first = clamp(
      timeAtSvgX(Math.min(from.x, to.x), viewport, plot),
      bounds.start,
      bounds.end,
    );
    const last = clamp(
      timeAtSvgX(Math.max(from.x, to.x), viewport, plot),
      bounds.start,
      bounds.end,
    );
    if (
      last > first &&
      recordsInTimeRange(inspection, first, last) >= MIN_ZOOM_RECORDS
    ) {
      timeStart = first;
      timeEnd = last;
    } else if (mode === "x") {
      return null;
    }
  }

  if (mode === "y" || mode === "xy") {
    const current = viewport.yZoom ?? { low: 0, high: 1 };
    const span = current.high - current.low;
    const topRatio = 1 - (Math.min(from.y, to.y) - plot.top) / plot.height;
    const bottomRatio = 1 - (Math.max(from.y, to.y) - plot.top) / plot.height;
    const high = current.low + clamp(topRatio, 0, 1) * span;
    const low = current.low + clamp(bottomRatio, 0, 1) * span;
    if (high - low > 1e-9) {
      yZoom = { low, high };
    } else if (mode === "y") {
      return null;
    }
  }

  if (
    timeStart === viewport.timeStart &&
    timeEnd === viewport.timeEnd &&
    yZoom === viewport.yZoom
  ) {
    return null;
  }
  return { timeStart, timeEnd, yZoom };
}

/**
 * Convierte la configuración y la vista visible en la petición enviada al
 * backend: mismo intervalo temporal y mismo rango Y de cada serie, de modo
 * que la imagen guardada reproduce la vista en pantalla.
 */
export function graphtecViewToSettings(
  state: GraphtecPanelState,
  inspection: GraphtecInspectionResponse,
): GraphtecChartSettings {
  const full = isFullGraphtecViewport(
    { ...state.viewport, yZoom: null },
    inspection,
  );
  const ranges = visibleGraphtecRanges(state, inspection);
  const valueRanges: Partial<Record<GraphtecSeriesId, GraphtecValueRange>> = {};
  for (const seriesId of state.form.series) {
    const range = ranges[seriesId];
    if (range) {
      valueRanges[seriesId] = { minimum: range.minimum, maximum: range.maximum };
    }
  }
  return {
    series: [...state.form.series],
    title: state.form.title.trim(),
    show_legend: state.form.showLegend,
    show_phase_separators: state.form.showPhaseSeparators,
    time_min: full ? null : state.viewport.timeStart,
    time_max: full ? null : state.viewport.timeEnd,
    value_ranges: valueRanges,
  };
}

/** Actualiza el estado del panel. */
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
      return graphtecPanelReducer(state, {
        type: "formChanged",
        patch: { series: SERIES_ORDER.filter((id) => selected.has(id)) },
      });
    }
    case "viewportChanged":
      return {
        ...state,
        viewport: action.viewport,
        save: { status: "idle", message: null },
      };
    case "zoomReset":
      return {
        ...state,
        viewport: fullGraphtecViewport(action.inspection),
      };
    case "reset":
      return initialGraphtecPanelState(action.inspection);
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

/** Indica si puede guardarse la vista actual de la gráfica. */
export function canSaveGraphtec(
  state: GraphtecPanelState,
  inspection: GraphtecInspectionResponse,
  disabled: boolean,
): boolean {
  return (
    !disabled &&
    state.save.status !== "saving" &&
    inspection.chart_data.elapsed_time_seconds.length > 0 &&
    validateGraphtecForm(state.form, inspection) === null
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
 * Marcas "redondas" (1, 2 o 5 × 10^n) dentro de un rango, con sus
 * decimales. Las etiquetas siempre coinciden con la posición real de la
 * marca, también al ampliar.
 *
 * @param range Rango visible.
 * @param target Número aproximado de intervalos deseado.
 */
export function niceTicks(
  range: ValueRange,
  target: number,
): { values: number[]; decimals: number } {
  const span = range.maximum - range.minimum;
  if (!Number.isFinite(span) || span <= 0) {
    return { values: [range.minimum], decimals: 0 };
  }
  const rough = span / Math.max(1, target);
  const magnitude = Math.pow(10, Math.floor(Math.log10(rough)));
  // Paso redondo (1, 2 o 5 × 10^n) más cercano al paso aproximado.
  const step = [1, 2, 5, 10]
    .map((factor) => factor * magnitude)
    .reduce((best, candidate) =>
      Math.abs(candidate - rough) < Math.abs(best - rough) ? candidate : best,
    );
  const first = Math.ceil(range.minimum / step - 1e-9);
  const last = Math.floor(range.maximum / step + 1e-9);
  const decimals = clamp(Math.ceil(-Math.log10(step) - 1e-9), 0, 8);
  const values: number[] = [];
  for (let index = first; index <= last; index += 1) {
    values.push(Number((index * step).toFixed(decimals)));
  }
  return { values, decimals };
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
