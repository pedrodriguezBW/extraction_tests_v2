import { describe, expect, it } from "vitest";

import {
  canAnalyzeSimpati,
  dataSelectionReducer,
  dataSourceOptions,
  fileSelectorHint,
  formatFileSize,
  INITIAL_DATA_SELECTION,
  isFileSelectorDisabled,
  pendingSourceMessage,
  simpatiAnalysisHint,
  sourceFiles,
  type DataSelectionState,
} from "./dataSourceSelection";
import { buildInspection, dataSource } from "./testFixtures";
import type { SimpatiInspectionResponse } from "../types/simpati";

const SIMPATI_FILE = "03_Data/01_SIMPATI/acquisition.x03";
const GRAPHTEC_FILE = "03_Data/02_Graphtec/run_01.csv";

function simpatiResult(): SimpatiInspectionResponse {
  return {
    success: true,
    test_root: "C:\\Tests\\TEST - 001",
    available: true,
    file_name: "acquisition.x03",
    file_path: "C:\\Tests\\TEST - 001\\03_Data\\01_SIMPATI\\acquisition.x03",
    encoding: "cp1252",
    records_count: 2,
    acquisition_start: "2026-09-23T08:00:00",
    acquisition_end: "2026-09-23T10:30:00",
    channels: [],
    preview_timestamps: [],
    thermal_channels: [],
    advanced_channels: [],
    errors: [],
  };
}

function analyzedSimpatiState(): DataSelectionState {
  let state = dataSelectionReducer(INITIAL_DATA_SELECTION, {
    type: "sourceSelected",
    sourceKey: "simpati",
  });
  state = dataSelectionReducer(state, {
    type: "fileSelected",
    fileRelativePath: SIMPATI_FILE,
  });
  return dataSelectionReducer(state, {
    type: "simpatiInspected",
    fileRelativePath: SIMPATI_FILE,
    result: simpatiResult(),
  });
}

const ready = {
  backendConnected: true,
  busy: false,
};

describe("data source options", () => {
  it("lists SIMPATI, Graphtec and CANoe in this order", () => {
    const options = dataSourceOptions(buildInspection());

    expect(options.map((option) => option.key)).toEqual([
      "simpati",
      "graphtec",
      "canoe",
    ]);
    expect(options.map((option) => option.label)).toEqual([
      "SIMPATI",
      "Graphtec",
      "CANoe",
    ]);
    expect(options.map((option) => option.fileCount)).toEqual([1, 2, 0]);
  });

  it("keeps the three sources when their folders are missing", () => {
    const inspection = buildInspection();
    inspection.data.graphtec = dataSource(
      "graphtec",
      "Graphtec",
      "02_Graphtec",
      [],
      false,
    );

    const options = dataSourceOptions(inspection);

    expect(options).toHaveLength(3);
    expect(options[1]).toMatchObject({ key: "graphtec", found: false });
  });
});

describe("file selector", () => {
  it("shows the files of the selected source", () => {
    const inspection = buildInspection();

    expect(
      sourceFiles(inspection, "simpati").map((file) => file.relative_path),
    ).toEqual([SIMPATI_FILE]);
    expect(
      sourceFiles(inspection, "graphtec").map((file) => file.name),
    ).toEqual(["run_01.csv", "run_02.csv"]);
    expect(sourceFiles(inspection, "canoe")).toEqual([]);
  });

  it("is disabled without a selected source", () => {
    expect(isFileSelectorDisabled(buildInspection(), null)).toBe(true);
    expect(fileSelectorHint(buildInspection(), null)).toBe(
      "Select a data source to list its files.",
    );
  });

  it("is disabled when the source has no files", () => {
    const inspection = buildInspection();

    expect(isFileSelectorDisabled(inspection, "canoe")).toBe(true);
    expect(fileSelectorHint(inspection, "canoe")).toBe(
      "No files were found in the CANoe folder.",
    );
  });

  it("is disabled when the source folder does not exist", () => {
    const inspection = buildInspection();
    inspection.data.canoe = dataSource(
      "canoe",
      "CANoe",
      "03_CANoe",
      [],
      false,
    );

    expect(isFileSelectorDisabled(inspection, "canoe")).toBe(true);
    expect(fileSelectorHint(inspection, "canoe")).toBe(
      "The CANoe folder was not found in 03_Data.",
    );
  });

  it("is enabled when the source contains files", () => {
    const inspection = buildInspection();

    expect(isFileSelectorDisabled(inspection, "graphtec")).toBe(false);
    expect(fileSelectorHint(inspection, "graphtec")).toBeNull();
  });
});

describe("selection state", () => {
  it("clears the selected file when the source changes", () => {
    let state = dataSelectionReducer(INITIAL_DATA_SELECTION, {
      type: "sourceSelected",
      sourceKey: "graphtec",
    });
    state = dataSelectionReducer(state, {
      type: "fileSelected",
      fileRelativePath: GRAPHTEC_FILE,
    });
    expect(state.fileRelativePath).toBe(GRAPHTEC_FILE);

    state = dataSelectionReducer(state, {
      type: "sourceSelected",
      sourceKey: "canoe",
    });

    expect(state).toEqual({
      sourceKey: "canoe",
      fileRelativePath: null,
      simpati: null,
    });
  });

  it("clears the SIMPATI result and preview when the source changes", () => {
    const analyzed = analyzedSimpatiState();
    expect(analyzed.simpati).not.toBeNull();

    const state = dataSelectionReducer(analyzed, {
      type: "sourceSelected",
      sourceKey: "graphtec",
    });

    expect(state.simpati).toBeNull();
    expect(state.fileRelativePath).toBeNull();
  });

  it("keeps the state when the same source is selected again", () => {
    const analyzed = analyzedSimpatiState();

    expect(
      dataSelectionReducer(analyzed, {
        type: "sourceSelected",
        sourceKey: "simpati",
      }),
    ).toBe(analyzed);
  });

  it("keeps the new file and clears the previous result when the file changes", () => {
    const state = dataSelectionReducer(analyzedSimpatiState(), {
      type: "fileSelected",
      fileRelativePath: "03_Data/01_SIMPATI/other.x03",
    });

    expect(state.sourceKey).toBe("simpati");
    expect(state.fileRelativePath).toBe("03_Data/01_SIMPATI/other.x03");
    expect(state.simpati).toBeNull();
  });

  it("does not analyze anything when the selection changes", () => {
    let state = dataSelectionReducer(INITIAL_DATA_SELECTION, {
      type: "sourceSelected",
      sourceKey: "simpati",
    });
    state = dataSelectionReducer(state, {
      type: "fileSelected",
      fileRelativePath: SIMPATI_FILE,
    });

    expect(state.simpati).toBeNull();
  });

  it("ignores a SIMPATI result that belongs to a previous selection", () => {
    const state = dataSelectionReducer(
      dataSelectionReducer(INITIAL_DATA_SELECTION, {
        type: "sourceSelected",
        sourceKey: "graphtec",
      }),
      {
        type: "simpatiInspected",
        fileRelativePath: SIMPATI_FILE,
        result: simpatiResult(),
      },
    );

    expect(state.simpati).toBeNull();
  });

  it("resets the selection", () => {
    expect(
      dataSelectionReducer(analyzedSimpatiState(), { type: "reset" }),
    ).toEqual(INITIAL_DATA_SELECTION);
  });
});

describe("SIMPATI analysis gating", () => {
  const simpatiSelection = {
    sourceKey: "simpati" as const,
    fileRelativePath: SIMPATI_FILE,
  };

  it("is enabled for the selected SIMPATI acquisition file", () => {
    expect(
      canAnalyzeSimpati({
        inspection: buildInspection(),
        selection: simpatiSelection,
        ...ready,
      }),
    ).toBe(true);
    expect(
      simpatiAnalysisHint(buildInspection(), simpatiSelection),
    ).toBeNull();
  });

  it("is disabled for Graphtec and CANoe", () => {
    const inspection = buildInspection();

    expect(
      canAnalyzeSimpati({
        inspection,
        selection: { sourceKey: "graphtec", fileRelativePath: GRAPHTEC_FILE },
        ...ready,
      }),
    ).toBe(false);
    expect(
      canAnalyzeSimpati({
        inspection,
        selection: { sourceKey: "canoe", fileRelativePath: null },
        ...ready,
      }),
    ).toBe(false);
    expect(pendingSourceMessage(inspection, "graphtec")).toBe(
      "Reading Graphtec files will be added in a later increment.",
    );
    expect(pendingSourceMessage(inspection, "canoe")).toBe(
      "Reading CANoe files will be added in a later increment.",
    );
    expect(pendingSourceMessage(inspection, "simpati")).toBeNull();
  });

  it("requires a selected SIMPATI file", () => {
    const selection = { sourceKey: "simpati" as const, fileRelativePath: null };

    expect(
      canAnalyzeSimpati({
        inspection: buildInspection(),
        selection,
        ...ready,
      }),
    ).toBe(false);
    expect(simpatiAnalysisHint(buildInspection(), selection)).toBe(
      "Select a SIMPATI file to enable the analysis.",
    );
  });

  it("requires a selected source", () => {
    const selection = { sourceKey: null, fileRelativePath: null };

    expect(
      canAnalyzeSimpati({
        inspection: buildInspection(),
        selection,
        ...ready,
      }),
    ).toBe(false);
  });

  it("requires an inspected project", () => {
    expect(
      canAnalyzeSimpati({
        inspection: null,
        selection: simpatiSelection,
        ...ready,
      }),
    ).toBe(false);
    expect(simpatiAnalysisHint(null, simpatiSelection)).toBe(
      "SIMPATI analysis is enabled after project inspection.",
    );
  });

  it("requires a connected backend and no operation in progress", () => {
    const inspection = buildInspection();

    expect(
      canAnalyzeSimpati({
        inspection,
        selection: simpatiSelection,
        backendConnected: false,
        busy: false,
      }),
    ).toBe(false);
    expect(
      canAnalyzeSimpati({
        inspection,
        selection: simpatiSelection,
        backendConnected: true,
        busy: true,
      }),
    ).toBe(false);
  });

  it("only analyzes the acquisition file used by the SIMPATI flow", () => {
    const inspection = buildInspection();
    inspection.data.simpati = dataSource("simpati", "SIMPATI", "01_SIMPATI", [
      "acquisition.x03",
      "notes.txt",
    ]);
    const selection = {
      sourceKey: "simpati" as const,
      fileRelativePath: "03_Data/01_SIMPATI/notes.txt",
    };

    expect(canAnalyzeSimpati({ inspection, selection, ...ready })).toBe(false);
    expect(simpatiAnalysisHint(inspection, selection)).toBe(
      "SIMPATI analysis currently supports the detected acquisition file acquisition.x03.",
    );
  });

  it("rejects a file that is not part of the selected source", () => {
    expect(
      canAnalyzeSimpati({
        inspection: buildInspection(),
        selection: { sourceKey: "simpati", fileRelativePath: GRAPHTEC_FILE },
        ...ready,
      }),
    ).toBe(false);
  });
});

describe("file size formatting", () => {
  it("uses compact units", () => {
    expect(formatFileSize(512)).toBe("512 B");
    expect(formatFileSize(125600)).toBe("123 KB");
    expect(formatFileSize(1536)).toBe("1.5 KB");
    expect(formatFileSize(5 * 1024 * 1024)).toBe("5.0 MB");
  });
});
