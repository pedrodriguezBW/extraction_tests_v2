import type {
  RenderedAsset,
  RenderedAssetWarning,
} from "../types/renderedAssets";

/**
 * Estado del inventario de `04_Report/_RenderedAssets` y de la selección de
 * imágenes para el informe.
 *
 * El inventario conserva el orden estable devuelto por el backend. La
 * selección se guarda como conjunto de rutas relativas y se materializa en
 * orden de inventario al generar el informe, de modo que el contrato quede
 * preparado para admitir una reordenación futura sin cambiar el reducer.
 */
export interface RenderedAssetSelectionState {
  /** Imágenes seleccionables en el orden del inventario. */
  assets: RenderedAsset[];

  /** Rutas relativas marcadas para el informe. */
  selected: ReadonlySet<string>;

  /** Archivos del inventario que no son imágenes seleccionables. */
  warnings: RenderedAssetWarning[];

  /** Indica si el inventario se ha cargado al menos una vez. */
  loaded: boolean;
}

export type RenderedAssetSelectionAction =
  | {
      /** Inventario recibido del backend (listado, guardado o eliminación). */
      type: "inventoryLoaded";
      assets: RenderedAsset[];
      warnings?: RenderedAssetWarning[];
    }
  | { type: "toggled"; relativePath: string }
  | { type: "selectAll" }
  | { type: "clearSelection" }
  | { type: "removed"; relativePath: string }
  | { type: "reset" };

export const INITIAL_RENDERED_ASSET_SELECTION: RenderedAssetSelectionState = {
  assets: [],
  selected: new Set<string>(),
  warnings: [],
  loaded: false,
};

/**
 * Reducer puro de inventario y selección.
 *
 * Reglas:
 * - Las imágenes detectadas se seleccionan por defecto.
 * - Al refrescar el inventario se conserva la selección de las imágenes que
 *   siguen existiendo, se seleccionan las nuevas y desaparecen de la
 *   selección las eliminadas.
 * - El usuario puede marcar y desmarcar cada imagen, seleccionar todas o
 *   vaciar la selección.
 */
export function renderedAssetSelectionReducer(
  state: RenderedAssetSelectionState,
  action: RenderedAssetSelectionAction,
): RenderedAssetSelectionState {
  switch (action.type) {
    case "inventoryLoaded": {
      const previousPaths = new Set(state.assets.map((a) => a.relative_path));
      const selected = new Set<string>();
      for (const asset of action.assets) {
        const existedBefore = previousPaths.has(asset.relative_path);
        if (!state.loaded || !existedBefore) {
          // First load or new asset: selected by default.
          selected.add(asset.relative_path);
        } else if (state.selected.has(asset.relative_path)) {
          selected.add(asset.relative_path);
        }
      }
      return {
        assets: [...action.assets],
        selected,
        warnings: [...(action.warnings ?? [])],
        loaded: true,
      };
    }
    case "toggled": {
      if (!state.assets.some((a) => a.relative_path === action.relativePath)) {
        return state;
      }
      const selected = new Set(state.selected);
      if (selected.has(action.relativePath)) {
        selected.delete(action.relativePath);
      } else {
        selected.add(action.relativePath);
      }
      return { ...state, selected };
    }
    case "selectAll":
      return {
        ...state,
        selected: new Set(state.assets.map((a) => a.relative_path)),
      };
    case "clearSelection":
      return { ...state, selected: new Set<string>() };
    case "removed": {
      const assets = state.assets.filter(
        (a) => a.relative_path !== action.relativePath,
      );
      const selected = new Set(state.selected);
      selected.delete(action.relativePath);
      return { ...state, assets, selected };
    }
    case "reset":
      return INITIAL_RENDERED_ASSET_SELECTION;
    default:
      return state;
  }
}

/**
 * Rutas relativas seleccionadas, en el orden del inventario. Es la lista
 * exacta que se envía al backend al generar el informe.
 */
export function selectedRenderedAssetPaths(
  state: RenderedAssetSelectionState,
): string[] {
  return state.assets
    .filter((asset) => state.selected.has(asset.relative_path))
    .map((asset) => asset.relative_path);
}

export function isRenderedAssetSelected(
  state: RenderedAssetSelectionState,
  relativePath: string,
): boolean {
  return state.selected.has(relativePath);
}

export function selectedRenderedAssetCount(
  state: RenderedAssetSelectionState,
): number {
  return selectedRenderedAssetPaths(state).length;
}

/**
 * Mensaje de estado de la selección mostrado junto al inventario y en la
 * sección de generación del informe.
 */
export function renderedAssetSelectionSummary(
  state: RenderedAssetSelectionState,
): string {
  const total = state.assets.length;
  if (total === 0) {
    return "No rendered images were found. The report can still be generated.";
  }
  const count = selectedRenderedAssetCount(state);
  if (count === 0) {
    return "No rendered images are selected. The report will be generated without them.";
  }
  return `${count} of ${total} image${total === 1 ? "" : "s"} selected for the report.`;
}

/** Etiqueta visible de la procedencia de una imagen. */
export function renderedAssetSourceLabel(source: string): string {
  switch (source.toLowerCase()) {
    case "simpati":
      return "SIMPATI";
    case "graphtec":
      return "Graphtec";
    case "canoe":
      return "CANoe";
    case "manual":
      return "Manual";
    case "unknown":
      return "Unknown";
    default:
      return source;
  }
}

/** Formato legible del tamaño de un archivo. */
export function formatFileSize(sizeBytes: number): string {
  if (sizeBytes < 1024) {
    return `${sizeBytes} B`;
  }

  if (sizeBytes < 1024 * 1024) {
    return `${(sizeBytes / 1024).toFixed(1)} KB`;
  }

  return `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`;
}
