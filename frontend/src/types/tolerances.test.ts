import {describe, expect, it} from "vitest";
import {toleranceSummary, type ToleranceResult} from "./tolerances";

describe("duraciones y ciclos observados", () => {
  const base: ToleranceResult = {status: null, channel: "A", reference: "N", scope: "full_acquisition",
    out_of_tolerance_segments: 0, ta_c: -40, tb_c: 85, t1_minutes: null, cycles: 2,
    plateaus: [], excursions: [], warnings: []};
  it("muestra frío y calor por separado cuando no hay una duración común", () => {
    const lines = toleranceSummary({...base, t1_low_minutes: 30, t1_high_minutes: 45, cycles_partial: true});
    expect(lines).toContain("t1 medido: TA 30 min · TB 45 min");
    expect(lines).toContain("Ciclos: 2 (parcial)");
  });
  it("no presenta falta de datos como cero ciclos", () => {
    expect(toleranceSummary({...base, cycles: null}).join(" ")).toContain("Ciclos: —");
  });
});
