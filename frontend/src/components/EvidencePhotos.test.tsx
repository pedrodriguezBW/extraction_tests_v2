import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { EvidencePhotos } from "./EvidencePhotos";
import {
  INITIAL_EVIDENCE_PHOTO_SELECTION,
  evidencePhotoSelectionReducer,
  type EvidencePhotoSelectionState,
} from "../services/evidencePhotoSelection";
import { buildInspection } from "../services/testFixtures";

function loaded(): EvidencePhotoSelectionState {
  const inspection = buildInspection();
  const evidences = {
    ...inspection.evidences,
    evidences: [
      {
        ...inspection.evidences.evidences[0],
        photos: [1, 2, 3, 4, 5].map((n) => ({
          ...inspection.evidences.evidences[0].photos[0],
          saved_name: `initial_${n}.jpg`,
          relative_path: `02_Evidences/00_Initial/initial_${n}.jpg`,
        })),
      },
      inspection.evidences.evidences[1],
    ],
  };
  return evidencePhotoSelectionReducer(INITIAL_EVIDENCE_PHOTO_SELECTION, {
    type: "inspectionLoaded",
    evidences,
  });
}

function render(state: EvidencePhotoSelectionState): string {
  return renderToStaticMarkup(
    <EvidencePhotos
      state={state}
      getImageUrl={(path) => `http://backend/evidence-photo?relative_path=${path}`}
      onToggle={() => undefined}
      onSelectAll={() => undefined}
      onClearSelection={() => undefined}
      onSelectEvidence={() => undefined}
      onClearEvidence={() => undefined}
    />,
  );
}

function panel(html: string, section: "assembly" | "results"): string {
  const start = html.indexOf(`data-section="${section}"`);
  const other = html.indexOf('data-section="', start + 20);
  return html.slice(start, other === -1 ? undefined : other);
}

describe("EvidencePhotos", () => {
  it("shows two separated panels named after the report sections", () => {
    const html = render(loaded());
    expect(html).toContain("2. Test Assembly");
    expect(html).toContain("4. Test Results");
    expect(html).toContain("evidence-photos__panel--assembly");
    expect(html).toContain("evidence-photos__panel--results");
    expect(html.indexOf("2. Test Assembly")).toBeLessThan(html.indexOf("4. Test Results"));
  });

  it("lists each evidence only in its own panel with the panel badge", () => {
    const html = render(loaded());
    const assembly = panel(html, "assembly");
    const results = panel(html, "results");
    expect(assembly).toContain("Initial condition");
    expect(assembly).not.toContain("Final condition");
    expect(assembly).toContain("evidence-photos__badge--assembly");
    expect(assembly).not.toContain("evidence-photos__badge--results");
    expect(results).toContain("Final condition");
    expect(results).not.toContain("Initial condition");
  });

  it("shows the assembly limit and disables unselected photos at 4", () => {
    const html = panel(render(loaded()), "assembly");
    expect(html).toContain("4 / 4 selected");
    expect(html).toContain("admits up to 4 photos");
    expect(html).toContain("Select first 4");
    expect((html.match(/evidence-photos__photo--blocked/g) ?? []).length).toBe(1);
  });

  it("explains that an evidence without photos keeps its slide", () => {
    const html = panel(render(loaded()), "results");
    expect(html).toContain("0 of 0 selected");
    expect(html).toContain("the evidence slide is kept");
  });

  it("shows empty states when a section has no evidences", () => {
    const html = render(INITIAL_EVIDENCE_PHOTO_SELECTION);
    expect(html).toContain("Test Assembly will be generated without photos");
    expect(html).toContain("No evidences other than the initial condition");
  });
});
