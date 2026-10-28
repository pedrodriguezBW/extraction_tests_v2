"""Parser for the tab-separated Graphtec TXT format.

The format has no header. Every non-empty line contains exactly six
tab-separated fields::

    channel  test type  status  voltage  measurement  phase=time

    1	DCW	TEST	2.149kV	002.5 uA	T=000.4s
    1	IR	TEST	0.958kV	>50Gohm	D=000.4s
    1	IR	PASS	0.999kV	8.794Gohm	D=005.0s

The phase letters (I, R, T, D) are kept as they appear in the file; no
functional meaning is attached to them.
"""

from __future__ import annotations

import re

from .models import (
    MEASUREMENT_QUANTITIES,
    STATUS_PASS,
    STATUS_TEST,
    TEST_TYPE_DCW,
    TEST_TYPE_IR,
    GraphtecAcquisition,
    GraphtecFormatError,
    GraphtecRecord,
)
from .timeline import compute_elapsed_times

FORMAT_ID = "graphtec_txt_tabulated"
FORMAT_LABEL = "Graphtec TXT (tab-separated)"

#: File extensions accepted for this format.
SUPPORTED_EXTENSIONS = frozenset({".txt"})

FIELD_COUNT = 6
SUPPORTED_TEST_TYPES = (TEST_TYPE_DCW, TEST_TYPE_IR)
SUPPORTED_STATUSES = (STATUS_TEST, STATUS_PASS)
SUPPORTED_PHASES = ("I", "R", "T", "D")
SUPPORTED_VOLTAGE_UNITS = ("kV",)

#: Accepted measurement units per test type and factor to the normalized
#: unit. Units are case-sensitive: ``Mohm`` is not ``mohm``.
MEASUREMENT_UNITS = {
    TEST_TYPE_DCW: ({"uA": 1.0}, "uA"),
    TEST_TYPE_IR: ({"Mohm": 1.0, "Gohm": 1000.0}, "Mohm"),
}

#: Maximum number of line issues reported in one error.
MAX_REPORTED_ISSUES = 50

_NUMBER = r"\d+(?:\.\d+)?"
_VOLTAGE_PATTERN = re.compile(rf"^({_NUMBER})\s*([A-Za-z]+)$")
_MEASUREMENT_PATTERN = re.compile(rf"^([<>])?\s*({_NUMBER})\s*([A-Za-z]+)$")
_PHASE_PATTERN = re.compile(rf"^([A-Za-z])=({_NUMBER})s$")


def _content_lines(text: str) -> list[tuple[int, str]]:
    """Return ``(line number, line)`` pairs, skipping fully empty lines."""
    lines: list[tuple[int, str]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if line.strip():
            lines.append((number, line))
    return lines


def matches(text: str) -> bool:
    """Whether the content looks like this format.

    The first non-empty line must have exactly six tab-separated fields.
    Every line is then fully validated by :func:`parse`.
    """
    lines = _content_lines(text)
    if not lines:
        return False
    return len(lines[0][1].split("\t")) == FIELD_COUNT


def _parse_line(number: int, line: str) -> GraphtecRecord:
    fields = [value.strip() for value in line.split("\t")]
    if len(fields) != FIELD_COUNT:
        raise ValueError(
            f"expected {FIELD_COUNT} tab-separated fields, found {len(fields)}"
        )
    channel_text, test_type, status, voltage, measurement, phase_text = fields

    if not re.fullmatch(r"\d+", channel_text):
        raise ValueError(f"invalid channel '{channel_text}'")
    channel = int(channel_text)

    if test_type not in SUPPORTED_TEST_TYPES:
        raise ValueError(
            f"unsupported test type '{test_type}' "
            f"(supported: {', '.join(SUPPORTED_TEST_TYPES)})"
        )
    if status not in SUPPORTED_STATUSES:
        raise ValueError(
            f"unsupported status '{status}' "
            f"(supported: {', '.join(SUPPORTED_STATUSES)})"
        )

    voltage_match = _VOLTAGE_PATTERN.match(voltage)
    if not voltage_match:
        raise ValueError(f"invalid voltage '{voltage}'")
    voltage_unit = voltage_match.group(2)
    if voltage_unit not in SUPPORTED_VOLTAGE_UNITS:
        raise ValueError(f"unsupported voltage unit '{voltage_unit}'")

    measurement_match = _MEASUREMENT_PATTERN.match(measurement)
    if not measurement_match:
        raise ValueError(f"invalid measurement '{measurement}'")
    operator, value_text, unit = measurement_match.groups()
    factors, normalized_unit = MEASUREMENT_UNITS[test_type]
    if unit not in factors:
        raise ValueError(
            f"unsupported unit '{unit}' for {test_type} "
            f"(supported: {', '.join(factors)})"
        )
    measurement_value = float(value_text)

    phase_match = _PHASE_PATTERN.match(phase_text)
    if not phase_match:
        raise ValueError(
            f"invalid phase field '{phase_text}' (expected LETTER=value s)"
        )
    phase = phase_match.group(1)
    if phase not in SUPPORTED_PHASES:
        raise ValueError(
            f"unsupported phase '{phase}' "
            f"(supported: {', '.join(SUPPORTED_PHASES)})"
        )

    return GraphtecRecord(
        line_number=number,
        channel=channel,
        test_type=test_type,
        status=status,
        raw_voltage=voltage,
        voltage_value=float(voltage_match.group(1)),
        voltage_unit=voltage_unit,
        raw_measurement=measurement,
        measurement_operator=operator,
        measurement_value=measurement_value,
        measurement_unit=unit,
        measurement_quantity=MEASUREMENT_QUANTITIES[test_type],
        normalized_value=round(measurement_value * factors[unit], 9),
        normalized_unit=normalized_unit,
        phase=phase,
        phase_time_seconds=float(phase_match.group(2)),
    )


def _consistency_issues(records: list[GraphtecRecord]) -> list[str]:
    issues: list[str] = []
    first = records[0]
    for record in records[1:]:
        if record.test_type != first.test_type:
            issues.append(
                f"Line {record.line_number}: test type {record.test_type} "
                f"does not match {first.test_type} from line "
                f"{first.line_number}. One file must contain one test type."
            )
        if record.channel != first.channel:
            issues.append(
                f"Line {record.line_number}: channel {record.channel} does "
                f"not match channel {first.channel} from line "
                f"{first.line_number}. Several channels in one file are not "
                "supported yet."
            )
    return issues


def _result_warnings(records: list[GraphtecRecord]) -> list[str]:
    warnings: list[str] = []
    result_lines = [r.line_number for r in records if r.status != STATUS_TEST]
    if not result_lines:
        warnings.append("No result record (PASS) was found in the file.")
    elif result_lines[-1] != records[-1].line_number or len(result_lines) > 1:
        early = [n for n in result_lines if n != records[-1].line_number]
        warnings.append(
            "Result records were found before the last line: lines "
            + ", ".join(str(n) for n in early)
            + "."
        )
    return warnings


def parse(text: str) -> GraphtecAcquisition:
    """Parse and validate the whole content.

    Raises:
        GraphtecFormatError: with one message per invalid line.
    """
    lines = _content_lines(text)
    if not lines:
        raise GraphtecFormatError("The Graphtec file is empty.")

    records: list[GraphtecRecord] = []
    issues: list[str] = []
    for number, line in lines:
        try:
            records.append(_parse_line(number, line))
        except ValueError as error:
            issues.append(f"Line {number}: {error}.")

    if not issues:
        issues = _consistency_issues(records)
    if issues:
        shown = issues[:MAX_REPORTED_ISSUES]
        if len(issues) > len(shown):
            shown.append(
                f"{len(issues) - len(shown)} more invalid line(s) not shown."
            )
        raise GraphtecFormatError(
            f"The Graphtec file contains {len(issues)} invalid line(s).",
            shown,
        )

    records = compute_elapsed_times(records)
    return GraphtecAcquisition(
        format_id=FORMAT_ID,
        format_label=FORMAT_LABEL,
        records=records,
        warnings=_result_warnings(records),
    )
