import { useEffect, useId, useState } from "react";

import {
  formatFileSize,
  isRenderedAssetSelected,
  renderedAssetSelectionSummary,
  renderedAssetSourceLabel,
  selectedRenderedAssetCount,
  type RenderedAssetSelectionState,
} from "../services/renderedAssetSelection";
import type { RenderedAsset } from "../types/renderedAssets";

/**
 * Propiedades de la sección genérica de imágenes del informe.
 */
export interface RenderedAssetsProps {
  /** Inventario y selección actuales. */
  state: RenderedAssetSelectionState;

  /** Indica si el inventario se está actualizando. */
  loading: boolean;

  /** Ruta relativa de la imagen que se está eliminando. */
  deletingRelativePath: string | null;

  /** Deshabilita las acciones mientras otra operación está en curso. */
  disabled?: boolean;

  /** Construye la URL de la miniatura. */
  getImageUrl: (relativePath: string) => string;

  /** Marca o desmarca una imagen. */
  onToggle: (relativePath: string) => void;

  /** Selecciona todas las imágenes. */
  onSelectAll: () => void;

  /** Vacía la selección. */
  onClearSelection: () => void;

  /** Recupera la imagen completa. */
  onOpen: (relativePath: string) => Promise<Blob>;

  /** Solicita la eliminación de una imagen. */
  onDelete: (relativePath: string) => void;
}

interface OpenedAsset {
  asset: RenderedAsset;
  objectUrl: string | null;
}

function itemStateClass(
  selected: boolean,
  deleting: boolean,
  disabled: boolean,
): string {
  if (deleting) {
    return "rendered-assets__item--deleting";
  }
  if (disabled) {
    return "rendered-assets__item--unavailable";
  }
  return selected
    ? "rendered-assets__item--selected"
    : "rendered-assets__item--unselected";
}

/**
 * Muestra el inventario genérico de `04_Report/_RenderedAssets` y permite
 * elegir qué imágenes se incluyen en el PowerPoint.
 *
 * Cada imagen compatible, sea cual sea su origen (SIMPATI, Graphtec, manual
 * o futuras fuentes), aparece una sola vez con una casilla de selección, una
 * miniatura, su nombre, su procedencia y las acciones de abrir y eliminar.
 *
 * @returns La sección de imágenes del informe y el diálogo de vista previa.
 */
export function RenderedAssets({
  state,
  loading,
  deletingRelativePath,
  disabled = false,
  getImageUrl,
  onToggle,
  onSelectAll,
  onClearSelection,
  onOpen,
  onDelete,
}: RenderedAssetsProps) {
  const headingId = useId();
  const [openingPath, setOpeningPath] = useState<string | null>(null);
  const [opened, setOpened] = useState<OpenedAsset | null>(null);
  const [openError, setOpenError] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      if (opened?.objectUrl) {
        URL.revokeObjectURL(opened.objectUrl);
      }
    };
  }, [opened?.objectUrl]);

  useEffect(() => {
    if (!opened) {
      return;
    }

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpened(null);
      }
    };

    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [opened]);

  const openAsset = async (asset: RenderedAsset) => {
    setOpeningPath(asset.relative_path);
    setOpenError(null);
    setOpened({ asset, objectUrl: null });

    try {
      const imageBlob = await onOpen(asset.relative_path);
      setOpened({ asset, objectUrl: URL.createObjectURL(imageBlob) });
    } catch (error) {
      setOpenError(
        error instanceof Error
          ? error.message
          : "The image could not be opened.",
      );
      setOpened(null);
    } finally {
      setOpeningPath(null);
    }
  };

  const total = state.assets.length;
  const selectedCount = selectedRenderedAssetCount(state);
  const summary = renderedAssetSelectionSummary(state);
  const busy = disabled || loading || deletingRelativePath !== null;

  return (
    <section className="rendered-assets" aria-labelledby={headingId}>
      <div className="rendered-assets__heading">
        <div>
          <h3 id={headingId}>Report images</h3>
          <p>
            Images saved in 04_Report/_RenderedAssets. Select the ones to
            include in Test Results; they are inserted in the order shown.
          </p>
        </div>
        <span className="rendered-assets__count" aria-live="polite">
          {summary}
        </span>
      </div>

      {total > 0 && (
        <div className="rendered-assets__toolbar">
          <button
            className="button button--quiet"
            type="button"
            onClick={onSelectAll}
            disabled={busy || selectedCount === total}
          >
            Select all
          </button>
          <button
            className="button button--quiet"
            type="button"
            onClick={onClearSelection}
            disabled={busy || selectedCount === 0}
          >
            Clear selection
          </button>
        </div>
      )}

      {openError && (
        <div className="rendered-assets__status rendered-assets__status--error" role="alert">
          {openError}
        </div>
      )}

      {loading ? (
        <p className="loading-text" role="status">
          Refreshing report images...
        </p>
      ) : total === 0 ? (
        <div className="empty-state">{summary}</div>
      ) : (
        <ol className="rendered-assets__list" aria-label="Report images">
          {state.assets.map((asset) => {
            const selected = isRenderedAssetSelected(state, asset.relative_path);
            const deleting = deletingRelativePath === asset.relative_path;
            const checkboxId = `${headingId}-${asset.relative_path}`;

            return (
              <li
                key={asset.relative_path}
                className={`rendered-assets__item ${itemStateClass(
                  selected,
                  deleting,
                  disabled,
                )}`}
                aria-busy={deleting}
              >
                <div className="rendered-assets__select">
                  <input
                    id={checkboxId}
                    type="checkbox"
                    checked={selected}
                    disabled={busy}
                    onChange={() => onToggle(asset.relative_path)}
                    aria-label={`Include ${asset.name} in the report`}
                  />
                </div>

                <button
                  className="rendered-assets__preview"
                  type="button"
                  onClick={() => void openAsset(asset)}
                  disabled={deleting}
                  aria-label={`Open ${asset.name}`}
                >
                  <img
                    src={getImageUrl(asset.relative_path)}
                    alt={`Preview of ${asset.name}`}
                  />
                </button>

                <div className="rendered-assets__details">
                  <label htmlFor={checkboxId}>
                    <strong>{asset.name}</strong>
                  </label>
                  <span className="rendered-assets__meta">
                    <span
                      className={`rendered-assets__source rendered-assets__source--${asset.source.toLowerCase()}`}
                    >
                      {renderedAssetSourceLabel(asset.source)}
                    </span>
                    <span>{formatFileSize(asset.size)}</span>
                    <span className="rendered-assets__state">
                      {deleting
                        ? "Deleting..."
                        : selected
                          ? "Included in the report"
                          : "Not included"}
                    </span>
                  </span>
                  <code title={asset.relative_path}>{asset.relative_path}</code>
                </div>

                <div className="rendered-assets__actions">
                  <button
                    className="button button--secondary"
                    type="button"
                    disabled={deleting || openingPath === asset.relative_path}
                    onClick={() => void openAsset(asset)}
                  >
                    {openingPath === asset.relative_path
                      ? "Opening..."
                      : "Open image"}
                  </button>
                  <button
                    className="button button--danger"
                    type="button"
                    disabled={busy}
                    onClick={() => onDelete(asset.relative_path)}
                  >
                    {deleting ? "Deleting..." : "Delete"}
                  </button>
                </div>
              </li>
            );
          })}
        </ol>
      )}

      {state.warnings.length > 0 && (
        <div className="message-panel message-panel--warning rendered-assets__warnings">
          <h4>Files not available for the report</h4>
          <ul>
            {state.warnings.map((warning) => (
              <li key={warning.name}>{warning.message}</li>
            ))}
          </ul>
        </div>
      )}

      {opened && (
        <div
          className="saved-chart-modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="rendered-asset-modal-title"
          onClick={() => setOpened(null)}
        >
          <div
            className="saved-chart-modal__content"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="saved-chart-modal__header">
              <h3 id="rendered-asset-modal-title">{opened.asset.name}</h3>
              <button
                className="button button--quiet"
                type="button"
                onClick={() => setOpened(null)}
              >
                Close
              </button>
            </div>
            <img
              src={opened.objectUrl ?? undefined}
              alt={`Full preview of ${opened.asset.name}`}
              hidden={!opened.objectUrl}
            />
            {!opened.objectUrl && (
              <div className="saved-chart-modal__loading" role="status">
                Loading image...
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
