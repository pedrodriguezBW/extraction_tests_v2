import type { ApiError } from "./common";

/**
 * Canal disponible en la vista previa de una adquisición SIMPATI.
 */
export interface SimpatiPreviewChannel {
  /** Identificador estable del canal. */
  id: string;

  /** Etiqueta visible del canal. */
  label: string;

  /** Nombre de la columna de origen en la adquisición. */
  source_column: string;

  /** Indica si el canal pertenece al grupo térmico. */
  thermal: boolean;

  /** Valores del canal alineados con las marcas temporales de la vista previa. */
  values: Array<number | null>;
}

/**
 * Petición utilizada para guardar una gráfica SIMPATI.
 */
export interface SimpatiChartSaveRequest {
  /** Ruta de la carpeta raíz del ensayo. */
  test_root: string;

  /** Imagen PNG codificada como una URL de datos en Base64. */
  image_base64: string;
}

/**
 * Petición utilizada para eliminar una gráfica SIMPATI guardada.
 */
export interface SimpatiChartDeleteRequest {
  /** Ruta de la carpeta raíz del ensayo. */
  test_root: string;

  /** Nombre del archivo de la gráfica que se debe eliminar. */
  chart_name: string;
}

/**
 * Información de una gráfica SIMPATI almacenada para el ensayo.
 */
export interface SimpatiSavedChart {
  /** Nombre del archivo de la gráfica. */
  chart_name: string;

  /** Ruta completa del archivo guardado. */
  chart_path: string;

  /** Tamaño del archivo en bytes. */
  size_bytes: number;
}

/**
 * Respuesta del backend al consultar las gráficas SIMPATI guardadas.
 */
export interface SimpatiChartListResponse {
  /** Indica si la consulta se ha completado correctamente. */
  success: boolean;

  /** Ruta de la carpeta raíz del ensayo consultado. */
  test_root: string;

  /** Número total de gráficas guardadas. */
  charts_count: number;

  /** Gráficas guardadas en el orden devuelto por el backend. */
  charts: SimpatiSavedChart[];

  /** Errores devueltos durante la consulta. */
  errors: ApiError[];
}

/**
 * Respuesta del backend después de intentar guardar una gráfica SIMPATI.
 */
export interface SimpatiChartSaveResponse {
  /** Indica si la gráfica se ha guardado correctamente. */
  success: boolean;

  /** Ruta de la carpeta raíz del ensayo procesado. */
  test_root: string;

  /** Ruta completa de la gráfica guardada, cuando la operación tiene éxito. */
  chart_path: string | null;

  /** Nombre del archivo guardado, cuando la operación tiene éxito. */
  chart_name: string | null;

  /** Número total de gráficas después de la operación. */
  charts_count: number;

  /** Lista actualizada de gráficas guardadas. */
  charts: SimpatiSavedChart[];

  /** Errores devueltos durante el guardado. */
  errors: ApiError[];
}

/**
 * Respuesta del backend después de intentar eliminar una gráfica SIMPATI.
 */
export interface SimpatiChartDeleteResponse {
  /** Indica si la gráfica se ha eliminado correctamente. */
  success: boolean;

  /** Ruta de la carpeta raíz del ensayo procesado. */
  test_root: string;

  /** Nombre de la gráfica eliminada, cuando la operación tiene éxito. */
  deleted_chart_name: string | null;

  /** Número total de gráficas después de la operación. */
  charts_count: number;

  /** Lista actualizada de gráficas guardadas. */
  charts: SimpatiSavedChart[];

  /** Errores devueltos durante la eliminación. */
  errors: ApiError[];
}

/**
 * Resultado del análisis de una adquisición SIMPATI y de la preparación de su
 * vista previa.
 */
export interface SimpatiInspectionResponse {
  /** Indica si el análisis se ha completado correctamente. */
  success: boolean;

  /** Ruta de la carpeta raíz del ensayo inspeccionado. */
  test_root: string;

  /** Indica si existe una adquisición SIMPATI disponible. */
  available: boolean;

  /** Nombre del archivo de adquisición, cuando está disponible. */
  file_name: string | null;

  /** Ruta completa del archivo de adquisición, cuando está disponible. */
  file_path: string | null;

  /** Codificación detectada para el archivo. */
  encoding: string | null;

  /** Número de registros procesados. */
  records_count: number;

  /** Marca temporal inicial de la adquisición. */
  acquisition_start: string | null;

  /** Marca temporal final de la adquisición. */
  acquisition_end: string | null;

  /** Nombres de todos los canales detectados. */
  channels: string[];

  /** Marcas temporales utilizadas por la vista previa. */
  preview_timestamps: string[];

  /** Canales térmicos disponibles en la vista previa. */
  thermal_channels: SimpatiPreviewChannel[];

  /** Canales avanzados disponibles en la vista previa. */
  advanced_channels: SimpatiPreviewChannel[];

  /** Errores devueltos durante el análisis. */
  errors: ApiError[];
}
