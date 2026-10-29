import base64
import binascii
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pandas import isna
from PIL import UnidentifiedImageError

from src.report_generator.assets.simpati_extractor import (
    OUTPUT_FILE_PREFIX,
    SimpatiError,
    SimpatiFileNotFoundError,
    SimpatiFormatError,
    find_simpati_file,
    get_temperature_channels,
    prepare_rendered_assets_directory,
    read_simpati,
)
from src.report_generator.rendered_assets import (
    METADATA_SUFFIX,
    metadata_path_for,
    relative_asset_path,
    validate_png_bytes,
    write_new_chart,
)

from ..models.common import ApiError
from ..models.simpati_inspection import (
    SimpatiChartSaveResponse,
    SimpatiInspectionResponse,
    SimpatiPreviewChannel,
)
from .rendered_assets import inventory_fields


MAX_PREVIEW_POINTS = 1200


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


def _decode_png(image_base64: str) -> bytes:
    encoded_data = image_base64.strip()
    data_url_prefix = "data:image/png;base64,"

    if encoded_data.startswith(data_url_prefix):
        encoded_data = encoded_data[len(data_url_prefix):]

    image_bytes = base64.b64decode(encoded_data, validate=True)
    return validate_png_bytes(image_bytes)


SIMPATI_SOURCE = "simpati"
METADATA_SCHEMA_VERSION = 1


def _chart_metadata(chart_path: Path, image_bytes: bytes) -> dict:
    """Companion metadata of a saved SIMPATI chart (origin is informative)."""
    return {
        "schema_version": METADATA_SCHEMA_VERSION,
        "source": SIMPATI_SOURCE,
        "chart_name": chart_path.name,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "size": len(image_bytes),
    }


def save_project_simpati_chart(
    test_root: str | Path,
    image_base64: str,
) -> SimpatiChartSaveResponse:
    """
    Save a PNG chart in 04_Report/_RenderedAssets.

    The chart is written with a generated, non-overwriting name and a JSON
    metadata file that records its origin. From then on it is a generic
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

        image_bytes = _decode_png(image_base64)
        output_directory = prepare_rendered_assets_directory(
            project_root
        )

        def companions(chart_path: Path):
            yield (
                metadata_path_for(chart_path),
                json.dumps(
                    _chart_metadata(chart_path, image_bytes),
                    indent=2,
                    ensure_ascii=False,
                ).encode("utf-8"),
            )

        output_path = write_new_chart(
            output_directory,
            OUTPUT_FILE_PREFIX,
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
        errors=[],
        **inventory,
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
