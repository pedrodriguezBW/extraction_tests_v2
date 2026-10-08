"""Visual constants shared by the PowerPoint report generator.

This module contains presentation-wide style tokens only. It must not
contain section-specific rendering logic.
"""

from pptx.dml.color import RGBColor


# -----------------------------------------------------------------------------
# Typography
# -----------------------------------------------------------------------------

FONT_FAMILY = "Arial"
MIN_GENERATED_FONT_SIZE_PT = 12

FONT_SIZE_SLIDE_TITLE_PT = 32
FONT_SIZE_SECTION_TITLE_PT = 14
FONT_SIZE_LABEL_PT = 12
FONT_SIZE_VALUE_PT = 16
FONT_SIZE_FOOTER_PT = 10
FONT_SIZE_COMPACT_LABEL_PT = 12

FONT_SIZE_TABLE_HEADER_PT = 14
FONT_SIZE_TABLE_BODY_PT = 14
FONT_SIZE_TESTED_PARTS_PT = 18
FONT_SIZE_CHART_TITLE_PT = 17
FONT_SIZE_CHART_AXIS_PT = 13
FONT_SIZE_CHART_TICK_PT = 12
FONT_SIZE_CHART_LEGEND_PT = 12


# -----------------------------------------------------------------------------
# Colours
# -----------------------------------------------------------------------------

COLOR_NAVY = RGBColor(5, 23, 40)
COLOR_GRAY = RGBColor(99, 100, 102)
COLOR_CYAN = RGBColor(0, 174, 199)
COLOR_ROW_ALTERNATE = RGBColor(240, 243, 245)
COLOR_WHITE = RGBColor(255, 255, 255)


# -----------------------------------------------------------------------------
# Global slide geometry
# -----------------------------------------------------------------------------

CONTENT_LEFT_CM = 2.12
CONTENT_WIDTH_CM = 29.63
CONTENT_RIGHT_CM = CONTENT_LEFT_CM + CONTENT_WIDTH_CM

SLIDE_TITLE_LEFT_CM = 2.12
SLIDE_TITLE_TOP_CM = 1.85
SLIDE_TITLE_WIDTH_CM = 29.63
SLIDE_TITLE_HEIGHT_CM = 2.10

FOOTER_NUMBER_LEFT_CM = 2.12
FOOTER_NUMBER_WIDTH_CM = 1.27
FOOTER_TEXT_LEFT_CM = 3.40
FOOTER_TEXT_WIDTH_CM = 12.70
FOOTER_TOP_CM = 17.25
FOOTER_HEIGHT_CM = 0.51
FOOTER_TEXT = "Highly Confidential"


# -----------------------------------------------------------------------------
# Shared spacing and dimensions
# -----------------------------------------------------------------------------

SECTION_HEADER_HEIGHT_CM = 0.55
SECTION_UNDERLINE_OFFSET_CM = 0.58
SECTION_UNDERLINE_HEIGHT_CM = 0.06

LABEL_HEIGHT_CM = 0.45
LABEL_TO_VALUE_GAP_CM = 0.03

TABLE_HEADER_HEIGHT_CM = 0.90
TABLE_ROW_HEIGHT_CM = 0.90

IMAGE_COLUMN_GAP_CM = 0.93
RESULT_HORIZONTAL_GAP_CM = 0.80
RESULT_VERTICAL_GAP_CM = 0.55


# -----------------------------------------------------------------------------
# Reusable image areas
# -----------------------------------------------------------------------------

TWO_COLUMN_IMAGE_WIDTH_CM = 14.35
TWO_COLUMN_IMAGE_HEIGHT_CM = TWO_COLUMN_IMAGE_WIDTH_CM * 9 / 16

SINGLE_CHART_WIDTH_CM = 20.00
SINGLE_CHART_HEIGHT_CM = 10.00

# -----------------------------------------------------------------------------
# Test Inputs
# -----------------------------------------------------------------------------

TEST_INPUTS_PARAMETERS_TOP_CM = 4.10
TEST_INPUTS_FIRST_ROW_TOP_CM = 5.05
TEST_INPUTS_SECOND_ROW_TOP_CM = 7.25

TEST_INPUTS_DUT_SECTION_TOP_CM = 9.05
TEST_INPUTS_DUT_FIRST_ROW_TOP_CM = 10.00
TEST_INPUTS_DUT_SECOND_ROW_TOP_CM = 11.95
TEST_INPUTS_DUT_THIRD_ROW_TOP_CM = 13.90

PROFILE_SLIDE_CONTENT_TOP_CM = 4.15
PROFILE_SLIDE_CONTENT_BOTTOM_CM = 16.60
PROFILE_SECTION_TO_TABLE_GAP_CM = 0.15
PROFILE_SECTION_BOTTOM_GAP_CM = 0.45

PROFILE_CHARTS_SECTION_TOP_CM = 4.05
PROFILE_CHARTS_TOP_CM = 5.15

SINGLE_PROFILE_CHART_TOP_CM = 5.00

# -----------------------------------------------------------------------------
# Test Description
# -----------------------------------------------------------------------------

TEST_DESCRIPTION_IDENTIFICATION_TOP_CM = 4.15
TEST_DESCRIPTION_FIRST_ROW_TOP_CM = 4.90
TEST_DESCRIPTION_SECOND_ROW_TOP_CM = 6.45

TEST_DESCRIPTION_PROCEDURE_SECTION_TOP_CM = 7.90
TEST_DESCRIPTION_PROCEDURE_TOP_CM = 8.70
TEST_DESCRIPTION_PROCEDURE_HEIGHT_CM = 4.45

TEST_DESCRIPTION_CONTACTS_SECTION_TOP_CM = 13.85
TEST_DESCRIPTION_CONTACTS_ROW_TOP_CM = 14.75

FONT_SIZE_PROCEDURE_MAX_PT = 18
FONT_SIZE_PROCEDURE_MIN_PT = 12
