import { describe, expect, it } from "vitest";

import {
  GENERIC_GRAPHTEC_TITLE,
  applyGraphtecZoom,
  canSaveGraphtec,
  defaultGraphtecForm,
  defaultGraphtecSeriesRange,
  fullGraphtecViewport,
  graphtecPanelReducer,
  graphtecTimeDomain,
  graphtecUnitsSummary,
  graphtecViewToSettings,
  initialGraphtecPanelState,
  isFullGraphtecViewport,
  niceTicks,
  validateGraphtecForm,
  visibleGraphtecRanges,
} from "./graphtecChart";
import type { PlotArea } from "./chartZoom";
import {
  buildGraphtecInspection,
  buildGraphtecInspectionWithData,
} from "./testFixtures";

const ir = buildGraphtecInspectionWithData();
const dcw = buildGraphtecInspection({
  test_types: ["DCW"],
  available_series: [
    { id: "voltage", label: "Voltage", unit: "kV", axis: "left", default_selected: true },
    { id: "current", label: "Current", unit: "uA", axis: "right", default_selected: true },
  ],
  default_title: "Graphtec DCW - Channel 1",
});

// Área de trazado sencilla: 1 unidad SVG = 1 % del ancho/alto.
const plot: PlotArea = { left: 0, top: 0, width: 100, height: 100 };

/** Coordenada X del SVG para un tiempo con la vista completa (0-8 s). */
function xFor(time: number): number {
  const domain = graphtecTimeDomain(fullGraphtecViewport(ir));
  return ((time - domain.minimum) / (domain.maximum - domain.minimum)) * 100;
}

describe("Graphtec chart defaults", () => {
  it("selects voltage and the measured quantity", () => {
    expect(defaultGraphtecForm(dcw).series).toEqual(["voltage", "current"]);
    expect(defaultGraphtecForm(ir).series).toEqual(["voltage", "resistance"]);
  });

  it("uses the content-based title, legend on and the full view", () => {
    const state = initialGraphtecPanelState(ir);

    expect(state.form).toEqual({
      series: ["voltage", "resistance"],
      title: "Graphtec IR - Channel 1",
      showLegend: true,
      showPhaseSeparators: true,
    });
    expect(state.viewport).toEqual({ timeStart: 0, timeEnd: 8, yZoom: null });
    expect(isFullGraphtecViewport(state.viewport, ir)).toBe(true);
  });

  it("falls back to a generic title, never to the file name", () => {
    const form = defaultGraphtecForm(
      buildGraphtecInspection({ default_title: null, file_name: "IR_TC1_PASS.txt" }),
    );

    expect(form.title).toBe(GENERIC_GRAPHTEC_TITLE);
  });

  it("enables saving straight away, without a preview step", () => {
    const state = initialGraphtecPanelState(ir);

    expect(canSaveGraphtec(state, ir, false)).toBe(true);
    expect(canSaveGraphtec(state, ir, true)).toBe(false);
    expect(
      canSaveGraphtec(initialGraphtecPanelState(buildGraphtecInspection()), buildGraphtecInspection(), false),
    ).toBe(false);
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
    expect(canSaveGraphtec(state, ir, false)).toBe(false);
  });

  it("trims the title and limits its length", () => {
    const state = graphtecPanelReducer(initialGraphtecPanelState(ir), {
      type: "formChanged",
      patch: { title: "  Insulation  " },
    });

    expect(graphtecViewToSettings(state, ir).title).toBe("Insulation");
    expect(
      validateGraphtecForm({ ...state.form, title: "x".repeat(201) }, ir),
    ).toBe("The title cannot exceed 200 characters.");
  });
});

describe("Graphtec zoom", () => {
  it("uses the whole acquisition for the default value range of each axis", () => {
    expect(defaultGraphtecSeriesRange(ir, "voltage")).toEqual({
      minimum: -0.08,
      maximum: 1.08,
    });
    const resistance = defaultGraphtecSeriesRange(ir, "resistance");
    expect(resistance.minimum).toBeCloseTo(100 - 49900 * 0.08);
    expect(resistance.maximum).toBeCloseTo(50000 + 49900 * 0.08);
  });

  it("zooms the time interval with a horizontal drag without touching Y", () => {
    const state = initialGraphtecPanelState(ir);
    const next = applyGraphtecZoom(
      state.viewport,
      { x: xFor(2), y: 50 },
      { x: xFor(6), y: 52 },
      plot,
      ir,
    );

    expect(next?.timeStart).toBeCloseTo(2);
    expect(next?.timeEnd).toBeCloseTo(6);
    expect(next?.yZoom).toBeNull();
  });

  it("zooms both value axes together with a vertical drag", () => {
    const state = initialGraphtecPanelState(ir);
    const next = applyGraphtecZoom(state.viewport, { x: 50, y: 25 }, { x: 51, y: 75 }, plot, ir);

    expect(next).not.toBeNull();
    expect(next?.timeStart).toBe(0);
    expect(next?.timeEnd).toBe(8);
    expect(next?.yZoom?.low).toBeCloseTo(0.25);
    expect(next?.yZoom?.high).toBeCloseTo(0.75);

    const zoomed = graphtecPanelReducer(state, { type: "viewportChanged", viewport: next! });
    const ranges = visibleGraphtecRanges(zoomed, ir);
    expect(ranges.voltage?.minimum).toBeCloseTo(-0.08 + 0.25 * 1.16);
    expect(ranges.voltage?.maximum).toBeCloseTo(-0.08 + 0.75 * 1.16);
    const full = defaultGraphtecSeriesRange(ir, "resistance");
    const span = full.maximum - full.minimum;
    expect(ranges.resistance?.minimum).toBeCloseTo(full.minimum + 0.25 * span);
    expect(ranges.resistance?.maximum).toBeCloseTo(full.minimum + 0.75 * span);
  });

  it("nests vertical zooms inside the current value zoom", () => {
    const first = applyGraphtecZoom(fullGraphtecViewport(ir), { x: 50, y: 0 }, { x: 51, y: 50 }, plot, ir)!;
    const second = applyGraphtecZoom(first, { x: 50, y: 50 }, { x: 51, y: 100 }, plot, ir)!;

    expect(first.yZoom).toEqual({ low: 0.5, high: 1 });
    expect(second.yZoom?.low).toBeCloseTo(0.5);
    expect(second.yZoom?.high).toBeCloseTo(0.75);
  });

  it("zooms both axes with a diagonal drag", () => {
    const next = applyGraphtecZoom(
      fullGraphtecViewport(ir),
      { x: xFor(1), y: 10 },
      { x: xFor(7), y: 60 },
      plot,
      ir,
    );

    expect(next?.timeStart).toBeCloseTo(1);
    expect(next?.timeEnd).toBeCloseTo(7);
    expect(next?.yZoom?.low).toBeCloseTo(0.4);
    expect(next?.yZoom?.high).toBeCloseTo(0.9);
  });

  it("ignores clicks and intervals with fewer than two records", () => {
    const viewport = fullGraphtecViewport(ir);

    expect(applyGraphtecZoom(viewport, { x: 40, y: 40 }, { x: 43, y: 42 }, plot, ir)).toBeNull();
    expect(
      applyGraphtecZoom(viewport, { x: xFor(2.2), y: 40 }, { x: xFor(2.8), y: 40 }, plot, ir),
    ).toBeNull();
  });

  it("restores the full view on double-click and on Reset view", () => {
    let state = initialGraphtecPanelState(ir);
    state = graphtecPanelReducer(state, {
      type: "viewportChanged",
      viewport: { timeStart: 2, timeEnd: 6, yZoom: { low: 0.2, high: 0.4 } },
    });
    state = graphtecPanelReducer(state, { type: "seriesToggled", seriesId: "voltage", selected: false });

    const zoomOnly = graphtecPanelReducer(state, { type: "zoomReset", inspection: ir });
    expect(zoomOnly.viewport).toEqual(fullGraphtecViewport(ir));
    expect(zoomOnly.form.series).toEqual(["resistance"]);

    expect(graphtecPanelReducer(state, { type: "reset", inspection: ir })).toEqual(
      initialGraphtecPanelState(ir),
    );
  });
});

describe("Graphtec saved view", () => {
  it("sends the full range and the displayed value ranges for the full view", () => {
    const settings = graphtecViewToSettings(initialGraphtecPanelState(ir), ir);

    expect(settings.time_min).toBeNull();
    expect(settings.time_max).toBeNull();
    expect(settings.series).toEqual(["voltage", "resistance"]);
    expect(settings.value_ranges?.voltage).toEqual({ minimum: -0.08, maximum: 1.08 });
    expect(Object.keys(settings.value_ranges ?? {})).toEqual(["voltage", "resistance"]);
  });

  it("sends exactly the zoomed interval and value ranges", () => {
    let state = initialGraphtecPanelState(ir);
    state = graphtecPanelReducer(state, {
      type: "viewportChanged",
      viewport: { timeStart: 2, timeEnd: 6, yZoom: { low: 0.5, high: 1 } },
    });
    state = graphtecPanelReducer(state, { type: "seriesToggled", seriesId: "resistance", selected: false });
    const settings = graphtecViewToSettings(state, ir);

    expect(settings.time_min).toBe(2);
    expect(settings.time_max).toBe(6);
    expect(settings.series).toEqual(["voltage"]);
    expect(settings.value_ranges).toEqual({
      voltage: { minimum: expect.closeTo(0.5, 6), maximum: expect.closeTo(1.08, 6) },
    });
  });

  it("clears the save message when the view changes", () => {
    let state = graphtecPanelReducer(initialGraphtecPanelState(ir), { type: "saveStarted" });
    state = graphtecPanelReducer(state, { type: "saveSucceeded", chartName: "graphtec_chart_01.png" });
    expect(state.save.message).toBe("Chart saved as graphtec_chart_01.png.");

    state = graphtecPanelReducer(state, {
      type: "viewportChanged",
      viewport: { timeStart: 1, timeEnd: 3, yZoom: null },
    });
    expect(state.save).toEqual({ status: "idle", message: null });
  });

  it("reports saving and failed states", () => {
    const saving = graphtecPanelReducer(initialGraphtecPanelState(ir), { type: "saveStarted" });
    expect(saving.save.status).toBe("saving");
    expect(canSaveGraphtec(saving, ir, false)).toBe(false);

    const failed = graphtecPanelReducer(saving, { type: "saveFailed", message: "Disk full." });
    expect(failed.save).toEqual({ status: "error", message: "Disk full." });
  });
});

describe("Graphtec axes and units", () => {
  it("places round ticks whose labels match their position", () => {
    expect(niceTicks({ minimum: 0, maximum: 14.8 }, 5)).toEqual({
      values: [0, 2, 4, 6, 8, 10, 12, 14],
      decimals: 0,
    });
    expect(niceTicks({ minimum: -0.08, maximum: 1.08 }, 4)).toEqual({
      values: [0, 0.2, 0.4, 0.6, 0.8, 1],
      decimals: 1,
    });
    expect(niceTicks({ minimum: -3892, maximum: 53992 }, 4).values).toEqual([
      0, 10000, 20000, 30000, 40000, 50000,
    ]);
    expect(niceTicks({ minimum: 2.019, maximum: 2.031 }, 5)).toEqual({
      values: [2.02, 2.022, 2.024, 2.026, 2.028, 2.03],
      decimals: 3,
    });
  });

  it("summarizes original and normalized units", () => {
    expect(graphtecUnitsSummary(ir)).toEqual([
      "Voltage: kV",
      "Resistance: Mohm, Gohm → Mohm",
    ]);
  });
});
