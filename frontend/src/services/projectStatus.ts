import type {
  DataSourceInspectionResult,
  DataSourceKey,
  EvidenceResult,
  MetadataInspectionResult,
  ProjectInspectionResponse,
} from "../types/project";

export type ResultStatus = "success" | "warning" | "error" | "unavailable";

export interface ResourceSummaryItem {
  key: string;
  label: string;
  value: string;
  note: string | null;
  status: ResultStatus;
}

export const DATA_SOURCE_KEYS: DataSourceKey[] = [
  "simpati",
  "csv",
  "datalogger",
  "graphtec",
];

/**
 * Report generation only depends on a valid inspection and a valid,
 * existing test_metadata.json. Optional resources never block it.
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

export function evidenceLabel(evidence: EvidenceResult): string {
  return evidence.title?.trim() || evidence.folder;
}

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
