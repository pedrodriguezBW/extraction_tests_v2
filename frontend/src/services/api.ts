import type {
  HealthResponse,
  ProjectInspectionRequest,
  ProjectInspectionResponse,
} from "../types/project";
import type {
  GraphtecChartDeleteResponse,
  GraphtecChartListResponse,
  GraphtecChartPreviewResponse,
  GraphtecChartRequest,
  GraphtecChartSaveResponse,
  GraphtecChartSettings,
  GraphtecFileRequest,
  GraphtecInspectionResponse,
} from "../types/graphtec";
import type { ReportGenerationResponse } from "../types/report";
import type {
  SimpatiChartDeleteRequest,
  SimpatiChartDeleteResponse,
  SimpatiChartListResponse,
  SimpatiChartSaveRequest,
  SimpatiChartSaveResponse,
  SimpatiInspectionResponse,
} from "../types/simpati";

/**
 * URL base utilizada para comunicarse con el backend FastAPI.
 *
 * Se obtiene de `VITE_API_BASE_URL` y utiliza la dirección local por defecto
 * cuando la variable de entorno no está definida.
 */
export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000"
).replace(/\/+$/, "");

interface FastApiErrorBody {
  detail?: unknown;
  errors?: unknown;
}

/**
 * Representa un error devuelto por el backend o producido durante una
 * petición HTTP.
 *
 * Conserva el código de estado HTTP cuando existe para que la interfaz pueda
 * distinguir errores de validación, acceso y servidor.
 */
export class ApiClientError extends Error {
  readonly status: number | null;

  constructor(message: string, status: number | null = null) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function messageFromErrorBody(
  body: FastApiErrorBody | null,
  fallback: string,
): string {
  if (!body) {
    return fallback;
  }

  if (Array.isArray(body.errors)) {
    const messages = body.errors
      .filter(isRecord)
      .map((error) => error.message)
      .filter(
        (message): message is string =>
          typeof message === "string" && message.trim().length > 0,
      );

    if (messages.length > 0) {
      return messages.join(" ");
    }
  }

  if (typeof body.detail === "string" && body.detail.trim()) {
    return body.detail;
  }

  if (Array.isArray(body.detail)) {
    const messages = body.detail
      .filter(isRecord)
      .map((issue) => issue.msg)
      .filter(
        (message): message is string =>
          typeof message === "string" && message.trim().length > 0,
      );

    if (messages.length > 0) {
      return messages.join(" ");
    }
  }

  return fallback;
}

async function readJson(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return null;
  }

  try {
    return await response.json();
  } catch {
    throw new ApiClientError(
      "The backend returned an invalid JSON response.",
      response.status,
    );
  }
}

async function requestJson<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, init);
  } catch (error) {
    const detail = error instanceof Error ? ` ${error.message}` : "";
    throw new ApiClientError(
      `The backend could not be reached.${detail}`,
    );
  }

  const body = await readJson(response);

  if (!response.ok) {
    const fallback = `The backend returned HTTP error ${response.status}.`;
    throw new ApiClientError(
      messageFromErrorBody(
        isRecord(body) ? (body as FastApiErrorBody) : null,
        fallback,
      ),
      response.status,
    );
  }

  return body as T;
}

/**
 * Comprueba si el backend local está disponible.
 *
 * @returns El estado, el identificador y la versión del backend.
 * @throws {@link ApiClientError} Si no se puede completar la petición.
 */
export function checkHealth(): Promise<HealthResponse> {
  return requestJson<HealthResponse>("/health");
}

/**
 * Solicita la inspección de la carpeta individual de un ensayo.
 *
 * @param testRoot Ruta de la carpeta raíz del ensayo.
 * @returns El resultado completo de la inspección del proyecto.
 * @throws {@link ApiClientError} Si el backend rechaza la petición o no está
 * disponible.
 */
export function inspectProject(
  testRoot: string,
): Promise<ProjectInspectionResponse> {
  const request: ProjectInspectionRequest = {
    test_root: testRoot,
  };

  return requestJson<ProjectInspectionResponse>("/projects/inspect", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });
}

/**
 * Solicita la generación del informe PowerPoint para un ensayo.
 *
 * @param testRoot Ruta de la carpeta raíz del ensayo.
 * @returns El resultado de la generación, incluido el nombre y la ruta del
 * informe cuando la operación finaliza correctamente.
 * @throws {@link ApiClientError} Si el informe no puede generarse.
 */
export function generateReport(
  testRoot: string,
): Promise<ReportGenerationResponse> {
  const request: ProjectInspectionRequest = {
    test_root: testRoot,
  };

  return requestJson<ReportGenerationResponse>(
    "/projects/generate-report",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    },
  );
}

/**
 * Solicita el análisis de la adquisición SIMPATI del ensayo.
 *
 * @param testRoot Ruta de la carpeta raíz del ensayo.
 * @returns El resultado del análisis y los datos de vista previa disponibles.
 * @throws {@link ApiClientError} Si la adquisición no puede analizarse.
 */
export function inspectSimpati(
  testRoot: string,
): Promise<SimpatiInspectionResponse> {
  const request: ProjectInspectionRequest = {
    test_root: testRoot,
  };

  return requestJson<SimpatiInspectionResponse>(
    "/projects/simpati/inspect",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    },
  );
}

/**
 * Guarda una gráfica SIMPATI como imagen para incluirla en el informe.
 *
 * @param testRoot Ruta de la carpeta raíz del ensayo.
 * @param imageBase64 Imagen PNG codificada como una URL de datos.
 * @returns El resultado del guardado y la lista actualizada de gráficas.
 * @throws {@link ApiClientError} Si la imagen no puede guardarse.
 */
export function saveSimpatiChart(
  testRoot: string,
  imageBase64: string,
): Promise<SimpatiChartSaveResponse> {
  const request: SimpatiChartSaveRequest = {
    test_root: testRoot,
    image_base64: imageBase64,
  };

  return requestJson<SimpatiChartSaveResponse>(
    "/projects/simpati/save-chart",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    },
  );
}

/**
 * Obtiene las gráficas SIMPATI guardadas para el ensayo.
 *
 * @param testRoot Ruta de la carpeta raíz del ensayo.
 * @returns La lista de gráficas guardadas y su número total.
 * @throws {@link ApiClientError} Si no se puede consultar la lista.
 */
export function listSimpatiCharts(
  testRoot: string,
): Promise<SimpatiChartListResponse> {
  const request: ProjectInspectionRequest = {
    test_root: testRoot,
  };

  return requestJson<SimpatiChartListResponse>(
    "/projects/simpati/charts",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    },
  );
}

/**
 * Elimina una gráfica SIMPATI guardada para el ensayo.
 *
 * @param testRoot Ruta de la carpeta raíz del ensayo.
 * @param chartName Nombre del archivo de la gráfica.
 * @returns La lista actualizada de gráficas después de la eliminación.
 * @throws {@link ApiClientError} Si la gráfica no puede eliminarse.
 */
export function deleteSimpatiChart(
  testRoot: string,
  chartName: string,
): Promise<SimpatiChartDeleteResponse> {
  const request: SimpatiChartDeleteRequest = {
    test_root: testRoot,
    chart_name: chartName,
  };

  return requestJson<SimpatiChartDeleteResponse>(
    "/projects/simpati/delete-chart",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    },
  );
}

/**
 * Construye la URL utilizada para solicitar una gráfica SIMPATI guardada.
 *
 * @param testRoot Ruta de la carpeta raíz del ensayo.
 * @param chartName Nombre del archivo de la gráfica.
 * @returns La URL del recurso servido por el backend.
 */
export function getSimpatiChartUrl(
  testRoot: string,
  chartName: string,
): string {
  const query = new URLSearchParams({
    test_root: testRoot,
    chart_name: chartName,
  });

  return `${API_BASE_URL}/projects/simpati/chart?${query.toString()}`;
}

/**
 * Descarga una gráfica SIMPATI guardada y valida que la respuesta sea una
 * imagen.
 *
 * @param testRoot Ruta de la carpeta raíz del ensayo.
 * @param chartName Nombre del archivo de la gráfica.
 * @returns El contenido binario de la imagen.
 * @throws {@link ApiClientError} Si la petición falla, el backend devuelve un
 * error o la respuesta no contiene una imagen válida.
 */
export async function fetchSimpatiChart(
  testRoot: string,
  chartName: string,
): Promise<Blob> {
  return fetchChartImage(getSimpatiChartUrl(testRoot, chartName));
}

async function fetchChartImage(chartUrl: string): Promise<Blob> {
  let response: Response;

  try {
    response = await fetch(chartUrl, {
      method: "GET",
      cache: "no-store",
    });
  } catch (error) {
    const detail = error instanceof Error ? ` ${error.message}` : "";
    throw new ApiClientError(
      `The saved chart could not be loaded.${detail}`,
    );
  }

  if (!response.ok) {
    const body = await readJson(response);
    const fallback =
      `The backend returned HTTP error ${response.status}.`;
    throw new ApiClientError(
      messageFromErrorBody(
        isRecord(body) ? (body as FastApiErrorBody) : null,
        fallback,
      ),
      response.status,
    );
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.startsWith("image/")) {
    throw new ApiClientError(
      "The backend did not return a valid chart image.",
      response.status,
    );
  }

  return response.blob();
}

function postJson<T>(path: string, request: unknown): Promise<T> {
  return requestJson<T>(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });
}

/**
 * Analiza un archivo Graphtec seleccionado.
 *
 * El backend reconstruye y valida la ruta dentro de `03_Data/02_Graphtec` y
 * obtiene toda la información técnica del contenido, nunca del nombre.
 *
 * @param testRoot Ruta de la carpeta raíz del ensayo.
 * @param relativePath Ruta relativa devuelta por la inspección del proyecto.
 * @returns El resumen y los datos normalizados del archivo.
 * @throws {@link ApiClientError} Si el archivo no puede analizarse.
 */
export function inspectGraphtec(
  testRoot: string,
  relativePath: string,
): Promise<GraphtecInspectionResponse> {
  const request: GraphtecFileRequest = {
    test_root: testRoot,
    relative_path: relativePath,
  };
  return postJson<GraphtecInspectionResponse>(
    "/projects/graphtec/inspect",
    request,
  );
}

/**
 * Genera la previsualización de una gráfica Graphtec sin guardarla.
 *
 * @throws {@link ApiClientError} Si la configuración o el archivo no son
 * válidos.
 */
export function previewGraphtecChart(
  testRoot: string,
  relativePath: string,
  chart: GraphtecChartSettings,
): Promise<GraphtecChartPreviewResponse> {
  const request: GraphtecChartRequest = {
    test_root: testRoot,
    relative_path: relativePath,
    chart,
  };
  return postJson<GraphtecChartPreviewResponse>(
    "/projects/graphtec/preview-chart",
    request,
  );
}

/**
 * Genera y guarda una gráfica Graphtec en `04_Report/_RenderedAssets`.
 *
 * @throws {@link ApiClientError} Si la gráfica no puede guardarse.
 */
export function saveGraphtecChart(
  testRoot: string,
  relativePath: string,
  chart: GraphtecChartSettings,
): Promise<GraphtecChartSaveResponse> {
  const request: GraphtecChartRequest = {
    test_root: testRoot,
    relative_path: relativePath,
    chart,
  };
  return postJson<GraphtecChartSaveResponse>(
    "/projects/graphtec/save-chart",
    request,
  );
}

/**
 * Obtiene las gráficas Graphtec guardadas para el ensayo.
 *
 * @throws {@link ApiClientError} Si no se puede consultar la lista.
 */
export function listGraphtecCharts(
  testRoot: string,
): Promise<GraphtecChartListResponse> {
  const request: ProjectInspectionRequest = { test_root: testRoot };
  return postJson<GraphtecChartListResponse>(
    "/projects/graphtec/charts",
    request,
  );
}

/**
 * Elimina una gráfica Graphtec guardada y sus metadatos.
 *
 * @throws {@link ApiClientError} Si la gráfica no puede eliminarse.
 */
export function deleteGraphtecChart(
  testRoot: string,
  chartName: string,
): Promise<GraphtecChartDeleteResponse> {
  return postJson<GraphtecChartDeleteResponse>(
    "/projects/graphtec/delete-chart",
    { test_root: testRoot, chart_name: chartName },
  );
}

/**
 * Construye la URL de una gráfica Graphtec guardada.
 */
export function getGraphtecChartUrl(
  testRoot: string,
  chartName: string,
): string {
  const query = new URLSearchParams({
    test_root: testRoot,
    chart_name: chartName,
  });

  return `${API_BASE_URL}/projects/graphtec/chart?${query.toString()}`;
}

/**
 * Descarga una gráfica Graphtec guardada.
 *
 * @throws {@link ApiClientError} Si la respuesta no contiene una imagen.
 */
export function fetchGraphtecChart(
  testRoot: string,
  chartName: string,
): Promise<Blob> {
  return fetchChartImage(getGraphtecChartUrl(testRoot, chartName));
}
