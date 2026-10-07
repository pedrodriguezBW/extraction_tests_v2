from __future__ import annotations
from pathlib import Path
from typing import Any
from pptx import Presentation
from ..powerpoint.navigation import chunk_items, clear_slide_body, create_continuation_slide, find_slide_by_title
from ..powerpoint.tables import add_tested_parts_table

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

    samples_per_slide = 6

    sample_groups = chunk_items(
        items=samples,
        chunk_size=samples_per_slide,
    )

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
