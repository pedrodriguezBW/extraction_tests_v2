import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { GraphtecAnalysis, GraphtecAnalysisView } from "./GraphtecAnalysis";
import {
  graphtecFormKey,
  graphtecPanelReducer,
  initialGraphtecPanelState,
  type GraphtecPanelState,
} from "../services/graphtecChart";
import {
  buildGraphtecInspection,
  buildGraphtecPreview,
} from "../services/testFixtures";

const inspection = buildGraphtecInspection({
  warnings: ["No result record (PASS) was found in the file."],
});

function render(
  state: GraphtecPanelState,
  disabled = false,
  saveDisabled = false,
): string {
  return renderToStaticMarkup(
    <GraphtecAnalysisView
      inspection={inspection}
      state={state}
      disabled={disabled}
      saveDisabled={saveDisabled}
      dispatch={() => undefined}
      onPreview={() => undefined}
      onSave={() => undefined}
    />,
  );
}

function button(markup: string, label: string): string {
  const end = markup.indexOf(`>${label}</button>`);
  if (end < 0) {
    throw new Error(`Button not found: ${label}`);
  }
  return markup.slice(markup.lastIndexOf("<button", end), end);
}

function ready(): GraphtecPanelState {
  const initial = initialGraphtecPanelState(inspection);
  const loading = graphtecPanelReducer(initial, {
    type: "previewRequested",
    requestId: 1,
    formKey: graphtecFormKey(initial.form),
  });
  return graphtecPanelReducer(loading, {
    type: "previewSucceeded",
    requestId: 1,
    response: buildGraphtecPreview(),
  });
}

describe("GraphtecAnalysisView", () => {
  it("renders the analysis summary", () => {
    const markup = render(initialGraphtecPanelState(inspection));

    for (const text of [
      "Graphtec analyzed",
      "run_01.csv",
      "Graphtec TXT (tab-separated)",
      "<dt>Test type</dt><dd>IR</dd>",
      "<dt>Records</dt><dd>73</dd>",
      "<dt>Final result</dt><dd>PASS</dd>",
      "<dt>Phases</dt><dd>R, T, D</dd>",
      "Voltage [kV], Resistance [Mohm]",
      "Resistance: Mohm, Gohm → Mohm",
      "14.8 s",
      "No result record (PASS) was found in the file.",
      "20 limited values",
    ]) {
      expect(markup).toContain(text);
    }
  });

  it("shows the series selector with the default selection", () => {
    const markup = render(initialGraphtecPanelState(inspection));

    expect(markup).toContain('checked="" value="voltage"');
    expect(markup).toContain('checked="" value="resistance"');
    expect(markup).not.toContain('value="current"');
  });

  it("shows an editable title and the time range inputs", () => {
    const markup = render(initialGraphtecPanelState(inspection));

    expect(markup).toContain('id="graphtec-title"');
    expect(markup).toContain('value="Graphtec IR - Channel 1"');
    expect(markup).toContain('id="graphtec-time-min"');
    expect(markup).toContain('placeholder="0"');
    expect(markup).toContain('id="graphtec-time-max"');
    expect(markup).toContain('placeholder="14.8"');
    expect(markup).toContain("X axis: Elapsed time [s]");
  });

  it("enables Preview chart and keeps Save chart disabled before a preview", () => {
    const markup = render(initialGraphtecPanelState(inspection));

    expect(button(markup, "Preview chart")).not.toContain("disabled");
    expect(button(markup, "Save chart")).toContain("disabled");
    expect(markup).toContain("Preview the chart to enable saving.");
  });

  it("shows the loading state", () => {
    const initial = initialGraphtecPanelState(inspection);
    const loading = graphtecPanelReducer(initial, {
      type: "previewRequested",
      requestId: 1,
      formKey: graphtecFormKey(initial.form),
    });
    const markup = render(loading);

    expect(markup).toContain('aria-busy="true"');
    expect(button(markup, "Generating preview...")).toContain("disabled");
  });

  it("shows the preview with axes and limit note, and enables Save chart", () => {
    const markup = render(ready());

    expect(markup).toContain('src="data:image/png;base64,iVBORw0KGgo="');
    expect(markup).toContain("Voltage [kV] | Resistance [Mohm]");
    expect(markup).toContain(
      "Limit marker indicates a value greater than the displayed threshold.",
    );
    expect(button(markup, "Save chart")).not.toContain("disabled");
  });

  it("keeps preview available while disabling saves in read-only mode", () => {
    const markup = render(ready(), false, true);

    expect(button(markup, "Preview chart")).not.toContain("disabled");
    expect(button(markup, "Save chart")).toContain("disabled");
  });

  it("shows preview errors", () => {
    const state = graphtecPanelReducer(
      graphtecPanelReducer(initialGraphtecPanelState(inspection), {
        type: "previewRequested",
        requestId: 1,
        formKey: "x",
      }),
      { type: "previewFailed", requestId: 1, message: "No records fall inside the selected time range." },
    );
    const markup = render(state);

    expect(markup).toContain('role="alert"');
    expect(markup).toContain("No records fall inside the selected time range.");
  });

  it("shows the saving and saved states", () => {
    const saving = graphtecPanelReducer(ready(), { type: "saveStarted" });
    expect(button(render(saving), "Saving chart...")).toContain("disabled");

    const saved = graphtecPanelReducer(saving, {
      type: "saveSucceeded",
      chartName: "graphtec_chart_01.png",
    });
    const markup = render(saved);
    expect(markup).toContain("Chart saved as graphtec_chart_01.png.");
    expect(markup).toContain("It is not added to the PowerPoint automatically.");
  });

  it("shows validation errors", () => {
    const state = graphtecPanelReducer(initialGraphtecPanelState(inspection), {
      type: "formChanged",
      patch: { timeMin: "10", timeMax: "2" },
    });
    const markup = render(state);

    expect(markup).toContain("The start time must be lower than the end time.");
    expect(button(markup, "Preview chart")).toContain("disabled");
  });

  it("disables every action while another operation runs", () => {
    const markup = render(ready(), true);

    expect(button(markup, "Preview chart")).toContain("disabled");
    expect(button(markup, "Save chart")).toContain("disabled");
    expect(button(markup, "Reset")).toContain("disabled");
  });
});

describe("GraphtecAnalysis", () => {
  it("starts from the defaults without requesting a preview", () => {
    let previews = 0;
    const markup = renderToStaticMarkup(
      <GraphtecAnalysis
        inspection={inspection}
        disabled={false}
        onPreview={() => {
          previews += 1;
          return Promise.resolve(buildGraphtecPreview());
        }}
        onSave={() => Promise.reject(new Error("not expected"))}
      />,
    );

    expect(previews).toBe(0);
    expect(markup).toContain("Configure the chart and select Preview chart.");
  });
});
