import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { SimpatiChart } from "./SimpatiChart";
import {
  buildSimpatiAcquisition,
  buildSimpatiInspection,
} from "../services/testFixtures";
import type { SimpatiInspectionResponse } from "../types/simpati";

function inspection(): SimpatiInspectionResponse {
  const base = buildSimpatiInspection([buildSimpatiAcquisition(1)]);
  return {
    ...base,
    preview_timestamps: [
      "2024-02-22T10:00:00",
      "2024-02-22T10:01:00",
      "2024-02-22T10:02:00",
    ],
    thermal_channels: [
      {
        id: "chamber_temperature",
        label: "Chamber temperature",
        source_column: "A:Temp",
        thermal: true,
        role: "chamber_temperature",
        unit: "°C",
        values: [20, 21.5, 23],
      },
    ],
  };
}

function render(): string {
  return renderToStaticMarkup(
    <SimpatiChart
      data={inspection()}
      saving={false}
      savedChartNames={[]}
      title="SIMPATI x01 · test.x01"
      onSave={() => Promise.reject(new Error("not used"))}
    />,
  );
}

describe("SimpatiChart", () => {
  it("has no start and end range controls below the chart", () => {
    const markup = render();
    expect(markup).not.toContain('type="range"');
    expect(markup).not.toContain("simpati-range-controls");
    expect(markup).not.toContain("Start:");
    expect(markup).not.toContain("End:");
  });

  it("keeps Reset view and Save current chart", () => {
    const markup = render();
    expect(markup).toContain(">Reset view</button>");
    expect(markup).toContain(">Save current chart</button>");
  });

  it("explains the zoom on the chart without axis mode buttons", () => {
    const markup = render();
    expect(markup).toContain("Drag on the chart to zoom");
    expect(markup).toContain("Double-click the chart");
    expect(markup).not.toMatch(/>\s*(Edit X|Edit Y|Zoom X|Zoom Y)\s*</);
  });

  it("defines the plot clip used by a zoomed value range", () => {
    const markup = render();
    const clipId = /<clipPath id="([^"]+)"/.exec(markup)?.[1];
    expect(clipId).toBeTruthy();
    expect(clipId).toMatch(/^[A-Za-z0-9_-]+$/);
    // En la vista completa el eje Y es automático y las series no se recortan.
    expect(markup).not.toContain(`clip-path="url(#${clipId})"`);
  });

  it("does not draw a zoom selection until the user drags", () => {
    expect(render()).not.toContain("simpati-chart__selection");
  });
});
