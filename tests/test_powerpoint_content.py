import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from pptx import Presentation

from project_fixtures import build_test_folder, write_image

from src.report_generator.powerpoint.charts import (
    add_climatic_profile_chart,
    add_dut_profile_chart,
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
    prune_climatic_report_slides,
)
from src.report_generator.sections.test_results import (
    _reference_text,
    _result_evidences,
    populate_test_results,
)


class PresentationPruningTests(unittest.TestCase):
    @staticmethod
    def _add_titled_slide(presentation, title, footer_number):
        slide = presentation.slides.add_slide(presentation.slide_layouts[5])
        if slide.shapes.title is None:
            title_box = slide.shapes.add_textbox(0, 0, 5000000, 500000)
            title_box.text = title
        else:
            slide.shapes.title.text = title
        footer = slide.shapes.add_textbox(
            100000,
            15 * 360000,
            500000,
            300000,
        )
        footer.text = str(footer_number)
        return slide

    def test_pruning_keeps_climatic_scope_and_conclusions(self):
        with tempfile.TemporaryDirectory() as directory:
            presentation_path = Path(directory) / "report.pptx"
            presentation = Presentation()
            self._add_titled_slide(presentation, "Cover", 1)
            self._add_titled_slide(presentation, "LEG Summary", 2)
            self._add_titled_slide(presentation, "One Page Summary", 3)
            self._add_titled_slide(presentation, "2. Tested Parts", 4)
            self._add_titled_slide(
                presentation,
                "2. Tested Parts (cont.)",
                5,
            )
            self._add_titled_slide(presentation, "TEST A", 6)
            self._add_titled_slide(presentation, "Contents", 7)
            self._add_titled_slide(presentation, "1. Test Description", 8)
            self._add_titled_slide(presentation, "2. Test Assembly", 9)
            self._add_titled_slide(presentation, "3. Test Inputs", 10)
            self._add_titled_slide(
                presentation,
                "3. Test Inputs (cont.)",
                11,
            )
            self._add_titled_slide(presentation, "4. Test Results", 12)
            self._add_titled_slide(
                presentation,
                "4. Test Results (cont.)",
                13,
            )
            self._add_titled_slide(presentation, "5. Conclusions", 14)
            self._add_titled_slide(presentation, "TEST B", 15)
            self._add_titled_slide(presentation, "5. Conclusions", 16)
            self._add_titled_slide(presentation, "TEST C", 17)
            self._add_titled_slide(presentation, "Sample Analysis", 18)
            self._add_titled_slide(
                presentation,
                "Additional Information",
                19,
            )
            presentation.save(presentation_path)

            prune_climatic_report_slides(presentation_path)
            result = Presentation(presentation_path)
            titles = [
                slide.shapes.title.text
                for slide in result.slides
                if slide.shapes.title is not None
            ]

            self.assertEqual(
                titles,
                [
                    "Cover",
                    "2. Tested Parts",
                    "2. Tested Parts (cont.)",
                    "TEST A",
                    "Contents",
                    "1. Test Description",
                    "2. Test Assembly",
                    "3. Test Inputs",
                    "3. Test Inputs (cont.)",
                    "4. Test Results",
                    "4. Test Results (cont.)",
                    "5. Conclusions",
                ],
            )
            self.assertNotIn("TEST B", titles)
            self.assertNotIn("TEST C", titles)
            self.assertNotIn("Additional Information", titles)

            footer_numbers = []
            for slide in result.slides:
                numeric_footer = [
                    shape.text.strip()
                    for shape in slide.shapes
                    if shape.has_text_frame
                    and shape.text.strip().isdigit()
                    and shape.top >= 15 * 360000
                ]
                footer_numbers.append(numeric_footer[0])
            self.assertEqual(
                footer_numbers,
                [str(index) for index in range(1, len(result.slides) + 1)],
            )

    def test_pruning_requires_test_a_conclusions(self):
        with tempfile.TemporaryDirectory() as directory:
            presentation_path = Path(directory) / "report.pptx"
            presentation = Presentation()
            self._add_titled_slide(presentation, "Cover", 1)
            self._add_titled_slide(presentation, "2. Tested Parts", 2)
            self._add_titled_slide(presentation, "TEST A", 3)
            presentation.save(presentation_path)

            with self.assertRaises(ValueError):
                prune_climatic_report_slides(presentation_path)


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
        "src.report_generator.sections.test_results.discover_evidences"
    )
    @patch(
        "src.report_generator.sections.test_results.Presentation"
    )
    def test_selected_images_create_test_results_continuations(
        self,
        presentation_mock,
        discover_mock,
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
        discover_mock.return_value = EvidenceDiscovery(
            directory=Path("test") / "02_Evidences", found=False
        )

        # Mixed origins and formats, deliberately out of natural order: the
        # engine inserts exactly what it receives, in that order.
        charts = [
            Path("graphtec_chart_02.png"),
            Path("chart03_simpati_acquisition_01.png"),
            Path("manual_photo.JPG"),
            Path("canoe_future.jpeg"),
            Path("graphtec_chart_01.png"),
            Path("extra.png"),
        ]

        populate_test_results(
            presentation_path=Path("report.pptx"),
            test_root=Path("test"),
            result_image_paths=charts,
        )

        clear_slide_mock.assert_called_once_with(
            slide=first_slide,
            expected_title="4. Test Results",
        )
        self.assertEqual(populate_slide_mock.call_count, 3)
        self.assertEqual(
            populate_slide_mock.call_args_list[0].kwargs["image_paths"],
            charts[:2],
        )
        self.assertEqual(
            populate_slide_mock.call_args_list[1].kwargs["image_paths"],
            charts[2:4],
        )
        self.assertEqual(
            populate_slide_mock.call_args_list[2].kwargs["image_paths"],
            charts[4:],
        )
        
        self.assertEqual(create_continuation_mock.call_count, 2)

        self.assertEqual(
            create_continuation_mock.call_args_list[0].kwargs,
            {
                "presentation": presentation,
                "reference_slide": first_slide,
                "title": "4. Test Results (cont.)",
            },
        )
        self.assertEqual(
            create_continuation_mock.call_args_list[1].kwargs,
            {
                "presentation": presentation,
                "reference_slide": continuation_slide,
                "title": "4. Test Results (cont.)",
            },
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
        "src.report_generator.sections.test_results.discover_evidences"
    )
    @patch(
        "src.report_generator.sections.test_results.Presentation"
    )
    def test_report_generation_continues_without_selected_images(
        self,
        presentation_mock,
        discover_mock,
        find_slide_mock,
        clear_slide_mock,
    ):
        presentation = MagicMock()
        first_slide = object()
        presentation_mock.return_value = presentation
        find_slide_mock.return_value = first_slide
        discover_mock.return_value = EvidenceDiscovery(
            directory=Path("test") / "02_Evidences", found=False
        )

        populate_test_results(
            presentation_path=Path("report.pptx"),
            test_root=Path("test"),
            result_image_paths=[],
        )

        clear_slide_mock.assert_called_once()
        presentation.save.assert_called_once_with(Path("report.pptx"))

    @patch(
        "src.report_generator.sections.test_results."
        "populate_test_results_slide"
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
        "src.report_generator.sections.test_results.discover_evidences"
    )
    @patch(
        "src.report_generator.sections.test_results.Presentation"
    )
    def test_engine_never_scans_rendered_assets(
        self,
        presentation_mock,
        discover_mock,
        find_slide_mock,
        clear_slide_mock,
        populate_slide_mock,
    ):
        """Images present on disk but not selected are never inserted."""
        presentation_mock.return_value = MagicMock()
        find_slide_mock.return_value = object()
        discover_mock.return_value = EvidenceDiscovery(
            directory=Path("test") / "02_Evidences", found=False
        )
        with tempfile.TemporaryDirectory() as directory:
            test_root = Path(directory)
            assets = test_root / "04_Report" / "_RenderedAssets"
            write_image(assets / "chart03_simpati_acquisition_01.png")
            write_image(assets / "graphtec_chart_01.png")
            selected = write_image(assets / "manual.png")

            populate_test_results(
                presentation_path=Path("report.pptx"),
                test_root=test_root,
                result_image_paths=[selected],
            )

        populate_slide_mock.assert_called_once()
        self.assertEqual(
            populate_slide_mock.call_args.kwargs["image_paths"],
            [selected],
        )

    @patch("src.report_generator.generator.load_report_inputs")
    @patch("src.report_generator.generator.publish_report")
    @patch("src.report_generator.generator.prune_climatic_report_slides")
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
    @patch("src.report_generator.generator.select_rendered_assets")
    @patch("src.report_generator.generator.select_evidence_photos")
    def test_generator_passes_selected_images_to_test_results(
        self,
        select_photos_mock,
        select_assets_mock,
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
        prune_slides_mock,
        publish_report_mock,
        load_inputs_mock,
    ):
        from src.report_generator.report_inputs import ReportInputs
        load_inputs_mock.return_value = (ReportInputs(), [])
        test_root = Path("test")
        template_path = Path("template.pptx")
        working_path = Path("working") / "report.pptx"
        output_path = Path("test") / "04_Report" / "report.pptx"
        metadata = {"test": {"test_name": "Example"}}
        load_metadata_mock.return_value = metadata
        initial_images=[test_root/"02_Evidences"/"00_Initial"/"initial_01.jpg"]
        evidence_discovery=MagicMock();discover_evidences_mock.return_value=evidence_discovery
        assembly_photo=MagicMock(path=initial_images[0])
        result_photo=MagicMock(path=test_root/"02_Evidences"/"01_Final"/"final_01.jpg")
        result_photo.evidence.descriptor_path=test_root/"02_Evidences"/"01_Final"/"evidence.json"
        select_photos_mock.side_effect=[[assembly_photo],[result_photo]]
        require_report_mock.return_value = Path("test") / "04_Report"
        prepare_directory_mock.return_value = Path("working")
        create_presentation_mock.return_value = working_path
        publish_report_mock.return_value = output_path
        selected = [
            "04_Report/_RenderedAssets/graphtec_chart_01.png",
            "04_Report/_RenderedAssets/chart03_simpati_acquisition_01.png",
        ]
        resolved = [test_root / "04_Report" / "_RenderedAssets" / Path(s).name for s in selected]
        select_assets_mock.return_value = resolved

        result = generate_climatic_report(
            test_root=test_root,
            template_path=template_path,
            selected_rendered_assets=selected,
            selected_assembly_photos=["02_Evidences/00_Initial/initial_01.jpg"],
            selected_result_photos=["02_Evidences/01_Final/final_01.jpg"],
        )

        self.assertEqual(result, output_path)
        self.assertEqual(
            select_photos_mock.call_args_list,
            [
                call(evidence_discovery, "assembly", ["02_Evidences/00_Initial/initial_01.jpg"]),
                call(evidence_discovery, "results", ["02_Evidences/01_Final/final_01.jpg"]),
            ],
        )
        select_assets_mock.assert_called_once_with(test_root, selected)
        populate_assembly_mock.assert_called_once_with(presentation_path=working_path,metadata=metadata,image_paths=initial_images,report_inputs=ReportInputs().model_dump())
        populate_results_mock.assert_called_once_with(presentation_path=working_path,test_root=test_root,evidence_discovery=evidence_discovery,result_image_paths=resolved,evidence_photo_paths={result_photo.evidence.descriptor_path:[result_photo.path]})
        prune_slides_mock.assert_called_once_with(working_path)
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
        "prune_climatic_report_slides",
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


class RenderedAssetOrderTests(unittest.TestCase):
    def test_inventory_uses_a_stable_natural_order(self):
        from src.report_generator.rendered_assets import list_rendered_assets

        with tempfile.TemporaryDirectory() as directory:
            test_root = Path(directory)
            assets_directory = (
                test_root
                / "04_Report"
                / "_RenderedAssets"
            )
            for name in (
                "chart03_simpati_acquisition_10.png",
                "chart03_simpati_acquisition_2.png",
                "Zeta.jpg",
                "chart03_simpati_acquisition_1.png",
                "graphtec_chart_01.png",
            ):
                write_image(assets_directory / name)

            names = [a.name for a in list_rendered_assets(test_root).assets]

            self.assertEqual(
                names,
                [
                    "chart03_simpati_acquisition_1.png",
                    "chart03_simpati_acquisition_2.png",
                    "chart03_simpati_acquisition_10.png",
                    "graphtec_chart_01.png",
                    "Zeta.jpg",
                ],
            )


if __name__ == "__main__":
    unittest.main()
