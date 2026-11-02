"""Console tool and compatibility layer for SIMPATI acquisitions.

The generic SIMPATI parser lives in :mod:`report_generator.simpati`. This
module keeps the historical import path used by the backend and the
console scripts, and provides the interactive Matplotlib tool that
generates charts for every acquisition (``.x01`` ... ``.x99``) of a test.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, CheckButtons, SpanSelector
import pandas as pd

from ..chart_export import (
    LINE_WIDTH_PT,
    MAX_X_TICKS,
    SECONDARY_LINE_WIDTH_PT,
    add_report_legend,
    new_report_figure,
    report_chart_style,
    save_report_png,
    wrap_title,
)
from ..cli import prompt_test_root
from ..rendered_assets import (
    METADATA_SUFFIX,
    build_next_chart_path,
    metadata_path_for,
    prepare_rendered_assets_directory,
)
from ..simpati import (
    CHART_PREFIX,
    STATUS_READY,
    TIMESTAMP_FORMAT,
    SimpatiAcquisitionFile,
    SimpatiError,
    SimpatiFileNotFoundError,
    SimpatiFormatError,
    analyze_simpati_acquisitions,
    chart_metadata,
    chart_prefix,
    classify_channels,
    discover_simpati_acquisitions,
    get_temperature_channels,
    read_simpati,
    read_simpati_acquisition,
)

__all__ = [
    "CHART_PREFIX",
    "SimpatiError",
    "SimpatiFileNotFoundError",
    "SimpatiFormatError",
    "TIMESTAMP_FORMAT",
    "chart_prefix",
    "chart_title",
    "discover_simpati_acquisitions",
    "export_simpati_chart",
    "find_simpati_files",
    "generate_simpati_chart",
    "get_temperature_channels",
    "prepare_rendered_assets_directory",
    "read_simpati",
    "read_simpati_acquisition",
]

#: Line style of each thermal role. Setpoints are dashed.
_ROLE_COLORS = {
    "chamber": "#005A9C",
    "supply_air": "#8764B8",
    "return_air": "#00B7C3",
    "basket": "#005A9C",
    "hot_chamber": "#D83B01",
    "cold_chamber": "#107C10",
    "specimen": "#C239B3",
}


def find_simpati_files(test_root: Union[str, Path]) -> List[Path]:
    """Return every ``.xNN`` acquisition of the test in numeric order."""
    return [item.path for item in discover_simpati_acquisitions(test_root)]


def chart_title(
    dataframe: pd.DataFrame,
    acquisition_file: Optional[SimpatiAcquisitionFile] = None,
) -> str:
    """Chart title naming the source acquisition."""
    if acquisition_file is not None:
        return (
            f"SIMPATI {acquisition_file.label} - {acquisition_file.name} - "
            "Temperature profile"
        )
    source = dataframe.attrs.get("source_file")
    name = Path(source).name if source else "acquisition"
    return f"SIMPATI {name} - Temperature profile"


def _configure_chart_axis(axis, title: str, max_ticks: int = 12) -> None:
    axis.set_title(title)
    axis.set_xlabel("Date and time")
    axis.set_ylabel("Temperature [°C]")
    axis.grid(visible=True, alpha=0.25)

    # En la exportación se limitan las marcas para que las fechas no se solapen.
    date_locator = mdates.AutoDateLocator(
        minticks=3 if max_ticks < 12 else 5,
        maxticks=max_ticks,
    )
    axis.xaxis.set_major_locator(date_locator)
    axis.xaxis.set_major_formatter(
        mdates.ConciseDateFormatter(date_locator)
    )


def _line_style(dataframe: pd.DataFrame, column_name: str) -> dict:
    roles = {
        channel.column: channel.role or ""
        for channel in classify_channels(dataframe[["Timestamp", column_name]])
    }
    role = roles.get(column_name, "")
    family = role.rsplit("_", 1)[0] if role else ""
    setpoint = role.endswith("_setpoint")
    return {
        "color": _ROLE_COLORS.get(family, None),
        "linewidth": 0.8 if setpoint else 1.0,
        "linestyle": "--" if setpoint else "-",
        "alpha": 0.85 if setpoint else 1.0,
    }


def _plot_temperature_channels(
    axis,
    dataframe: pd.DataFrame,
    channels: Dict[str, str],
) -> Dict[str, object]:
    plotted_lines: Dict[str, object] = {}

    for display_name, column_name in channels.items():
        valid_rows = dataframe[column_name].notna()

        if not valid_rows.any():
            continue

        style = {
            key: value
            for key, value in _line_style(dataframe, column_name).items()
            if value is not None
        }
        line = axis.plot(
            dataframe.loc[valid_rows, "Timestamp"],
            dataframe.loc[valid_rows, column_name],
            label=display_name,
            **style,
        )[0]
        plotted_lines[display_name] = line

    if not plotted_lines:
        raise SimpatiFormatError(
            "The temperature channels do not contain numeric data."
        )

    return plotted_lines


def save_current_view(
    dataframe: pd.DataFrame,
    channels: Dict[str, str],
    visible_channels: List[str],
    x_limits: Tuple[float, float],
    y_limits: Tuple[float, float],
    output_directory: Path,
    acquisition_file: Optional[SimpatiAcquisitionFile],
    title: str,
) -> Path:
    """Save the current view as a new ``chart_simpati_xNN_MM.png``.

    La imagen usa el formato común de ``_RenderedAssets`` (1800 × 1125 px,
    proporción 1,6:1) y conserva los límites X e Y de la vista actual.
    """
    visible_mapping = {
        display_name: channels[display_name]
        for display_name in visible_channels
        if display_name in channels
    }

    with report_chart_style():
        export_figure = new_report_figure()
        export_axis = export_figure.add_subplot(111)
        lines = _plot_temperature_channels(
            axis=export_axis,
            dataframe=dataframe,
            channels=visible_mapping,
        )
        # Trazos de exportación algo más gruesos que en la ventana interactiva.
        for line in lines.values():
            line.set_linewidth(
                SECONDARY_LINE_WIDTH_PT
                if line.get_linestyle() == "--"
                else LINE_WIDTH_PT
            )
        _configure_chart_axis(export_axis, wrap_title(title), max_ticks=MAX_X_TICKS)
        export_axis.set_xlim(x_limits)
        export_axis.set_ylim(y_limits)
        # Valores completos en rangos Y estrechos (sin desplazamiento).
        export_axis.ticklabel_format(axis="y", style="plain", useOffset=False)
        add_report_legend(export_figure, list(lines.values()), list(lines.keys()))

    prefix = (
        chart_prefix(acquisition_file.index)
        if acquisition_file is not None
        else CHART_PREFIX
    )
    output_path = build_next_chart_path(
        output_directory, prefix, (METADATA_SUFFIX,)
    )
    with report_chart_style():
        save_report_png(export_figure, output_path)

    if acquisition_file is not None:
        metadata = chart_metadata(
            output_path.name,
            output_path.stat().st_size,
            acquisition_file,
        )
        metadata_path_for(output_path).write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    return output_path


def export_simpati_chart(
    dataframe: pd.DataFrame,
    output_directory: Union[str, Path],
    acquisition_file: Optional[SimpatiAcquisitionFile] = None,
) -> List[Path]:
    """Open the interactive chart of one acquisition and save its views.

    Each saved view is written as ``chart_simpati_xNN_MM.png`` with a
    companion JSON that records the source acquisition.
    """
    output_directory = Path(output_directory).expanduser().resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    channels = get_temperature_channels(dataframe)
    title = chart_title(dataframe, acquisition_file)

    figure, axis = plt.subplots(figsize=(16, 8), dpi=120)
    figure.subplots_adjust(
        left=0.08,
        right=0.80,
        bottom=0.18,
        top=0.90,
    )

    plotted_lines = _plot_temperature_channels(
        axis=axis,
        dataframe=dataframe,
        channels=channels,
    )
    _configure_chart_axis(axis, title)

    original_x_limits = axis.get_xlim()
    original_y_limits = axis.get_ylim()

    checkbox_axis = figure.add_axes([0.82, 0.48, 0.17, 0.32])
    channel_names = list(plotted_lines.keys())
    channel_states = [True] * len(channel_names)
    channel_selector = CheckButtons(
        checkbox_axis,
        channel_names,
        channel_states,
    )
    checkbox_axis.set_title("Visible channels", fontsize=10)

    def toggle_channel(label: str) -> None:
        line = plotted_lines[label]
        line.set_visible(not line.get_visible())
        figure.canvas.draw_idle()

    channel_selector.on_clicked(toggle_channel)

    status_text = figure.text(
        0.82,
        0.42,
        "Drag over the chart to select a time range.",
        fontsize=9,
        va="top",
        wrap=True,
    )

    def select_time_range(x_min: float, x_max: float) -> None:
        if x_min == x_max:
            return
        axis.set_xlim(min(x_min, x_max), max(x_min, x_max))
        figure.canvas.draw_idle()
        status_text.set_text(
            "Time range selected. Adjust the vertical axis with "
            "the toolbar if required."
        )

    span_selector = SpanSelector(
        axis,
        select_time_range,
        direction="horizontal",
        useblit=True,
        props={
            "facecolor": "#5B9BD5",
            "alpha": 0.25,
        },
        interactive=True,
        drag_from_anywhere=True,
    )

    save_axis = figure.add_axes([0.82, 0.31, 0.17, 0.055])
    reset_axis = figure.add_axes([0.82, 0.24, 0.17, 0.055])
    close_axis = figure.add_axes([0.82, 0.17, 0.17, 0.055])

    save_button = Button(
        save_axis,
        "Save current view",
        color="#D9EAF7",
        hovercolor="#B8D7EE",
    )
    reset_button = Button(
        reset_axis,
        "Reset view",
        color="#EAEAEA",
        hovercolor="#D5D5D5",
    )
    close_button = Button(
        close_axis,
        "Close",
        color="#EAEAEA",
        hovercolor="#D5D5D5",
    )

    saved_paths: List[Path] = []

    def save_view(_event) -> None:
        visible_channels = [
            display_name
            for display_name, line in plotted_lines.items()
            if line.get_visible()
        ]

        if not visible_channels:
            status_text.set_text(
                "Select at least one visible channel before saving."
            )
            figure.canvas.draw_idle()
            return

        output_path = save_current_view(
            dataframe=dataframe,
            channels=channels,
            visible_channels=visible_channels,
            x_limits=axis.get_xlim(),
            y_limits=axis.get_ylim(),
            output_directory=output_directory,
            acquisition_file=acquisition_file,
            title=title,
        )
        saved_paths.append(output_path)
        status_text.set_text(
            f"Saved image {len(saved_paths)}:\n"
            f"{output_path.name}"
        )
        figure.canvas.draw_idle()

    def reset_view(_event) -> None:
        axis.set_xlim(original_x_limits)
        axis.set_ylim(original_y_limits)
        figure.canvas.draw_idle()
        status_text.set_text(
            "Full acquisition restored."
        )

    def close_window(_event) -> None:
        plt.close(figure)

    save_button.on_clicked(save_view)
    reset_button.on_clicked(reset_view)
    close_button.on_clicked(close_window)

    figure._simpati_widgets = {
        "channel_selector": channel_selector,
        "span_selector": span_selector,
        "save_button": save_button,
        "reset_button": reset_button,
        "close_button": close_button,
    }

    print()
    print("Interactive chart opened")
    print("------------------------")
    print("1. Drag horizontally over the chart to select a time range.")
    print("2. Use the Matplotlib toolbar for additional zoom or pan.")
    print("3. Use the channel list to show or hide signals.")
    print("4. Press 'Save current view' once for each image required.")
    print()

    plt.show()

    if not saved_paths:
        print("The chart window was closed without saving.")
    else:
        print(f"Saved charts: {len(saved_paths)}")
        for saved_path in saved_paths:
            print(f"  - {saved_path}")

    return saved_paths

def generate_simpati_chart(
    test_root: Union[str, Path],
) -> List[Path]:
    """Open the interactive chart of every representable acquisition.

    Acquisitions without thermal channels or with an incompatible content
    are reported and skipped; they never stop the others.
    """
    test_root = Path(test_root).expanduser().resolve()
    report = analyze_simpati_acquisitions(test_root)
    if not report.analyses:
        raise SimpatiFileNotFoundError(
            "No SIMPATI acquisition (.x01 to .x99) was found in 03_Data/01_SIMPATI."
        )
    assets_directory = prepare_rendered_assets_directory(test_root)

    print()
    print("SIMPATI acquisitions")
    print("--------------------")
    generated_charts: List[Path] = []
    for analysis in report.analyses:
        acquisition_file = analysis.file
        print(f"{acquisition_file.label}  {acquisition_file.name}  [{analysis.status}]")
        if analysis.error is not None:
            print(f"    {analysis.error}")
        if analysis.status != STATUS_READY or analysis.acquisition is None:
            continue
        dataframe = analysis.acquisition.dataframe
        print(f"    Records: {len(dataframe)}")
        print(f"    Acquisition start: {dataframe['Timestamp'].iloc[0]}")
        print(f"    Acquisition end: {dataframe['Timestamp'].iloc[-1]}")
        generated_charts.extend(
            export_simpati_chart(
                dataframe=dataframe,
                output_directory=assets_directory,
                acquisition_file=acquisition_file,
            )
        )

    print()
    print("SIMPATI extraction completed")
    print("----------------------------")
    print(f"Test root: {test_root}")
    print(f"Acquisitions found: {report.found_count}")
    print(f"Acquisitions processed: {report.processed_count}")
    print(f"Without representable channels: {report.without_thermal_count}")
    print(f"Incompatible: {report.incompatible_count}")
    print(f"Generated charts: {len(generated_charts)}")
    for generated_chart in generated_charts:
        print(f"  - {generated_chart}")
    print()

    return generated_charts


def main() -> None:
    print("SIMPATI Extractor")
    print("=================")

    generate_simpati_chart(test_root=prompt_test_root())


if __name__ == "__main__":
    main()
