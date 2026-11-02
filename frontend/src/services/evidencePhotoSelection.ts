import type {
  EvidenceReportSection,
  EvidenceResult,
  EvidencesInspectionResult,
} from "../types/project";

/**
 * Selección de las fotografías de evidencia que se insertan en el informe.
 *
 * Las evidencias se reparten en dos zonas que nunca se mezclan:
 *
 * - `assembly`: evidencias de tipo `initial` → **2. Test Assembly**. Como
 *   máximo {@link DEFAULT_ASSEMBLY_MAX_PHOTOS} fotografías.
 * - `results`: el resto de evidencias → **4. Test Results**. Sin límite.
 *
 * El orden de inserción es siempre el automático (secuencia de la evidencia
 * y orden de sus fotografías). Cada zona tiene su propia selección: las
 * acciones de una zona nunca modifican la otra.
 */

/** Máximo de fotografías de Test Assembly si el backend no lo indica. */
export const DEFAULT_ASSEMBLY_MAX_PHOTOS = 4;

/** Fotografías por diapositiva si el backend no lo indica. */
export const DEFAULT_PHOTOS_PER_SLIDE = 2;

/** Zonas en el orden en que aparecen en el informe. */
export const EVIDENCE_PHOTO_SECTIONS: readonly EvidenceReportSection[] = [
  "assembly",
  "results",
];

/** Fotografía declarada por una evidencia. */
export interface EvidencePhotoItem {
  /** Identificador de selección (`02_Evidences/<carpeta>/<savedName>`). */
  relativePath: string;

  /** Nombre del archivo guardado. */
  savedName: string;

  /** Nombre original de la cámara, si está declarado. */
  originalName: string | null;

  /** Fecha de captura declarada. */
  captureDate: string | null;

  /** El archivo existe y es una imagen admitida. */
  selectable: boolean;

  /** El archivo existe. */
  found: boolean;
}

/** Evidencia con sus fotografías, en el orden del informe. */
export interface EvidencePhotoGroup {
  /** Clave estable de la evidencia (ruta de su descriptor). */
  key: string;

  /** Zona del informe que recibe sus fotografías. */
  section: EvidenceReportSection;

  /** Secuencia declarada. */
  sequence: number | null;

  /** Título visible. */
  title: string;

  /** Tipo declarado (`initial`, `incident`...). */
  type: string | null;

  /** Referencia legible (`450 cycles`), vacía si no existe. */
  reference: string;

  /** Carpeta de la evidencia. */
  folder: string;

  /** Fotografías declaradas, en orden. */
  photos: EvidencePhotoItem[];
}

export interface EvidencePhotoSelectionState {
  /** Evidencias en orden automático. */
  groups: EvidencePhotoGroup[];

  /** Rutas seleccionadas para cada zona. */
  selected: Record<EvidenceReportSection, ReadonlySet<string>>;

  /** Máximo de fotografías de Test Assembly. */
  assemblyMaxPhotos: number;

  /** Máximo de fotografías por diapositiva. */
  photosPerSlide: number;

  /** Indica si se ha recibido al menos una inspección. */
  loaded: boolean;
}

export type EvidencePhotoSelectionAction =
  | { type: "inspectionLoaded"; evidences: EvidencesInspectionResult }
  | {
      type: "toggled";
      section: EvidenceReportSection;
      relativePath: string;
    }
  | { type: "selectAll"; section: EvidenceReportSection }
  | { type: "clearSelection"; section: EvidenceReportSection }
  | {
      type: "selectEvidence";
      section: EvidenceReportSection;
      evidenceKey: string;
    }
  | {
      type: "clearEvidence";
      section: EvidenceReportSection;
      evidenceKey: string;
    }
  | { type: "reset" };

export const INITIAL_EVIDENCE_PHOTO_SELECTION: EvidencePhotoSelectionState = {
  groups: [],
  selected: { assembly: new Set<string>(), results: new Set<string>() },
  assemblyMaxPhotos: DEFAULT_ASSEMBLY_MAX_PHOTOS,
  photosPerSlide: DEFAULT_PHOTOS_PER_SLIDE,
  loaded: false,
};

/** Zona del informe de una evidencia (por compatibilidad, por su tipo). */
export function evidenceReportSection(
  evidence: EvidenceResult,
): EvidenceReportSection {
  if (evidence.report_section === "assembly" || evidence.report_section === "results") {
    return evidence.report_section;
  }
  return (evidence.type ?? "").trim().toLowerCase() === "initial"
    ? "assembly"
    : "results";
}

function referenceText(evidence: EvidenceResult): string {
  const value = (evidence.reference_value ?? "").trim();
  const kind = (evidence.reference_type ?? "").trim();
  if (!value) {
    return "";
  }
  if (!kind || kind.toLowerCase() === "none") {
    return value;
  }
  return `${value} ${kind}`;
}

/** Convierte el resultado de la inspección en grupos ordenados. */
export function evidencePhotoGroups(
  evidences: EvidencesInspectionResult,
): EvidencePhotoGroup[] {
  return evidences.evidences.map((evidence) => ({
    key: evidence.descriptor_path,
    section: evidenceReportSection(evidence),
    sequence: evidence.sequence,
    title: evidence.title?.trim() || evidence.folder,
    type: evidence.type,
    reference: referenceText(evidence),
    folder: evidence.folder,
    photos: evidence.photos.map((photo) => ({
      relativePath:
        photo.relative_path ||
        `02_Evidences/${evidence.folder}/${photo.saved_name}`,
      savedName: photo.saved_name,
      originalName: photo.original_name,
      captureDate: photo.capture_date,
      selectable:
        photo.selectable ?? photo.found,
      found: photo.found,
    })),
  }));
}

/** Evidencias de una zona, en orden automático. */
export function sectionGroups(
  state: EvidencePhotoSelectionState,
  section: EvidenceReportSection,
): EvidencePhotoGroup[] {
  return state.groups.filter((group) => group.section === section);
}

/** Fotografías seleccionables de una zona, en orden automático. */
export function selectableSectionPaths(
  groups: readonly EvidencePhotoGroup[],
  section: EvidenceReportSection,
): string[] {
  return groups
    .filter((group) => group.section === section)
    .flatMap((group) =>
      group.photos
        .filter((photo) => photo.selectable)
        .map((photo) => photo.relativePath),
    );
}

function sectionLimit(
  state: EvidencePhotoSelectionState,
  section: EvidenceReportSection,
): number {
  return section === "assembly"
    ? state.assemblyMaxPhotos
    : Number.POSITIVE_INFINITY;
}

/**
 * Añade rutas en orden hasta el límite de la zona, sin superar nunca el
 * máximo de Test Assembly.
 */
function addWithinLimit(
  current: ReadonlySet<string>,
  paths: readonly string[],
  limit: number,
): Set<string> {
  const next = new Set(current);
  for (const path of paths) {
    if (next.size >= limit) {
      break;
    }
    next.add(path);
  }
  return next;
}

/**
 * Reducer puro de la selección de fotografías de evidencia.
 *
 * Reglas:
 * - Primera carga: Test Results marca todas las fotografías; Test Assembly
 *   marca las primeras hasta el máximo.
 * - Al volver a inspeccionar se conserva la selección de las fotografías
 *   que siguen existiendo, se marcan las nuevas (en Assembly solo si queda
 *   hueco) y desaparecen las que ya no existen.
 * - En Test Assembly no se puede marcar una fotografía más cuando se ha
 *   alcanzado el máximo; "Select all" marca las primeras hasta el máximo.
 * - Las acciones de una zona nunca modifican la otra.
 */
export function evidencePhotoSelectionReducer(
  state: EvidencePhotoSelectionState,
  action: EvidencePhotoSelectionAction,
): EvidencePhotoSelectionState {
  switch (action.type) {
    case "inspectionLoaded": {
      const groups = evidencePhotoGroups(action.evidences);
      const assemblyMaxPhotos =
        action.evidences.assembly_max_photos || DEFAULT_ASSEMBLY_MAX_PHOTOS;
      const photosPerSlide =
        action.evidences.photos_per_slide || DEFAULT_PHOTOS_PER_SLIDE;
      const previous = new Set(
        state.groups.flatMap((group) =>
          group.photos
            .filter((photo) => photo.selectable)
            .map((photo) => photo.relativePath),
        ),
      );
      const selected = {} as Record<EvidenceReportSection, Set<string>>;
      for (const section of EVIDENCE_PHOTO_SECTIONS) {
        const available = selectableSectionPaths(groups, section);
        const limit =
          section === "assembly" ? assemblyMaxPhotos : Number.POSITIVE_INFINITY;
        const kept = available.filter(
          (path) =>
            state.loaded && previous.has(path) && state.selected[section].has(path),
        );
        const added = available.filter(
          (path) => !state.loaded || !previous.has(path),
        );
        const keptSet = addWithinLimit(new Set<string>(), kept, limit);
        selected[section] = addWithinLimit(keptSet, added, limit);
      }
      return {
        groups,
        selected,
        assemblyMaxPhotos,
        photosPerSlide,
        loaded: true,
      };
    }
    case "toggled": {
      const available = selectableSectionPaths(state.groups, action.section);
      if (!available.includes(action.relativePath)) {
        return state;
      }
      const current = state.selected[action.section];
      const next = new Set(current);
      if (next.has(action.relativePath)) {
        next.delete(action.relativePath);
      } else {
        if (next.size >= sectionLimit(state, action.section)) {
          return state;
        }
        next.add(action.relativePath);
      }
      return {
        ...state,
        selected: { ...state.selected, [action.section]: next },
      };
    }
    case "selectAll": {
      const available = selectableSectionPaths(state.groups, action.section);
      const next = addWithinLimit(
        new Set<string>(),
        available,
        sectionLimit(state, action.section),
      );
      return {
        ...state,
        selected: { ...state.selected, [action.section]: next },
      };
    }
    case "clearSelection":
      return {
        ...state,
        selected: { ...state.selected, [action.section]: new Set<string>() },
      };
    case "selectEvidence": {
      const group = state.groups.find(
        (candidate) =>
          candidate.key === action.evidenceKey &&
          candidate.section === action.section,
      );
      if (!group) {
        return state;
      }
      const paths = group.photos
        .filter((photo) => photo.selectable)
        .map((photo) => photo.relativePath);
      const next = addWithinLimit(
        state.selected[action.section],
        paths,
        sectionLimit(state, action.section),
      );
      return {
        ...state,
        selected: { ...state.selected, [action.section]: next },
      };
    }
    case "clearEvidence": {
      const group = state.groups.find(
        (candidate) =>
          candidate.key === action.evidenceKey &&
          candidate.section === action.section,
      );
      if (!group) {
        return state;
      }
      const next = new Set(state.selected[action.section]);
      for (const photo of group.photos) {
        next.delete(photo.relativePath);
      }
      return {
        ...state,
        selected: { ...state.selected, [action.section]: next },
      };
    }
    case "reset":
      return INITIAL_EVIDENCE_PHOTO_SELECTION;
    default:
      return state;
  }
}

/**
 * Rutas seleccionadas de una zona en orden automático. Es la lista exacta
 * que se envía al backend.
 */
export function selectedEvidencePhotoPaths(
  state: EvidencePhotoSelectionState,
  section: EvidenceReportSection,
): string[] {
  return selectableSectionPaths(state.groups, section).filter((path) =>
    state.selected[section].has(path),
  );
}

export function isEvidencePhotoSelected(
  state: EvidencePhotoSelectionState,
  section: EvidenceReportSection,
  relativePath: string,
): boolean {
  return state.selected[section].has(relativePath);
}

/** Número de fotografías seleccionables de una zona. */
export function selectableEvidencePhotoCount(
  state: EvidencePhotoSelectionState,
  section: EvidenceReportSection,
): number {
  return selectableSectionPaths(state.groups, section).length;
}

/** Número de fotografías seleccionadas de una zona. */
export function selectedEvidencePhotoCount(
  state: EvidencePhotoSelectionState,
  section: EvidenceReportSection,
): number {
  return selectedEvidencePhotoPaths(state, section).length;
}

/** Indica si Test Assembly ha alcanzado su máximo. */
export function isAssemblyLimitReached(
  state: EvidencePhotoSelectionState,
): boolean {
  return selectedEvidencePhotoCount(state, "assembly") >= state.assemblyMaxPhotos;
}

/** Fotografías seleccionadas de una evidencia concreta. */
export function selectedPhotosInGroup(
  state: EvidencePhotoSelectionState,
  group: EvidencePhotoGroup,
): number {
  return group.photos.filter((photo) =>
    state.selected[group.section].has(photo.relativePath),
  ).length;
}

/** Diapositivas que ocupará un número de fotografías. */
export function slidesForPhotos(count: number, photosPerSlide: number): number {
  return Math.ceil(count / Math.max(1, photosPerSlide));
}

/**
 * Diapositivas de evidencia de Test Results: cada evidencia ocupa al menos
 * una (aunque no tenga fotografías) y dos fotografías por diapositiva.
 */
export function resultEvidenceSlideCount(
  state: EvidencePhotoSelectionState,
): number {
  return sectionGroups(state, "results").reduce(
    (total, group) =>
      total +
      Math.max(
        1,
        slidesForPhotos(selectedPhotosInGroup(state, group), state.photosPerSlide),
      ),
    0,
  );
}

function plural(count: number, word: string): string {
  return `${count} ${word}${count === 1 ? "" : "s"}`;
}

/** Contador visible de una zona. */
export function evidencePhotoSectionCounter(
  state: EvidencePhotoSelectionState,
  section: EvidenceReportSection,
): string {
  const selected = selectedEvidencePhotoCount(state, section);
  if (section === "assembly") {
    return `${selected} / ${state.assemblyMaxPhotos} selected`;
  }
  return `${selected} of ${selectableEvidencePhotoCount(state, section)} selected`;
}

/**
 * Resumen del reparto que se muestra junto al botón de generación.
 */
export function evidencePhotoReportSummary(
  state: EvidencePhotoSelectionState,
): string {
  const assembly = selectedEvidencePhotoCount(state, "assembly");
  const results = selectedEvidencePhotoCount(state, "results");
  const resultGroups = sectionGroups(state, "results").length;
  const assemblySlides = Math.max(1, slidesForPhotos(assembly, state.photosPerSlide));
  const assemblyText =
    assembly === 0
      ? "Test Assembly: no photos"
      : `Test Assembly: ${plural(assembly, "photo")} (${plural(assemblySlides, "slide")})`;
  const resultsText =
    resultGroups === 0
      ? "Test Results: no evidences"
      : `Test Results: ${plural(results, "evidence photo")} in ${plural(
          resultEvidenceSlideCount(state),
          "evidence slide",
        )}`;
  return `${assemblyText} · ${resultsText}`;
}
