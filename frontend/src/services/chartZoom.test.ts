import { describe, expect, it } from "vitest";

import {
  AXIS_LOCK_RATIO,
  MIN_ZOOM_DRAG,
  applyZoomSelection,
  classifyZoomSelection,
  clampToPlot,
  clientToSvgPoint,
  defaultValueRange,
  fullViewport,
  indexAtSvgX,
  isFullViewport,
  isInsidePlot,
  selectionRectangle,
  valueAtSvgY,
  valueTickDecimals,
  type ChartViewport,
  type PlotArea,
} from "./chartZoom";

// Área de trazado de 100 x 100 unidades para que las cuentas sean exactas.
const PLOT: PlotArea = { left: 100, top: 50, width: 100, height: 100 };
const Y_BOUNDS = { minimum: 0, maximum: 100 };
const LAST_INDEX = 100;

function full(): ChartViewport {
  return fullViewport(LAST_INDEX);
}

describe("classifyZoomSelection", () => {
  it("ignores clicks and very short drags", () => {
    expect(classifyZoomSelection({ x: 10, y: 10 }, { x: 10, y: 10 })).toBeNull();
    expect(
      classifyZoomSelection(
        { x: 10, y: 10 },
        { x: 10 + MIN_ZOOM_DRAG - 1, y: 10 + MIN_ZOOM_DRAG - 1 },
      ),
    ).toBeNull();
  });

  it("classifies a horizontal drag as a time zoom", () => {
    expect(classifyZoomSelection({ x: 0, y: 0 }, { x: 200, y: 3 })).toBe("x");
    // Una pequeña desviación vertical no convierte la selección en rectangular.
    expect(
      classifyZoomSelection({ x: 0, y: 0 }, { x: 200, y: 200 * AXIS_LOCK_RATIO }),
    ).toBe("x");
  });

  it("classifies a vertical drag as a value zoom", () => {
    expect(classifyZoomSelection({ x: 0, y: 0 }, { x: 2, y: 150 })).toBe("y");
    expect(classifyZoomSelection({ x: 0, y: 150 }, { x: 25, y: 0 })).toBe("y");
  });

  it("classifies a diagonal drag as a rectangular zoom", () => {
    expect(classifyZoomSelection({ x: 0, y: 0 }, { x: 120, y: 80 })).toBe("xy");
    expect(classifyZoomSelection({ x: 120, y: 80 }, { x: 0, y: 0 })).toBe("xy");
  });
});

describe("selectionRectangle", () => {
  it("spans the full plot height for a time selection", () => {
    expect(
      selectionRectangle({ x: 150, y: 70 }, { x: 120, y: 75 }, "x", PLOT),
    ).toEqual({ x: 120, y: 50, width: 30, height: 100 });
  });

  it("spans the full plot width for a value selection", () => {
    expect(
      selectionRectangle({ x: 150, y: 120 }, { x: 152, y: 80 }, "y", PLOT),
    ).toEqual({ x: 100, y: 80, width: 100, height: 40 });
  });

  it("follows the pointer for a rectangular selection", () => {
    expect(
      selectionRectangle({ x: 180, y: 140 }, { x: 120, y: 60 }, "xy", PLOT),
    ).toEqual({ x: 120, y: 60, width: 60, height: 80 });
  });
});

describe("coordinates", () => {
  it("converts pointer positions to SVG coordinates", () => {
    const bounds = { left: 10, top: 20, width: 500, height: 235 };
    expect(clientToSvgPoint(260, 137.5, bounds, 1000, 470)).toEqual({
      x: 500,
      y: 235,
    });
  });

  it("clamps points to the plot and detects points inside it", () => {
    expect(clampToPlot({ x: 0, y: 500 }, PLOT)).toEqual({ x: 100, y: 150 });
    expect(isInsidePlot({ x: 150, y: 100 }, PLOT)).toBe(true);
    expect(isInsidePlot({ x: 50, y: 100 }, PLOT)).toBe(false);
    expect(isInsidePlot({ x: 150, y: 20 }, PLOT)).toBe(false);
  });

  it("maps SVG coordinates to sample indexes and values", () => {
    const viewport: ChartViewport = { xStart: 20, xEnd: 60, yRange: null };
    expect(indexAtSvgX(100, viewport, PLOT)).toBe(20);
    expect(indexAtSvgX(150, viewport, PLOT)).toBe(40);
    expect(indexAtSvgX(200, viewport, PLOT)).toBe(60);
    expect(valueAtSvgY(50, Y_BOUNDS, PLOT)).toBe(100);
    expect(valueAtSvgY(125, Y_BOUNDS, PLOT)).toBe(25);
    expect(valueAtSvgY(150, Y_BOUNDS, PLOT)).toBe(0);
  });
});

describe("applyZoomSelection", () => {
  it("narrows only the time interval for a horizontal selection", () => {
    const next = applyZoomSelection(
      full(),
      { x: 120, y: 100 },
      { x: 160, y: 102 },
      PLOT,
      Y_BOUNDS,
      LAST_INDEX,
    );
    // El eje Y conserva el rango por defecto: no se reajusta al intervalo.
    expect(next).toEqual({ xStart: 20, xEnd: 60, yRange: null });
  });

  it("keeps a value range fixed by the user when zooming in time", () => {
    const viewport: ChartViewport = {
      xStart: 0,
      xEnd: 100,
      yRange: { minimum: 10, maximum: 30 },
    };
    const next = applyZoomSelection(
      viewport,
      { x: 150, y: 90 },
      { x: 200, y: 90 },
      PLOT,
      viewport.yRange!,
      LAST_INDEX,
    );
    expect(next).toEqual({
      xStart: 50,
      xEnd: 100,
      yRange: { minimum: 10, maximum: 30 },
    });
  });

  it("sets only the value range for a vertical selection", () => {
    const viewport: ChartViewport = { xStart: 10, xEnd: 40, yRange: null };
    const next = applyZoomSelection(
      viewport,
      { x: 150, y: 70 },
      { x: 152, y: 110 },
      PLOT,
      Y_BOUNDS,
      LAST_INDEX,
    );
    expect(next).toEqual({
      xStart: 10,
      xEnd: 40,
      yRange: { minimum: 40, maximum: 80 },
    });
  });

  it("adjusts both axes for a rectangular selection", () => {
    const next = applyZoomSelection(
      full(),
      { x: 175, y: 140 },
      { x: 125, y: 60 },
      PLOT,
      Y_BOUNDS,
      LAST_INDEX,
    );
    expect(next).toEqual({
      xStart: 25,
      xEnd: 75,
      yRange: { minimum: 10, maximum: 90 },
    });
  });

  it("zooms relative to the current view", () => {
    const viewport: ChartViewport = {
      xStart: 20,
      xEnd: 60,
      yRange: { minimum: 10, maximum: 30 },
    };
    const next = applyZoomSelection(
      viewport,
      { x: 150, y: 50 },
      { x: 200, y: 100 },
      PLOT,
      viewport.yRange!,
      LAST_INDEX,
    );
    expect(next).toEqual({
      xStart: 40,
      xEnd: 60,
      yRange: { minimum: 20, maximum: 30 },
    });
  });

  it("limits selections that leave the plot area", () => {
    const next = applyZoomSelection(
      full(),
      { x: 150, y: 100 },
      { x: 400, y: 101 },
      PLOT,
      Y_BOUNDS,
      LAST_INDEX,
    );
    expect(next).toEqual({ xStart: 50, xEnd: 100, yRange: null });
  });

  it("ignores clicks and selections narrower than two samples", () => {
    expect(
      applyZoomSelection(
        full(),
        { x: 150, y: 100 },
        { x: 152, y: 101 },
        PLOT,
        Y_BOUNDS,
        LAST_INDEX,
      ),
    ).toBeNull();
    const narrow: ChartViewport = { xStart: 10, xEnd: 11, yRange: null };
    expect(
      applyZoomSelection(
        narrow,
        { x: 110, y: 100 },
        { x: 140, y: 100 },
        PLOT,
        Y_BOUNDS,
        LAST_INDEX,
      ),
    ).toBeNull();
  });
});

describe("full view", () => {
  it("covers every sample with an automatic value axis", () => {
    expect(fullViewport(LAST_INDEX)).toEqual({
      xStart: 0,
      xEnd: LAST_INDEX,
      yRange: null,
    });
    expect(fullViewport(-1)).toEqual({ xStart: 0, xEnd: 0, yRange: null });
    expect(isFullViewport(full(), LAST_INDEX)).toBe(true);
    expect(
      isFullViewport({ xStart: 0, xEnd: LAST_INDEX, yRange: Y_BOUNDS }, LAST_INDEX),
    ).toBe(false);
  });
});

describe("valueTickDecimals", () => {
  it("keeps one decimal for the usual ranges", () => {
    expect(valueTickDecimals({ minimum: -40, maximum: 150 }, 4)).toBe(1);
    expect(valueTickDecimals({ minimum: 20, maximum: 22 }, 4)).toBe(1);
  });

  it("adds decimals for narrow zoomed ranges", () => {
    expect(valueTickDecimals({ minimum: 20, maximum: 20.2 }, 4)).toBe(2);
    expect(valueTickDecimals({ minimum: 20, maximum: 20.02 }, 4)).toBe(3);
  });
});

describe("defaultValueRange", () => {
  it("uses every value of the series, not only the visible interval", () => {
    const range = defaultValueRange([
      { values: [10, null, 60] },
      { values: [35, Number.NaN, 110] },
    ]);
    // Mínimo 10, máximo 110 y un margen del 8 % del intervalo (8).
    expect(range.minimum).toBe(2);
    expect(range.maximum).toBe(118);
  });

  it("keeps a visible range for flat or empty series", () => {
    expect(defaultValueRange([{ values: [5, 5] }])).toEqual({
      minimum: 4,
      maximum: 6,
    });
    expect(defaultValueRange([])).toEqual({ minimum: -1, maximum: 1 });
    expect(defaultValueRange([{ values: [null] }])).toEqual({
      minimum: -1,
      maximum: 1,
    });
  });
});
