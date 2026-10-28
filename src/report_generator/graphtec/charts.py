"""Chart rendering for normalized Graphtec acquisitions.

* X axis: always ``elapsed_time_seconds`` (Elapsed time [s]).
* Left Y axis: Voltage [kV].
* Right Y axis: Current [uA] for DCW or Resistance [Mohm] for IR.
  Current and resistance never share a chart. With one series selected only
  its axis is drawn.
* Limited values such as ``>50Gohm`` are drawn at their normalized
  threshold (50000 Mohm) with a different marker. They are not joined to
  the measured line and a note explains the marker.
* Result records (status other than TEST) are drawn as separate markers.
* Phase changes are shown as subtle vertical lines with the phase letter.

Rendering uses the Agg canvas directly: no window is opened and the source
file is never modified.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from io import BytesIO

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from .models import STATUS_TEST, GraphtecAcquisition, GraphtecRecord

X_AXIS_FIELD = "elapsed_time_seconds"
X_AXIS_LABEL = "Elapsed time"
X_AXIS_UNIT = "s"

MAX_TITLE_LENGTH = 200
FIGURE_SIZE_INCHES = (11.0, 5.6)
FIGURE_DPI = 150

LIMIT_NOTES = {
    ">": "Limit marker indicates a value greater than the displayed threshold.",
    "<": "Limit marker indicates a value lower than the displayed threshold.",
}

SERIES_COLORS = {
    "voltage": "#0b4b70",
    "current": "#b83b0b",
    "resistance": "#24733e",
}


class GraphtecChartConfigError(ValueError):
    """The chart configuration is not valid for the acquisition."""


@dataclass(frozen=True)
class GraphtecSeries:
    """Series that can be drawn for an acquisition."""

    id: str
    label: str
    unit: str
    axis: str
    default_selected: bool = True


@dataclass(frozen=True)
class GraphtecChartConfig:
    """User settings for one Graphtec chart."""

    series: tuple[str, ...]
    title: str
    show_legend: bool = True
    show_phase_separators: bool = True
    time_min: float | None = None
    time_max: float | None = None


@dataclass(frozen=True)
class ChartAxisInfo:
    position: str
    label: str
    series: tuple[str, ...]


@dataclass(frozen=True)
class PhaseMarker:
    phase: str
    elapsed_time_seconds: float


@dataclass
class GraphtecChartRender:
    """PNG image and a description of what was drawn."""

    png: bytes
    width: int
    height: int
    title: str
    series: list[GraphtecSeries]
    axes: list[ChartAxisInfo]
    time_start: float
    time_end: float
    full_range: bool
    records_plotted: int
    limited_points: int
    result_points: int
    phase_markers: list[PhaseMarker] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def available_series(acquisition: GraphtecAcquisition) -> list[GraphtecSeries]:
    """Voltage plus the measured quantity of the test type."""
    measurement_id = acquisition.measurement_quantity
    return [
        GraphtecSeries("voltage", "Voltage", "kV", "left"),
        GraphtecSeries(
            measurement_id,
            measurement_id.capitalize(),
            acquisition.normalized_measurement_unit,
            "right",
        ),
    ]


def default_title(acquisition: GraphtecAcquisition) -> str:
    """Title built from the content only, never from the file name."""
    return f"Graphtec {acquisition.test_type} - Channel {acquisition.channel}"


def default_chart_config(acquisition: GraphtecAcquisition) -> GraphtecChartConfig:
    return GraphtecChartConfig(
        series=tuple(s.id for s in available_series(acquisition)),
        title=default_title(acquisition),
    )


def _finite(value: float | None, name: str) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise GraphtecChartConfigError(f"{name} must be a number.") from error
    if not math.isfinite(number):
        raise GraphtecChartConfigError(f"{name} must be a finite number.")
    if number < 0:
        raise GraphtecChartConfigError(f"{name} cannot be negative.")
    return number


def validate_chart_config(
    acquisition: GraphtecAcquisition,
    config: GraphtecChartConfig,
) -> GraphtecChartConfig:
    """Return a normalized configuration or raise a controlled error."""
    available = {s.id: s for s in available_series(acquisition)}
    requested = list(dict.fromkeys(config.series or ()))
    if not requested:
        raise GraphtecChartConfigError("Select at least one series.")
    unknown = [s for s in requested if s not in available]
    if unknown:
        raise GraphtecChartConfigError(
            f"Series not available for {acquisition.test_type}: "
            + ", ".join(unknown)
            + f". Available: {', '.join(available)}."
        )

    title = (config.title or "").strip() or default_title(acquisition)
    if len(title) > MAX_TITLE_LENGTH:
        raise GraphtecChartConfigError(
            f"The title cannot exceed {MAX_TITLE_LENGTH} characters."
        )

    time_min = _finite(config.time_min, "The start time")
    time_max = _finite(config.time_max, "The end time")
    start = acquisition.elapsed_time_start if time_min is None else time_min
    end = acquisition.elapsed_time_end if time_max is None else time_max
    if start >= end:
        raise GraphtecChartConfigError(
            "The start time must be lower than the end time."
        )
    if not any(start <= r.elapsed_time_seconds <= end for r in acquisition.records):
        raise GraphtecChartConfigError(
            "No records fall inside the selected time range "
            f"({acquisition.elapsed_time_start:g}-"
            f"{acquisition.elapsed_time_end:g} s available)."
        )

    ordered = tuple(s for s in available if s in requested)
    return GraphtecChartConfig(
        series=ordered,
        title=title,
        show_legend=bool(config.show_legend),
        show_phase_separators=bool(config.show_phase_separators),
        time_min=time_min,
        time_max=time_max,
    )


def _series_value(record: GraphtecRecord, series_id: str) -> float:
    if series_id == "voltage":
        return record.voltage_value
    return record.normalized_value


def _phase_markers(
    acquisition: GraphtecAcquisition, start: float, end: float
) -> list[PhaseMarker]:
    markers = []
    for segment in acquisition.phase_segments:
        if segment.end_elapsed_seconds < start or segment.start_elapsed_seconds > end:
            continue
        markers.append(
            PhaseMarker(segment.phase, max(segment.start_elapsed_seconds, start))
        )
    return markers


def build_graphtec_figure(
    acquisition: GraphtecAcquisition,
    config: GraphtecChartConfig,
) -> tuple[Figure, GraphtecChartRender]:
    """Build the Matplotlib figure and its description (without PNG)."""
    config = validate_chart_config(acquisition, config)
    series_by_id = {s.id: s for s in available_series(acquisition)}
    selected = [series_by_id[s] for s in config.series]

    start = acquisition.elapsed_time_start if config.time_min is None else config.time_min
    end = acquisition.elapsed_time_end if config.time_max is None else config.time_max
    full_range = config.time_min is None and config.time_max is None
    if not full_range:
        full_range = (
            start <= acquisition.elapsed_time_start
            and end >= acquisition.elapsed_time_end
        )
    visible = [r for r in acquisition.records if start <= r.elapsed_time_seconds <= end]

    figure = Figure(figsize=FIGURE_SIZE_INCHES, dpi=FIGURE_DPI)
    FigureCanvasAgg(figure)
    primary = figure.add_subplot(111)

    axes_for_series = {}
    axes_info: list[ChartAxisInfo] = []
    if len(selected) == 1:
        axes_for_series[selected[0].id] = primary
        axes_info.append(
            ChartAxisInfo("left", f"{selected[0].label} [{selected[0].unit}]", (selected[0].id,))
        )
    else:
        secondary = primary.twinx()
        for series in selected:
            axis = primary if series.axis == "left" else secondary
            axes_for_series[series.id] = axis
            axes_info.append(
                ChartAxisInfo(series.axis, f"{series.label} [{series.unit}]", (series.id,))
            )

    handles: list[Line2D] = []
    limited_points = 0
    result_points = 0
    operators: set[str] = set()

    for series in selected:
        axis = axes_for_series[series.id]
        color = SERIES_COLORS.get(series.id, "#465a65")
        measured = series.id != "voltage"
        xs, ys = [], []
        limit_x, limit_y, limit_ops = [], [], []
        for record in visible:
            if record.status != STATUS_TEST:
                continue
            value = _series_value(record, series.id)
            if measured and record.is_limited:
                limit_x.append(record.elapsed_time_seconds)
                limit_y.append(value)
                limit_ops.append(record.measurement_operator)
                xs.append(record.elapsed_time_seconds)
                ys.append(math.nan)
            else:
                xs.append(record.elapsed_time_seconds)
                ys.append(value)
        (line,) = axis.plot(
            xs, ys, color=color, linewidth=1.6, marker="o", markersize=2.5,
            label=f"{series.label} [{series.unit}]",
        )
        handles.append(line)
        if limit_x:
            for operator in sorted(set(limit_ops)):
                ox = [x for x, o in zip(limit_x, limit_ops) if o == operator]
                oy = [y for y, o in zip(limit_y, limit_ops) if o == operator]
                marker = "^" if operator == ">" else "v"
                (limit_line,) = axis.plot(
                    ox, oy, linestyle="none", marker=marker, markersize=7,
                    markerfacecolor="white", markeredgecolor=color,
                    markeredgewidth=1.4,
                    label=f"{series.label} limit ({operator} threshold)",
                )
                handles.append(limit_line)
                operators.add(operator)
            limited_points += len(limit_x)
        axis.set_ylabel(f"{series.label} [{series.unit}]", color=color)
        axis.tick_params(axis="y", colors=color)

    result_records = [r for r in visible if r.status != STATUS_TEST]
    for status in sorted({r.status for r in result_records}):
        for index, series in enumerate(selected):
            axis = axes_for_series[series.id]
            points = [r for r in result_records if r.status == status]
            (marker,) = axis.plot(
                [r.elapsed_time_seconds for r in points],
                [_series_value(r, series.id) for r in points],
                linestyle="none", marker="D", markersize=6,
                markerfacecolor=SERIES_COLORS.get(series.id, "#465a65"),
                markeredgecolor="black",
                label=f"{series.label} - {status} record",
            )
            handles.append(marker)
        result_points += len([r for r in result_records if r.status == status])

    phase_markers = _phase_markers(acquisition, start, end)
    span = end - start
    if config.show_phase_separators:
        label_y = 0.985
        previous_x: float | None = None
        for index, marker in enumerate(phase_markers):
            if index > 0 or marker.elapsed_time_seconds > start:
                primary.axvline(
                    marker.elapsed_time_seconds, color="#8a99a6",
                    linestyle=":", linewidth=0.9, zorder=0,
                )
            # Stagger letters of phases that start very close to each other.
            if previous_x is not None and marker.elapsed_time_seconds - previous_x < span * 0.04:
                label_y -= 0.055
            else:
                label_y = 0.985
            previous_x = marker.elapsed_time_seconds
            primary.text(
                marker.elapsed_time_seconds, label_y, f" {marker.phase}",
                transform=primary.get_xaxis_transform(),
                ha="left", va="top", fontsize=9, color="#5b6b78",
            )

    # A small margin keeps the first and last markers fully visible.
    primary.set_xlim(start - span * 0.015, end + span * 0.015)
    primary.set_xlabel(f"{X_AXIS_LABEL} [{X_AXIS_UNIT}]")
    primary.grid(True, color="#e3e8ec", linewidth=0.7)
    primary.set_title(config.title, fontsize=13, loc="left")

    notes = [LIMIT_NOTES[o] for o in sorted(operators)]
    if config.show_legend:
        primary.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.0, -0.13),
                       ncol=3, fontsize=8, frameon=False)
    if notes:
        figure.text(0.01, 0.01, "  ".join(notes), fontsize=8, color="#405566")
    figure.tight_layout(rect=(0, 0.04 if notes else 0, 1, 1))

    width, height = figure.canvas.get_width_height()
    render = GraphtecChartRender(
        png=b"",
        width=width,
        height=height,
        title=config.title,
        series=selected,
        axes=axes_info,
        time_start=start,
        time_end=end,
        full_range=full_range,
        records_plotted=len(visible),
        limited_points=limited_points,
        result_points=result_points,
        phase_markers=phase_markers if config.show_phase_separators else [],
        notes=notes,
    )
    return figure, render


def render_graphtec_chart(
    acquisition: GraphtecAcquisition,
    config: GraphtecChartConfig,
) -> GraphtecChartRender:
    """Render the chart as a PNG image."""
    figure, render = build_graphtec_figure(acquisition, config)
    buffer = BytesIO()
    figure.savefig(buffer, format="png", dpi=FIGURE_DPI, facecolor="white")
    render.png = buffer.getvalue()
    return render
