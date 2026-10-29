import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { RenderedAssets } from "./RenderedAssets";
import {
  INITIAL_RENDERED_ASSET_SELECTION,
  renderedAssetSelectionReducer,
  type RenderedAssetSelectionState,
} from "../services/renderedAssetSelection";
import { buildRenderedAsset } from "../services/testFixtures";

const simpati = buildRenderedAsset("chart03_simpati_acquisition_01.png", "simpati");
const graphtec = buildRenderedAsset("graphtec_chart_01.png", "graphtec");
const manual = buildRenderedAsset("manual_photo.jpg", "manual");

function loaded(assets = [simpati, graphtec, manual]): RenderedAssetSelectionState {
  return renderedAssetSelectionReducer(INITIAL_RENDERED_ASSET_SELECTION, {
    type: "inventoryLoaded",
    assets,
  });
}

function render(
  state: RenderedAssetSelectionState,
  options: { loading?: boolean; deleting?: string | null; disabled?: boolean } = {},
): string {
  return renderToStaticMarkup(
    <RenderedAssets
      state={state}
      loading={options.loading ?? false}
      deletingRelativePath={options.deleting ?? null}
      disabled={options.disabled ?? false}
      getImageUrl={(path) => `http://backend/rendered-asset?relative_path=${path}`}
      onToggle={() => undefined}
      onSelectAll={() => undefined}
      onClearSelection={() => undefined}
      onOpen={() => Promise.reject(new Error("not used"))}
      onDelete={() => undefined}
    />,
  );
}

function item(markup: string, name: string): string {
  const index = markup.indexOf(`<strong>${name}</strong>`);
  if (index < 0) {
    throw new Error(`Item not found: ${name}`);
  }
  const start = markup.lastIndexOf("<li", index);
  const end = markup.indexOf("</li>", index);
  return markup.slice(start, end);
}

function checkbox(markup: string, name: string): string {
  const fragment = item(markup, name);
  const start = fragment.indexOf('<input');
  const end = fragment.indexOf("/>", start);
  return fragment.slice(start, end);
}

function button(markup: string, label: string): string {
  const end = markup.indexOf(`>${label}</button>`);
  if (end < 0) {
    throw new Error(`Button not found: ${label}`);
  }
  return markup.slice(markup.lastIndexOf("<button", end), end);
}

describe("RenderedAssets", () => {
  it("renders the generic report images section", () => {
    const markup = render(loaded());

    expect(markup).toContain("Report images");
    expect(markup).toContain("Images saved in 04_Report/_RenderedAssets");
    expect(markup).toContain('aria-label="Report images"');
    expect(markup).not.toContain("SIMPATI charts");
  });

  it("lists SIMPATI, Graphtec and manual images with their source", () => {
    const markup = render(loaded());

    expect(item(markup, simpati.name)).toContain(">SIMPATI<");
    expect(item(markup, graphtec.name)).toContain(">Graphtec<");
    expect(item(markup, manual.name)).toContain(">Manual<");
    expect(markup).toContain(
      `relative_path=${manual.relative_path}`,
    );
    expect(markup).toContain(`<code title="${manual.relative_path}">`);
  });

  it("checks every image by default and exposes an accessible checkbox", () => {
    const markup = render(loaded());

    for (const asset of [simpati, graphtec, manual]) {
      const input = checkbox(markup, asset.name);
      expect(input).toContain('type="checkbox"');
      expect(input).toContain('checked=""');
      expect(input).toContain(`aria-label="Include ${asset.name} in the report"`);
      expect(input).toContain('id="');
    }
    expect(markup).toContain("rendered-assets__item--selected");
    expect(markup).toContain("3 of 3 images selected for the report.");
  });

  it("shows an unchecked image as not included", () => {
    const state = renderedAssetSelectionReducer(loaded(), {
      type: "toggled",
      relativePath: graphtec.relative_path,
    });

    const markup = render(state);

    expect(checkbox(markup, graphtec.name)).not.toContain('checked=""');
    expect(item(markup, graphtec.name)).toContain("rendered-assets__item--unselected");
    expect(item(markup, graphtec.name)).toContain("Not included");
    expect(item(markup, simpati.name)).toContain("Included in the report");
    expect(markup).toContain("2 of 3 images selected for the report.");
  });

  it("offers Select all and Clear selection", () => {
    const markup = render(loaded());

    expect(button(markup, "Select all")).toContain("disabled");
    expect(button(markup, "Clear selection")).not.toContain("disabled");

    const cleared = render(
      renderedAssetSelectionReducer(loaded(), { type: "clearSelection" }),
    );

    expect(button(cleared, "Select all")).not.toContain("disabled");
    expect(button(cleared, "Clear selection")).toContain("disabled");
    expect(cleared).toContain(
      "No rendered images are selected. The report will be generated without them.",
    );
  });

  it("explains the empty inventory", () => {
    const markup = render(loaded([]));

    expect(markup).toContain(
      "No rendered images were found. The report can still be generated.",
    );
    expect(markup).not.toContain("Select all");
    expect(markup).not.toContain("<li");
  });

  it("shows the loading state", () => {
    const markup = render(loaded(), { loading: true });

    expect(markup).toContain("Refreshing report images...");
    expect(markup).not.toContain("<li");
  });

  it("shows the deleting state for one image", () => {
    const markup = render(loaded(), { deleting: simpati.relative_path });

    const deleting = item(markup, simpati.name);
    expect(deleting).toContain("rendered-assets__item--deleting");
    expect(deleting).toContain('aria-busy="true"');
    expect(deleting).toContain("Deleting...");
    expect(item(markup, graphtec.name)).not.toContain("Deleting...");
  });

  it("marks images as unavailable while another operation runs", () => {
    const markup = render(loaded(), { disabled: true });

    expect(item(markup, graphtec.name)).toContain("rendered-assets__item--unavailable");
    expect(checkbox(markup, graphtec.name)).toContain("disabled");
  });

  it("offers open and delete actions per image", () => {
    const markup = render(loaded());

    expect(markup.split(">Open image</button>").length - 1).toBe(3);
    expect(markup.split(">Delete</button>").length - 1).toBe(3);
    expect(markup).toContain(`aria-label="Open ${manual.name}"`);
    expect(markup).toContain(`alt="Preview of ${manual.name}"`);
  });

  it("lists files that are not available for the report", () => {
    const state = renderedAssetSelectionReducer(INITIAL_RENDERED_ASSET_SELECTION, {
      type: "inventoryLoaded",
      assets: [manual],
      warnings: [
        {
          name: "data.csv",
          code: "unsupported_file",
          message: "data.csv is not a PNG, JPG or JPEG image and is not available for the report.",
        },
      ],
    });

    const markup = render(state);

    expect(markup).toContain("Files not available for the report");
    expect(markup).toContain("data.csv is not a PNG, JPG or JPEG image");
  });
});
