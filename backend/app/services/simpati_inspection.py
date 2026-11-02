"""SIMPATI analysis and chart saving for the API.

Every ``.xNN`` acquisition of ``03_Data/01_SIMPATI`` is analyzed on its
own with the generic SIMPATI parser. The response lists all of them, in
numeric order and with their own status, and includes the preview data of
the selected acquisition for the chart editor. One incompatible file never
invalidates the others.
"""

import base64
import binascii
import json
import math
from collections import OrderedDict
from pathlib import Path
from threading import Lock
from typing import Any

from pandas import isna
from PIL import UnidentifiedImageError

from src.report_generator.rendered_assets import (
    METADATA_SUFFIX,
    metadata_path_for,
    prepare_rendered_assets_directory,
    relative_asset_path,
    validate_png_bytes,
    write_new_chart,
)
from src.report_generator.simpati import (
    STATUS_ERROR,
    STATUS_READY,
    SimpatiAcquisitionFile,
    SimpatiAnalysis,
    SimpatiChannel,
    SimpatiError,
    SimpatiFileNotFoundError,
    SimpatiPathError,
    analyze_simpati_file,
    chart_metadata,
    chart_prefix,
    discover_simpati_acquisitions,
    resolve_simpati_acquisition,
    thermal_channels,
)

from ..models.common import ApiError
from ..models.simpati_inspection import (
    SimpatiAcquisitionSummary,
    SimpatiChannelResult,
    SimpatiChartSaveResponse,
    SimpatiInspectionResponse,
    SimpatiPreviewChannel,
)
from .rendered_assets import inventory_fields


MAX_PREVIEW_POINTS = 1200

#: Analyses kept in memory, keyed by path, modification time and size.
ANALYSIS_CACHE_SIZE = 16

_analysis_cache: "OrderedDict[tuple, SimpatiAnalysis]" = OrderedDict()
_analysis_cache_lock = Lock()


class SimpatiInspectionError(Exception):
    """Controlled SIMPATI inspection error."""

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

    def to_response(self) -> SimpatiInspectionResponse:
        return SimpatiInspectionResponse(
            success=False,
            test_root=str(self.test_root),
            available=False,
            errors=[self.error],
        )


class SimpatiChartSaveError(Exception):
    """Controlled SIMPATI chart save error."""

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

    def to_response(self) -> SimpatiChartSaveResponse:
        return SimpatiChartSaveResponse(
            success=False,
            test_root=str(self.test_root),
            errors=[self.error],
        )


def _format_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return str(isoformat())
    return str(value)


def _preview_indexes(row_count: int) -> list[int]:
    if row_count <= MAX_PREVIEW_POINTS:
        return list(range(row_count))

    last_index = row_count - 1
    indexes = [
        round(position * last_index / (MAX_PREVIEW_POINTS - 1))
        for position in range(MAX_PREVIEW_POINTS)
    ]
    return list(dict.fromkeys(indexes))


def _numeric_values(series) -> list[float | None]:
    values: list[float | None] = []

    for value in series.tolist():
        if isna(value):
            values.append(None)
        else:
            numeric_value = float(value)
            values.append(
                numeric_value
                if math.isfinite(numeric_value)
                else None
            )

    return values


def _preview_channel(
    *,
    dataframe,
    indexes: list[int],
    channel: SimpatiChannel,
    thermal: bool,
) -> SimpatiPreviewChannel:
    preview_series = dataframe.iloc[indexes][channel.column]

    return SimpatiPreviewChannel(
        id=channel.column,
        label=channel.display_label if thermal else channel.column,
        source_column=channel.column,
        thermal=thermal,
        role=channel.role,
        unit=channel.unit,
        values=_numeric_values(preview_series),
    )


def _exception_error(error: BaseException, code: str, default: str) -> ApiError:
    message = str(error).strip() or default
    return ApiError(
        code=code,
        message=message,
        exception_type=type(error).__name__,
    )


def _build_inspection_error(
    test_root: Path,
    error: Exception,
) -> SimpatiInspectionError:
    if isinstance(error, PermissionError):
        status_code = 403
        code = "simpati_inspection_permission_denied"
    elif isinstance(error, SimpatiPathError):
        status_code = 400
        code = "simpati_inspection_invalid_path"
    elif isinstance(
        error,
        (
            FileNotFoundError,
            NotADirectoryError,
            SimpatiError,
            ValueError,
            TypeError,
            KeyError,
        ),
    ):
        status_code = 400
        code = "simpati_inspection_invalid_file"
    else:
        status_code = 500
        code = "simpati_inspection_failed"

    return SimpatiInspectionError(
        test_root=test_root,
        status_code=status_code,
        error=_exception_error(
            error, code, "The SIMPATI acquisitions could not be inspected."
        ),
    )


def _build_save_error(
    test_root: Path,
    error: Exception,
) -> SimpatiChartSaveError:
    if isinstance(error, PermissionError):
        status_code = 403
        code = "simpati_chart_permission_denied"
    elif isinstance(error, (SimpatiPathError, SimpatiFileNotFoundError)):
        status_code = 400
        code = "simpati_chart_invalid_source"
    elif isinstance(
        error,
        (
            FileNotFoundError,
            NotADirectoryError,
            ValueError,
            binascii.Error,
            UnidentifiedImageError,
            OSError,
            SyntaxError,
        ),
    ):
        status_code = 400
        code = "simpati_chart_invalid_image"
    else:
        status_code = 500
        code = "simpati_chart_save_failed"

    return SimpatiChartSaveError(
        test_root=test_root,
        status_code=status_code,
        error=_exception_error(error, code, "The SIMPATI chart could not be saved."),
    )


def _decode_png(image_base64: str) -> bytes:
    encoded_data = image_base64.strip()
    data_url_prefix = "data:image/png;base64,"

    if encoded_data.startswith(data_url_prefix):
        encoded_data = encoded_data[len(data_url_prefix):]

    image_bytes = base64.b64decode(encoded_data, validate=True)
    return validate_png_bytes(image_bytes)


def clear_analysis_cache() -> None:
    """Forget the cached analyses (used by tests)."""
    with _analysis_cache_lock:
        _analysis_cache.clear()


def _analyze(acquisition_file: SimpatiAcquisitionFile) -> SimpatiAnalysis:
    """Analyze an acquisition, reusing the result while the file is unchanged."""
    try:
        stat = acquisition_file.path.stat()
        key = (str(acquisition_file.path), stat.st_mtime_ns, stat.st_size)
    except OSError:
        return analyze_simpati_file(acquisition_file)

    with _analysis_cache_lock:
        cached = _analysis_cache.get(key)
        if cached is not None:
            _analysis_cache.move_to_end(key)
            return SimpatiAnalysis(
                file=acquisition_file,
                status=cached.status,
                acquisition=cached.acquisition,
                channels=cached.channels,
                error=cached.error,
            )

    analysis = analyze_simpati_file(acquisition_file)
    with _analysis_cache_lock:
        _analysis_cache[key] = analysis
        while len(_analysis_cache) > ANALYSIS_CACHE_SIZE:
            _analysis_cache.popitem(last=False)
    return analysis


def _channel_result(channel: SimpatiChannel) -> SimpatiChannelResult:
    return SimpatiChannelResult(
        column=channel.column,
        name=channel.name,
        unit=channel.unit,
        kind=channel.kind,
        role=channel.role,
        label=channel.label,
        thermal=channel.thermal,
        has_data=channel.has_data,
    )


def _analysis_error(analysis: SimpatiAnalysis) -> ApiError | None:
    if analysis.error is None:
        return None
    code = (
        "simpati_acquisition_read_error"
        if analysis.status == STATUS_ERROR
        else "simpati_acquisition_incompatible"
    )
    message = str(analysis.error).strip() or "The acquisition could not be analyzed."
    return ApiError(
        code=code,
        message=f"{analysis.file.name}: {message}",
        exception_type=type(analysis.error).__name__,
    )


def _summary(analysis: SimpatiAnalysis) -> SimpatiAcquisitionSummary:
    acquisition_file = analysis.file
    summary = SimpatiAcquisitionSummary(
        index=acquisition_file.index,
        label=acquisition_file.label,
        file_name=acquisition_file.name,
        relative_path=acquisition_file.relative_path,
        size=acquisition_file.size,
        status=analysis.status,
        error=_analysis_error(analysis),
    )
    acquisition = analysis.acquisition
    if acquisition is None:
        return summary

    preamble = acquisition.structure.preamble
    summary.encoding = acquisition.encoding
    summary.records_count = acquisition.records_count
    summary.acquisition_start = _format_timestamp(acquisition.start)
    summary.acquisition_end = _format_timestamp(acquisition.end)
    summary.device = preamble.get("device")
    summary.program = preamble.get("program")
    summary.channels_count = len(analysis.channels)
    summary.channels = [_channel_result(channel) for channel in analysis.channels]
    summary.thermal_channels = [
        channel.display_label for channel in thermal_channels(analysis.channels)
    ]
    summary.rejected_rows = acquisition.rejected_count
    summary.rejected_rows_examples = list(acquisition.rejected_rows)
    return summary


def _select_analysis(
    analyses: list[SimpatiAnalysis],
    relative_path: str | None,
) -> SimpatiAnalysis | None:
    if relative_path is not None:
        for analysis in analyses:
            if analysis.file.relative_path == relative_path:
                return analysis
        return None
    for analysis in analyses:
        if analysis.status == STATUS_READY:
            return analysis
    for analysis in analyses:
        if analysis.processed:
            return analysis
    return analyses[0] if analyses else None


def _apply_preview(
    response: SimpatiInspectionResponse,
    analysis: SimpatiAnalysis,
) -> None:
    acquisition_file = analysis.file
    response.selected_relative_path = acquisition_file.relative_path
    response.selected_index = acquisition_file.index
    response.selected_status = analysis.status
    response.file_name = acquisition_file.name
    response.file_path = str(acquisition_file.path.resolve())

    acquisition = analysis.acquisition
    if acquisition is None:
        error = _analysis_error(analysis)
        if error is not None:
            response.errors.append(error)
        return

    dataframe = acquisition.dataframe
    indexes = _preview_indexes(len(dataframe))
    preview_frame = dataframe.iloc[indexes]
    thermal = thermal_channels(analysis.channels)
    thermal_columns = {channel.column for channel in thermal}

    response.encoding = acquisition.encoding
    response.records_count = acquisition.records_count
    response.acquisition_start = _format_timestamp(acquisition.start)
    response.acquisition_end = _format_timestamp(acquisition.end)
    response.channels = acquisition.channel_columns
    response.preview_timestamps = [
        _format_timestamp(value) or ""
        for value in preview_frame["Timestamp"].tolist()
    ]
    response.thermal_channels = [
        _preview_channel(
            dataframe=dataframe,
            indexes=indexes,
            channel=channel,
            thermal=True,
        )
        for channel in thermal
    ]
    response.advanced_channels = [
        _preview_channel(
            dataframe=dataframe,
            indexes=indexes,
            channel=channel,
            thermal=False,
        )
        for channel in analysis.channels
        if channel.column not in thermal_columns and channel.has_data
    ]


def inspect_project_simpati(
    test_root: str | Path,
    relative_path: str | None = None,
) -> SimpatiInspectionResponse:
    """Analyze every SIMPATI acquisition and preview one of them.

    ``relative_path`` selects the previewed acquisition; without it the
    first acquisition with representable thermal channels is used. A
    missing SIMPATI folder or the absence of ``.xNN`` files is not an
    error: SIMPATI is optional.
    """
    project_root = Path(test_root).expanduser()

    try:
        project_root = project_root.resolve()
        files = discover_simpati_acquisitions(project_root)
        selected_file = (
            resolve_simpati_acquisition(project_root, relative_path)
            if relative_path
            else None
        )
    except Exception as error:
        raise _build_inspection_error(project_root, error) from error

    if not files and selected_file is None:
        return SimpatiInspectionResponse(
            success=True,
            test_root=str(project_root),
            available=False,
            errors=[],
        )

    analyses = [_analyze(acquisition_file) for acquisition_file in files]
    if selected_file is not None and not any(
        analysis.file.relative_path == selected_file.relative_path
        for analysis in analyses
    ):
        analyses.append(_analyze(selected_file))
        analyses.sort(key=lambda item: (item.file.index, item.file.name.casefold()))

    response = SimpatiInspectionResponse(
        success=True,
        test_root=str(project_root),
        available=True,
        acquisitions=[_summary(analysis) for analysis in analyses],
        found_count=len(analyses),
        processed_count=sum(1 for analysis in analyses if analysis.processed),
        ready_count=sum(1 for analysis in analyses if analysis.status == STATUS_READY),
        without_thermal_count=sum(
            1 for analysis in analyses
            if analysis.processed and analysis.status != STATUS_READY
        ),
        incompatible_count=sum(1 for analysis in analyses if not analysis.processed),
        errors=[],
    )

    selected = _select_analysis(
        analyses,
        selected_file.relative_path if selected_file is not None else None,
    )
    if selected is not None:
        _apply_preview(response, selected)
    return response


def save_project_simpati_chart(
    test_root: str | Path,
    relative_path: str,
    image_base64: str,
) -> SimpatiChartSaveResponse:
    """
    Save a PNG chart of one acquisition in 04_Report/_RenderedAssets.

    The chart is written as ``chart_simpati_xNN_MM.png`` (``NN`` = index
    of the source acquisition) without overwriting anything, together
    with a JSON that records its source file. From then on it is a generic
    rendered asset: the user selects in the interface which images of
    ``_RenderedAssets`` the PowerPoint includes. The 04_Report folder must
    already exist.
    """
    project_root = Path(test_root).expanduser()

    try:
        project_root = project_root.resolve()
        if not project_root.is_dir():
            raise FileNotFoundError(
                f"The test folder does not exist: {project_root}"
            )

        acquisition_file = resolve_simpati_acquisition(project_root, relative_path)
        image_bytes = _decode_png(image_base64)
        output_directory = prepare_rendered_assets_directory(project_root)

        def companions(chart_path: Path):
            yield (
                metadata_path_for(chart_path),
                json.dumps(
                    chart_metadata(chart_path.name, len(image_bytes), acquisition_file),
                    indent=2,
                    ensure_ascii=False,
                ).encode("utf-8"),
            )

        output_path = write_new_chart(
            output_directory,
            chart_prefix(acquisition_file.index),
            image_bytes,
            companions=companions,
            companion_suffixes=(METADATA_SUFFIX,),
        )
        inventory = inventory_fields(project_root)
    except Exception as error:
        raise _build_save_error(project_root, error) from error

    return SimpatiChartSaveResponse(
        success=True,
        test_root=str(project_root),
        chart_path=str(output_path.resolve()),
        chart_name=output_path.name,
        relative_path=relative_asset_path(output_path.name),
        source_relative_path=acquisition_file.relative_path,
        acquisition_index=acquisition_file.index,
        errors=[],
        **inventory,
    )
