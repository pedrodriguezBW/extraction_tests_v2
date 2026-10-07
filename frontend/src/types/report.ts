import type { ApiError } from "./common";


export interface ReportGenerationResponse {
  success: boolean;
  test_root: string;
  report_path: string | null;
  report_name: string | null;
  errors: ApiError[];
}
