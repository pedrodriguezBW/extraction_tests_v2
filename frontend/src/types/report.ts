import type { ApiError } from "./common";

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

  /** Errores devueltos por el backend durante la generación. */
  errors: ApiError[];
}
