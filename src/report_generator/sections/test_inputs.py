from __future__ import annotations

from pathlib import Path
from typing import Any

from pptx import Presentation

from ..powerpoint.charts import (
    add_climatic_profile_chart,
    add_dut_profile_chart,
    has_climatic_chart_data,
    has_dut_chart_data,
)
from ..powerpoint.layout import (
    add_section_header,
    add_test_input_parameter,
    format_test_input_value,
)
from ..powerpoint.navigation import (
    clear_slide_body,
    create_continuation_slide,
    find_slide_in_section,
)
from ..powerpoint.styles import (
    CONTENT_LEFT_CM,
    CONTENT_WIDTH_CM,
    IMAGE_COLUMN_GAP_CM,
    PROFILE_CHARTS_SECTION_TOP_CM,
    PROFILE_CHARTS_TOP_CM,
    PROFILE_SECTION_BOTTOM_GAP_CM,
    PROFILE_SECTION_TO_TABLE_GAP_CM,
    PROFILE_SLIDE_CONTENT_BOTTOM_CM,
    PROFILE_SLIDE_CONTENT_TOP_CM,
    SINGLE_CHART_HEIGHT_CM,
    SINGLE_CHART_WIDTH_CM,
    SINGLE_PROFILE_CHART_TOP_CM,
    TABLE_HEADER_HEIGHT_CM,
    TABLE_ROW_HEIGHT_CM,
    TEST_INPUTS_DUT_FIRST_ROW_TOP_CM,
    TEST_INPUTS_DUT_SECOND_ROW_TOP_CM,
    TEST_INPUTS_DUT_SECTION_TOP_CM,
    TEST_INPUTS_DUT_THIRD_ROW_TOP_CM,
    TEST_INPUTS_FIRST_ROW_TOP_CM,
    TEST_INPUTS_PARAMETERS_TOP_CM,
    TEST_INPUTS_SECOND_ROW_TOP_CM,
    TWO_COLUMN_IMAGE_HEIGHT_CM,
    TWO_COLUMN_IMAGE_WIDTH_CM,
)
from ..powerpoint.tables import (
    add_profile_table,
    build_climatic_profile_rows,
    build_dut_profile_rows,
)

def add_test_input_profile_slides(
    presentation: Presentation,
    reference_slide,
    climatic_profile_points: list[dict[str, Any]],
    dut_profile_points: list[dict[str, Any]],
):
    slide_top_cm = PROFILE_SLIDE_CONTENT_TOP_CM
    slide_bottom_cm = PROFILE_SLIDE_CONTENT_BOTTOM_CM

    section_header_height_cm = 0.75
    section_to_table_gap_cm = (
        PROFILE_SECTION_TO_TABLE_GAP_CM
    )
    section_bottom_gap_cm = (
        PROFILE_SECTION_BOTTOM_GAP_CM
    )

    table_header_height_cm = TABLE_HEADER_HEIGHT_CM
    data_row_height_cm = TABLE_ROW_HEIGHT_CM

    climatic_rows = build_climatic_profile_rows(
        climatic_profile_points
    )

    dut_rows = build_dut_profile_rows(
        dut_profile_points
    )

    climatic_headers = [
        "POINT",
        "TIME [min]",
        "DURATION [min]",
        "TEMPERATURE [°C]",
        "HUMIDITY [%]",
        "ACTUATION",
    ]

    climatic_widths_cm = [
        2.50,
        4.50,
        4.80,
        6.00,
        5.50,
        6.33,
    ]

    dut_headers = [
        "POINT",
        "TIME [ms]",
        "DUT POSITION [%]",
    ]

    dut_widths_cm = [
        4.00,
        12.00,
        13.63,
    ]

    previous_slide = reference_slide
    current_slide = None
    current_y_cm = slide_top_cm

    def create_profile_slide():
        nonlocal previous_slide
        nonlocal current_slide
        nonlocal current_y_cm

        current_slide = create_continuation_slide(
            presentation=presentation,
            reference_slide=previous_slide,
            title="3. Test Inputs (cont.)",
        )

        previous_slide = current_slide
        current_y_cm = slide_top_cm

    def available_rows() -> int:
        required_before_rows_cm = (
            section_header_height_cm
            + section_to_table_gap_cm
            + table_header_height_cm
        )

        available_height_cm = (
            slide_bottom_cm
            - current_y_cm
            - required_before_rows_cm
        )

        return max(
            0,
            int(
                available_height_cm
                // data_row_height_cm
            ),
        )

    def add_paginated_profile(
        section_title: str,
        headers: list[str],
        rows: list[list[Any]],
        column_widths_cm: list[float],
    ) -> None:
        nonlocal current_slide
        nonlocal current_y_cm

        remaining_rows = list(rows)
        first_fragment = True

        while remaining_rows:
            if current_slide is None:
                create_profile_slide()

            rows_that_fit = available_rows()

            if rows_that_fit <= 0:
                create_profile_slide()
                rows_that_fit = available_rows()

            current_rows = remaining_rows[:rows_that_fit]
            remaining_rows = remaining_rows[rows_that_fit:]

            displayed_section_title = section_title

            if not first_fragment:
                displayed_section_title = (
                    f"{section_title} (cont.)"
                )

            add_section_header(
                slide=current_slide,
                title=displayed_section_title,
                left_cm=CONTENT_LEFT_CM,
                top_cm=current_y_cm,
                width_cm=CONTENT_WIDTH_CM,
            )

            table_top_cm = (
                current_y_cm
                + section_header_height_cm
                + section_to_table_gap_cm
            )

            table_bottom_cm = add_profile_table(
                slide=current_slide,
                headers=headers,
                rows=current_rows,
                column_widths_cm=column_widths_cm,
                table_top_cm=table_top_cm,
                data_row_height_cm=data_row_height_cm,
            )

            current_y_cm = (
                table_bottom_cm
                + section_bottom_gap_cm
            )

            first_fragment = False

            if remaining_rows:
                create_profile_slide()

    # El perfil climático se añade primero.
    if climatic_rows:
        add_paginated_profile(
            section_title="Climatic profile",
            headers=climatic_headers,
            rows=climatic_rows,
            column_widths_cm=climatic_widths_cm,
        )

    # El perfil DUT continúa debajo si queda espacio.
    if dut_rows:
        add_paginated_profile(
            section_title="DUT profile",
            headers=dut_headers,
            rows=dut_rows,
            column_widths_cm=dut_widths_cm,
        )

    return previous_slide

def has_dut_input_content(
    dut_inputs: dict[str, Any],
) -> bool:
    """
    Indica si existe información DUT relevante para mostrar.

    El valor profile_required=False, por sí solo, no provoca
    la creación de la sección DUT.
    """
    fields_to_check = (
        "component",
        "controller_equipment",
        "dataset_filename",
        "voltage_v",
        "expected_current_a",
        "other_comments",
    )

    has_general_data = any(
        dut_inputs.get(field) not in (None, "")
        for field in fields_to_check
    )

    controller_codes = (
        dut_inputs.get("controller_codes")
        or []
    )

    profile_points = (
        dut_inputs.get("profile_points")
        or []
    )

    return (
        dut_inputs.get("profile_required") is True
        or has_general_data
        or bool(controller_codes)
        or bool(profile_points)
    )

def add_test_input_charts_slide(
    presentation: Presentation,
    reference_slide,
    climatic_profile_points: list[dict[str, Any]],
    dut_profile_points: list[dict[str, Any]],
):
    climatic_chart_available = has_climatic_chart_data(
        climatic_profile_points
    )
    dut_chart_available = has_dut_chart_data(
        dut_profile_points
    )

    # No creamos una diapositiva vacía si no existe ninguna
    # gráfica que deba mostrarse.
    if (
        not climatic_chart_available
        and not dut_chart_available
    ):
        return reference_slide

    chart_slide = create_continuation_slide(
        presentation=presentation,
        reference_slide=reference_slide,
        title="3. Test Inputs (cont.)",
    )

    add_section_header(
        slide=chart_slide,
        title="Input profiles",
        left_cm=CONTENT_LEFT_CM,
        top_cm=PROFILE_CHARTS_SECTION_TOP_CM,
        width_cm=CONTENT_WIDTH_CM,
    )

    # ==========================================================
    # DOS GRÁFICAS
    # ==========================================================

    if climatic_chart_available and dut_chart_available:
        chart_area_top_cm = PROFILE_CHARTS_TOP_CM
        chart_area_width_cm = TWO_COLUMN_IMAGE_WIDTH_CM
        chart_area_height_cm = TWO_COLUMN_IMAGE_HEIGHT_CM
        chart_area_gap_cm = IMAGE_COLUMN_GAP_CM

        climatic_chart_left_cm = CONTENT_LEFT_CM

        dut_chart_left_cm = (
            climatic_chart_left_cm
            + chart_area_width_cm
            + chart_area_gap_cm
        )

        add_climatic_profile_chart(
            slide=chart_slide,
            profile_points=climatic_profile_points,
            left_cm=climatic_chart_left_cm,
            top_cm=chart_area_top_cm,
            width_cm=chart_area_width_cm,
            height_cm=chart_area_height_cm,
        )

        add_dut_profile_chart(
            slide=chart_slide,
            profile_points=dut_profile_points,
            left_cm=dut_chart_left_cm,
            top_cm=chart_area_top_cm,
            width_cm=chart_area_width_cm,
            height_cm=chart_area_height_cm,
        )

    # ==========================================================
    # UNA SOLA GRÁFICA
    # ==========================================================

    else:
        if climatic_chart_available:
            add_single_chart = add_climatic_profile_chart
            single_profile_points = climatic_profile_points
        else:
            add_single_chart = add_dut_profile_chart
            single_profile_points = dut_profile_points

        # Área estándar más contenida para una sola gráfica.
        # La imagen se encaja completa dentro de ella manteniendo
        # su proporción original.
        chart_area_width_cm = SINGLE_CHART_WIDTH_CM
        chart_area_height_cm = SINGLE_CHART_HEIGHT_CM

        content_left_cm = CONTENT_LEFT_CM
        content_width_cm = CONTENT_WIDTH_CM

        chart_area_left_cm = (
            content_left_cm
            + (
                content_width_cm
                - chart_area_width_cm
            ) / 2
        )

        chart_area_top_cm = SINGLE_PROFILE_CHART_TOP_CM

        add_single_chart(
            slide=chart_slide,
            profile_points=single_profile_points,
            left_cm=chart_area_left_cm,
            top_cm=chart_area_top_cm,
            width_cm=chart_area_width_cm,
            height_cm=chart_area_height_cm,
        )

    return chart_slide

def populate_test_inputs(
    presentation_path: Path,
    metadata: dict[str, Any],
) -> None:
    presentation = Presentation(presentation_path)

    slide = find_slide_in_section(
        presentation=presentation,
        section_title="TEST A",
        slide_title="3. Test Inputs",
    )

    clear_slide_body(
        slide=slide,
        expected_title="3. Test Inputs",
    )

    # ==========================================================
    # 1. CLIMATIC TEST PARAMETERS
    # ==========================================================

    climatic_inputs = metadata.get("climatic_inputs") or {}

    program_name = str(
        climatic_inputs.get("program_name") or ""
    )

    minimum_temperature = format_test_input_value(
        climatic_inputs.get("minimum_temperature_c"),
        "°C",
    )

    maximum_temperature = format_test_input_value(
        climatic_inputs.get("maximum_temperature_c"),
        "°C",
    )

    cycle_duration = format_test_input_value(
        climatic_inputs.get("cycle_duration_h"),
        "h",
    )

    number_of_cycles = format_test_input_value(
        climatic_inputs.get("number_of_cycles"),
    )

    total_duration = format_test_input_value(
        climatic_inputs.get("total_duration_h"),
        "h",
    )

    add_section_header(
        slide=slide,
        title="Climatic test parameters",
        left_cm=CONTENT_LEFT_CM,
        top_cm=TEST_INPUTS_PARAMETERS_TOP_CM,
        width_cm=CONTENT_WIDTH_CM,
    )

    # Primera fila climática.
    add_test_input_parameter(
        slide=slide,
        label="Program name",
        value=program_name,
        left_cm=CONTENT_LEFT_CM,
        top_cm=TEST_INPUTS_FIRST_ROW_TOP_CM,
        width_cm=11.00,
    )

    add_test_input_parameter(
        slide=slide,
        label="Minimum temperature",
        value=minimum_temperature,
        left_cm=14.00,
        top_cm=TEST_INPUTS_FIRST_ROW_TOP_CM,
        width_cm=7.50,
    )

    add_test_input_parameter(
        slide=slide,
        label="Maximum temperature",
        value=maximum_temperature,
        left_cm=23.00,
        top_cm=TEST_INPUTS_FIRST_ROW_TOP_CM,
        width_cm=8.75,
    )

    # Segunda fila climática.
    add_test_input_parameter(
        slide=slide,
        label="Cycle duration",
        value=cycle_duration,
        left_cm=CONTENT_LEFT_CM,
        top_cm=TEST_INPUTS_SECOND_ROW_TOP_CM,
        width_cm=8.50,
    )

    add_test_input_parameter(
        slide=slide,
        label="Number of cycles",
        value=number_of_cycles,
        left_cm=12.00,
        top_cm=TEST_INPUTS_SECOND_ROW_TOP_CM,
        width_cm=8.50,
    )

    add_test_input_parameter(
        slide=slide,
        label="Total duration",
        value=total_duration,
        left_cm=22.00,
        top_cm=TEST_INPUTS_SECOND_ROW_TOP_CM,
        width_cm=9.75,
    )

    # ==========================================================
    # 2. DUT CONTROLLER INPUTS
    # ==========================================================

    dut_inputs = metadata.get(
        "dut_controller_inputs"
    ) or {}

    dut_profile_points = (
        dut_inputs.get("profile_points")
        or []
    )

    controller_codes = (
        dut_inputs.get("controller_codes")
        or []
    )

    has_dut_content = has_dut_input_content(dut_inputs)

    if has_dut_content:
        profile_required = dut_inputs.get(
            "profile_required"
        )

        if profile_required is True:
            profile_required_text = "YES"
        elif profile_required is False:
            profile_required_text = "NO"
        else:
            profile_required_text = ""

        component = str(
            dut_inputs.get("component") or ""
        )

        controller_equipment = str(
            dut_inputs.get("controller_equipment")
            or ""
        )

        dataset_filename = str(
            dut_inputs.get("dataset_filename")
            or ""
        )

        voltage = format_test_input_value(
            dut_inputs.get("voltage_v"),
            "V",
        )

        expected_current = format_test_input_value(
            dut_inputs.get("expected_current_a"),
            "A",
        )

        other_comments = str(
            dut_inputs.get("other_comments") or ""
        )

        controller_codes_text = ", ".join(
            str(controller_code)
            for controller_code in controller_codes
            if (
                controller_code is not None
                and str(controller_code).strip()
            )
        )

        add_section_header(
            slide=slide,
            title="DUT controller inputs",
            left_cm=CONTENT_LEFT_CM,
            top_cm=TEST_INPUTS_DUT_SECTION_TOP_CM,
            width_cm=CONTENT_WIDTH_CM,
        )

        # Primera fila DUT.
        add_test_input_parameter(
            slide=slide,
            label="DUT profile?",
            value=profile_required_text,
            left_cm=CONTENT_LEFT_CM,
            top_cm=TEST_INPUTS_DUT_FIRST_ROW_TOP_CM,
            width_cm=7.25,
        )

        add_test_input_parameter(
            slide=slide,
            label="Component",
            value=component,
            left_cm=10.10,
            top_cm=TEST_INPUTS_DUT_FIRST_ROW_TOP_CM,
            width_cm=9.60,
        )

        add_test_input_parameter(
            slide=slide,
            label="Controller equipment",
            value=controller_equipment,
            left_cm=20.50,
            top_cm=TEST_INPUTS_DUT_FIRST_ROW_TOP_CM,
            width_cm=11.25,
        )

        # Segunda fila DUT.
        add_test_input_parameter(
            slide=slide,
            label="Dataset filename",
            value=dataset_filename,
            left_cm=CONTENT_LEFT_CM,
            top_cm=TEST_INPUTS_DUT_SECOND_ROW_TOP_CM,
            width_cm=11.50,
        )

        add_test_input_parameter(
            slide=slide,
            label="Voltage",
            value=voltage,
            left_cm=14.40,
            top_cm=TEST_INPUTS_DUT_SECOND_ROW_TOP_CM,
            width_cm=7.50,
        )

        add_test_input_parameter(
            slide=slide,
            label="Expected current",
            value=expected_current,
            left_cm=22.70,
            top_cm=TEST_INPUTS_DUT_SECOND_ROW_TOP_CM,
            width_cm=9.05,
        )

        # Tercera fila DUT.
        add_test_input_parameter(
            slide=slide,
            label="Controller codes",
            value=controller_codes_text,
            left_cm=CONTENT_LEFT_CM,
            top_cm=TEST_INPUTS_DUT_THIRD_ROW_TOP_CM,
            width_cm=12.00,
        )

        add_test_input_parameter(
            slide=slide,
            label="Other comments",
            value=other_comments,
            left_cm=14.90,
            top_cm=TEST_INPUTS_DUT_THIRD_ROW_TOP_CM,
            width_cm=16.85,
        )

    # ==========================================================
    # 3. TABLAS PAGINADAS DE LOS PERFILES
    # ==========================================================

    climatic_profile_points = (
        climatic_inputs.get("profile_points")
        or []
    )

    last_profile_slide = add_test_input_profile_slides(
        presentation=presentation,
        reference_slide=slide,
        climatic_profile_points=(
            climatic_profile_points
        ),
        dut_profile_points=dut_profile_points,
    )

    add_test_input_charts_slide(
        presentation=presentation,
        reference_slide=last_profile_slide,
        climatic_profile_points=climatic_profile_points,
        dut_profile_points=dut_profile_points,
    )

    presentation.save(presentation_path)
