export interface HealthResponse {
  status: string;
  application: string;
  version: string;
}

export interface ProjectInspectionRequest {
  test_root: string;
}

export interface FileInspectionResult {
  found: boolean;
  name: string | null;
  path: string | null;
}

export interface DirectoryInspectionResult {
  found: boolean;
  path: string;
  file_count: number | null;
}

export interface MetadataInspectionResult extends FileInspectionResult {
  valid: boolean;
  error: string | null;
  errors: string[];
  test_name: string | null;
  schema_version: string | null;
  samples_count: number;
  equipment_count: number;
  climatic_profile_points_count: number;
  dut_profile_points_count: number;
  test_events_count: number;
  setup_images_count: number;
  setup_images_found_count: number;
}

export interface EvidencePhotoResult {
  id: string | null;
  original_name: string | null;
  saved_name: string;
  capture_date: string | null;
  mime: string | null;
  size: number | null;
  path: string;
  found: boolean;
}

export interface EvidenceResult {
  id: string | null;
  type: string | null;
  title: string | null;
  reference_type: string | null;
  reference_value: string | null;
  notes: string | null;
  sequence: number | null;
  schema_version: number | null;
  folder: string;
  declared_folder: string | null;
  directory: string;
  descriptor_path: string;
  photos: EvidencePhotoResult[];
  photos_count: number;
  photos_found_count: number;
}

export interface InvalidEvidenceResult {
  folder: string;
  descriptor_path: string;
  errors: string[];
}

export interface MissingEvidencePhotoResult {
  evidence_folder: string;
  evidence_title: string | null;
  saved_name: string;
  path: string;
}

export interface EvidencesInspectionResult {
  directory: DirectoryInspectionResult;
  evidences_count: number;
  photos_count: number;
  photos_found_count: number;
  evidences: EvidenceResult[];
  invalid_evidences: InvalidEvidenceResult[];
  missing_photos: MissingEvidencePhotoResult[];
}

export type DataSourceKey = "simpati" | "csv" | "datalogger" | "graphtec";

export interface DataSourceInspectionResult {
  key: DataSourceKey;
  label: string;
  found: boolean;
  available: boolean;
  path: string;
  file_count: number;
  files: string[];
}

export interface DataSourcesInspectionResult {
  directory: DirectoryInspectionResult;
  simpati: DataSourceInspectionResult;
  csv: DataSourceInspectionResult;
  datalogger: DataSourceInspectionResult;
  graphtec: DataSourceInspectionResult;
  simpati_file: FileInspectionResult;
}

export interface ProjectInspectionResponse {
  valid: boolean;
  test_root: string;
  inputs_directory: DirectoryInspectionResult;
  evidences: EvidencesInspectionResult;
  data: DataSourcesInspectionResult;
  report_directory: DirectoryInspectionResult;
  metadata: MetadataInspectionResult;
  powerpoint_template: FileInspectionResult;
  errors: string[];
  warnings: string[];
}
