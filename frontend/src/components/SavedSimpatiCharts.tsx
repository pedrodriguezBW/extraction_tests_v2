import { useEffect, useState } from "react";

import type { SimpatiSavedChart } from "../types/simpati";


/**
 * Propiedades necesarias para mostrar y gestionar las gráficas SIMPATI
 * guardadas.
 */
export interface SavedSimpatiChartsProps {
  /** Gráficas almacenadas para el ensayo seleccionado. */
  charts: SimpatiSavedChart[];

  /** Indica si se está actualizando la lista de gráficas. */
  loading: boolean;

  /** Nombre de la gráfica que se está eliminando. */
  deletingChartName: string | null;

  /**
   * Construye la URL utilizada para mostrar la vista previa.
   *
   * @param chartName Nombre del archivo de la gráfica.
   * @returns La URL de la imagen.
   */
  getImageUrl: (chartName: string) => string;

  /**
   * Recupera una gráfica guardada.
   *
   * @param chartName Nombre del archivo de la gráfica.
   * @returns El contenido binario de la imagen.
   */
  onOpen: (chartName: string) => Promise<Blob>;

  /**
   * Solicita la eliminación de una gráfica.
   *
   * @param chartName Nombre del archivo de la gráfica.
   */
  onDelete: (chartName: string) => void;
}

interface OpenedChart {
  chartName: string;
  objectUrl: string | null;
}

function formatFileSize(sizeBytes: number): string {
  if (sizeBytes < 1024) {
    return `${sizeBytes} B`;
  }

  if (sizeBytes < 1024 * 1024) {
    return `${(sizeBytes / 1024).toFixed(1)} KB`;
  }

  return `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`;
}


/**
 * Muestra y gestiona las gráficas SIMPATI guardadas para el ensayo
 * seleccionado.
 *
 * Las gráficas se presentan en el orden en el que se incluirán en el informe
 * PowerPoint. El componente permite solicitar la imagen completa, mostrarla
 * en una vista modal y delegar su eliminación en el componente padre.
 *
 * Las URL temporales creadas para las vistas previas se liberan cuando dejan
 * de ser necesarias.
 *
 * @returns La lista de gráficas guardadas y el diálogo de vista previa.
 */

export function SavedSimpatiCharts({
  charts,
  loading,
  deletingChartName,
  getImageUrl,
  onOpen,
  onDelete,
}: SavedSimpatiChartsProps) {
  const [openingChartName, setOpeningChartName] =
    useState<string | null>(null);
  const [openedChart, setOpenedChart] = useState<OpenedChart | null>(null);
  const [openError, setOpenError] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      if (openedChart?.objectUrl) {
        URL.revokeObjectURL(openedChart.objectUrl);
      }
    };
  }, [openedChart?.objectUrl]);

  useEffect(() => {
    if (!openedChart) {
      return;
    }

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpenedChart(null);
      }
    };

    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [openedChart]);

  const openChart = async (chartName: string) => {
    setOpeningChartName(chartName);
    setOpenError(null);
    setOpenedChart({
      chartName,
      objectUrl: null,
    });

    try {
      const imageBlob = await onOpen(chartName);
      const objectUrl = URL.createObjectURL(imageBlob);
      setOpenedChart({
        chartName,
        objectUrl,
      });
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "The saved chart could not be opened.";
      setOpenError(message);
      setOpenedChart(null);
    } finally {
      setOpeningChartName(null);
    }
  };

  return (
    <div className="saved-simpati">
      <div className="saved-simpati__heading">
        <div>
          <h3>Saved charts for Test Results</h3>
          <p>
            These images are included in the PowerPoint in the order shown.
          </p>
        </div>
        <span className="saved-simpati__count">
          {charts.length} chart{charts.length === 1 ? "" : "s"}
        </span>
      </div>

      {loading ? (
        <p className="loading-text">Refreshing saved charts...</p>
      ) : charts.length === 0 ? (
        <div className="empty-state">
          No saved SIMPATI charts. The report can still be generated.
        </div>
      ) : (
        <>
          {openError && (
            <div
              className="simpati-save-status simpati-save-status--error"
              role="alert"
            >
              {openError}
            </div>
          )}

          <ol className="saved-simpati__list">
            {charts.map((chart) => (
              <li key={chart.chart_name} className="saved-simpati__item">
                <button
                  className="saved-simpati__preview"
                  type="button"
                  onClick={() => void openChart(chart.chart_name)}
                  aria-label={`Open ${chart.chart_name}`}
                >
                  <img
                    src={getImageUrl(chart.chart_name)}
                    alt={`Preview of ${chart.chart_name}`}
                  />
                </button>

                <div className="saved-simpati__details">
                  <strong>{chart.chart_name}</strong>
                  <span>{formatFileSize(chart.size_bytes)}</span>
                  <code title={chart.chart_path}>{chart.chart_path}</code>
                </div>

                <div className="saved-simpati__actions">
                  <button
                    className="button button--secondary"
                    type="button"
                    disabled={openingChartName === chart.chart_name}
                    onClick={() => void openChart(chart.chart_name)}
                  >
                    {openingChartName === chart.chart_name
                      ? "Opening..."
                      : "Open image"}
                  </button>
                  <button
                    className="button button--danger"
                    type="button"
                    disabled={deletingChartName === chart.chart_name}
                    onClick={() => onDelete(chart.chart_name)}
                  >
                    {deletingChartName === chart.chart_name
                      ? "Deleting..."
                      : "Delete"}
                  </button>
                </div>
              </li>
            ))}
          </ol>
        </>
      )}

      {openedChart && (
        <div
          className="saved-chart-modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="saved-chart-modal-title"
          onClick={() => setOpenedChart(null)}
        >
          <div
            className="saved-chart-modal__content"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="saved-chart-modal__header">
              <h3 id="saved-chart-modal-title">
                {openedChart.chartName}
              </h3>
              <button
                className="button button--quiet"
                type="button"
                onClick={() => setOpenedChart(null)}
              >
                Close
              </button>
            </div>
            <img
              src={openedChart.objectUrl ?? undefined}
              alt={`Full preview of ${openedChart.chartName}`}
              hidden={!openedChart.objectUrl}
            />
            {!openedChart.objectUrl && (
              <div className="saved-chart-modal__loading" role="status">
                Loading image from FastAPI...
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
