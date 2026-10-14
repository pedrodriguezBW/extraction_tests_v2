import type {
  DataSourceInspectionResult,
  DataSourceKey,
  EvidenceResult,
  MetadataInspectionResult,
  ProjectInspectionResponse,
} from "../types/project";

/**
 * Estado visual utilizado para representar el resultado de una comprobación.
 */
export type ResultStatus = "success" | "warning" | "error" | "unavailable";

/**
 * Elemento mostrado en el resumen de recursos detectados durante la
 * inspección.
 */
export interface ResourceSummaryItem {
  /** Identificador estable del elemento. */
  key: string;

  /** Etiqueta visible del recurso. */
  label: string;

  /** Valor principal mostrado en la interfaz. */
  value: string;

  /** Información complementaria opcional. */
  note: string | null;

  /** Estado visual asociado al recurso. */
  status: ResultStatus;
}

/**
 * Fuentes de adquisición mostradas en el resumen del proyecto.
 */
export const DATA_SOURCE_KEYS: DataSourceKey[] = [
  "simpati",
  "csv",
  "datalogger",
  "graphtec",
];

/**
 * Determina si el resultado de inspección permite generar el informe.
 *
 * La generación depende de una inspección válida y de la existencia de un
 * `test_metadata.json` válido. Los recursos opcionales no bloquean el proceso.
 *
 * @param inspection Resultado de la inspección o `null` si todavía no existe.
 * @returns `true` cuando el informe puede generarse.
 */
export function canGenerateReport(
  inspection: ProjectInspectionResponse | null,
): boolean {
  return (
    inspection !== null &&
    inspection.valid &&
    inspection.metadata.found &&
    inspection.metadata.valid
  );
}

/**
 * Traduce el resultado de validación de los metadatos a un estado visible.
 *
 * @param metadata Resultado de la inspección de `test_metadata.json`.
 * @returns La etiqueta y el estado que debe mostrar la interfaz.
 */
export function metadataStatus(metadata: MetadataInspectionResult): {
  status: ResultStatus;
  label: string;
} {
  if (!metadata.found) {
    return { status: "error", label: "Missing" };
  }
  if (!metadata.valid) {
    return { status: "error", label: "Invalid" };
  }
  return { status: "success", label: "Valid" };
}

/**
 * Construye el resumen visible de una fuente de adquisición.
 *
 * @param source Resultado de la inspección de la fuente.
 * @returns El elemento preparado para el resumen de recursos.
 */
export function dataSourceSummary(
  source: DataSourceInspectionResult,
): ResourceSummaryItem {
  return {
    key: source.key,
    label: source.label,
    value: source.available
      ? `${source.file_count} file${source.file_count === 1 ? "" : "s"}`
      : "Not available",
    note: source.available ? null : "Optional",
    status: source.available ? "success" : "unavailable",
  };
}

/**
 * Obtiene la etiqueta visible de una evidencia.
 *
 * @param evidence Evidencia detectada durante la inspección.
 * @returns El texto utilizado para identificarla en la interfaz.
 */
export function evidenceLabel(evidence: EvidenceResult): string {
  return evidence.title?.trim() || evidence.folder;
}

/**
 * Construye el resumen de metadatos, evidencias y fuentes de adquisición.
 *
 * @param inspection Resultado completo de la inspección del proyecto.
 * @returns Los elementos mostrados en el resumen de recursos.
 */
export function buildResourceSummary(
  inspection: ProjectInspectionResponse,
): ResourceSummaryItem[] {
  const metadata = metadataStatus(inspection.metadata);
  const evidences = inspection.evidences;
  const invalidCount = evidences.invalid_evidences.length;
  const missingPhotos = evidences.photos_count - evidences.photos_found_count;

  return [
    {
      key: "metadata",
      label: "test_metadata.json",
      value: metadata.label,
      note: inspection.metadata.test_name
        ? `Test ${inspection.metadata.test_name}`
        : null,
      status: metadata.status,
    },
    {
      key: "evidences",
      label: "Evidences",
      value: String(evidences.evidences_count),
      note: invalidCount > 0 ? `${invalidCount} invalid` : null,
      status: !evidences.directory.found
        ? "warning"
        : invalidCount > 0
          ? "warning"
          : evidences.evidences_count > 0
            ? "success"
            : "unavailable",
    },
    {
      key: "photos",
      label: "Photos found",
      value: `${evidences.photos_found_count} / ${evidences.photos_count}`,
      note: missingPhotos > 0 ? `${missingPhotos} missing` : null,
      status:
        missingPhotos > 0
          ? "warning"
          : evidences.photos_count > 0
            ? "success"
            : "unavailable",
    },
    ...DATA_SOURCE_KEYS.map((key) => dataSourceSummary(inspection.data[key])),
    {
      key: "template",
      label: "PowerPoint template",
      value: inspection.powerpoint_template.found ? "Found" : "Missing",
      note: inspection.powerpoint_template.name,
      status: inspection.powerpoint_template.found ? "success" : "error",
    },
  ];
}
