"""Graphtec inspection, chart preview and chart saving.

Every request rebuilds and confines the file path on the server, reads the
file content without modifying it and never interprets the file name.
Saved charts are written to ``04_Report/_RenderedAssets`` with generated
names and a JSON metadata file. From then on they are generic rendered
assets: the user selects in the interface which images of the folder the
PowerPoint includes (see ``services.rendered_assets``).
"""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, TypeVar

from src.report_generator.graphtec import (
    GRAPHTEC_SOURCE,
    GraphtecAcquisition,
    GraphtecChartConfig,
    GraphtecChartConfigError,
    GraphtecFormatError,
    GraphtecPathError,
    GraphtecUnsupportedFormatError,
    available_series,
    default_title,
    read_graphtec_file,
    render_graphtec_chart,
    resolve_graphtec_file,
)
from src.report_generator.graphtec.charts import (
    X_AXIS_FIELD,
    X_AXIS_LABEL,
    X_AXIS_UNIT,
    GraphtecChartRender,
)
from src.report_generator.graphtec.files import relative_to_test_root
from src.report_generator.rendered_assets import (
    METADATA_SUFFIX,
    metadata_path_for,
    prepare_rendered_assets_directory,
    relative_asset_path,
    write_new_chart,
)

from ..models.common import ApiError
from ..models.graphtec import (
    GraphtecChartAxis,
    GraphtecChartData,
    GraphtecChartPreviewResponse,
    GraphtecChartSaveResponse,
    GraphtecChartSettings,
    GraphtecInspectionResponse,
    GraphtecPhaseMarker,
    GraphtecPhaseSegmentResult,
    GraphtecRecordResult,
    GraphtecSeriesResult,
)
from .rendered_assets import inventory_fields

#: Prefix of saved Graphtec charts. The name is only a label: it never
#: decides whether the chart is included in the PowerPoint.
CHART_PREFIX = "graphtec_chart"
METADATA_SCHEMA_VERSION = 1

MAX_PREVIEW_RECORDS = 25
MAX_CHART_DATA_POINTS = 5000

ResponseT = TypeVar("ResponseT")


class GraphtecServiceError(Exception):
    """Controlled error converted into a structured API response."""

    def __init__(
        self,
        *,
        test_root: Path | str,
        status_code: int,
        errors: list[ApiError],
    ) -> None:
        super().__init__(errors[0].message if errors else "Graphtec error")
        self.test_root = str(test_root)
        self.status_code = status_code
        self.errors = errors

    def to_response(self, response_type: Callable[..., ResponseT]) -> ResponseT:
        return response_type(
            success=False,
            test_root=self.test_root,
            errors=self.errors,
        )


def _error(code: str, message: str, exception: Exception) -> ApiError:
    return ApiError(
        code=code,
        message=message,
        exception_type=type(exception).__name__,
    )


def _service_error(test_root: Path | str, error: Exception) -> GraphtecServiceError:
    """Map any exception to a structured error without tracebacks."""
    if isinstance(error, GraphtecServiceError):
        return error
    if isinstance(error, GraphtecPathError):
        status, errors = 400, [_error("graphtec_invalid_path", str(error), error)]
    elif isinstance(error, GraphtecUnsupportedFormatError):
        status, errors = 415, [
            _error("graphtec_unsupported_format", str(error), error)
        ]
    elif isinstance(error, GraphtecFormatError):
        status = 400
        errors = [_error("graphtec_invalid_file", str(error), error)] + [
            _error("graphtec_invalid_line", issue, error)
            for issue in error.issues
            if issue != str(error)
        ]
    elif isinstance(error, GraphtecChartConfigError):
        status, errors = 400, [
            _error("graphtec_invalid_chart_config", str(error), error)
        ]
    elif isinstance(error, PermissionError):
        status, errors = 403, [
            _error(
                "graphtec_permission_denied",
                "Access to the file or folder was denied.",
                error,
            )
        ]
    elif isinstance(error, (FileNotFoundError, NotADirectoryError, ValueError)):
        status, errors = 400, [
            _error("graphtec_invalid_request", str(error) or "Invalid request.", error)
        ]
    else:
        status, errors = 500, [
            _error(
                "graphtec_failed",
                "The Graphtec request could not be completed.",
                error,
            )
        ]
    return GraphtecServiceError(test_root=test_root, status_code=status, errors=errors)


def _project_root(test_root: str | Path) -> Path:
    project_root = Path(test_root).expanduser().resolve()
    if not project_root.is_dir():
        raise GraphtecPathError(f"The test folder does not exist: {project_root}")
    return project_root


def _load(test_root: str | Path, relative_path: str) -> tuple[Path, Path, GraphtecAcquisition]:
    project_root = _project_root(test_root)
    file_path = resolve_graphtec_file(project_root, relative_path)
    return project_root, file_path, read_graphtec_file(file_path)


def _series_results(acquisition: GraphtecAcquisition) -> list[GraphtecSeriesResult]:
    return [
        GraphtecSeriesResult(
            id=s.id, label=s.label, unit=s.unit, axis=s.axis,
            default_selected=s.default_selected,
        )
        for s in available_series(acquisition)
    ]


def _record_result(record) -> GraphtecRecordResult:
    return GraphtecRecordResult(**{
        name: getattr(record, name)
        for name in GraphtecRecordResult.model_fields
    })


def _chart_data(acquisition: GraphtecAcquisition) -> GraphtecChartData:
    records = acquisition.records
    truncated = len(records) > MAX_CHART_DATA_POINTS
    if truncated:
        last = len(records) - 1
        indexes = sorted({
            round(i * last / (MAX_CHART_DATA_POINTS - 1))
            for i in range(MAX_CHART_DATA_POINTS)
        })
        records = [records[i] for i in indexes]
    return GraphtecChartData(
        elapsed_time_seconds=[r.elapsed_time_seconds for r in records],
        voltage_kv=[r.voltage_value for r in records],
        measurement=[r.normalized_value for r in records],
        measurement_operator=[r.measurement_operator for r in records],
        status=[r.status for r in records],
        phase=[r.phase for r in records],
        truncated=truncated,
    )


def inspect_project_graphtec(
    test_root: str | Path,
    relative_path: str,
) -> GraphtecInspectionResponse:
    """Read, validate and summarize one Graphtec file."""
    try:
        project_root, file_path, acquisition = _load(test_root, relative_path)
        records = acquisition.records
        measurement = acquisition.measurement_quantity
        return GraphtecInspectionResponse(
            success=True,
            test_root=str(project_root),
            source=GRAPHTEC_SOURCE,
            format=acquisition.format_id,
            format_label=acquisition.format_label,
            # The name is returned for display and traceability only.
            file_name=file_path.name,
            relative_path=relative_to_test_root(project_root, file_path),
            records_count=len(records),
            channels=acquisition.ordered_unique("channel"),
            test_types=acquisition.ordered_unique("test_type"),
            statuses=acquisition.ordered_unique("status"),
            phases=acquisition.ordered_unique("phase"),
            phase_segments=[
                GraphtecPhaseSegmentResult(**segment.__dict__)
                for segment in acquisition.phase_segments
            ],
            final_result=acquisition.final_result,
            available_series=_series_results(acquisition),
            original_units={
                "voltage": acquisition.ordered_unique("voltage_unit"),
                measurement: acquisition.ordered_unique("measurement_unit"),
            },
            normalized_units={
                "voltage": "kV",
                measurement: acquisition.normalized_measurement_unit,
                X_AXIS_FIELD: X_AXIS_UNIT,
            },
            elapsed_time_start=acquisition.elapsed_time_start,
            elapsed_time_end=acquisition.elapsed_time_end,
            duration_seconds=round(
                acquisition.elapsed_time_end - acquisition.elapsed_time_start, 6
            ),
            limited_values_count=sum(r.is_limited for r in records),
            default_title=default_title(acquisition),
            preview_records=[_record_result(r) for r in records[:MAX_PREVIEW_RECORDS]],
            preview_truncated=len(records) > MAX_PREVIEW_RECORDS,
            chart_data=_chart_data(acquisition),
            warnings=list(acquisition.warnings),
            errors=[],
        )
    except Exception as error:
        raise _service_error(test_root, error) from error


def _chart_config(settings: GraphtecChartSettings) -> GraphtecChartConfig:
    return GraphtecChartConfig(
        series=tuple(settings.series),
        title=settings.title,
        show_legend=settings.show_legend,
        show_phase_separators=settings.show_phase_separators,
        time_min=settings.time_min,
        time_max=settings.time_max,
    )


def _render(
    test_root: str | Path,
    relative_path: str,
    settings: GraphtecChartSettings,
) -> tuple[Path, Path, GraphtecAcquisition, GraphtecChartRender]:
    project_root, file_path, acquisition = _load(test_root, relative_path)
    render = render_graphtec_chart(acquisition, _chart_config(settings))
    return project_root, file_path, acquisition, render


def preview_project_graphtec_chart(
    test_root: str | Path,
    relative_path: str,
    settings: GraphtecChartSettings,
) -> GraphtecChartPreviewResponse:
    """Render a chart preview. Nothing is written to disk."""
    try:
        project_root, file_path, acquisition, render = _render(
            test_root, relative_path, settings
        )
        encoded = base64.b64encode(render.png).decode("ascii")
        return GraphtecChartPreviewResponse(
            success=True,
            test_root=str(project_root),
            relative_path=relative_to_test_root(project_root, file_path),
            image_base64=f"data:image/png;base64,{encoded}",
            width=render.width,
            height=render.height,
            title=render.title,
            x_axis_label=f"{X_AXIS_LABEL} [{X_AXIS_UNIT}]",
            series=[
                GraphtecSeriesResult(id=s.id, label=s.label, unit=s.unit, axis=s.axis)
                for s in render.series
            ],
            axes=[
                GraphtecChartAxis(position=a.position, label=a.label, series=list(a.series))
                for a in render.axes
            ],
            time_start=render.time_start,
            time_end=render.time_end,
            full_range=render.full_range,
            records_plotted=render.records_plotted,
            limited_points=render.limited_points,
            result_points=render.result_points,
            phase_markers=[
                GraphtecPhaseMarker(phase=m.phase, elapsed_time_seconds=m.elapsed_time_seconds)
                for m in render.phase_markers
            ],
            notes=render.notes,
            errors=[],
        )
    except Exception as error:
        raise _service_error(test_root, error) from error


def _chart_metadata(
    chart_path: Path,
    project_root: Path,
    file_path: Path,
    acquisition: GraphtecAcquisition,
    render: GraphtecChartRender,
    settings: GraphtecChartSettings,
) -> dict:
    content = file_path.read_bytes()
    return {
        "schema_version": METADATA_SCHEMA_VERSION,
        "source": GRAPHTEC_SOURCE,
        "format": acquisition.format_id,
        "chart_name": chart_path.name,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_file": {
            "relative_path": relative_to_test_root(project_root, file_path),
            "size": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        },
        "test_type": acquisition.test_type,
        "channel": acquisition.channel,
        "final_result": acquisition.final_result,
        "title": render.title,
        "x_axis": {"field": X_AXIS_FIELD, "label": X_AXIS_LABEL, "unit": X_AXIS_UNIT},
        "series": [
            {"id": s.id, "label": s.label, "unit": s.unit, "axis": s.axis}
            for s in render.series
        ],
        "units": {s.id: s.unit for s in render.series} | {X_AXIS_FIELD: X_AXIS_UNIT},
        "time_range": {
            "start": render.time_start,
            "end": render.time_end,
            "full_range": render.full_range,
            "requested_min": settings.time_min,
            "requested_max": settings.time_max,
        },
        "show_legend": settings.show_legend,
        "show_phase_separators": settings.show_phase_separators,
        "records_plotted": render.records_plotted,
        "limited_points": render.limited_points,
    }


def save_project_graphtec_chart(
    test_root: str | Path,
    relative_path: str,
    settings: GraphtecChartSettings,
) -> GraphtecChartSaveResponse:
    """Render the chart on the server and save it with a generated name."""
    try:
        project_root, file_path, acquisition, render = _render(
            test_root, relative_path, settings
        )
        output_directory = prepare_rendered_assets_directory(project_root)

        def companions(chart_path: Path):
            metadata = _chart_metadata(
                chart_path, project_root, file_path, acquisition, render, settings
            )
            yield (
                metadata_path_for(chart_path),
                json.dumps(metadata, indent=2, ensure_ascii=False).encode("utf-8"),
            )

        chart_path = write_new_chart(
            output_directory,
            CHART_PREFIX,
            render.png,
            companions=companions,
            companion_suffixes=(METADATA_SUFFIX,),
        )
        return GraphtecChartSaveResponse(
            success=True,
            test_root=str(project_root),
            chart_name=chart_path.name,
            chart_path=str(chart_path.resolve()),
            relative_path=relative_asset_path(chart_path.name),
            metadata_name=metadata_path_for(chart_path).name,
            errors=[],
            **inventory_fields(project_root),
        )
    except Exception as error:
        raise _service_error(test_root, error) from error
