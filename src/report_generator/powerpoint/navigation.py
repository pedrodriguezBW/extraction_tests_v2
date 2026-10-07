from __future__ import annotations
import re
from typing import Any
from pptx import Presentation
from pptx.enum.text import MSO_ANCHOR
from pptx.util import Cm, Pt

from .styles import (
    COLOR_NAVY,
    FONT_FAMILY,
    FONT_SIZE_FOOTER_PT,
    FONT_SIZE_SLIDE_TITLE_PT,
    FOOTER_HEIGHT_CM,
    FOOTER_NUMBER_LEFT_CM,
    FOOTER_NUMBER_WIDTH_CM,
    FOOTER_TEXT,
    FOOTER_TEXT_LEFT_CM,
    FOOTER_TEXT_WIDTH_CM,
    FOOTER_TOP_CM,
    SLIDE_TITLE_HEIGHT_CM,
    SLIDE_TITLE_LEFT_CM,
    SLIDE_TITLE_TOP_CM,
    SLIDE_TITLE_WIDTH_CM,
)


def normalize_slide_text(text: str) -> str:
    return " ".join(
        text.replace("\xa0", " ").split()
    ).casefold()

def find_slide_in_section(
    presentation: Presentation,
    section_title: str,
    slide_title: str,
):
    normalized_section_title = normalize_slide_text(section_title)
    normalized_slide_title = normalize_slide_text(slide_title)

    section_start_index = None

    # Buscamos TEST A únicamente como título real de diapositiva.
    for slide_index, slide in enumerate(presentation.slides):
        title_shape = slide.shapes.title

        if title_shape is None:
            continue

        current_title = normalize_slide_text(title_shape.text)

        if current_title == normalized_section_title:
            section_start_index = slide_index
            break

    if section_start_index is None:
        raise ValueError(
            f"No slide was found with the title "
            f"{section_title!r}."
        )

    # Buscamos Test Assembly después de la portada TEST A.
    for slide_index in range(
        section_start_index + 1,
        len(presentation.slides),
    ):
        slide = presentation.slides[slide_index]
        title_shape = slide.shapes.title

        if title_shape is None:
            continue

        current_title = normalize_slide_text(title_shape.text)

        if current_title == normalized_slide_title:
            return slide

        # Paramos si alcanzamos otra portada TEST B, TEST C, etc.
        is_another_test_section = (
            re.fullmatch(r"test\s+\S+", current_title) is not None
            and current_title != normalized_section_title
        )

        if is_another_test_section:
            raise ValueError(
                f"The slide {slide_title!r} was not found in section "
                f"{section_title!r}."
            )

    raise ValueError(
        f"The slide {slide_title!r} was not found in section "
        f"{section_title!r}."
    )

def find_slide_by_title(
    presentation: Presentation,
    expected_title: str,
):
    normalized_expected_title = expected_title.strip().casefold()

    for slide in presentation.slides:
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue

            shape_text = shape.text.strip().casefold()

            if shape_text == normalized_expected_title:
                return slide

    raise ValueError(
        f"No slide was found with the title "
        f"{expected_title!r}."
    )

def remove_shape(shape) -> None:
    shape_element = shape._element
    shape_element.getparent().remove(shape_element)

def clear_slide_body(slide, expected_title: str,) -> None:
    """
    Elimina el contenido propio de una diapositiva y conserva:
    - El título indicado.
    - El texto 'Highly Confidential'.
    - El número de diapositiva.
    - Los elementos no editables procedentes del patrón.
    """
    normalized_expected_title = normalize_slide_text(
        expected_title
    )

    for shape in list(slide.shapes):
        # Solo eliminamos elementos existentes en la diapositiva.
        # Los elementos del patrón no aparecen en slide.shapes.
        if shape.has_text_frame:
            shape_text = shape.text.strip()
            normalized_shape_text = normalize_slide_text(
                shape_text
            )

            if normalized_shape_text == normalized_expected_title:
                continue

            if normalized_shape_text == "highly confidential":
                continue

            if shape_text.isdigit():
                continue

        remove_shape(shape)

    apply_slide_title_style(
        slide=slide,
        expected_title=expected_title,
    )

    apply_slide_footer_style(
        slide=slide,
    )

def clear_test_assembly_content(slide) -> None:
    preserved_texts = {
        "2. test assembly",
        "highly confidential",
    }

    for shape in list(slide.shapes):
        if not shape.has_text_frame:
            continue

        shape_text = shape.text.strip()
        normalized_text = shape_text.casefold()

        if normalized_text in preserved_texts:
            continue

        if shape_text.isdigit():
            continue

        remove_shape(shape)

    apply_slide_title_style(
        slide=slide,
        expected_title="2. Test Assembly",
    )

    apply_slide_footer_style(
        slide=slide,
    )



def chunk_items(
    items: list[dict[str, Any]],
    chunk_size: int,
) -> list[list[dict[str, Any]]]:
    return [
        items[index:index + chunk_size]
        for index in range(0, len(items), chunk_size)
    ]

def add_continuation_slide_frame(
    slide,
    title: str,
    slide_number: int,
) -> None:
    # Título
    title_box = slide.shapes.add_textbox(
        Cm(SLIDE_TITLE_LEFT_CM),
        Cm(SLIDE_TITLE_TOP_CM),
        Cm(SLIDE_TITLE_WIDTH_CM),
        Cm(SLIDE_TITLE_HEIGHT_CM),
    )

    title_frame = title_box.text_frame
    title_frame.clear()
    title_frame.margin_left = 0
    title_frame.margin_right = 0
    title_frame.margin_top = 0
    title_frame.margin_bottom = 0
    title_frame.vertical_anchor = MSO_ANCHOR.MIDDLE

    title_paragraph = title_frame.paragraphs[0]
    title_paragraph.text = title
    apply_slide_title_style(
        slide=slide,
        expected_title=title,
    )

    title_paragraph.font.name = FONT_FAMILY
    title_paragraph.font.size = Pt(
        FONT_SIZE_SLIDE_TITLE_PT
    )
    title_paragraph.font.color.rgb = COLOR_NAVY

    # Número de diapositiva
    number_box = slide.shapes.add_textbox(
        Cm(FOOTER_NUMBER_LEFT_CM),
        Cm(FOOTER_TOP_CM),
        Cm(FOOTER_NUMBER_WIDTH_CM),
        Cm(FOOTER_HEIGHT_CM),
    )

    number_frame = number_box.text_frame
    number_frame.clear()
    number_frame.margin_left = 0
    number_frame.margin_right = 0
    number_frame.margin_top = 0
    number_frame.margin_bottom = 0

    number_paragraph = number_frame.paragraphs[0]
    number_paragraph.text = str(slide_number)
    number_paragraph.font.name = FONT_FAMILY
    number_paragraph.font.size = Pt(
        FONT_SIZE_FOOTER_PT
    )
    number_paragraph.font.color.rgb = COLOR_NAVY

    # Confidencialidad
    footer_box = slide.shapes.add_textbox(
        Cm(FOOTER_TEXT_LEFT_CM),
        Cm(FOOTER_TOP_CM),
        Cm(FOOTER_TEXT_WIDTH_CM),
        Cm(FOOTER_HEIGHT_CM),
    )

    footer_frame = footer_box.text_frame
    footer_frame.clear()
    footer_frame.margin_left = 0
    footer_frame.margin_right = 0
    footer_frame.margin_top = 0
    footer_frame.margin_bottom = 0

    footer_paragraph = footer_frame.paragraphs[0]
    footer_paragraph.text = FOOTER_TEXT
    footer_paragraph.font.name = FONT_FAMILY
    footer_paragraph.font.size = Pt(
        FONT_SIZE_FOOTER_PT
    )
    footer_paragraph.font.color.rgb = COLOR_NAVY

    apply_slide_title_style(
        slide=slide,
        expected_title=title,
    )

    apply_slide_footer_style(
        slide=slide,
    )


def apply_slide_title_style(
    slide,
    expected_title=None,
):
    """
    Aplica el estilo global al título de una diapositiva.

    Funciona tanto con placeholders heredados de la plantilla
    como con cuadros de texto creados dinámicamente.
    """
    normalized_expected_title = None

    if expected_title:
        normalized_expected_title = normalize_slide_text(
            expected_title
        )

    title_shape = slide.shapes.title

    if title_shape is None:
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue

            shape_text = normalize_slide_text(
                shape.text
            )

            if (
                normalized_expected_title is None
                or shape_text == normalized_expected_title
            ):
                title_shape = shape
                break

    if title_shape is None:
        raise ValueError(
            "The slide title was not found."
        )

    for paragraph in title_shape.text_frame.paragraphs:
        paragraph.font.name = FONT_FAMILY
        paragraph.font.size = Pt(
            FONT_SIZE_SLIDE_TITLE_PT
        )
        paragraph.font.color.rgb = COLOR_NAVY

        # Algunos placeholders conservan el formato en los runs.
        # Lo aplicamos también ahí para sobrescribir el estilo
        # heredado de la plantilla.
        for run in paragraph.runs:
            run.font.name = FONT_FAMILY
            run.font.size = Pt(
                FONT_SIZE_SLIDE_TITLE_PT
            )
            run.font.color.rgb = COLOR_NAVY


def create_continuation_slide(
    presentation: Presentation,
    reference_slide,
    title: str,
):
    reference_index = None

    for slide_index, candidate_slide in enumerate(
        presentation.slides
    ):
        if candidate_slide.part is reference_slide.part:
            reference_index = slide_index
            break

    if reference_index is None:
        raise ValueError(
            "The reference slide could not be located."
        )

    continuation_slide = presentation.slides.add_slide(
        reference_slide.slide_layout
    )

    # Eliminamos todos los placeholders creados automáticamente.
    # El logo y la línea inferior pertenecen al patrón y se conservan.
    for shape in list(continuation_slide.shapes):
        if shape.is_placeholder:
            remove_shape(shape)

    slide_id_list = presentation.slides._sldIdLst
    continuation_slide_id = slide_id_list[-1]

    slide_id_list.remove(continuation_slide_id)
    slide_id_list.insert(
        reference_index + 1,
        continuation_slide_id,
    )

    # La numeración de PowerPoint comienza en 1.
    continuation_slide_number = reference_index + 2

    add_continuation_slide_frame(
        slide=continuation_slide,
        title=title,
        slide_number=continuation_slide_number,
    )

    return continuation_slide


def apply_slide_footer_style(slide):
    """
    Aplica el estilo global al pie y al número de diapositiva.

    Funciona con:
    - Placeholders conservados de la plantilla.
    - Cuadros de texto creados en las continuaciones.
    """
    normalized_footer_text = normalize_slide_text(
        FOOTER_TEXT
    )

    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue

        shape_text = shape.text.strip()
        normalized_shape_text = normalize_slide_text(
            shape_text
        )

        is_footer_text = (
            normalized_shape_text
            == normalized_footer_text
        )

        is_slide_number = (
            shape_text.isdigit()
            and shape.top >= Cm(15.0)
        )

        if not is_footer_text and not is_slide_number:
            continue

        if is_footer_text:
            shape.left = Cm(FOOTER_TEXT_LEFT_CM)
            shape.top = Cm(FOOTER_TOP_CM)
            shape.width = Cm(FOOTER_TEXT_WIDTH_CM)
            shape.height = Cm(FOOTER_HEIGHT_CM)

        if is_slide_number:
            shape.left = Cm(FOOTER_NUMBER_LEFT_CM)
            shape.top = Cm(FOOTER_TOP_CM)
            shape.width = Cm(FOOTER_NUMBER_WIDTH_CM)
            shape.height = Cm(FOOTER_HEIGHT_CM)

        text_frame = shape.text_frame
        text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE

        for paragraph in text_frame.paragraphs:
            paragraph.font.name = FONT_FAMILY
            paragraph.font.size = Pt(
                FONT_SIZE_FOOTER_PT
            )
            paragraph.font.color.rgb = COLOR_NAVY

            for run in paragraph.runs:
                run.font.name = FONT_FAMILY
                run.font.size = Pt(
                    FONT_SIZE_FOOTER_PT
                )
                run.font.color.rgb = COLOR_NAVY
