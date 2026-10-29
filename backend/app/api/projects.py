from fastapi import APIRouter, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, FileResponse

from ..models.project import (
    ProjectInspectionRequest,
    ProjectInspectionResponse,
)
from ..models.graphtec import (
    GraphtecChartPreviewResponse,
    GraphtecChartRequest,
    GraphtecChartSaveResponse,
    GraphtecFileRequest,
    GraphtecInspectionResponse,
)
from ..models.rendered_assets import (
    RenderedAssetDeleteResponse,
    RenderedAssetListResponse,
    RenderedAssetRequest,
)
from ..models.report_generation import (
    ReportGenerationRequest,
    ReportGenerationResponse,
)
from ..models.simpati_inspection import (
    SimpatiChartSaveRequest,
    SimpatiChartSaveResponse,
    SimpatiInspectionResponse,
)
from ..services.graphtec_inspection import (
    GraphtecServiceError,
    inspect_project_graphtec,
    preview_project_graphtec_chart,
    save_project_graphtec_chart,
)
from ..services.project_inspection import inspect_project
from ..services.rendered_assets import (
    RenderedAssetServiceError,
    delete_project_rendered_asset,
    list_project_rendered_assets,
    media_type_for,
    resolve_project_rendered_asset,
)
from ..services.report_generation import (
    ReportGenerationError,
    generate_project_report,
)
from ..services.simpati_inspection import (
    SimpatiChartSaveError,
    SimpatiInspectionError,
    inspect_project_simpati,
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
        404: {"model": ReportGenerationResponse},
        415: {"model": ReportGenerationResponse},
        500: {"model": ReportGenerationResponse},
    },
)
def generate_project_report_endpoint(
    request: ReportGenerationRequest,
) -> ReportGenerationResponse | JSONResponse:
    """Generate the PowerPoint from test_metadata.json and the selected images.

    ``selected_rendered_assets`` lists, in order, the images of
    ``04_Report/_RenderedAssets`` to insert in Test Results. Only those
    images are inserted; an empty list generates the report without them.
    """
    try:
        return generate_project_report(
            request.test_root,
            request.selected_rendered_assets,
        )
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
    """Save a SIMPATI chart in 04_Report/_RenderedAssets."""
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


def _rendered_asset_error_response(
    error: RenderedAssetServiceError,
    response_type,
) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content=jsonable_encoder(error.to_response(response_type)),
    )


_RENDERED_ASSET_ERROR_STATUSES = (400, 403, 404, 415, 500)


@router.post(
    "/rendered-assets",
    response_model=RenderedAssetListResponse,
    responses={
        code: {"model": RenderedAssetListResponse}
        for code in _RENDERED_ASSET_ERROR_STATUSES
    },
)
def list_project_rendered_assets_endpoint(
    request: ProjectInspectionRequest,
) -> RenderedAssetListResponse | JSONResponse:
    """List the images of 04_Report/_RenderedAssets selectable for the report.

    Every PNG, JPG or JPEG placed directly in the folder is listed whatever
    its origin (SIMPATI, Graphtec, manual...). Unsupported files are
    reported as warnings and never block the listing.
    """
    try:
        return list_project_rendered_assets(request.test_root)
    except RenderedAssetServiceError as error:
        return _rendered_asset_error_response(error, RenderedAssetListResponse)


@router.get("/rendered-asset", response_model=None)
def open_project_rendered_asset_endpoint(
    test_root: str,
    relative_path: str,
) -> Response:
    """Serve one validated image of 04_Report/_RenderedAssets."""
    try:
        image_path = resolve_project_rendered_asset(test_root, relative_path)
        return FileResponse(
            image_path,
            media_type=media_type_for(image_path),
            headers={"Cache-Control": "no-store"},
        )
    except RenderedAssetServiceError as error:
        return _rendered_asset_error_response(error, RenderedAssetListResponse)


@router.post(
    "/rendered-assets/delete",
    response_model=RenderedAssetDeleteResponse,
    responses={
        code: {"model": RenderedAssetDeleteResponse}
        for code in _RENDERED_ASSET_ERROR_STATUSES
    },
)
def delete_project_rendered_asset_endpoint(
    request: RenderedAssetRequest,
) -> RenderedAssetDeleteResponse | JSONResponse:
    """Delete one image of 04_Report/_RenderedAssets and its metadata file."""
    try:
        return delete_project_rendered_asset(
            request.test_root,
            request.relative_path,
        )
    except RenderedAssetServiceError as error:
        return _rendered_asset_error_response(
            error, RenderedAssetDeleteResponse
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
