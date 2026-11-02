from __future__ import annotations

from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.util import Cm

from ..powerpoint.navigation import (
    clear_slide_body,
    create_continuation_slide,
    find_slide_by_title,
)
from ..powerpoint.styles import FOOTER_TOP_CM
from ..powerpoint.tables import (
    TESTED_PARTS_BASE_ROW_HEIGHT_CM,
    TESTED_PARTS_HEADER_HEIGHT_CM,
    TESTED_PARTS_TABLE_BOTTOM_GAP_CM,
    TESTED_PARTS_TABLE_TOP_CM,
    add_tested_parts_table,
    tested_part_row_height_cm,
)

def populate_tested_parts(
    presentation_path: Path,
    metadata: dict[str, Any],
) -> None:
    presentation = Presentation(presentation_path)

    slide = find_slide_by_title(
        presentation=presentation,
        expected_title="2. Tested Parts",
    )

    clear_slide_body(
        slide=slide,
        expected_title="2. Tested Parts",
    )

    samples = metadata.get("samples") or []

    slide_height_cm = presentation.slide_height / Cm(1)
    table_bottom_cm = min(
        slide_height_cm,
        FOOTER_TOP_CM - TESTED_PARTS_TABLE_BOTTOM_GAP_CM,
    )
    max_table_height_cm = table_bottom_cm - TESTED_PARTS_TABLE_TOP_CM
    max_data_height_cm = (
        max_table_height_cm - TESTED_PARTS_HEADER_HEIGHT_CM
    )
    if max_data_height_cm < TESTED_PARTS_BASE_ROW_HEIGHT_CM:
        raise ValueError(
            "The slide does not have enough vertical space for a Tested Parts table."
        )

    sample_groups: list[list[dict[str, Any]]] = []
    current_group: list[dict[str, Any]] = []
    current_group_height_cm = 0.0

    for sample in samples:
        row_height_cm = tested_part_row_height_cm(sample)
        if row_height_cm > max_data_height_cm:
            sample_code = str(sample.get("sample_code") or "")
            raise ValueError(
                "Tested Part "
                f"{sample_code!r} requires more vertical space than one slide can provide."
            )

        if (
            current_group
            and current_group_height_cm + row_height_cm > max_data_height_cm
        ):
            sample_groups.append(current_group)
            current_group = []
            current_group_height_cm = 0.0

        current_group.append(sample)
        current_group_height_cm += row_height_cm

    if current_group:
        sample_groups.append(current_group)

    # Si no existen muestras, dejamos una tabla vacía editable.
    if not sample_groups:
        sample_groups = [[]]

    # Primera tabla en la diapositiva original.
    add_tested_parts_table(
        slide=slide,
        samples=sample_groups[0],
    )

    previous_slide = slide

    # Continuaciones para las muestras restantes.
    for sample_group in sample_groups[1:]:
        continuation_slide = create_continuation_slide(
            presentation=presentation,
            reference_slide=previous_slide,
            title="2. Tested Parts (cont.)",
        )

        add_tested_parts_table(
            slide=continuation_slide,
            samples=sample_group,
        )

        previous_slide = continuation_slide

    presentation.save(presentation_path)
