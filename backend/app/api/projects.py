from fastapi import APIRouter, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, FileResponse

from ..models.project import (
    ProjectInspectionRequest,
    ProjectInspectionResponse,
)
from ..models.graphtec import (
    GraphtecChartDeleteRequest,
    GraphtecChartDeleteResponse,
    GraphtecChartListResponse,
    GraphtecChartPreviewResponse,
    GraphtecChartRequest,
    GraphtecChartSaveResponse,
    GraphtecFileRequest,
    GraphtecInspectionResponse,
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
from ..services.graphtec_inspection import (
    GraphtecServiceError,
    delete_project_graphtec_chart,
    inspect_project_graphtec,
    list_project_graphtec_charts,
    preview_project_graphtec_chart,
    resolve_project_graphtec_chart,
    save_project_graphtec_chart,
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


def _graphtec_error_response(
    error: GraphtecServiceError,
    response_type,
) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content=jsonable_encoder(error.to_response(response_type)),
    )


_GRAPHTEC_ERROR_STATUSES = (400, 403, 404, 415, 500)


@router.post(
    "/graphtec/inspect",
    response_model=GraphtecInspectionResponse,
    responses={
        code: {"model": GraphtecInspectionResponse}
        for code in _GRAPHTEC_ERROR_STATUSES
    },
)
def inspect_project_graphtec_endpoint(
    request: GraphtecFileRequest,
) -> GraphtecInspectionResponse | JSONResponse:
    """Read and summarize the selected Graphtec file."""
    try:
        return inspect_project_graphtec(
            request.test_root,
            request.relative_path,
        )
    except GraphtecServiceError as error:
        return _graphtec_error_response(error, GraphtecInspectionResponse)


@router.post(
    "/graphtec/preview-chart",
    response_model=GraphtecChartPreviewResponse,
    responses={
        code: {"model": GraphtecChartPreviewResponse}
        for code in _GRAPHTEC_ERROR_STATUSES
    },
)
def preview_project_graphtec_chart_endpoint(
    request: GraphtecChartRequest,
) -> GraphtecChartPreviewResponse | JSONResponse:
    """Render a Graphtec chart preview without saving it."""
    try:
        return preview_project_graphtec_chart(
            request.test_root,
            request.relative_path,
            request.chart,
        )
    except GraphtecServiceError as error:
        return _graphtec_error_response(error, GraphtecChartPreviewResponse)


@router.post(
    "/graphtec/save-chart",
    response_model=GraphtecChartSaveResponse,
    responses={
        code: {"model": GraphtecChartSaveResponse}
        for code in _GRAPHTEC_ERROR_STATUSES
    },
)
def save_project_graphtec_chart_endpoint(
    request: GraphtecChartRequest,
) -> GraphtecChartSaveResponse | JSONResponse:
    """Render and save a Graphtec chart in 04_Report/_RenderedAssets."""
    try:
        return save_project_graphtec_chart(
            request.test_root,
            request.relative_path,
            request.chart,
        )
    except GraphtecServiceError as error:
        return _graphtec_error_response(error, GraphtecChartSaveResponse)


@router.post(
    "/graphtec/charts",
    response_model=GraphtecChartListResponse,
    responses={
        code: {"model": GraphtecChartListResponse}
        for code in _GRAPHTEC_ERROR_STATUSES
    },
)
def list_project_graphtec_charts_endpoint(
    request: ProjectInspectionRequest,
) -> GraphtecChartListResponse | JSONResponse:
    """List saved Graphtec charts. They are not added to the PowerPoint."""
    try:
        return list_project_graphtec_charts(request.test_root)
    except GraphtecServiceError as error:
        return _graphtec_error_response(error, GraphtecChartListResponse)


@router.get("/graphtec/chart", response_model=None)
def open_project_graphtec_chart_endpoint(
    test_root: str,
    chart_name: str,
) -> Response:
    """Serve one saved Graphtec chart."""
    try:
        chart_path = resolve_project_graphtec_chart(test_root, chart_name)
        return FileResponse(
            chart_path,
            media_type="image/png",
            headers={"Cache-Control": "no-store"},
        )
    except GraphtecServiceError as error:
        return _graphtec_error_response(error, GraphtecChartListResponse)


@router.post(
    "/graphtec/delete-chart",
    response_model=GraphtecChartDeleteResponse,
    responses={
        code: {"model": GraphtecChartDeleteResponse}
        for code in _GRAPHTEC_ERROR_STATUSES
    },
)
def delete_project_graphtec_chart_endpoint(
    request: GraphtecChartDeleteRequest,
) -> GraphtecChartDeleteResponse | JSONResponse:
    """Delete one saved Graphtec chart and its metadata."""
    try:
        return delete_project_graphtec_chart(
            request.test_root,
            request.chart_name,
        )
    except GraphtecServiceError as error:
        return _graphtec_error_response(error, GraphtecChartDeleteResponse)
