import {
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import { evaluateTolerances } from "../services/api";
import { toleranceSummary, timestampPosition, type ToleranceSettings, type ToleranceResult } from "../types/tolerances";

import {
  EXPORT_HEIGHT_PX,
  EXPORT_WIDTH_PX,
  buildChartExportSvg,
} from "../services/chartExport";
import {
  applyZoomSelection,
  classifyZoomSelection,
  clampToPlot,
  clientToSvgPoint,
  defaultValueRange,
  fullViewport,
  isInsidePlot,
  selectionRectangle,
  valueTickDecimals,
  type ChartViewport,
  type PlotArea,
  type SvgPoint,
} from "../services/chartZoom";
import type {
  SimpatiChartSaveResponse,
  SimpatiInspectionResponse,
  SimpatiPreviewChannel,
} from "../types/simpati";


/**
 * Propiedades necesarias para mostrar y guardar una gráfica SIMPATI.
 */
export interface SimpatiChartProps {
  testType?: string;
  controlChannel?: string;
  /** Datos procesados de la adquisición y de su vista previa. */
  data: SimpatiInspectionResponse;

  /** Indica si existe una operación de guardado en curso. */
  saving: boolean;

  /** Impide guardar la gráfica aunque permita seguir explorando su vista. */
  saveDisabled?: boolean;

  /** Nombres de las gráficas almacenadas actualmente para el ensayo. */
  savedChartNames: string[];

  /**
   * Título dibujado en la gráfica, por ejemplo `SIMPATI x04 · ensayo.x04`.
   * Identifica la adquisición de origen en la imagen guardada.
   */
  title?: string;

  /**
   * Guarda la representación PNG de la vista actual.
   *
   * @param imageBase64 Imagen PNG codificada como una URL de datos.
   * @returns La respuesta devuelta por el backend.
   */
  onSave: (
    imageBase64: string,
    tolerances?: ToleranceSettings,
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
const PLOT_TOP = 104;
const PLOT_BOTTOM = 64;
const PLOT_WIDTH = CHART_WIDTH - PLOT_LEFT - PLOT_RIGHT;
const PLOT_HEIGHT = CHART_HEIGHT - PLOT_TOP - PLOT_BOTTOM;

/** Área de trazado usada por el zoom por arrastre. */
const PLOT_AREA: PlotArea = {
  left: PLOT_LEFT,
  top: PLOT_TOP,
  width: PLOT_WIDTH,
  height: PLOT_HEIGHT,
};

/** Número de intervalos entre las marcas del eje Y. */
const Y_TICK_INTERVALS = 4;

/**
 * Color de cada familia de canales térmicos. Las consignas usan el mismo
 * color que su valor real, con trazo discontinuo.
 */
const THERMAL_FAMILY_COLORS: Record<string, string> = {
  chamber: "#005a9c",
  supply_air: "#6b4c9a",
  return_air: "#007c91",
  basket: "#005a9c",
  hot_chamber: "#b83b0b",
  cold_chamber: "#24733e",
  specimen: "#8b3a62",
};

const SETPOINT_DASH = "9 6";

function thermalStyle(channel: SimpatiPreviewChannel): SeriesStyle {
  const role = channel.role ?? "";
  const setpoint = role.endsWith("_setpoint");
  const family = role.replace(/_(temperature|setpoint)$/, "");
  const color = THERMAL_FAMILY_COLORS[family] ?? "#0b4b70";
  return setpoint ? { color, dash: SETPOINT_DASH } : { color };
}

const ADVANCED_COLORS = [
  "#6b4c9a",
  "#9a6700",
  "#007c91",
  "#8b3a62",
  "#465a65",
  "#7a4e00",
];

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
    return thermalStyle(channel);
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
 * El componente permite seleccionar canales térmicos y avanzados, ampliar la
 * gráfica arrastrando sobre ella (eje X, eje Y o ambos según la forma de la
 * selección), restablecer la vista con `Reset view` o con doble clic y
 * guardar exactamente la vista visible como una imagen PNG.
 *
 * El componente no escribe archivos directamente. La persistencia se delega
 * en la función `onSave` proporcionada por el componente padre.
 *
 * @returns La interfaz interactiva de la gráfica SIMPATI.
 */

export function SimpatiChart({
  data,
  saving,
  saveDisabled = false,
  savedChartNames,
  title = "SIMPATI temperature profile",
  onSave,
  testType = "",
  controlChannel,
}: SimpatiChartProps) {
  const [showTolerances, setShowTolerances] = useState(false);
  const actualChannels = data.thermal_channels.filter(channel => channel.role?.endsWith("_temperature"));
  const referenceChannels = data.thermal_channels.filter(channel => channel.role?.endsWith("_setpoint"));
  const [evaluatedChannel, setEvaluatedChannel] = useState("");
  const [referenceChannel, setReferenceChannel] = useState("");
  const [evaluation, setEvaluation] = useState<{key: string; result: ToleranceResult} | null>(null);
  const [toleranceError, setToleranceError] = useState<string | null>(null);
  useEffect(() => {
    setEvaluatedChannel(controlChannel && actualChannels.some(channel => channel.id === controlChannel)
      ? controlChannel : actualChannels[0]?.id ?? "");
  }, [data, controlChannel]);
  const settings = useMemo<ToleranceSettings>(() => ({test_type: testType, channel: evaluatedChannel, reference: referenceChannel || null}), [testType, evaluatedChannel, referenceChannel]);
  const evaluationKey = JSON.stringify([data.selected_relative_path, settings]);
  const tolerancesActive = showTolerances && !!testType;
  const toleranceResult = tolerancesActive && evaluation?.key === evaluationKey ? evaluation.result : null;
  useEffect(() => {
    let cancelled = false;
    setToleranceError(null);
    if (tolerancesActive && data.selected_relative_path) {
      void evaluateTolerances(data.test_root, data.selected_relative_path, settings).then(result => {
        if (!cancelled) setEvaluation({key: evaluationKey, result});
      }).catch(error => {if (!cancelled) setToleranceError(error instanceof Error ? error.message : String(error));});
    }
    return () => {cancelled = true;};
  }, [tolerancesActive, evaluationKey, data.test_root, data.selected_relative_path, settings]);
  const titleId = useId();
  const descriptionId = useId();
  const svgRef = useRef<SVGSVGElement | null>(null);
  const lastIndex = Math.max(0, data.preview_timestamps.length - 1);
  const [selectedChannelIds, setSelectedChannelIds] = useState<string[]>([]);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  // Vista visible (zoom). El eje Y es automático mientras `yRange` es null.
  const [viewport, setViewport] = useState<ChartViewport>(() =>
    fullViewport(lastIndex),
  );
  const [dragStart, setDragStart] = useState<SvgPoint | null>(null);
  const [dragCurrent, setDragCurrent] = useState<SvgPoint | null>(null);
  const [preparingSave, setPreparingSave] = useState(false);
  const [savedChart, setSavedChart] =
    useState<SimpatiChartSaveResponse | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    setSelectedChannelIds(
      data.thermal_channels.map((channel) => channel.id),
    );
    setAdvancedOpen(false);
    setViewport(fullViewport(data.preview_timestamps.length - 1));
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

  const rangeStart = viewport.xStart;
  const rangeEnd = viewport.xEnd;

  // Rango Y por defecto: todos los datos de los canales activos. No depende
  // del intervalo temporal visible, de modo que ampliar el eje X nunca
  // reajusta el eje Y; este solo cambia cuando el usuario lo amplía.
  const defaultYBounds = useMemo(
    () => defaultValueRange(selectedChannels),
    [selectedChannels],
  );

  // Rango Y mostrado: el fijado por el usuario o el rango por defecto.
  const yBounds = viewport.yRange ?? defaultYBounds;

  const xScale = (index: number): number => {
    const rangeLength = Math.max(1, rangeEnd - rangeStart);
    return (
      PLOT_LEFT +
      ((index - rangeStart) / rangeLength) * PLOT_WIDTH
    );
  };

  const yScale = (value: number): number => {
    // Se usa el rango real para que los rangos ampliados menores que la
    // unidad ocupen todo el alto del área de trazado.
    const rawSpan = yBounds.maximum - yBounds.minimum;
    const span = rawSpan > 0 ? rawSpan : 1;
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
      Array.from({ length: Y_TICK_INTERVALS + 1 }, (_, position) => {
        const ratio = position / Y_TICK_INTERVALS;
        return yBounds.maximum -
          ratio * (yBounds.maximum - yBounds.minimum);
      }),
    [yBounds],
  );

  const yTickDecimals = valueTickDecimals(yBounds, Y_TICK_INTERVALS);

  const pointFromPointer = (
    event: ReactPointerEvent<SVGSVGElement>,
  ): SvgPoint =>
    clientToSvgPoint(
      event.clientX,
      event.clientY,
      event.currentTarget.getBoundingClientRect(),
      CHART_WIDTH,
      CHART_HEIGHT,
    );

  const handlePointerDown = (
    event: ReactPointerEvent<SVGSVGElement>,
  ) => {
    // Solo el botón principal inicia una selección y debe empezar dentro
    // del área de trazado.
    if (event.button !== 0 || selectedChannels.length === 0) {
      return;
    }

    const point = pointFromPointer(event);
    if (!isInsidePlot(point, PLOT_AREA)) {
      return;
    }

    event.currentTarget.setPointerCapture?.(event.pointerId);
    setDragStart(point);
    setDragCurrent(point);
  };

  const handlePointerMove = (
    event: ReactPointerEvent<SVGSVGElement>,
  ) => {
    if (dragStart === null) {
      return;
    }
    setDragCurrent(clampToPlot(pointFromPointer(event), PLOT_AREA));
  };

  const finishPointerSelection = () => {
    if (dragStart !== null && dragCurrent !== null) {
      const nextViewport = applyZoomSelection(
        viewport,
        dragStart,
        dragCurrent,
        PLOT_AREA,
        yBounds,
        lastIndex,
      );

      if (nextViewport !== null) {
        setViewport(nextViewport);
      }
    }

    setDragStart(null);
    setDragCurrent(null);
  };

  const cancelPointerSelection = () => {
    setDragStart(null);
    setDragCurrent(null);
  };

  // Restablece solo el zoom (ambos ejes); no modifica los canales.
  const resetZoom = () => {
    setViewport(fullViewport(lastIndex));
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
    resetZoom();
  };

  const renderPngDataUrl = (): Promise<string> => {
    // La imagen del informe se genera con el formato común de exportación
    // (1800 × 1125 px, 1,6:1, textos y trazos legibles en PowerPoint) a
    // partir de exactamente la vista visible: intervalo X, rango Y,
    // canales, título y estilos. No se recalculan los límites.
    const serialized = buildChartExportSvg({
      tolerances: toleranceResult,
      toleranceUnit: actualChannels.find(channel => channel.id === evaluatedChannel)?.unit,
      title,
      valueAxisLabel: "Value",
      timestamps: data.preview_timestamps,
      viewport,
      yBounds,
      series: selectedChannels.map((channel) => {
        const advancedIndex = data.advanced_channels.findIndex(
          (candidate) => candidate.id === channel.id,
        );
        const style = styleForChannel(channel, Math.max(0, advancedIndex));
        return {
          id: channel.id,
          label: channel.label,
          values: channel.values,
          color: style.color,
          dash: style.dash,
          primary: channel.thermal,
        };
      }),
    });
    const blob = new Blob([serialized], {
      type: "image/svg+xml;charset=utf-8",
    });
    const objectUrl = URL.createObjectURL(blob);

    return new Promise((resolve, reject) => {
      const image = new Image();

      image.onload = () => {
        const canvas = document.createElement("canvas");
        canvas.width = EXPORT_WIDTH_PX;
        canvas.height = EXPORT_HEIGHT_PX;
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
      const result = await onSave(imageBase64, ...(toleranceResult ? [settings] : []));
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

  // Selección en curso: su forma indica qué ejes se van a ajustar.
  const selectionMode =
    dragStart !== null && dragCurrent !== null
      ? classifyZoomSelection(dragStart, dragCurrent)
      : null;
  const selection =
    dragStart !== null && dragCurrent !== null && selectionMode !== null
      ? selectionRectangle(dragStart, dragCurrent, selectionMode, PLOT_AREA)
      : null;
  // Identificador válido en `url(#...)` para recortar las series al área de
  // trazado cuando el eje Y está ampliado.
  const clipPathId = `simpati-plot-${titleId.replace(/[^A-Za-z0-9_-]/g, "")}`;

  return (
    <div className="simpati-chart">
      <div className="simpati-chart__toolbar">
        <label><input type="checkbox" checked={tolerancesActive} disabled={!testType}
          onChange={event => {setEvaluation(null); setShowTolerances(event.target.checked);}}/>Mostrar tolerancias</label>
        {!testType && <span>Seleccione un tipo de ensayo en Configuración del ensayo.</span>}
        {tolerancesActive && <>
          <label>Canal evaluado <select value={evaluatedChannel} onChange={event => setEvaluatedChannel(event.target.value)}>
            {actualChannels.map(channel => <option key={channel.id} value={channel.id}>{channel.label}</option>)}
          </select></label>
          <label>Consigna <select value={referenceChannel} onChange={event => setReferenceChannel(event.target.value)}>
            <option value="">Automática (misma familia)</option>
            {referenceChannels.map(channel => <option key={channel.id} value={channel.id}>{channel.label}</option>)}
          </select></label>
          {toleranceError && <p role="alert">{toleranceError}</p>}
          {!toleranceResult && !toleranceError && <span>Evaluando adquisición completa…</span>}
        </>}
      </div>
      {toleranceResult && <div role="status">{toleranceSummary(toleranceResult).map(line => <div key={line}>{line}</div>)}
        {toleranceResult.warnings.map(line => <p key={line}>{line}</p>)}</div>}
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
              saveDisabled ||
              (tolerancesActive && !toleranceResult) ||
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
          onPointerCancel={cancelPointerSelection}
          onDoubleClick={resetZoom}
        >
          <title id={titleId}>{title}</title>
          <desc id={descriptionId}>
            Interactive time-series preview of the selected SIMPATI channels.
            Drag across the plot to zoom: horizontally for the time interval,
            vertically for the value range or diagonally for both.
            Double-click to restore the full view.
          </desc>
          <defs>
            <clipPath id={clipPathId}>
              <rect
                x={PLOT_LEFT}
                y={PLOT_TOP}
                width={PLOT_WIDTH}
                height={PLOT_HEIGHT}
              />
            </clipPath>
          </defs>
          <rect
            x="0"
            y="0"
            width={CHART_WIDTH}
            height={CHART_HEIGHT}
            fill="#ffffff"
          />
          <text
            x={PLOT_LEFT}
            y="26"
            fill="#102f49"
            fontSize="15"
            fontWeight="700"
          >
            {title}
          </text>
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
            const legendY = 52 + Math.floor(index / 4) * 24;

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
              y="80"
              fill="#60717f"
              fontSize="11"
            >
              +{selectedChannels.length - 8} more
            </text>
          )}

          {toleranceResult && <g clipPath={`url(#${clipPathId})`} pointerEvents="none">
            {toleranceResult.plateaus.map((plateau, index) => {
              const display = (value: number) => actualChannels.find(channel => channel.id === evaluatedChannel)?.unit.toLowerCase().includes("f") ? value * 9 / 5 + 32 : value;
              const left = xScale(timestampPosition(data.preview_timestamps, plateau.start));
              const right = xScale(timestampPosition(data.preview_timestamps, plateau.end));
              return <rect key={index} x={left} width={Math.max(0, right - left)} y={yScale(display(plateau.setpoint_c + 2))}
                height={yScale(display(plateau.setpoint_c - 2)) - yScale(display(plateau.setpoint_c + 2))} fill="#58a881" opacity="0.25"/>;
            })}
            {toleranceResult.excursions.flatMap((segment, index) => segment.map(([time, value], i) => {
              const displayValue = actualChannels.find(channel => channel.id === evaluatedChannel)?.unit.toLowerCase().includes("f") ? value * 9 / 5 + 32 : value;
              return <circle key={`${index}-${i}`} cx={xScale(timestampPosition(data.preview_timestamps, time))} cy={yScale(displayValue)} r="4" fill="#d72631"/>;
            }))}
          </g>}
          {yTicks.map((tick, tickIndex) => {
            const y = yScale(tick);
            return (
              <g key={`y-tick-${tickIndex}`}>
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
                  {tick.toFixed(yTickDecimals)}
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

          {/* Recorte al área de trazado solo con rango Y fijado: en modo
              automático los datos siempre caben y el trazo no cambia. */}
          <g
            clipPath={
              viewport.yRange !== null ? `url(#${clipPathId})` : undefined
            }
          >
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
          </g>

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

      <p className="simpati-chart__hint">
        Drag on the chart to zoom: horizontally for time, vertically for
        values or diagonally for both. Double-click the chart or use Reset
        view to show the full chart.
      </p>

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
