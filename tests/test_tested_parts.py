import tempfile
import unittest
from pathlib import Path

from pptx import Presentation
from pptx.util import Cm, Pt

from src.report_generator.powerpoint.styles import FOOTER_TOP_CM
from src.report_generator.powerpoint.tables import tested_part_row_height_cm
from src.report_generator.sections.tested_parts import populate_tested_parts


class TestedPartsPaginationTests(unittest.TestCase):
    def _create_presentation(self, path: Path) -> None:
        presentation = Presentation()
        presentation.slide_width = Cm(33.87)
        presentation.slide_height = Cm(19.05)
        slide = presentation.slides.add_slide(
            presentation.slide_layouts[6]
        )
        title = slide.shapes.add_textbox(
            Cm(2.12),
            Cm(1.85),
            Cm(29.63),
            Cm(2.10),
        )
        title.text = "2. Tested Parts"
        presentation.save(path)

    def test_long_descriptions_are_sized_and_paginated_without_overflow(self):
        samples = [
            {
                "sample_code": f"PART-{index}",
                "sample_description": (
                    f"Description {index} " + "long description " * 10
                ),
            }
            for index in range(1, 4)
        ]
        expected_text = [
            f"{sample['sample_code']}\n{sample['sample_description']}"
            for sample in samples
        ]

        with tempfile.TemporaryDirectory() as directory:
            presentation_path = Path(directory) / "report.pptx"
            self._create_presentation(presentation_path)

            populate_tested_parts(
                presentation_path=presentation_path,
                metadata={"samples": samples},
            )

            presentation = Presentation(presentation_path)
            self.assertEqual(len(presentation.slides), 3)

            actual_text = []
            for slide in presentation.slides:
                table_shape = next(
                    shape for shape in slide.shapes if shape.has_table
                )
                table = table_shape.table
                self.assertEqual(len(table.rows), 2)

                table_bottom_cm = (
                    table_shape.top + table_shape.height
                ) / Cm(1)
                self.assertLessEqual(
                    table_bottom_cm,
                    FOOTER_TOP_CM - 0.44,
                )
                self.assertGreater(table.rows[1].height, Cm(1.65))
                self.assertEqual(
                    table.cell(1, 0)
                    .text_frame.paragraphs[0]
                    .font.size,
                    Pt(18),
                )
                actual_text.append(table.cell(1, 0).text)

            self.assertEqual(actual_text, expected_text)

    def test_empty_samples_still_create_an_editable_header_table(self):
        with tempfile.TemporaryDirectory() as directory:
            presentation_path = Path(directory) / "report.pptx"
            self._create_presentation(presentation_path)

            populate_tested_parts(
                presentation_path=presentation_path,
                metadata={"samples": []},
            )

            presentation = Presentation(presentation_path)
            self.assertEqual(len(presentation.slides), 1)
            table_shape = next(
                shape
                for shape in presentation.slides[0].shapes
                if shape.has_table
            )
            self.assertEqual(len(table_shape.table.rows), 1)

    def test_description_larger_than_one_slide_fails_instead_of_overflowing(self):
        with tempfile.TemporaryDirectory() as directory:
            presentation_path = Path(directory) / "report.pptx"
            self._create_presentation(presentation_path)

            with self.assertRaisesRegex(
                ValueError,
                "requires more vertical space than one slide",
            ):
                populate_tested_parts(
                    presentation_path=presentation_path,
                    metadata={
                        "samples": [
                            {
                                "sample_code": "PART-LONG",
                                "sample_description": "description " * 1000,
                            }
                        ]
                    },
                )

            self.assertEqual(
                len(Presentation(presentation_path).slides),
                1,
            )

    def test_row_height_increases_for_wrapped_descriptions(self):
        short_sample = {
            "sample_code": "PART-1",
            "sample_description": "Short description",
        }
        long_sample = {
            "sample_code": "PART-2",
            "sample_description": "Long description " * 10,
        }

        self.assertGreater(
            tested_part_row_height_cm(long_sample),
            tested_part_row_height_cm(short_sample),
        )


if __name__ == "__main__":
    unittest.main()
