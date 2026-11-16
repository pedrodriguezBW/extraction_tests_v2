from __future__ import annotations

from pathlib import Path
import textwrap
from typing import Any

from pptx import Presentation
from pptx.enum.text import MSO_AUTO_SIZE, MSO_ANCHOR, PP_ALIGN
from pptx.util import Cm, Pt
from config import LABORATORY_NAME
from ..standards import description_values

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
    create_continuation_slide,
)
from ..powerpoint.styles import (
    COLOR_NAVY,
    CONTENT_LEFT_CM,
    CONTENT_WIDTH_CM,
    FONT_FAMILY,
    FONT_SIZE_PROCEDURE_MAX_PT,
    FONT_SIZE_PROCEDURE_MIN_PT,
    FONT_SIZE_VALUE_PT,
    FOOTER_TOP_CM,
    TEST_DESCRIPTION_CONTACTS_SECTION_TOP_CM,
    TEST_DESCRIPTION_FIRST_ROW_TOP_CM,
    TEST_DESCRIPTION_IDENTIFICATION_TOP_CM,
    TEST_DESCRIPTION_SECOND_ROW_TOP_CM,
)


def text_height_cm(text: str, width_cm: float, font_size: float) -> float:
    """Reserva altura para el ajuste de palabras, saltos explícitos y márgenes."""
    characters = max(1, int((width_cm - 0.2) * 48 / font_size))
    wrapper = textwrap.TextWrapper(width=characters, replace_whitespace=False,
                                   drop_whitespace=False, expand_tabs=False)
    lines = sum(max(1, len(wrapper.wrap(line))) for line in text.split("\n"))
    return lines * font_size * 0.047 + 0.16


def procedure_page(text: str, height_cm: float, font_size: float) -> tuple[str, str]:
    """Divide solo cuando se llena la página, conservando exactamente el texto."""
    if text_height_cm(text, CONTENT_WIDTH_CM, font_size) <= height_cm:
        return text, ""
    lower, upper = 0, len(text)
    while lower < upper:
        middle = (lower + upper + 1) // 2
        if text_height_cm(text[:middle], CONTENT_WIDTH_CM, font_size) <= height_cm:
            lower = middle
        else:
            upper = middle - 1
    if lower == 0:
        raise ValueError("No queda espacio para una línea del procedimiento")
    # Preferimos un párrafo completo y, después, un límite de palabra.
    paragraph_end = text.rfind("\n", 0, lower)
    word_end = max(text.rfind(" ", 0, lower), paragraph_end)
    boundary = paragraph_end + 1 if paragraph_end >= lower // 2 else word_end + 1
    if boundary > 0:
        lower = boundary
    return text[:lower], text[lower:]


def add_procedure_text(slide, text: str, top_cm: float, font_size: float) -> float:
    """Dibuja un fragmento del procedimiento con altura ajustada a su contenido."""
    height = text_height_cm(text, CONTENT_WIDTH_CM, font_size)
    box = slide.shapes.add_textbox(Cm(CONTENT_LEFT_CM), Cm(top_cm),
                                   Cm(CONTENT_WIDTH_CM), Cm(height))
    frame = box.text_frame
    frame.word_wrap = True
    frame.auto_size = MSO_AUTO_SIZE.NONE
    frame.vertical_anchor = MSO_ANCHOR.TOP
    frame.margin_left = frame.margin_right = Cm(0.10)
    frame.margin_top = frame.margin_bottom = Cm(0.08)
    paragraph = frame.paragraphs[0]
    paragraph.text = text
    paragraph.alignment = PP_ALIGN.LEFT
    paragraph.space_before = paragraph.space_after = Pt(0)
    paragraph.line_spacing = 1.0
    paragraph.font.name = FONT_FAMILY
    paragraph.font.size = Pt(font_size)
    paragraph.font.color.rgb = COLOR_NAVY
    return top_cm + height


def populate_procedure_and_contacts(presentation, slide, procedure, requester, technician, header_top):
    """Mantiene el orden: identificación, procedimiento completo y contactos."""
    bottom = min(presentation.slide_height / Cm(1), FOOTER_TOP_CM) - 0.45
    text_top = header_top + 0.80
    available = bottom - text_top
    # Se utiliza primero todo el espacio disponible, sin encoger para los contactos.
    font_size = float(FONT_SIZE_PROCEDURE_MIN_PT)
    for size in range(int(FONT_SIZE_PROCEDURE_MAX_PT), int(FONT_SIZE_PROCEDURE_MIN_PT) - 1, -1):
        if text_height_cm(procedure, CONTENT_WIDTH_CM, size) <= available:
            font_size = float(size)
            break
    current_slide = slide
    remaining = procedure
    first_page = True
    while True:
        add_section_header(current_slide, "Test procedure" if first_page else "Test procedure (continued)",
                           CONTENT_LEFT_CM, header_top, CONTENT_WIDTH_CM)
        fragment, remaining = procedure_page(remaining, bottom - text_top, font_size)
        procedure_end = add_procedure_text(current_slide, fragment, text_top, font_size)
        if not remaining:
            break
        current_slide = create_continuation_slide(presentation, current_slide, "1. Test Description (cont.)")
        first_page = False
        header_top, text_top = 4.25, 5.05

    contacts_top = procedure_end + 0.50
    if first_page:
        contacts_top = max(contacts_top, TEST_DESCRIPTION_CONTACTS_SECTION_TOP_CM)
    contacts_height = 2.10
    if contacts_top + contacts_height > bottom:
        current_slide = create_continuation_slide(presentation, current_slide, "1. Test Description (cont.)")
        contacts_top = 4.25
    add_section_header(current_slide, "Test contacts", CONTENT_LEFT_CM, contacts_top, CONTENT_WIDTH_CM)
    for label, value, left, width in (("Requester", requester, CONTENT_LEFT_CM, 13.50),
                                      ("Test technician", technician, 17.50, 14.25)):
        add_label_and_value(current_slide, label, value, left, contacts_top + 0.90, width, 1.20)


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
    report_inputs: dict | None = None,
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

    test_type, standard = description_values(metadata, report_inputs or {})
    fields_top = TEST_DESCRIPTION_SECOND_ROW_TOP_CM + 1.55
    fields = (
        ("Laboratory", LABORATORY_NAME, CONTENT_LEFT_CM, 4.0),
        ("Test type", test_type, 7.0, 14.0),
        ("Standard", standard, 22.0, 9.75),
    )
    fields_height = max(1.5, *(0.48 + text_height_cm(str(value), width, FONT_SIZE_VALUE_PT)
                               for _, value, _, width in fields))
    for label, value, left, width in fields:
        add_label_and_value(slide, label, str(value), left, fields_top, width, fields_height)

    populate_procedure_and_contacts(
        presentation, slide, procedure, requester, technician,
        header_top=fields_top + fields_height + 0.50,
    )
    presentation.save(presentation_path)
