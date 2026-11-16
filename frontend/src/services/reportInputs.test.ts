import { afterEach, describe, expect, it, vi } from "vitest";
import { generateReport } from "./api";
import { emptyInputs } from "../types/reportInputs";

afterEach(() => vi.unstubAllGlobals());
describe("guardado automático", () => {
  it("guarda lo editado antes de generar sin guardar manualmente", async () => {
    const fetch = vi.fn().mockImplementation(async () => new Response(JSON.stringify({success: true}), {headers: {"Content-Type": "application/json"}}));
    vi.stubGlobal("fetch", fetch);
    const inputs = {...emptyInputs(), test_type: "Nb"};
    await generateReport("test", [], {assembly: [], results: []}, inputs);
    expect(fetch.mock.calls.map(call => String(call[0]).split("/projects")[1])).toEqual(["/report-inputs/save", "/generate-report"]);
    expect(JSON.parse(fetch.mock.calls[0][1].body).inputs).toEqual(inputs);
  });
  it("no genera si el guardado falla", async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({detail: "Sin permisos"}), {status: 403, headers: {"Content-Type": "application/json"}}));
    vi.stubGlobal("fetch", fetch);
    await expect(generateReport("test", [], undefined, emptyInputs())).rejects.toThrow("Sin permisos");
    expect(fetch).toHaveBeenCalledTimes(1);
  });
});
