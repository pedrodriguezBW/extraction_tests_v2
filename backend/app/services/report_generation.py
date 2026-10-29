from pathlib import Path
from typing import Sequence
from zipfile import BadZipFile

from pptx.exc import PackageNotFoundError
from config import POWERPOINT_TEMPLATE_PATH
from src.report_generator import generate_climatic_report
from src.report_generator.generator import resolve_result_images
from src.report_generator.rendered_assets import (
    RenderedAssetError,
    RenderedAssetNotFoundError,
    RenderedAssetPathError,
    RenderedAssetUnsupportedError,
    relative_asset_path,
)

from ..models.common import ApiError
from ..models.report_generation import ReportGenerationResponse


class ReportGenerationError(Exception):
    """Controlled PowerPoint generation error."""

    def __init__(
        self,
        *,
        test_root: Path,
        status_code: int,
        error: ApiError,
    ) -> None:
        super().__init__(error.message)
        self.test_root = test_root
        self.status_code = status_code
        self.error = error

    def to_response(self) -> ReportGenerationResponse:
        return ReportGenerationResponse(
            success=False,
            test_root=str(self.test_root),
            errors=[self.error],
        )


def _build_generation_error(
    test_root: Path,
    error: Exception,
) -> ReportGenerationError:
    if isinstance(error, PermissionError):
        status_code = 403
        code = "report_generation_permission_denied"
    elif isinstance(error, RenderedAssetNotFoundError):
        status_code = 404
        code = "report_generation_rendered_asset_not_found"
    elif isinstance(error, RenderedAssetUnsupportedError):
        status_code = 415
        code = "report_generation_rendered_asset_unsupported"
    elif isinstance(error, (RenderedAssetPathError, RenderedAssetError)):
        status_code = 400
        code = "report_generation_invalid_rendered_asset"
    elif isinstance(
        error,
        (
            FileNotFoundError,
            NotADirectoryError,
            ValueError,
            KeyError,
            TypeError,
            IndexError,
            RuntimeError,
            BadZipFile,
            PackageNotFoundError,
        ),
    ):
        status_code = 400
        code = "report_generation_invalid_project"
    else:
        status_code = 500
        code = "report_generation_failed"

    message = str(error).strip()
    if not message:
        message = "The PowerPoint report could not be generated."

    return ReportGenerationError(
        test_root=test_root,
        status_code=status_code,
        error=ApiError(
            code=code,
            message=message,
            exception_type=type(error).__name__,
        ),
    )


def generate_project_report(
    test_root: str | Path,
    selected_rendered_assets: Sequence[str] | None = None,
) -> ReportGenerationResponse:
    """
    Generate the report with the existing PowerPoint engine.

    The engine reads 04_Report/test_metadata.json and saves the
    PowerPoint directly in 04_Report. ``selected_rendered_assets`` is the
    ordered list of images of ``04_Report/_RenderedAssets`` to insert in
    Test Results. The selection is validated here first so that an invalid,
    duplicated, external or missing image is reported as a structured error
    before any file is written; the engine then receives exactly that list.
    An empty list generates the report without result images. ``None``
    (field omitted) includes every valid image of the inventory.
    """
    project_root = Path(test_root).expanduser()

    try:
        project_root = project_root.resolve()
        selection = (
            None
            if selected_rendered_assets is None
            else list(selected_rendered_assets)
        )
        resolved_images = resolve_result_images(project_root, selection)
        template_path = Path(
            POWERPOINT_TEMPLATE_PATH
        ).expanduser().resolve()
        output_path = Path(
            generate_climatic_report(
                test_root=project_root,
                template_path=template_path,
                selected_rendered_assets=[
                    relative_asset_path(image.name)
                    for image in resolved_images
                ],
            )
        ).resolve()
    except Exception as error:
        raise _build_generation_error(project_root, error) from error

    return ReportGenerationResponse(
        success=True,
        test_root=str(project_root),
        report_path=str(output_path),
        report_name=output_path.name,
        rendered_assets_count=len(resolved_images),
        rendered_assets=[
            relative_asset_path(image.name) for image in resolved_images
        ],
        errors=[],
    )
