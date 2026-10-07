from __future__ import annotations

from pathlib import Path

from pptx import Presentation

from ..powerpoint.images import (
    add_contained_image,
    find_test_result_charts,
)
from ..powerpoint.navigation import (
    chunk_items,
    clear_slide_body,
    create_continuation_slide,
    find_slide_in_section,
)
from ..powerpoint.styles import (
    CONTENT_LEFT_CM,
    CONTENT_WIDTH_CM,
    RESULT_HORIZONTAL_GAP_CM,
    RESULT_VERTICAL_GAP_CM,
    SINGLE_CHART_HEIGHT_CM,
    SINGLE_CHART_WIDTH_CM,
)


def add_test_result_image(
    slide,
    image_path,
    left_cm,
    top_cm,
    width_cm,
    height_cm,
):
    """
    Inserta una imagen completa dentro del área asignada.

    La imagen mantiene su proporción y no se recorta.
    """
    add_contained_image(
        slide=slide,
        image_path=image_path,
        left_cm=left_cm,
        top_cm=top_cm,
        width_cm=width_cm,
        height_cm=height_cm,
    )


def populate_test_results_slide(
    slide,
    image_paths,
):
    """
    Distribuye entre una y cuatro gráficas.

    Reglas:
    - Una gráfica: centrada.
    - Dos gráficas: una en cada mitad.
    - Tres gráficas: cuadrícula 2 x 2 con un hueco vacío.
    - Cuatro gráficas: cuadrícula 2 x 2 completa.
    """
    image_count = len(image_paths)

    if image_count == 0:
        return

    content_top_cm = 4.10
    content_height_cm = 12.30

    # ==========================================================
    # UNA IMAGEN
    # ==========================================================

    if image_count == 1:
        image_area_width_cm = SINGLE_CHART_WIDTH_CM
        image_area_height_cm = SINGLE_CHART_HEIGHT_CM

        image_left_cm = (
            CONTENT_LEFT_CM
            + (
                CONTENT_WIDTH_CM
                - image_area_width_cm
            ) / 2
        )

        image_top_cm = (
            content_top_cm
            + (
                content_height_cm
                - image_area_height_cm
            ) / 2
        )

        add_test_result_image(
            slide=slide,
            image_path=image_paths[0],
            left_cm=image_left_cm,
            top_cm=image_top_cm,
            width_cm=image_area_width_cm,
            height_cm=image_area_height_cm,
        )

        return

    # ==========================================================
    # DOS IMÁGENES
    # ==========================================================

    if image_count == 2:
        image_area_width_cm = (
            CONTENT_WIDTH_CM
            - RESULT_HORIZONTAL_GAP_CM
        ) / 2

        image_area_height_cm = 8.50

        image_top_cm = (
            content_top_cm
            + (
                content_height_cm
                - image_area_height_cm
            ) / 2
        )

        first_image_left_cm = CONTENT_LEFT_CM

        second_image_left_cm = (
            CONTENT_LEFT_CM
            + image_area_width_cm
            + RESULT_HORIZONTAL_GAP_CM
        )

        add_test_result_image(
            slide=slide,
            image_path=image_paths[0],
            left_cm=first_image_left_cm,
            top_cm=image_top_cm,
            width_cm=image_area_width_cm,
            height_cm=image_area_height_cm,
        )

        add_test_result_image(
            slide=slide,
            image_path=image_paths[1],
            left_cm=second_image_left_cm,
            top_cm=image_top_cm,
            width_cm=image_area_width_cm,
            height_cm=image_area_height_cm,
        )

        return

    # ==========================================================
    # TRES O CUATRO IMÁGENES
    # ==========================================================

    image_area_width_cm = (
        CONTENT_WIDTH_CM
        - RESULT_HORIZONTAL_GAP_CM
    ) / 2

    image_area_height_cm = (
        content_height_cm
        - RESULT_VERTICAL_GAP_CM
    ) / 2

    first_column_left_cm = CONTENT_LEFT_CM

    second_column_left_cm = (
        CONTENT_LEFT_CM
        + image_area_width_cm
        + RESULT_HORIZONTAL_GAP_CM
    )

    first_row_top_cm = content_top_cm

    second_row_top_cm = (
        content_top_cm
        + image_area_height_cm
        + RESULT_VERTICAL_GAP_CM
    )

    image_positions = [
        (
            first_column_left_cm,
            first_row_top_cm,
        ),
        (
            second_column_left_cm,
            first_row_top_cm,
        ),
        (
            first_column_left_cm,
            second_row_top_cm,
        ),
        (
            second_column_left_cm,
            second_row_top_cm,
        ),
    ]

    for image_index in range(len(image_paths)):
        image_path = image_paths[image_index]

        image_left_cm = image_positions[
            image_index
        ][0]

        image_top_cm = image_positions[
            image_index
        ][1]

        add_test_result_image(
            slide=slide,
            image_path=image_path,
            left_cm=image_left_cm,
            top_cm=image_top_cm,
            width_cm=image_area_width_cm,
            height_cm=image_area_height_cm,
        )


def populate_test_results(
    presentation_path,
    test_root,
):
    """
    Genera las diapositivas de resultados de TEST A.

    Las imágenes se agrupan de cuatro en cuatro. Se crean
    continuaciones automáticamente cuando son necesarias.
    """
    presentation_path = Path(presentation_path)
    test_root = Path(test_root)

    presentation = Presentation(
        presentation_path
    )

    first_results_slide = find_slide_in_section(
        presentation=presentation,
        section_title="TEST A",
        slide_title="4. Test Results",
    )

    clear_slide_body(
        slide=first_results_slide,
        expected_title="4. Test Results",
    )

    result_charts = find_test_result_charts(
        test_root=test_root,
    )

    if not result_charts:
        presentation.save(
            presentation_path
        )
        return

    chart_groups = chunk_items(
        items=result_charts,
        chunk_size=4,
    )

    populate_test_results_slide(
        slide=first_results_slide,
        image_paths=chart_groups[0],
    )

    previous_slide = first_results_slide

    # Se utiliza range para evitar que el editor de la
    # conversación introduzca caracteres en el slicing.
    for group_index in range(
        1,
        len(chart_groups),
    ):
        chart_group = chart_groups[
            group_index
        ]

        continuation_slide = (
            create_continuation_slide(
                presentation=presentation,
                reference_slide=previous_slide,
                title="4. Test Results (cont.)",
            )
        )

        populate_test_results_slide(
            slide=continuation_slide,
            image_paths=chart_group,
        )

        previous_slide = continuation_slide

    presentation.save(
        presentation_path
    )