from __future__ import annotations

from pathlib import Path
from typing import Any
from math import ceil

from pptx import Presentation
from pptx.enum.text import MSO_ANCHOR
from pptx.util import Cm, Pt
from ..standards import chamber_description
from ..powerpoint.tables import add_profile_table

from ..evidence_photos import ASSEMBLY_MAX_PHOTOS, EVIDENCE_PHOTOS_PER_SLIDE
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

#: Parte superior de las fotografías en la diapositiva principal.
ASSEMBLY_FIRST_PHOTOS_TOP_CM = 3.70

#: Parte superior de las fotografías en la continuación (bajo su cabecera).
ASSEMBLY_CONTINUATION_PHOTOS_TOP_CM = 5.10

#: Altura máxima de las fotografías en la continuación, por encima del pie.
ASSEMBLY_CONTINUATION_PHOTOS_HEIGHT_CM = 11.00


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


def add_assembly_photo_row(
    slide,
    image_paths: list[Path],
    top_cm: float,
    height_cm: float,
) -> None:
    """Coloca hasta dos fotografías en dos columnas, sin deformarlas."""
    if len(image_paths) > EVIDENCE_PHOTOS_PER_SLIDE:
        raise ValueError(
            "A Test Assembly slide holds at most "
            f"{EVIDENCE_PHOTOS_PER_SLIDE} photos."
        )

    for column, image_path in enumerate(image_paths):
        add_contained_image(
            slide=slide,
            image_path=image_path,
            left_cm=(
                CONTENT_LEFT_CM
                + column
                * (TWO_COLUMN_IMAGE_WIDTH_CM + IMAGE_COLUMN_GAP_CM)
            ),
            top_cm=top_cm,
            width_cm=TWO_COLUMN_IMAGE_WIDTH_CM,
            height_cm=height_cm,
        )


def populate_assembly_photos_continuation_slide(
    slide,
    image_paths: list[Path],
) -> None:
    """Diapositiva de continuación con las fotografías 3 y 4 del montaje."""
    add_section_header(
        slide=slide,
        title="Test assembly photos",
        left_cm=CONTENT_LEFT_CM,
        top_cm=4.25,
        width_cm=CONTENT_WIDTH_CM,
    )

    add_assembly_photo_row(
        slide=slide,
        image_paths=image_paths,
        top_cm=ASSEMBLY_CONTINUATION_PHOTOS_TOP_CM,
        height_cm=ASSEMBLY_CONTINUATION_PHOTOS_HEIGHT_CM,
    )


def populate_test_assembly_images(
    presentation_path: Path,
    metadata: dict[str, Any],
    image_paths: list[Path],
    report_inputs: dict | None = None,
) -> None:
    """Rellena ``2. Test Assembly``.

    ``image_paths`` son las fotografías seleccionadas de las evidencias
    ``initial`` (como máximo :data:`ASSEMBLY_MAX_PHOTOS`), en orden
    automático. Se colocan dos por diapositiva: las dos primeras en la
    diapositiva principal y las dos siguientes en una continuación
    ``2. Test Assembly (cont.)`` situada justo después.
    """
    presentation = Presentation(presentation_path)

    slide = find_slide_in_section(
        presentation=presentation,
        section_title="TEST A",
        slide_title="2. Test Assembly",
    )

    clear_test_assembly_content(slide)

    # ==========================================================
    # 1. INITIAL EVIDENCE PHOTOS
    # ==========================================================
    if len(image_paths) > ASSEMBLY_MAX_PHOTOS:
        raise ValueError(
            f"Test Assembly admits at most {ASSEMBLY_MAX_PHOTOS} photos; "
            f"{len(image_paths)} were received."
        )

    photo_groups = chunk_items(
        items=list(image_paths),
        chunk_size=EVIDENCE_PHOTOS_PER_SLIDE,
    )

    if photo_groups:
        add_assembly_photo_row(
            slide=slide,
            image_paths=photo_groups[0],
            top_cm=ASSEMBLY_FIRST_PHOTOS_TOP_CM,
            height_cm=TWO_COLUMN_IMAGE_HEIGHT_CM,
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

    # Fotografías 3 y 4: diapositiva propia, justo después de la primera.
    for photo_group in photo_groups[1:]:
        photo_slide = create_continuation_slide(
            presentation=presentation,
            reference_slide=previous_slide,
            title="2. Test Assembly (cont.)",
        )

        populate_assembly_photos_continuation_slide(
            slide=photo_slide,
            image_paths=photo_group,
        )

        previous_slide = photo_slide

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

    # Se reutilizan las continuaciones para no reducir las fotografías.
    points = (report_inputs or {}).get("measurement_points", [])
    functions = {"specimen": "Specimen", "air": "Air", "control": "Control"}
    groups = [[]]
    heights = [[]]
    for point in points:
        # Reserva espacio según el texto más largo, sin reducir la fuente.
        lines = max(sum(max(1, ceil(len(line) / width)) for line in str(point.get(key) or "—").splitlines())
                    for key, width in (("channel", 30), ("location", 30), ("sensor_type", 19)))
        height = max(0.85, 0.56 * lines + 0.2)
        capacity = 7.0 if len(groups) == 1 else 10.8
        if groups[-1] and sum(heights[-1]) + height > capacity:
            groups.append([])
            heights.append([])
        groups[-1].append(point)
        heights[-1].append(height)
    for index, group in enumerate(groups):
        details = create_continuation_slide(
            presentation=presentation, reference_slide=previous_slide,
            title="2. Test Assembly (cont.)",
        )
        top = 4.25
        if index == 0:
            top = add_profile_table(details, ["Chamber", "Chamber type"],
                                    [[climatic_chamber or "—", chamber_description(climatic_chamber)]],
                                    [12.0, 17.63], top, data_row_height_cm=1.1) + 0.6
        add_section_header(details, "Measurement points", CONTENT_LEFT_CM, top, CONTENT_WIDTH_CM)
        rows = [[point.get(key) or "—" for key in ("channel", "location", "sensor_type")]
                + [functions.get(point.get("function"), "—")] for point in group]
        add_profile_table(details, ["Channel", "Location", "Sensor type", "Function"],
                          rows or [["—"] * 4], [9.0, 9.0, 6.0, 5.63], top + 0.8,
                          data_row_height_cm=0.85, row_heights_cm=heights[index] or [0.85])
        previous_slide = details

    presentation.save(presentation_path)
