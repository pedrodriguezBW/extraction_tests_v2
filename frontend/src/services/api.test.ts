import { afterEach, describe, expect, it, vi } from "vitest";

import {
  checkHealth,
  deleteGraphtecChart,
  fetchGraphtecChart,
  getGraphtecChartUrl,
  inspectGraphtec,
  listGraphtecCharts,
  previewGraphtecChart,
  saveGraphtecChart,
  deleteSimpatiChart,
  fetchSimpatiChart,
  generateReport,
  getSimpatiChartUrl,
  inspectProject,
  inspectSimpati,
  listSimpatiCharts,
  saveSimpatiChart,
} from "./api";
import {
  buildGraphtecInspection,
  buildGraphtecPreview,
  buildInspection,
  TEST_ROOT,
} from "./testFixtures";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json",
    },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("API service", () => {
  it("interprets a valid health response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        status: "ok",
        application: "climatic-report-generator",
        version: "0.2.1",
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(checkHealth()).resolves.toEqual({
      status: "ok",
      application: "climatic-report-generator",
      version: "0.2.1",
    });
  });

  it("sends the selected path when inspecting a project", async () => {
    const inspection = buildInspection();
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(inspection));
    vi.stubGlobal("fetch", fetchMock);

    await expect(inspectProject(TEST_ROOT)).resolves.toEqual(inspection);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/projects/inspect"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          test_root: TEST_ROOT,
        }),
      }),
    );
  });

  it("exposes only the agent metadata workflow endpoints", async () => {
    const api = await import("./api");

    expect(Object.keys(api).sort()).toEqual([
      "API_BASE_URL",
      "ApiClientError",
      "checkHealth",
      "deleteGraphtecChart",
      "deleteSimpatiChart",
      "fetchGraphtecChart",
      "fetchSimpatiChart",
      "generateReport",
      "getGraphtecChartUrl",
      "getSimpatiChartUrl",
      "inspectGraphtec",
      "inspectProject",
      "inspectSimpati",
      "listGraphtecCharts",
      "listSimpatiCharts",
      "previewGraphtecChart",
      "saveGraphtecChart",
      "saveSimpatiChart",
    ]);
  });

  it("converts structured HTTP errors into readable messages", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(
          {
            success: false,
            errors: [
              {
                code: "report_generation_invalid_project",
                message: "The metadata file was not found.",
                exception_type: "FileNotFoundError",
              },
            ],
          },
          400,
        ),
      ),
    );

    await expect(
      generateReport("C:\\Tests\\Missing"),
    ).rejects.toMatchObject({
      message: "The metadata file was not found.",
      status: 400,
    });
  });

  it("sends the selected path when generating a report", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        success: true,
        test_root: "C:\\Tests\\Climate",
        report_path:
          "C:\\Tests\\Climate\\04_Report\\report.pptx",
        report_name: "report.pptx",
        errors: [],
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await generateReport("C:\\Tests\\Climate");

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/projects/generate-report"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          test_root: "C:\\Tests\\Climate",
        }),
      }),
    );
  });

  it("sends the selected path when inspecting SIMPATI", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        success: true,
        test_root: "C:\\Tests\\Climate",
        available: true,
        file_name: "acquisition.x03",
        file_path:
          "C:\\Tests\\Climate\\03_Data\\01_SIMPATI\\acquisition.x03",
        encoding: "cp1252",
        records_count: 120,
        acquisition_start: "2026-09-23T08:00:00",
        acquisition_end: "2026-09-23T10:30:00",
        channels: ["Basket temperature", "Basket setpoint"],
        preview_timestamps: [
          "2026-09-23T08:00:00",
          "2026-09-23T10:30:00",
        ],
        thermal_channels: [
          {
            id: "A:Temp canast [°C]",
            label: "Basket temperature",
            source_column: "A:Temp canast [°C]",
            thermal: true,
            values: [21.5, 22],
          },
        ],
        advanced_channels: [],
        errors: [],
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await inspectSimpati("C:\\Tests\\Climate");

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/projects/simpati/inspect"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          test_root: "C:\\Tests\\Climate",
        }),
      }),
    );
  });

  it("sends PNG data when saving the current SIMPATI chart", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        success: true,
        test_root: "C:\\Tests\\Climate",
        chart_path:
          "C:\\Tests\\Climate\\04_Report\\_RenderedAssets\\chart03_simpati_acquisition_01.png",
        chart_name: "chart03_simpati_acquisition_01.png",
        charts_count: 1,
        charts: [
          {
            chart_name: "chart03_simpati_acquisition_01.png",
            chart_path:
              "C:\\Tests\\Climate\\04_Report\\_RenderedAssets\\chart03_simpati_acquisition_01.png",
            size_bytes: 1200,
          },
        ],
        errors: [],
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await saveSimpatiChart(
      "C:\\Tests\\Climate",
      "data:image/png;base64,AAAA",
    );

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/projects/simpati/save-chart"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          test_root: "C:\\Tests\\Climate",
          image_base64: "data:image/png;base64,AAAA",
        }),
      }),
    );
  });

  it("lists saved SIMPATI charts for the selected project", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        success: true,
        test_root: "C:\\Tests\\Climate",
        charts_count: 1,
        charts: [],
        errors: [],
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await listSimpatiCharts("C:\\Tests\\Climate");

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/projects/simpati/charts"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          test_root: "C:\\Tests\\Climate",
        }),
      }),
    );
  });

  it("deletes one saved SIMPATI chart by exact name", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        success: true,
        test_root: "C:\\Tests\\Climate",
        deleted_chart_name: "chart03_simpati_acquisition_01.png",
        charts_count: 0,
        charts: [],
        errors: [],
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await deleteSimpatiChart(
      "C:\\Tests\\Climate",
      "chart03_simpati_acquisition_01.png",
    );

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/projects/simpati/delete-chart"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          test_root: "C:\\Tests\\Climate",
          chart_name: "chart03_simpati_acquisition_01.png",
        }),
      }),
    );
  });

  it("builds an encoded URL for safely opening a saved chart", () => {
    const url = getSimpatiChartUrl(
      "C:\\Tests\\Climate",
      "chart03_simpati_acquisition_01.png",
    );

    expect(url).toContain("/projects/simpati/chart?");
    expect(url).toContain("chart_name=chart03_simpati_acquisition_01.png");
    expect(url).toContain("test_root=C%3A%5CTests%5CClimate");
  });

  it("fetches a saved chart image from FastAPI", async () => {
    const imageBlob = new Blob(["image"], { type: "image/png" });
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(imageBlob, {
        status: 200,
        headers: {
          "Content-Type": "image/png",
        },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchSimpatiChart(
      "C:\\Tests\\Climate",
      "chart03_simpati_acquisition_01.png",
    );

    expect(result.type).toBe("image/png");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/projects/simpati/chart?"),
      {
        method: "GET",
        cache: "no-store",
      },
    );
  });
});

describe("Graphtec API", () => {
  const relativePath = "03_Data/02_Graphtec/run_01.txt";
  const chart = {
    series: ["voltage" as const, "resistance" as const],
    title: "Graphtec IR - Channel 1",
    show_legend: true,
    show_phase_separators: true,
    time_min: null,
    time_max: 9,
  };

  it("sends the test root and relative path when analyzing Graphtec", async () => {
    const result = buildGraphtecInspection();
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(result));
    vi.stubGlobal("fetch", fetchMock);

    await expect(inspectGraphtec(TEST_ROOT, relativePath)).resolves.toEqual(result);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/projects/graphtec/inspect"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ test_root: TEST_ROOT, relative_path: relativePath }),
      }),
    );
  });

  it("sends the chart settings when previewing and saving", async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve(jsonResponse(buildGraphtecPreview())),
    );
    vi.stubGlobal("fetch", fetchMock);

    await previewGraphtecChart(TEST_ROOT, relativePath, chart);
    await saveGraphtecChart(TEST_ROOT, relativePath, chart);

    const body = JSON.stringify({ test_root: TEST_ROOT, relative_path: relativePath, chart });
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/projects/graphtec/preview-chart"),
      expect.objectContaining({ method: "POST", body }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/projects/graphtec/save-chart"),
      expect.objectContaining({ method: "POST", body }),
    );
  });

  it("reports structured Graphtec errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(
          {
            success: false,
            errors: [
              {
                code: "graphtec_invalid_path",
                message: "The selected file is not inside 03_Data/02_Graphtec.",
              },
            ],
          },
          400,
        ),
      ),
    );

    await expect(inspectGraphtec(TEST_ROOT, "03_Data/01_SIMPATI/a.txt")).rejects.toMatchObject({
      message: "The selected file is not inside 03_Data/02_Graphtec.",
      status: 400,
    });
  });

  it("lists, opens and deletes saved Graphtec charts", async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve(
        jsonResponse({ success: true, test_root: TEST_ROOT, charts_count: 0, charts: [], errors: [] }),
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await listGraphtecCharts(TEST_ROOT);
    await deleteGraphtecChart(TEST_ROOT, "graphtec_chart_01.png");

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/projects/graphtec/charts"),
      expect.objectContaining({ body: JSON.stringify({ test_root: TEST_ROOT }) }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/projects/graphtec/delete-chart"),
      expect.objectContaining({
        body: JSON.stringify({ test_root: TEST_ROOT, chart_name: "graphtec_chart_01.png" }),
      }),
    );

    const url = getGraphtecChartUrl(TEST_ROOT, "graphtec_chart_01.png");
    expect(url).toContain("/projects/graphtec/chart?");
    expect(url).toContain("chart_name=graphtec_chart_01.png");

    const imageMock = vi.fn().mockResolvedValue(
      new Response(new Blob(["image"], { type: "image/png" }), {
        status: 200,
        headers: { "Content-Type": "image/png" },
      }),
    );
    vi.stubGlobal("fetch", imageMock);
    const image = await fetchGraphtecChart(TEST_ROOT, "graphtec_chart_01.png");
    expect(image.type).toBe("image/png");
  });
});
