/**
 * Respuesta del endpoint utilizado para comprobar la disponibilidad del
 * backend.
 */
export interface HealthResponse {
  /** Estado general del servicio. */
  status: string;

  /** Identificador de la aplicación backend. */
  application: string;

  /** Versión publicada por el backend. */
  version: string;
}

/**
 * Petición común para las operaciones que necesitan la carpeta raíz del
 * ensayo.
 */
export interface ProjectInspectionRequest {
  /** Ruta de la carpeta individual del ensayo. */
  test_root: string;
}

/**
 * Resultado básico de la inspección de un archivo.
 */
export interface FileInspectionResult {
  /** Indica si el archivo existe. */
  found: boolean;

  /** Nombre del archivo, cuando está disponible. */
  name: string | null;

  /** Ruta del archivo, cuando está disponible. */
  path: string | null;
}

/**
 * Resultado básico de la inspección de una carpeta.
 */
export interface DirectoryInspectionResult {
  /** Indica si la carpeta existe. */
  found: boolean;

  /** Ruta esperada o encontrada de la carpeta. */
  path: string;

  /** Número de archivos detectados, cuando se ha calculado. */
  file_count: number | null;
}

/**
 * Resultado de la localización y validación de `test_metadata.json`.
 */
export interface MetadataInspectionResult extends FileInspectionResult {
  /** Indica si el contenido de los metadatos es válido. */
  valid: boolean;

  /** Mensaje principal de error, cuando existe. */
  error: string | null;

  /** Errores de validación detectados. */
  errors: string[];

  /** Nombre del ensayo extraído de los metadatos. */
  test_name: string | null;

  /** Versión del esquema declarada en los metadatos. */
  schema_version: string | null;

  /** Número de muestras declaradas. */
  samples_count: number;

  /** Número de equipos declarados. */
  equipment_count: number;

  /** Número de puntos del perfil climático. */
  climatic_profile_points_count: number;

  /** Número de puntos del perfil del controlador DUT. */
  dut_profile_points_count: number;

  /** Número de eventos del ensayo. */
  test_events_count: number;

  /** Número de imágenes de montaje referenciadas. */
  setup_images_count: number;

  /** Número de imágenes de montaje encontradas. */
  setup_images_found_count: number;
}

/**
 * Resultado de la resolución de una fotografía declarada en una evidencia.
 */
export interface EvidencePhotoResult {
  /** Identificador de la fotografía, cuando está declarado. */
  id: string | null;

  /** Nombre original del archivo, cuando está disponible. */
  original_name: string | null;

  /** Nombre con el que la fotografía se guarda en la evidencia. */
  saved_name: string;

  /** Fecha y hora de captura declaradas. */
  capture_date: string | null;

  /** Tipo MIME declarado para la imagen. */
  mime: string | null;

  /** Tamaño declarado del archivo en bytes. */
  size: number | null;

  /** Ruta resuelta de la fotografía. */
  path: string;

  /** Indica si el archivo físico existe. */
  found: boolean;
}

/**
 * Evidencia válida detectada durante la inspección del ensayo.
 */
export interface EvidenceResult {
  /** Identificador de la evidencia, cuando está declarado. */
  id: string | null;

  /** Tipo de evidencia. */
  type: string | null;

  /** Título visible de la evidencia. */
  title: string | null;

  /** Tipo de referencia temporal o funcional. */
  reference_type: string | null;

  /** Valor asociado a la referencia. */
  reference_value: string | null;

  /** Notas asociadas a la evidencia. */
  notes: string | null;

  /** Posición cronológica de la evidencia. */
  sequence: number | null;

  /** Versión declarada del descriptor. */
  schema_version: number | null;

  /** Nombre real de la carpeta inspeccionada. */
  folder: string;

  /** Nombre de carpeta declarado en el descriptor. */
  declared_folder: string | null;

  /** Ruta de la carpeta de la evidencia. */
  directory: string;

  /** Ruta del archivo `evidence.json`. */
  descriptor_path: string;

  /** Fotografías declaradas por la evidencia. */
  photos: EvidencePhotoResult[];

  /** Número de fotografías declaradas. */
  photos_count: number;

  /** Número de fotografías encontradas. */
  photos_found_count: number;
}

/**
 * Descriptor de evidencia que no ha superado la validación.
 */
export interface InvalidEvidenceResult {
  /** Nombre de la carpeta que contiene el descriptor. */
  folder: string;

  /** Ruta del descriptor no válido. */
  descriptor_path: string;

  /** Errores detectados durante la validación. */
  errors: string[];
}

/**
 * Fotografía declarada por una evidencia cuyo archivo no se ha encontrado.
 */
export interface MissingEvidencePhotoResult {
  /** Carpeta de la evidencia. */
  evidence_folder: string;

  /** Título de la evidencia, cuando está disponible. */
  evidence_title: string | null;

  /** Nombre esperado de la fotografía. */
  saved_name: string;

  /** Ruta esperada del archivo. */
  path: string;
}

/**
 * Resultado agregado de la inspección de las evidencias del ensayo.
 */
export interface EvidencesInspectionResult {
  /** Estado de la carpeta `02_Evidences`. */
  directory: DirectoryInspectionResult;

  /** Número de evidencias válidas detectadas. */
  evidences_count: number;

  /** Número total de fotografías declaradas. */
  photos_count: number;

  /** Número total de fotografías encontradas. */
  photos_found_count: number;

  /** Evidencias válidas ordenadas para su uso posterior. */
  evidences: EvidenceResult[];

  /** Evidencias cuyos descriptores no son válidos. */
  invalid_evidences: InvalidEvidenceResult[];

  /** Fotografías declaradas que no se han encontrado. */
  missing_photos: MissingEvidencePhotoResult[];
}

/**
 * Identificador de una fuente de adquisición reconocida por la aplicación.
 *
 * SIMPATI, Graphtec y CANoe son orígenes de datos. CSV es un formato de
 * archivo y no se trata como una fuente independiente.
 */
export type DataSourceKey = "simpati" | "graphtec" | "canoe";

/**
 * Archivo regular detectado directamente dentro de la carpeta de una fuente.
 *
 * La inspección no lee su contenido.
 */
export interface DataSourceFileResult {
  /** Nombre del archivo. */
  name: string;

  /**
   * Ruta relativa a la carpeta raíz del ensayo con separadores `/`, por
   * ejemplo `03_Data/01_SIMPATI/acquisition.csv`.
   */
  relative_path: string;

  /** Extensión en minúsculas incluyendo el punto, o cadena vacía. */
  extension: string;

  /** Tamaño del archivo en bytes. */
  size: number;
}

/**
 * Resultado de la inspección de una fuente de adquisición concreta.
 */
export interface DataSourceInspectionResult {
  /** Identificador estable de la fuente. */
  key: DataSourceKey;

  /** Etiqueta visible de la fuente. */
  label: string;

  /** Indica si la carpeta de la fuente existe. */
  found: boolean;

  /** Indica si la fuente contiene datos disponibles. */
  available: boolean;

  /** Ruta inspeccionada. */
  path: string;

  /** Número de archivos detectados. */
  file_count: number;

  /** Archivos detectados, ordenados sin distinguir mayúsculas. */
  files: DataSourceFileResult[];
}

/**
 * Resultado agregado de la inspección de `03_Data` y sus fuentes.
 */
export interface DataSourcesInspectionResult {
  /** Estado de la carpeta `03_Data`. */
  directory: DirectoryInspectionResult;

  /** Resultado de la inspección de `03_Data/01_SIMPATI`. */
  simpati: DataSourceInspectionResult;

  /** Resultado de la inspección de `03_Data/02_Graphtec`. */
  graphtec: DataSourceInspectionResult;

  /** Resultado de la inspección de `03_Data/03_CANoe`. */
  canoe: DataSourceInspectionResult;

  /** Archivo SIMPATI que utiliza el análisis SIMPATI, cuando existe. */
  simpati_file: FileInspectionResult;
}

/**
 * Respuesta completa de la inspección de una carpeta de ensayo.
 */
export interface ProjectInspectionResponse {
  /** Indica si el proyecto permite continuar con la generación. */
  valid: boolean;

  /** Ruta de la carpeta raíz inspeccionada. */
  test_root: string;

  /** Estado de la carpeta `01_Inputs`. */
  inputs_directory: DirectoryInspectionResult;

  /** Resultado de la inspección de evidencias. */
  evidences: EvidencesInspectionResult;

  /** Resultado de la inspección de fuentes de adquisición. */
  data: DataSourcesInspectionResult;

  /** Estado de la carpeta `04_Report`. */
  report_directory: DirectoryInspectionResult;

  /** Resultado de la validación de `test_metadata.json`. */
  metadata: MetadataInspectionResult;

  /** Estado de la plantilla PowerPoint configurada. */
  powerpoint_template: FileInspectionResult;

  /** Errores bloqueantes detectados. */
  errors: string[];

  /** Advertencias no bloqueantes detectadas. */
  warnings: string[];
}
