import type {
  GraphtecChartPreviewResponse,
  GraphtecInspectionResponse,
} from "../types/graphtec";
import type {
  DataSourceFileResult,
  DataSourceInspectionResult,
  DataSourceKey,
  ProjectInspectionResponse,
} from "../types/project";

export const TEST_ROOT = "C:\\Tests\\TEST - 001";

/**
 * Builds a source result as returned by `POST /projects/inspect`.
 *
 * @param found `false` simulates a missing source folder.
 */
export function dataSource(
  key: DataSourceKey,
  label: string,
  folder: string,
  files: string[],
  found = true,
): DataSourceInspectionResult {
  const sourceFiles: DataSourceFileResult[] = found
    ? files.map((name, index) => ({
        name,
        relative_path: `03_Data/${folder}/${name}`,
        extension: name.includes(".")
          ? name.slice(name.lastIndexOf(".")).toLowerCase()
          : "",
        size: 1000 * (index + 1),
      }))
    : [];

  return {
    key,
    label,
    found,
    available: found && sourceFiles.length > 0,
    path: `${TEST_ROOT}\\03_Data\\${folder}`,
    file_count: sourceFiles.length,
    files: sourceFiles,
  };
}

/** Inspection response matching the backend contract for TEST - 001. */
export function buildInspection(
  overrides: Partial<ProjectInspectionResponse> = {},
): ProjectInspectionResponse {
  return {
    valid: true,
    test_root: TEST_ROOT,
    inputs_directory: {
      found: true,
      path: `${TEST_ROOT}\\01_Inputs`,
      file_count: 1,
    },
    evidences: {
      directory: {
        found: true,
        path: `${TEST_ROOT}\\02_Evidences`,
        file_count: null,
      },
      evidences_count: 2,
      photos_count: 3,
      photos_found_count: 2,
      evidences: [
        {
          id: "initial",
          type: "initial",
          title: "Initial condition",
          reference_type: "none",
          reference_value: "",
          notes: "",
          sequence: 0,
          schema_version: 1,
          folder: "00_Initial",
          declared_folder: "00_Initial",
          directory: `${TEST_ROOT}\\02_Evidences\\00_Initial`,
          descriptor_path: `${TEST_ROOT}\\02_Evidences\\00_Initial\\evidence.json`,
          photos: [
            {
              id: "photo-1",
              original_name: "PA285482.JPG",
              saved_name: "251028_Evidence_01.jpg",
              capture_date: "2025-10-28T18:43:18",
              mime: "image/jpeg",
              size: 2580919,
              path: `${TEST_ROOT}\\02_Evidences\\00_Initial\\251028_Evidence_01.jpg`,
              found: true,
            },
          ],
          photos_count: 1,
          photos_found_count: 1,
        },
        {
          id: "final",
          type: "final",
          title: "Final condition",
          reference_type: "none",
          reference_value: "",
          notes: "",
          sequence: 6,
          schema_version: 1,
          folder: "99_Final",
          declared_folder: "99_Final",
          directory: `${TEST_ROOT}\\02_Evidences\\99_Final`,
          descriptor_path: `${TEST_ROOT}\\02_Evidences\\99_Final\\evidence.json`,
          photos: [],
          photos_count: 2,
          photos_found_count: 1,
        },
      ],
      invalid_evidences: [],
      missing_photos: [
        {
          evidence_folder: "99_Final",
          evidence_title: "Final condition",
          saved_name: "251103_Evidence_02.jpg",
          path: `${TEST_ROOT}\\02_Evidences\\99_Final\\251103_Evidence_02.jpg`,
        },
      ],
    },
    data: {
      directory: {
        found: true,
        path: `${TEST_ROOT}\\03_Data`,
        file_count: null,
      },
      simpati: dataSource("simpati", "SIMPATI", "01_SIMPATI", [
        "acquisition.x03",
      ]),
      graphtec: dataSource("graphtec", "Graphtec", "02_Graphtec", [
        "run_01.csv",
        "run_02.csv",
      ]),
      canoe: dataSource("canoe", "CANoe", "03_CANoe", []),
      simpati_file: {
        found: true,
        name: "acquisition.x03",
        path: `${TEST_ROOT}\\03_Data\\01_SIMPATI\\acquisition.x03`,
      },
    },
    report_directory: {
      found: true,
      path: `${TEST_ROOT}\\04_Report`,
      file_count: null,
    },
    metadata: {
      found: true,
      valid: true,
      name: "test_metadata.json",
      path: `${TEST_ROOT}\\04_Report\\test_metadata.json`,
      error: null,
      errors: [],
      test_name: "K-01",
      schema_version: "1.0",
      samples_count: 20,
      equipment_count: 11,
      climatic_profile_points_count: 11,
      dut_profile_points_count: 3,
      test_events_count: 2,
      setup_images_count: 0,
      setup_images_found_count: 0,
    },
    powerpoint_template: {
      found: true,
      name: "template.pptx",
      path: "C:\\Templates\\template.pptx",
    },
    errors: [],
    warnings: [
      "Evidence '99_Final' references a missing photo: 251103_Evidence_02.jpg",
    ],
    ...overrides,
  };
}

/** Graphtec analysis matching the backend contract for an IR file. */
export function buildGraphtecInspection(
  overrides: Partial<GraphtecInspectionResponse> = {},
): GraphtecInspectionResponse {
  return {
    success: true,
    test_root: TEST_ROOT,
    source: "graphtec",
    format: "graphtec_txt_tabulated",
    format_label: "Graphtec TXT (tab-separated)",
    file_name: "run_01.csv",
    relative_path: "03_Data/02_Graphtec/run_01.csv",
    records_count: 73,
    channels: [1],
    test_types: ["IR"],
    statuses: ["TEST", "PASS"],
    phases: ["R", "T", "D"],
    phase_segments: [],
    final_result: "PASS",
    available_series: [
      { id: "voltage", label: "Voltage", unit: "kV", axis: "left", default_selected: true },
      { id: "resistance", label: "Resistance", unit: "Mohm", axis: "right", default_selected: true },
    ],
    original_units: { voltage: ["kV"], resistance: ["Mohm", "Gohm"] },
    normalized_units: { voltage: "kV", resistance: "Mohm", elapsed_time_seconds: "s" },
    elapsed_time_start: 0,
    elapsed_time_end: 14.8,
    duration_seconds: 14.8,
    limited_values_count: 20,
    default_title: "Graphtec IR - Channel 1",
    preview_records: [],
    preview_truncated: true,
    chart_data: {
      elapsed_time_seconds: [],
      voltage_kv: [],
      measurement: [],
      measurement_operator: [],
      status: [],
      phase: [],
      truncated: false,
    },
    warnings: [],
    errors: [],
    ...overrides,
  };
}

/** Graphtec chart preview returned by the backend. */
export function buildGraphtecPreview(
  overrides: Partial<GraphtecChartPreviewResponse> = {},
): GraphtecChartPreviewResponse {
  return {
    success: true,
    test_root: TEST_ROOT,
    relative_path: "03_Data/02_Graphtec/run_01.csv",
    image_base64: "data:image/png;base64,iVBORw0KGgo=",
    width: 1650,
    height: 840,
    title: "Graphtec IR - Channel 1",
    x_axis_label: "Elapsed time [s]",
    series: [],
    axes: [
      { position: "left", label: "Voltage [kV]", series: ["voltage"] },
      { position: "right", label: "Resistance [Mohm]", series: ["resistance"] },
    ],
    time_start: 0,
    time_end: 14.8,
    full_range: true,
    records_plotted: 73,
    limited_points: 20,
    result_points: 1,
    phase_markers: [],
    notes: ["Limit marker indicates a value greater than the displayed threshold."],
    errors: [],
    ...overrides,
  };
}
