from __future__ import annotations

from math import ceil
from typing import Any

from pptx.enum.text import MSO_VERTICAL_ANCHOR, PP_ALIGN
from pptx.util import Cm, Pt

from .styles import (
    COLOR_NAVY,
    COLOR_ROW_ALTERNATE,
    COLOR_WHITE,
    FONT_FAMILY,
    FONT_SIZE_TABLE_BODY_PT,
    FONT_SIZE_TABLE_HEADER_PT,
    FONT_SIZE_TESTED_PARTS_PT,
    TABLE_HEADER_HEIGHT_CM,
    TABLE_ROW_HEIGHT_CM,
)

TESTED_PARTS_TABLE_TOP_CM = 4.35
TESTED_PARTS_TABLE_BOTTOM_GAP_CM = 0.45
TESTED_PARTS_HEADER_HEIGHT_CM = 1.10
TESTED_PARTS_BASE_ROW_HEIGHT_CM = 1.65
TESTED_PARTS_COLUMN_WIDTHS_CM = [10.50, 5.30, 4.30, 4.00, 5.53]
TESTED_PARTS_TABLE_WIDTH_CM = sum(TESTED_PARTS_COLUMN_WIDTHS_CM)


def tested_part_row_height_cm(sample: dict[str, Any]) -> float:
    sample_code = str(sample.get("sample_code") or "")
    sample_description = str(sample.get("sample_description") or "")
    tested_part_value = "\n".join(
        value for value in (sample_code, sample_description) if value
    )

    characters_per_line = max(
        1,
        int(
            ((TESTED_PARTS_COLUMN_WIDTHS_CM[0] - 0.24) * 30)
            / FONT_SIZE_TESTED_PARTS_PT
        ),
    )
    estimated_lines = sum(
        max(1, ceil(len(line) / characters_per_line))
        for line in tested_part_value.splitlines()
    ) or 1

    line_height_cm = FONT_SIZE_TESTED_PARTS_PT / 28.35
    return max(
        TESTED_PARTS_BASE_ROW_HEIGHT_CM,
        TESTED_PARTS_BASE_ROW_HEIGHT_CM
        + max(0, estimated_lines - 2) * line_height_cm,
    )


def add_tested_parts_table(
    slide,
    samples: list[dict[str, Any]],
    row_heights_cm: list[float] | None = None,
) -> None:
    column_headers = [
        "TESTED PART",
        "BW REFERENCE",
        "HW REF.",
        "SW REF.",
        "CUSTOMER PN",
    ]

    table_left_cm = 2.12
    table_top_cm = TESTED_PARTS_TABLE_TOP_CM
    table_width_cm = TESTED_PARTS_TABLE_WIDTH_CM
    header_height_cm = TESTED_PARTS_HEADER_HEIGHT_CM
    if row_heights_cm is None:
        row_heights_cm = [
            tested_part_row_height_cm(sample)
            for sample in samples
        ]
    if len(row_heights_cm) != len(samples):
        raise ValueError(
            "The number of Tested Parts row heights must match the samples."
        )

    row_count = len(samples) + 1
    column_count = len(column_headers)

    table_height_cm = header_height_cm + sum(row_heights_cm)

    table_shape = slide.shapes.add_table(
        row_count,
        column_count,
        Cm(table_left_cm),
        Cm(table_top_cm),
        Cm(table_width_cm),
        Cm(table_height_cm),
    )

    table = table_shape.table

    for column_index, column_width_cm in enumerate(
        TESTED_PARTS_COLUMN_WIDTHS_CM
    ):
        table.columns[column_index].width = Cm(
            column_width_cm
        )

    table.rows[0].height = Cm(header_height_cm)

    for row_index in range(1, row_count):
        table.rows[row_index].height = Cm(
            row_heights_cm[row_index - 1]
        )

    # ==========================================================
    # CABECERA
    # ==========================================================

    for column_index, header in enumerate(column_headers):
        cell = table.cell(0, column_index)
        cell.text = header

        cell.vertical_anchor = MSO_VERTICAL_ANCHOR.MIDDLE

        cell.fill.solid()
        cell.fill.fore_color.rgb = COLOR_NAVY

        cell.margin_left = Cm(0.10)
        cell.margin_right = Cm(0.10)
        cell.margin_top = Cm(0.05)
        cell.margin_bottom = Cm(0.05)

        text_frame = cell.text_frame
        text_frame.word_wrap = True

        for paragraph in text_frame.paragraphs:
            paragraph.alignment = PP_ALIGN.CENTER
            paragraph.space_before = Pt(0)
            paragraph.space_after = Pt(0)

            paragraph.font.name = FONT_FAMILY
            paragraph.font.size = Pt(
                FONT_SIZE_TESTED_PARTS_PT
            )
            paragraph.font.bold = True
            paragraph.font.color.rgb = COLOR_WHITE

    # ==========================================================
    # FILAS DE MUESTRAS
    # ==========================================================

    for row_index, sample in enumerate(
        samples,
        start=1,
    ):
        tested_part_value = "\n".join(
            value
            for value in (
                str(sample.get("sample_code") or ""),
                str(sample.get("sample_description") or ""),
            )
            if value
        )

        row_values = [
            tested_part_value,
            "",
            "",
            "",
            "",
        ]

        for column_index, value in enumerate(
            row_values
        ):
            cell = table.cell(
                row_index,
                column_index,
            )

            cell.text = value
            cell.vertical_anchor = (
                MSO_VERTICAL_ANCHOR.MIDDLE
            )

            cell.margin_left = Cm(0.12)
            cell.margin_right = Cm(0.12)
            cell.margin_top = Cm(0.05)
            cell.margin_bottom = Cm(0.05)

            text_frame = cell.text_frame
            text_frame.word_wrap = True

            for paragraph in text_frame.paragraphs:
                paragraph.alignment = PP_ALIGN.CENTER
                paragraph.space_before = Pt(0)
                paragraph.space_after = Pt(0)

                paragraph.font.name = FONT_FAMILY
                paragraph.font.size = Pt(
                    FONT_SIZE_TESTED_PARTS_PT
                )
                paragraph.font.color.rgb = COLOR_NAVY

            cell.fill.solid()

            if row_index % 2 == 0:
                cell.fill.fore_color.rgb = (
                    COLOR_ROW_ALTERNATE
                )
            else:
                cell.fill.fore_color.rgb = COLOR_WHITE


def add_profile_table(
    slide,
    headers: list[str],
    rows: list[list[Any]],
    column_widths_cm: list[float],
    table_top_cm: float,
    data_row_height_cm: float = TABLE_ROW_HEIGHT_CM,
) -> float:
    """
    Añade una tabla nativa de PowerPoint y devuelve
    la coordenada vertical donde termina.
    """
    table_left_cm = 2.12
    table_width_cm = 29.63
    header_height_cm = TABLE_HEADER_HEIGHT_CM

    row_count = len(rows) + 1
    column_count = len(headers)

    table_height_cm = (
        header_height_cm
        + len(rows) * data_row_height_cm
    )

    table_shape = slide.shapes.add_table(
        row_count,
        column_count,
        Cm(table_left_cm),
        Cm(table_top_cm),
        Cm(table_width_cm),
        Cm(table_height_cm),
    )

    table = table_shape.table

    for column_index, width_cm in enumerate(
        column_widths_cm
    ):
        table.columns[column_index].width = Cm(
            width_cm
        )

    table.rows[0].height = Cm(header_height_cm)

    for row_index in range(1, row_count):
        table.rows[row_index].height = Cm(
            data_row_height_cm
        )

    # ==========================================================
    # CABECERA
    # ==========================================================

    for column_index, header in enumerate(headers):
        cell = table.cell(0, column_index)
        cell.text = header

        cell.vertical_anchor = (
            MSO_VERTICAL_ANCHOR.MIDDLE
        )

        cell.fill.solid()
        cell.fill.fore_color.rgb = COLOR_NAVY

        cell.margin_left = Cm(0.08)
        cell.margin_right = Cm(0.08)
        cell.margin_top = Cm(0.04)
        cell.margin_bottom = Cm(0.04)

        text_frame = cell.text_frame
        text_frame.word_wrap = True

        for paragraph in text_frame.paragraphs:
            paragraph.alignment = PP_ALIGN.CENTER
            paragraph.space_before = Pt(0)
            paragraph.space_after = Pt(0)

            paragraph.font.name = FONT_FAMILY
            paragraph.font.size = Pt(
                FONT_SIZE_TABLE_HEADER_PT
            )
            paragraph.font.bold = True
            paragraph.font.color.rgb = COLOR_WHITE

    # ==========================================================
    # CONTENIDO
    # ==========================================================

    for row_index, row_values in enumerate(
        rows,
        start=1,
    ):
        for column_index, value in enumerate(
            row_values
        ):
            cell = table.cell(
                row_index,
                column_index,
            )

            cell.text = (
                ""
                if value is None
                else str(value)
            )

            cell.vertical_anchor = (
                MSO_VERTICAL_ANCHOR.MIDDLE
            )

            cell.margin_left = Cm(0.08)
            cell.margin_right = Cm(0.08)
            cell.margin_top = Cm(0.04)
            cell.margin_bottom = Cm(0.04)

            text_frame = cell.text_frame
            text_frame.word_wrap = True

            for paragraph in text_frame.paragraphs:
                paragraph.alignment = PP_ALIGN.CENTER
                paragraph.space_before = Pt(0)
                paragraph.space_after = Pt(0)

                paragraph.font.name = FONT_FAMILY
                paragraph.font.size = Pt(
                    FONT_SIZE_TABLE_BODY_PT
                )
                paragraph.font.color.rgb = COLOR_NAVY

            cell.fill.solid()

            if row_index % 2 == 0:
                cell.fill.fore_color.rgb = (
                    COLOR_ROW_ALTERNATE
                )
            else:
                cell.fill.fore_color.rgb = COLOR_WHITE

    return table_top_cm + table_height_cm


def build_climatic_profile_rows(
    profile_points: list[dict[str, Any]],
) -> list[list[Any]]:
    def display_optional_value(value):
        return "-" if value is None or value == "" else value

    return [
        [
            point.get("sequence"),
            point.get("time_min"),
            point.get("duration_min"),
            point.get("temperature_c"),
            display_optional_value(
                point.get("humidity_percent")
            ),
            display_optional_value(
                point.get("actuation")
            ),
        ]
        for point in profile_points
    ]


def build_dut_profile_rows(
    profile_points: list[dict[str, Any]],
) -> list[list[Any]]:
    return [
        [
            point.get("sequence"),
            point.get("time_ms"),
            point.get("dut_position_percent"),
        ]
        for point in profile_points
    ]
