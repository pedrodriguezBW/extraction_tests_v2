import { useCallback, useEffect, useReducer, useRef } from "react";

import { GraphtecChart } from "./GraphtecChart";
import {
  canSaveGraphtec,
  formatSeconds,
  graphtecPanelReducer,
  graphtecUnitsSummary,
  graphtecViewToSettings,
  initialGraphtecPanelState,
  isFullGraphtecViewport,
  validateGraphtecForm,
  type GraphtecPanelAction,
  type GraphtecPanelState,
} from "../services/graphtecChart";
import type {
  GraphtecChartSaveResponse,
  GraphtecChartSettings,
  GraphtecInspectionResponse,
} from "../types/graphtec";

function errorText(error: unknown, fallback: string): string {
  return error instanceof Error && error.message.trim()
    ? error.message
    : fallback;
}

/**
 * Propiedades de la vista del análisis Graphtec. No tiene estado propio para
 * poder probarse con cualquier combinación de estados.
 */
export interface GraphtecAnalysisViewProps {
  inspection: GraphtecInspectionResponse;
  state: GraphtecPanelState;
  /** Otra operación incompatible está en curso. */
  disabled: boolean;
  /** Impide guardar el gráfico sin deshabilitar la exploración. */
  saveDisabled?: boolean;
  dispatch: (action: GraphtecPanelAction) => void;
  onSave: () => void;
}

/**
 * Resumen del archivo Graphtec, gráfica interactiva (zoom por arrastre, como
 * en SIMPATI) y guardado de la vista visible.
 */
export function GraphtecAnalysisView({
  inspection,
  state,
  disabled,
  saveDisabled = false,
  dispatch,
  onSave,
}: GraphtecAnalysisViewProps) {
  const { form, save } = state;
  const validationError = validateGraphtecForm(form, inspection);
  const zoomed = !isFullGraphtecViewport(state.viewport, inspection);
  const controlsDisabled = disabled || save.status === "saving";
  const testType = inspection.test_types.join(", ") || "Unknown";

  return (
    <div className="result-panel graphtec-panel">
      <div className="result-panel__header">
        <div>
          <span>Graphtec file</span>
          <h3 title={inspection.relative_path ?? undefined}>
            {inspection.file_name ?? "Graphtec file"}
          </h3>
        </div>
        <span className="overall-status overall-status--success">
          Graphtec analyzed
        </span>
      </div>

      <dl className="metrics-grid graphtec-metrics">
        <div>
          <dt>Format</dt>
          <dd>{inspection.format_label ?? inspection.format ?? "Unknown"}</dd>
        </div>
        <div>
          <dt>Test type</dt>
          <dd>{testType}</dd>
        </div>
        <div>
          <dt>Records</dt>
          <dd>{inspection.records_count}</dd>
        </div>
        <div>
          <dt>Final result</dt>
          <dd>{inspection.final_result ?? "Not reported"}</dd>
        </div>
        <div>
          <dt>Phases</dt>
          <dd>{inspection.phases.join(", ") || "None"}</dd>
        </div>
        <div>
          <dt>Series</dt>
          <dd>
            {inspection.available_series
              .map((series) => `${series.label} [${series.unit}]`)
              .join(", ")}
          </dd>
        </div>
        <div>
          <dt>Units</dt>
          <dd>{graphtecUnitsSummary(inspection).join("; ")}</dd>
        </div>
        <div>
          <dt>Duration</dt>
          <dd>
            {formatSeconds(inspection.duration_seconds)}
            <span className="resource-metrics__note">
              Elapsed time {formatSeconds(inspection.elapsed_time_start)} to{" "}
              {formatSeconds(inspection.elapsed_time_end)}
            </span>
          </dd>
        </div>
      </dl>

      <div className="metadata-path">
        <span>Source file</span>
        <code title={inspection.relative_path ?? undefined}>
          {inspection.relative_path}
        </code>
      </div>

      {inspection.limited_values_count > 0 && (
        <p className="graphtec-note">
          {inspection.limited_values_count} limited value
          {inspection.limited_values_count === 1 ? "" : "s"} (for example
          &gt;50Gohm) are shown at their threshold with a limit marker, not
          as exact measurements.
        </p>
      )}

      {inspection.warnings.length > 0 && (
        <div className="message-panel message-panel--warning graphtec-warnings">
          <h3>Warnings</h3>
          <ul>
            {inspection.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="graphtec-config" aria-label="Chart configuration">
        <h3>Chart configuration</h3>
        <p className="action-hint">
          X axis: Elapsed time [s]. Voltage uses the left axis; current or
          resistance uses the right axis. Save chart stores exactly the view
          shown below, including the zoom.
        </p>

        <fieldset className="graphtec-config__series" disabled={controlsDisabled}>
          <legend>Series</legend>
          {inspection.available_series.map((series) => (
            <label key={series.id} className="simpati-series-option">
              <input
                type="checkbox"
                name="graphtec-series"
                value={series.id}
                checked={form.series.includes(series.id)}
                onChange={(event) =>
                  dispatch({
                    type: "seriesToggled",
                    seriesId: series.id,
                    selected: event.target.checked,
                  })
                }
              />
              {series.label} [{series.unit}]
            </label>
          ))}
        </fieldset>

        <div className="graphtec-config__grid">
          <label className="graphtec-field graphtec-field--wide">
            <span>Title</span>
            <input
              id="graphtec-title"
              type="text"
              value={form.title}
              maxLength={200}
              disabled={controlsDisabled}
              onChange={(event) =>
                dispatch({
                  type: "formChanged",
                  patch: { title: event.target.value },
                })
              }
            />
          </label>
        </div>

        <div className="graphtec-config__toggles">
          <label className="simpati-series-option">
            <input
              type="checkbox"
              checked={form.showLegend}
              disabled={controlsDisabled}
              onChange={(event) =>
                dispatch({
                  type: "formChanged",
                  patch: { showLegend: event.target.checked },
                })
              }
            />
            Show legend
          </label>
          <label className="simpati-series-option">
            <input
              type="checkbox"
              checked={form.showPhaseSeparators}
              disabled={controlsDisabled}
              onChange={(event) =>
                dispatch({
                  type: "formChanged",
                  patch: { showPhaseSeparators: event.target.checked },
                })
              }
            />
            Show phase separators
          </label>
        </div>

        {validationError && (
          <p className="graphtec-validation" role="alert">
            {validationError}
          </p>
        )}

        <div className="section-actions graphtec-config__actions">
          <button
            className="button button--quiet graphtec-reset"
            type="button"
            disabled={controlsDisabled}
            onClick={() => dispatch({ type: "reset", inspection })}
          >
            Reset view
          </button>
          <button
            className="button button--primary"
            type="button"
            disabled={
              !canSaveGraphtec(state, inspection, disabled || saveDisabled)
            }
            onClick={onSave}
          >
            {save.status === "saving" ? "Saving chart..." : "Save chart"}
          </button>
          {zoomed && (
            <span className="action-hint graphtec-zoom-status">
              Zoomed view: {formatSeconds(state.viewport.timeStart)} to{" "}
              {formatSeconds(state.viewport.timeEnd)}
              {state.viewport.yZoom !== null ? ", value range zoomed" : ""}.
            </span>
          )}
        </div>
      </div>

      {save.message && (
        <div
          className={`simpati-save-status ${
            save.status === "error"
              ? "simpati-save-status--error"
              : "simpati-save-status--success"
          }`}
          role={save.status === "error" ? "alert" : "status"}
        >
          {save.message}
          {save.status === "saved" &&
            " Saved in 04_Report/_RenderedAssets. It is not added to the PowerPoint automatically."}
        </div>
      )}

      {inspection.chart_data.elapsed_time_seconds.length === 0 ? (
        <div className="empty-state">
          The file has no records to display.
        </div>
      ) : (
        <>
          <GraphtecChart
            inspection={inspection}
            state={state}
            onViewportChange={(viewport) =>
              dispatch({ type: "viewportChanged", viewport })
            }
            onZoomReset={() => dispatch({ type: "zoomReset", inspection })}
          />
          <p className="simpati-chart__hint">
            Drag on the chart to zoom: horizontally for time, vertically for
            values or diagonally for both. Double-click the chart or use Reset
            view to show the full chart.
            {inspection.chart_data.truncated &&
              " Long files are shown with a reduced number of points; the saved chart uses every record."}
          </p>
        </>
      )}
    </div>
  );
}

/** Propiedades del contenedor del análisis Graphtec. */
export interface GraphtecAnalysisProps {
  inspection: GraphtecInspectionResponse;
  disabled: boolean;
  saveDisabled?: boolean;
  /** Genera y guarda la imagen de la vista indicada. */
  onSave: (
    settings: GraphtecChartSettings,
  ) => Promise<GraphtecChartSaveResponse>;
}

/**
 * Gestiona la gráfica interactiva y el guardado de un archivo Graphtec
 * analizado.
 *
 * El componente debe montarse con `key` igual a la ruta del archivo para
 * descartar la configuración y el zoom al cambiar de archivo. Las respuestas
 * que llegan tras desmontarse se ignoran.
 */
export function GraphtecAnalysis({
  inspection,
  disabled,
  saveDisabled = false,
  onSave,
}: GraphtecAnalysisProps) {
  const [state, dispatch] = useReducer(
    graphtecPanelReducer,
    inspection,
    initialGraphtecPanelState,
  );
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const save = useCallback(async () => {
    if (!canSaveGraphtec(state, inspection, disabled || saveDisabled)) {
      return;
    }
    dispatch({ type: "saveStarted" });
    try {
      const response = await onSave(graphtecViewToSettings(state, inspection));
      if (mounted.current) {
        dispatch({
          type: "saveSucceeded",
          chartName: response.chart_name ?? "PNG image",
        });
      }
    } catch (error) {
      if (mounted.current) {
        dispatch({
          type: "saveFailed",
          message: errorText(error, "The chart could not be saved."),
        });
      }
    }
  }, [disabled, inspection, onSave, saveDisabled, state]);

  return (
    <GraphtecAnalysisView
      inspection={inspection}
      state={state}
      disabled={disabled}
      saveDisabled={saveDisabled}
      dispatch={dispatch}
      onSave={() => void save()}
    />
  );
}
