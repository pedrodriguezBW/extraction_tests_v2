import { describe, expect, it } from "vitest";
import { emptyInputs, mergeChannels } from "./reportInputs";

describe("configuración del ensayo", () => {
  it("precarga canales conservando valores y filas ausentes o manuales", () => {
    const first = mergeChannels(emptyInputs(), ["A", "B"]);
    first.measurement_points[0].location = "Espécimen";
    first.measurement_points[0].function = "control";
    first.measurement_points.push({channel: "Manual", location: "Puerta", sensor_type: "T", function: "air"});
    const second = mergeChannels(first, ["A", "C"]);
    expect(second.measurement_points.map(point => point.channel)).toEqual(["A", "B", "Manual", "C"]);
    expect(second.measurement_points[0].location).toBe("Espécimen");
    expect(second.measurement_points[0].function).toBe("control");
    expect(second.measurement_points[3].location).toBe("");
    expect(mergeChannels(second, ["A", "C"])).toEqual(second);
  });
});
