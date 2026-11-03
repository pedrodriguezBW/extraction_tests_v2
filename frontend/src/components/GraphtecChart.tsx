import { useId, useMemo, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";

import {
  classifyZoomSelection,
  clampToPlot,
  clientToSvgPoint,
  isInsidePlot,
  selectionRectangle,
  type PlotArea,
  type SvgPoint,
  type ValueRange,
} from "../services/chartZoom";
import {
  GRAPHTEC_STATUS_TEST,
  applyGraphtecZoom,
  niceTicks,
  graphtecSeriesValues,
  graphtecTimeDomain,
  visibleGraphtecRanges,
  type GraphtecPanelState,
  type GraphtecViewport,
} from "../services/graphtecChart";
import type {
  GraphtecInspectionResponse,
  GraphtecSeries,
  GraphtecSeriesId,
} from "../types/graphtec";

/** Colores de las series, iguales a los de la imagen generada por el backend. */
export const GRAPHTEC_SERIES_COLORS: Record<GraphtecSeriesId, string> = {
  voltage: "#0b4b70",
  current: "#b83b0b",
  resistance: "#24733e",
};

const CHART_WIDTH = 1000;
const CHART_HEIGHT = 470;
const PLOT_LEFT = 84;
const PLOT_TOP = 92;
const PLOT_BOTTOM = 62;
const PLOT_RIGHT_SINGLE = 24;
const PLOT_RIGHT_DUAL = 84;
const Y_TICK_INTERVALS = 4;
const X_TICK_INTERVALS = 5;

/** Eje Y dibujado y series que representa. */
interface DrawnAxis {
  position: "left" | "right";
  series: GraphtecSeries;
  range: ValueRange;
}

/** Entrada de la leyenda y su símbolo. */
interface LegendItem {
  key: string;
  color: string;
  marker: "line" | "limitUp" | "limitDown" | "result";
  label: string;
}

/** Propiedades del visor interactivo de una gráfica Graphtec. */
export interface GraphtecChartProps {
  inspection: GraphtecInspectionResponse;
  state: GraphtecPanelState;
  /** Aplica una vista nueva (zoom por arrastre). */
  onViewportChange: (viewport: GraphtecViewport) => void;
  /** Restablece solo el zoom (doble clic). */
  onZoomReset: () => void;
}

function formatTick(value: number, decimals: number): string {
  return value.toFixed(decimals);
}

/**
 * Visor interactivo de un archivo Graphtec (TXT) con el mismo sistema de
 * zoom que las gráficas SIMPATI: arrastrar en horizontal amplía el tiempo,
 * en vertical los valores (ambos ejes Y a la vez) y en diagonal ambos; el
 * doble clic restablece la vista completa.
 *
 * Dibuja tensión en el eje izquierdo y corriente o resistencia en el
 * derecho. Los valores limitados (por ejemplo `>50Gohm`) se muestran en su
 * umbral con un triángulo hueco y no se unen a la línea; los registros de
 * resultado (PASS, FAIL...) se muestran con un rombo.
 */
export function GraphtecChart({
  inspection,
  state,
  onViewportChange,
  onZoomReset,
}: GraphtecChartProps) {
  const titleId = useId();
  const descriptionId = useId();
  const [dragStart, setDragStart] = useState<SvgPoint | null>(null);
  const [dragCurrent, setDragCurrent] = useState<SvgPoint | null>(null);
  const { form, viewport } = state;
  const data = inspection.chart_data;

  const selectedSeries = useMemo(
    () =>
      inspection.available_series.filter((series) =>
        form.series.includes(series.id),
      ),
    [form.series, inspection.available_series],
  );

  const ranges = useMemo(
    () => visibleGraphtecRanges(state, inspection),
    [inspection, state],
  );

  // Con una sola serie se dibuja en el eje izquierdo, como en el backend.
  const axes: DrawnAxis[] = selectedSeries.map((series) => ({
    position:
      selectedSeries.length === 1 ? "left" : series.axis === "right" ? "right" : "left",
    series,
    range: ranges[series.id] ?? { minimum: 0, maximum: 1 },
  }));
  const dual = axes.length > 1;
  const plotRight = dual ? PLOT_RIGHT_DUAL : PLOT_RIGHT_SINGLE;
  const plot: PlotArea = {
    left: PLOT_LEFT,
    top: PLOT_TOP,
    width: CHART_WIDTH - PLOT_LEFT - plotRight,
    height: CHART_HEIGHT - PLOT_TOP - PLOT_BOTTOM,
  };

  const domain = graphtecTimeDomain(viewport);
  const xScale = (time: number): number =>
    plot.left +
    ((time - domain.minimum) / (domain.maximum - domain.minimum)) * plot.width;
  const yScaleFor = (range: ValueRange) => (value: number): number => {
    const span = range.maximum - range.minimum || 1;
    return plot.top + ((range.maximum - value) / span) * plot.height;
  };

  const { values: xTicks, decimals: xDecimals } = niceTicks(
    { minimum: viewport.timeStart, maximum: viewport.timeEnd },
    X_TICK_INTERVALS,
  );

  // Índices visibles (con el margen del eje X).
  const visibleIndexes: number[] = [];
  data.elapsed_time_seconds.forEach((time, index) => {
    if (time >= domain.minimum && time <= domain.maximum) {
      visibleIndexes.push(index);
    }
  });

  const seriesDrawing = axes.map(({ series, range }) => {
    const values = graphtecSeriesValues(inspection, series.id);
    const yScale = yScaleFor(range);
    const measured = series.id !== "voltage";
    const segments: string[] = [];
    const limited: Array<{ x: number; y: number; operator: string }> = [];
    const results: Array<{ x: number; y: number; status: string }> = [];
    let current: string[] = [];
    const flush = () => {
      if (current.length > 0) {
        segments.push(current.join(" "));
      }
      current = [];
    };
    for (const index of visibleIndexes) {
      const value = values[index];
      const time = data.elapsed_time_seconds[index];
      if (value === undefined || value === null || !Number.isFinite(value)) {
        flush();
        continue;
      }
      const point = { x: xScale(time), y: yScale(value) };
      const status = data.status[index] ?? GRAPHTEC_STATUS_TEST;
      if (status !== GRAPHTEC_STATUS_TEST) {
        results.push({ ...point, status });
        continue;
      }
      const operator = data.measurement_operator[index];
      if (measured && operator) {
        // Igual que el backend: el valor limitado no se une a la línea.
        flush();
        limited.push({ ...point, operator });
        continue;
      }
      current.push(`${point.x},${point.y}`);
    }
    flush();
    return {
      series,
      color: GRAPHTEC_SERIES_COLORS[series.id] ?? "#465a65",
      segments,
      limited,
      results,
    };
  });

  const phaseMarkers = form.showPhaseSeparators
    ? inspection.phase_segments
        .filter(
          (segment) =>
            segment.end_elapsed_seconds >= viewport.timeStart &&
            segment.start_elapsed_seconds <= viewport.timeEnd,
        )
        .map((segment) => ({
          phase: segment.phase,
          time: Math.max(segment.start_elapsed_seconds, viewport.timeStart),
        }))
    : [];

  const pointFromPointer = (event: ReactPointerEvent<SVGSVGElement>): SvgPoint =>
    clientToSvgPoint(
      event.clientX,
      event.clientY,
      event.currentTarget.getBoundingClientRect(),
      CHART_WIDTH,
      CHART_HEIGHT,
    );

  const handlePointerDown = (event: ReactPointerEvent<SVGSVGElement>) => {
    if (event.button !== 0 || selectedSeries.length === 0) {
      return;
    }
    const point = pointFromPointer(event);
    if (!isInsidePlot(point, plot)) {
      return;
    }
    event.currentTarget.setPointerCapture?.(event.pointerId);
    setDragStart(point);
    setDragCurrent(point);
  };

  const handlePointerMove = (event: ReactPointerEvent<SVGSVGElement>) => {
    if (dragStart === null) {
      return;
    }
    setDragCurrent(clampToPlot(pointFromPointer(event), plot));
  };

  const finishPointerSelection = () => {
    if (dragStart !== null && dragCurrent !== null) {
      const next = applyGraphtecZoom(viewport, dragStart, dragCurrent, plot, inspection);
      if (next !== null) {
        onViewportChange(next);
      }
    }
    setDragStart(null);
    setDragCurrent(null);
  };

  const cancelPointerSelection = () => {
    setDragStart(null);
    setDragCurrent(null);
  };

  const selectionMode =
    dragStart !== null && dragCurrent !== null
      ? classifyZoomSelection(dragStart, dragCurrent)
      : null;
  const selection =
    dragStart !== null && dragCurrent !== null && selectionMode !== null
      ? selectionRectangle(dragStart, dragCurrent, selectionMode, plot)
      : null;
  const clipPathId = `graphtec-plot-${titleId.replace(/[^A-Za-z0-9_-]/g, "")}`;
  const title = form.title.trim() || inspection.default_title || "Graphtec chart";

  const legendItems: LegendItem[] = form.showLegend
    ? seriesDrawing.flatMap((drawing) => {
        const items: LegendItem[] = [
          {
            key: `${drawing.series.id}-line`,
            color: drawing.color,
            marker: "line",
            label: `${drawing.series.label} [${drawing.series.unit}]`,
          },
        ];
        for (const operator of [...new Set(drawing.limited.map((p) => p.operator))]) {
          items.push({
            key: `${drawing.series.id}-limit-${operator}`,
            color: drawing.color,
            marker: operator === "<" ? "limitDown" : "limitUp",
            label: `${drawing.series.label} limit (${operator} threshold)`,
          });
        }
        for (const status of [...new Set(drawing.results.map((p) => p.status))]) {
          items.push({
            key: `${drawing.series.id}-result-${status}`,
            color: drawing.color,
            marker: "result",
            label: `${drawing.series.label} - ${status} record`,
          });
        }
        return items;
      })
    : [];

  return (
    <div className="simpati-chart graphtec-chart">
      <div className="simpati-chart__canvas">
        <svg
          viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
          role="img"
          aria-labelledby={`${titleId} ${descriptionId}`}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={finishPointerSelection}
          onPointerCancel={cancelPointerSelection}
          onDoubleClick={onZoomReset}
        >
          <title id={titleId}>{title}</title>
          <desc id={descriptionId}>
            Interactive chart of the selected Graphtec series. Drag across the
            plot to zoom: horizontally for the time interval, vertically for
            the value range or diagonally for both. Double-click to restore
            the full view.
          </desc>
          <defs>
            <clipPath id={clipPathId}>
              <rect x={plot.left} y={plot.top - 6} width={plot.width} height={plot.height + 12} />
            </clipPath>
          </defs>
          <rect x="0" y="0" width={CHART_WIDTH} height={CHART_HEIGHT} fill="#ffffff" />
          <text x={PLOT_LEFT} y="26" fill="#102f49" fontSize="15" fontWeight="700">
            {title.length > 110 ? `${title.slice(0, 109)}…` : title}
          </text>
          <rect
            x={plot.left}
            y={plot.top}
            width={plot.width}
            height={plot.height}
            fill="#f8fafb"
            stroke="#aebbc6"
          />

          {legendItems.slice(0, 8).map((item, index) => {
            const legendX = PLOT_LEFT + (index % 4) * 220;
            const legendY = 50 + Math.floor(index / 4) * 20;
            return (
              <g key={`legend-${item.key}`} className="graphtec-chart__legend-item">
                {item.marker === "line" && (
                  <line x1={legendX} x2={legendX + 24} y1={legendY} y2={legendY} stroke={item.color} strokeWidth="3" />
                )}
                {item.marker === "limitUp" && (
                  <polygon points={`${legendX + 12},${legendY - 6} ${legendX + 18},${legendY + 5} ${legendX + 6},${legendY + 5}`} fill="#ffffff" stroke={item.color} strokeWidth="1.6" />
                )}
                {item.marker === "limitDown" && (
                  <polygon points={`${legendX + 12},${legendY + 6} ${legendX + 18},${legendY - 5} ${legendX + 6},${legendY - 5}`} fill="#ffffff" stroke={item.color} strokeWidth="1.6" />
                )}
                {item.marker === "result" && (
                  <polygon points={`${legendX + 12},${legendY - 6} ${legendX + 18},${legendY} ${legendX + 12},${legendY + 6} ${legendX + 6},${legendY}`} fill={item.color} stroke="#000000" strokeWidth="1" />
                )}
                <text x={legendX + 32} y={legendY + 4} fill="#32485b" fontSize="11">
                  {item.label.length > 32 ? `${item.label.slice(0, 31)}…` : item.label}
                </text>
              </g>
            );
          })}

          {/* Rejilla y etiquetas del eje izquierdo (o único). */}
          {axes.map((axis) => {
            const yScale = yScaleFor(axis.range);
            const ticks = niceTicks(axis.range, Y_TICK_INTERVALS);
            const color = GRAPHTEC_SERIES_COLORS[axis.series.id] ?? "#526575";
            const left = axis.position === "left";
            const labelX = left ? 18 : CHART_WIDTH - 14;
            const middle = plot.top + plot.height / 2;
            return (
              <g key={`axis-${axis.series.id}`} className={`graphtec-chart__axis graphtec-chart__axis--${axis.position}`}>
                {ticks.values.map((value, i) => {
                  const y = yScale(value);
                  return (
                    <g key={`y-${axis.series.id}-${i}`}>
                      {left && (
                        <line x1={plot.left} x2={plot.left + plot.width} y1={y} y2={y} stroke="#d7dfe5" strokeWidth="1" />
                      )}
                      <text
                        x={left ? plot.left - 10 : plot.left + plot.width + 10}
                        y={y + 4}
                        textAnchor={left ? "end" : "start"}
                        fill={color}
                        fontSize="12"
                      >
                        {formatTick(value, ticks.decimals)}
                      </text>
                    </g>
                  );
                })}
                <text
                  x={labelX}
                  y={middle}
                  transform={`rotate(${left ? -90 : 90} ${labelX} ${middle})`}
                  textAnchor="middle"
                  fill={color}
                  fontSize="13"
                  fontWeight="700"
                >
                  {`${axis.series.label} [${axis.series.unit}]`}
                </text>
              </g>
            );
          })}

          {xTicks.map((time, index) => (
            <g key={`x-${index}`}>
              <line x1={xScale(time)} x2={xScale(time)} y1={plot.top} y2={plot.top + plot.height} stroke="#e4e9ed" strokeWidth="1" />
              <text x={xScale(time)} y={plot.top + plot.height + 20} textAnchor="middle" fill="#526575" fontSize="11">
                {formatTick(time, xDecimals)}
              </text>
            </g>
          ))}
          <text
            x={plot.left + plot.width / 2}
            y={CHART_HEIGHT - 14}
            textAnchor="middle"
            fill="#32485b"
            fontSize="13"
            fontWeight="700"
          >
            Elapsed time [s]
          </text>

          {phaseMarkers.map((marker, index) => {
            const x = xScale(marker.time);
            const previous = index > 0 ? xScale(phaseMarkers[index - 1].time) : null;
            const staggered = previous !== null && x - previous < plot.width * 0.04;
            return (
              <g key={`phase-${index}`} className="graphtec-chart__phase">
                {(index > 0 || marker.time > viewport.timeStart) && (
                  <line x1={x} x2={x} y1={plot.top} y2={plot.top + plot.height} stroke="#8a99a6" strokeDasharray="2 3" strokeWidth="1" />
                )}
                <text x={x + 3} y={plot.top + (staggered ? 26 : 13)} fill="#5b6b78" fontSize="11">
                  {marker.phase}
                </text>
              </g>
            );
          })}

          <g clipPath={`url(#${clipPathId})`}>
            {seriesDrawing.map((drawing) => (
              <g key={`series-${drawing.series.id}`} className={`graphtec-chart__series graphtec-chart__series--${drawing.series.id}`}>
                {drawing.segments.map((points, index) =>
                  points.includes(" ") ? (
                    <polyline key={`seg-${index}`} points={points} fill="none" stroke={drawing.color} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
                  ) : null,
                )}
                {drawing.segments.flatMap((points, index) =>
                  points.split(" ").map((pair, pointIndex) => {
                    const [x, y] = pair.split(",").map(Number);
                    return <circle key={`pt-${index}-${pointIndex}`} cx={x} cy={y} r="2.2" fill={drawing.color} />;
                  }),
                )}
                {drawing.limited.map((point, index) => (
                  <polygon
                    key={`limit-${index}`}
                    className="graphtec-chart__limit"
                    points={
                      point.operator === "<"
                        ? `${point.x},${point.y + 6} ${point.x + 6},${point.y - 5} ${point.x - 6},${point.y - 5}`
                        : `${point.x},${point.y - 6} ${point.x + 6},${point.y + 5} ${point.x - 6},${point.y + 5}`
                    }
                    fill="#ffffff"
                    stroke={drawing.color}
                    strokeWidth="1.5"
                  />
                ))}
                {drawing.results.map((point, index) => (
                  <polygon
                    key={`result-${index}`}
                    className="graphtec-chart__result"
                    points={`${point.x},${point.y - 6} ${point.x + 6},${point.y} ${point.x},${point.y + 6} ${point.x - 6},${point.y}`}
                    fill={drawing.color}
                    stroke="#000000"
                    strokeWidth="1"
                  />
                ))}
              </g>
            ))}
          </g>

          {selectedSeries.length === 0 && (
            <text x={plot.left + plot.width / 2} y={plot.top + plot.height / 2} textAnchor="middle" fill="#60717f" fontSize="16">
              Select at least one series to display the chart.
            </text>
          )}

          {selection !== null && (
            <rect
              className="simpati-chart__selection"
              x={selection.x}
              y={selection.y}
              width={Math.max(2, selection.width)}
              height={Math.max(2, selection.height)}
              fill="#13a8c7"
              fillOpacity="0.18"
              stroke="#087b93"
              strokeDasharray="5 4"
              pointerEvents="none"
            />
          )}
        </svg>
      </div>
    </div>
  );
}
