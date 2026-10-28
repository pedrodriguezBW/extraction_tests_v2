import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, CheckButtons, SpanSelector
import pandas as pd

from ..cli import prompt_test_root
from ..paths import simpati_directory
from ..rendered_assets import (
    build_next_chart_path as _build_next_chart_path,
    prepare_rendered_assets_directory,
)

OUTPUT_FILE_PREFIX = "chart03_simpati_acquisition"
TIMESTAMP_FORMAT = "%d.%m.%Y %H:%M:%S"
SUPPORTED_ENCODINGS = (
    "utf-8-sig",
    "cp1252",
    "latin-1",
)


class SimpatiError(Exception):
    """Base exception for SIMPATI processing errors."""


class SimpatiFileNotFoundError(SimpatiError):
    """Raised when the SIMPATI acquisition file cannot be found."""


class SimpatiFormatError(SimpatiError):
    """Raised when the SIMPATI file structure is invalid."""


def find_simpati_file(test_root: Union[str, Path]) -> Path:
    test_root = Path(test_root).expanduser().resolve()

    if not test_root.exists():
        raise FileNotFoundError(
            f"The test folder does not exist: {test_root}"
        )

    if not test_root.is_dir():
        raise NotADirectoryError(
            f"The specified path is not a folder: {test_root}"
        )

    acquisition_directory = simpati_directory(test_root)

    if not acquisition_directory.exists():
        raise SimpatiFileNotFoundError(
            "The SIMPATI acquisition folder was not found:\n"
            f"{acquisition_directory}"
        )

    if not acquisition_directory.is_dir():
        raise NotADirectoryError(
            "The SIMPATI acquisition path is not a folder:\n"
            f"{acquisition_directory}"
        )

    simpati_files = sorted(
        file_path
        for file_path in acquisition_directory.iterdir()
        if file_path.is_file()
        and (
            file_path.suffix.lower() == ".x03"
            or file_path.name.lower().endswith(".x03.txt")
        )
    )

    if not simpati_files:
        raise SimpatiFileNotFoundError(
            "No .x03 file was found in:\n"
            f"{acquisition_directory}"
        )

    if len(simpati_files) > 1:
        file_names = "\n".join(
            f"  - {file_path.name}"
            for file_path in simpati_files
        )
        raise SimpatiError(
            "More than one SIMPATI file was found:\n"
            f"{file_names}"
        )

    return simpati_files[0]


def read_text_lines(
    file_path: Union[str, Path],
) -> Tuple[List[str], str]:
    file_path = Path(file_path)
    raw_data = file_path.read_bytes()

    if raw_data.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            decoded_text = raw_data.decode("utf-16")
            lines = decoded_text.splitlines()
            if any("A:Temp canast" in line for line in lines):
                return lines, "utf-16"
        except UnicodeDecodeError:
            pass

    for encoding in SUPPORTED_ENCODINGS:
        try:
            decoded_text = raw_data.decode(encoding)
        except UnicodeDecodeError:
            continue

        lines = decoded_text.splitlines()

        if any("A:Temp canast" in line for line in lines):
            return lines, encoding

    raise SimpatiFormatError(
        "The SIMPATI file could be decoded, but the expected "
        "channel header was not found in any supported encoding:\n"
        f"{file_path}"
    )


def split_simpati_line(line: str) -> List[str]:
    return next(
        csv.reader(
            [line],
            delimiter=";",
            quotechar='"',
        )
    )


def find_channel_header_row(lines: List[str]) -> int:
    required_markers = (
        "A:Pos canasta",
        "A:Temp canast",
        "N:Temp canast",
        "A:Cam calient",
        "N:Cam calient",
        "A:Cam fria",
        "N:Cam fria",
    )

    for line_index, line in enumerate(lines):
        if all(marker in line for marker in required_markers):
            return line_index

    raise SimpatiFormatError(
        "The SIMPATI channel header could not be identified."
    )


def normalize_channel_name(
    raw_name: str,
    position: int,
    occurrences: Dict[str, int],
) -> str:
    channel_name = " ".join(raw_name.strip().split())

    if not channel_name:
        channel_name = f"Unnamed_{position:02d}"

    occurrences[channel_name] = occurrences.get(channel_name, 0) + 1
    occurrence = occurrences[channel_name]

    if occurrence == 1:
        return channel_name

    return f"{channel_name}_{occurrence}"


def build_column_names(
    raw_headers: List[str],
    raw_units: List[str],
) -> List[str]:
    while raw_headers and not raw_headers[-1].strip():
        raw_headers.pop()

    while raw_units and not raw_units[-1].strip():
        raw_units.pop()

    signal_count = max(len(raw_headers), len(raw_units))

    if signal_count == 0:
        raise SimpatiFormatError(
            "The SIMPATI header does not contain channels."
        )

    column_names = ["Timestamp"]
    occurrences: Dict[str, int] = {}

    for position in range(signal_count):
        raw_name = raw_headers[position] if position < len(raw_headers) else ""
        raw_unit = raw_units[position] if position < len(raw_units) else ""

        channel_name = normalize_channel_name(
            raw_name=raw_name,
            position=position + 1,
            occurrences=occurrences,
        )
        unit = raw_unit.strip()

        if unit:
            column_names.append(f"{channel_name} {unit}")
        else:
            column_names.append(channel_name)

    return column_names


def parse_data_rows(
    lines: List[str],
    first_data_row: int,
    expected_column_count: int,
) -> List[List[str]]:
    parsed_rows: List[List[str]] = []

    for line in lines[first_data_row:]:
        if not line.strip():
            continue

        fields = split_simpati_line(line)

        while fields and not fields[-1].strip():
            fields.pop()

        if not fields:
            continue

        timestamp = pd.to_datetime(
            fields[0].strip(),
            format=TIMESTAMP_FORMAT,
            errors="coerce",
        )

        if pd.isna(timestamp):
            continue

        if len(fields) < expected_column_count:
            fields.extend([""] * (expected_column_count - len(fields)))
        elif len(fields) > expected_column_count:
            fields = fields[:expected_column_count]

        parsed_rows.append(fields)

    if not parsed_rows:
        raise SimpatiFormatError(
            "No valid timestamped rows were found."
        )

    return parsed_rows


def read_simpati(
    simpati_file: Union[str, Path],
) -> pd.DataFrame:
    simpati_file = Path(simpati_file).expanduser().resolve()

    if not simpati_file.is_file():
        raise SimpatiFileNotFoundError(
            f"The SIMPATI file does not exist: {simpati_file}"
        )

    lines, detected_encoding = read_text_lines(simpati_file)
    header_row = find_channel_header_row(lines)
    units_row = header_row + 1

    if units_row >= len(lines):
        raise SimpatiFormatError(
            "The units row is missing from the SIMPATI file."
        )

    raw_headers = split_simpati_line(lines[header_row])
    raw_units = split_simpati_line(lines[units_row])

    column_names = build_column_names(
        raw_headers=raw_headers,
        raw_units=raw_units,
    )

    parsed_rows = parse_data_rows(
        lines=lines,
        first_data_row=units_row + 1,
        expected_column_count=len(column_names),
    )

    dataframe = pd.DataFrame(
        parsed_rows,
        columns=column_names,
    )

    dataframe["Timestamp"] = pd.to_datetime(
        dataframe["Timestamp"].astype(str).str.strip(),
        format=TIMESTAMP_FORMAT,
        errors="coerce",
    )

    for column_name in dataframe.columns[1:]:
        cleaned_values = (
            dataframe[column_name]
            .astype(str)
            .str.strip()
            .str.replace(",", ".", regex=False)
        )
        dataframe[column_name] = pd.to_numeric(
            cleaned_values,
            errors="coerce",
        )

    dataframe = (
        dataframe
        .dropna(subset=["Timestamp"])
        .sort_values("Timestamp")
        .drop_duplicates(subset=["Timestamp"], keep="last")
        .reset_index(drop=True)
    )

    if dataframe.empty:
        raise SimpatiFormatError(
            "The SIMPATI acquisition is empty after normalisation."
        )

    dataframe.attrs["source_file"] = str(simpati_file)
    dataframe.attrs["encoding"] = detected_encoding
    return dataframe


def find_channel(
    dataframe: pd.DataFrame,
    channel_prefix: str,
) -> Optional[str]:
    matches = [
        column_name
        for column_name in dataframe.columns
        if column_name.startswith(channel_prefix)
    ]

    if not matches:
        return None

    return matches[0]


def get_temperature_channels(
    dataframe: pd.DataFrame,
) -> Dict[str, str]:
    requested_channels = (
        ("Basket temperature", "A:Temp canast"),
        ("Basket setpoint", "N:Temp canast"),
        ("Hot chamber temperature", "A:Cam calient"),
        ("Hot chamber setpoint", "N:Cam calient"),
        ("Cold chamber temperature", "A:Cam fria"),
        ("Cold chamber setpoint", "N:Cam fria"),
    )

    available_channels: Dict[str, str] = {}

    for display_name, channel_prefix in requested_channels:
        column_name = find_channel(
            dataframe=dataframe,
            channel_prefix=channel_prefix,
        )
        if column_name is not None:
            available_channels[display_name] = column_name

    if not available_channels:
        raise SimpatiFormatError(
            "No temperature channels were found."
        )

    return available_channels


def _configure_chart_axis(axis) -> None:
    axis.set_title("SIMPATI acquisition - Temperature profile")
    axis.set_xlabel("Date and time")
    axis.set_ylabel("Temperature [°C]")
    axis.grid(visible=True, alpha=0.25)

    date_locator = mdates.AutoDateLocator(
        minticks=5,
        maxticks=12,
    )
    axis.xaxis.set_major_locator(date_locator)
    axis.xaxis.set_major_formatter(
        mdates.ConciseDateFormatter(date_locator)
    )


def _plot_temperature_channels(
    axis,
    dataframe: pd.DataFrame,
    channels: Dict[str, str],
) -> Dict[str, object]:
    styles = {
        "Basket temperature": {
            "color": "#005A9C",
            "linewidth": 1.0,
            "linestyle": "-",
            "alpha": 1.0,
        },
        "Basket setpoint": {
            "color": "#005A9C",
            "linewidth": 0.8,
            "linestyle": "--",
            "alpha": 0.85,
        },
        "Hot chamber temperature": {
            "color": "#D83B01",
            "linewidth": 0.8,
            "linestyle": "-",
            "alpha": 0.8,
        },
        "Hot chamber setpoint": {
            "color": "#D83B01",
            "linewidth": 0.7,
            "linestyle": "--",
            "alpha": 0.75,
        },
        "Cold chamber temperature": {
            "color": "#107C10",
            "linewidth": 0.8,
            "linestyle": "-",
            "alpha": 0.8,
        },
        "Cold chamber setpoint": {
            "color": "#107C10",
            "linewidth": 0.7,
            "linestyle": "--",
            "alpha": 0.75,
        },
    }

    plotted_lines: Dict[str, object] = {}

    for display_name, column_name in channels.items():
        valid_rows = dataframe[column_name].notna()

        if not valid_rows.any():
            continue

        line = axis.plot(
            dataframe.loc[valid_rows, "Timestamp"],
            dataframe.loc[valid_rows, column_name],
            label=display_name,
            **styles[display_name],
        )[0]
        plotted_lines[display_name] = line

    if not plotted_lines:
        raise SimpatiFormatError(
            "The temperature channels do not contain numeric data."
        )

    return plotted_lines


def _save_current_view(
    dataframe: pd.DataFrame,
    channels: Dict[str, str],
    visible_channels: List[str],
    x_limits: Tuple[float, float],
    y_limits: Tuple[float, float],
    output_path: Path,
) -> None:
    export_figure, export_axis = plt.subplots(
        figsize=(16, 7),
        dpi=160,
    )

    visible_mapping = {
        display_name: channels[display_name]
        for display_name in visible_channels
        if display_name in channels
    }

    _plot_temperature_channels(
        axis=export_axis,
        dataframe=dataframe,
        channels=visible_mapping,
    )
    _configure_chart_axis(export_axis)
    export_axis.set_xlim(x_limits)
    export_axis.set_ylim(y_limits)
    export_axis.legend(
        ncol=3,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.14),
        frameon=False,
    )
    export_figure.tight_layout()
    export_figure.savefig(
        output_path,
        format="png",
        dpi=160,
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(export_figure)


def build_next_chart_path(output_directory: Path) -> Path:
    """Return the next free ``chart03_simpati_acquisition_NN.png`` path."""
    return _build_next_chart_path(Path(output_directory), OUTPUT_FILE_PREFIX)


def export_simpati_chart(
    dataframe: pd.DataFrame,
    output_directory: Union[str, Path],
) -> List[Path]:
    output_directory = Path(output_directory).expanduser().resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    channels = get_temperature_channels(dataframe)

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
    _configure_chart_axis(axis)

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

        output_path = build_next_chart_path(
            output_directory
        )

        _save_current_view(
            dataframe=dataframe,
            channels=channels,
            visible_channels=visible_channels,
            x_limits=axis.get_xlim(),
            y_limits=axis.get_ylim(),
            output_path=output_path,
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
    test_root = Path(test_root).expanduser().resolve()
    simpati_file = find_simpati_file(test_root)
    assets_directory = prepare_rendered_assets_directory(test_root)
    dataframe = read_simpati(simpati_file)
    generated_charts = export_simpati_chart(
        dataframe=dataframe,
        output_directory=assets_directory,
    )

    print()
    print("SIMPATI extraction completed")
    print("----------------------------")
    print(f"Test root: {test_root}")
    print(f"Source file: {simpati_file}")
    print(f"Records: {len(dataframe)}")
    print(f"Acquisition start: {dataframe['Timestamp'].iloc[0]}")
    print(f"Acquisition end: {dataframe['Timestamp'].iloc[-1]}")
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
