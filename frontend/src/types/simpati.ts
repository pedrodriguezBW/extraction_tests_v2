import type { ApiError } from "./common";


export interface SimpatiPreviewChannel {
  id: string;
  label: string;
  source_column: string;
  thermal: boolean;
  values: Array<number | null>;
}

export interface SimpatiChartSaveRequest {
  test_root: string;
  image_base64: string;
}

export interface SimpatiChartDeleteRequest {
  test_root: string;
  chart_name: string;
}

export interface SimpatiSavedChart {
  chart_name: string;
  chart_path: string;
  size_bytes: number;
}

export interface SimpatiChartListResponse {
  success: boolean;
  test_root: string;
  charts_count: number;
  charts: SimpatiSavedChart[];
  errors: ApiError[];
}

export interface SimpatiChartSaveResponse {
  success: boolean;
  test_root: string;
  chart_path: string | null;
  chart_name: string | null;
  charts_count: number;
  charts: SimpatiSavedChart[];
  errors: ApiError[];
}

export interface SimpatiChartDeleteResponse {
  success: boolean;
  test_root: string;
  deleted_chart_name: string | null;
  charts_count: number;
  charts: SimpatiSavedChart[];
  errors: ApiError[];
}

export interface SimpatiInspectionResponse {
  success: boolean;
  test_root: string;
  available: boolean;
  file_name: string | null;
  file_path: string | null;
  encoding: string | null;
  records_count: number;
  acquisition_start: string | null;
  acquisition_end: string | null;
  channels: string[];
  preview_timestamps: string[];
  thermal_channels: SimpatiPreviewChannel[];
  advanced_channels: SimpatiPreviewChannel[];
  errors: ApiError[];
}
