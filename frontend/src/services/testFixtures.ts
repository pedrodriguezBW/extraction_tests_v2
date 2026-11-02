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
import type { RenderedAsset } from "../types/renderedAssets";
import type {
  SimpatiAcquisitionSummary,
  SimpatiInspectionResponse,
} from "../types/simpati";

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
              relative_path: "02_Evidences/00_Initial/251028_Evidence_01.jpg",
              selectable: true,
            },
          ],
          photos_count: 1,
          photos_found_count: 1,
          report_section: "assembly",
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
          report_section: "results",
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
      assembly_max_photos: 4,
      photos_per_slide: 2,
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
      simpati_acquisitions: [
        {
          index: 3,
          label: "x03",
          name: "acquisition.x03",
          relative_path: "03_Data/01_SIMPATI/acquisition.x03",
          size: 1024,
        },
      ],
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

/**
 * Rendered asset of `04_Report/_RenderedAssets` as listed by the backend.
 *
 * @param name File name; the extension is derived from it.
 * @param source Informative origin (`simpati`, `graphtec`, `manual`...).
 */
export function buildRenderedAsset(
  name: string,
  source = "manual",
  overrides: Partial<RenderedAsset> = {},
): RenderedAsset {
  const extension = name.includes(".")
    ? name.slice(name.lastIndexOf(".")).toLowerCase()
    : "";
  return {
    name,
    relative_path: `04_Report/_RenderedAssets/${name}`,
    extension,
    size: 1200,
    source,
    metadata_name: source === "manual" ? null : `${name.slice(0, name.lastIndexOf("."))}.json`,
    ...overrides,
  };
}

/**
 * Resumen de una adquisición SIMPATI analizada.
 *
 * @param index Número de la extensión `.xNN`.
 * @param overrides Campos que se sustituyen.
 */
export function buildSimpatiAcquisition(
  index: number,
  overrides: Partial<SimpatiAcquisitionSummary> = {},
): SimpatiAcquisitionSummary {
  const label = `x${String(index).padStart(2, "0")}`;
  return {
    index,
    label,
    file_name: `ensayo.${label}`,
    relative_path: `03_Data/01_SIMPATI/ensayo.${label}`,
    size: 2048,
    status: "ready",
    encoding: "cp1252",
    records_count: 120,
    acquisition_start: "2024-03-27T17:25:30",
    acquisition_end: "2024-04-09T20:00:13",
    device: "VOSTCH TS",
    program: null,
    channels_count: 86,
    channels: [],
    thermal_channels: ["Basket temperature", "Basket setpoint"],
    rejected_rows: 0,
    rejected_rows_examples: [],
    error: null,
    ...overrides,
  };
}

/**
 * Resultado del análisis SIMPATI con varias adquisiciones.
 *
 * @param acquisitions Adquisiciones analizadas, en orden numérico.
 * @param selectedIndex Índice de la adquisición previsualizada.
 */
export function buildSimpatiInspection(
  acquisitions: SimpatiAcquisitionSummary[],
  selectedIndex: number | null = acquisitions[0]?.index ?? null,
): SimpatiInspectionResponse {
  const selected =
    acquisitions.find((acquisition) => acquisition.index === selectedIndex) ??
    null;
  const processed = acquisitions.filter(
    (acquisition) =>
      acquisition.status === "ready" ||
      acquisition.status === "no_thermal_channels",
  );
  return {
    success: true,
    test_root: TEST_ROOT,
    available: acquisitions.length > 0,
    acquisitions,
    found_count: acquisitions.length,
    processed_count: processed.length,
    ready_count: acquisitions.filter((item) => item.status === "ready").length,
    without_thermal_count: acquisitions.filter(
      (item) => item.status === "no_thermal_channels",
    ).length,
    incompatible_count: acquisitions.length - processed.length,
    selected_relative_path: selected?.relative_path ?? null,
    selected_index: selected?.index ?? null,
    selected_status: selected?.status ?? null,
    file_name: selected?.file_name ?? null,
    file_path: selected ? `${TEST_ROOT}\\03_Data\\01_SIMPATI\\${selected.file_name}` : null,
    encoding: selected?.encoding ?? null,
    records_count: selected?.records_count ?? 0,
    acquisition_start: selected?.acquisition_start ?? null,
    acquisition_end: selected?.acquisition_end ?? null,
    channels: [],
    preview_timestamps: [],
    thermal_channels: [],
    advanced_channels: [],
    errors: [],
  };
}
