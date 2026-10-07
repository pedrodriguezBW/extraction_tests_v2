from __future__ import annotations

from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.enum.text import MSO_AUTO_SIZE, MSO_ANCHOR, PP_ALIGN
from pptx.util import Cm, Pt

from ..powerpoint.layout import (
    add_label_and_value,
    add_section_header,
    format_date_for_presentation,
)
from ..powerpoint.navigation import (
    apply_slide_footer_style,
    apply_slide_title_style,
    find_slide_by_title,
    remove_shape,
)
from ..powerpoint.styles import (
    COLOR_NAVY,
    CONTENT_LEFT_CM,
    CONTENT_WIDTH_CM,
    FONT_FAMILY,
    FONT_SIZE_PROCEDURE_MAX_PT,
    FONT_SIZE_PROCEDURE_MIN_PT,
    TEST_DESCRIPTION_CONTACTS_ROW_TOP_CM,
    TEST_DESCRIPTION_CONTACTS_SECTION_TOP_CM,
    TEST_DESCRIPTION_FIRST_ROW_TOP_CM,
    TEST_DESCRIPTION_IDENTIFICATION_TOP_CM,
    TEST_DESCRIPTION_PROCEDURE_HEIGHT_CM,
    TEST_DESCRIPTION_PROCEDURE_SECTION_TOP_CM,
    TEST_DESCRIPTION_PROCEDURE_TOP_CM,
    TEST_DESCRIPTION_SECOND_ROW_TOP_CM,
)


def calculate_procedure_font_size(
    text: str,
    box_width_cm: float,
    box_height_cm: float,
    maximum_size_pt: float = FONT_SIZE_PROCEDURE_MAX_PT,
    minimum_size_pt: float = FONT_SIZE_PROCEDURE_MIN_PT,
) -> float:
    """
    Estima un tamaño de fuente que mantenga el texto dentro
    del cuadro reservado para el procedimiento.

    No modifica, resume ni interpreta el contenido.
    """
    if not text:
        return maximum_size_pt

    normalized_lines = text.splitlines() or [""]

    for font_size in range(
        int(maximum_size_pt),
        int(minimum_size_pt) - 1,
        -1,
    ):
        characters_per_line = max(
            1,
            int(
                (box_width_cm * 30)
                / font_size
            ),
        )

        estimated_lines = 0

        for line in normalized_lines:
            line_length = max(
                1,
                len(line),
            )

            estimated_lines += max(
                1,
                (
                    line_length
                    + characters_per_line
                    - 1
                )
                // characters_per_line,
            )

        line_height_cm = font_size * 0.047

        required_height_cm = (
            estimated_lines
            * line_height_cm
        )

        if required_height_cm <= box_height_cm:
            return float(font_size)

    return minimum_size_pt


def populate_test_description(
    presentation_path: Path,
    metadata: dict[str, Any],
) -> None:
    presentation = Presentation(
        presentation_path
    )

    slide = find_slide_by_title(
        presentation=presentation,
        expected_title="1. Test Description",
    )

    # Eliminamos únicamente el placeholder provisional.
    content_placeholder_found = False

    for shape in list(slide.shapes):
        if (
            shape.has_text_frame
            and shape.text.strip() == "Xyz"
        ):
            remove_shape(shape)

            content_placeholder_found = True
            break

    if not content_placeholder_found:
        raise ValueError(
            "The 'Xyz' placeholder was not found on slide "
            "'1. Test Description'."
        )

    # Aplicamos los estilos globales al título y al pie
    # conservados desde la plantilla original.
    apply_slide_title_style(
        slide=slide,
        expected_title="1. Test Description",
    )

    apply_slide_footer_style(
        slide=slide,
    )

    test_data = metadata["test"]
    people_data = metadata["people"]

    test_name = str(
        test_data.get("test_name")
        or ""
    )

    customer = str(
        test_data.get("customer")
        or ""
    )

    program_number = str(
        test_data.get("program_number")
        or ""
    )

    program_description = str(
        test_data.get("program_description")
        or ""
    )

    phase = str(
        test_data.get("phase")
        or ""
    )

    procedure = str(
        test_data.get("procedure")
        or ""
    )

    start_date = format_date_for_presentation(
        test_data.get("start_date")
    )

    end_date = format_date_for_presentation(
        test_data.get("end_date")
    )

    requester = str(
        people_data
        .get("requester", {})
        .get("name")
        or ""
    )

    technician = str(
        people_data
        .get("test_technician", {})
        .get("name")
        or ""
    )

    program = " | ".join(
        value
        for value in (
            program_number,
            program_description,
        )
        if value
    )

    test_period = " – ".join(
        value
        for value in (
            start_date,
            end_date,
        )
        if value
    )

    # ==========================================================
    # 1. TEST IDENTIFICATION
    # ==========================================================

    add_section_header(
        slide=slide,
        title="Test identification",
        left_cm=CONTENT_LEFT_CM,
        top_cm=(
            TEST_DESCRIPTION_IDENTIFICATION_TOP_CM
        ),
        width_cm=CONTENT_WIDTH_CM,
    )

    add_label_and_value(
        slide=slide,
        label="Test",
        value=test_name,
        left_cm=CONTENT_LEFT_CM,
        top_cm=TEST_DESCRIPTION_FIRST_ROW_TOP_CM,
        width_cm=8.50,
        height_cm=1.10,
    )

    add_label_and_value(
        slide=slide,
        label="Customer",
        value=customer,
        left_cm=12.00,
        top_cm=TEST_DESCRIPTION_FIRST_ROW_TOP_CM,
        width_cm=8.50,
        height_cm=1.10,
    )

    add_label_and_value(
        slide=slide,
        label="Phase",
        value=phase,
        left_cm=22.00,
        top_cm=TEST_DESCRIPTION_FIRST_ROW_TOP_CM,
        width_cm=9.75,
        height_cm=1.10,
    )

    add_label_and_value(
        slide=slide,
        label="Program",
        value=program,
        left_cm=CONTENT_LEFT_CM,
        top_cm=TEST_DESCRIPTION_SECOND_ROW_TOP_CM,
        width_cm=14.00,
        height_cm=1.10,
    )

    add_label_and_value(
        slide=slide,
        label="Test period",
        value=test_period,
        left_cm=17.50,
        top_cm=TEST_DESCRIPTION_SECOND_ROW_TOP_CM,
        width_cm=14.25,
        height_cm=1.10,
    )

    # ==========================================================
    # 2. TEST PROCEDURE
    # ==========================================================

    add_section_header(
        slide=slide,
        title="Test procedure",
        left_cm=CONTENT_LEFT_CM,
        top_cm=(
            TEST_DESCRIPTION_PROCEDURE_SECTION_TOP_CM
        ),
        width_cm=CONTENT_WIDTH_CM,
    )

    procedure_box = slide.shapes.add_textbox(
        Cm(CONTENT_LEFT_CM),
        Cm(TEST_DESCRIPTION_PROCEDURE_TOP_CM),
        Cm(CONTENT_WIDTH_CM),
        Cm(TEST_DESCRIPTION_PROCEDURE_HEIGHT_CM),
    )

    procedure_frame = procedure_box.text_frame
    procedure_frame.clear()
    procedure_frame.word_wrap = True
    procedure_frame.auto_size = (
        MSO_AUTO_SIZE.NONE
    )
    procedure_frame.vertical_anchor = (
        MSO_ANCHOR.TOP
    )

    procedure_frame.margin_left = Cm(0.10)
    procedure_frame.margin_right = Cm(0.10)
    procedure_frame.margin_top = Cm(0.08)
    procedure_frame.margin_bottom = Cm(0.08)

    procedure_font_size = (
        calculate_procedure_font_size(
            text=procedure,
            box_width_cm=CONTENT_WIDTH_CM,
            box_height_cm=(
                TEST_DESCRIPTION_PROCEDURE_HEIGHT_CM
            ),
        )
    )

    procedure_paragraph = (
        procedure_frame.paragraphs[0]
    )

    procedure_paragraph.text = procedure
    procedure_paragraph.alignment = PP_ALIGN.LEFT
    procedure_paragraph.space_before = Pt(0)
    procedure_paragraph.space_after = Pt(0)
    procedure_paragraph.line_spacing = 1.0

    procedure_paragraph.font.name = FONT_FAMILY
    procedure_paragraph.font.size = Pt(
        procedure_font_size
    )
    procedure_paragraph.font.color.rgb = COLOR_NAVY

    # ==========================================================
    # 3. TEST CONTACTS
    # ==========================================================

    add_section_header(
        slide=slide,
        title="Test contacts",
        left_cm=CONTENT_LEFT_CM,
        top_cm=(
            TEST_DESCRIPTION_CONTACTS_SECTION_TOP_CM
        ),
        width_cm=CONTENT_WIDTH_CM,
    )

    add_label_and_value(
        slide=slide,
        label="Requester",
        value=requester,
        left_cm=CONTENT_LEFT_CM,
        top_cm=TEST_DESCRIPTION_CONTACTS_ROW_TOP_CM,
        width_cm=13.50,
        height_cm=1.20,
    )

    add_label_and_value(
        slide=slide,
        label="Test technician",
        value=technician,
        left_cm=17.50,
        top_cm=TEST_DESCRIPTION_CONTACTS_ROW_TOP_CM,
        width_cm=14.25,
        height_cm=1.20,
    )

    presentation.save(
        presentation_path
    )