"""Construction of the DataFrame of a SIMPATI acquisition.

The parser is purely structural: it keeps every channel, known or not,
with the name read from the header and the unit read from the units row.
The semantic interpretation of the channels lives in :mod:`.channels`.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Sequence

import pandas as pd

from .decoding import decode_simpati_bytes
from .files import acquisition_index
from .models import (
    TIMESTAMP_COLUMN,
    TIMESTAMP_FORMAT,
    SimpatiAcquisition,
    SimpatiFileNotFoundError,
    SimpatiFormatError,
    SimpatiHeaderField,
    SimpatiStructure,
)
from .structure import is_timestamp_text, split_simpati_lines, trim_trailing_empty

#: Rejected record messages kept in the result (the count is always exact).
MAX_REPORTED_REJECTED_ROWS = 20


def normalize_unit(raw_unit: str) -> str:
    """``"[°C   ]"`` -> ``"°C"``; ``"[]"`` -> ``""``."""
    unit = raw_unit.strip()
    if unit.startswith("[") and unit.endswith("]"):
        unit = unit[1:-1]
    return " ".join(unit.split())


def normalize_channel_name(
    raw_name: str,
    position: int,
    occurrences: dict[str, int],
) -> str:
    """Collapse spaces and make the name unique in a stable way.

    Empty names become ``Unnamed_NN`` (``NN`` = column position). Repeated
    names get ``_2``, ``_3``... in column order.
    """
    channel_name = " ".join(raw_name.strip().split())
    if not channel_name:
        channel_name = f"Unnamed_{position:02d}"

    occurrences[channel_name] = occurrences.get(channel_name, 0) + 1
    occurrence = occurrences[channel_name]
    return channel_name if occurrence == 1 else f"{channel_name}_{occurrence}"


def build_column_names(fields: Sequence[SimpatiHeaderField]) -> list[str]:
    """Return ``Timestamp`` followed by one unique name per channel.

    The column name is ``"<name> [<unit>]"`` when the unit is known.
    """
    occurrences: dict[str, int] = {TIMESTAMP_COLUMN: 1}
    column_names = [TIMESTAMP_COLUMN]
    for field in fields:
        name = normalize_channel_name(field.raw_name, field.position, occurrences)
        unit = normalize_unit(field.raw_unit)
        column_names.append(f"{name} [{unit}]" if unit else name)
    return column_names


def _collect_records(
    lines: Sequence[str],
    structure: SimpatiStructure,
) -> tuple[list[list[str]], list[str], int, int]:
    """Return aligned records, rejected-row messages and counters.

    - Trailing empty fields are ignored.
    - Missing trailing fields are filled with empty values: the existing
      values keep their position, so nothing moves to another column.
    - A record with more values than channels is rejected, never truncated.
    """
    channel_count = structure.channel_count
    records: list[list[str]] = []
    rejected: list[str] = []
    rejected_count = 0
    skipped = 0

    data_lines = lines[structure.first_data_row:]
    for offset, fields in enumerate(split_simpati_lines(data_lines)):
        if not fields or not any(field.strip() for field in fields):
            continue
        line_number = structure.first_data_row + offset + 1
        timestamp = fields[0].strip()
        if not is_timestamp_text(timestamp):
            skipped += 1
            continue
        values = trim_trailing_empty(fields[1:])
        if len(values) > channel_count:
            rejected_count += 1
            if len(rejected) < MAX_REPORTED_REJECTED_ROWS:
                rejected.append(
                    f"Line {line_number}: {len(values)} values for "
                    f"{channel_count} channels."
                )
            continue
        values.extend([""] * (channel_count - len(values)))
        records.append([timestamp, *values])

    return records, rejected, rejected_count, skipped


def _records_dataframe(
    records: list[list[str]],
    column_names: list[str],
) -> pd.DataFrame:
    """Build the DataFrame with numeric channels (decimal comma accepted).

    The aligned records are handed to the C CSV reader, which converts
    decimal commas much faster than per-column string replacements.
    Values that are not numbers become ``NaN``.
    """
    buffer = io.StringIO()
    csv.writer(buffer, delimiter=";", lineterminator="\n").writerows(records)
    buffer.seek(0)
    dataframe = pd.read_csv(
        buffer,
        sep=";",
        header=None,
        names=range(len(column_names)),
        dtype={0: str},
        decimal=",",
        skipinitialspace=True,
        keep_default_na=False,
        na_values=[""],
        quotechar='"',
        engine="c",
    )
    dataframe.columns = column_names
    for column_name in column_names[1:]:
        if not pd.api.types.is_numeric_dtype(dataframe[column_name]):
            cleaned = (
                dataframe[column_name]
                .astype(str)
                .str.strip()
                .str.replace(",", ".", regex=False)
            )
            dataframe[column_name] = pd.to_numeric(cleaned, errors="coerce")
        else:
            dataframe[column_name] = dataframe[column_name].astype(float)
    return dataframe


def parse_simpati_content(
    raw_data: bytes,
    *,
    source_file: str | Path = "<memory>",
    index: int | None = None,
) -> SimpatiAcquisition:
    """Parse the bytes of a SIMPATI export.

    Raises:
        SimpatiDecodingError: when no encoding yields a SIMPATI structure.
        SimpatiFormatError: when no valid record remains.
    """
    lines, encoding, structure = decode_simpati_bytes(raw_data)
    column_names = build_column_names(structure.fields)
    records, rejected, rejected_count, skipped = _collect_records(lines, structure)

    dataframe = _records_dataframe(records, column_names)
    timestamps = pd.to_datetime(
        dataframe[TIMESTAMP_COLUMN].str.strip(),
        format=TIMESTAMP_FORMAT,
        errors="coerce",
    )
    invalid_dates = int(timestamps.isna().sum())
    if invalid_dates:
        rejected_count += invalid_dates
        for value in dataframe.loc[timestamps.isna(), TIMESTAMP_COLUMN].head(
            max(0, MAX_REPORTED_REJECTED_ROWS - len(rejected))
        ):
            rejected.append(f"Invalid timestamp: {value}")
    dataframe[TIMESTAMP_COLUMN] = timestamps

    dataframe = dataframe.dropna(subset=[TIMESTAMP_COLUMN])
    # Stable sort: equal timestamps keep their file order, so keeping the
    # last occurrence is deterministic.
    dataframe = dataframe.sort_values(TIMESTAMP_COLUMN, kind="mergesort")
    before = len(dataframe)
    dataframe = dataframe.drop_duplicates(subset=[TIMESTAMP_COLUMN], keep="last")
    duplicates = before - len(dataframe)
    dataframe = dataframe.reset_index(drop=True)

    if dataframe.empty:
        raise SimpatiFormatError(
            "The SIMPATI acquisition does not contain valid timestamped records."
        )

    source_path = Path(source_file)
    dataframe.attrs["source_file"] = str(source_path)
    dataframe.attrs["encoding"] = encoding
    dataframe.attrs["acquisition_index"] = index
    dataframe.attrs["rejected_rows"] = rejected_count
    dataframe.attrs["preamble"] = dict(structure.preamble)

    acquisition = SimpatiAcquisition(
        source_file=source_path,
        encoding=encoding,
        index=index,
        dataframe=dataframe,
        structure=structure,
        rejected_rows=rejected,
        rejected_count=rejected_count,
        skipped_rows=skipped,
        duplicate_timestamps=duplicates,
    )
    return acquisition


def read_simpati_acquisition(file_path: str | Path) -> SimpatiAcquisition:
    """Read and parse one ``.xNN`` file.

    The extension only provides the acquisition index; the content alone
    decides whether the file is a valid SIMPATI acquisition.

    Raises:
        SimpatiFileNotFoundError: when the file does not exist.
        SimpatiDecodingError / SimpatiFormatError: invalid content.
        OSError: when the file cannot be read.
    """
    path = Path(file_path).expanduser().resolve()
    if not path.is_file():
        raise SimpatiFileNotFoundError(f"The SIMPATI file does not exist: {path}")
    return parse_simpati_content(
        path.read_bytes(),
        source_file=path,
        index=acquisition_index(path.name),
    )


def read_simpati(file_path: str | Path) -> pd.DataFrame:
    """Return only the DataFrame of an acquisition (metadata in ``attrs``)."""
    return read_simpati_acquisition(file_path).dataframe
