from pydantic import BaseModel, Field

from .common import ApiError


class SimpatiChartSaveRequest(BaseModel):
    """PNG chart data to save for a test."""

    test_root: str = Field(
        min_length=1,
        description="Full path to the test folder.",
    )
    image_base64: str = Field(
        min_length=1,
        max_length=25_000_000,
        description="Base64-encoded PNG image.",
    )


class SimpatiChartDeleteRequest(BaseModel):
    """Saved SIMPATI chart to delete."""

    test_root: str = Field(
        min_length=1,
        description="Full path to the test folder.",
    )
    chart_name: str = Field(
        min_length=1,
        max_length=255,
        description="Exact saved chart file name.",
    )


class SimpatiSavedChart(BaseModel):
    """Saved SIMPATI image available for Test Results."""

    chart_name: str
    chart_path: str
    size_bytes: int


class SimpatiChartListResponse(BaseModel):
    """Saved SIMPATI charts discovered for a test."""

    success: bool
    test_root: str
    charts_count: int = 0
    charts: list[SimpatiSavedChart] = Field(default_factory=list)
    errors: list[ApiError] = Field(default_factory=list)


class SimpatiChartSaveResponse(BaseModel):
    """Result of saving a SIMPATI chart image."""

    success: bool
    test_root: str
    chart_path: str | None = None
    chart_name: str | None = None
    charts_count: int = 0
    charts: list[SimpatiSavedChart] = Field(default_factory=list)
    errors: list[ApiError] = Field(default_factory=list)


class SimpatiChartDeleteResponse(BaseModel):
    """Result of deleting a saved SIMPATI chart."""

    success: bool
    test_root: str
    deleted_chart_name: str | None = None
    charts_count: int = 0
    charts: list[SimpatiSavedChart] = Field(default_factory=list)
    errors: list[ApiError] = Field(default_factory=list)


class SimpatiPreviewChannel(BaseModel):
    """Channel values included in the interactive preview."""

    id: str
    label: str
    source_column: str
    thermal: bool
    values: list[float | None] = Field(default_factory=list)


class SimpatiInspectionResponse(BaseModel):
    """Result of inspecting an optional SIMPATI acquisition file."""

    success: bool
    test_root: str
    available: bool
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
