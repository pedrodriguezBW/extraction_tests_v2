import type { ApiError } from "./common";
import type { RenderedAsset, RenderedAssetWarning } from "./renderedAssets";

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

  /**
   * Papel térmico reconocido (`chamber_temperature`, `basket_setpoint`...)
   * o `null` si ningún perfil reconoce el canal.
   */
  role: string | null;

  /** Unidad leída de la fila de unidades, o cadena vacía. */
  unit: string;

  /** Valores del canal alineados con las marcas temporales de la vista previa. */
  values: Array<number | null>;
}

/**
 * Estado del análisis aislado de una adquisición `.xNN`.
 *
 * - `ready`: tiene canales térmicos representables.
 * - `no_thermal_channels`: es válida pero ningún perfil reconoce canales
 *   térmicos.
 * - `incompatible`: el contenido no tiene una estructura SIMPATI válida.
 * - `error`: el archivo no se ha podido leer.
 */
export type SimpatiAcquisitionStatus =
  | "ready"
  | "no_thermal_channels"
  | "incompatible"
  | "error";

/**
 * Canal detectado en una adquisición, reconocido o no.
 */
export interface SimpatiChannelResult {
  /** Nombre de la columna (nombre y unidad). */
  column: string;

  /** Nombre leído de la cabecera. */
  name: string;

  /** Unidad leída de la fila de unidades. */
  unit: string;

  /** Tipo según el prefijo: `actual`, `setpoint`, `counter`, `digital`... */
  kind: string;

  /** Papel térmico reconocido o `null`. */
  role: string | null;

  /** Etiqueta del papel térmico o `null`. */
  label: string | null;

  /** Indica si el canal se puede representar como canal térmico. */
  thermal: boolean;

  /** Indica si el canal contiene algún valor numérico. */
  has_data: boolean;
}

/**
 * Resultado del análisis aislado de una adquisición SIMPATI `.xNN`.
 */
export interface SimpatiAcquisitionSummary {
  /** Número de la extensión `.xNN`. */
  index: number;

  /** Identificador visible, por ejemplo `x04`. */
  label: string;

  /** Nombre del archivo. */
  file_name: string;

  /** Ruta relativa a la carpeta raíz del ensayo. */
  relative_path: string;

  /** Tamaño en bytes. */
  size: number;

  /** Estado del análisis. */
  status: SimpatiAcquisitionStatus;

  /** Codificación detectada por la estructura del contenido. */
  encoding: string | null;

  /** Número de registros válidos. */
  records_count: number;

  /** Primera marca temporal. */
  acquisition_start: string | null;

  /** Última marca temporal. */
  acquisition_end: string | null;

  /** Equipo indicado en el preámbulo, cuando existe. */
  device: string | null;

  /** Programa indicado en el preámbulo, cuando existe. */
  program: string | null;

  /** Número de canales detectados. */
  channels_count: number;

  /** Canales detectados, en el orden del archivo. */
  channels: SimpatiChannelResult[];

  /** Etiquetas de los canales térmicos representables. */
  thermal_channels: string[];

  /** Registros rechazados por no coincidir con la cabecera. */
  rejected_rows: number;

  /** Ejemplos de registros rechazados. */
  rejected_rows_examples: string[];

  /** Error del análisis, cuando el archivo no se ha podido procesar. */
  error: ApiError | null;
}

/**
 * Petición del análisis SIMPATI.
 */
export interface SimpatiInspectionRequest {
  /** Ruta de la carpeta raíz del ensayo. */
  test_root: string;

  /**
   * Adquisición que se previsualiza. Sin ella se usa la primera con canales
   * representables.
   */
  relative_path?: string;
}

/**
 * Petición utilizada para guardar una gráfica SIMPATI.
 */
export interface SimpatiChartSaveRequest {
  /** Ruta de la carpeta raíz del ensayo. */
  test_root: string;

  /** Adquisición de origen; determina el nombre `chart_simpati_xNN_MM`. */
  relative_path: string;

  /** Imagen PNG codificada como una URL de datos en Base64. */
  image_base64: string;
}

/**
 * Respuesta del backend después de intentar guardar una gráfica SIMPATI.
 *
 * La gráfica guardada pasa a ser un recurso genérico de
 * `04_Report/_RenderedAssets`; la respuesta incluye el inventario
 * actualizado para añadirla a la selección del informe.
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

  /** Ruta relativa del recurso guardado, cuando la operación tiene éxito. */
  relative_path: string | null;

  /** Adquisición de origen de la gráfica. */
  source_relative_path: string | null;

  /** Índice `xNN` de la adquisición de origen. */
  acquisition_index: number | null;

  /** Indica si la carpeta `_RenderedAssets` existe. */
  directory_found: boolean;

  /** Número de imágenes del inventario después de la operación. */
  assets_count: number;

  /** Inventario actualizado de imágenes seleccionables. */
  assets: RenderedAsset[];

  /** Archivos del inventario que no son imágenes seleccionables. */
  warnings: RenderedAssetWarning[];

  /** Errores devueltos durante el guardado. */
  errors: ApiError[];
}

/**
 * Resultado del análisis de todas las adquisiciones SIMPATI del ensayo y de
 * la vista previa de la adquisición seleccionada.
 */
export interface SimpatiInspectionResponse {
  /** Indica si el análisis se ha completado correctamente. */
  success: boolean;

  /** Ruta de la carpeta raíz del ensayo inspeccionado. */
  test_root: string;

  /** Indica si existe alguna adquisición SIMPATI. */
  available: boolean;

  /** Todas las adquisiciones `.xNN`, en orden numérico. */
  acquisitions: SimpatiAcquisitionSummary[];

  /** Adquisiciones encontradas. */
  found_count: number;

  /** Adquisiciones procesadas (estructura válida). */
  processed_count: number;

  /** Adquisiciones con canales térmicos representables. */
  ready_count: number;

  /** Adquisiciones válidas sin canales térmicos representables. */
  without_thermal_count: number;

  /** Adquisiciones incompatibles o ilegibles. */
  incompatible_count: number;

  /** Adquisición previsualizada. */
  selected_relative_path: string | null;

  /** Índice `xNN` de la adquisición previsualizada. */
  selected_index: number | null;

  /** Estado de la adquisición previsualizada. */
  selected_status: SimpatiAcquisitionStatus | null;

  /** Nombre del archivo de adquisición previsualizado. */
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
