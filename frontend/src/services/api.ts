import type {
  HealthResponse,
  ProjectInspectionRequest,
  ProjectInspectionResponse,
} from "../types/project";
import type { ReportGenerationResponse } from "../types/report";
import type {
  SimpatiChartDeleteRequest,
  SimpatiChartDeleteResponse,
  SimpatiChartListResponse,
  SimpatiChartSaveRequest,
  SimpatiChartSaveResponse,
  SimpatiInspectionResponse,
} from "../types/simpati";

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000"
).replace(/\/+$/, "");

interface FastApiErrorBody {
  detail?: unknown;
  errors?: unknown;
}

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

export function checkHealth(): Promise<HealthResponse> {
  return requestJson<HealthResponse>("/health");
}

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

export async function fetchSimpatiChart(
  testRoot: string,
  chartName: string,
): Promise<Blob> {
  const chartUrl = getSimpatiChartUrl(testRoot, chartName);
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
