import { afterEach, describe, expect, it, vi } from "vitest";

import {
  checkHealth,
  deleteRenderedAsset,
  fetchRenderedAsset,
  generateReport,
  getRenderedAssetUrl,
  inspectGraphtec,
  inspectProject,
  inspectSimpati,
  listRenderedAssets,
  previewGraphtecChart,
  saveGraphtecChart,
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
      "deleteRenderedAsset",
      "fetchRenderedAsset",
      "generateReport",
      "getRenderedAssetUrl",
      "inspectGraphtec",
      "inspectProject",
      "inspectSimpati",
      "listRenderedAssets",
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
      generateReport("C:\\Tests\\Missing", []),
    ).rejects.toMatchObject({
      message: "The metadata file was not found.",
      status: 400,
    });
  });

  it("sends the ordered image selection when generating a report", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        success: true,
        test_root: "C:\\Tests\\Climate",
        report_path:
          "C:\\Tests\\Climate\\04_Report\\report.pptx",
        report_name: "report.pptx",
        rendered_assets_count: 2,
        rendered_assets: [
          "04_Report/_RenderedAssets/graphtec_chart_01.png",
          "04_Report/_RenderedAssets/chart03_simpati_acquisition_01.png",
        ],
        errors: [],
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const response = await generateReport("C:\\Tests\\Climate", [
      "04_Report/_RenderedAssets/graphtec_chart_01.png",
      "04_Report/_RenderedAssets/chart03_simpati_acquisition_01.png",
    ]);

    expect(response.rendered_assets_count).toBe(2);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/projects/generate-report"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          test_root: "C:\\Tests\\Climate",
          selected_rendered_assets: [
            "04_Report/_RenderedAssets/graphtec_chart_01.png",
            "04_Report/_RenderedAssets/chart03_simpati_acquisition_01.png",
          ],
        }),
      }),
    );
  });

  it("sends an explicit empty selection when no image is selected", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        success: true,
        test_root: "C:\\Tests\\Climate",
        report_path: "C:\\Tests\\Climate\\04_Report\\report.pptx",
        report_name: "report.pptx",
        rendered_assets_count: 0,
        rendered_assets: [],
        errors: [],
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await generateReport("C:\\Tests\\Climate", []);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/projects/generate-report"),
      expect.objectContaining({
        body: JSON.stringify({
          test_root: "C:\\Tests\\Climate",
          selected_rendered_assets: [],
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

    const selectedFetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        success: true,
        test_root: "C:\\Tests\\Climate",
        available: true,
        acquisitions: [],
        errors: [],
      }),
    );
    vi.stubGlobal("fetch", selectedFetchMock);

    await inspectSimpati(
      "C:\\Tests\\Climate",
      "03_Data/01_SIMPATI/ensayo.x04",
    );

    expect(selectedFetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/projects/simpati/inspect"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          test_root: "C:\\Tests\\Climate",
          relative_path: "03_Data/01_SIMPATI/ensayo.x04",
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
          "C:\\Tests\\Climate\\04_Report\\_RenderedAssets\\chart_simpati_x04_01.png",
        chart_name: "chart_simpati_x04_01.png",
        relative_path:
          "04_Report/_RenderedAssets/chart_simpati_x04_01.png",
        source_relative_path: "03_Data/01_SIMPATI/ensayo.x04",
        acquisition_index: 4,
        directory_found: true,
        assets_count: 1,
        assets: [
          {
            name: "chart_simpati_x04_01.png",
            relative_path:
              "04_Report/_RenderedAssets/chart_simpati_x04_01.png",
            extension: ".png",
            size: 1200,
            source: "simpati",
            metadata_name: "chart_simpati_x04_01.json",
          },
        ],
        warnings: [],
        errors: [],
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const saved = await saveSimpatiChart(
      "C:\\Tests\\Climate",
      "03_Data/01_SIMPATI/ensayo.x04",
      "data:image/png;base64,AAAA",
    );

    expect(saved.assets[0].source).toBe("simpati");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/projects/simpati/save-chart"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          test_root: "C:\\Tests\\Climate",
          relative_path: "03_Data/01_SIMPATI/ensayo.x04",
          image_base64: "data:image/png;base64,AAAA",
        }),
      }),
    );
  });

  it("lists the rendered assets of the selected project", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        success: true,
        test_root: "C:\\Tests\\Climate",
        directory_found: true,
        assets_count: 2,
        assets: [
          {
            name: "chart03_simpati_acquisition_01.png",
            relative_path:
              "04_Report/_RenderedAssets/chart03_simpati_acquisition_01.png",
            extension: ".png",
            size: 1200,
            source: "simpati",
            metadata_name: null,
          },
          {
            name: "manual.jpg",
            relative_path: "04_Report/_RenderedAssets/manual.jpg",
            extension: ".jpg",
            size: 800,
            source: "manual",
            metadata_name: null,
          },
        ],
        warnings: [{ name: "notes.txt", code: "unsupported_file", message: "x" }],
        errors: [],
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const response = await listRenderedAssets("C:\\Tests\\Climate");

    expect(response.assets.map((asset) => asset.source)).toEqual([
      "simpati",
      "manual",
    ]);
    expect(response.warnings).toHaveLength(1);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/projects/rendered-assets"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          test_root: "C:\\Tests\\Climate",
        }),
      }),
    );
  });

  it("deletes one rendered asset by relative path", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        success: true,
        test_root: "C:\\Tests\\Climate",
        deleted_relative_path:
          "04_Report/_RenderedAssets/chart03_simpati_acquisition_01.png",
        directory_found: true,
        assets_count: 0,
        assets: [],
        warnings: [],
        errors: [],
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await deleteRenderedAsset(
      "C:\\Tests\\Climate",
      "04_Report/_RenderedAssets/chart03_simpati_acquisition_01.png",
    );

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/projects/rendered-assets/delete"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          test_root: "C:\\Tests\\Climate",
          relative_path:
            "04_Report/_RenderedAssets/chart03_simpati_acquisition_01.png",
        }),
      }),
    );
  });

  it("builds an encoded URL for safely opening a rendered asset", () => {
    const url = getRenderedAssetUrl(
      "C:\\Tests\\Climate",
      "04_Report/_RenderedAssets/chart03_simpati_acquisition_01.png",
    );

    expect(url).toContain("/projects/rendered-asset?");
    expect(url).toContain(
      "relative_path=04_Report%2F_RenderedAssets%2Fchart03_simpati_acquisition_01.png",
    );
    expect(url).toContain("test_root=C%3A%5CTests%5CClimate");
  });

  it("fetches a rendered asset image from FastAPI", async () => {
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

    const result = await fetchRenderedAsset(
      "C:\\Tests\\Climate",
      "04_Report/_RenderedAssets/graphtec_chart_01.png",
    );

    expect(result.type).toBe("image/png");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/projects/rendered-asset?"),
      {
        method: "GET",
        cache: "no-store",
      },
    );
  });

  it("rejects a non-image response when opening a rendered asset", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ success: true }, 200)),
    );

    await expect(
      fetchRenderedAsset("C:\\Tests\\Climate", "04_Report/_RenderedAssets/x.png"),
    ).rejects.toMatchObject({
      message: "The backend did not return a valid image.",
    });
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

  it("returns the rendered asset inventory after saving a Graphtec chart", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        success: true,
        test_root: TEST_ROOT,
        chart_name: "graphtec_chart_01.png",
        chart_path: `${TEST_ROOT}\\04_Report\\_RenderedAssets\\graphtec_chart_01.png`,
        relative_path: "04_Report/_RenderedAssets/graphtec_chart_01.png",
        metadata_name: "graphtec_chart_01.json",
        directory_found: true,
        assets_count: 1,
        assets: [
          {
            name: "graphtec_chart_01.png",
            relative_path: "04_Report/_RenderedAssets/graphtec_chart_01.png",
            extension: ".png",
            size: 2000,
            source: "graphtec",
            metadata_name: "graphtec_chart_01.json",
          },
        ],
        warnings: [],
        errors: [],
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const response = await saveGraphtecChart(TEST_ROOT, "03_Data/02_Graphtec/a.txt", {
      series: ["voltage"],
      title: "",
      show_legend: true,
      show_phase_separators: true,
      time_min: null,
      time_max: null,
    });

    expect(response.relative_path).toBe("04_Report/_RenderedAssets/graphtec_chart_01.png");
    expect(response.assets.map((asset) => asset.source)).toEqual(["graphtec"]);
  });
});
