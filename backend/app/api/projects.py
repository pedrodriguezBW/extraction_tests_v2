from fastapi import APIRouter, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, FileResponse

from ..models.project import (
    ProjectInspectionRequest,
    ProjectInspectionResponse,
)
from ..models.report_generation import ReportGenerationResponse
from ..models.simpati_inspection import (
    SimpatiChartDeleteRequest,
    SimpatiChartDeleteResponse,
    SimpatiChartListResponse,
    SimpatiChartSaveRequest,
    SimpatiChartSaveResponse,
    SimpatiInspectionResponse,
)
from ..services.project_inspection import inspect_project
from ..services.report_generation import (
    ReportGenerationError,
    generate_project_report,
)
from ..services.simpati_inspection import (
    SimpatiChartManagementError,
    SimpatiChartSaveError,
    delete_project_simpati_chart,
    SimpatiInspectionError,
    inspect_project_simpati,
    list_project_simpati_charts,
    resolve_project_simpati_chart,
    save_project_simpati_chart,
)


router = APIRouter(
    prefix="/projects",
    tags=["projects"],
)


@router.post(
    "/inspect",
    response_model=ProjectInspectionResponse,
)
def inspect_project_endpoint(
    request: ProjectInspectionRequest,
) -> ProjectInspectionResponse:
    """Inspect the test structure, metadata, evidences and sources."""
    return inspect_project(request.test_root)


@router.post(
    "/generate-report",
    response_model=ReportGenerationResponse,
    responses={
        400: {"model": ReportGenerationResponse},
        403: {"model": ReportGenerationResponse},
        500: {"model": ReportGenerationResponse},
    },
)
def generate_project_report_endpoint(
    request: ProjectInspectionRequest,
) -> ReportGenerationResponse | JSONResponse:
    """Generate the PowerPoint from the existing test_metadata.json."""
    try:
        return generate_project_report(request.test_root)
    except ReportGenerationError as error:
        return JSONResponse(
            status_code=error.status_code,
            content=jsonable_encoder(error.to_response()),
        )


@router.post(
    "/simpati/inspect",
    response_model=SimpatiInspectionResponse,
    responses={
        400: {"model": SimpatiInspectionResponse},
        403: {"model": SimpatiInspectionResponse},
        500: {"model": SimpatiInspectionResponse},
    },
)
def inspect_project_simpati_endpoint(
    request: ProjectInspectionRequest,
) -> SimpatiInspectionResponse | JSONResponse:
    """Inspect an optional SIMPATI acquisition file."""
    try:
        return inspect_project_simpati(request.test_root)
    except SimpatiInspectionError as error:
        return JSONResponse(
            status_code=error.status_code,
            content=jsonable_encoder(error.to_response()),
        )


@router.post(
    "/simpati/save-chart",
    response_model=SimpatiChartSaveResponse,
    responses={
        400: {"model": SimpatiChartSaveResponse},
        403: {"model": SimpatiChartSaveResponse},
        500: {"model": SimpatiChartSaveResponse},
    },
)
def save_project_simpati_chart_endpoint(
    request: SimpatiChartSaveRequest,
) -> SimpatiChartSaveResponse | JSONResponse:
    """Save a SIMPATI chart for later PowerPoint generation."""
    try:
        return save_project_simpati_chart(
            request.test_root,
            request.image_base64,
        )
    except SimpatiChartSaveError as error:
        return JSONResponse(
            status_code=error.status_code,
            content=jsonable_encoder(error.to_response()),
        )


@router.post(
    "/simpati/charts",
    response_model=SimpatiChartListResponse,
    responses={
        400: {"model": SimpatiChartListResponse},
        403: {"model": SimpatiChartListResponse},
        500: {"model": SimpatiChartListResponse},
    },
)
def list_project_simpati_charts_endpoint(
    request: ProjectInspectionRequest,
) -> SimpatiChartListResponse | JSONResponse:
    """List saved SIMPATI charts included in Test Results."""
    try:
        return list_project_simpati_charts(request.test_root)
    except SimpatiChartManagementError as error:
        return JSONResponse(
            status_code=error.status_code,
            content=jsonable_encoder(error.to_list_response()),
        )


@router.get("/simpati/chart", response_model=None)
def open_project_simpati_chart_endpoint(
    test_root: str,
    chart_name: str,
) -> Response:
    """Serve one validated saved chart for safe viewing."""
    try:
        chart_path = resolve_project_simpati_chart(
            test_root,
            chart_name,
        )
        media_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
        }

        return FileResponse(
            chart_path,
            media_type=media_types[chart_path.suffix.casefold()],
            headers={"Cache-Control": "no-store"},
        )
    except SimpatiChartManagementError as error:
        return JSONResponse(
            status_code=error.status_code,
            content=jsonable_encoder(error.to_list_response()),
        )


@router.post(
    "/simpati/delete-chart",
    response_model=SimpatiChartDeleteResponse,
    responses={
        400: {"model": SimpatiChartDeleteResponse},
        403: {"model": SimpatiChartDeleteResponse},
        404: {"model": SimpatiChartDeleteResponse},
        500: {"model": SimpatiChartDeleteResponse},
    },
)
def delete_project_simpati_chart_endpoint(
    request: SimpatiChartDeleteRequest,
) -> SimpatiChartDeleteResponse | JSONResponse:
    """Delete one validated saved SIMPATI chart."""
    try:
        return delete_project_simpati_chart(
            request.test_root,
            request.chart_name,
        )
    except SimpatiChartManagementError as error:
        return JSONResponse(
            status_code=error.status_code,
            content=jsonable_encoder(error.to_delete_response()),
        )