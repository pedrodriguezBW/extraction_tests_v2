"""Accumulated time for Graphtec records.

Algorithm. Each record carries ``phase_time_seconds``, a counter that restarts every
time the phase letter changes. ``elapsed_time_seconds`` places every record
on one continuous axis:

1. Records are processed in file order. The file name is never used.
2. ``offset`` starts at 0.
3. When the phase letter differs from the previous record, the last
   ``phase_time_seconds`` of the previous phase is added to ``offset``.
   The phase that ends contributes the time it reached in its last record.
4. ``elapsed_time_seconds = offset + phase_time_seconds``.
5. Inside one phase, ``phase_time_seconds`` must not decrease. A decrease is
   reported as a controlled format error with the line number, because it
   would make the elapsed time go backwards.

With non-negative phase times this produces a monotonic, non-decreasing
elapsed time. A phase letter that appears again after another phase starts
a new segment. Values are rounded to microseconds to avoid floating-point
noise such as ``4.9 + 0.1 = 5.000000000000001``.

Example::

    R=000.1s  R=004.9s | T=000.2s  T=003.0s | D=000.2s
    0.1       4.9      | 5.1       7.9      | 8.1
"""

from __future__ import annotations

from dataclasses import replace

from .models import GraphtecFormatError, GraphtecRecord

ELAPSED_TIME_DECIMALS = 6


def compute_elapsed_times(
    records: list[GraphtecRecord],
) -> list[GraphtecRecord]:
    """Return copies of ``records`` with ``elapsed_time_seconds`` set.

    Raises:
        GraphtecFormatError: when the phase time decreases inside a phase.
    """
    issues: list[str] = []
    result: list[GraphtecRecord] = []
    offset = 0.0
    previous: GraphtecRecord | None = None

    for record in records:
        if previous is not None:
            if record.phase != previous.phase:
                offset += previous.phase_time_seconds
            elif record.phase_time_seconds < previous.phase_time_seconds:
                issues.append(
                    f"Line {record.line_number}: the phase time goes back "
                    f"from {previous.phase_time_seconds:g} s to "
                    f"{record.phase_time_seconds:g} s inside phase "
                    f"{record.phase}."
                )
        elapsed = round(offset + record.phase_time_seconds, ELAPSED_TIME_DECIMALS)
        result.append(replace(record, elapsed_time_seconds=elapsed))
        previous = record

    if issues:
        raise GraphtecFormatError(
            "The phase times are not consistent.",
            issues,
        )
    return result
