import type { ApiError } from "./common";
import type { RenderedAsset, RenderedAssetWarning } from "./renderedAssets";

/**
 * Identificador de una serie Graphtec. `current` solo existe en DCW y
 * `resistance` solo en IR.
 */
export type GraphtecSeriesId = "voltage" | "current" | "resistance";

/** Petición con el archivo Graphtec seleccionado en la inspección. */
export interface GraphtecFileRequest {
  /** Ruta de la carpeta raíz del ensayo. */
  test_root: string;

  /** Ruta relativa a la raíz del ensayo dentro de `03_Data/02_Graphtec`. */
  relative_path: string;
}

/**
 * Configuración de una gráfica Graphtec. El eje X siempre es
 * `elapsed_time_seconds`.
 */
export interface GraphtecChartSettings {
  /** Series visibles. */
  series: GraphtecSeriesId[];

  /** Título de la gráfica. Vacío utiliza el título por defecto. */
  title: string;

  /** Muestra la leyenda. */
  show_legend: boolean;

  /** Muestra los separadores de fase. */
  show_phase_separators: boolean;

  /** Inicio del intervalo en segundos o `null` para el inicio completo. */
  time_min: number | null;

  /** Fin del intervalo en segundos o `null` para el final completo. */
  time_max: number | null;
}

/** Petición de previsualización o guardado. */
export interface GraphtecChartRequest extends GraphtecFileRequest {
  /** Configuración de la gráfica. */
  chart: GraphtecChartSettings;
}

/** Registro normalizado de Graphtec. */
export interface GraphtecRecord {
  line_number: number;
  channel: number;
  test_type: string;
  status: string;
  raw_voltage: string;
  voltage_value: number;
  voltage_unit: string;
  raw_measurement: string;
  /** Operador de límite, por ejemplo `>`, o `null` si el valor es exacto. */
  measurement_operator: string | null;
  measurement_value: number;
  measurement_unit: string;
  measurement_quantity: string;
  normalized_value: number;
  normalized_unit: string;
  phase: string;
  phase_time_seconds: number;
  elapsed_time_seconds: number;
}

/** Serie disponible para la gráfica. */
export interface GraphtecSeries {
  id: GraphtecSeriesId;
  label: string;
  unit: string;
  /** Eje Y utilizado cuando se representan dos magnitudes. */
  axis: "left" | "right";
  default_selected?: boolean;
}

/** Tramo consecutivo con la misma letra de fase. */
export interface GraphtecPhaseSegment {
  phase: string;
  start_elapsed_seconds: number;
  end_elapsed_seconds: number;
  first_line: number;
  last_line: number;
  records_count: number;
}

/** Valores normalizados alineados por índice. */
export interface GraphtecChartData {
  elapsed_time_seconds: number[];
  voltage_kv: number[];
  measurement: number[];
  measurement_operator: Array<string | null>;
  status: string[];
  phase: string[];
  truncated: boolean;
}

/** Resultado del análisis de un archivo Graphtec. */
export interface GraphtecInspectionResponse {
  success: boolean;
  test_root: string;
  source: "graphtec";
  /** Identificador del formato detectado a partir del contenido. */
  format: string | null;
  format_label: string | null;
  /** Nombre del archivo, solo para mostrar y trazar. No se interpreta. */
  file_name: string | null;
  relative_path: string | null;
  records_count: number;
  channels: number[];
  test_types: string[];
  statuses: string[];
  phases: string[];
  phase_segments: GraphtecPhaseSegment[];
  final_result: string | null;
  available_series: GraphtecSeries[];
  original_units: Record<string, string[]>;
  normalized_units: Record<string, string>;
  elapsed_time_start: number | null;
  elapsed_time_end: number | null;
  duration_seconds: number | null;
  limited_values_count: number;
  default_title: string | null;
  preview_records: GraphtecRecord[];
  preview_truncated: boolean;
  chart_data: GraphtecChartData;
  warnings: string[];
  errors: ApiError[];
}

/** Eje dibujado en la gráfica. */
export interface GraphtecChartAxis {
  position: "left" | "right";
  label: string;
  series: GraphtecSeriesId[];
}

/** Previsualización generada por el backend. No se guarda nada. */
export interface GraphtecChartPreviewResponse {
  success: boolean;
  test_root: string;
  relative_path: string | null;
  /** Imagen PNG como URL de datos. */
  image_base64: string | null;
  width: number;
  height: number;
  title: string | null;
  x_axis_label: string;
  series: GraphtecSeries[];
  axes: GraphtecChartAxis[];
  time_start: number | null;
  time_end: number | null;
  full_range: boolean;
  records_plotted: number;
  limited_points: number;
  result_points: number;
  phase_markers: Array<{ phase: string; elapsed_time_seconds: number }>;
  notes: string[];
  errors: ApiError[];
}

/**
 * Resultado del guardado de una gráfica Graphtec.
 *
 * La gráfica guardada pasa a ser un recurso genérico de
 * `04_Report/_RenderedAssets`; la respuesta incluye el inventario
 * actualizado para añadirla a la selección del informe.
 */
export interface GraphtecChartSaveResponse {
  success: boolean;
  test_root: string;
  chart_name: string | null;
  chart_path: string | null;
  relative_path: string | null;
  metadata_name: string | null;
  directory_found: boolean;
  assets_count: number;
  assets: RenderedAsset[];
  warnings: RenderedAssetWarning[];
  errors: ApiError[];
}
