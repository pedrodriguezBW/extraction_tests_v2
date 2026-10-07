import base64
import binascii
import math
from io import BytesIO
from pathlib import Path
from typing import Any

from pandas import isna
from PIL import Image, UnidentifiedImageError

from src.report_generator.assets.simpati_extractor import (
    SimpatiError,
    SimpatiFileNotFoundError,
    SimpatiFormatError,
    build_next_chart_path,
    find_simpati_file,
    get_temperature_channels,
    prepare_rendered_assets_directory,
    read_simpati,
)
from src.report_generator.paths import rendered_assets_directory
from src.report_generator.powerpoint.images import find_test_result_charts

from ..models.common import ApiError
from ..models.simpati_inspection import (
    SimpatiChartDeleteResponse,
    SimpatiChartListResponse,
    SimpatiChartSaveResponse,
    SimpatiInspectionResponse,
    SimpatiPreviewChannel,
    SimpatiSavedChart,
)


MAX_PREVIEW_POINTS = 1200
MAX_IMAGE_BYTES = 15 * 1024 * 1024
MAX_IMAGE_DIMENSION = 8000


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


class SimpatiChartManagementError(Exception):
    """Controlled saved-chart management error."""

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

    def to_list_response(self) -> SimpatiChartListResponse:
        return SimpatiChartListResponse(
            success=False,
            test_root=str(self.test_root),
            errors=[self.error],
        )

    def to_delete_response(self) -> SimpatiChartDeleteResponse:
        return SimpatiChartDeleteResponse(
            success=False,
            test_root=str(self.test_root),
            errors=[self.error],
        )


def _format_timestamp(value: Any) -> str:
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
    source_column: str,
    label: str,
    thermal: bool,
) -> SimpatiPreviewChannel:
    preview_series = dataframe.iloc[indexes][source_column]

    return SimpatiPreviewChannel(
        id=source_column,
        label=label,
        source_column=source_column,
        thermal=thermal,
        values=_numeric_values(preview_series),
    )


def _build_inspection_error(
    test_root: Path,
    error: Exception,
) -> SimpatiInspectionError:
    if isinstance(error, PermissionError):
        status_code = 403
        code = "simpati_inspection_permission_denied"
    elif isinstance(
        error,
        (
            FileNotFoundError,
            NotADirectoryError,
            SimpatiFormatError,
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

    message = str(error).strip()
    if not message:
        message = "The SIMPATI acquisition could not be inspected."

    return SimpatiInspectionError(
        test_root=test_root,
        status_code=status_code,
        error=ApiError(
            code=code,
            message=message,
            exception_type=type(error).__name__,
        ),
    )


def _build_save_error(
    test_root: Path,
    error: Exception,
) -> SimpatiChartSaveError:
    if isinstance(error, PermissionError):
        status_code = 403
        code = "simpati_chart_permission_denied"
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

    message = str(error).strip()
    if not message:
        message = "The SIMPATI chart could not be saved."

    return SimpatiChartSaveError(
        test_root=test_root,
        status_code=status_code,
        error=ApiError(
            code=code,
            message=message,
            exception_type=type(error).__name__,
        ),
    )


def _build_management_error(
    test_root: Path,
    error: Exception,
    *,
    not_found: bool = False,
) -> SimpatiChartManagementError:
    if not_found:
        status_code = 404
        code = "simpati_chart_not_found"
    elif isinstance(error, PermissionError):
        status_code = 403
        code = "simpati_chart_permission_denied"
    elif isinstance(
        error,
        (
            FileNotFoundError,
            NotADirectoryError,
            ValueError,
        ),
    ):
        status_code = 400
        code = "simpati_chart_invalid_request"
    else:
        status_code = 500
        code = "simpati_chart_management_failed"

    message = str(error).strip()
    if not message:
        message = "The saved SIMPATI charts could not be managed."

    return SimpatiChartManagementError(
        test_root=test_root,
        status_code=status_code,
        error=ApiError(
            code=code,
            message=message,
            exception_type=type(error).__name__,
        ),
    )


def _saved_charts(test_root: Path) -> list[SimpatiSavedChart]:
    assets_directory = rendered_assets_directory(test_root).resolve()
    saved_charts: list[SimpatiSavedChart] = []

    for chart_path in find_test_result_charts(test_root):
        resolved_chart_path = chart_path.resolve()
        if resolved_chart_path.parent != assets_directory:
            continue

        saved_charts.append(
            SimpatiSavedChart(
                chart_name=chart_path.name,
                chart_path=str(resolved_chart_path),
                size_bytes=chart_path.stat().st_size,
            )
        )

    return saved_charts


def list_project_simpati_charts(
    test_root: str | Path,
) -> SimpatiChartListResponse:
    """List the saved images that PowerPoint will include."""
    project_root = Path(test_root).expanduser()

    try:
        project_root = project_root.resolve()
        if not project_root.is_dir():
            raise FileNotFoundError(
                f"The test folder does not exist: {project_root}"
            )
        charts = _saved_charts(project_root)
    except Exception as error:
        raise _build_management_error(project_root, error) from error

    return SimpatiChartListResponse(
        success=True,
        test_root=str(project_root),
        charts_count=len(charts),
        charts=charts,
        errors=[],
    )


def resolve_project_simpati_chart(
    test_root: str | Path,
    chart_name: str,
) -> Path:
    """Resolve a chart only when it belongs to the discovered chart set."""
    project_root = Path(test_root).expanduser()

    try:
        project_root = project_root.resolve()
        requested_name = Path(chart_name).name

        if requested_name != chart_name:
            raise ValueError("The chart name is invalid.")

        chart_path = next(
            (
                candidate
                for candidate in find_test_result_charts(project_root)
                if candidate.name == requested_name
            ),
            None,
        )

        if chart_path is None:
            raise _build_management_error(
                project_root,
                FileNotFoundError(
                    f"The saved SIMPATI chart was not found: {requested_name}"
                ),
                not_found=True,
            )

        resolved_chart_path = chart_path.resolve()
        expected_directory = rendered_assets_directory(
            project_root
        ).resolve()
        if resolved_chart_path.parent != expected_directory:
            raise ValueError(
                "The chart path is outside 04_Report/_RenderedAssets."
            )
    except SimpatiChartManagementError:
        raise
    except Exception as error:
        raise _build_management_error(project_root, error) from error

    return resolved_chart_path


def delete_project_simpati_chart(
    test_root: str | Path,
    chart_name: str,
) -> SimpatiChartDeleteResponse:
    """Delete one chart from the same confined set used by PowerPoint."""
    project_root = Path(test_root).expanduser().resolve()

    try:
        chart_path = resolve_project_simpati_chart(
            project_root,
            chart_name,
        )
        chart_path.unlink()
        charts = _saved_charts(project_root)
    except SimpatiChartManagementError:
        raise
    except Exception as error:
        raise _build_management_error(project_root, error) from error

    return SimpatiChartDeleteResponse(
        success=True,
        test_root=str(project_root),
        deleted_chart_name=chart_name,
        charts_count=len(charts),
        charts=charts,
        errors=[],
    )


def _decode_png(image_base64: str) -> bytes:
    encoded_data = image_base64.strip()
    data_url_prefix = "data:image/png;base64,"

    if encoded_data.startswith(data_url_prefix):
        encoded_data = encoded_data[len(data_url_prefix):]

    image_bytes = base64.b64decode(encoded_data, validate=True)

    if not image_bytes:
        raise ValueError("The PNG image is empty.")

    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ValueError("The PNG image exceeds the 15 MB limit.")

    with Image.open(BytesIO(image_bytes)) as image:
        if image.format != "PNG":
            raise ValueError("The chart must be a PNG image.")
        if (
            image.width > MAX_IMAGE_DIMENSION
            or image.height > MAX_IMAGE_DIMENSION
        ):
            raise ValueError(
                "The PNG image dimensions exceed the allowed limit."
            )
        image.verify()

    return image_bytes


def save_project_simpati_chart(
    test_root: str | Path,
    image_base64: str,
) -> SimpatiChartSaveResponse:
    """
    Save a PNG chart in 04_Report/_RenderedAssets.

    PowerPoint generation discovers the saved charts there. The
    04_Report folder must already exist.
    """
    project_root = Path(test_root).expanduser()
    temporary_path: Path | None = None

    try:
        project_root = project_root.resolve()
        if not project_root.is_dir():
            raise FileNotFoundError(
                f"The test folder does not exist: {project_root}"
            )

        image_bytes = _decode_png(image_base64)
        output_directory = prepare_rendered_assets_directory(
            project_root
        )
        output_path = build_next_chart_path(output_directory)
        temporary_path = output_path.with_suffix(".tmp")
        temporary_path.write_bytes(image_bytes)
        temporary_path.replace(output_path)
        charts = _saved_charts(project_root)
    except Exception as error:
        raise _build_save_error(project_root, error) from error
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

    return SimpatiChartSaveResponse(
        success=True,
        test_root=str(project_root),
        chart_path=str(output_path.resolve()),
        chart_name=output_path.name,
        charts_count=len(charts),
        charts=charts,
        errors=[],
    )


def inspect_project_simpati(
    test_root: str | Path,
) -> SimpatiInspectionResponse:
    """Inspect optional SIMPATI data with the existing parser."""
    project_root = Path(test_root).expanduser()

    try:
        project_root = project_root.resolve()
        simpati_file = find_simpati_file(project_root)
    except SimpatiFileNotFoundError:
        return SimpatiInspectionResponse(
            success=True,
            test_root=str(project_root),
            available=False,
            errors=[],
        )
    except Exception as error:
        raise _build_inspection_error(project_root, error) from error

    try:
        dataframe = read_simpati(simpati_file)
        timestamps = dataframe["Timestamp"]
        temperature_channels = get_temperature_channels(dataframe)
        channels = [
            str(column_name)
            for column_name in dataframe.columns
            if str(column_name) != "Timestamp"
        ]
        indexes = _preview_indexes(len(dataframe))
        preview_frame = dataframe.iloc[indexes]
        preview_timestamps = [
            _format_timestamp(value)
            for value in preview_frame["Timestamp"].tolist()
        ]
        thermal_source_columns = set(temperature_channels.values())
        thermal_preview_channels = [
            _preview_channel(
                dataframe=dataframe,
                indexes=indexes,
                source_column=source_column,
                label=display_name,
                thermal=True,
            )
            for display_name, source_column
            in temperature_channels.items()
        ]
        advanced_preview_channels = [
            _preview_channel(
                dataframe=dataframe,
                indexes=indexes,
                source_column=column_name,
                label=column_name,
                thermal=False,
            )
            for column_name in channels
            if column_name not in thermal_source_columns
            and dataframe[column_name].notna().any()
        ]
        encoding_value = dataframe.attrs.get("encoding")
    except SimpatiFileNotFoundError:
        return SimpatiInspectionResponse(
            success=True,
            test_root=str(project_root),
            available=False,
            errors=[],
        )
    except Exception as error:
        raise _build_inspection_error(project_root, error) from error

    return SimpatiInspectionResponse(
        success=True,
        test_root=str(project_root),
        available=True,
        file_name=simpati_file.name,
        file_path=str(simpati_file.resolve()),
        encoding=(
            str(encoding_value)
            if encoding_value is not None
            else None
        ),
        records_count=len(dataframe),
        acquisition_start=_format_timestamp(timestamps.iloc[0]),
        acquisition_end=_format_timestamp(timestamps.iloc[-1]),
        channels=channels,
        preview_timestamps=preview_timestamps,
        thermal_channels=thermal_preview_channels,
        advanced_channels=advanced_preview_channels,
        errors=[],
    )
