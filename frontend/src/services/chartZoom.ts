/**
 * Lógica común del zoom por arrastre de los visores de gráficas.
 *
 * El usuario arrastra sobre el área de trazado y la forma de la selección
 * decide qué ejes se ajustan:
 *
 * - selección horizontal: intervalo temporal (eje X), sin tocar el eje Y;
 * - selección vertical: rango de valores (eje Y);
 * - selección rectangular: ambos ejes a la vez.
 *
 * Todas las funciones son puras y trabajan en coordenadas del `viewBox` del
 * SVG, de modo que no dependen del tamaño real del visor en pantalla.
 */

/** Rectángulo del área de trazado en coordenadas del SVG. */
export interface PlotArea {
  left: number;
  top: number;
  width: number;
  height: number;
}

/** Punto en coordenadas del SVG. */
export interface SvgPoint {
  x: number;
  y: number;
}

/** Rango de valores del eje Y. */
export interface ValueRange {
  minimum: number;
  maximum: number;
}

/**
 * Vista visible de la gráfica.
 *
 * `xStart` y `xEnd` son índices de muestra (incluidos). `yRange` es el rango
 * fijado por el usuario; `null` significa que se muestra el rango por
 * defecto (`defaultValueRange`), calculado con todos los datos de los
 * canales activos y nunca reajustado al ampliar el eje X.
 */
export interface ChartViewport {
  xStart: number;
  xEnd: number;
  yRange: ValueRange | null;
}

/** Ejes que ajusta una selección. */
export type ZoomSelectionMode = "x" | "y" | "xy";

/** Desplazamiento mínimo (unidades SVG) para considerar que hay arrastre. */
export const MIN_ZOOM_DRAG = 8;

/**
 * Proporción por debajo de la cual el desplazamiento secundario se ignora:
 * un arrastre casi horizontal ajusta solo el eje X y uno casi vertical solo
 * el eje Y.
 */
export const AXIS_LOCK_RATIO = 0.2;

/** Vista completa: todas las muestras y rango Y por defecto. */
export function fullViewport(lastIndex: number): ChartViewport {
  return { xStart: 0, xEnd: Math.max(0, lastIndex), yRange: null };
}

/** Indica si la vista coincide con la vista completa. */
export function isFullViewport(
  viewport: ChartViewport,
  lastIndex: number,
): boolean {
  return (
    viewport.xStart === 0 &&
    viewport.xEnd === Math.max(0, lastIndex) &&
    viewport.yRange === null
  );
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, value));
}

/** Limita un punto al área de trazado. */
export function clampToPlot(point: SvgPoint, plot: PlotArea): SvgPoint {
  return {
    x: clamp(point.x, plot.left, plot.left + plot.width),
    y: clamp(point.y, plot.top, plot.top + plot.height),
  };
}

/** Indica si un punto cae dentro del área de trazado. */
export function isInsidePlot(point: SvgPoint, plot: PlotArea): boolean {
  return (
    point.x >= plot.left &&
    point.x <= plot.left + plot.width &&
    point.y >= plot.top &&
    point.y <= plot.top + plot.height
  );
}

/**
 * Convierte la posición del puntero en pantalla a coordenadas del SVG.
 *
 * @param clientX Posición horizontal del puntero.
 * @param clientY Posición vertical del puntero.
 * @param bounds Rectángulo del SVG en pantalla.
 * @param viewBoxWidth Ancho del `viewBox`.
 * @param viewBoxHeight Alto del `viewBox`.
 */
export function clientToSvgPoint(
  clientX: number,
  clientY: number,
  bounds: { left: number; top: number; width: number; height: number },
  viewBoxWidth: number,
  viewBoxHeight: number,
): SvgPoint {
  const width = bounds.width > 0 ? bounds.width : viewBoxWidth;
  const height = bounds.height > 0 ? bounds.height : viewBoxHeight;
  return {
    x: ((clientX - bounds.left) / width) * viewBoxWidth,
    y: ((clientY - bounds.top) / height) * viewBoxHeight,
  };
}

/**
 * Decide qué ejes ajusta una selección según su forma.
 *
 * @returns `null` si el arrastre es demasiado corto (un clic).
 */
export function classifyZoomSelection(
  start: SvgPoint,
  end: SvgPoint,
): ZoomSelectionMode | null {
  const dx = Math.abs(end.x - start.x);
  const dy = Math.abs(end.y - start.y);

  if (dx < MIN_ZOOM_DRAG && dy < MIN_ZOOM_DRAG) {
    return null;
  }
  if (dy < MIN_ZOOM_DRAG || dy <= dx * AXIS_LOCK_RATIO) {
    return "x";
  }
  if (dx < MIN_ZOOM_DRAG || dx <= dy * AXIS_LOCK_RATIO) {
    return "y";
  }
  return "xy";
}

/**
 * Rectángulo que se dibuja durante el arrastre. Una selección de un solo eje
 * ocupa todo el alto (eje X) o todo el ancho (eje Y) del área de trazado.
 */
export function selectionRectangle(
  start: SvgPoint,
  end: SvgPoint,
  mode: ZoomSelectionMode,
  plot: PlotArea,
): { x: number; y: number; width: number; height: number } {
  const left = Math.min(start.x, end.x);
  const top = Math.min(start.y, end.y);
  const width = Math.abs(end.x - start.x);
  const height = Math.abs(end.y - start.y);

  if (mode === "x") {
    return { x: left, y: plot.top, width, height: plot.height };
  }
  if (mode === "y") {
    return { x: plot.left, y: top, width: plot.width, height };
  }
  return { x: left, y: top, width, height };
}

/** Índice de muestra correspondiente a una coordenada X del SVG. */
export function indexAtSvgX(
  svgX: number,
  viewport: ChartViewport,
  plot: PlotArea,
): number {
  const ratio = clamp((svgX - plot.left) / plot.width, 0, 1);
  return viewport.xStart + ratio * (viewport.xEnd - viewport.xStart);
}

/** Valor correspondiente a una coordenada Y del SVG. */
export function valueAtSvgY(
  svgY: number,
  yBounds: ValueRange,
  plot: PlotArea,
): number {
  const ratio = clamp((svgY - plot.top) / plot.height, 0, 1);
  return yBounds.maximum - ratio * (yBounds.maximum - yBounds.minimum);
}

/**
 * Calcula la vista resultante de una selección.
 *
 * El eje que la selección no ajusta conserva exactamente su rango: una
 * selección horizontal no modifica el eje Y y una vertical no modifica el X.
 *
 * @param viewport Vista actual.
 * @param start Punto inicial del arrastre (coordenadas SVG).
 * @param end Punto final del arrastre (coordenadas SVG).
 * @param plot Área de trazado.
 * @param yBounds Rango Y que se está mostrando (automático o fijado).
 * @param lastIndex Último índice de muestra disponible.
 * @returns La nueva vista o `null` si la selección no produce ningún zoom
 *   (arrastre corto o intervalo inferior a una muestra).
 */
export function applyZoomSelection(
  viewport: ChartViewport,
  start: SvgPoint,
  end: SvgPoint,
  plot: PlotArea,
  yBounds: ValueRange,
  lastIndex: number,
): ChartViewport | null {
  const from = clampToPlot(start, plot);
  const to = clampToPlot(end, plot);
  const mode = classifyZoomSelection(from, to);

  if (mode === null) {
    return null;
  }

  let { xStart, xEnd, yRange } = viewport;

  if (mode === "x" || mode === "xy") {
    const first = indexAtSvgX(Math.min(from.x, to.x), viewport, plot);
    const last = indexAtSvgX(Math.max(from.x, to.x), viewport, plot);
    const nextStart = clamp(Math.round(first), 0, Math.max(0, lastIndex));
    const nextEnd = clamp(Math.round(last), 0, Math.max(0, lastIndex));

    // El intervalo debe contener al menos dos muestras.
    if (nextEnd <= nextStart) {
      if (mode === "x") {
        return null;
      }
    } else {
      xStart = nextStart;
      xEnd = nextEnd;
    }
  }

  if (mode === "y" || mode === "xy") {
    const maximum = valueAtSvgY(Math.min(from.y, to.y), yBounds, plot);
    const minimum = valueAtSvgY(Math.max(from.y, to.y), yBounds, plot);
    const currentSpan = Math.abs(yBounds.maximum - yBounds.minimum);

    // Se descartan rangos degenerados que no pueden representarse.
    if (
      Number.isFinite(minimum) &&
      Number.isFinite(maximum) &&
      maximum - minimum > currentSpan * 1e-9
    ) {
      yRange = { minimum, maximum };
    } else if (mode === "y") {
      return null;
    }
  }

  if (
    xStart === viewport.xStart &&
    xEnd === viewport.xEnd &&
    yRange === viewport.yRange
  ) {
    return null;
  }

  return { xStart, xEnd, yRange };
}

/** Serie con valores representables (los nulos son huecos). */
export interface ValueSeries {
  values: ReadonlyArray<number | null>;
}

/**
 * Rango Y por defecto: mínimo y máximo de todos los valores de las series,
 * con un margen del 8 %. Usa la adquisición completa, no el intervalo
 * visible, para que el eje Y no se reajuste al ampliar el eje X.
 */
export function defaultValueRange(
  series: ReadonlyArray<ValueSeries>,
): ValueRange {
  let minimum = Number.POSITIVE_INFINITY;
  let maximum = Number.NEGATIVE_INFINITY;

  for (const item of series) {
    for (const value of item.values) {
      if (value === null || !Number.isFinite(value)) {
        continue;
      }
      minimum = Math.min(minimum, value);
      maximum = Math.max(maximum, value);
    }
  }

  if (!Number.isFinite(minimum) || !Number.isFinite(maximum)) {
    return { minimum: -1, maximum: 1 };
  }

  const span = maximum - minimum;
  const padding = span === 0 ? 1 : span * 0.08;
  return { minimum: minimum - padding, maximum: maximum + padding };
}

/**
 * Número de decimales de las etiquetas del eje Y. Mantiene un decimal en la
 * vista habitual y añade los necesarios al ampliar rangos pequeños para que
 * las etiquetas no se repitan.
 */
export function valueTickDecimals(
  yBounds: ValueRange,
  tickIntervals: number,
): number {
  const step = Math.abs(yBounds.maximum - yBounds.minimum) /
    Math.max(1, tickIntervals);
  if (!Number.isFinite(step) || step <= 0) {
    return 1;
  }
  return clamp(Math.ceil(-Math.log10(step)), 1, 6);
}
