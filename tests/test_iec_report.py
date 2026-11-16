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
        self.assertIn("STANDARD\n—", text)
        self.assertIn("MEASUREMENT POINTS", text)
        self.assertIn("MIN TEMPERATURE (TA)", text)
        self.assertIn("MAX TEMPERATURE (TB)", text)
        self.assertEqual(metadata_path.read_bytes(), original)
        description = next(slide for slide in presentation.slides if slide.shapes.title and slide.shapes.title.text == "1. Test Description")
        self.assertFalse(any(shape.has_table for shape in description.shapes))
        labels = {shape.text: shape for shape in description.shapes if shape.has_text_frame}
        for label in ("LABORATORY", "TEST TYPE", "STANDARD"):
            self.assertTrue(labels[label].text_frame.paragraphs[0].font.bold)
        self.assertEqual(labels["STC"].left, labels["LABORATORY"].left)
        self.assertGreater(labels["STC"].top, labels["LABORATORY"].top)

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

    def test_procedure_expands_on_first_slide_and_moves_contacts_after_it(self):
        procedure = "Detailed engineering procedure with mounting and measurement instructions. " * 10
        metadata = minimal_metadata(test={"test_name": "IEC", "procedure": procedure},
                                    people={"requester": {"name": "Requester example"}})
        root = build_test_folder(self.workspace / "TEST - 003", metadata=metadata)
        presentation = Presentation(generate_climatic_report(root, self.template))
        first_index = next(i for i, slide in enumerate(presentation.slides)
                           if slide.shapes.title and slide.shapes.title.text == "1. Test Description")
        first = presentation.slides[first_index]
        first_text = all_text(type("Deck", (), {"slides": [first]})())
        self.assertIn(procedure, first_text)
        self.assertNotIn("TEST CONTACTS", first_text)
        following = presentation.slides[first_index + 1]
        following_text = all_text(type("Deck", (), {"slides": [following]})())
        self.assertIn("TEST CONTACTS", following_text)
        self.assertIn("Requester example", following_text)
        self.assertNotIn("TEST PROCEDURE", following_text)

    def test_very_long_procedure_starts_on_first_slide_and_contacts_follow_last_fragment(self):
        procedure = "Procedure step with a detailed measurement and mounting instruction.\n" * 90
        root = build_test_folder(self.workspace / "TEST - 004",
                                 metadata=minimal_metadata(test={"test_name": "IEC", "procedure": procedure}))
        presentation = Presentation(generate_climatic_report(root, self.template))
        slides = [slide for slide in presentation.slides
                  if any(shape.has_text_frame and shape.text.startswith("1. Test Description") for shape in slide.shapes)]
        fragments = []
        contact_seen = False
        for slide in slides:
            for shape in slide.shapes:
                if not shape.has_text_frame:
                    continue
                if shape.text == "TEST CONTACTS":
                    contact_seen = True
                if "Procedure step" in shape.text:
                    self.assertFalse(contact_seen)
                    fragments.append(shape.text)
                    self.assertLessEqual(shape.top + shape.height, Cm(16.80))
        self.assertGreater(len(fragments), 1)
        self.assertIn("Procedure step", all_text(type("Deck", (), {"slides": [slides[0]]})()))
        self.assertEqual("".join(fragments).replace("\v", "\n"), procedure)
        self.assertTrue(contact_seen)

    def test_chamber_appears_once_above_equipment_with_matching_style(self):
        chamber = "TECLI00023 - CC TS (OS)"
        description = "Rapid change chamber – 2 compartments, basket"
        equipment = [{"equipment_used": f"Equipment-{i}", "equipment_code": f"EQ-{i}"} for i in range(5)]
        root = build_test_folder(self.workspace / "TEST - 005", metadata=minimal_metadata(
            test_facility={"climatic_chamber": chamber}, equipment=equipment))
        presentation = Presentation(generate_climatic_report(root, self.template))
        text = all_text(presentation)
        self.assertEqual(text.count(chamber), 1)
        self.assertEqual(text.count(description), 1)
        first = next(slide for slide in presentation.slides if slide.shapes.title and slide.shapes.title.text == "2. Test Assembly")
        shapes = {shape.text: shape for shape in first.shapes if shape.has_text_frame}
        name_shape, type_shape = shapes[chamber], shapes[description]
        self.assertGreaterEqual(type_shape.left, name_shape.left + name_shape.width)
        self.assertEqual(name_shape.top, type_shape.top)
        self.assertLess(type_shape.top + type_shape.height, shapes["ADDITIONAL EQUIPMENT"].top)
        name_font = name_shape.text_frame.paragraphs[0].font
        type_font = type_shape.text_frame.paragraphs[0].font
        self.assertEqual((name_font.name, name_font.size, name_font.color.rgb),
                         (type_font.name, type_font.size, type_font.color.rgb))
        self.assertFalse(any(shape.has_table for shape in first.shapes))
        for item in equipment:
            self.assertEqual(text.count(item["equipment_used"]), 1)
        for shape in first.shapes:
            if shape.has_text_frame and shape.text.startswith("Equipment-"):
                self.assertLess(shape.top + shape.height, Cm(16.80))
