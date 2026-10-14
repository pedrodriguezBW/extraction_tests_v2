import {
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react";
import type { PointerEvent as ReactPointerEvent } from "react";

import type {
  SimpatiChartSaveResponse,
  SimpatiInspectionResponse,
  SimpatiPreviewChannel,
} from "../types/simpati";


/**
 * Propiedades necesarias para mostrar y guardar una gráfica SIMPATI.
 */
export interface SimpatiChartProps {
  /** Datos procesados de la adquisición y de su vista previa. */
  data: SimpatiInspectionResponse;

  /** Indica si existe una operación de guardado en curso. */
  saving: boolean;

  /** Nombres de las gráficas almacenadas actualmente para el ensayo. */
  savedChartNames: string[];

  /**
   * Guarda la representación PNG de la vista actual.
   *
   * @param imageBase64 Imagen PNG codificada como una URL de datos.
   * @returns La respuesta devuelta por el backend.
   */
  onSave: (
    imageBase64: string,
  ) => Promise<SimpatiChartSaveResponse>;
}

interface SeriesStyle {
  color: string;
  dash?: string;
}

const CHART_WIDTH = 1000;
const CHART_HEIGHT = 470;
const PLOT_LEFT = 72;
const PLOT_RIGHT = 24;
const PLOT_TOP = 80;
const PLOT_BOTTOM = 64;
const PLOT_WIDTH = CHART_WIDTH - PLOT_LEFT - PLOT_RIGHT;
const PLOT_HEIGHT = CHART_HEIGHT - PLOT_TOP - PLOT_BOTTOM;

const THERMAL_STYLES: Record<string, SeriesStyle> = {
  "Basket temperature": { color: "#005a9c" },
  "Basket setpoint": { color: "#005a9c", dash: "9 6" },
  "Hot chamber temperature": { color: "#b83b0b" },
  "Hot chamber setpoint": { color: "#b83b0b", dash: "9 6" },
  "Cold chamber temperature": { color: "#24733e" },
  "Cold chamber setpoint": { color: "#24733e", dash: "9 6" },
};

const ADVANCED_COLORS = [
  "#6b4c9a",
  "#9a6700",
  "#007c91",
  "#8b3a62",
  "#465a65",
  "#7a4e00",
];

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, value));
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return "Not available";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}

function styleForChannel(
  channel: SimpatiPreviewChannel,
  advancedIndex: number,
): SeriesStyle {
  if (channel.thermal) {
    return THERMAL_STYLES[channel.label] ?? { color: "#0b4b70" };
  }

  return {
    color: ADVANCED_COLORS[advancedIndex % ADVANCED_COLORS.length],
  };
}

function pathSegments(
  channel: SimpatiPreviewChannel,
  startIndex: number,
  endIndex: number,
  xScale: (index: number) => number,
  yScale: (value: number) => number,
): string[] {
  const segments: string[] = [];
  let currentSegment: string[] = [];

  for (let index = startIndex; index <= endIndex; index += 1) {
    const value = channel.values[index];

    if (value === null || !Number.isFinite(value)) {
      if (currentSegment.length > 1) {
        segments.push(currentSegment.join(" "));
      }
      currentSegment = [];
      continue;
    }

    currentSegment.push(`${xScale(index)},${yScale(value)}`);
  }

  if (currentSegment.length > 1) {
    segments.push(currentSegment.join(" "));
  }

  return segments;
}


/**
 * Muestra una vista interactiva de los canales extraídos de una adquisición
 * SIMPATI.
 *
 * El componente permite seleccionar canales térmicos y avanzados, limitar el
 * intervalo temporal visible mediante arrastre, restablecer la vista y guardar
 * la gráfica visible como una imagen PNG.
 *
 * El componente no escribe archivos directamente. La persistencia se delega
 * en la función `onSave` proporcionada por el componente padre.
 *
 * @returns La interfaz interactiva de la gráfica SIMPATI.
 */

export function SimpatiChart({
  data,
  saving,
  savedChartNames,
  onSave,
}: SimpatiChartProps) {
  const titleId = useId();
  const descriptionId = useId();
  const svgRef = useRef<SVGSVGElement | null>(null);
  const lastIndex = Math.max(0, data.preview_timestamps.length - 1);
  const [selectedChannelIds, setSelectedChannelIds] = useState<string[]>([]);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [rangeStart, setRangeStart] = useState(0);
  const [rangeEnd, setRangeEnd] = useState(lastIndex);
  const [dragStart, setDragStart] = useState<number | null>(null);
  const [dragCurrent, setDragCurrent] = useState<number | null>(null);
  const [preparingSave, setPreparingSave] = useState(false);
  const [savedChart, setSavedChart] =
    useState<SimpatiChartSaveResponse | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    setSelectedChannelIds(
      data.thermal_channels.map((channel) => channel.id),
    );
    setAdvancedOpen(false);
    setRangeStart(0);
    setRangeEnd(Math.max(0, data.preview_timestamps.length - 1));
    setDragStart(null);
    setDragCurrent(null);
    setSavedChart(null);
    setSaveError(null);
  }, [data]);

  useEffect(() => {
    setSavedChart((current) => {
      if (
        current?.chart_name &&
        !savedChartNames.includes(current.chart_name)
      ) {
        return null;
      }
      return current;
    });
  }, [savedChartNames]);

  const allChannels = useMemo(
    () => [...data.thermal_channels, ...data.advanced_channels],
    [data],
  );

  const selectedChannels = useMemo(
    () =>
      allChannels.filter((channel) =>
        selectedChannelIds.includes(channel.id),
      ),
    [allChannels, selectedChannelIds],
  );

  const yBounds = useMemo(() => {
    const visibleValues = selectedChannels.flatMap((channel) =>
      channel.values
        .slice(rangeStart, rangeEnd + 1)
        .filter(
          (value): value is number =>
            value !== null && Number.isFinite(value),
        ),
    );

    if (visibleValues.length === 0) {
      return { minimum: -1, maximum: 1 };
    }

    let minimum = visibleValues[0];
    let maximum = visibleValues[0];

    for (const value of visibleValues.slice(1)) {
      minimum = Math.min(minimum, value);
      maximum = Math.max(maximum, value);
    }
    const span = maximum - minimum;
    const padding = span === 0 ? 1 : span * 0.08;

    return {
      minimum: minimum - padding,
      maximum: maximum + padding,
    };
  }, [rangeEnd, rangeStart, selectedChannels]);

  const xScale = (index: number): number => {
    const rangeLength = Math.max(1, rangeEnd - rangeStart);
    return (
      PLOT_LEFT +
      ((index - rangeStart) / rangeLength) * PLOT_WIDTH
    );
  };

  const yScale = (value: number): number => {
    const span = Math.max(1, yBounds.maximum - yBounds.minimum);
    return (
      PLOT_TOP +
      ((yBounds.maximum - value) / span) * PLOT_HEIGHT
    );
  };

  const xTicks = useMemo(() => {
    const tickCount = Math.min(5, rangeEnd - rangeStart + 1);
    if (tickCount <= 1) {
      return [rangeStart];
    }

    return Array.from({ length: tickCount }, (_, position) =>
      Math.round(
        rangeStart +
          (position * (rangeEnd - rangeStart)) / (tickCount - 1),
      ),
    );
  }, [rangeEnd, rangeStart]);

  const yTicks = useMemo(
    () =>
      Array.from({ length: 5 }, (_, position) => {
        const ratio = position / 4;
        return yBounds.maximum -
          ratio * (yBounds.maximum - yBounds.minimum);
      }),
    [yBounds],
  );

  const indexFromPointer = (
    event: ReactPointerEvent<SVGSVGElement>,
  ): number => {
    const bounds = event.currentTarget.getBoundingClientRect();
    const svgX =
      ((event.clientX - bounds.left) / bounds.width) * CHART_WIDTH;
    const ratio = clamp(
      (svgX - PLOT_LEFT) / PLOT_WIDTH,
      0,
      1,
    );
    return Math.round(
      rangeStart + ratio * (rangeEnd - rangeStart),
    );
  };

  const handlePointerDown = (
    event: ReactPointerEvent<SVGSVGElement>,
  ) => {
    if (rangeEnd <= rangeStart) {
      return;
    }

    const index = indexFromPointer(event);
    event.currentTarget.setPointerCapture(event.pointerId);
    setDragStart(index);
    setDragCurrent(index);
  };

  const handlePointerMove = (
    event: ReactPointerEvent<SVGSVGElement>,
  ) => {
    if (dragStart === null) {
      return;
    }
    setDragCurrent(indexFromPointer(event));
  };

  const finishPointerSelection = () => {
    if (dragStart !== null && dragCurrent !== null) {
      const nextStart = Math.min(dragStart, dragCurrent);
      const nextEnd = Math.max(dragStart, dragCurrent);

      if (nextEnd > nextStart) {
        setRangeStart(nextStart);
        setRangeEnd(nextEnd);
      }
    }

    setDragStart(null);
    setDragCurrent(null);
  };

  const toggleChannel = (channelId: string) => {
    setSelectedChannelIds((current) =>
      current.includes(channelId)
        ? current.filter((id) => id !== channelId)
        : [...current, channelId],
    );
  };

  const resetView = () => {
    setSelectedChannelIds(
      data.thermal_channels.map((channel) => channel.id),
    );
    setRangeStart(0);
    setRangeEnd(lastIndex);
    setDragStart(null);
    setDragCurrent(null);
  };

  const renderPngDataUrl = (): Promise<string> => {
    if (!svgRef.current) {
      return Promise.reject(
        new Error("The chart preview is not available."),
      );
    }

    const clonedSvg = svgRef.current.cloneNode(true) as SVGSVGElement;
    clonedSvg.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    clonedSvg.setAttribute("width", String(CHART_WIDTH));
    clonedSvg.setAttribute("height", String(CHART_HEIGHT));
    clonedSvg.setAttribute(
      "font-family",
      "Segoe UI, Arial, sans-serif",
    );
    const serialized = new XMLSerializer().serializeToString(clonedSvg);
    const blob = new Blob([serialized], {
      type: "image/svg+xml;charset=utf-8",
    });
    const objectUrl = URL.createObjectURL(blob);

    return new Promise((resolve, reject) => {
      const image = new Image();

      image.onload = () => {
        const scale = 1.6;
        const canvas = document.createElement("canvas");
        canvas.width = Math.round(CHART_WIDTH * scale);
        canvas.height = Math.round(CHART_HEIGHT * scale);
        const context = canvas.getContext("2d");

        if (!context) {
          URL.revokeObjectURL(objectUrl);
          reject(new Error("The chart image could not be prepared."));
          return;
        }

        context.fillStyle = "#ffffff";
        context.fillRect(0, 0, canvas.width, canvas.height);
        context.drawImage(image, 0, 0, canvas.width, canvas.height);
        URL.revokeObjectURL(objectUrl);
        resolve(canvas.toDataURL("image/png"));
      };

      image.onerror = () => {
        URL.revokeObjectURL(objectUrl);
        reject(new Error("The chart image could not be prepared."));
      };

      image.src = objectUrl;
    });
  };

  const saveCurrentView = async () => {
    setPreparingSave(true);
    setSavedChart(null);
    setSaveError(null);

    try {
      const imageBase64 = await renderPngDataUrl();
      const result = await onSave(imageBase64);
      setSavedChart(result);
    } catch (error) {
      setSaveError(
        error instanceof Error
          ? error.message
          : "The chart could not be saved.",
      );
    } finally {
      setPreparingSave(false);
    }
  };

  const selectionStart =
    dragStart !== null && dragCurrent !== null
      ? Math.min(dragStart, dragCurrent)
      : null;
  const selectionEnd =
    dragStart !== null && dragCurrent !== null
      ? Math.max(dragStart, dragCurrent)
      : null;

  return (
    <div className="simpati-chart">
      <div className="simpati-chart__toolbar">
        <div className="simpati-chart__series">
          {data.thermal_channels.map((channel, index) => {
            const style = styleForChannel(channel, index);
            return (
              <label key={channel.id} className="simpati-series-option">
                <input
                  type="checkbox"
                  checked={selectedChannelIds.includes(channel.id)}
                  onChange={() => toggleChannel(channel.id)}
                />
                <span
                  className="simpati-series-swatch"
                  style={{
                    backgroundColor: style.dash
                      ? "transparent"
                      : style.color,
                    borderTopColor: style.color,
                    borderStyle: style.dash ? "dashed" : "solid",
                  }}
                  aria-hidden="true"
                />
                <span>{channel.label}</span>
              </label>
            );
          })}
        </div>

        <div className="simpati-chart__actions">
          <button
            className="button button--quiet"
            type="button"
            onClick={resetView}
          >
            Reset view
          </button>
          <button
            className="button button--secondary"
            type="button"
            onClick={() => void saveCurrentView()}
            disabled={
              selectedChannels.length === 0 ||
              preparingSave ||
              saving
            }
          >
            {preparingSave || saving
              ? "Saving chart..."
              : "Save current chart"}
          </button>
        </div>
      </div>

      {savedChart?.success && (
        <div
          className="simpati-save-status simpati-save-status--success"
          role="status"
        >
          <strong>Chart saved: {savedChart.chart_name}</strong>
          <code title={savedChart.chart_path ?? undefined}>
            {savedChart.chart_path}
          </code>
        </div>
      )}

      {saveError && (
        <div
          className="simpati-save-status simpati-save-status--error"
          role="alert"
        >
          {saveError}
        </div>
      )}

      <div className="simpati-chart__canvas">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
          role="img"
          aria-labelledby={`${titleId} ${descriptionId}`}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={finishPointerSelection}
          onPointerCancel={finishPointerSelection}
        >
          <title id={titleId}>SIMPATI temperature profile</title>
          <desc id={descriptionId}>
            Interactive time-series preview of the selected SIMPATI channels.
            Drag across the plot to select a time interval.
          </desc>
          <rect
            x="0"
            y="0"
            width={CHART_WIDTH}
            height={CHART_HEIGHT}
            fill="#ffffff"
          />
          <rect
            x={PLOT_LEFT}
            y={PLOT_TOP}
            width={PLOT_WIDTH}
            height={PLOT_HEIGHT}
            fill="#f8fafb"
            stroke="#aebbc6"
          />

          {selectedChannels.slice(0, 8).map((channel, index) => {
            const advancedIndex = data.advanced_channels.findIndex(
              (candidate) => candidate.id === channel.id,
            );
            const style = styleForChannel(
              channel,
              Math.max(0, advancedIndex),
            );
            const legendX = PLOT_LEFT + (index % 4) * 220;
            const legendY = 24 + Math.floor(index / 4) * 24;

            return (
              <g key={`legend-${channel.id}`}>
                <line
                  x1={legendX}
                  x2={legendX + 24}
                  y1={legendY}
                  y2={legendY}
                  stroke={style.color}
                  strokeWidth="3"
                  strokeDasharray={style.dash}
                />
                <text
                  x={legendX + 32}
                  y={legendY + 4}
                  fill="#32485b"
                  fontSize="11"
                >
                  {channel.label.length > 25
                    ? `${channel.label.slice(0, 24)}…`
                    : channel.label}
                </text>
              </g>
            );
          })}

          {selectedChannels.length > 8 && (
            <text
              x={PLOT_LEFT + 3 * 220}
              y="52"
              fill="#60717f"
              fontSize="11"
            >
              +{selectedChannels.length - 8} more
            </text>
          )}

          {yTicks.map((tick) => {
            const y = yScale(tick);
            return (
              <g key={tick}>
                <line
                  x1={PLOT_LEFT}
                  x2={PLOT_LEFT + PLOT_WIDTH}
                  y1={y}
                  y2={y}
                  stroke="#d7dfe5"
                  strokeWidth="1"
                />
                <text
                  x={PLOT_LEFT - 12}
                  y={y + 4}
                  textAnchor="end"
                  fill="#526575"
                  fontSize="12"
                >
                  {tick.toFixed(1)}
                </text>
              </g>
            );
          })}

          {xTicks.map((index) => {
            const timestamp = data.preview_timestamps[index] ?? "";
            return (
              <g key={`${timestamp}-${index}`}>
                <line
                  x1={xScale(index)}
                  x2={xScale(index)}
                  y1={PLOT_TOP}
                  y2={PLOT_TOP + PLOT_HEIGHT}
                  stroke="#e4e9ed"
                  strokeWidth="1"
                />
                <text
                  x={xScale(index)}
                  y={PLOT_TOP + PLOT_HEIGHT + 22}
                  textAnchor="middle"
                  fill="#526575"
                  fontSize="11"
                >
                  {formatTimestamp(timestamp)}
                </text>
              </g>
            );
          })}

          <text
            x="18"
            y={PLOT_TOP + PLOT_HEIGHT / 2}
            transform={`rotate(-90 18 ${PLOT_TOP + PLOT_HEIGHT / 2})`}
            textAnchor="middle"
            fill="#32485b"
            fontSize="13"
            fontWeight="700"
          >
            Value
          </text>

          {selectedChannels.flatMap((channel) => {
            const advancedIndex = data.advanced_channels.findIndex(
              (candidate) => candidate.id === channel.id,
            );
            const style = styleForChannel(
              channel,
              Math.max(0, advancedIndex),
            );
            return pathSegments(
              channel,
              rangeStart,
              rangeEnd,
              xScale,
              yScale,
            ).map((points, segmentIndex) => (
              <polyline
                key={`${channel.id}-${segmentIndex}`}
                points={points}
                fill="none"
                stroke={style.color}
                strokeWidth={channel.thermal ? "2.2" : "1.7"}
                strokeDasharray={style.dash}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
            ));
          })}

          {selectedChannels.length === 0 && (
            <text
              x={PLOT_LEFT + PLOT_WIDTH / 2}
              y={PLOT_TOP + PLOT_HEIGHT / 2}
              textAnchor="middle"
              fill="#60717f"
              fontSize="16"
            >
              Select at least one channel to display the chart.
            </text>
          )}

          {selectionStart !== null && selectionEnd !== null && (
            <rect
              x={xScale(selectionStart)}
              y={PLOT_TOP}
              width={Math.max(
                2,
                xScale(selectionEnd) - xScale(selectionStart),
              )}
              height={PLOT_HEIGHT}
              fill="#13a8c7"
              fillOpacity="0.18"
              stroke="#087b93"
              strokeDasharray="5 4"
            />
          )}
        </svg>
      </div>

      <p className="simpati-chart__hint">
        Drag across the plot or use the range controls to select a time
        interval.
      </p>

      <div className="simpati-range-controls">
        <label>
          <span>Start: {formatTimestamp(data.preview_timestamps[rangeStart])}</span>
          <input
            type="range"
            min="0"
            max={Math.max(0, rangeEnd - 1)}
            value={Math.min(rangeStart, Math.max(0, rangeEnd - 1))}
            disabled={lastIndex < 1}
            onChange={(event) => setRangeStart(Number(event.target.value))}
          />
        </label>
        <label>
          <span>End: {formatTimestamp(data.preview_timestamps[rangeEnd])}</span>
          <input
            type="range"
            min={Math.min(lastIndex, rangeStart + 1)}
            max={lastIndex}
            value={Math.max(rangeEnd, Math.min(lastIndex, rangeStart + 1))}
            disabled={lastIndex < 1}
            onChange={(event) => setRangeEnd(Number(event.target.value))}
          />
        </label>
      </div>

      {data.advanced_channels.length > 0 && (
        <div className="simpati-advanced">
          <button
            className="button button--quiet simpati-advanced__toggle"
            type="button"
            aria-expanded={advancedOpen}
            onClick={() => setAdvancedOpen((current) => !current)}
          >
            Advanced channel selection
          </button>

          {advancedOpen && (
            <div className="simpati-advanced__options">
              {data.advanced_channels.map((channel, index) => {
                const style = styleForChannel(channel, index);
                return (
                  <label key={channel.id} className="simpati-series-option">
                    <input
                      type="checkbox"
                      checked={selectedChannelIds.includes(channel.id)}
                      onChange={() => toggleChannel(channel.id)}
                    />
                    <span
                      className="simpati-series-swatch"
                      style={{
                        backgroundColor: style.color,
                        borderTopColor: style.color,
                      }}
                      aria-hidden="true"
                    />
                    <span>{channel.label}</span>
                  </label>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
