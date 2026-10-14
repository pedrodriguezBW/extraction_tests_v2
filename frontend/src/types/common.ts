/**
 * Error estructurado devuelto por el backend.
 */
export interface ApiError {
  /** Código estable utilizado para identificar el tipo de error. */
  code: string;

  /** Mensaje descriptivo que puede mostrarse en la interfaz. */
  message: string;

  /** Tipo de excepción original, cuando el backend lo proporciona. */
  exception_type: string | null;
}