from pydantic import BaseModel, Field

from .common import ApiError
from .rendered_assets import RenderedAssetResult, RenderedAssetWarning


class GraphtecFileRequest(BaseModel):
    """Graphtec file selected from the project inspection."""

    test_root: str = Field(
        min_length=1,
        description="Full path to the test folder.",
    )
    relative_path: str = Field(
        min_length=1,
        max_length=1024,
        description=(
            "File path relative to the test folder, as returned by "
            "POST /projects/inspect. It must be inside 03_Data/02_Graphtec."
        ),
    )


class GraphtecValueRange(BaseModel):
    """Visible value range of one series axis (Y zoom)."""

    minimum: float
    maximum: float


class GraphtecChartSettings(BaseModel):
    """Chart settings. The X axis is always elapsed_time_seconds."""

    series: list[str] = Field(
        min_length=1,
        max_length=2,
        description="Series ids: voltage, current (DCW) or resistance (IR).",
    )
    title: str = Field(default="", max_length=200)
    show_legend: bool = True
    show_phase_separators: bool = True
    time_min: float | None = Field(
        default=None,
        description="Start of the elapsed time range in seconds.",
    )
    time_max: float | None = Field(
        default=None,
        description="End of the elapsed time range in seconds.",
    )
    value_ranges: dict[str, GraphtecValueRange] | None = Field(
        default=None,
        description=(
            "Visible Y range per series id (voltage, current, resistance), "
            "as shown by the interactive viewer. Missing series use the "
            "automatic range."
        ),
    )


class GraphtecChartRequest(GraphtecFileRequest):
    """Graphtec file and chart settings."""

    chart: GraphtecChartSettings


class GraphtecRecordResult(BaseModel):
    """One normalized Graphtec record."""

    line_number: int
    channel: int
    test_type: str
    status: str
    raw_voltage: str
    voltage_value: float
    voltage_unit: str
    raw_measurement: str
    measurement_operator: str | None = None
    measurement_value: float
    measurement_unit: str
    measurement_quantity: str
    normalized_value: float
    normalized_unit: str
    phase: str
    phase_time_seconds: float
    elapsed_time_seconds: float


class GraphtecSeriesResult(BaseModel):
    """Series that can be drawn for the acquisition."""

    id: str
    label: str
    unit: str
    axis: str
    default_selected: bool = True


class GraphtecPhaseSegmentResult(BaseModel):
    """Consecutive records sharing a phase letter."""

    phase: str
    start_elapsed_seconds: float
    end_elapsed_seconds: float
    first_line: int
    last_line: int
    records_count: int


class GraphtecChartData(BaseModel):
    """Normalized values used to draw the chart, aligned by index."""

    elapsed_time_seconds: list[float] = Field(default_factory=list)
    voltage_kv: list[float] = Field(default_factory=list)
    measurement: list[float] = Field(default_factory=list)
    measurement_operator: list[str | None] = Field(default_factory=list)
    status: list[str] = Field(default_factory=list)
    phase: list[str] = Field(default_factory=list)
    truncated: bool = False


class GraphtecInspectionResponse(BaseModel):
    """Result of reading one Graphtec file."""

    success: bool
    test_root: str
    source: str = "graphtec"
    format: str | None = None
    format_label: str | None = None
    file_name: str | None = None
    relative_path: str | None = None
    records_count: int = 0
    channels: list[int] = Field(default_factory=list)
    test_types: list[str] = Field(default_factory=list)
    statuses: list[str] = Field(default_factory=list)
    phases: list[str] = Field(default_factory=list)
    phase_segments: list[GraphtecPhaseSegmentResult] = Field(
        default_factory=list
    )
    final_result: str | None = None
    available_series: list[GraphtecSeriesResult] = Field(default_factory=list)
    original_units: dict[str, list[str]] = Field(default_factory=dict)
    normalized_units: dict[str, str] = Field(default_factory=dict)
    elapsed_time_start: float | None = None
    elapsed_time_end: float | None = None
    duration_seconds: float | None = None
    limited_values_count: int = 0
    default_title: str | None = None
    preview_records: list[GraphtecRecordResult] = Field(default_factory=list)
    preview_truncated: bool = False
    chart_data: GraphtecChartData = Field(default_factory=GraphtecChartData)
    warnings: list[str] = Field(default_factory=list)
    errors: list[ApiError] = Field(default_factory=list)


class GraphtecChartAxis(BaseModel):
    position: str
    label: str
    series: list[str] = Field(default_factory=list)


class GraphtecPhaseMarker(BaseModel):
    phase: str
    elapsed_time_seconds: float


class GraphtecChartPreviewResponse(BaseModel):
    """Rendered chart preview. Nothing is saved."""

    success: bool
    test_root: str
    relative_path: str | None = None
    image_base64: str | None = None
    width: int = 0
    height: int = 0
    title: str | None = None
    x_axis_label: str = "Elapsed time [s]"
    series: list[GraphtecSeriesResult] = Field(default_factory=list)
    axes: list[GraphtecChartAxis] = Field(default_factory=list)
    time_start: float | None = None
    time_end: float | None = None
    full_range: bool = True
    records_plotted: int = 0
    limited_points: int = 0
    result_points: int = 0
    phase_markers: list[GraphtecPhaseMarker] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    errors: list[ApiError] = Field(default_factory=list)


class GraphtecChartSaveResponse(BaseModel):
    """Result of saving a Graphtec chart.

    The saved image becomes a generic rendered asset. The response returns
    the refreshed inventory of ``04_Report/_RenderedAssets`` so the client
    can add the new image to the report selection.
    """

    success: bool
    test_root: str
    chart_name: str | None = None
    chart_path: str | None = None
    relative_path: str | None = None
    metadata_name: str | None = None
    directory_found: bool = False
    assets_count: int = 0
    assets: list[RenderedAssetResult] = Field(default_factory=list)
    warnings: list[RenderedAssetWarning] = Field(default_factory=list)
    errors: list[ApiError] = Field(default_factory=list)
