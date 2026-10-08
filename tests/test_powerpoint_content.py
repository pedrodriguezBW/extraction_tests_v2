import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from pptx import Presentation

from project_fixtures import build_test_folder

from src.report_generator.powerpoint.charts import (
    add_climatic_profile_chart,
    add_dut_profile_chart,
)
from src.report_generator.powerpoint.images import (
    find_test_result_charts,
)
from src.report_generator.powerpoint.styles import (
    FONT_SIZE_CHART_AXIS_PT,
    FONT_SIZE_CHART_LEGEND_PT,
    FONT_SIZE_CHART_TICK_PT,
    FONT_SIZE_CHART_TITLE_PT,
    FONT_SIZE_COMPACT_LABEL_PT,
    FONT_SIZE_LABEL_PT,
    FONT_SIZE_PROCEDURE_MIN_PT,
    FONT_SIZE_SECTION_TITLE_PT,
    FONT_SIZE_TABLE_BODY_PT,
    FONT_SIZE_TABLE_HEADER_PT,
    FONT_SIZE_TESTED_PARTS_PT,
    FONT_SIZE_VALUE_PT,
    MIN_GENERATED_FONT_SIZE_PT,
)
from src.report_generator.powerpoint.tables import (
    build_climatic_profile_rows,
)
from src.report_generator.evidences import Evidence, EvidenceDiscovery, discover_evidences
from src.report_generator.generator import generate_climatic_report
from src.report_generator.powerpoint.presentation import (
    build_report_filename,
)
from src.report_generator.sections.test_results import (
    _reference_text,
    _result_evidences,
    populate_test_results,
)


class GeneratedTypographyTests(unittest.TestCase):
    def test_generated_font_tokens_respect_minimum(self):
        generated_sizes = (
            FONT_SIZE_SECTION_TITLE_PT,
            FONT_SIZE_LABEL_PT,
            FONT_SIZE_VALUE_PT,
            FONT_SIZE_COMPACT_LABEL_PT,
            FONT_SIZE_TABLE_HEADER_PT,
            FONT_SIZE_TABLE_BODY_PT,
            FONT_SIZE_TESTED_PARTS_PT,
            FONT_SIZE_PROCEDURE_MIN_PT,
            FONT_SIZE_CHART_TITLE_PT,
            FONT_SIZE_CHART_AXIS_PT,
            FONT_SIZE_CHART_TICK_PT,
            FONT_SIZE_CHART_LEGEND_PT,
        )
        self.assertTrue(
            all(
                size >= MIN_GENERATED_FONT_SIZE_PT
                for size in generated_sizes
            )
        )


class ClimaticTableTests(unittest.TestCase):
    def test_missing_humidity_and_actuation_use_dash(self):
        rows = build_climatic_profile_rows(
            [
                {
                    "sequence": 1,
                    "time_min": 0,
                    "duration_min": 0,
                    "temperature_c": -40,
                    "humidity_percent": None,
                    "actuation": "",
                }
            ]
        )

        self.assertEqual(rows[0][4], "-")
        self.assertEqual(rows[0][5], "-")


class NativeChartTests(unittest.TestCase):
    def setUp(self):
        self.presentation = Presentation()
        self.slide = self.presentation.slides.add_slide(
            self.presentation.slide_layouts[6]
        )

    def test_climatic_profile_is_native_chart(self):
        chart = add_climatic_profile_chart(
            slide=self.slide,
            profile_points=[
                {"time_min": 0, "temperature_c": -40},
                {"time_min": 70, "temperature_c": 90},
            ],
            left_cm=1,
            top_cm=1,
            width_cm=12,
            height_cm=7,
        )

        self.assertIsNotNone(chart)
        self.assertEqual(
            sum(shape.has_chart for shape in self.slide.shapes),
            1,
        )
        axis_ids = [
            int(axis_reference.get("val"))
            for axis_reference in chart._chartSpace.xpath(
                ".//c:axId | .//c:crossAx"
            )
        ]
        self.assertTrue(
            all(-(2**31) <= axis_id < 2**31 for axis_id in axis_ids)
        )

    def test_dut_profile_is_native_chart(self):
        chart = add_dut_profile_chart(
            slide=self.slide,
            profile_points=[
                {"time_ms": 0, "dut_position_percent": 0},
                {"time_ms": 100, "dut_position_percent": 100},
            ],
            left_cm=1,
            top_cm=1,
            width_cm=12,
            height_cm=7,
        )

        self.assertIsNotNone(chart)
        self.assertEqual(
            sum(shape.has_chart for shape in self.slide.shapes),
            1,
        )


class InitialEvidencePhotoTests(unittest.TestCase):
    def test_initial_photos_are_selected_in_descriptor_order(self):
        with tempfile.TemporaryDirectory() as directory:
            test_root=build_test_folder(Path(directory)/"TEST - 001")
            folder=test_root/"02_Evidences"/"00_Initial";folder.mkdir(parents=True)
            first=folder/"initial_01.jpg";second=folder/"initial_02.jpg";first.write_bytes(b"photo");second.write_bytes(b"photo")
            (folder/"evidence.json").write_text(json.dumps({"schemaVersion":1,"type":"initial","sequence":0,"photos":[{"savedName":first.name},{"savedName":second.name}]}),encoding="utf-8")
            self.assertEqual(discover_evidences(test_root).found_photo_paths_for_type("initial"),[first,second])


class TestResultsPopulationTests(unittest.TestCase):
    @patch(
        "src.report_generator.sections.test_results."
        "populate_test_results_slide"
    )
    @patch(
        "src.report_generator.sections.test_results."
        "create_continuation_slide"
    )
    @patch(
        "src.report_generator.sections.test_results."
        "clear_slide_body"
    )
    @patch(
        "src.report_generator.sections.test_results."
        "find_slide_in_section"
    )
    @patch(
        "src.report_generator.sections.test_results."
        "find_test_result_charts"
    )
    @patch(
        "src.report_generator.sections.test_results.Presentation"
    )
    def test_saved_charts_create_test_results_continuations(
        self,
        presentation_mock,
        find_charts_mock,
        find_slide_mock,
        clear_slide_mock,
        create_continuation_mock,
        populate_slide_mock,
    ):
        presentation = MagicMock()
        first_slide = object()
        continuation_slide = object()
        presentation_mock.return_value = presentation
        find_slide_mock.return_value = first_slide
        create_continuation_mock.return_value = continuation_slide

        charts = [
            Path(f"chart03_simpati_acquisition_{index:02d}.png")
            for index in range(1, 7)
        ]
        find_charts_mock.return_value = charts

        populate_test_results(
            presentation_path=Path("report.pptx"),
            test_root=Path("test"),
        )

        clear_slide_mock.assert_called_once_with(
            slide=first_slide,
            expected_title="4. Test Results",
        )
        self.assertEqual(populate_slide_mock.call_count, 2)
        self.assertEqual(
            populate_slide_mock.call_args_list[0].kwargs["image_paths"],
            charts[:4],
        )
        self.assertEqual(
            populate_slide_mock.call_args_list[1].kwargs["image_paths"],
            charts[4:],
        )
        create_continuation_mock.assert_called_once_with(
            presentation=presentation,
            reference_slide=first_slide,
            title="4. Test Results (cont.)",
        )
        presentation.save.assert_called_once_with(Path("report.pptx"))

    @patch(
        "src.report_generator.sections.test_results."
        "clear_slide_body"
    )
    @patch(
        "src.report_generator.sections.test_results."
        "find_slide_in_section"
    )
    @patch(
        "src.report_generator.sections.test_results."
        "find_test_result_charts"
    )
    @patch(
        "src.report_generator.sections.test_results.Presentation"
    )
    def test_report_generation_continues_without_saved_charts(
        self,
        presentation_mock,
        find_charts_mock,
        find_slide_mock,
        clear_slide_mock,
    ):
        presentation = MagicMock()
        first_slide = object()
        presentation_mock.return_value = presentation
        find_slide_mock.return_value = first_slide
        find_charts_mock.return_value = []

        populate_test_results(
            presentation_path=Path("report.pptx"),
            test_root=Path("test"),
        )

        clear_slide_mock.assert_called_once()
        presentation.save.assert_called_once_with(Path("report.pptx"))

    @patch("src.report_generator.generator.publish_report")
    @patch("src.report_generator.generator.populate_test_results")
    @patch("src.report_generator.generator.populate_test_inputs")
    @patch("src.report_generator.generator.populate_test_assembly_images")
    @patch("src.report_generator.generator.populate_tested_parts")
    @patch("src.report_generator.generator.populate_test_description")
    @patch("src.report_generator.generator.create_working_presentation")
    @patch("src.report_generator.generator.validate_template_path")
    @patch("src.report_generator.generator.prepare_working_directory")
    @patch("src.report_generator.generator.require_report_directory")
    @patch("src.report_generator.generator.load_test_metadata")
    @patch("src.report_generator.generator.discover_evidences")
    def test_generator_includes_saved_charts_in_test_results(
        self,
        discover_evidences_mock,
        load_metadata_mock,
        require_report_mock,
        prepare_directory_mock,
        validate_template_mock,
        create_presentation_mock,
        populate_description_mock,
        populate_parts_mock,
        populate_assembly_mock,
        populate_inputs_mock,
        populate_results_mock,
        publish_report_mock,
    ):
        test_root = Path("test")
        template_path = Path("template.pptx")
        working_path = Path("working") / "report.pptx"
        output_path = Path("test") / "04_Report" / "report.pptx"
        metadata = {"test": {"test_name": "Example"}}
        load_metadata_mock.return_value = metadata
        initial_images=[test_root/"02_Evidences"/"00_Initial"/"initial_01.jpg"]
        evidence_discovery=MagicMock();evidence_discovery.found_photo_paths_for_type.return_value=initial_images;discover_evidences_mock.return_value=evidence_discovery
        require_report_mock.return_value = Path("test") / "04_Report"
        prepare_directory_mock.return_value = Path("working")
        create_presentation_mock.return_value = working_path
        publish_report_mock.return_value = output_path

        result = generate_climatic_report(
            test_root=test_root,
            template_path=template_path,
        )

        self.assertEqual(result, output_path)
        populate_assembly_mock.assert_called_once_with(presentation_path=working_path,metadata=metadata,image_paths=initial_images)
        populate_results_mock.assert_called_once_with(presentation_path=working_path,test_root=test_root,evidence_discovery=evidence_discovery)
        publish_report_mock.assert_called_once_with(
            working_path,
            Path("test") / "04_Report",
        )


class EvidenceTimelineTests(unittest.TestCase):
    def evidence(self,sequence,event_type,title):
        return Evidence(directory=Path(str(sequence)),descriptor_path=Path(str(sequence))/"evidence.json",folder_name=f"{sequence:02d}_{title}",type=event_type,title=title,sequence=sequence)
    def test_mixed_types_keep_sequence_order(self):
        discovery=EvidenceDiscovery(directory=Path("02_Evidences"),found=True,evidences=[self.evidence(0,"initial","Initial"),self.evidence(1,"incident","Incident"),self.evidence(2,"planned_inspection","Inspection"),self.evidence(3,"restart","Restart")])
        self.assertEqual([e.title for e in _result_evidences(discovery)],["Incident","Inspection","Restart"])
    def test_reference_uses_descriptor_value_and_type(self):
        evidence=self.evidence(1,"incident","Incident");object.__setattr__(evidence,"reference_type","cycles");object.__setattr__(evidence,"reference_value","450");self.assertEqual(_reference_text(evidence),"450 cycles")


class GeneratorOutputTests(unittest.TestCase):
    """Run the real generator flow with the slide sections mocked."""

    SECTION_PATCHES = (
        "populate_test_description",
        "populate_tested_parts",
        "populate_test_assembly_images",
        "populate_test_inputs",
        "populate_test_results",
    )

    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        workspace = Path(self.temporary_directory.name)
        self.test_root = build_test_folder(workspace / "TEST - 001")
        self.metadata_file = (
            self.test_root / "04_Report" / "test_metadata.json"
        )
        self.template_path = workspace / "template.pptx"
        Presentation().save(self.template_path)

        self.section_mocks = {}
        for name in self.SECTION_PATCHES:
            patcher = patch(f"src.report_generator.generator.{name}")
            self.section_mocks[name] = patcher.start()
            self.addCleanup(patcher.stop)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_report_is_saved_directly_in_04_report(self):
        metadata_before = self.metadata_file.read_bytes()

        output_path = generate_climatic_report(
            test_root=self.test_root,
            template_path=self.template_path,
        )

        self.assertEqual(
            output_path,
            self.test_root / "04_Report" / "K-01_report_prototype.pptx",
        )
        self.assertTrue(output_path.is_file())
        Presentation(output_path)
        self.assertEqual(
            list((self.test_root / "04_Report" / "_Working").iterdir()),
            [],
        )
        self.assertEqual(self.metadata_file.read_bytes(), metadata_before)
        self.assertEqual(
            sorted(path.name for path in self.test_root.iterdir()),
            ["01_Inputs", "02_Evidences", "03_Data", "04_Report"],
        )
        self.assertEqual(
            sorted(path.name for path in (self.test_root / "04_Report").iterdir()),
            ["K-01_report_prototype.pptx", "_Working", "test_metadata.json"],
        )

    def test_profile_sections_receive_points_from_json(self):
        generate_climatic_report(
            test_root=self.test_root,
            template_path=self.template_path,
        )

        metadata = self.section_mocks["populate_test_inputs"].call_args[0][1]
        expected = json.loads(self.metadata_file.read_text(encoding="utf-8"))
        self.assertEqual(
            metadata["climatic_inputs"]["profile_points"],
            expected["climatic_inputs"]["profile_points"],
        )
        self.assertEqual(
            metadata["dut_controller_inputs"]["profile_points"],
            expected["dut_controller_inputs"]["profile_points"],
        )

    def test_missing_metadata_stops_before_creating_outputs(self):
        self.metadata_file.unlink()

        with self.assertRaises(FileNotFoundError):
            generate_climatic_report(
                test_root=self.test_root,
                template_path=self.template_path,
            )

        self.assertEqual(list((self.test_root / "04_Report").iterdir()), [])
        self.section_mocks["populate_test_inputs"].assert_not_called()

    def test_existing_report_is_replaced(self):
        previous = (
            self.test_root / "04_Report" / "K-01_report_prototype.pptx"
        )
        previous.write_bytes(b"old report")

        output_path = generate_climatic_report(
            test_root=self.test_root,
            template_path=self.template_path,
        )

        self.assertEqual(output_path, previous)
        self.assertNotEqual(previous.read_bytes(), b"old report")


class ReportFileNameTests(unittest.TestCase):
    def test_invalid_windows_characters_are_replaced(self):
        self.assertEqual(
            build_report_filename('K-01: "A/B"'),
            "K-01_ _A_B__report_prototype.pptx",
        )

    def test_empty_name_is_rejected(self):
        with self.assertRaises(ValueError):
            build_report_filename("  ")


class SavedChartDiscoveryTests(unittest.TestCase):
    def test_simpati_charts_are_returned_in_natural_order(self):
        with tempfile.TemporaryDirectory() as directory:
            test_root = Path(directory)
            assets_directory = (
                test_root
                / "04_Report"
                / "_RenderedAssets"
            )
            assets_directory.mkdir(parents=True)

            for chart_number in (10, 2, 1):
                chart_path = assets_directory / (
                    f"chart03_simpati_acquisition_{chart_number}.png"
                )
                chart_path.write_bytes(b"image")

            charts = find_test_result_charts(test_root)

            self.assertEqual(
                [chart.name for chart in charts],
                [
                    "chart03_simpati_acquisition_1.png",
                    "chart03_simpati_acquisition_2.png",
                    "chart03_simpati_acquisition_10.png",
                ],
            )


if __name__ == "__main__":
    unittest.main()
