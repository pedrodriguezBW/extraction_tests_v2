import type {
  DataSourceFileResult,
  DataSourceKey,
  ProjectInspectionResponse,
} from "../types/project";
import type { GraphtecInspectionResponse } from "../types/graphtec";
import type { SimpatiInspectionResponse } from "../types/simpati";
import { DATA_SOURCE_KEYS } from "./projectStatus";

/**
 * Opción mostrada en el selector de fuente de datos.
 */
export interface DataSourceOption {
  /** Identificador estable de la fuente. */
  key: DataSourceKey;

  /** Etiqueta visible de la fuente. */
  label: string;

  /** Indica si la carpeta de la fuente existe. */
  found: boolean;

  /** Número de archivos detectados en la fuente. */
  fileCount: number;
}

/**
 * Selección de fuente y archivo, junto con los análisis asociados.
 *
 * Los resultados SIMPATI y Graphtec forman parte de este estado para que
 * cualquier cambio de fuente o de archivo descarte el análisis y la
 * previsualización correspondientes a la selección anterior.
 */
export interface DataSelectionState {
  /** Fuente seleccionada o `null` si todavía no se ha elegido ninguna. */
  sourceKey: DataSourceKey | null;

  /** `relative_path` del archivo seleccionado o `null`. */
  fileRelativePath: string | null;

  /** Resultado del análisis SIMPATI del archivo seleccionado. */
  simpati: SimpatiInspectionResponse | null;

  /** Resultado del análisis Graphtec del archivo seleccionado. */
  graphtec: GraphtecInspectionResponse | null;
}

/**
 * Acciones admitidas por {@link dataSelectionReducer}.
 */
export type DataSelectionAction =
  | { type: "reset" }
  | { type: "sourceSelected"; sourceKey: DataSourceKey | null }
  | { type: "fileSelected"; fileRelativePath: string | null }
  | { type: "simpatiCleared" }
  | {
      type: "simpatiInspected";
      fileRelativePath: string;
      result: SimpatiInspectionResponse;
    }
  | { type: "graphtecCleared" }
  | {
      type: "graphtecInspected";
      fileRelativePath: string;
      result: GraphtecInspectionResponse;
    };

/** Estado inicial: sin fuente, sin archivo y sin análisis SIMPATI. */
export const INITIAL_DATA_SELECTION: DataSelectionState = {
  sourceKey: null,
  fileRelativePath: null,
  simpati: null,
  graphtec: null,
};

/**
 * Actualiza la selección de fuente y archivo.
 *
 * - Cambiar de fuente limpia el archivo y los resultados SIMPATI y Graphtec.
 * - Cambiar de archivo limpia los resultados del archivo anterior.
 * - Ninguna acción de selección inicia un análisis ni lee archivos.
 * - Un resultado solo se acepta si corresponde a la selección vigente.
 *
 * @param state Estado actual.
 * @param action Acción que se debe aplicar.
 * @returns El nuevo estado.
 */
export function dataSelectionReducer(
  state: DataSelectionState,
  action: DataSelectionAction,
): DataSelectionState {
  switch (action.type) {
    case "reset":
      return INITIAL_DATA_SELECTION;
    case "sourceSelected":
      if (action.sourceKey === state.sourceKey) {
        return state;
      }
      return {
        sourceKey: action.sourceKey,
        fileRelativePath: null,
        simpati: null,
        graphtec: null,
      };
    case "fileSelected":
      if (action.fileRelativePath === state.fileRelativePath) {
        return state;
      }
      return {
        ...state,
        fileRelativePath: action.fileRelativePath,
        simpati: null,
        graphtec: null,
      };
    case "simpatiCleared":
      return state.simpati === null ? state : { ...state, simpati: null };
    case "simpatiInspected":
      if (
        state.sourceKey !== "simpati" ||
        state.fileRelativePath !== action.fileRelativePath
      ) {
        return state;
      }
      return { ...state, simpati: action.result };
    case "graphtecCleared":
      return state.graphtec === null ? state : { ...state, graphtec: null };
    case "graphtecInspected":
      if (
        state.sourceKey !== "graphtec" ||
        state.fileRelativePath !== action.fileRelativePath
      ) {
        return state;
      }
      return { ...state, graphtec: action.result };
    default:
      return state;
  }
}

/**
 * Construye las opciones del selector de fuente.
 *
 * Siempre devuelve SIMPATI, Graphtec y CANoe, en este orden, aunque su
 * carpeta no exista.
 *
 * @param inspection Resultado de la inspección del proyecto.
 * @returns Las tres fuentes reconocidas.
 */
export function dataSourceOptions(
  inspection: ProjectInspectionResponse,
): DataSourceOption[] {
  return DATA_SOURCE_KEYS.map((key) => {
    const source = inspection.data[key];
    return {
      key,
      label: source.label,
      found: source.found,
      fileCount: source.files.length,
    };
  });
}

/**
 * Obtiene los archivos detectados en una fuente.
 *
 * @param inspection Resultado de la inspección o `null`.
 * @param sourceKey Fuente seleccionada o `null`.
 * @returns Los archivos de la fuente; vacío si no existe la carpeta.
 */
export function sourceFiles(
  inspection: ProjectInspectionResponse | null,
  sourceKey: DataSourceKey | null,
): DataSourceFileResult[] {
  if (inspection === null || sourceKey === null) {
    return [];
  }
  const source = inspection.data[sourceKey];
  return source.found ? source.files : [];
}

/**
 * Busca el archivo seleccionado dentro de la fuente elegida.
 *
 * @returns El archivo o `null` cuando no forma parte de la fuente.
 */
export function selectedSourceFile(
  inspection: ProjectInspectionResponse | null,
  selection: Pick<DataSelectionState, "sourceKey" | "fileRelativePath">,
): DataSourceFileResult | null {
  if (selection.fileRelativePath === null) {
    return null;
  }
  return (
    sourceFiles(inspection, selection.sourceKey).find(
      (file) => file.relative_path === selection.fileRelativePath,
    ) ?? null
  );
}

/**
 * Indica si el selector de archivo debe estar deshabilitado.
 *
 * Se deshabilita cuando no hay fuente seleccionada, cuando la carpeta de la
 * fuente no existe o cuando la fuente no contiene archivos.
 */
export function isFileSelectorDisabled(
  inspection: ProjectInspectionResponse | null,
  sourceKey: DataSourceKey | null,
): boolean {
  return sourceFiles(inspection, sourceKey).length === 0;
}

/**
 * Explica por qué el selector de archivo no tiene opciones disponibles.
 *
 * @returns Un texto en inglés o `null` cuando hay archivos disponibles.
 */
export function fileSelectorHint(
  inspection: ProjectInspectionResponse | null,
  sourceKey: DataSourceKey | null,
): string | null {
  if (inspection === null || sourceKey === null) {
    return "Select a data source to list its files.";
  }
  const source = inspection.data[sourceKey];
  if (!source.found) {
    return `The ${source.label} folder was not found in 03_Data.`;
  }
  if (source.files.length === 0) {
    return `No files were found in the ${source.label} folder.`;
  }
  return null;
}

/** Fuentes cuya lectura todavía no está implementada. */
export const PENDING_SOURCE_KEYS: DataSourceKey[] = ["canoe"];

/**
 * Mensaje neutral para las fuentes cuya lectura todavía no está disponible.
 *
 * @returns El mensaje para CANoe, o `null` para SIMPATI y Graphtec.
 */
export function pendingSourceMessage(
  inspection: ProjectInspectionResponse | null,
  sourceKey: DataSourceKey | null,
): string | null {
  if (
    inspection === null ||
    sourceKey === null ||
    !PENDING_SOURCE_KEYS.includes(sourceKey)
  ) {
    return null;
  }
  const label = inspection.data[sourceKey].label;
  return `Reading ${label} files will be added in a later increment.`;
}

/**
 * Indica si el archivo seleccionado es la adquisición SIMPATI que analiza el
 * flujo SIMPATI existente.
 *
 * El análisis SIMPATI actual procesa el archivo `.x03` detectado durante la
 * inspección (`data.simpati_file`). Exigir que coincida con la selección
 * evita mostrar resultados de un archivo distinto al elegido.
 */
export function isSimpatiAnalysisFile(
  inspection: ProjectInspectionResponse | null,
  file: DataSourceFileResult | null,
): boolean {
  if (inspection === null || file === null) {
    return false;
  }
  const simpatiFile = inspection.data.simpati_file;
  return simpatiFile.found && simpatiFile.name === file.name;
}

/**
 * Condiciones para habilitar el botón de análisis SIMPATI.
 */
export interface SimpatiAnalysisContext {
  /** Resultado de la inspección del proyecto o `null`. */
  inspection: ProjectInspectionResponse | null;

  /** Fuente y archivo seleccionados. */
  selection: Pick<DataSelectionState, "sourceKey" | "fileRelativePath">;

  /** Indica si el backend está conectado. */
  backendConnected: boolean;

  /** Indica si hay otra operación incompatible en curso. */
  busy: boolean;
}

/**
 * Determina si el análisis SIMPATI puede iniciarse.
 *
 * Requiere un proyecto inspeccionado, el backend conectado, ninguna
 * operación en curso, SIMPATI como fuente seleccionada y un archivo SIMPATI
 * seleccionado que coincida con la adquisición detectada.
 */
export function canAnalyzeSimpati({
  inspection,
  selection,
  backendConnected,
  busy,
}: SimpatiAnalysisContext): boolean {
  if (
    inspection === null ||
    !backendConnected ||
    busy ||
    selection.sourceKey !== "simpati"
  ) {
    return false;
  }
  return isSimpatiAnalysisFile(
    inspection,
    selectedSourceFile(inspection, selection),
  );
}

/**
 * Explica qué falta para habilitar el análisis SIMPATI.
 *
 * @returns Un texto en inglés o `null` cuando no hace falta ninguna ayuda.
 */
export function simpatiAnalysisHint(
  inspection: ProjectInspectionResponse | null,
  selection: Pick<DataSelectionState, "sourceKey" | "fileRelativePath">,
): string | null {
  if (inspection === null) {
    return "SIMPATI analysis is enabled after project inspection.";
  }
  if (selection.sourceKey === null) {
    return "Select SIMPATI as the data source and choose a file to enable the analysis.";
  }
  if (selection.sourceKey !== "simpati") {
    return "SIMPATI analysis is only available for the SIMPATI source.";
  }
  const file = selectedSourceFile(inspection, selection);
  if (file === null) {
    return "Select a SIMPATI file to enable the analysis.";
  }
  if (!isSimpatiAnalysisFile(inspection, file)) {
    const simpatiFile = inspection.data.simpati_file;
    return simpatiFile.found && simpatiFile.name
      ? `SIMPATI analysis currently supports the detected acquisition file ${simpatiFile.name}.`
      : "No single SIMPATI acquisition file (.x03) was detected. Review the inspection warnings.";
  }
  return null;
}

/**
 * Formatea un tamaño en bytes para mostrarlo en la interfaz.
 */
export function formatFileSize(size: number): string {
  if (size < 1024) {
    return `${size} B`;
  }
  const units = ["KB", "MB", "GB"];
  let value = size / 1024;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[unit]}`;
}

/** Condiciones comunes para habilitar el análisis de una fuente. */
export type SourceAnalysisContext = SimpatiAnalysisContext;

/**
 * Determina si el análisis Graphtec puede iniciarse: proyecto inspeccionado,
 * backend conectado, ninguna operación incompatible en curso, Graphtec como
 * fuente y un archivo Graphtec seleccionado.
 *
 * El nombre del archivo no se evalúa; el backend valida la ruta y el formato
 * a partir del contenido.
 */
export function canAnalyzeGraphtec({
  inspection,
  selection,
  backendConnected,
  busy,
}: SourceAnalysisContext): boolean {
  return (
    inspection !== null &&
    backendConnected &&
    !busy &&
    selection.sourceKey === "graphtec" &&
    selectedSourceFile(inspection, selection) !== null
  );
}

/**
 * Explica qué falta para habilitar el análisis Graphtec.
 *
 * @returns Un texto en inglés o `null` cuando no hace falta ninguna ayuda.
 */
export function graphtecAnalysisHint(
  inspection: ProjectInspectionResponse | null,
  selection: Pick<DataSelectionState, "sourceKey" | "fileRelativePath">,
): string | null {
  if (inspection === null) {
    return "Graphtec analysis is enabled after project inspection.";
  }
  if (selection.sourceKey !== "graphtec") {
    return null;
  }
  if (selectedSourceFile(inspection, selection) === null) {
    return "Select a Graphtec file to enable the analysis.";
  }
  return null;
}
