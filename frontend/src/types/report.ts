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

  /**
   * Fotografías de las evidencias `initial` para 2. Test Assembly
   * (`02_Evidences/<carpeta>/<savedName>`). Máximo 4.
   */
  selected_assembly_photos: string[];

  /**
   * Fotografías del resto de evidencias para 4. Test Results. Sin límite.
   * El backend siempre usa el orden automático (secuencia de la evidencia y
   * orden de sus fotografías).
   */
  selected_result_photos: string[];
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

  /** Número de fotografías insertadas en Test Assembly. */
  assembly_photos_count: number;

  /** Fotografías insertadas en Test Assembly, en orden. */
  assembly_photos: string[];

  /** Número de fotografías de evidencia insertadas en Test Results. */
  result_photos_count: number;

  /** Fotografías de evidencia insertadas en Test Results, en orden. */
  result_photos: string[];

  /** Errores devueltos por el backend durante la generación. */
  errors: ApiError[];
}
