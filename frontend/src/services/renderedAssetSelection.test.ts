import { describe, expect, it } from "vitest";

import {
  INITIAL_RENDERED_ASSET_SELECTION,
  formatFileSize,
  isRenderedAssetSelected,
  renderedAssetSelectionReducer,
  renderedAssetSelectionSummary,
  renderedAssetSourceLabel,
  selectedRenderedAssetCount,
  selectedRenderedAssetPaths,
  type RenderedAssetSelectionState,
} from "./renderedAssetSelection";
import { buildRenderedAsset } from "./testFixtures";

const simpati = buildRenderedAsset("chart03_simpati_acquisition_01.png", "simpati");
const graphtec = buildRenderedAsset("graphtec_chart_01.png", "graphtec");
const manual = buildRenderedAsset("manual_photo.jpg", "manual");

function loaded(
  assets = [simpati, graphtec, manual],
  state: RenderedAssetSelectionState = INITIAL_RENDERED_ASSET_SELECTION,
): RenderedAssetSelectionState {
  return renderedAssetSelectionReducer(state, {
    type: "inventoryLoaded",
    assets,
  });
}

describe("renderedAssetSelectionReducer", () => {
  it("selects every detected image by default on the first load", () => {
    const state = loaded();

    expect(state.loaded).toBe(true);
    expect(selectedRenderedAssetPaths(state)).toEqual([
      simpati.relative_path,
      graphtec.relative_path,
      manual.relative_path,
    ]);
    expect(renderedAssetSelectionSummary(state)).toBe(
      "3 of 3 images selected for the report.",
    );
  });

  it("lists SIMPATI, Graphtec and manual images together", () => {
    const state = loaded();

    expect(state.assets.map((asset) => asset.source)).toEqual([
      "simpati",
      "graphtec",
      "manual",
    ]);
  });

  it("toggles a single image off and on again", () => {
    const unselected = renderedAssetSelectionReducer(loaded(), {
      type: "toggled",
      relativePath: graphtec.relative_path,
    });

    expect(isRenderedAssetSelected(unselected, graphtec.relative_path)).toBe(false);
    expect(selectedRenderedAssetPaths(unselected)).toEqual([
      simpati.relative_path,
      manual.relative_path,
    ]);
    expect(renderedAssetSelectionSummary(unselected)).toBe(
      "2 of 3 images selected for the report.",
    );

    const reselected = renderedAssetSelectionReducer(unselected, {
      type: "toggled",
      relativePath: graphtec.relative_path,
    });

    expect(isRenderedAssetSelected(reselected, graphtec.relative_path)).toBe(true);
    expect(selectedRenderedAssetCount(reselected)).toBe(3);
  });

  it("ignores toggles of unknown paths", () => {
    const state = loaded();

    expect(
      renderedAssetSelectionReducer(state, {
        type: "toggled",
        relativePath: "04_Report/_RenderedAssets/unknown.png",
      }),
    ).toBe(state);
  });

  it("supports select all and clear selection", () => {
    const cleared = renderedAssetSelectionReducer(loaded(), {
      type: "clearSelection",
    });

    expect(selectedRenderedAssetPaths(cleared)).toEqual([]);
    expect(renderedAssetSelectionSummary(cleared)).toBe(
      "No rendered images are selected. The report will be generated without them.",
    );

    const all = renderedAssetSelectionReducer(cleared, { type: "selectAll" });

    expect(selectedRenderedAssetCount(all)).toBe(3);
  });

  it("describes an empty inventory", () => {
    const state = loaded([]);

    expect(renderedAssetSelectionSummary(state)).toBe(
      "No rendered images were found. The report can still be generated.",
    );
    expect(renderedAssetSelectionSummary(INITIAL_RENDERED_ASSET_SELECTION)).toBe(
      "No rendered images were found. The report can still be generated.",
    );
  });

  it("keeps the selection of existing images when the inventory refreshes", () => {
    const partial = renderedAssetSelectionReducer(loaded(), {
      type: "toggled",
      relativePath: simpati.relative_path,
    });

    const refreshed = loaded([simpati, graphtec, manual], partial);

    expect(selectedRenderedAssetPaths(refreshed)).toEqual([
      graphtec.relative_path,
      manual.relative_path,
    ]);
  });

  it("selects new images found during a refresh by default", () => {
    const partial = renderedAssetSelectionReducer(loaded([simpati, graphtec]), {
      type: "toggled",
      relativePath: simpati.relative_path,
    });
    const added = buildRenderedAsset("graphtec_chart_02.png", "graphtec");

    const refreshed = loaded([simpati, graphtec, added, manual], partial);

    expect(selectedRenderedAssetPaths(refreshed)).toEqual([
      graphtec.relative_path,
      added.relative_path,
      manual.relative_path,
    ]);
  });

  it("drops images that disappeared from the inventory", () => {
    const refreshed = loaded([graphtec], loaded());

    expect(refreshed.assets).toEqual([graphtec]);
    expect(selectedRenderedAssetPaths(refreshed)).toEqual([graphtec.relative_path]);
  });

  it("removes a deleted image from the inventory and the selection", () => {
    const removed = renderedAssetSelectionReducer(loaded(), {
      type: "removed",
      relativePath: graphtec.relative_path,
    });

    expect(removed.assets.map((asset) => asset.name)).toEqual([
      simpati.name,
      manual.name,
    ]);
    expect(selectedRenderedAssetPaths(removed)).toEqual([
      simpati.relative_path,
      manual.relative_path,
    ]);
    expect(renderedAssetSelectionSummary(removed)).toBe(
      "2 of 2 images selected for the report.",
    );
  });

  it("returns the selection in inventory order whatever the toggle order", () => {
    let state = renderedAssetSelectionReducer(loaded(), { type: "clearSelection" });
    state = renderedAssetSelectionReducer(state, {
      type: "toggled",
      relativePath: manual.relative_path,
    });
    state = renderedAssetSelectionReducer(state, {
      type: "toggled",
      relativePath: simpati.relative_path,
    });

    expect(selectedRenderedAssetPaths(state)).toEqual([
      simpati.relative_path,
      manual.relative_path,
    ]);
  });

  it("keeps warnings from the inventory and resets to the initial state", () => {
    const withWarnings = renderedAssetSelectionReducer(
      INITIAL_RENDERED_ASSET_SELECTION,
      {
        type: "inventoryLoaded",
        assets: [manual],
        warnings: [{ name: "data.csv", code: "unsupported_file", message: "x" }],
      },
    );

    expect(withWarnings.warnings).toHaveLength(1);
    expect(
      renderedAssetSelectionReducer(withWarnings, { type: "reset" }),
    ).toBe(INITIAL_RENDERED_ASSET_SELECTION);
  });

  it("formats sources and sizes for display", () => {
    expect(renderedAssetSourceLabel("simpati")).toBe("SIMPATI");
    expect(renderedAssetSourceLabel("graphtec")).toBe("Graphtec");
    expect(renderedAssetSourceLabel("manual")).toBe("Manual");
    expect(renderedAssetSourceLabel("unknown")).toBe("Unknown");
    expect(renderedAssetSourceLabel("canoe")).toBe("CANoe");
    expect(renderedAssetSourceLabel("other")).toBe("other");
    expect(formatFileSize(512)).toBe("512 B");
    expect(formatFileSize(2048)).toBe("2.0 KB");
    expect(formatFileSize(3 * 1024 * 1024)).toBe("3.0 MB");
  });
});
