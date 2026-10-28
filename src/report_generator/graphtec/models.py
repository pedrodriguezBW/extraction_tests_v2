"""Normalized Graphtec data model shared by every Graphtec file format.

The data is always obtained from the file content. The file name is an
opaque identifier: it is only used to display the file and to keep
traceability, never to infer the test type, dates, channels, units, phases
or results.
"""

from __future__ import annotations

from dataclasses import dataclass, field


#: Source identifier used in API responses and saved chart metadata.
GRAPHTEC_SOURCE = "graphtec"

#: Test types supported by the first Graphtec format.
TEST_TYPE_DCW = "DCW"
TEST_TYPE_IR = "IR"

#: Record status written while the acquisition is running.
STATUS_TEST = "TEST"

#: Record status written as a result record.
STATUS_PASS = "PASS"

#: Physical quantity measured by each supported test type.
MEASUREMENT_QUANTITIES = {
    TEST_TYPE_DCW: "current",
    TEST_TYPE_IR: "resistance",
}


class GraphtecError(Exception):
    """Base class for controlled Graphtec errors."""


class GraphtecUnsupportedFormatError(GraphtecError):
    """The file does not match any supported Graphtec format."""


class GraphtecFormatError(GraphtecError):
    """The file matches a supported format but its content is invalid.

    ``issues`` contains one message per invalid line so that no invalid
    line is silently skipped.
    """

    def __init__(self, message: str, issues: list[str] | None = None):
        super().__init__(message)
        self.issues = list(issues or [message])


@dataclass(frozen=True)
class GraphtecRecord:
    """One normalized line of a Graphtec acquisition."""

    line_number: int
    channel: int
    test_type: str
    status: str
    raw_voltage: str
    voltage_value: float
    voltage_unit: str
    raw_measurement: str
    measurement_operator: str | None
    measurement_value: float
    measurement_unit: str
    measurement_quantity: str
    normalized_value: float
    normalized_unit: str
    phase: str
    phase_time_seconds: float
    elapsed_time_seconds: float = 0.0

    @property
    def is_limited(self) -> bool:
        """Whether the measurement is a bound (``>`` or ``<``), not a value."""
        return self.measurement_operator is not None


@dataclass(frozen=True)
class GraphtecPhaseSegment:
    """Consecutive records that share the same phase letter."""

    phase: str
    start_elapsed_seconds: float
    end_elapsed_seconds: float
    first_line: int
    last_line: int
    records_count: int


@dataclass(frozen=True)
class GraphtecAcquisition:
    """Validated content of one Graphtec file."""

    format_id: str
    format_label: str
    records: list[GraphtecRecord]
    warnings: list[str] = field(default_factory=list)

    @property
    def test_type(self) -> str:
        return self.records[0].test_type

    @property
    def channel(self) -> int:
        return self.records[0].channel

    @property
    def measurement_quantity(self) -> str:
        return self.records[0].measurement_quantity

    @property
    def normalized_measurement_unit(self) -> str:
        return self.records[0].normalized_unit

    @property
    def elapsed_time_start(self) -> float:
        return self.records[0].elapsed_time_seconds

    @property
    def elapsed_time_end(self) -> float:
        return self.records[-1].elapsed_time_seconds

    @property
    def final_result(self) -> str | None:
        """Status of the last result record, read from the content."""
        for record in reversed(self.records):
            if record.status != STATUS_TEST:
                return record.status
        return None

    def ordered_unique(self, attribute: str) -> list:
        values: list = []
        for record in self.records:
            value = getattr(record, attribute)
            if value not in values:
                values.append(value)
        return values

    @property
    def phase_segments(self) -> list[GraphtecPhaseSegment]:
        segments: list[GraphtecPhaseSegment] = []
        current: list[GraphtecRecord] = []
        for record in self.records:
            if current and record.phase != current[-1].phase:
                segments.append(_segment(current))
                current = []
            current.append(record)
        if current:
            segments.append(_segment(current))
        return segments


def _segment(records: list[GraphtecRecord]) -> GraphtecPhaseSegment:
    return GraphtecPhaseSegment(
        phase=records[0].phase,
        start_elapsed_seconds=records[0].elapsed_time_seconds,
        end_elapsed_seconds=records[-1].elapsed_time_seconds,
        first_line=records[0].line_number,
        last_line=records[-1].line_number,
        records_count=len(records),
    )
