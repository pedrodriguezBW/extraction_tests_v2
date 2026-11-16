import {describe, expect, it} from "vitest";
import {mergeToleranceTrace, timedPathSegments} from "./simpatiToleranceTrace";
import type {ToleranceResult} from "../types/tolerances";

const times = ["2026-01-01T00:00:00", "2026-01-01T00:01:00", "2026-01-01T00:02:00"];
const peak = "2026-01-01T00:00:30";
const result: ToleranceResult = {channel: "actual", reference: "nominal", status: "NOK", scope: "full_acquisition",
  out_of_tolerance_segments: 1, ta_c: null, tb_c: 90, t1_minutes: 30, cycles: 1, plateaus: [], warnings: [],
  excursions: [[[peak, 84]]], excursion_context: [["2026-01-01T00:00:29", 90], [peak, 84], ["2026-01-01T00:00:31", 90]]};

describe("trazado de las medidas fuera de tolerancia", () => {
  it("la línea incluye el pico real que el muestreo del visor había omitido y sus vecinos", () => {
    const points = mergeToleranceTrace(times, [90, 90, 90], result, "°C");
    expect(points).toContainEqual([peak, 84]);
    expect(points).toContainEqual(["2026-01-01T00:00:29", 90]);
    expect(points).toContainEqual(["2026-01-01T00:00:31", 90]);
    const paths = timedPathSegments(points, times, 0, 2, x => x, y => y);
    expect(paths[0].split(" ")).toContain("0.5,84");
  });
  it("convierte los valores originales a la unidad visible y no duplica muestras", () => {
    const duplicate = {...result, excursions: [[[times[1], 84] as [string, number]]]};
    const points = mergeToleranceTrace(times, [194, 194, 194], duplicate, "°F");
    const matching = points.filter(([time]) => time === times[1]);
    expect(matching).toHaveLength(1);
    expect(matching[0][1]).toBeCloseTo(183.2);
  });
  it("conserva las ausencias de medida como cortes de la línea", () => {
    const incomplete = {...result, excursion_context: [[times[1], null]] as [string, number | null][]};
    const points = mergeToleranceTrace(times, [90, 90, 90], incomplete, "°C");
    expect(points).toContainEqual([times[1], null]);
    const paths = timedPathSegments(points, times, 0, 2, x => x, y => y);
    expect(paths.join(" ")).not.toContain("1,90");
  });
});
