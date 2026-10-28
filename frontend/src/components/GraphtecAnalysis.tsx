import { useCallback, useEffect, useReducer, useRef } from "react";

import {
  canPreviewGraphtec,
  canSaveGraphtec,
  formatSeconds,
  graphtecFormKey,
  graphtecFormToSettings,
  graphtecPanelReducer,
  graphtecUnitsSummary,
  initialGraphtecPanelState,
  isGraphtecPreviewCurrent,
  shouldAutoRefreshPreview,
  validateGraphtecForm,
  type GraphtecPanelAction,
  type GraphtecPanelState,
} from "../services/graphtecChart";
import type {
  GraphtecChartPreviewResponse,
  GraphtecChartSaveResponse,
  GraphtecChartSettings,
  GraphtecInspectionResponse,
} from "../types/graphtec";

/** Retardo antes de regenerar la previsualización tras un cambio. */
export const PREVIEW_REFRESH_DELAY_MS = 450;

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
  dispatch: (action: GraphtecPanelAction) => void;
  onPreview: () => void;
  onSave: () => void;
}

/**
 * Resumen del archivo Graphtec, configuración de la gráfica,
 * previsualización y guardado.
 */
export function GraphtecAnalysisView({
  inspection,
  state,
  disabled,
  dispatch,
  onPreview,
  onSave,
}: GraphtecAnalysisViewProps) {
  const { form, preview, save } = state;
  const validationError = validateGraphtecForm(form, inspection);
  const previewCurrent = isGraphtecPreviewCurrent(state);
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
          resistance uses the right axis.
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
          <label className="graphtec-field">
            <span>Start [s]</span>
            <input
              id="graphtec-time-min"
              type="number"
              min={0}
              step="any"
              value={form.timeMin}
              placeholder={String(inspection.elapsed_time_start ?? 0)}
              disabled={controlsDisabled}
              onChange={(event) =>
                dispatch({
                  type: "formChanged",
                  patch: { timeMin: event.target.value },
                })
              }
            />
          </label>
          <label className="graphtec-field">
            <span>End [s]</span>
            <input
              id="graphtec-time-max"
              type="number"
              min={0}
              step="any"
              value={form.timeMax}
              placeholder={String(inspection.elapsed_time_end ?? "")}
              disabled={controlsDisabled}
              onChange={(event) =>
                dispatch({
                  type: "formChanged",
                  patch: { timeMax: event.target.value },
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
            Reset
          </button>
          <button
            className="button button--secondary"
            type="button"
            disabled={!canPreviewGraphtec(state, inspection, disabled)}
            onClick={onPreview}
          >
            {preview.status === "loading" ? "Generating preview..." : "Preview chart"}
          </button>
          <button
            className="button button--primary"
            type="button"
            disabled={!canSaveGraphtec(state, inspection, disabled)}
            onClick={onSave}
          >
            {save.status === "saving" ? "Saving chart..." : "Save chart"}
          </button>
          {!previewCurrent && preview.status !== "loading" && (
            <span className="action-hint">
              Preview the chart to enable saving.
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

      <div className="graphtec-preview" aria-busy={preview.status === "loading"}>
        {preview.status === "idle" && (
          <div className="empty-state">
            Configure the chart and select Preview chart.
          </div>
        )}
        {preview.status === "loading" && (
          <p className="loading-text" role="status">
            Generating preview...
          </p>
        )}
        {preview.status === "error" && (
          <div className="simpati-save-status simpati-save-status--error" role="alert">
            {preview.error ?? "The preview could not be generated."}
          </div>
        )}
        {preview.response?.image_base64 && preview.status !== "error" && (
          <figure className="graphtec-preview__figure">
            <img
              src={preview.response.image_base64}
              alt={`Graphtec chart preview: ${preview.response.title ?? ""}`}
            />
            <figcaption>
              {preview.response.axes.map((axis) => axis.label).join(" | ")}
              {" | "}
              {preview.response.x_axis_label} from{" "}
              {formatSeconds(preview.response.time_start)} to{" "}
              {formatSeconds(preview.response.time_end)}
              {preview.response.notes.map((note) => (
                <span key={note} className="graphtec-preview__note">
                  {note}
                </span>
              ))}
            </figcaption>
          </figure>
        )}
      </div>
    </div>
  );
}

/** Propiedades del contenedor del análisis Graphtec. */
export interface GraphtecAnalysisProps {
  inspection: GraphtecInspectionResponse;
  disabled: boolean;
  onPreview: (
    settings: GraphtecChartSettings,
  ) => Promise<GraphtecChartPreviewResponse>;
  onSave: (
    settings: GraphtecChartSettings,
  ) => Promise<GraphtecChartSaveResponse>;
}

/**
 * Gestiona la configuración, la previsualización y el guardado de la
 * gráfica de un archivo Graphtec analizado.
 *
 * El componente debe montarse con `key` igual a la ruta del archivo para
 * descartar la configuración y la previsualización al cambiar de archivo.
 * Las respuestas que llegan tras desmontarse o tras una petición más
 * reciente se ignoran.
 */
export function GraphtecAnalysis({
  inspection,
  disabled,
  onPreview,
  onSave,
}: GraphtecAnalysisProps) {
  const [state, dispatch] = useReducer(
    graphtecPanelReducer,
    inspection,
    initialGraphtecPanelState,
  );
  const requestCounter = useRef(0);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const requestPreview = useCallback(async () => {
    if (validateGraphtecForm(state.form, inspection) !== null) {
      return;
    }
    requestCounter.current += 1;
    const requestId = requestCounter.current;
    dispatch({
      type: "previewRequested",
      requestId,
      formKey: graphtecFormKey(state.form),
    });
    try {
      const response = await onPreview(graphtecFormToSettings(state.form));
      if (mounted.current) {
        dispatch({ type: "previewSucceeded", requestId, response });
      }
    } catch (error) {
      if (mounted.current) {
        dispatch({
          type: "previewFailed",
          requestId,
          message: errorText(error, "The preview could not be generated."),
        });
      }
    }
  }, [inspection, onPreview, state.form]);

  useEffect(() => {
    if (disabled || !shouldAutoRefreshPreview(state, inspection)) {
      return;
    }
    const timer = window.setTimeout(() => {
      void requestPreview();
    }, PREVIEW_REFRESH_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [disabled, inspection, requestPreview, state]);

  const save = useCallback(async () => {
    if (!canSaveGraphtec(state, inspection, disabled)) {
      return;
    }
    dispatch({ type: "saveStarted" });
    try {
      const response = await onSave(graphtecFormToSettings(state.form));
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
  }, [disabled, inspection, onSave, state]);

  return (
    <GraphtecAnalysisView
      inspection={inspection}
      state={state}
      disabled={disabled}
      dispatch={dispatch}
      onPreview={() => void requestPreview()}
      onSave={() => void save()}
    />
  );
}
