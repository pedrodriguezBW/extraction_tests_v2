import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { GraphtecAnalysis, GraphtecAnalysisView } from "./GraphtecAnalysis";
import {
  graphtecPanelReducer,
  initialGraphtecPanelState,
  type GraphtecPanelState,
} from "../services/graphtecChart";
import {
  buildGraphtecInspection,
  buildGraphtecInspectionWithData,
} from "../services/testFixtures";

const inspection = buildGraphtecInspectionWithData({
  warnings: ["No result record (PASS) was found in the file."],
  records_count: 73,
  limited_values_count: 20,
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
      "8 s",
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

  it("replaces the Start/End fields and the preview image by the interactive chart", () => {
    const markup = render(initialGraphtecPanelState(inspection));

    expect(markup).toContain('id="graphtec-title"');
    expect(markup).not.toContain('id="graphtec-time-min"');
    expect(markup).not.toContain('id="graphtec-time-max"');
    expect(markup).not.toContain("Preview chart");
    expect(markup).not.toContain("<img");
    expect(markup).toContain("<svg");
    expect(markup).toContain("Drag across the");
    expect(markup).toContain("Double-click the chart or use Reset");
  });

  it("draws both axes, the phases, limit markers and the result record", () => {
    const markup = render(initialGraphtecPanelState(inspection));

    expect(markup).toContain("Voltage [kV]</text>");
    expect(markup).toContain("Resistance [Mohm]</text>");
    expect(markup).toContain("graphtec-chart__axis--left");
    expect(markup).toContain("graphtec-chart__axis--right");
    expect(markup.match(/class="graphtec-chart__phase"/g)?.length).toBe(3);
    expect(markup.match(/class="graphtec-chart__limit"/g)?.length).toBe(2);
    // El registro PASS se marca en las dos series.
    expect(markup.match(/class="graphtec-chart__result"/g)?.length).toBe(2);
    expect(markup).toContain("Resistance limit (&gt; threshold)");
    expect(markup).toContain("Voltage - PASS record");
  });

  it("hides legend and phase separators when they are switched off", () => {
    const state = graphtecPanelReducer(initialGraphtecPanelState(inspection), {
      type: "formChanged",
      patch: { showLegend: false, showPhaseSeparators: false },
    });
    const markup = render(state);

    expect(markup).not.toContain("graphtec-chart__legend-item");
    expect(markup).not.toContain("graphtec-chart__phase");
  });

  it("draws only the visible interval when zoomed", () => {
    const state = graphtecPanelReducer(initialGraphtecPanelState(inspection), {
      type: "viewportChanged",
      viewport: { timeStart: 5, timeEnd: 8, yZoom: null },
    });
    const markup = render(state);

    expect(markup).not.toContain("graphtec-chart__limit");
    expect(markup).toContain("Zoomed view: 5 s to 8 s.");
  });

  it("uses a single left axis with one series", () => {
    const state = graphtecPanelReducer(initialGraphtecPanelState(inspection), {
      type: "seriesToggled",
      seriesId: "voltage",
      selected: false,
    });
    const markup = render(state);

    expect(markup).toContain("graphtec-chart__axis--left");
    expect(markup).not.toContain("graphtec-chart__axis--right");
  });

  it("enables Save chart without a preview step and disables it in read-only mode", () => {
    expect(button(render(initialGraphtecPanelState(inspection)), "Save chart")).not.toContain("disabled");
    expect(button(render(initialGraphtecPanelState(inspection), false, true), "Save chart")).toContain("disabled");
  });

  it("shows the saving and saved states", () => {
    const saving = graphtecPanelReducer(initialGraphtecPanelState(inspection), { type: "saveStarted" });
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
      patch: { series: [] },
    });
    const markup = render(state);

    expect(markup).toContain("Select at least one series.");
    expect(button(markup, "Save chart")).toContain("disabled");
  });

  it("disables every action while another operation runs", () => {
    const markup = render(initialGraphtecPanelState(inspection), true);

    expect(button(markup, "Save chart")).toContain("disabled");
    expect(button(markup, "Reset view")).toContain("disabled");
  });

  it("explains when the file has no records to draw", () => {
    const empty = buildGraphtecInspection();
    const markup = renderToStaticMarkup(
      <GraphtecAnalysisView
        inspection={empty}
        state={initialGraphtecPanelState(empty)}
        disabled={false}
        dispatch={() => undefined}
        onSave={() => undefined}
      />,
    );

    expect(markup).toContain("The file has no records to display.");
  });
});

describe("GraphtecAnalysis", () => {
  it("shows the interactive chart immediately without calling the backend", () => {
    let saves = 0;
    const markup = renderToStaticMarkup(
      <GraphtecAnalysis
        inspection={inspection}
        disabled={false}
        onSave={() => {
          saves += 1;
          return Promise.reject(new Error("not expected"));
        }}
      />,
    );

    expect(saves).toBe(0);
    expect(markup).toContain("<svg");
  });
});
