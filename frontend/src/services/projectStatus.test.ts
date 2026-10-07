import { describe, expect, it } from "vitest";

import {
  buildResourceSummary,
  canGenerateReport,
  metadataStatus,
} from "./projectStatus";
import { buildInspection } from "./testFixtures";

describe("report generation gating", () => {
  it("is disabled before an inspection", () => {
    expect(canGenerateReport(null)).toBe(false);
  });

  it("is enabled for a valid inspection with valid metadata", () => {
    expect(canGenerateReport(buildInspection())).toBe(true);
  });

  it("does not depend on optional data sources or evidences", () => {
    const inspection = buildInspection();
    inspection.data.simpati.available = false;
    inspection.data.csv.available = false;
    inspection.evidences.evidences = [];
    inspection.evidences.evidences_count = 0;

    expect(canGenerateReport(inspection)).toBe(true);
  });

  it("is disabled when the inspection is invalid", () => {
    expect(canGenerateReport(buildInspection({ valid: false }))).toBe(false);
  });

  it("is disabled when test_metadata.json is missing", () => {
    const inspection = buildInspection();
    inspection.metadata = { ...inspection.metadata, found: false };

    expect(canGenerateReport(inspection)).toBe(false);
  });

  it("is disabled when test_metadata.json is invalid", () => {
    const inspection = buildInspection();
    inspection.metadata = {
      ...inspection.metadata,
      valid: false,
      error: "The metadata file does not contain valid JSON.",
    };

    expect(canGenerateReport(inspection)).toBe(false);
  });
});

describe("metadata status", () => {
  it("distinguishes valid, invalid and missing metadata", () => {
    const metadata = buildInspection().metadata;

    expect(metadataStatus(metadata)).toEqual({
      status: "success",
      label: "Valid",
    });
    expect(metadataStatus({ ...metadata, valid: false })).toEqual({
      status: "error",
      label: "Invalid",
    });
    expect(metadataStatus({ ...metadata, found: false })).toEqual({
      status: "error",
      label: "Missing",
    });
  });
});

describe("resource summary", () => {
  it("lists every resource shown in the review step", () => {
    const summary = buildResourceSummary(buildInspection());

    expect(summary.map((item) => item.label)).toEqual([
      "test_metadata.json",
      "Evidences",
      "Photos found",
      "SIMPATI",
      "CSV",
      "Datalogger",
      "Graphtec",
      "PowerPoint template",
    ]);
  });

  it("reports counts and optional sources compactly", () => {
    const summary = Object.fromEntries(
      buildResourceSummary(buildInspection()).map((item) => [item.key, item]),
    );

    expect(summary.metadata.value).toBe("Valid");
    expect(summary.metadata.note).toBe("Test K-01");
    expect(summary.evidences.value).toBe("2");
    expect(summary.photos.value).toBe("2 / 3");
    expect(summary.photos.note).toBe("1 missing");
    expect(summary.photos.status).toBe("warning");
    expect(summary.simpati.value).toBe("1 file");
    expect(summary.simpati.status).toBe("success");
    expect(summary.datalogger.value).toBe("Not available");
    expect(summary.datalogger.note).toBe("Optional");
    expect(summary.datalogger.status).toBe("unavailable");
    expect(summary.template.value).toBe("Found");
  });
});
