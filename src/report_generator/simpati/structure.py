"""Structural detection of a decoded SIMPATI export.

A SIMPATI ``.xNN`` export is a ``;`` delimited text with:

1. An optional preamble (device, program, start and stop lines).
2. A header row with one name per column. The first column is the
   timestamp column and its name is usually empty.
3. A units row right below the header, with one ``[unit]`` per column.
4. Records whose first field is a ``dd.mm.yyyy HH:MM:SS`` timestamp.

Nothing here depends on a particular channel name or on the extension
number: the same rules apply to every acquisition.
"""

from __future__ import annotations

import csv
import re
from typing import Iterable, Sequence

from .models import (
    FIELD_SEPARATOR,
    SimpatiFormatError,
    SimpatiHeaderField,
    SimpatiStructure,
)

#: Records inspected to validate a candidate structure.
VALIDATION_SAMPLE_SIZE = 50

#: Minimum share of non-empty unit fields written as ``[unit]``.
UNITS_ROW_MIN_RATIO = 0.8

_TIMESTAMP_PATTERN = re.compile(
    r"^\d{1,2}\.\d{1,2}\.\d{4} \d{1,2}:\d{2}:\d{2}$"
)
_UNIT_PATTERN = re.compile(r"^\[[^\[\]]*\]$")
_NUMBER_PATTERN = re.compile(r"^[+-]?(\d+([.,]\d*)?|[.,]\d+)([eE][+-]?\d+)?$")


def split_simpati_line(line: str) -> list[str]:
    """Split one line on ``;`` honouring double quotes."""
    return next(csv.reader([line], delimiter=FIELD_SEPARATOR, quotechar='"'))


def split_simpati_lines(lines: Iterable[str]) -> list[list[str]]:
    """Split many lines at once (faster than one reader per line)."""
    return list(csv.reader(lines, delimiter=FIELD_SEPARATOR, quotechar='"'))


def trim_trailing_empty(fields: Sequence[str]) -> list[str]:
    """Remove the empty fields produced by a trailing ``;``."""
    trimmed = list(fields)
    while trimmed and not trimmed[-1].strip():
        trimmed.pop()
    return trimmed


def is_timestamp_text(value: str) -> bool:
    """Return whether ``value`` has the SIMPATI timestamp shape."""
    return bool(_TIMESTAMP_PATTERN.match(value.strip()))


def is_number_text(value: str) -> bool:
    """Return whether ``value`` is a number, accepting a decimal comma."""
    return bool(_NUMBER_PATTERN.match(value.strip()))


def _is_units_row(fields: Sequence[str]) -> bool:
    values = [field.strip() for field in fields[1:] if field.strip()]
    if not values:
        return False
    matches = sum(1 for value in values if _UNIT_PATTERN.match(value))
    return matches / len(values) >= UNITS_ROW_MIN_RATIO


def _is_header_row(fields: Sequence[str]) -> bool:
    channel_names = [field.strip() for field in fields[1:] if field.strip()]
    if not channel_names or is_timestamp_text(fields[0]):
        return False
    if _is_units_row(fields):
        return False
    # A header names channels; it is not a row of numbers.
    numeric = sum(1 for name in channel_names if is_number_text(name))
    return numeric < len(channel_names) / 2


def _parse_preamble(lines: Sequence[str]) -> dict[str, str]:
    """Extract device, program and start/stop information when present."""
    preamble: dict[str, str] = {}
    for line in lines:
        fields = [field.strip() for field in split_simpati_line(line)] if line.strip() else []
        if not fields:
            continue
        key = fields[0].rstrip(":").casefold()
        if key in {"start", "stop"} and len(fields) >= 3:
            preamble[key] = f"{fields[1]} {fields[2]}".strip()
            if len(fields) >= 4 and fields[3]:
                preamble[f"{key}_user"] = fields[3]
            continue
        if "device" not in preamble and fields[0]:
            preamble["device"] = fields[0].rstrip("~").strip()
            for value in fields[1:]:
                if value.casefold().startswith("progr"):
                    program = value.split(":", 1)[1].strip() if ":" in value else ""
                    if program and set(program) != {"-"}:
                        preamble["program"] = program
    return preamble


def _validate_records(
    lines: Sequence[str],
    first_data_row: int,
    channel_count: int,
) -> None:
    """Check a sample of records against the header.

    Raises:
        SimpatiFormatError: when no record is consistent with the header.
    """
    inspected = 0
    consistent = 0
    numeric_values = 0
    for line in lines[first_data_row:]:
        if not line.strip():
            continue
        fields = split_simpati_line(line)
        if not is_timestamp_text(fields[0]):
            continue
        inspected += 1
        values = trim_trailing_empty(fields[1:])
        if 0 < len(values) <= channel_count:
            consistent += 1
            numeric_values += sum(1 for value in values if is_number_text(value))
        if inspected >= VALIDATION_SAMPLE_SIZE:
            break

    if inspected == 0:
        raise SimpatiFormatError(
            "No record with a valid timestamp follows the units row."
        )
    if consistent == 0:
        raise SimpatiFormatError(
            "The records do not match the number of channels of the header."
        )
    if numeric_values == 0:
        raise SimpatiFormatError("The records do not contain numeric values.")


def detect_structure(lines: Sequence[str]) -> SimpatiStructure:
    """Locate the header, units and first record rows of an export.

    Every candidate header (a ``;`` row naming channels followed by a
    ``[unit]`` row) is validated against the records below it; the first
    consistent candidate wins.

    Raises:
        SimpatiFormatError: when no recognizable SIMPATI structure exists.
    """
    last_error: SimpatiFormatError | None = None

    for row, line in enumerate(lines[:-1]):
        if FIELD_SEPARATOR not in line:
            continue
        header = split_simpati_line(line)
        if not _is_header_row(header):
            continue
        units_line = lines[row + 1]
        if FIELD_SEPARATOR not in units_line:
            continue
        units = split_simpati_line(units_line)
        if not _is_units_row(units):
            continue

        trimmed_header = trim_trailing_empty(header)
        trimmed_units = trim_trailing_empty(units)
        column_count = max(len(trimmed_header), len(trimmed_units))
        if column_count < 2:
            continue

        fields = tuple(
            SimpatiHeaderField(
                position=position,
                raw_name=header[position] if position < len(header) else "",
                raw_unit=units[position] if position < len(units) else "",
            )
            for position in range(1, column_count)
        )

        try:
            _validate_records(lines, row + 2, len(fields))
        except SimpatiFormatError as error:
            last_error = error
            continue

        return SimpatiStructure(
            header_row=row,
            units_row=row + 1,
            first_data_row=row + 2,
            fields=fields,
            preamble=_parse_preamble(lines[:row]),
        )

    if last_error is not None:
        raise last_error
    raise SimpatiFormatError(
        "No SIMPATI header followed by a units row was found."
    )
