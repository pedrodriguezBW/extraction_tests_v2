import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { SimpatiAcquisitions } from "./SimpatiAcquisitions";
import {
  buildSimpatiAcquisition,
  buildSimpatiInspection,
} from "../services/testFixtures";

function render(selectedIndex: number | null = 1): string {
  const result = buildSimpatiInspection(
    [
      buildSimpatiAcquisition(1, {
        thermal_channels: ["Chamber temperature", "Chamber setpoint"],
        channels_count: 59,
      }),
      buildSimpatiAcquisition(3),
      buildSimpatiAcquisition(4, {
        status: "no_thermal_channels",
        thermal_channels: [],
      }),
      buildSimpatiAcquisition(7, {
        status: "incompatible",
        encoding: null,
        records_count: 0,
        acquisition_start: null,
        acquisition_end: null,
        channels_count: 0,
        thermal_channels: [],
        error: {
          code: "simpati_acquisition_incompatible",
          message: "ensayo.x07: no SIMPATI structure",
          exception_type: "SimpatiDecodingError",
        },
      }),
    ],
    selectedIndex,
  );
  return renderToStaticMarkup(
    <SimpatiAcquisitions
      result={result}
      disabled={false}
      onSelect={() => undefined}
    />,
  );
}

describe("SimpatiAcquisitions", () => {
  it("lists every acquisition with its index, file and status", () => {
    const markup = render();

    for (const label of ["x01", "x03", "x04", "x07"]) {
      expect(markup).toContain(`<strong>${label}</strong>`);
      expect(markup).toContain(`ensayo.${label}`);
    }
    expect(markup.indexOf("x01")).toBeLessThan(markup.indexOf("x03"));
    expect(markup).toContain("cp1252");
    expect(markup).toContain("2024-03-27 17:25:30 – 2024-04-09 20:00:13");
    expect(markup).toContain("Chamber temperature, Chamber setpoint");
    expect(markup).toContain("No representable channels");
    expect(markup).toContain("Incompatible");
    expect(markup).toContain("ensayo.x07: no SIMPATI structure");
  });

  it("summarizes found, processed, without channels and incompatible files", () => {
    const markup = render();

    expect(markup).toContain("4 found");
    expect(markup).toContain("3 processed");
    expect(markup).toContain("2 with representable channels");
    expect(markup).toContain("1 without representable channels");
    expect(markup).toContain("1 incompatible");
  });

  it("marks the previewed acquisition and lets the user open the others", () => {
    const markup = render(3);

    expect(markup).toContain('class="is-selected" aria-selected="true"');
    expect(markup.match(/>Selected</g)).toHaveLength(1);
    expect(markup.match(/>Open</g)).toHaveLength(3);
  });
});
