"""Generic inventory, opening and deletion of ``04_Report/_RenderedAssets``.

Every image of the folder is listed regardless of where it came from.
SIMPATI and Graphtec keep their own analysis and chart generation; once an
image is saved it is just another rendered asset that the user can select
for the PowerPoint. Paths received from the client are rebuilt and confined
to ``_RenderedAssets`` on the server.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, TypeVar

from src.report_generator.rendered_assets import (
    RenderedAssetInventory,
    RenderedAssetNotFoundError,
    RenderedAssetPathError,
    RenderedAssetUnsupportedError,
    delete_rendered_asset,
    list_rendered_assets,
    relative_asset_path,
    resolve_rendered_asset,
)

from ..models.common import ApiError
from ..models.rendered_assets import (
    RenderedAssetDeleteResponse,
    RenderedAssetListResponse,
    RenderedAssetResult,
    RenderedAssetWarning,
)

#: Media types served for the accepted image extensions.
IMAGE_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}

ResponseT = TypeVar("ResponseT")


class RenderedAssetServiceError(Exception):
    """Controlled error converted into a structured API response."""

    def __init__(
        self,
        *,
        test_root: Path | str,
        status_code: int,
        error: ApiError,
    ) -> None:
        super().__init__(error.message)
        self.test_root = str(test_root)
        self.status_code = status_code
        self.error = error

    def to_response(self, response_type: Callable[..., ResponseT]) -> ResponseT:
        return response_type(
            success=False,
            test_root=self.test_root,
            errors=[self.error],
        )


def _api_error(code: str, error: Exception, fallback: str) -> ApiError:
    message = str(error).strip() or fallback
    return ApiError(
        code=code,
        message=message,
        exception_type=type(error).__name__,
    )


def service_error(
    test_root: Path | str,
    error: Exception,
) -> RenderedAssetServiceError:
    """Map any exception to a structured error without tracebacks."""
    if isinstance(error, RenderedAssetServiceError):
        return error
    if isinstance(error, RenderedAssetNotFoundError):
        status, code = 404, "rendered_asset_not_found"
    elif isinstance(error, RenderedAssetUnsupportedError):
        status, code = 415, "rendered_asset_unsupported"
    elif isinstance(error, RenderedAssetPathError):
        status, code = 400, "rendered_asset_invalid_path"
    elif isinstance(error, PermissionError):
        status, code = 403, "rendered_asset_permission_denied"
    elif isinstance(error, (FileNotFoundError, NotADirectoryError, ValueError)):
        status, code = 400, "rendered_asset_invalid_request"
    else:
        status, code = 500, "rendered_asset_failed"
    return RenderedAssetServiceError(
        test_root=test_root,
        status_code=status,
        error=_api_error(
            code,
            error,
            "The rendered assets request could not be completed.",
        ),
    )


def _project_root(test_root: str | Path) -> Path:
    project_root = Path(test_root).expanduser().resolve()
    if not project_root.is_dir():
        raise RenderedAssetPathError(
            f"The test folder does not exist: {project_root}"
        )
    return project_root


def asset_results(inventory: RenderedAssetInventory) -> list[RenderedAssetResult]:
    return [
        RenderedAssetResult(
            name=asset.name,
            relative_path=asset.relative_path,
            extension=asset.extension,
            size=asset.size,
            source=asset.source,
            metadata_name=asset.metadata_name,
        )
        for asset in inventory.assets
    ]


def warning_results(inventory: RenderedAssetInventory) -> list[RenderedAssetWarning]:
    return [
        RenderedAssetWarning(name=w.name, code=w.code, message=w.message)
        for w in inventory.warnings
    ]


def inventory_fields(project_root: Path) -> dict:
    """Inventory fields shared by the list, delete and save responses."""
    inventory = list_rendered_assets(project_root)
    return {
        "directory_found": inventory.exists,
        "assets_count": len(inventory.assets),
        "assets": asset_results(inventory),
        "warnings": warning_results(inventory),
    }


def list_project_rendered_assets(
    test_root: str | Path,
) -> RenderedAssetListResponse:
    """List every selectable image of ``04_Report/_RenderedAssets``."""
    try:
        project_root = _project_root(test_root)
        return RenderedAssetListResponse(
            success=True,
            test_root=str(project_root),
            errors=[],
            **inventory_fields(project_root),
        )
    except Exception as error:
        raise service_error(test_root, error) from error


def resolve_project_rendered_asset(
    test_root: str | Path,
    relative_path: str,
) -> Path:
    """Resolve one image for safe viewing. Rejects anything else."""
    try:
        project_root = _project_root(test_root)
        return resolve_rendered_asset(project_root, relative_path)
    except Exception as error:
        raise service_error(test_root, error) from error


def media_type_for(image_path: Path) -> str:
    return IMAGE_MEDIA_TYPES[image_path.suffix.casefold()]


def delete_project_rendered_asset(
    test_root: str | Path,
    relative_path: str,
) -> RenderedAssetDeleteResponse:
    """Delete one image (and its metadata file) and return the inventory."""
    try:
        project_root = _project_root(test_root)
        deleted = delete_rendered_asset(project_root, relative_path)
        return RenderedAssetDeleteResponse(
            success=True,
            test_root=str(project_root),
            deleted_relative_path=relative_asset_path(deleted.name),
            errors=[],
            **inventory_fields(project_root),
        )
    except Exception as error:
        raise service_error(test_root, error) from error
