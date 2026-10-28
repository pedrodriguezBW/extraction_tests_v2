import { describe, expect, it } from "vitest";

import {
  canPreviewGraphtec,
  canSaveGraphtec,
  defaultGraphtecForm,
  GENERIC_GRAPHTEC_TITLE,
  graphtecFormKey,
  graphtecFormToSettings,
  graphtecPanelReducer,
  graphtecUnitsSummary,
  initialGraphtecPanelState,
  isGraphtecPreviewCurrent,
  shouldAutoRefreshPreview,
  validateGraphtecForm,
  type GraphtecPanelState,
} from "./graphtecChart";
import { buildGraphtecInspection, buildGraphtecPreview } from "./testFixtures";

const ir = buildGraphtecInspection();
const dcw = buildGraphtecInspection({
  test_types: ["DCW"],
  available_series: [
    { id: "voltage", label: "Voltage", unit: "kV", axis: "left", default_selected: true },
    { id: "current", label: "Current", unit: "uA", axis: "right", default_selected: true },
  ],
  default_title: "Graphtec DCW - Channel 1",
});

function previewed(state: GraphtecPanelState): GraphtecPanelState {
  const requested = graphtecPanelReducer(state, {
    type: "previewRequested",
    requestId: 1,
    formKey: graphtecFormKey(state.form),
  });
  return graphtecPanelReducer(requested, {
    type: "previewSucceeded",
    requestId: 1,
    response: buildGraphtecPreview(),
  });
}

describe("Graphtec chart defaults", () => {
  it("selects voltage and the measured quantity", () => {
    expect(defaultGraphtecForm(dcw).series).toEqual(["voltage", "current"]);
    expect(defaultGraphtecForm(ir).series).toEqual(["voltage", "resistance"]);
  });

  it("uses the content-based title, legend on and the full range", () => {
    const form = defaultGraphtecForm(ir);

    expect(form.title).toBe("Graphtec IR - Channel 1");
    expect(form.showLegend).toBe(true);
    expect(form.showPhaseSeparators).toBe(true);
    expect(form.timeMin).toBe("");
    expect(form.timeMax).toBe("");
    expect(graphtecFormToSettings(form)).toEqual({
      series: ["voltage", "resistance"],
      title: "Graphtec IR - Channel 1",
      show_legend: true,
      show_phase_separators: true,
      time_min: null,
      time_max: null,
    });
  });

  it("falls back to a generic title, never to the file name", () => {
    const form = defaultGraphtecForm(
      buildGraphtecInspection({ default_title: null, file_name: "IR_TC1_PASS.txt" }),
    );

    expect(form.title).toBe(GENERIC_GRAPHTEC_TITLE);
  });
});

describe("Graphtec chart form", () => {
  it("toggles series in a stable order", () => {
    let state = initialGraphtecPanelState(ir);
    state = graphtecPanelReducer(state, { type: "seriesToggled", seriesId: "voltage", selected: false });
    expect(state.form.series).toEqual(["resistance"]);
    state = graphtecPanelReducer(state, { type: "seriesToggled", seriesId: "voltage", selected: true });
    expect(state.form.series).toEqual(["voltage", "resistance"]);
  });

  it("requires at least one series", () => {
    const state = graphtecPanelReducer(initialGraphtecPanelState(ir), {
      type: "formChanged",
      patch: { series: [] },
    });

    expect(validateGraphtecForm(state.form, ir)).toBe("Select at least one series.");
    expect(canPreviewGraphtec(state, ir, false)).toBe(false);
  });

  it("edits the title", () => {
    const state = graphtecPanelReducer(initialGraphtecPanelState(ir), {
      type: "formChanged",
      patch: { title: "  Insulation  " },
    });

    expect(state.form.title).toBe("  Insulation  ");
    expect(graphtecFormToSettings(state.form).title).toBe("Insulation");
    expect(
      validateGraphtecForm({ ...state.form, title: "x".repeat(201) }, ir),
    ).toBe("The title cannot exceed 200 characters.");
  });

  it("converts the time range and rejects invalid ranges", () => {
    const form = { ...defaultGraphtecForm(ir), timeMin: "2.5", timeMax: "9" };

    expect(validateGraphtecForm(form, ir)).toBeNull();
    expect(graphtecFormToSettings(form).time_min).toBe(2.5);
    expect(graphtecFormToSettings(form).time_max).toBe(9);
    expect(validateGraphtecForm({ ...form, timeMin: "9", timeMax: "2" }, ir)).toBe(
      "The start time must be lower than the end time.",
    );
    expect(validateGraphtecForm({ ...form, timeMin: "-1" }, ir)).toBe(
      "Start and end must be non-negative numbers of seconds.",
    );
    expect(validateGraphtecForm({ ...form, timeMin: "abc" }, ir)).toBe(
      "Start and end must be non-negative numbers of seconds.",
    );
    expect(validateGraphtecForm({ ...form, timeMin: "20", timeMax: "" }, ir)).toBe(
      "The start time must be lower than the end time.",
    );
  });

  it("resets the configuration and the preview", () => {
    let state = previewed(initialGraphtecPanelState(ir));
    state = graphtecPanelReducer(state, { type: "formChanged", patch: { title: "Other", timeMin: "3" } });
    state = graphtecPanelReducer(state, { type: "reset", inspection: ir });

    expect(state).toEqual(initialGraphtecPanelState(ir));
  });
});

describe("Graphtec preview", () => {
  it("shows a loading state and then the preview", () => {
    const initial = initialGraphtecPanelState(ir);
    const loading = graphtecPanelReducer(initial, {
      type: "previewRequested",
      requestId: 1,
      formKey: graphtecFormKey(initial.form),
    });

    expect(loading.preview.status).toBe("loading");
    expect(canPreviewGraphtec(loading, ir, false)).toBe(false);
    expect(canSaveGraphtec(loading, ir, false)).toBe(false);

    const ready = graphtecPanelReducer(loading, {
      type: "previewSucceeded",
      requestId: 1,
      response: buildGraphtecPreview(),
    });
    expect(ready.preview.status).toBe("ready");
    expect(isGraphtecPreviewCurrent(ready)).toBe(true);
  });

  it("stores preview errors", () => {
    const initial = initialGraphtecPanelState(ir);
    const loading = graphtecPanelReducer(initial, {
      type: "previewRequested",
      requestId: 4,
      formKey: graphtecFormKey(initial.form),
    });
    const failed = graphtecPanelReducer(loading, {
      type: "previewFailed",
      requestId: 4,
      message: "The start time must be lower than the end time.",
    });

    expect(failed.preview.status).toBe("error");
    expect(failed.preview.error).toBe("The start time must be lower than the end time.");
    expect(canSaveGraphtec(failed, ir, false)).toBe(false);
  });

  it("ignores responses from previous requests", () => {
    const initial = initialGraphtecPanelState(ir);
    const loading = graphtecPanelReducer(initial, {
      type: "previewRequested",
      requestId: 2,
      formKey: graphtecFormKey(initial.form),
    });

    expect(
      graphtecPanelReducer(loading, {
        type: "previewSucceeded",
        requestId: 1,
        response: buildGraphtecPreview(),
      }),
    ).toBe(loading);
  });

  it("refreshes automatically after a change once a preview exists", () => {
    const initial = initialGraphtecPanelState(ir);
    expect(shouldAutoRefreshPreview(initial, ir)).toBe(false);

    const ready = previewed(initial);
    expect(shouldAutoRefreshPreview(ready, ir)).toBe(false);

    const changedSeries = graphtecPanelReducer(ready, {
      type: "seriesToggled",
      seriesId: "resistance",
      selected: false,
    });
    expect(isGraphtecPreviewCurrent(changedSeries)).toBe(false);
    expect(shouldAutoRefreshPreview(changedSeries, ir)).toBe(true);

    const changedRange = graphtecPanelReducer(ready, {
      type: "formChanged",
      patch: { timeMin: "2" },
    });
    expect(shouldAutoRefreshPreview(changedRange, ir)).toBe(true);

    const invalid = graphtecPanelReducer(ready, {
      type: "formChanged",
      patch: { timeMin: "9", timeMax: "1" },
    });
    expect(shouldAutoRefreshPreview(invalid, ir)).toBe(false);
  });
});

describe("Graphtec save", () => {
  it("is only enabled for a current preview", () => {
    const initial = initialGraphtecPanelState(ir);
    expect(canSaveGraphtec(initial, ir, false)).toBe(false);

    const ready = previewed(initial);
    expect(canSaveGraphtec(ready, ir, false)).toBe(true);
    expect(canSaveGraphtec(ready, ir, true)).toBe(false);

    const changed = graphtecPanelReducer(ready, { type: "formChanged", patch: { title: "New" } });
    expect(canSaveGraphtec(changed, ir, false)).toBe(false);
  });

  it("reports saving, saved and failed states", () => {
    const ready = previewed(initialGraphtecPanelState(ir));
    const saving = graphtecPanelReducer(ready, { type: "saveStarted" });
    expect(saving.save.status).toBe("saving");
    expect(canSaveGraphtec(saving, ir, false)).toBe(false);

    const saved = graphtecPanelReducer(saving, { type: "saveSucceeded", chartName: "graphtec_chart_01.png" });
    expect(saved.save.message).toBe("Chart saved as graphtec_chart_01.png.");

    const failed = graphtecPanelReducer(saving, { type: "saveFailed", message: "Disk full." });
    expect(failed.save).toEqual({ status: "error", message: "Disk full." });
  });
});

describe("Graphtec units", () => {
  it("summarizes original and normalized units", () => {
    expect(graphtecUnitsSummary(ir)).toEqual([
      "Voltage: kV",
      "Resistance: Mohm, Gohm → Mohm",
    ]);
  });
});
