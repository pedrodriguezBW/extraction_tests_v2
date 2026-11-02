from pydantic import BaseModel, Field

from .common import ApiError
from .rendered_assets import RenderedAssetResult, RenderedAssetWarning


class SimpatiInspectionRequest(BaseModel):
    """Test folder and, optionally, the acquisition to preview."""

    test_root: str = Field(
        min_length=1,
        description="Full path to the test folder.",
    )
    relative_path: str | None = Field(
        default=None,
        max_length=1024,
        description=(
            "Acquisition to preview (.x01 to .x99), relative to the test "
            "folder as returned by POST /projects/inspect. When omitted, "
            "the first acquisition with representable channels is previewed."
        ),
    )


class SimpatiChartSaveRequest(BaseModel):
    """PNG chart data to save for one SIMPATI acquisition."""

    test_root: str = Field(
        min_length=1,
        description="Full path to the test folder.",
    )
    relative_path: str = Field(
        min_length=1,
        max_length=1024,
        description=(
            "Source acquisition of the chart (.x01 to .x99), relative to "
            "the test folder. It decides the chart name chart_simpati_xNN_MM."
        ),
    )
    image_base64: str = Field(
        min_length=1,
        max_length=25_000_000,
        description="Base64-encoded PNG image.",
    )


class SimpatiChartSaveResponse(BaseModel):
    """Result of saving a SIMPATI chart image.

    The saved image becomes a generic rendered asset. The response returns
    the refreshed inventory of ``04_Report/_RenderedAssets`` so the client
    can add the new image to the report selection.
    """

    success: bool
    test_root: str
    chart_path: str | None = None
    chart_name: str | None = None
    relative_path: str | None = None
    source_relative_path: str | None = None
    acquisition_index: int | None = None
    directory_found: bool = False
    assets_count: int = 0
    assets: list[RenderedAssetResult] = Field(default_factory=list)
    warnings: list[RenderedAssetWarning] = Field(default_factory=list)
    errors: list[ApiError] = Field(default_factory=list)


class SimpatiPreviewChannel(BaseModel):
    """Channel values included in the interactive preview."""

    id: str
    label: str
    source_column: str
    thermal: bool
    role: str | None = None
    unit: str = ""
    values: list[float | None] = Field(default_factory=list)


class SimpatiChannelResult(BaseModel):
    """Channel detected in an acquisition, recognized or not."""

    column: str
    name: str
    unit: str = ""
    kind: str
    role: str | None = None
    label: str | None = None
    thermal: bool = False
    has_data: bool = True


class SimpatiAcquisitionSummary(BaseModel):
    """Isolated analysis result of one ``.xNN`` acquisition."""

    index: int
    label: str = Field(description="Acquisition identifier, e.g. x04.")
    file_name: str
    relative_path: str
    size: int = 0
    status: str = Field(
        description=(
            "ready, no_thermal_channels, incompatible or error."
        ),
    )
    encoding: str | None = None
    records_count: int = 0
    acquisition_start: str | None = None
    acquisition_end: str | None = None
    device: str | None = None
    program: str | None = None
    channels_count: int = 0
    channels: list[SimpatiChannelResult] = Field(default_factory=list)
    thermal_channels: list[str] = Field(
        default_factory=list,
        description="Labels of the representable thermal channels.",
    )
    rejected_rows: int = 0
    rejected_rows_examples: list[str] = Field(default_factory=list)
    error: ApiError | None = None


class SimpatiInspectionResponse(BaseModel):
    """Every SIMPATI acquisition of the test and the selected preview.

    ``acquisitions`` lists every ``.xNN`` file in numeric order with its
    own status: an incompatible file never hides the others. The fields
    below ``selected_relative_path`` describe the previewed acquisition.
    """

    success: bool
    test_root: str
    available: bool
    acquisitions: list[SimpatiAcquisitionSummary] = Field(default_factory=list)
    found_count: int = 0
    processed_count: int = 0
    ready_count: int = 0
    without_thermal_count: int = 0
    incompatible_count: int = 0
    selected_relative_path: str | None = None
    selected_index: int | None = None
    selected_status: str | None = None
    file_name: str | None = None
    file_path: str | None = None
    encoding: str | None = None
    records_count: int = 0
    acquisition_start: str | None = None
    acquisition_end: str | None = None
    channels: list[str] = Field(default_factory=list)
    preview_timestamps: list[str] = Field(default_factory=list)
    thermal_channels: list[SimpatiPreviewChannel] = Field(
        default_factory=list
    )
    advanced_channels: list[SimpatiPreviewChannel] = Field(
        default_factory=list
    )
    errors: list[ApiError] = Field(default_factory=list)
