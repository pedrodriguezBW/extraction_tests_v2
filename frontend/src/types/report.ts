import type { ApiError } from "./common";

/**
 * Petición de generación del informe PowerPoint.
 */
export interface ReportGenerationRequest {
  /** Ruta de la carpeta raíz del ensayo. */
  test_root: string;

  /**
   * Rutas relativas, en orden, de las imágenes de
   * `04_Report/_RenderedAssets` que se insertarán en Test Results. El orden
   * se conserva en el PowerPoint. Una lista vacía genera el informe sin
   * imágenes de resultados; el backend nunca la sustituye por el inventario.
   */
  selected_rendered_assets: string[];
}

/**
 * Resultado devuelto por el backend después de intentar generar el informe
 * PowerPoint de un ensayo.
 */
export interface ReportGenerationResponse {
  /** Indica si el informe se ha generado correctamente. */
  success: boolean;

  /** Ruta de la carpeta raíz del ensayo procesado. */
  test_root: string;

  /** Ruta completa del informe generado, cuando la operación tiene éxito. */
  report_path: string | null;

  /** Nombre del archivo generado, cuando la operación tiene éxito. */
  report_name: string | null;

  /** Número de imágenes insertadas en Test Results. */
  rendered_assets_count: number;

  /** Rutas relativas de las imágenes insertadas, en el orden de inserción. */
  rendered_assets: string[];

  /** Errores devueltos por el backend durante la generación. */
  errors: ApiError[];
}
