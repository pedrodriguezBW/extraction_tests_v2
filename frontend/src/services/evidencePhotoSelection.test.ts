import { describe, expect, it } from "vitest";

import {
  INITIAL_EVIDENCE_PHOTO_SELECTION,
  evidencePhotoReportSummary,
  evidencePhotoSectionCounter,
  evidencePhotoSelectionReducer,
  isAssemblyLimitReached,
  resultEvidenceSlideCount,
  selectedEvidencePhotoPaths,
  type EvidencePhotoSelectionState,
} from "./evidencePhotoSelection";
import type {
  EvidenceResult,
  EvidencesInspectionResult,
} from "../types/project";

function evidence(
  folder: string,
  type: string,
  sequence: number,
  names: string[],
  missing: string[] = [],
): EvidenceResult {
  const photo = (name: string, found: boolean) => ({
    id: null,
    original_name: null,
    saved_name: name,
    capture_date: null,
    mime: "image/jpeg",
    size: 1,
    path: `C:\\T\\02_Evidences\\${folder}\\${name}`,
    found,
    relative_path: `02_Evidences/${folder}/${name}`,
    selectable: found,
  });
  return {
    id: folder,
    type,
    title: folder,
    reference_type: "cycles",
    reference_value: type === "initial" ? "" : "450",
    notes: "",
    sequence,
    schema_version: 1,
    folder,
    declared_folder: folder,
    directory: `C:\\T\\02_Evidences\\${folder}`,
    descriptor_path: `C:\\T\\02_Evidences\\${folder}\\evidence.json`,
    photos: [
      ...names.map((name) => photo(name, true)),
      ...missing.map((name) => photo(name, false)),
    ],
    photos_count: names.length + missing.length,
    photos_found_count: names.length,
    report_section: type === "initial" ? "assembly" : "results",
  };
}

function inspection(evidences: EvidenceResult[]): EvidencesInspectionResult {
  return {
    directory: { found: true, path: "C:\\T\\02_Evidences", file_count: null },
    evidences_count: evidences.length,
    photos_count: 0,
    photos_found_count: 0,
    evidences,
    invalid_evidences: [],
    missing_photos: [],
    assembly_max_photos: 4,
    photos_per_slide: 2,
  };
}

const initial = evidence("00_Initial", "initial", 0, ["i1.jpg", "i2.jpg", "i3.jpg", "i4.jpg", "i5.jpg", "i6.jpg"]);
const incident = evidence("01_Incident", "incident", 1, ["a1.jpg", "a2.jpg", "a3.jpg"], ["gone.jpg"]);
const final = evidence("02_Final", "final", 2, ["f1.jpg"]);

function load(
  evidences = [initial, incident, final],
  state: EvidencePhotoSelectionState = INITIAL_EVIDENCE_PHOTO_SELECTION,
): EvidencePhotoSelectionState {
  return evidencePhotoSelectionReducer(state, {
    type: "inspectionLoaded",
    evidences: inspection(evidences),
  });
}

const A = (n: number) => `02_Evidences/00_Initial/i${n}.jpg`;

describe("evidence photo selection", () => {
  it("splits the photos into Test Assembly and Test Results", () => {
    const state = load();
    expect(state.groups.filter((g) => g.section === "assembly").map((g) => g.folder)).toEqual(["00_Initial"]);
    expect(state.groups.filter((g) => g.section === "results").map((g) => g.folder)).toEqual(["01_Incident", "02_Final"]);
  });

  it("selects the first 4 assembly photos and every result photo by default", () => {
    const state = load();
    expect(selectedEvidencePhotoPaths(state, "assembly")).toEqual([A(1), A(2), A(3), A(4)]);
    expect(selectedEvidencePhotoPaths(state, "results")).toEqual([
      "02_Evidences/01_Incident/a1.jpg",
      "02_Evidences/01_Incident/a2.jpg",
      "02_Evidences/01_Incident/a3.jpg",
      "02_Evidences/02_Final/f1.jpg",
    ]);
    expect(isAssemblyLimitReached(state)).toBe(true);
  });

  it("never selects more than 4 assembly photos", () => {
    let state = load();
    state = evidencePhotoSelectionReducer(state, { type: "toggled", section: "assembly", relativePath: A(5) });
    expect(selectedEvidencePhotoPaths(state, "assembly")).toEqual([A(1), A(2), A(3), A(4)]);
    state = evidencePhotoSelectionReducer(state, { type: "toggled", section: "assembly", relativePath: A(2) });
    state = evidencePhotoSelectionReducer(state, { type: "toggled", section: "assembly", relativePath: A(6) });
    expect(selectedEvidencePhotoPaths(state, "assembly")).toEqual([A(1), A(3), A(4), A(6)]);
    state = evidencePhotoSelectionReducer(state, { type: "selectEvidence", section: "assembly", evidenceKey: initial.descriptor_path });
    expect(selectedEvidencePhotoPaths(state, "assembly")).toHaveLength(4);
  });

  it("select all and clear only affect their own section", () => {
    let state = load();
    state = evidencePhotoSelectionReducer(state, { type: "clearSelection", section: "results" });
    expect(selectedEvidencePhotoPaths(state, "results")).toEqual([]);
    expect(selectedEvidencePhotoPaths(state, "assembly")).toHaveLength(4);
    state = evidencePhotoSelectionReducer(state, { type: "clearSelection", section: "assembly" });
    state = evidencePhotoSelectionReducer(state, { type: "selectAll", section: "results" });
    expect(selectedEvidencePhotoPaths(state, "results")).toHaveLength(4);
    expect(selectedEvidencePhotoPaths(state, "assembly")).toEqual([]);
    state = evidencePhotoSelectionReducer(state, { type: "selectAll", section: "assembly" });
    expect(selectedEvidencePhotoPaths(state, "assembly")).toEqual([A(1), A(2), A(3), A(4)]);
  });

  it("rejects photos of the other section and missing photos", () => {
    const state = load();
    const cleared = evidencePhotoSelectionReducer(state, { type: "clearSelection", section: "assembly" });
    expect(evidencePhotoSelectionReducer(cleared, { type: "toggled", section: "assembly", relativePath: "02_Evidences/02_Final/f1.jpg" })).toBe(cleared);
    expect(evidencePhotoSelectionReducer(state, { type: "toggled", section: "results", relativePath: "02_Evidences/01_Incident/gone.jpg" })).toBe(state);
    expect(evidencePhotoSelectionReducer(state, { type: "selectEvidence", section: "assembly", evidenceKey: final.descriptor_path })).toBe(state);
  });

  it("keeps the selection on a new inspection, adds new photos and drops removed ones", () => {
    let state = load();
    state = evidencePhotoSelectionReducer(state, { type: "toggled", section: "results", relativePath: "02_Evidences/01_Incident/a2.jpg" });
    const incidentWithout3 = evidence("01_Incident", "incident", 1, ["a1.jpg", "a2.jpg", "a4.jpg"]);
    state = load([initial, incidentWithout3, final], state);
    expect(selectedEvidencePhotoPaths(state, "results")).toEqual([
      "02_Evidences/01_Incident/a1.jpg",
      "02_Evidences/01_Incident/a4.jpg",
      "02_Evidences/02_Final/f1.jpg",
    ]);
  });

  it("new assembly photos are only selected while there is room", () => {
    let state = load([evidence("00_Initial", "initial", 0, ["i1.jpg", "i2.jpg"])]);
    state = load([evidence("00_Initial", "initial", 0, ["i1.jpg", "i2.jpg", "i3.jpg", "i4.jpg", "i5.jpg"])], state);
    expect(selectedEvidencePhotoPaths(state, "assembly")).toEqual([A(1), A(2), A(3), A(4)]);
  });

  it("counts slides: two photos per slide, one slide per evidence at least", () => {
    let state = load();
    expect(resultEvidenceSlideCount(state)).toBe(3);
    state = evidencePhotoSelectionReducer(state, { type: "clearSelection", section: "results" });
    expect(resultEvidenceSlideCount(state)).toBe(2);
    expect(evidencePhotoSectionCounter(state, "assembly")).toBe("4 / 4 selected");
    expect(evidencePhotoSectionCounter(state, "results")).toBe("0 of 4 selected");
    expect(evidencePhotoReportSummary(load())).toBe(
      "Test Assembly: 4 photos (2 slides) · Test Results: 4 evidence photos in 3 evidence slides",
    );
  });

  it("resets to the initial state", () => {
    expect(evidencePhotoSelectionReducer(load(), { type: "reset" })).toBe(INITIAL_EVIDENCE_PHOTO_SELECTION);
  });
});
