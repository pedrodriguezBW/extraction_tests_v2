"""Integración del informe editable con configuración nueva y ensayos antiguos."""

import tempfile
import unittest
from pathlib import Path

from pptx import Presentation
from pptx.util import Cm
from project_fixtures import build_test_folder, minimal_metadata
from src.report_generator.generator import generate_climatic_report
from src.report_generator.report_inputs import save_report_inputs


def validation_template(path):
    presentation = Presentation()
    presentation.slide_width = Cm(33.87)
    presentation.slide_height = Cm(19.05)
    for title in ("Cover", "2. Tested Parts", "TEST A", "1. Test Description", "2. Test Assembly",
                  "3. Test Inputs", "4. Test Results", "5. Conclusions"):
        slide = presentation.slides.add_slide(presentation.slide_layouts[5])
        slide.shapes.title.text = title
        if title == "1. Test Description":
            slide.shapes.add_textbox(Cm(2), Cm(4), Cm(20), Cm(1)).text = "Xyz"
    presentation.save(path)


def all_text(presentation):
    values = []
    for slide in presentation.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                values.append(shape.text)
            if shape.has_table:
                values.extend(cell.text for row in shape.table.rows for cell in row.cells)
    return "\n".join(values)


class IecReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.template = self.workspace / "template.pptx"
        validation_template(self.template)

    def test_legacy_test_without_inputs_generates_editable_rows(self):
        root = build_test_folder(self.workspace / "TEST - 001")
        metadata_path = root / "04_Report/test_metadata.json"
        original = metadata_path.read_bytes()
        result = generate_climatic_report(root, self.template)
        presentation = Presentation(result)
        text = all_text(presentation)
        self.assertIn("STC", text)
        self.assertIn("Standard\n—", text)
        self.assertIn("MEASUREMENT POINTS", text)
        self.assertIn("MIN TEMPERATURE (TA)", text)
        self.assertIn("MAX TEMPERATURE (TB)", text)
        self.assertEqual(metadata_path.read_bytes(), original)

    def test_many_points_and_long_procedure_continue_without_losing_content(self):
        procedure = "Detailed engineering procedure with mounting and measurement instructions. " * 10
        metadata = minimal_metadata(test={"test_name": "IEC", "standard": "Customer-specific edition", "procedure": procedure},
                                    test_facility={"climatic_chamber": "TECLI00023 - CC TS (OS)"})
        root = build_test_folder(self.workspace / "TEST - 002", metadata=metadata)
        points = [{"channel": f"TC-{index:03d}", "location": "Specimen mounting area " * 5,
                   "sensor_type": "Type T", "function": "specimen"} for index in range(25)]
        save_report_inputs(root, {"test_type": "Na", "measurement_points": points})
        presentation = Presentation(generate_climatic_report(root, self.template))
        text = all_text(presentation)
        self.assertIn(procedure, text)
        self.assertIn("1. Test Description (cont.)", text)
        self.assertIn("Customer-specific edition", text)
        self.assertIn("Rapid change chamber – 2 compartments, basket", text)
        self.assertGreater(text.count("2. Test Assembly (cont.)"), 1)
        for point in points:
            self.assertEqual(text.count(point["channel"]), 1)
        for slide in presentation.slides:
            for shape in slide.shapes:
                if shape.has_table:
                    self.assertLess(shape.top + shape.height, Cm(17.0))
