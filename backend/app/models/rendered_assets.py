from pydantic import BaseModel, Field

from .common import ApiError


class RenderedAssetResult(BaseModel):
    """One image of ``04_Report/_RenderedAssets`` selectable for the report.

    The origin (``source``) is informative only. Whether the image can be
    included in the PowerPoint depends on its format and content, never on
    where it came from.
    """

    name: str
    relative_path: str = Field(
        description=(
            "Path relative to the test folder with '/' separators, e.g. "
            "04_Report/_RenderedAssets/graphtec_chart_01.png. It identifies "
            "the asset in every request."
        ),
    )
    extension: str
    size: int
    source: str = Field(
        description="Informative origin: simpati, graphtec, manual, unknown...",
    )
    metadata_name: str | None = None


class RenderedAssetWarning(BaseModel):
    """A file of ``_RenderedAssets`` that is not a selectable image."""

    name: str
    code: str
    message: str


class RenderedAssetRequest(BaseModel):
    """One rendered asset identified by its relative path."""

    test_root: str = Field(
        min_length=1,
        description="Full path to the test folder.",
    )
    relative_path: str = Field(
        min_length=1,
        max_length=1024,
        description=(
            "Asset path relative to the test folder, as returned by "
            "POST /projects/rendered-assets."
        ),
    )


class RenderedAssetListResponse(BaseModel):
    """Inventory of selectable images, in a stable order."""

    success: bool
    test_root: str
    directory_found: bool = False
    assets_count: int = 0
    assets: list[RenderedAssetResult] = Field(default_factory=list)
    warnings: list[RenderedAssetWarning] = Field(default_factory=list)
    errors: list[ApiError] = Field(default_factory=list)


class RenderedAssetDeleteResponse(BaseModel):
    """Result of deleting one rendered asset, with the refreshed inventory."""

    success: bool
    test_root: str
    deleted_relative_path: str | None = None
    directory_found: bool = False
    assets_count: int = 0
    assets: list[RenderedAssetResult] = Field(default_factory=list)
    warnings: list[RenderedAssetWarning] = Field(default_factory=list)
    errors: list[ApiError] = Field(default_factory=list)
