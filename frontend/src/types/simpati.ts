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
