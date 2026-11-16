import { describe, expect, it } from "vitest";

import {
  EXPORT_ASPECT_RATIO,
  EXPORT_FONT_PT,
  EXPORT_HEIGHT_PX,
  EXPORT_LINE_PT,
  EXPORT_MAX_X_TICKS,
  EXPORT_VIEW_HEIGHT,
  EXPORT_VIEW_WIDTH,
  EXPORT_WIDTH_PX,
  UNITS_PER_PT,
  buildChartExportSvg,
  estimateTextWidth,
  layoutChartExport,
  scaleDash,
  timestampTickLines,
  type ChartExportModel,
  type ExportSeries,
} from "./chartExport";
import { defaultValueRange, fullViewport } from "./chartZoom";
import type { ToleranceResult } from "../types/tolerances";

// Una muestra por hora durante diez días: fechas largas en el eje X.
const TIMESTAMPS = Array.from({ length: 241 }, (_, index) =>
  new Date(Date.UTC(2024, 1, 22, 10 + index)).toISOString(),
);

function series(label: string, offset: number, extra: Partial<ExportSeries> = {}): ExportSeries {
  return {
    id: label,
    label,
    values: TIMESTAMPS.map((_, index) => offset + Math.sin(index / 10) * 20),
    color: "#005a9c",
    primary: true,
    ...extra,
  };
}

function model(overrides: Partial<ChartExportModel> = {}): ChartExportModel {
  const channels = overrides.series ?? [
    series("Chamber temperature", 20),
    series("Chamber setpoint", 20, { dash: "9 6" }),
  ];
  const viewport = overrides.viewport ?? fullViewport(TIMESTAMPS.length - 1);
  return {
    title: "SIMPATI x01 · 240222_11371_Aging.x01",
    valueAxisLabel: "Value",
    timestamps: TIMESTAMPS,
    series: channels,
    viewport,
    yBounds: viewport.yRange ?? defaultValueRange(channels),
    ...overrides,
  };
}

describe("export format", () => {
  it("conserva exactamente el SVG cuando las tolerancias están desactivadas", () => {
    expect(buildChartExportSvg(model())).toBe(buildChartExportSvg(model({tolerances: null})));
  });

  it("exporta bandas, excursiones y severidades sin perder una excursión entre muestras del visor", () => {
    const tolerances: ToleranceResult = {status: "NOK", channel: "actual", reference: "setpoint", scope: "full_acquisition",
      out_of_tolerance_segments: 1, ta_c: -40, tb_c: 85, t1_minutes: 30, cycles: 2,
      plateaus: [{start: TIMESTAMPS[2], end: TIMESTAMPS[20], setpoint_c: 20}],
      excursions: [[[new Date(Date.parse(TIMESTAMPS[5]) + 30000).toISOString(), 23]]], warnings: []};
    const svg = buildChartExportSvg(model({tolerances,
      series: [series("Chamber temperature", 20, {id: "actual"})]}));
    expect(svg).toContain("Tolerancias: NOK (1 tramo fuera)");
    expect(svg).toContain("TA medida: -40 °C");
    expect(svg).not.toContain("Estabilización");
    expect(svg).not.toContain("Rampas");
    expect(svg).toContain("Adquisición completa");
    expect(svg).toContain('fill="#58a881"');
    expect(svg).toContain('fill="#d72631"');
    const marker = /<circle cx="([^"]+)" cy="([^"]+)"/.exec(svg);
    const measuredCurve = /<polyline points="([^"]+)"[^>]*stroke="#005a9c"/.exec(svg);
    expect(marker).not.toBeNull();
    expect(measuredCurve?.[1].split(" ")).toContain(`${marker?.[1]},${marker?.[2]}`);
    expect(svg).not.toContain("NaN");
    expect(layoutChartExport(model({tolerances})).plot.top).toBeGreaterThan(layoutChartExport(model()).plot.top);
  });
  it("uses 1800 × 1125 px with a 1.6:1 ratio", () => {
    expect(EXPORT_WIDTH_PX).toBe(1800);
    expect(EXPORT_HEIGHT_PX).toBe(1125);
    expect(EXPORT_ASPECT_RATIO).toBe(1.6);
    expect(EXPORT_VIEW_WIDTH / EXPORT_VIEW_HEIGHT).toBe(1.6);
    const svg = buildChartExportSvg(model());
    expect(svg).toContain('width="1800" height="1125"');
    expect(svg).toContain('viewBox="0 0 1000 625"');
  });

  it("draws text and lines with the enlarged report sizes", () => {
    const svg = buildChartExportSvg(model());
    const tick = Math.round(EXPORT_FONT_PT.tick * UNITS_PER_PT * 100) / 100;
    const legend = Math.round(EXPORT_FONT_PT.legend * UNITS_PER_PT * 100) / 100;
    const line = Math.round(EXPORT_LINE_PT.primary * UNITS_PER_PT * 100) / 100;
    expect(svg).toContain(`font-size="${tick}"`);
    expect(svg).toContain(`font-size="${legend}"`);
    expect(svg).toContain(`stroke-width="${line}"`);
    // 11 pt en una columna de 14,4 cm equivale a unas 27 unidades SVG.
    expect(tick).toBeGreaterThan(25);
  });

  it("scales the setpoint dash pattern with the line width", () => {
    expect(scaleDash("9 6")).toBe("18 12");
    expect(scaleDash(undefined)).toBe(undefined);
    expect(buildChartExportSvg(model())).toContain('stroke-dasharray="18 12"');
  });
});

describe("layout", () => {
  it("keeps the full legend size for the usual SIMPATI channels", () => {
    const layout = layoutChartExport(model());
    expect(layout.legendFontSize).toBeCloseTo(EXPORT_FONT_PT.legend * UNITS_PER_PT, 5);
    expect(layout.plot.height).toBeGreaterThan(EXPORT_VIEW_HEIGHT * 0.45);
  });

  it("keeps every legend entry and the title inside the image", () => {
    const channels = Array.from({ length: 9 }, (_, index) =>
      series(`Channel ${index + 1} with a fairly long descriptive name`, index * 5),
    );
    const layout = layoutChartExport(
      model({
        series: channels,
        title:
          "SIMPATI x04 · 240327_11371_RD_Aging.x04 · thermal shock profile with specimen temperature and every chamber setpoint",
      }),
    );
    expect(layout.titleLines.length).toBeGreaterThan(1);
    for (const line of layout.titleLines) {
      expect(estimateTextWidth(line, layout.titleFontSize)).toBeLessThanOrEqual(
        EXPORT_VIEW_WIDTH - 20,
      );
    }
    expect(layout.legend.items).toHaveLength(9);
    const legendFont = layout.legendFontSize;
    // Con tantos canales la leyenda se reduce, pero nunca por debajo del 70 %.
    expect(legendFont).toBeGreaterThanOrEqual(EXPORT_FONT_PT.legend * UNITS_PER_PT * 0.7 - 0.01);
    for (const item of layout.legend.items) {
      const right =
        item.x + 2.6 * legendFont + estimateTextWidth(item.series.label, legendFont);
      expect(right).toBeLessThanOrEqual(EXPORT_VIEW_WIDTH);
    }
    // La leyenda queda por encima del área de trazado, que conserva altura.
    const lastRow = Math.max(...layout.legend.items.map((item) => item.y));
    expect(lastRow).toBeLessThan(layout.plot.top);
    expect(layout.plot.height).toBeGreaterThan(140);
    expect(layout.plot.top + layout.plot.height).toBeLessThan(EXPORT_VIEW_HEIGHT);
  });

  it("places date labels on two lines without overlaps", () => {
    expect(timestampTickLines("2024-02-22T10:00:00")).toEqual([
      "22 Feb 2024",
      "10:00:00",
    ]);
    const layout = layoutChartExport(model());
    expect(layout.xTicks.length).toBeGreaterThan(1);
    expect(layout.xTicks.length).toBeLessThanOrEqual(EXPORT_MAX_X_TICKS);
    const half = layout.xLabelWidth / 2;
    layout.xTicks.forEach((tick, index) => {
      expect(tick.labelX - half).toBeGreaterThanOrEqual(0);
      expect(tick.labelX + half).toBeLessThanOrEqual(EXPORT_VIEW_WIDTH);
      if (index > 0) {
        expect(tick.labelX - layout.xTicks[index - 1].labelX).toBeGreaterThan(
          layout.xLabelWidth,
        );
      }
    });
  });

  it("shows distinct value labels for a narrow zoomed range", () => {
    const viewport = {
      xStart: 40,
      xEnd: 60,
      yRange: { minimum: 20.1, maximum: 20.3 },
    };
    const layout = layoutChartExport(model({ viewport }));
    const labels = layout.yTicks.map((tick) => tick.toFixed(layout.yDecimals));
    expect(new Set(labels).size).toBe(labels.length);
    expect(labels[0]).toBe("20.30");
  });
});

describe("exact visible view", () => {
  it("draws only the visible interval and clips a fixed value range", () => {
    const viewport = {
      xStart: 100,
      xEnd: 150,
      yRange: { minimum: 10, maximum: 30 },
    };
    const svg = buildChartExportSvg(
      model({ series: [series("Chamber temperature", 20)], viewport }),
    );
    const points = /<polyline points="([^"]+)"/.exec(svg)?.[1] ?? "";
    expect(points.split(" ")).toHaveLength(51);
    expect(svg).toContain('clip-path="url(#export-plot)"');
    expect(svg).toContain(">30.0</text>");
    expect(svg).toContain(">10.0</text>");
  });

  it("does not clip the default value range", () => {
    expect(buildChartExportSvg(model())).not.toContain('clip-path="url(#export-plot)"');
  });

  it("escapes channel names and titles", () => {
    const svg = buildChartExportSvg(
      model({ title: "A < B & C", series: [series("T<1> & \"x\"", 0)] }),
    );
    expect(svg).toContain("A &lt; B &amp; C");
    expect(svg).toContain("T&lt;1&gt; &amp; &quot;x&quot;");
  });
});
