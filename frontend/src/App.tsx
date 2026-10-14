import { useCallback, useEffect, useMemo, useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";

import { SavedSimpatiCharts } from "./components/SavedSimpatiCharts";
import { SimpatiChart } from "./components/SimpatiChart";
import {
  checkHealth,
  deleteSimpatiChart,
  fetchSimpatiChart,
  generateReport,
  getSimpatiChartUrl,
  inspectProject,
  inspectSimpati,
  listSimpatiCharts,
  saveSimpatiChart,
} from "./services/api";
import {
  buildResourceSummary,
  canGenerateReport,
  evidenceLabel,
  metadataStatus,
  type ResultStatus,
} from "./services/projectStatus";
import type { ProjectInspectionResponse } from "./types/project";
import type { ReportGenerationResponse } from "./types/report";
import type {
  SimpatiChartSaveResponse,
  SimpatiInspectionResponse,
  SimpatiSavedChart,
} from "./types/simpati";

type BackendStatus = "checking" | "connected" | "unavailable";

interface InspectionRow {
  label: string;
  status: ResultStatus;
  statusText: string;
  detail: string;
}

function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }
  return "An unexpected error occurred.";
}

function StatusMark({ status }: { status: ResultStatus }) {
  const icon =
    status === "success" ? (
      <path d="m4 8 2.3 2.3L12 4.8" />
    ) : status === "warning" ? (
      <>
        <path d="M8 4v5" />
        <path d="M8 12.2v.1" />
      </>
    ) : status === "unavailable" ? (
      <path d="M4 8h8" />
    ) : (
      <>
        <path d="m5 5 6 6" />
        <path d="m11 5-6 6" />
      </>
    );

  return (
    <span className={`status-mark status-mark--${status}`} aria-hidden="true">
      <svg viewBox="0 0 16 16" focusable="false">
        {icon}
      </svg>
    </span>
  );
}

/**
 * Coordina el flujo completo de la aplicación de escritorio para generar
 * informes climáticos.
 *
 * El componente comprueba la conexión con el backend, abre el selector nativo
 * de carpetas, solicita la inspección del ensayo, presenta los recursos
 * detectados, gestiona el flujo opcional de SIMPATI e inicia la generación
 * del informe PowerPoint.
 *
 * Las operaciones de dominio se delegan en el servicio de API y las reglas
 * reutilizables de inspección y disponibilidad se obtienen del servicio de
 * estado del proyecto.
 *
 * @returns La interfaz principal de la aplicación.
 */

function App() {
  const [backendStatus, setBackendStatus] =
    useState<BackendStatus>("checking");
  const [backendVersion, setBackendVersion] = useState<string | null>(null);
  const [selectedPath, setSelectedPath] = useState("");
  const [inspectionLoading, setInspectionLoading] = useState(false);
  const [inspection, setInspection] =
    useState<ProjectInspectionResponse | null>(null);
  const [simpatiLoading, setSimpatiLoading] = useState(false);
  const [simpati, setSimpati] =
    useState<SimpatiInspectionResponse | null>(null);
  const [simpatiChartSaving, setSimpatiChartSaving] = useState(false);
  const [savedSimpatiCharts, setSavedSimpatiCharts] =
    useState<SimpatiSavedChart[]>([]);
  const [savedChartsLoading, setSavedChartsLoading] = useState(false);
  const [deletingChartName, setDeletingChartName] =
    useState<string | null>(null);
  const [reportChartCount, setReportChartCount] = useState(0);
  const [reportLoading, setReportLoading] = useState(false);
  const [report, setReport] = useState<ReportGenerationResponse | null>(null);
  const [currentError, setCurrentError] = useState<string | null>(null);
  const [operationMessage, setOperationMessage] = useState<string | null>(null);

  const retryBackendConnection = useCallback(async () => {
    setBackendStatus("checking");
    setCurrentError(null);

    try {
      const response = await checkHealth();
      setBackendVersion(response.version);
      setBackendStatus("connected");
    } catch (error) {
      setBackendVersion(null);
      setBackendStatus("unavailable");
      setCurrentError(errorMessage(error));
    }
  }, []);

  useEffect(() => {
    void retryBackendConnection();
  }, [retryBackendConnection]);

  const resetProjectResults = useCallback(() => {
    setInspection(null);
    setSimpati(null);
    setSavedSimpatiCharts([]);
    setReportChartCount(0);
    setReport(null);
    setCurrentError(null);
    setOperationMessage(null);
  }, []);

  const selectDirectory = useCallback(async () => {
    try {
      const selection = await open({
        directory: true,
        multiple: false,
        title: "Select test folder",
      });

      if (selection === null) {
        return;
      }

      const nextPath = Array.isArray(selection) ? selection[0] : selection;
      if (!nextPath) {
        return;
      }

      setSelectedPath(nextPath);
      resetProjectResults();
    } catch (error) {
      setCurrentError(
        `The folder picker could not be opened. ${errorMessage(error)}`,
      );
    }
  }, [resetProjectResults]);

  const clearSelection = useCallback(() => {
    setSelectedPath("");
    resetProjectResults();
  }, [resetProjectResults]);

  const refreshSavedSimpatiCharts = useCallback(
    async (
      testRoot: string,
      showLoading = true,
    ): Promise<SimpatiSavedChart[]> => {
      if (showLoading) {
        setSavedChartsLoading(true);
      }

      try {
        const response = await listSimpatiCharts(testRoot);
        setSavedSimpatiCharts(response.charts);
        setReportChartCount(response.charts_count);
        return response.charts;
      } finally {
        if (showLoading) {
          setSavedChartsLoading(false);
        }
      }
    },
    [],
  );

  const inspectSelectedProject = useCallback(async () => {
    if (
      !selectedPath ||
      backendStatus !== "connected" ||
      inspectionLoading ||
      simpatiLoading ||
      simpatiChartSaving ||
      savedChartsLoading ||
      deletingChartName !== null ||
      reportLoading
    ) {
      return;
    }

    setInspectionLoading(true);
    setCurrentError(null);
    setOperationMessage(null);
    setInspection(null);
    setSimpati(null);
    setReport(null);

    try {
      const response = await inspectProject(selectedPath);
      setInspection(response);
      await refreshSavedSimpatiCharts(selectedPath);
      setOperationMessage(
        canGenerateReport(response)
          ? "The project is ready. Review its resources and generate the report."
          : "The inspection found errors that must be corrected.",
      );
    } catch (error) {
      setCurrentError(errorMessage(error));
    } finally {
      setInspectionLoading(false);
    }
  }, [
    backendStatus,
    inspectionLoading,
    simpatiLoading,
    simpatiChartSaving,
    savedChartsLoading,
    deletingChartName,
    reportLoading,
    refreshSavedSimpatiCharts,
    selectedPath,
  ]);

  const generateSelectedProjectReport = useCallback(async () => {
    if (
      !selectedPath ||
      !canGenerateReport(inspection) ||
      backendStatus !== "connected" ||
      inspectionLoading ||
      simpatiLoading ||
      simpatiChartSaving ||
      savedChartsLoading ||
      deletingChartName !== null ||
      reportLoading
    ) {
      return;
    }

    setReportLoading(true);
    setCurrentError(null);
    setOperationMessage(null);
    setReport(null);

    try {
      const currentCharts = await refreshSavedSimpatiCharts(
        selectedPath,
        false,
      );
      const chartCount = currentCharts.length;
      setOperationMessage(
        chartCount === 0
          ? "No saved SIMPATI charts will be included. Generating report..."
          : `${chartCount} saved SIMPATI chart${
              chartCount === 1 ? "" : "s"
            } will be included. Generating report...`,
      );
      const response = await generateReport(selectedPath);
      setReport(response);
      setOperationMessage(
        chartCount === 0
          ? "The PowerPoint report was generated without SIMPATI charts."
          : `The PowerPoint report was generated with ${chartCount} SIMPATI chart${
              chartCount === 1 ? "" : "s"
            }.`,
      );
    } catch (error) {
      setCurrentError(errorMessage(error));
    } finally {
      setReportLoading(false);
    }
  }, [
    backendStatus,
    inspection,
    inspectionLoading,
    simpatiLoading,
    simpatiChartSaving,
    savedChartsLoading,
    deletingChartName,
    reportLoading,
    refreshSavedSimpatiCharts,
    selectedPath,
  ]);

  const inspectSelectedSimpati = useCallback(async () => {
    if (
      !selectedPath ||
      inspection === null ||
      backendStatus !== "connected" ||
      inspectionLoading ||
      simpatiLoading ||
      simpatiChartSaving ||
      savedChartsLoading ||
      deletingChartName !== null ||
      reportLoading
    ) {
      return;
    }

    setSimpatiLoading(true);
    setCurrentError(null);
    setOperationMessage(null);
    setSimpati(null);

    try {
      const response = await inspectSimpati(selectedPath);
      setSimpati(response);
      setOperationMessage(
        response.available
          ? "The SIMPATI acquisition was inspected successfully."
          : "No SIMPATI acquisition file was found. Report generation can continue.",
      );
    } catch (error) {
      setCurrentError(errorMessage(error));
    } finally {
      setSimpatiLoading(false);
    }
  }, [
    backendStatus,
    inspection,
    inspectionLoading,
    simpatiChartSaving,
    savedChartsLoading,
    deletingChartName,
    reportLoading,
    selectedPath,
    simpatiLoading,
  ]);

  const saveCurrentSimpatiChart = useCallback(
    async (imageBase64: string): Promise<SimpatiChartSaveResponse> => {
      if (!selectedPath) {
        throw new Error("Select a test folder before saving the chart.");
      }

      setSimpatiChartSaving(true);
      setCurrentError(null);
      setOperationMessage(null);

      try {
        const response = await saveSimpatiChart(
          selectedPath,
          imageBase64,
        );
        setSavedSimpatiCharts(response.charts);
        setReportChartCount(response.charts_count);

        setOperationMessage(
          `Chart saved as ${response.chart_name ?? "PNG image"}.`,
        );
        return response;
      } catch (error) {
        setCurrentError(errorMessage(error));
        throw error;
      } finally {
        setSimpatiChartSaving(false);
      }
    },
    [selectedPath],
  );

  const deleteSavedSimpatiChart = useCallback(
    async (chartName: string) => {
      if (!selectedPath) {
        return;
      }

      const confirmed = window.confirm(
        `Delete ${chartName}? This removes it from Test Results.`,
      );
      if (!confirmed) {
        return;
      }

      setDeletingChartName(chartName);
      setCurrentError(null);
      setOperationMessage(null);

      try {
        const response = await deleteSimpatiChart(
          selectedPath,
          chartName,
        );
        setSavedSimpatiCharts(response.charts);
        setReportChartCount(response.charts_count);
        setOperationMessage(`${chartName} was deleted.`);
      } catch (error) {
        setCurrentError(errorMessage(error));
      } finally {
        setDeletingChartName(null);
      }
    },
    [selectedPath],
  );

  const openSavedSimpatiChart = useCallback(
    async (chartName: string): Promise<Blob> => {
      if (!selectedPath) {
        throw new Error("Select a test folder before opening the image.");
      }
      return fetchSimpatiChart(selectedPath, chartName);
    },
    [selectedPath],
  );

  const inspectionRows = useMemo<InspectionRow[]>(() => {
    if (!inspection) {
      return [];
    }

    const metadata = metadataStatus(inspection.metadata);
    const optionalFolder = (
      label: string,
      found: boolean,
      path: string,
      foundText = "Found",
    ): InspectionRow => ({
      label,
      status: found ? "success" : "warning",
      statusText: found ? foundText : "Folder not found",
      detail: path,
    });

    return [
      optionalFolder(
        "01_Inputs",
        inspection.inputs_directory.found,
        inspection.inputs_directory.path,
        `${inspection.inputs_directory.file_count ?? 0} file(s)`,
      ),
      optionalFolder(
        "02_Evidences",
        inspection.evidences.directory.found,
        inspection.evidences.directory.path,
      ),
      optionalFolder(
        "03_Data",
        inspection.data.directory.found,
        inspection.data.directory.path,
      ),
      {
        label: "04_Report",
        status: inspection.report_directory.found ? "success" : "error",
        statusText: inspection.report_directory.found
          ? "Found"
          : "Required folder missing",
        detail: inspection.report_directory.path,
      },
      {
        label: "test_metadata.json",
        status: metadata.status,
        statusText: inspection.metadata.found
          ? metadata.label
          : "Required file missing",
        detail:
          inspection.metadata.error ??
          inspection.metadata.path ??
          "Not found.",
      },
      {
        label: "PowerPoint template",
        status: inspection.powerpoint_template.found ? "success" : "error",
        statusText: inspection.powerpoint_template.found
          ? "Found"
          : "Required file missing",
        detail:
          inspection.powerpoint_template.name ??
          inspection.powerpoint_template.path ??
          "Not configured.",
      },
    ];
  }, [inspection]);

  const resourceSummary = useMemo(
    () => (inspection ? buildResourceSummary(inspection) : []),
    [inspection],
  );

  const busy =
    inspectionLoading ||
    simpatiLoading ||
    simpatiChartSaving ||
    savedChartsLoading ||
    deletingChartName !== null ||
    reportLoading;
  const canInspect =
    selectedPath.length > 0 &&
    backendStatus === "connected" &&
    !busy;
  const reportReady = canGenerateReport(inspection);
  const canGenerate =
    selectedPath.length > 0 &&
    backendStatus === "connected" &&
    reportReady &&
    !busy;
  const canInspectSimpati =
    selectedPath.length > 0 &&
    backendStatus === "connected" &&
    inspection !== null &&
    !busy;

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <p className="app-kicker">HVCH Testing</p>
          <h1>Climatic Report Generator</h1>
        </div>
        <div className="backend-summary">
          <span
            className={`connection-dot connection-dot--${backendStatus}`}
            aria-hidden="true"
          />
          <div>
            <strong>
              {backendStatus === "checking"
                ? "Checking connection"
                : backendStatus === "connected"
                  ? "Backend connected"
                  : "Backend unavailable"}
            </strong>
            <span>
              {backendVersion ? `Version ${backendVersion}` : "Local FastAPI"}
            </span>
          </div>
          {backendStatus === "unavailable" && (
            <button
              className="button button--quiet"
              type="button"
              onClick={() => void retryBackendConnection()}
              disabled={busy}
            >
              Retry
            </button>
          )}
        </div>
      </header>

      <main className="workspace">
        <section className="workflow-section" aria-labelledby="project-heading">
          <div className="section-heading">
            <div className="step-number">1</div>
            <div>
              <h2 id="project-heading">Select project</h2>
              <p>
                Select the individual test folder, for example TEST - 001.
                Browsing does not modify it.
              </p>
            </div>
          </div>

          <div className="path-control">
            <label htmlFor="test-root">Test folder</label>
            <div className="path-control__row">
              <input
                id="test-root"
                type="text"
                value={selectedPath}
                readOnly
                placeholder="No folder selected"
                title={selectedPath || undefined}
              />
              <button
                className="button button--secondary"
                type="button"
                onClick={() => void selectDirectory()}
                disabled={busy}
              >
                Browse
              </button>
              {selectedPath && (
                <button
                  className="button button--quiet"
                  type="button"
                  onClick={clearSelection}
                  disabled={busy}
                >
                  Clear
                </button>
              )}
            </div>
          </div>
        </section>

        <section
          className="workflow-section"
          aria-labelledby="inspection-heading"
        >
          <div className="section-heading">
            <div className="step-number">2</div>
            <div>
              <h2 id="inspection-heading">Inspect project</h2>
              <p>
                Check the folder structure, test_metadata.json, and the
                PowerPoint template.
              </p>
            </div>
            {inspection && (
              <span
                className={`overall-status ${
                  inspection.valid
                    ? "overall-status--success"
                    : "overall-status--error"
                }`}
              >
                {inspection.valid ? "Valid project" : "Invalid project"}
              </span>
            )}
          </div>

          <div className="section-actions">
            <button
              className="button button--primary"
              type="button"
              onClick={() => void inspectSelectedProject()}
              disabled={!canInspect}
            >
              {inspectionLoading
                ? "Inspecting project..."
                : "Inspect project"}
            </button>
            {!selectedPath && (
              <span className="action-hint">
                Select a test folder to enable the inspection.
              </span>
            )}
          </div>

          {!inspection && !inspectionLoading ? (
            <div className="empty-state inspection-empty-state">
              Inspect a folder to view its structure here.
            </div>
          ) : (
            <div className="inspection-list" aria-busy={inspectionLoading}>
              {inspectionLoading ? (
                <p className="loading-text">Analyzing the test folder...</p>
              ) : (
                inspectionRows.map((row) => (
                  <div className="inspection-row" key={row.label}>
                    <StatusMark status={row.status} />
                    <div className="inspection-row__label">
                      <strong>{row.label}</strong>
                      <span>{row.statusText}</span>
                    </div>
                    <div className="inspection-row__detail" title={row.detail}>
                      {row.detail}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {inspection &&
            (inspection.errors.length > 0 ||
              inspection.warnings.length > 0) && (
              <div className="messages-grid">
                {inspection.errors.length > 0 && (
                  <div className="message-panel message-panel--error">
                    <h3>Errors</h3>
                    <ul>
                      {inspection.errors.map((message) => (
                        <li key={message}>{message}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {inspection.warnings.length > 0 && (
                  <div className="message-panel message-panel--warning">
                    <h3>Warnings</h3>
                    <ul>
                      {inspection.warnings.map((message) => (
                        <li key={message}>{message}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
        </section>

        <section
          className="workflow-section"
          aria-labelledby="resources-heading"
        >
          <div className="section-heading">
            <div className="step-number">3</div>
            <div>
              <h2 id="resources-heading">Review project resources</h2>
              <p>
                Metadata, evidences, and optional acquisition sources detected
                in the test folder.
              </p>
            </div>
          </div>

          {!inspection ? (
            <div className="empty-state">
              Resources are listed after the project inspection.
            </div>
          ) : (
            <>
              <dl className="metrics-grid resource-metrics">
                {resourceSummary.map((item) => (
                  <div key={item.key}>
                    <dt>{item.label}</dt>
                    <dd title={item.note ?? undefined}>
                      {item.value}
                      {item.note && (
                        <span className="resource-metrics__note">
                          {item.note}
                        </span>
                      )}
                    </dd>
                  </div>
                ))}
              </dl>

              {inspection.evidences.evidences.length > 0 && (
                <ol className="evidence-list" aria-label="Evidences">
                  {inspection.evidences.evidences.map((evidence) => (
                    <li key={evidence.descriptor_path}>
                      <StatusMark
                        status={
                          evidence.photos_found_count === evidence.photos_count
                            ? "success"
                            : "warning"
                        }
                      />
                      <span className="evidence-list__sequence">
                        {evidence.sequence ?? "-"}
                      </span>
                      <span
                        className="evidence-list__title"
                        title={evidence.directory}
                      >
                        {evidenceLabel(evidence)}
                      </span>
                      <span className="evidence-list__photos">
                        {evidence.photos_found_count} / {evidence.photos_count}{" "}
                        photo{evidence.photos_count === 1 ? "" : "s"}
                      </span>
                    </li>
                  ))}
                </ol>
              )}
            </>
          )}

          <div className="section-actions">
            <button
              className="button button--primary"
              type="button"
              onClick={() => void inspectSelectedSimpati()}
              disabled={!canInspectSimpati}
            >
              {simpatiLoading
                ? "Analyzing SIMPATI..."
                : "Analyze SIMPATI"}
            </button>
            {inspection === null && (
              <span className="action-hint">
                SIMPATI analysis is enabled after project inspection.
              </span>
            )}
          </div>

          {simpati && !simpati.available && (
            <div className="empty-state simpati-empty-state">
              No SIMPATI acquisition file was found in 03_Data/01_SIMPATI.
              This optional step does not block PowerPoint generation.
            </div>
          )}

          {simpati?.available && (
            <div className="result-panel">
              <div className="result-panel__header">
                <div>
                  <span>Acquisition file</span>
                  <h3>{simpati.file_name ?? "SIMPATI acquisition"}</h3>
                </div>
                <span className="overall-status overall-status--success">
                  SIMPATI analyzed
                </span>
              </div>

              <dl className="metrics-grid simpati-metrics">
                <div>
                  <dt>Encoding</dt>
                  <dd>{simpati.encoding ?? "Unknown"}</dd>
                </div>
                <div>
                  <dt>Records</dt>
                  <dd>{simpati.records_count}</dd>
                </div>
                <div>
                  <dt>Acquisition start</dt>
                  <dd title={simpati.acquisition_start ?? undefined}>
                    {simpati.acquisition_start ?? "Not available"}
                  </dd>
                </div>
                <div>
                  <dt>Acquisition end</dt>
                  <dd title={simpati.acquisition_end ?? undefined}>
                    {simpati.acquisition_end ?? "Not available"}
                  </dd>
                </div>
              </dl>

              <div className="metadata-path">
                <span>Acquisition file</span>
                <code title={simpati.file_path ?? undefined}>
                  {simpati.file_path}
                </code>
              </div>

              <SimpatiChart
                data={simpati}
                saving={simpatiChartSaving}
                savedChartNames={savedSimpatiCharts.map(
                  (chart) => chart.chart_name,
                )}
                onSave={saveCurrentSimpatiChart}
              />

              <SavedSimpatiCharts
                charts={savedSimpatiCharts}
                loading={savedChartsLoading}
                deletingChartName={deletingChartName}
                getImageUrl={(chartName) =>
                  getSimpatiChartUrl(selectedPath, chartName)
                }
                onOpen={openSavedSimpatiChart}
                onDelete={(chartName) =>
                  void deleteSavedSimpatiChart(chartName)
                }
              />
            </div>
          )}

          {inspection !== null && !simpati?.available && (
            <SavedSimpatiCharts
              charts={savedSimpatiCharts}
              loading={savedChartsLoading}
              deletingChartName={deletingChartName}
              getImageUrl={(chartName) =>
                getSimpatiChartUrl(selectedPath, chartName)
              }
              onOpen={openSavedSimpatiChart}
              onDelete={(chartName) =>
                void deleteSavedSimpatiChart(chartName)
              }
            />
          )}
        </section>

        <section
          className="workflow-section"
          aria-labelledby="report-heading"
        >
          <div className="section-heading">
            <div className="step-number">4</div>
            <div>
              <h2 id="report-heading">Generate report</h2>
              <p>
                Create an editable PowerPoint in 04_Report from
                test_metadata.json and the configured template.
              </p>
            </div>
          </div>

          <div className="section-actions">
            <button
              className="button button--primary"
              type="button"
              onClick={() => void generateSelectedProjectReport()}
              disabled={!canGenerate}
            >
              {reportLoading
                ? "Generating PowerPoint..."
                : "Generate PowerPoint"}
            </button>
            {!reportReady && (
              <span className="action-hint">
                Report generation is enabled after a valid inspection with a
                valid test_metadata.json.
              </span>
            )}
          </div>

          <div
            className={`report-chart-status ${
              reportChartCount === 0
                ? "report-chart-status--neutral"
                : "report-chart-status--ready"
            }`}
            aria-live="polite"
          >
            {reportChartCount === 0
              ? "No saved SIMPATI charts will be included. The report can still be generated."
              : `${reportChartCount} saved SIMPATI chart${
                  reportChartCount === 1 ? "" : "s"
                } will be included in Test Results.`}
          </div>

          {report?.success && (
            <div className="result-panel">
              <div className="result-panel__header">
                <div>
                  <span>PowerPoint report</span>
                  <h3>{report.report_name ?? "Generated report"}</h3>
                </div>
                <span className="overall-status overall-status--success">
                  Report generated
                </span>
              </div>

              <div className="metadata-path">
                <span>Generated file</span>
                <code title={report.report_path ?? undefined}>
                  {report.report_path}
                </code>
              </div>
            </div>
          )}
        </section>

        <div className="dynamic-messages" aria-live="polite">
          {currentError && (
            <div className="message-panel message-panel--error" role="alert">
              <h2>Operation error</h2>
              <p>{currentError}</p>
            </div>
          )}
          {operationMessage && !currentError && (
            <p className="operation-message">{operationMessage}</p>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
