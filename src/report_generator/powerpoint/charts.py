from __future__ import annotations

from numbers import Real
from typing import Any

from pptx.chart.data import XyChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.util import Cm, Pt

from .styles import COLOR_GRAY, COLOR_NAVY, FONT_FAMILY


COLOR_ORANGE = RGBColor(237, 125, 49)
COLOR_BLUE = RGBColor(68, 114, 196)
COLOR_PURPLE = RGBColor(112, 78, 145)


def _is_number(value: Any) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool)


def _series_points(
    profile_points: list[dict[str, Any]],
    x_field: str,
    y_field: str,
) -> list[tuple[float, float]]:
    return [
        (float(point[x_field]), float(point[y_field]))
        for point in profile_points
        if _is_number(point.get(x_field))
        and _is_number(point.get(y_field))
    ]


def has_climatic_chart_data(
    profile_points: list[dict[str, Any]],
) -> bool:
    return bool(
        _series_points(
            profile_points,
            "time_min",
            "temperature_c",
        )
        or _series_points(
            profile_points,
            "time_min",
            "humidity_percent",
        )
    )


def has_dut_chart_data(
    profile_points: list[dict[str, Any]],
) -> bool:
    return bool(
        _series_points(
            profile_points,
            "time_ms",
            "dut_position_percent",
        )
    )


def _set_text_style(text_frame, size_pt: float, bold: bool = False):
    for paragraph in text_frame.paragraphs:
        for run in paragraph.runs:
            run.font.name = FONT_FAMILY
            run.font.size = Pt(size_pt)
            run.font.bold = bold
            run.font.color.rgb = COLOR_NAVY


def _style_chart(
    chart,
    title: str,
    x_axis_title: str,
    y_axis_title: str,
    show_legend: bool,
) -> None:
    chart.has_title = True
    chart.chart_title.text_frame.text = title
    _set_text_style(
        chart.chart_title.text_frame,
        size_pt=14,
        bold=True,
    )

    chart.has_legend = show_legend
    if show_legend:
        chart.legend.position = XL_LEGEND_POSITION.BOTTOM
        chart.legend.include_in_layout = False
        chart.legend.font.name = FONT_FAMILY
        chart.legend.font.size = Pt(9)

    chart.category_axis.has_title = True
    chart.category_axis.axis_title.text_frame.text = x_axis_title
    _set_text_style(
        chart.category_axis.axis_title.text_frame,
        size_pt=10,
        bold=True,
    )
    chart.category_axis.tick_labels.font.name = FONT_FAMILY
    chart.category_axis.tick_labels.font.size = Pt(9)

    chart.value_axis.has_title = True
    chart.value_axis.axis_title.text_frame.text = y_axis_title
    _set_text_style(
        chart.value_axis.axis_title.text_frame,
        size_pt=10,
        bold=True,
    )
    chart.value_axis.tick_labels.font.name = FONT_FAMILY
    chart.value_axis.tick_labels.font.size = Pt(9)
    chart.value_axis.has_major_gridlines = True
    chart.value_axis.major_gridlines.format.line.color.rgb = COLOR_GRAY
    chart.value_axis.major_gridlines.format.line.transparency = 65


def _add_xy_series(chart_data, name, points):
    series = chart_data.add_series(name)
    for x_value, y_value in points:
        series.add_data_point(x_value, y_value)


def _format_series(chart_series, color: RGBColor) -> None:
    chart_series.format.line.color.rgb = color
    chart_series.format.line.width = Pt(2)


def add_climatic_profile_chart(
    slide,
    profile_points: list[dict[str, Any]],
    left_cm: float,
    top_cm: float,
    width_cm: float,
    height_cm: float,
):
    temperature_points = _series_points(
        profile_points,
        "time_min",
        "temperature_c",
    )
    humidity_points = _series_points(
        profile_points,
        "time_min",
        "humidity_percent",
    )

    if not temperature_points and not humidity_points:
        return None

    chart_data = XyChartData()
    if temperature_points:
        _add_xy_series(
            chart_data,
            "Temperature [°C]",
            temperature_points,
        )
    if humidity_points:
        _add_xy_series(
            chart_data,
            "Humidity [%]",
            humidity_points,
        )

    chart = slide.shapes.add_chart(
        XL_CHART_TYPE.XY_SCATTER_LINES_NO_MARKERS,
        Cm(left_cm),
        Cm(top_cm),
        Cm(width_cm),
        Cm(height_cm),
        chart_data,
    ).chart

    y_axis_title = "Temperature [°C]"
    if temperature_points and humidity_points:
        y_axis_title = "Temperature [°C] / Humidity [%]"
    elif humidity_points:
        y_axis_title = "Humidity [%]"

    _style_chart(
        chart,
        title="Climatic profile",
        x_axis_title="Time [min]",
        y_axis_title=y_axis_title,
        show_legend=bool(temperature_points and humidity_points),
    )

    for series_index, chart_series in enumerate(chart.series):
        color = COLOR_ORANGE if series_index == 0 else COLOR_BLUE
        _format_series(chart_series, color)

    return chart


def add_dut_profile_chart(
    slide,
    profile_points: list[dict[str, Any]],
    left_cm: float,
    top_cm: float,
    width_cm: float,
    height_cm: float,
):
    dut_points = _series_points(
        profile_points,
        "time_ms",
        "dut_position_percent",
    )

    if not dut_points:
        return None

    chart_data = XyChartData()
    _add_xy_series(
        chart_data,
        "DUT position [%]",
        dut_points,
    )

    chart = slide.shapes.add_chart(
        XL_CHART_TYPE.XY_SCATTER_LINES_NO_MARKERS,
        Cm(left_cm),
        Cm(top_cm),
        Cm(width_cm),
        Cm(height_cm),
        chart_data,
    ).chart

    _style_chart(
        chart,
        title="DUT position / power request",
        x_axis_title="Time [ms]",
        y_axis_title="Position / power request [%]",
        show_legend=False,
    )
    _format_series(chart.series[0], COLOR_PURPLE)

    return chart
