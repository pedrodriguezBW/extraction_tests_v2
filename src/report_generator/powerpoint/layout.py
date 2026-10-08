from __future__ import annotations
from datetime import datetime
from typing import Any
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Cm, Pt
from .styles import (
    COLOR_CYAN,
    COLOR_GRAY,
    COLOR_NAVY,
    FONT_FAMILY,
    FONT_SIZE_LABEL_PT,
    FONT_SIZE_SECTION_TITLE_PT,
    FONT_SIZE_VALUE_PT,
    LABEL_HEIGHT_CM,
    SECTION_HEADER_HEIGHT_CM,
    SECTION_UNDERLINE_HEIGHT_CM,
    SECTION_UNDERLINE_OFFSET_CM,
)


def format_date_for_presentation(date_value: str | None) -> str:
    if not date_value:
        return ""

    parsed_date = datetime.strptime(date_value, "%Y-%m-%d")
    return parsed_date.strftime("%d/%m/%Y")

def add_label_and_value(
    slide,
    label: str,
    value: str,
    left_cm: float,
    top_cm: float,
    width_cm: float,
    height_cm: float = 1.6,
) -> None:
    label_box = slide.shapes.add_textbox(
        Cm(left_cm),
        Cm(top_cm),
        Cm(width_cm),
        Cm(0.45),
    )

    label_frame = label_box.text_frame
    label_frame.clear()
    label_frame.margin_left = 0
    label_frame.margin_right = 0
    label_frame.margin_top = 0
    label_frame.margin_bottom = 0

    label_paragraph = label_frame.paragraphs[0]
    label_paragraph.text = label.upper()
    label_paragraph.font.name = FONT_FAMILY
    label_paragraph.font.size = Pt(FONT_SIZE_LABEL_PT)
    label_paragraph.font.bold = True
    label_paragraph.font.color.rgb = COLOR_GRAY

    value_box = slide.shapes.add_textbox(
        Cm(left_cm),
        Cm(top_cm + 0.48),
        Cm(width_cm),
        Cm(height_cm - 0.48),
    )

    value_frame = value_box.text_frame
    value_frame.clear()
    value_frame.margin_left = 0
    value_frame.margin_right = 0
    value_frame.margin_top = 0
    value_frame.margin_bottom = 0
    value_frame.vertical_anchor = MSO_ANCHOR.TOP
    value_frame.word_wrap = True

    value_paragraph = value_frame.paragraphs[0]
    value_paragraph.text = value
    value_paragraph.font.name = FONT_FAMILY
    value_paragraph.font.size = Pt(FONT_SIZE_VALUE_PT)
    value_paragraph.font.color.rgb = COLOR_NAVY

def add_section_header(
    slide,
    title: str,
    left_cm: float,
    top_cm: float,
    width_cm: float,
) -> None:
    title_box = slide.shapes.add_textbox(
        Cm(left_cm),
        Cm(top_cm),
        Cm(width_cm),
        Cm(SECTION_HEADER_HEIGHT_CM),
    )

    title_frame = title_box.text_frame
    title_frame.clear()
    title_frame.margin_left = 0
    title_frame.margin_right = 0
    title_frame.margin_top = 0
    title_frame.margin_bottom = 0

    title_paragraph = title_frame.paragraphs[0]
    title_paragraph.text = title.upper()
    title_paragraph.font.name = FONT_FAMILY
    title_paragraph.font.size = Pt(FONT_SIZE_SECTION_TITLE_PT)
    title_paragraph.font.bold = True
    title_paragraph.font.color.rgb = COLOR_NAVY

    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Cm(left_cm),
        Cm(top_cm + SECTION_UNDERLINE_OFFSET_CM),
        Cm(width_cm),
        Cm(SECTION_UNDERLINE_HEIGHT_CM),
    )

    line.fill.solid()
    line.fill.fore_color.rgb = COLOR_CYAN
    line.line.fill.background()

def add_assembly_data_row(
    slide,
    name: str,
    code: str,
    top_cm: float,
) -> None:
    name_box = slide.shapes.add_textbox(
        Cm(2.12),
        Cm(top_cm),
        Cm(19.00),
        Cm(SECTION_HEADER_HEIGHT_CM),
    )

    name_frame = name_box.text_frame
    name_frame.clear()
    name_frame.word_wrap = True
    name_frame.margin_left = 0
    name_frame.margin_right = 0
    name_frame.margin_top = 0
    name_frame.margin_bottom = 0
    name_frame.vertical_anchor = MSO_ANCHOR.TOP

    name_paragraph = name_frame.paragraphs[0]
    name_paragraph.text = name
    name_paragraph.font.name = FONT_FAMILY
    name_paragraph.font.size = Pt(FONT_SIZE_LABEL_PT)
    name_paragraph.font.color.rgb = COLOR_NAVY
    name_paragraph.space_before = Pt(0)
    name_paragraph.space_after = Pt(0)

    code_box = slide.shapes.add_textbox(
        Cm(22.00),
        Cm(top_cm),
        Cm(9.75),
        Cm(SECTION_HEADER_HEIGHT_CM),
    )

    code_frame = code_box.text_frame
    code_frame.clear()
    code_frame.word_wrap = False
    code_frame.margin_left = 0
    code_frame.margin_right = 0
    code_frame.margin_top = 0
    code_frame.margin_bottom = 0
    code_frame.vertical_anchor = MSO_ANCHOR.TOP

    code_paragraph = code_frame.paragraphs[0]
    code_paragraph.text = code
    code_paragraph.font.name = FONT_FAMILY
    code_paragraph.font.size = Pt(FONT_SIZE_LABEL_PT)
    code_paragraph.font.color.rgb = COLOR_NAVY
    code_paragraph.space_before = Pt(0)
    code_paragraph.space_after = Pt(0)

def add_test_input_parameter(
    slide,
    label: str,
    value: str,
    left_cm: float,
    top_cm: float,
    width_cm: float,
) -> None:
    label_box = slide.shapes.add_textbox(
        Cm(left_cm),
        Cm(top_cm),
        Cm(width_cm),
        Cm(0.45),
    )

    label_frame = label_box.text_frame
    label_frame.clear()
    label_frame.margin_left = 0
    label_frame.margin_right = 0
    label_frame.margin_top = 0
    label_frame.margin_bottom = 0

    label_paragraph = label_frame.paragraphs[0]
    label_paragraph.text = label.upper()
    label_paragraph.font.name = FONT_FAMILY
    label_paragraph.font.size = Pt(FONT_SIZE_LABEL_PT)
    label_paragraph.font.bold = True
    label_paragraph.font.color.rgb = COLOR_GRAY

    value_box = slide.shapes.add_textbox(
        Cm(left_cm),
        Cm(top_cm + 0.50),
        Cm(width_cm),
        Cm(0.85),
    )

    value_frame = value_box.text_frame
    value_frame.clear()
    value_frame.word_wrap = True
    value_frame.margin_left = 0
    value_frame.margin_right = 0
    value_frame.margin_top = 0
    value_frame.margin_bottom = 0
    value_frame.vertical_anchor = MSO_ANCHOR.TOP

    value_paragraph = value_frame.paragraphs[0]
    value_paragraph.text = value
    value_paragraph.font.name = FONT_FAMILY
    value_paragraph.font.size = Pt(FONT_SIZE_VALUE_PT)
    value_paragraph.font.color.rgb = COLOR_NAVY

def format_test_input_value(
    value: Any,
    unit: str = "",
) -> str:
    if value is None:
        return ""

    if unit:
        return f"{value} {unit}"

    return str(value)
