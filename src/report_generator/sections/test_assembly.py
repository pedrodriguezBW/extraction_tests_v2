from __future__ import annotations

from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.enum.text import MSO_ANCHOR
from pptx.util import Cm, Pt

from ..metadata import resolve_setup_images
from ..powerpoint.images import add_contained_image
from ..powerpoint.layout import (
    add_assembly_data_row,
    add_section_header,
)
from ..powerpoint.navigation import (
    chunk_items,
    clear_test_assembly_content,
    create_continuation_slide,
    find_slide_in_section,
)
from ..powerpoint.styles import (
    COLOR_GRAY,
    COLOR_NAVY,
    CONTENT_LEFT_CM,
    CONTENT_WIDTH_CM,
    FONT_FAMILY,
    FONT_SIZE_COMPACT_LABEL_PT,
    FONT_SIZE_LABEL_PT,
    IMAGE_COLUMN_GAP_CM,
    TWO_COLUMN_IMAGE_HEIGHT_CM,
    TWO_COLUMN_IMAGE_WIDTH_CM,
)


def add_equipment_column_headers(
    slide,
    top_cm: float,
) -> None:
    """
    Añade las cabeceras de las columnas de equipamiento.

    Esta función se utiliza tanto en la primera diapositiva
    como en las diapositivas de continuación.
    """
    equipment_label_box = slide.shapes.add_textbox(
        Cm(CONTENT_LEFT_CM),
        Cm(top_cm),
        Cm(19.00),
        Cm(0.40),
    )

    equipment_label_frame = equipment_label_box.text_frame
    equipment_label_frame.clear()
    equipment_label_frame.margin_left = 0
    equipment_label_frame.margin_right = 0
    equipment_label_frame.margin_top = 0
    equipment_label_frame.margin_bottom = 0

    equipment_label_paragraph = (
        equipment_label_frame.paragraphs[0]
    )

    equipment_label_paragraph.text = "EQUIPMENT"
    equipment_label_paragraph.font.name = FONT_FAMILY
    equipment_label_paragraph.font.size = Pt(
        FONT_SIZE_COMPACT_LABEL_PT
    )
    equipment_label_paragraph.font.bold = True
    equipment_label_paragraph.font.color.rgb = COLOR_GRAY

    code_label_box = slide.shapes.add_textbox(
        Cm(22.00),
        Cm(top_cm),
        Cm(9.75),
        Cm(0.40),
    )

    code_label_frame = code_label_box.text_frame
    code_label_frame.clear()
    code_label_frame.margin_left = 0
    code_label_frame.margin_right = 0
    code_label_frame.margin_top = 0
    code_label_frame.margin_bottom = 0

    code_label_paragraph = code_label_frame.paragraphs[0]

    code_label_paragraph.text = "EQUIPMENT CODE"
    code_label_paragraph.font.name = FONT_FAMILY
    code_label_paragraph.font.size = Pt(
        FONT_SIZE_COMPACT_LABEL_PT
    )
    code_label_paragraph.font.bold = True
    code_label_paragraph.font.color.rgb = COLOR_GRAY


def populate_equipment_continuation_slide(
    slide,
    equipment_items: list[dict[str, Any]],
) -> None:
    add_section_header(
        slide=slide,
        title="Additional equipment",
        left_cm=CONTENT_LEFT_CM,
        top_cm=4.25,
        width_cm=CONTENT_WIDTH_CM,
    )

    add_equipment_column_headers(
        slide=slide,
        top_cm=5.10,
    )

    first_equipment_top_cm = 5.70
    equipment_row_spacing_cm = 0.72

    for equipment_index, equipment_data in enumerate(
        equipment_items
    ):
        equipment_name = str(
            equipment_data.get("equipment_used") or ""
        )

        equipment_code = str(
            equipment_data.get("equipment_code") or ""
        )

        add_assembly_data_row(
            slide=slide,
            name=equipment_name,
            code=equipment_code,
            top_cm=(
                first_equipment_top_cm
                + equipment_index
                * equipment_row_spacing_cm
            ),
        )


def populate_test_assembly_images(
    presentation_path: Path,
    test_root: Path,
    metadata: dict[str, Any],
) -> None:
    presentation = Presentation(presentation_path)

    slide = find_slide_in_section(
        presentation=presentation,
        section_title="TEST A",
        slide_title="2. Test Assembly",
    )

    clear_test_assembly_content(slide)

    # ==========================================================
    # 1. FOTOGRAFÍAS DEL SETUP
    # ==========================================================

    # Las rutas se resuelven dentro de la carpeta del ensayo. Las
    # referencias que no existen se omiten sin detener la generación.
    resolved_images, _ = resolve_setup_images(
        metadata,
        Path(test_root),
    )

    first_slide_images = resolved_images[:2]

    image_top_cm = 3.70
    image_width_cm = TWO_COLUMN_IMAGE_WIDTH_CM
    image_height_cm = TWO_COLUMN_IMAGE_HEIGHT_CM
    image_gap_cm = IMAGE_COLUMN_GAP_CM

    first_image_left_cm = CONTENT_LEFT_CM

    second_image_left_cm = (
        first_image_left_cm
        + image_width_cm
        + image_gap_cm
    )

    if len(first_slide_images) >= 1:
        add_contained_image(
            slide=slide,
            image_path=first_slide_images[0],
            left_cm=first_image_left_cm,
            top_cm=image_top_cm,
            width_cm=image_width_cm,
            height_cm=image_height_cm,
        )

    if len(first_slide_images) >= 2:
        add_contained_image(
            slide=slide,
            image_path=first_slide_images[1],
            left_cm=second_image_left_cm,
            top_cm=image_top_cm,
            width_cm=image_width_cm,
            height_cm=image_height_cm,
        )

    # ==========================================================
    # 2. TEST FACILITY
    # ==========================================================

    climatic_chamber = str(
        metadata
        .get("test_facility", {})
        .get("climatic_chamber")
        or ""
    )

    add_section_header(
        slide=slide,
        title="Test Equipment",
        left_cm=CONTENT_LEFT_CM,
        top_cm=12.00,
        width_cm=CONTENT_WIDTH_CM,
    )

    facility_box = slide.shapes.add_textbox(
        Cm(CONTENT_LEFT_CM),
        Cm(12.70),
        Cm(CONTENT_WIDTH_CM),
        Cm(0.55),
    )

    facility_frame = facility_box.text_frame
    facility_frame.clear()
    facility_frame.word_wrap = True
    facility_frame.margin_left = 0
    facility_frame.margin_right = 0
    facility_frame.margin_top = 0
    facility_frame.margin_bottom = 0
    facility_frame.vertical_anchor = MSO_ANCHOR.TOP

    facility_paragraph = facility_frame.paragraphs[0]
    facility_paragraph.text = climatic_chamber
    facility_paragraph.font.name = FONT_FAMILY
    facility_paragraph.font.size = Pt(
        FONT_SIZE_LABEL_PT
    )
    facility_paragraph.font.color.rgb = COLOR_NAVY
    facility_paragraph.space_before = Pt(0)
    facility_paragraph.space_after = Pt(0)

    # ==========================================================
    # 3. EQUIPAMIENTO ADICIONAL
    # ==========================================================

    equipment_items = metadata.get("equipment") or []

    first_slide_equipment = equipment_items[:4]
    remaining_equipment = equipment_items[4:]

    continuation_equipment_groups = chunk_items(
        items=remaining_equipment,
        chunk_size=12,
    )

    if first_slide_equipment:
        add_section_header(
            slide=slide,
            title="Additional equipment",
            left_cm=CONTENT_LEFT_CM,
            top_cm=13.40,
            width_cm=CONTENT_WIDTH_CM,
        )

        add_equipment_column_headers(
            slide=slide,
            top_cm=14.07,
        )

        first_equipment_top_cm = 14.50
        equipment_row_spacing_cm = 0.52

        for equipment_index, equipment_data in enumerate(
            first_slide_equipment
        ):
            equipment_name = str(
                equipment_data.get("equipment_used") or ""
            )

            equipment_code = str(
                equipment_data.get("equipment_code") or ""
            )

            add_assembly_data_row(
                slide=slide,
                name=equipment_name,
                code=equipment_code,
                top_cm=(
                    first_equipment_top_cm
                    + equipment_index
                    * equipment_row_spacing_cm
                ),
            )

    # ==========================================================
    # 4. DIAPOSITIVAS DE CONTINUACIÓN
    # ==========================================================

    previous_slide = slide

    for equipment_group in continuation_equipment_groups:
        continuation_slide = create_continuation_slide(
            presentation=presentation,
            reference_slide=previous_slide,
            title="2. Test Assembly (cont.)",
        )

        populate_equipment_continuation_slide(
            slide=continuation_slide,
            equipment_items=equipment_group,
        )

        previous_slide = continuation_slide

    presentation.save(presentation_path)