import { useId } from "react";

import {
  evidencePhotoSectionCounter,
  isAssemblyLimitReached,
  isEvidencePhotoSelected,
  sectionGroups,
  selectableEvidencePhotoCount,
  selectedEvidencePhotoCount,
  selectedPhotosInGroup,
  slidesForPhotos,
  type EvidencePhotoGroup,
  type EvidencePhotoSelectionState,
} from "../services/evidencePhotoSelection";
import type { EvidenceReportSection } from "../types/project";

/**
 * Propiedades de la selección de fotografías de evidencia.
 */
export interface EvidencePhotosProps {
  /** Evidencias y selección actuales. */
  state: EvidencePhotoSelectionState;

  /** Deshabilita las acciones mientras otra operación está en curso. */
  disabled?: boolean;

  /** Construye la URL de la miniatura. */
  getImageUrl: (relativePath: string) => string;

  /** Marca o desmarca una fotografía en su zona. */
  onToggle: (section: EvidenceReportSection, relativePath: string) => void;

  /** Selecciona todas las fotografías de una zona (Assembly: hasta el máximo). */
  onSelectAll: (section: EvidenceReportSection) => void;

  /** Vacía la selección de una zona. */
  onClearSelection: (section: EvidenceReportSection) => void;

  /** Selecciona las fotografías de una evidencia. */
  onSelectEvidence: (section: EvidenceReportSection, evidenceKey: string) => void;

  /** Desmarca las fotografías de una evidencia. */
  onClearEvidence: (section: EvidenceReportSection, evidenceKey: string) => void;
}

interface SectionCopy {
  number: string;
  title: string;
  badge: string;
  description: string;
  empty: string;
}

const SECTION_COPY: Record<EvidenceReportSection, SectionCopy> = {
  assembly: {
    number: "2",
    title: "Test Assembly",
    badge: "Assembly",
    description:
      "Photos of the initial-condition evidences, inserted in the Test Assembly section. Two per slide, up to 4 photos.",
    empty:
      "No initial-condition evidence photos were found. Test Assembly will be generated without photos.",
  },
  results: {
    number: "4",
    title: "Test Results",
    badge: "Results",
    description:
      "Photos of the remaining evidences, inserted in the Test Results section, one or more slides per evidence. Two per slide, no limit.",
    empty:
      "No evidences other than the initial condition were found. Test Results will contain only the selected report images.",
  },
};

function typeLabel(type: string | null): string {
  return (type ?? "").trim().replace(/_/g, " ");
}

interface EvidenceGroupProps {
  group: EvidencePhotoGroup;
  state: EvidencePhotoSelectionState;
  busy: boolean;
  limitReached: boolean;
  getImageUrl: (relativePath: string) => string;
  onToggle: EvidencePhotosProps["onToggle"];
  onSelectEvidence: EvidencePhotosProps["onSelectEvidence"];
  onClearEvidence: EvidencePhotosProps["onClearEvidence"];
}

function EvidenceGroup({
  group,
  state,
  busy,
  limitReached,
  getImageUrl,
  onToggle,
  onSelectEvidence,
  onClearEvidence,
}: EvidenceGroupProps) {
  const copy = SECTION_COPY[group.section];
  const selectable = group.photos.filter((photo) => photo.selectable);
  const selectedCount = selectedPhotosInGroup(state, group);
  const missing = group.photos.length - selectable.length;
  const slides = Math.max(1, slidesForPhotos(selectedCount, state.photosPerSlide));

  return (
    <li
      className={`evidence-photos__group evidence-photos__group--${group.section}`}
      aria-label={`${group.title} (${copy.title})`}
    >
      <div className="evidence-photos__group-heading">
        <span className="evidence-photos__sequence">
          #{group.sequence ?? "-"}
        </span>
        <strong>{group.title}</strong>
        {group.type && (
          <span className="evidence-photos__type">{typeLabel(group.type)}</span>
        )}
        {group.reference && (
          <span className="evidence-photos__reference">{group.reference}</span>
        )}
        <span className="evidence-photos__group-count">
          {selectedCount} / {selectable.length} photo
          {selectable.length === 1 ? "" : "s"}
          {group.section === "results" && ` · ${slides} slide${slides === 1 ? "" : "s"}`}
        </span>
        {selectable.length > 0 && (
          <span className="evidence-photos__group-actions">
            <button
              className="button button--quiet"
              type="button"
              disabled={
                busy ||
                selectedCount === selectable.length ||
                (group.section === "assembly" && limitReached)
              }
              onClick={() => onSelectEvidence(group.section, group.key)}
            >
              Select
            </button>
            <button
              className="button button--quiet"
              type="button"
              disabled={busy || selectedCount === 0}
              onClick={() => onClearEvidence(group.section, group.key)}
            >
              Clear
            </button>
          </span>
        )}
      </div>

      {group.section === "results" && selectedCount === 0 && (
        <p className="evidence-photos__note">
          No photos selected: the evidence slide is kept with its title and
          notes only.
        </p>
      )}

      {missing > 0 && (
        <p className="evidence-photos__note evidence-photos__note--warning" role="note">
          {missing} referenced photo{missing === 1 ? " is" : "s are"} missing
          or not a supported image and cannot be selected.
        </p>
      )}

      {selectable.length > 0 && (
        <ul className="evidence-photos__grid">
          {selectable.map((photo) => {
            const selected = isEvidencePhotoSelected(
              state,
              group.section,
              photo.relativePath,
            );
            const blocked =
              !selected && group.section === "assembly" && limitReached;
            return (
              <li
                key={photo.relativePath}
                className={`evidence-photos__photo ${
                  selected
                    ? "evidence-photos__photo--selected"
                    : "evidence-photos__photo--unselected"
                }${blocked ? " evidence-photos__photo--blocked" : ""}`}
              >
                <label title={photo.relativePath}>
                  <input
                    type="checkbox"
                    checked={selected}
                    disabled={busy || blocked}
                    onChange={() => onToggle(group.section, photo.relativePath)}
                    aria-label={`Include ${photo.savedName} in ${copy.title}`}
                  />
                  <span className="evidence-photos__thumb">
                    <img
                      src={getImageUrl(photo.relativePath)}
                      alt={`Preview of ${photo.savedName}`}
                      loading="lazy"
                    />
                    <span
                      className={`evidence-photos__badge evidence-photos__badge--${group.section}`}
                    >
                      {copy.badge}
                    </span>
                  </span>
                  <span className="evidence-photos__name">{photo.savedName}</span>
                </label>
              </li>
            );
          })}
        </ul>
      )}
    </li>
  );
}

interface SectionPanelProps extends EvidencePhotosProps {
  section: EvidenceReportSection;
}

function SectionPanel({
  section,
  state,
  disabled = false,
  getImageUrl,
  onToggle,
  onSelectAll,
  onClearSelection,
  onSelectEvidence,
  onClearEvidence,
}: SectionPanelProps) {
  const headingId = useId();
  const copy = SECTION_COPY[section];
  const groups = sectionGroups(state, section);
  const available = selectableEvidencePhotoCount(state, section);
  const selected = selectedEvidencePhotoCount(state, section);
  const limitReached = section === "assembly" && isAssemblyLimitReached(state);
  const allSelected =
    section === "assembly"
      ? selected >= Math.min(available, state.assemblyMaxPhotos)
      : selected === available;

  return (
    <section
      className={`evidence-photos__panel evidence-photos__panel--${section}`}
      aria-labelledby={headingId}
      data-section={section}
    >
      <header className="evidence-photos__panel-heading">
        <span className="evidence-photos__panel-number" aria-hidden="true">
          {copy.number}
        </span>
        <div>
          <h4 id={headingId}>
            {copy.number}. {copy.title}
          </h4>
          <p>{copy.description}</p>
        </div>
        <span className="evidence-photos__counter" aria-live="polite">
          {evidencePhotoSectionCounter(state, section)}
        </span>
      </header>

      {available > 0 && (
        <div className="evidence-photos__toolbar">
          <button
            className="button button--quiet"
            type="button"
            disabled={disabled || allSelected}
            onClick={() => onSelectAll(section)}
          >
            {section === "assembly" && available > state.assemblyMaxPhotos
              ? `Select first ${state.assemblyMaxPhotos}`
              : "Select all"}
          </button>
          <button
            className="button button--quiet"
            type="button"
            disabled={disabled || selected === 0}
            onClick={() => onClearSelection(section)}
          >
            Clear selection
          </button>
        </div>
      )}

      {limitReached && available > state.assemblyMaxPhotos && (
        <p className="evidence-photos__limit" role="status">
          Test Assembly admits up to {state.assemblyMaxPhotos} photos. Clear
          one to choose a different photo.
        </p>
      )}

      {groups.length === 0 ? (
        <div className="empty-state">{copy.empty}</div>
      ) : (
        <ol className="evidence-photos__groups">
          {groups.map((group) => (
            <EvidenceGroup
              key={group.key}
              group={group}
              state={state}
              busy={disabled}
              limitReached={limitReached}
              getImageUrl={getImageUrl}
              onToggle={onToggle}
              onSelectEvidence={onSelectEvidence}
              onClearEvidence={onClearEvidence}
            />
          ))}
        </ol>
      )}
    </section>
  );
}

/**
 * Selección de las fotografías de `02_Evidences` que se insertan en el
 * informe, separada en dos paneles que nunca se mezclan:
 *
 * - **2. Test Assembly**: evidencias `initial`, máximo 4 fotografías.
 * - **4. Test Results**: resto de evidencias, sin límite.
 *
 * Cada panel tiene su color, su contador y sus propias acciones. Las
 * fotografías se insertan siempre en el orden mostrado, dos por diapositiva.
 */
export function EvidencePhotos(props: EvidencePhotosProps) {
  const headingId = useId();

  return (
    <section className="evidence-photos" aria-labelledby={headingId}>
      <div className="evidence-photos__heading">
        <h3 id={headingId}>Evidence photos</h3>
        <p>
          Choose which photos of 02_Evidences are inserted in each section of
          the report. They are inserted in the order shown, two per slide.
        </p>
      </div>
      <div className="evidence-photos__panels">
        <SectionPanel {...props} section="assembly" />
        <SectionPanel {...props} section="results" />
      </div>
    </section>
  );
}
