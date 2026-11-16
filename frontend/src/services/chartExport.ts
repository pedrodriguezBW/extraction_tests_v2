/**
 * Exportación de las gráficas del visor como imagen para el informe.
 *
 * La vista que el usuario tiene en pantalla (intervalo X, rango Y, canales,
 * título, leyenda y estilos de línea) se redibuja en un SVG con el formato
 * común de `_RenderedAssets`, que replica las cifras del backend
 * (`src/report_generator/chart_export.py`):
 *
 * - 1800 × 1125 px, proporción 1,6:1;
 * - diseñado para el ancho de una columna de `Test Results` (≈14,4 cm), de
 *   modo que los tamaños en puntos son los que se ven en la diapositiva;
 * - títulos, ejes, valores y leyenda más grandes, trazos algo más gruesos y
 *   márgenes mínimos.
 *
 * El módulo es puro: genera texto SVG sin acceder al DOM, por lo que puede
 * probarse sin navegador. El visor interactivo no cambia.
 */

import { valueTickDecimals, type ChartViewport, type ValueRange } from "./chartZoom";
import { toleranceSummary, timestampPosition, type ToleranceResult } from "../types/tolerances";
import {mergeToleranceTrace, timedPathSegments} from "./simpatiToleranceTrace";

/** Proporción ancho:alto de las imágenes exportadas. */
export const EXPORT_ASPECT_RATIO = 1.6;
/** Tamaño en píxeles de la imagen exportada. */
export const EXPORT_WIDTH_PX = 1800;
export const EXPORT_HEIGHT_PX = Math.round(EXPORT_WIDTH_PX / EXPORT_ASPECT_RATIO);

/** Sistema de coordenadas del SVG exportado (misma proporción 1,6:1). */
export const EXPORT_VIEW_WIDTH = 1000;
export const EXPORT_VIEW_HEIGHT = EXPORT_VIEW_WIDTH / EXPORT_ASPECT_RATIO;

/**
 * Ancho físico de diseño: una columna de `Test Results`
 * ((29,63 cm − 0,80 cm) / 2), igual que en el backend.
 */
export const EXPORT_DESIGN_WIDTH_CM = (29.63 - 0.8) / 2;

/** Unidades SVG por punto tipográfico a ese ancho físico. */
export const UNITS_PER_PT =
  EXPORT_VIEW_WIDTH / ((EXPORT_DESIGN_WIDTH_CM / 2.54) * 72);

/** Tamaños en puntos tal como se ven en la diapositiva (dos columnas). */
export const EXPORT_FONT_PT = {
  title: 13,
  axisLabel: 12,
  tick: 11,
  legend: 11,
} as const;

/** Grosores de línea en puntos. */
export const EXPORT_LINE_PT = {
  primary: 1.8,
  secondary: 1.5,
  grid: 0.6,
  frame: 0.8,
} as const;

/** Número máximo de marcas del eje X (evita que las fechas se solapen). */
export const EXPORT_MAX_X_TICKS = 6;

const PAD = 10;
/** Separación entre el área de trazado y las fechas del eje X. */
const X_LABEL_OFFSET = 12;
/** Ancho medio estimado de un carácter (en em) para Segoe UI / Arial. */
const CHAR_EM = 0.56;
const FONT_FAMILY = "Segoe UI, Arial, sans-serif";

/** Serie que se dibuja en la imagen exportada. */
export interface ExportSeries {
  id: string;
  label: string;
  values: ReadonlyArray<number | null>;
  color: string;
  /** Patrón de trazo discontinuo (consignas) o `undefined`. */
  dash?: string;
  /** Las series principales (térmicas) se dibujan algo más gruesas. */
  primary: boolean;
}

/** Vista que se exporta: exactamente la que el usuario ve en pantalla. */
export interface ChartExportModel {
  tolerances?: ToleranceResult | null;
  toleranceUnit?: string;
  title: string;
  valueAxisLabel: string;
  timestamps: ReadonlyArray<string>;
  series: ReadonlyArray<ExportSeries>;
  viewport: ChartViewport;
  /** Rango Y visible (fijado por el usuario o el rango por defecto). */
  yBounds: ValueRange;
}

const pt = (points: number) => points * UNITS_PER_PT;

/** Ancho estimado de un texto en unidades SVG. */
export function estimateTextWidth(text: string, fontSize: number): number {
  return text.length * CHAR_EM * fontSize;
}

function escapeXml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function round(value: number): string {
  return String(Math.round(value * 100) / 100);
}

/** Reparte un texto en líneas que caben en el ancho indicado. */
export function wrapText(
  text: string,
  fontSize: number,
  maxWidth: number,
): string[] {
  const maxChars = Math.max(8, Math.floor(maxWidth / (CHAR_EM * fontSize)));
  const words = text.split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let current = "";

  for (const word of words) {
    const candidate = current ? `${current} ${word}` : word;
    if (candidate.length <= maxChars || !current) {
      current = candidate;
    } else {
      lines.push(current);
      current = word;
    }
  }
  if (current) {
    lines.push(current);
  }
  return lines.length > 0 ? lines : [text];
}

/**
 * Etiqueta del eje X en dos líneas (fecha y hora) para que las marcas
 * no se solapen. Usa el mismo formato que el visor.
 */
export function timestampTickLines(value: string | undefined): string[] {
  if (!value) {
    return [""];
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return [value];
  }
  const day = new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
  const time = new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
  return [day, time];
}

/** Elemento de la leyenda colocado en la imagen. */
export interface LegendItemLayout {
  series: ExportSeries;
  x: number;
  y: number;
}

/**
 * Coloca la leyenda en filas que caben en el ancho disponible: se muestran
 * todos los canales con su nombre completo.
 */
export function layoutLegend(
  series: ReadonlyArray<ExportSeries>,
  left: number,
  top: number,
  maxWidth: number,
  fontSize: number = pt(EXPORT_FONT_PT.legend),
): { items: LegendItemLayout[]; height: number } {
  const swatch = 2.2 * fontSize;
  const gap = 0.4 * fontSize;
  const spacing = 1.1 * fontSize;
  const rowHeight = 1.35 * fontSize;
  const items: LegendItemLayout[] = [];
  let x = left;
  let row = 0;

  for (const item of series) {
    const width = swatch + gap + estimateTextWidth(item.label, fontSize);
    if (x > left && x + width > left + maxWidth) {
      row += 1;
      x = left;
    }
    items.push({ series: item, x, y: top + row * rowHeight });
    x += width + spacing;
  }

  return {
    items,
    height: series.length > 0 ? (row + 1) * rowHeight : 0,
  };
}

/** Índices de las marcas del eje X que caben sin solaparse. */
export function exportXTicks(
  xStart: number,
  xEnd: number,
  plotWidth: number,
  labelWidth: number,
): number[] {
  const span = Math.max(0, xEnd - xStart);
  const fitting = Math.floor(plotWidth / (labelWidth + pt(EXPORT_FONT_PT.tick))) + 1;
  const count = Math.max(1, Math.min(EXPORT_MAX_X_TICKS, fitting, span + 1));
  if (count <= 1) {
    return [xStart];
  }
  return Array.from({ length: count }, (_, position) =>
    Math.round(xStart + (position * span) / (count - 1)),
  );
}

/**
 * Escala el patrón discontinuo del visor al grosor de exportación para que
 * las consignas mantengan el mismo aspecto.
 */
export function scaleDash(dash: string | undefined, factor = 2): string | undefined {
  if (!dash) {
    return undefined;
  }
  return dash
    .split(/[\s,]+/)
    .filter(Boolean)
    .map((part) => round(Number(part) * factor))
    .join(" ");
}

function pathSegments(
  values: ReadonlyArray<number | null>,
  startIndex: number,
  endIndex: number,
  xScale: (index: number) => number,
  yScale: (value: number) => number,
): string[] {
  const segments: string[] = [];
  let current: string[] = [];
  for (let index = startIndex; index <= endIndex; index += 1) {
    const value = values[index];
    if (value === null || value === undefined || !Number.isFinite(value)) {
      if (current.length > 1) {
        segments.push(current.join(" "));
      }
      current = [];
      continue;
    }
    current.push(`${round(xScale(index))},${round(yScale(value))}`);
  }
  if (current.length > 1) {
    segments.push(current.join(" "));
  }
  return segments;
}

/** Marca del eje X: índice, posición de la línea y del texto. */
export interface XTickLayout {
  index: number;
  x: number;
  labelX: number;
}

/**
 * Coloca las etiquetas del eje X sin salirse de la imagen y sin solaparse:
 * las etiquetas de los extremos se desplazan hacia dentro y se descartan
 * las marcas intermedias cuya etiqueta chocaría con la anterior. La primera
 * y la última marca se conservan siempre.
 */
export function placeXTickLabels(
  ticks: ReadonlyArray<{ index: number; x: number }>,
  labelWidth: number,
  minimumX: number,
  maximumX: number,
  gap: number,
): XTickLayout[] {
  const half = labelWidth / 2;
  const placed = ticks.map((tick) => ({
    ...tick,
    labelX: Math.min(maximumX - half, Math.max(minimumX + half, tick.x)),
  }));
  if (placed.length <= 2) {
    return placed.length === 2 &&
      placed[1].labelX - placed[0].labelX < labelWidth + gap
      ? [placed[0]]
      : placed;
  }

  const last = placed[placed.length - 1];
  const kept: XTickLayout[] = [placed[0]];
  for (const tick of placed.slice(1, -1)) {
    const previous = kept[kept.length - 1];
    if (
      tick.labelX - previous.labelX >= labelWidth + gap &&
      last.labelX - tick.labelX >= labelWidth + gap
    ) {
      kept.push(tick);
    }
  }
  if (last.labelX - kept[kept.length - 1].labelX >= labelWidth + gap) {
    kept.push(last);
  }
  return kept;
}

/**
 * Marcas del eje X equiespaciadas cuyas etiquetas no se solapan: se prueba
 * con el mayor número de marcas que cabe y se reduce hasta que ninguna
 * etiqueta choca con su vecina (tras desplazar las de los extremos).
 */
export function evenXTicks(
  xStart: number,
  xEnd: number,
  plotLeft: number,
  plotWidth: number,
  labelWidth: number,
  fontSize: number,
): XTickLayout[] {
  const maximum = exportXTicks(xStart, xEnd, plotWidth, labelWidth).length;
  const span = Math.max(0, xEnd - xStart);
  const toX = (index: number) =>
    plotLeft + ((index - xStart) / Math.max(1, span)) * plotWidth;

  for (let count = maximum; count >= 2; count -= 1) {
    const indexes = Array.from({ length: count }, (_, position) =>
      Math.round(xStart + (position * span) / (count - 1)),
    );
    const ticks = indexes.map((index) => ({ index, x: toX(index) }));
    const placed = placeXTickLabels(
      ticks,
      labelWidth,
      PAD,
      EXPORT_VIEW_WIDTH - PAD,
      fontSize * 0.8,
    );
    if (placed.length === ticks.length) {
      return placed;
    }
  }
  return [{ index: xStart, x: toX(xStart), labelX: Math.max(PAD + labelWidth / 2, toX(xStart)) }];
}

/** Geometría calculada de la imagen exportada (útil para pruebas). */
export interface ChartExportLayout {
  titleLines: string[];
  titleFontSize: number;
  legendFontSize: number;
  legend: { items: LegendItemLayout[]; height: number };
  plot: { left: number; top: number; width: number; height: number };
  xTicks: XTickLayout[];
  xLabelWidth: number;
  yTicks: number[];
  yDecimals: number;
}

/**
 * Calcula la disposición de la imagen: título, leyenda, área de trazado y
 * marcas, reservando el espacio justo para que nada quede recortado.
 */
export function layoutChartExport(model: ChartExportModel): ChartExportLayout {
  // Con muchos canales o títulos muy largos se reduce ligeramente la
  // leyenda (y el título) para que el área de trazado conserve al menos
  // `MIN_PLOT_FRACTION` del alto. Todos los textos se muestran completos.
  let layout = layoutWithScale(model, LEGEND_SCALES[0]);
  for (const scale of LEGEND_SCALES.slice(1)) {
    if (layout.plot.height >= EXPORT_VIEW_HEIGHT * MIN_PLOT_FRACTION) {
      break;
    }
    layout = layoutWithScale(model, scale);
  }
  return layout;
}

/** Factores de reducción de leyenda y título que se prueban en orden. */
const LEGEND_SCALES: ReadonlyArray<{ legend: number; title: number }> = [
  { legend: 1, title: 1 },
  { legend: 0.9, title: 1 },
  { legend: 0.8, title: 0.9 },
  { legend: 0.7, title: 0.85 },
];

/** Fracción mínima del alto de la imagen reservada al área de trazado. */
const MIN_PLOT_FRACTION = 0.45;

function layoutWithScale(
  model: ChartExportModel,
  scale: { legend: number; title: number },
): ChartExportLayout {
  const innerWidth = EXPORT_VIEW_WIDTH - 2 * PAD;
  const titleFontSize = pt(EXPORT_FONT_PT.title) * scale.title;
  const legendFontSize = pt(EXPORT_FONT_PT.legend) * scale.legend;
  const tickFontSize = pt(EXPORT_FONT_PT.tick);
  const axisFontSize = pt(EXPORT_FONT_PT.axisLabel);

  const titleLines = wrapText(model.title, titleFontSize, innerWidth);
  const titleBottom = PAD + titleLines.length * titleFontSize * 1.2;

  const legend = layoutLegend(
    model.series,
    PAD,
    titleBottom + 6,
    innerWidth,
    legendFontSize,
  );
  const legendBottom = titleBottom + 6 + legend.height;

  const yDecimals = valueTickDecimals(model.yBounds, 4);
  const yTicks = Array.from({ length: 5 }, (_, position) =>
    model.yBounds.maximum -
    (position / 4) * (model.yBounds.maximum - model.yBounds.minimum),
  );
  const yLabelWidth = Math.max(
    ...yTicks.map((tick) => estimateTextWidth(tick.toFixed(yDecimals), tickFontSize)),
  );

  const left = PAD + axisFontSize * 1.25 + yLabelWidth + 10;
  const right = EXPORT_VIEW_WIDTH - PAD - 4;
  const summaryHeight = model.tolerances ? toleranceSummary(model.tolerances).length * 29 + 25 : 0;
  const top = legendBottom + 8 + tickFontSize * 0.5 + summaryHeight;
  const bottom = EXPORT_VIEW_HEIGHT - PAD - 2 * tickFontSize * 1.2 - X_LABEL_OFFSET;

  const { xStart, xEnd } = model.viewport;
  const sampleLines = [xStart, xEnd].flatMap((index) =>
    timestampTickLines(model.timestamps[index]),
  );
  const xLabelWidth = Math.max(
    ...sampleLines.map((line) => estimateTextWidth(line, tickFontSize)),
  );

  return {
    titleLines,
    titleFontSize,
    legendFontSize,
    legend,
    plot: {
      left,
      top,
      width: right - left,
      height: Math.max(40, bottom - top),
    },
    xTicks: evenXTicks(xStart, xEnd, left, right - left, xLabelWidth, tickFontSize),
    xLabelWidth,
    yTicks,
    yDecimals,
  };
}

/**
 * Genera el SVG de exportación (1000 × 625 unidades, dibujado a
 * 1800 × 1125 px) con exactamente la vista visible.
 */
export function buildChartExportSvg(model: ChartExportModel): string {
  const layout = layoutChartExport(model);
  const { plot } = layout;
  const { xStart, xEnd } = model.viewport;
  const { minimum, maximum } = model.yBounds;
  const tickFontSize = pt(EXPORT_FONT_PT.tick);
  const axisFontSize = pt(EXPORT_FONT_PT.axisLabel);
  const legendFontSize = layout.legendFontSize;

  const xScale = (index: number) =>
    plot.left + ((index - xStart) / Math.max(1, xEnd - xStart)) * plot.width;
  const ySpan = maximum - minimum > 0 ? maximum - minimum : 1;
  const yScale = (value: number) =>
    plot.top + ((maximum - value) / ySpan) * plot.height;

  const parts: string[] = [];
  parts.push(
    `<svg xmlns="http://www.w3.org/2000/svg" width="${EXPORT_WIDTH_PX}" height="${EXPORT_HEIGHT_PX}" ` +
      `viewBox="0 0 ${EXPORT_VIEW_WIDTH} ${EXPORT_VIEW_HEIGHT}" font-family="${FONT_FAMILY}">`,
  );
  parts.push(
    `<defs><clipPath id="export-plot"><rect x="${round(plot.left)}" y="${round(plot.top)}" ` +
      `width="${round(plot.width)}" height="${round(plot.height)}"/></clipPath></defs>`,
  );
  parts.push(
    `<rect x="0" y="0" width="${EXPORT_VIEW_WIDTH}" height="${EXPORT_VIEW_HEIGHT}" fill="#ffffff"/>`,
  );

  // Título (en varias líneas si es largo).
  layout.titleLines.forEach((line, index) => {
    parts.push(
      `<text x="${PAD}" y="${round(PAD + layout.titleFontSize * (0.95 + index * 1.2))}" ` +
        `fill="#102f49" font-size="${round(layout.titleFontSize)}" font-weight="700">${escapeXml(line)}</text>`,
    );
  });

  // Leyenda con todos los canales activados.
  for (const item of layout.legend.items) {
    const lineY = item.y + legendFontSize * 0.62;
    const swatch = 2.2 * legendFontSize;
    parts.push(
      `<line x1="${round(item.x)}" x2="${round(item.x + swatch)}" y1="${round(lineY)}" y2="${round(lineY)}" ` +
        `stroke="${item.series.color}" stroke-width="${round(pt(EXPORT_LINE_PT.primary) * 1.2)}"` +
        `${item.series.dash ? ` stroke-dasharray="${scaleDash(item.series.dash)}"` : ""}/>`,
    );
    parts.push(
      `<text x="${round(item.x + swatch + 0.4 * legendFontSize)}" y="${round(item.y + legendFontSize * 0.98)}" ` +
        `fill="#32485b" font-size="${round(legendFontSize)}">${escapeXml(item.series.label)}</text>`,
    );
  }

  // Área de trazado.
  parts.push(
    `<rect x="${round(plot.left)}" y="${round(plot.top)}" width="${round(plot.width)}" ` +
      `height="${round(plot.height)}" fill="#f8fafb" stroke="#aebbc6" stroke-width="${round(pt(EXPORT_LINE_PT.frame))}"/>`,
  );

  if (model.tolerances) {
    const result = model.tolerances;
    const display = (value: number) => model.toleranceUnit?.toLowerCase().includes("f") ? value * 9 / 5 + 32 : value;
    const tx = (timestamp: string) => xScale(timestampPosition(model.timestamps, timestamp));
    parts.push('<g clip-path="url(#export-plot)">');
    for (const plateau of result.plateaus) {
      parts.push(`<rect x="${tx(plateau.start)}" y="${yScale(display(plateau.setpoint_c + 2))}" width="${Math.max(0, tx(plateau.end) - tx(plateau.start))}" height="${yScale(display(plateau.setpoint_c - 2)) - yScale(display(plateau.setpoint_c + 2))}" fill="#58a881" fill-opacity="0.25"/>`);
    }
    parts.push('</g>');
    const summary = toleranceSummary(result);
    const summaryY = plot.top - summary.length * 29;
    parts.push(`<rect x="${plot.left}" y="${summaryY - 24}" width="${plot.width}" height="${summary.length * 29 + 6}" rx="3" fill="#f0f7f4" stroke="#7b9c8d"/>`);
    summary.forEach((line, index) => parts.push(`<text x="${plot.left + 5}" y="${summaryY + 29 * index}" font-size="${pt(10)}" fill="#102f49">${escapeXml(line)}</text>`));
  }

  // Eje Y: rejilla y valores.
  for (const tick of layout.yTicks) {
    const y = yScale(tick);
    parts.push(
      `<line x1="${round(plot.left)}" x2="${round(plot.left + plot.width)}" y1="${round(y)}" y2="${round(y)}" ` +
        `stroke="#d7dfe5" stroke-width="${round(pt(EXPORT_LINE_PT.grid))}"/>`,
    );
    parts.push(
      `<text x="${round(plot.left - 8)}" y="${round(y + tickFontSize * 0.35)}" text-anchor="end" ` +
        `fill="#405566" font-size="${round(tickFontSize)}">${tick.toFixed(layout.yDecimals)}</text>`,
    );
  }

  // Eje X: rejilla y fechas en dos líneas, sin salirse de la imagen.
  for (const { index, x, labelX } of layout.xTicks) {
    parts.push(
      `<line x1="${round(x)}" x2="${round(x)}" y1="${round(plot.top)}" y2="${round(plot.top + plot.height)}" ` +
        `stroke="#e4e9ed" stroke-width="${round(pt(EXPORT_LINE_PT.grid))}"/>`,
    );
    timestampTickLines(model.timestamps[index]).forEach((line, lineIndex) => {
      parts.push(
        `<text x="${round(labelX)}" y="${round(plot.top + plot.height + X_LABEL_OFFSET + tickFontSize * (0.95 + lineIndex * 1.2))}" ` +
          `text-anchor="middle" fill="#405566" font-size="${round(tickFontSize)}">${escapeXml(line)}</text>`,
      );
    });
  }

  // Título del eje Y.
  const axisX = PAD + axisFontSize * 0.85;
  const axisY = plot.top + plot.height / 2;
  parts.push(
    `<text x="${round(axisX)}" y="${round(axisY)}" transform="rotate(-90 ${round(axisX)} ${round(axisY)})" ` +
      `text-anchor="middle" fill="#32485b" font-size="${round(axisFontSize)}" font-weight="700">` +
      `${escapeXml(model.valueAxisLabel)}</text>`,
  );

  // Series: recortadas al área solo si el rango Y lo ha fijado el usuario.
  parts.push(model.viewport.yRange !== null ? `<g clip-path="url(#export-plot)">` : "<g>");
  for (const item of model.series) {
    const width = pt(item.primary ? EXPORT_LINE_PT.primary : EXPORT_LINE_PT.secondary);
    const segments = model.tolerances && item.id === model.tolerances.channel
      ? timedPathSegments(mergeToleranceTrace(model.timestamps, item.values, model.tolerances, model.toleranceUnit ?? "°C"),
          model.timestamps, xStart, xEnd, xScale, yScale)
      : pathSegments(item.values, xStart, xEnd, xScale, yScale);
    for (const points of segments) {
      parts.push(
        `<polyline points="${points}" fill="none" stroke="${item.color}" stroke-width="${round(width)}"` +
          `${item.dash ? ` stroke-dasharray="${scaleDash(item.dash)}"` : ""} stroke-linejoin="round" stroke-linecap="round"/>`,
      );
    }
  }
  parts.push("</g>");
  if (model.tolerances) {
    const display = (value: number) => model.toleranceUnit?.toLowerCase().includes("f") ? value * 9 / 5 + 32 : value;
    parts.push('<g clip-path="url(#export-plot)">');
    for (const excursion of model.tolerances.excursions) {
      const points = excursion.map(([timestamp, value]) => `${xScale(timestampPosition(model.timestamps, timestamp))},${yScale(display(value))}`).join(" ");
      parts.push(`<polyline points="${points}" fill="none" stroke="#d72631" stroke-width="5"/>`);
      for (const [timestamp, value] of excursion) parts.push(`<circle cx="${xScale(timestampPosition(model.timestamps, timestamp))}" cy="${yScale(display(value))}" r="3" fill="#d72631"/>`);
    }
    parts.push('</g>');
  }
  parts.push("</svg>");
  return parts.join("");
}
