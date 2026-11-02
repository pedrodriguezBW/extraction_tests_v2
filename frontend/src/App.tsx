import { useCallback, useEffect, useMemo, useReducer, useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";

import { DataSourceSelector } from "./components/DataSourceSelector";
import { GraphtecAnalysis } from "./components/GraphtecAnalysis";
import { EvidencePhotos } from "./components/EvidencePhotos";
import { RenderedAssets } from "./components/RenderedAssets";
import { SimpatiAcquisitions } from "./components/SimpatiAcquisitions";
import { SimpatiChart } from "./components/SimpatiChart";
import {
  checkHealth,
  deleteRenderedAsset,
  fetchRenderedAsset,
  generateReport,
  getEvidencePhotoUrl,
  getRenderedAssetUrl,
  inspectGraphtec,
  inspectProject,
  inspectSimpati,
  listRenderedAssets,
  previewGraphtecChart,
  saveGraphtecChart,
  saveSimpatiChart,
} from "./services/api";
import {
  canAnalyzeGraphtec,
  canAnalyzeSimpati,
  dataSelectionReducer,
  dataSourceOptions,
  fileSelectorHint,
  graphtecAnalysisHint,
  INITIAL_DATA_SELECTION,
  isFileSelectorDisabled,
  pendingSourceMessage,
  simpatiAnalysisHint,
  simpatiAnalysisSummary,
  simpatiStatusLabel,
  sourceFiles,
} from "./services/dataSourceSelection";
import {
  buildResourceSummary,
  canGenerateReport,
  evidenceLabel,
  metadataStatus,
  type ResultStatus,
} from "./services/projectStatus";
import {
  INITIAL_RENDERED_ASSET_SELECTION,
  renderedAssetSelectionReducer,
  renderedAssetSelectionSummary,
  selectedRenderedAssetCount,
  selectedRenderedAssetPaths,
} from "./services/renderedAssetSelection";
import {
  INITIAL_EVIDENCE_PHOTO_SELECTION,
  evidencePhotoReportSummary,
  evidencePhotoSelectionReducer,
  selectedEvidencePhotoPaths,
} from "./services/evidencePhotoSelection";
import type {
  DataSourceKey,
  ProjectInspectionResponse,
} from "./types/project";
import type {
  GraphtecChartSaveResponse,
  GraphtecChartSettings,
} from "./types/graphtec";
import type { ReportGenerationResponse } from "./types/report";
import type { SimpatiChartSaveResponse } from "./types/simpati";

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
 * detectados, gestiona los flujos opcionales de SIMPATI y Graphtec, mantiene
 * el inventario genérico de imágenes de `04_Report/_RenderedAssets` con la
 * selección del usuario e inicia la generación del informe PowerPoint con
 * la lista ordenada de imágenes seleccionadas.
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
  const [dataSelection, dispatchDataSelection] = useReducer(
    dataSelectionReducer,
    INITIAL_DATA_SELECTION,
  );
  const simpati = dataSelection.simpati;
  const graphtec = dataSelection.graphtec;
  const [graphtecLoading, setGraphtecLoading] = useState(false);
  const [graphtecSaving, setGraphtecSaving] = useState(false);
  const [simpatiChartSaving, setSimpatiChartSaving] = useState(false);
  const [renderedAssets, dispatchRenderedAssets] = useReducer(
    renderedAssetSelectionReducer,
    INITIAL_RENDERED_ASSET_SELECTION,
  );
  const [renderedAssetsLoading, setRenderedAssetsLoading] = useState(false);
  const [evidencePhotos, dispatchEvidencePhotos] = useReducer(
    evidencePhotoSelectionReducer,
    INITIAL_EVIDENCE_PHOTO_SELECTION,
  );
  const [deletingRenderedAssetPath, setDeletingRenderedAssetPath] =
    useState<string | null>(null);
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
    dispatchDataSelection({ type: "reset" });
    dispatchRenderedAssets({ type: "reset" });
    dispatchEvidencePhotos({ type: "reset" });
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

  const graphtecOperationActive = graphtecLoading || graphtecSaving;
  const renderedAssetsBusy =
    renderedAssetsLoading || deletingRenderedAssetPath !== null;

  /**
   * Refresca el inventario genérico de `_RenderedAssets`. La selección de
   * las imágenes que siguen existiendo se conserva; las nuevas se
   * seleccionan por defecto y las eliminadas desaparecen.
   */
  const refreshRenderedAssets = useCallback(
    async (testRoot: string, showLoading = true): Promise<void> => {
      if (showLoading) {
        setRenderedAssetsLoading(true);
      }

      try {
        const response = await listRenderedAssets(testRoot);
        dispatchRenderedAssets({
          type: "inventoryLoaded",
          assets: response.assets,
          warnings: response.warnings,
        });
      } finally {
        if (showLoading) {
          setRenderedAssetsLoading(false);
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
      renderedAssetsBusy ||
      graphtecOperationActive ||
      reportLoading
    ) {
      return;
    }

    setInspectionLoading(true);
    setCurrentError(null);
    setOperationMessage(null);
    setInspection(null);
    dispatchDataSelection({ type: "reset" });
    setReport(null);

    try {
      const response = await inspectProject(selectedPath);
      setInspection(response);
      // Same test folder: the photo selection survives a new inspection.
      dispatchEvidencePhotos({
        type: "inspectionLoaded",
        evidences: response.evidences,
      });
      await refreshRenderedAssets(selectedPath);
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
    renderedAssetsBusy,
    graphtecOperationActive,
    reportLoading,
    refreshRenderedAssets,
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
      renderedAssetsBusy ||
      graphtecOperationActive ||
      reportLoading
    ) {
      return;
    }

    setReportLoading(true);
    setCurrentError(null);
    setOperationMessage(null);
    setReport(null);

    try {
      // The explicit, ordered selection is what the backend receives. An
      // empty list deliberately generates the report without result images.
      const selectedAssets = selectedRenderedAssetPaths(renderedAssets);
      const imageCount = selectedAssets.length;
      setOperationMessage(
        imageCount === 0
          ? "No rendered images are selected. Generating report without them..."
          : `${imageCount} selected image${
              imageCount === 1 ? "" : "s"
            } will be included. Generating report...`,
      );
      const response = await generateReport(selectedPath, selectedAssets, {
        assembly: selectedEvidencePhotoPaths(evidencePhotos, "assembly"),
        results: selectedEvidencePhotoPaths(evidencePhotos, "results"),
      });
      setReport(response);
      const usedCount = response.rendered_assets_count;
      setOperationMessage(
        usedCount === 0
          ? "The PowerPoint report was generated without result images."
          : `The PowerPoint report was generated with ${usedCount} result image${
              usedCount === 1 ? "" : "s"
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
    renderedAssetsBusy,
    graphtecOperationActive,
    reportLoading,
    renderedAssets,
    evidencePhotos,
    selectedPath,
  ]);

  const inspectSelectedSimpati = useCallback(async (
    targetRelativePath?: string,
  ) => {
    // Every acquisition is analyzed; the selected one (or the one opened
    // from the acquisitions list) is previewed in the chart editor.
    const fileRelativePath =
      targetRelativePath ?? dataSelection.fileRelativePath;
    if (
      !selectedPath ||
      fileRelativePath === null ||
      !canAnalyzeSimpati({
        inspection,
        selection: {
          sourceKey: dataSelection.sourceKey,
          fileRelativePath,
        },
        backendConnected: backendStatus === "connected",
        busy:
          inspectionLoading ||
          simpatiLoading ||
          simpatiChartSaving ||
          renderedAssetsBusy ||
          graphtecOperationActive ||
          reportLoading,
      })
    ) {
      return;
    }

    setSimpatiLoading(true);
    setCurrentError(null);
    setOperationMessage(null);
    if (fileRelativePath !== dataSelection.fileRelativePath) {
      dispatchDataSelection({ type: "fileSelected", fileRelativePath });
    }
    dispatchDataSelection({ type: "simpatiCleared" });

    try {
      const response = await inspectSimpati(selectedPath, fileRelativePath);
      dispatchDataSelection({
        type: "simpatiInspected",
        fileRelativePath,
        result: response,
      });
      setOperationMessage(simpatiAnalysisSummary(response));
    } catch (error) {
      setCurrentError(errorMessage(error));
    } finally {
      setSimpatiLoading(false);
    }
  }, [
    backendStatus,
    dataSelection,
    inspection,
    inspectionLoading,
    simpatiChartSaving,
    renderedAssetsBusy,
    graphtecOperationActive,
    reportLoading,
    selectedPath,
    simpatiLoading,
  ]);

  const analyzeSelectedGraphtec = useCallback(async () => {
    const fileRelativePath = dataSelection.fileRelativePath;
    if (
      !selectedPath ||
      fileRelativePath === null ||
      !canAnalyzeGraphtec({
        inspection,
        selection: dataSelection,
        backendConnected: backendStatus === "connected",
        busy:
          inspectionLoading ||
          simpatiLoading ||
          simpatiChartSaving ||
          renderedAssetsBusy ||
          graphtecOperationActive ||
          reportLoading,
      })
    ) {
      return;
    }

    setGraphtecLoading(true);
    setCurrentError(null);
    setOperationMessage(null);
    dispatchDataSelection({ type: "graphtecCleared" });

    try {
      const response = await inspectGraphtec(selectedPath, fileRelativePath);
      dispatchDataSelection({
        type: "graphtecInspected",
        fileRelativePath,
        result: response,
      });
      setOperationMessage("The Graphtec file was analyzed successfully.");
    } catch (error) {
      setCurrentError(errorMessage(error));
    } finally {
      setGraphtecLoading(false);
    }
  }, [
    backendStatus,
    dataSelection,
    renderedAssetsBusy,
    graphtecOperationActive,
    inspection,
    inspectionLoading,
    reportLoading,
    selectedPath,
    simpatiChartSaving,
    simpatiLoading,
  ]);

  const previewSelectedGraphtecChart = useCallback(
    (settings: GraphtecChartSettings) => {
      const relativePath = dataSelection.graphtec?.relative_path;
      if (!selectedPath || !relativePath) {
        return Promise.reject(
          new Error("Analyze a Graphtec file before previewing the chart."),
        );
      }
      return previewGraphtecChart(selectedPath, relativePath, settings);
    },
    [dataSelection.graphtec?.relative_path, selectedPath],
  );

  const saveSelectedGraphtecChart = useCallback(
    async (
      settings: GraphtecChartSettings,
    ): Promise<GraphtecChartSaveResponse> => {
      const relativePath = dataSelection.graphtec?.relative_path;
      if (!selectedPath || !relativePath) {
        throw new Error("Analyze a Graphtec file before saving the chart.");
      }
      setGraphtecSaving(true);
      setCurrentError(null);
      setOperationMessage(null);
      try {
        const response = await saveGraphtecChart(
          selectedPath,
          relativePath,
          settings,
        );
        // The saved chart joins the generic inventory and is selected by
        // default for the report.
        dispatchRenderedAssets({
          type: "inventoryLoaded",
          assets: response.assets,
          warnings: response.warnings,
        });
        setOperationMessage(
          `Graphtec chart saved as ${response.chart_name ?? "PNG image"}.`,
        );
        return response;
      } finally {
        setGraphtecSaving(false);
      }
    },
    [dataSelection.graphtec?.relative_path, selectedPath],
  );

  const deleteSelectedRenderedAsset = useCallback(
    async (relativePath: string) => {
      if (!selectedPath) {
        return;
      }
      const asset = renderedAssets.assets.find(
        (candidate) => candidate.relative_path === relativePath,
      );
      const name = asset?.name ?? relativePath;
      const confirmed = window.confirm(
        `Delete ${name}? This removes it from 04_Report/_RenderedAssets and from the report.`,
      );
      if (!confirmed) {
        return;
      }
      setDeletingRenderedAssetPath(relativePath);
      setCurrentError(null);
      setOperationMessage(null);
      try {
        const response = await deleteRenderedAsset(selectedPath, relativePath);
        // Remove it from the inventory and the selection, then adopt the
        // refreshed inventory returned by the backend.
        dispatchRenderedAssets({ type: "removed", relativePath });
        dispatchRenderedAssets({
          type: "inventoryLoaded",
          assets: response.assets,
          warnings: response.warnings,
        });
        setOperationMessage(`${name} was deleted.`);
      } catch (error) {
        setCurrentError(errorMessage(error));
      } finally {
        setDeletingRenderedAssetPath(null);
      }
    },
    [renderedAssets.assets, selectedPath],
  );

  const openSelectedRenderedAsset = useCallback(
    async (relativePath: string): Promise<Blob> => {
      if (!selectedPath) {
        throw new Error("Select a test folder before opening the image.");
      }
      return fetchRenderedAsset(selectedPath, relativePath);
    },
    [selectedPath],
  );

  const toggleRenderedAsset = useCallback((relativePath: string) => {
    dispatchRenderedAssets({ type: "toggled", relativePath });
  }, []);

  const selectAllRenderedAssets = useCallback(() => {
    dispatchRenderedAssets({ type: "selectAll" });
  }, []);

  const clearRenderedAssetSelection = useCallback(() => {
    dispatchRenderedAssets({ type: "clearSelection" });
  }, []);

  const changeDataSource = useCallback(
    (sourceKey: DataSourceKey | null) => {
      if (sourceKey === dataSelection.sourceKey) {
        return;
      }
      dispatchDataSelection({ type: "sourceSelected", sourceKey });
      setCurrentError(null);
      setOperationMessage(null);
    },
    [dataSelection.sourceKey],
  );

  const changeDataSourceFile = useCallback(
    (fileRelativePath: string | null) => {
      if (fileRelativePath === dataSelection.fileRelativePath) {
        return;
      }
      dispatchDataSelection({ type: "fileSelected", fileRelativePath });
      setCurrentError(null);
      setOperationMessage(null);
    },
    [dataSelection.fileRelativePath],
  );

  const simpatiSourcePath = dataSelection.simpati?.selected_relative_path ?? null;

  const saveCurrentSimpatiChart = useCallback(
    async (imageBase64: string): Promise<SimpatiChartSaveResponse> => {
      if (!selectedPath) {
        throw new Error("Select a test folder before saving the chart.");
      }
      if (!simpatiSourcePath) {
        throw new Error("Analyze a SIMPATI acquisition before saving the chart.");
      }

      setSimpatiChartSaving(true);
      setCurrentError(null);
      setOperationMessage(null);

      try {
        const response = await saveSimpatiChart(
          selectedPath,
          simpatiSourcePath,
          imageBase64,
        );
        // The saved chart joins the generic inventory and is selected by
        // default for the report.
        dispatchRenderedAssets({
          type: "inventoryLoaded",
          assets: response.assets,
          warnings: response.warnings,
        });

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
    [selectedPath, simpatiSourcePath],
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
    renderedAssetsBusy ||
    graphtecOperationActive ||
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
    canAnalyzeSimpati({
      inspection,
      selection: dataSelection,
      backendConnected: backendStatus === "connected",
      busy,
    });
  const simpatiHint = simpatiAnalysisHint(inspection, dataSelection);
  const graphtecSelected = dataSelection.sourceKey === "graphtec";
  const canInspectGraphtec =
    selectedPath.length > 0 &&
    canAnalyzeGraphtec({
      inspection,
      selection: dataSelection,
      backendConnected: backendStatus === "connected",
      busy,
    });
  const graphtecHint = graphtecAnalysisHint(inspection, dataSelection);

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

              <EvidencePhotos
                state={evidencePhotos}
                disabled={busy}
                getImageUrl={(relativePath) =>
                  getEvidencePhotoUrl(selectedPath, relativePath)
                }
                onToggle={(section, relativePath) =>
                  dispatchEvidencePhotos({
                    type: "toggled",
                    section,
                    relativePath,
                  })
                }
                onSelectAll={(section) =>
                  dispatchEvidencePhotos({ type: "selectAll", section })
                }
                onClearSelection={(section) =>
                  dispatchEvidencePhotos({ type: "clearSelection", section })
                }
                onSelectEvidence={(section, evidenceKey) =>
                  dispatchEvidencePhotos({
                    type: "selectEvidence",
                    section,
                    evidenceKey,
                  })
                }
                onClearEvidence={(section, evidenceKey) =>
                  dispatchEvidencePhotos({
                    type: "clearEvidence",
                    section,
                    evidenceKey,
                  })
                }
              />
            </>
          )}

          {inspection && (
            <DataSourceSelector
              options={dataSourceOptions(inspection)}
              selectedSourceKey={dataSelection.sourceKey}
              files={sourceFiles(inspection, dataSelection.sourceKey)}
              selectedFileRelativePath={dataSelection.fileRelativePath}
              fileSelectorDisabled={isFileSelectorDisabled(
                inspection,
                dataSelection.sourceKey,
              )}
              fileHint={fileSelectorHint(inspection, dataSelection.sourceKey)}
              pendingMessage={pendingSourceMessage(
                inspection,
                dataSelection.sourceKey,
              )}
              disabled={busy}
              onSourceChange={changeDataSource}
              onFileChange={changeDataSourceFile}
            />
          )}

          {graphtecSelected ? (
            <div className="section-actions">
              <button
                className="button button--primary"
                type="button"
                onClick={() => void analyzeSelectedGraphtec()}
                disabled={!canInspectGraphtec}
              >
                {graphtecLoading
                  ? "Analyzing Graphtec..."
                  : "Analyze Graphtec"}
              </button>
              {graphtecHint && (
                <span className="action-hint">{graphtecHint}</span>
              )}
            </div>
          ) : (
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
              {simpatiHint && (
                <span className="action-hint">{simpatiHint}</span>
              )}
            </div>
          )}

          {graphtecSelected && graphtecLoading && (
            <p className="loading-text" role="status">
              Reading the Graphtec file...
            </p>
          )}

          {graphtecSelected && graphtec && (
            <GraphtecAnalysis
              key={graphtec.relative_path ?? "graphtec"}
              inspection={graphtec}
              disabled={busy}
              onPreview={previewSelectedGraphtecChart}
              onSave={saveSelectedGraphtecChart}
            />
          )}

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
                  <span>SIMPATI acquisitions</span>
                  <h3>
                    {simpati.found_count} acquisition
                    {simpati.found_count === 1 ? "" : "s"} in 03_Data/01_SIMPATI
                  </h3>
                </div>
                <span
                  className={`overall-status ${
                    simpati.incompatible_count > 0
                      ? "overall-status--error"
                      : "overall-status--success"
                  }`}
                >
                  SIMPATI analyzed
                </span>
              </div>

              <SimpatiAcquisitions
                result={simpati}
                disabled={busy}
                onSelect={(relativePath) =>
                  void inspectSelectedSimpati(relativePath)
                }
              />
            </div>
          )}

          {simpati?.available && simpati.selected_relative_path && (
            <div className="result-panel">
              <div className="result-panel__header">
                <div>
                  <span>
                    Acquisition{" "}
                    {simpati.selected_index !== null
                      ? `x${String(simpati.selected_index).padStart(2, "0")}`
                      : ""}
                  </span>
                  <h3>{simpati.file_name ?? "SIMPATI acquisition"}</h3>
                </div>
                {simpati.selected_status && (
                  <span
                    className={`overall-status ${
                      simpati.selected_status === "ready"
                        ? "overall-status--success"
                        : "overall-status--error"
                    }`}
                  >
                    {simpatiStatusLabel(simpati.selected_status)}
                  </span>
                )}
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
                <div>
                  <dt>Channels</dt>
                  <dd>{simpati.channels.length}</dd>
                </div>
                <div>
                  <dt>Thermal channels</dt>
                  <dd>{simpati.thermal_channels.length}</dd>
                </div>
              </dl>

              <div className="metadata-path">
                <span>Acquisition file</span>
                <code title={simpati.file_path ?? undefined}>
                  {simpati.file_path}
                </code>
              </div>

              {simpati.errors.map((error) => (
                <div
                  key={`${error.code}-${error.message}`}
                  className="simpati-save-status simpati-save-status--error"
                  role="alert"
                >
                  {error.message}
                </div>
              ))}

              {simpati.selected_status === "no_thermal_channels" && (
                <p className="action-hint">
                  No thermal channel of this acquisition is recognized. Its
                  channels remain available as advanced channels.
                </p>
              )}

              {simpati.records_count > 0 && (
                <SimpatiChart
                  key={simpati.selected_relative_path}
                  data={simpati}
                  title={`SIMPATI ${
                    simpati.selected_index !== null
                      ? `x${String(simpati.selected_index).padStart(2, "0")} · `
                      : ""
                  }${simpati.file_name ?? ""}`}
                  saving={simpatiChartSaving}
                  savedChartNames={renderedAssets.assets.map(
                    (asset) => asset.name,
                  )}
                  onSave={saveCurrentSimpatiChart}
                />
              )}
            </div>
          )}

          {inspection !== null && (
            <RenderedAssets
              state={renderedAssets}
              loading={renderedAssetsLoading}
              deletingRelativePath={deletingRenderedAssetPath}
              disabled={busy && !renderedAssetsBusy}
              getImageUrl={(relativePath) =>
                getRenderedAssetUrl(selectedPath, relativePath)
              }
              onToggle={toggleRenderedAsset}
              onSelectAll={selectAllRenderedAssets}
              onClearSelection={clearRenderedAssetSelection}
              onOpen={openSelectedRenderedAsset}
              onDelete={(relativePath) =>
                void deleteSelectedRenderedAsset(relativePath)
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
              selectedRenderedAssetCount(renderedAssets) === 0
                ? "report-chart-status--neutral"
                : "report-chart-status--ready"
            }`}
            aria-live="polite"
          >
            {renderedAssetSelectionSummary(renderedAssets)}
          </div>

          {inspection !== null && (
            <div
              className="report-chart-status report-chart-status--neutral report-photo-status"
              aria-live="polite"
            >
              {evidencePhotoReportSummary(evidencePhotos)}
            </div>
          )}

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

              <p className="report-images-used">
                {report.rendered_assets_count === 0
                  ? "No result images were included."
                  : `${report.rendered_assets_count} result image${
                      report.rendered_assets_count === 1 ? "" : "s"
                    } included in Test Results.`}
              </p>
              <p className="report-images-used">
                {`Evidence photos: ${report.assembly_photos_count ?? 0} in Test Assembly, ${
                  report.result_photos_count ?? 0
                } in Test Results.`}
              </p>
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
