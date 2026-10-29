import type { ApiError } from "./common";

/**
 * Imagen de `04_Report/_RenderedAssets` que puede seleccionarse para el
 * informe, con independencia de su origen.
 */
export interface RenderedAsset {
  /** Nombre del archivo. */
  name: string;

  /**
   * Ruta relativa a la carpeta del ensayo con separadores `/`
   * (`04_Report/_RenderedAssets/<archivo>`). Identifica el recurso en todas
   * las peticiones: abrir, eliminar y generar el informe.
   */
  relative_path: string;

  /** Extensión en minúsculas, con el punto. */
  extension: string;

  /** Tamaño del archivo en bytes. */
  size: number;

  /**
   * Procedencia informativa (`simpati`, `graphtec`, `manual`, `unknown`...).
   * Nunca determina si la imagen puede incluirse en el informe.
   */
  source: string;

  /** Nombre del archivo de metadatos asociado, cuando existe. */
  metadata_name: string | null;
}

/**
 * Archivo de `_RenderedAssets` que no es una imagen seleccionable.
 */
export interface RenderedAssetWarning {
  name: string;
  code: string;
  message: string;
}

/**
 * Petición que identifica un recurso por su ruta relativa.
 */
export interface RenderedAssetRequest {
  test_root: string;
  relative_path: string;
}

/**
 * Inventario de imágenes seleccionables devuelto por el backend.
 */
export interface RenderedAssetListResponse {
  success: boolean;
  test_root: string;
  directory_found: boolean;
  assets_count: number;
  assets: RenderedAsset[];
  warnings: RenderedAssetWarning[];
  errors: ApiError[];
}

/**
 * Resultado de eliminar un recurso, con el inventario actualizado.
 */
export interface RenderedAssetDeleteResponse {
  success: boolean;
  test_root: string;
  deleted_relative_path: string | null;
  directory_found: boolean;
  assets_count: number;
  assets: RenderedAsset[];
  warnings: RenderedAssetWarning[];
  errors: ApiError[];
}
