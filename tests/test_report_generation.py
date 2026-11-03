import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from project_fixtures import write_image

from backend.app.main import app
from backend.app.services.report_generation import (
    ReportGenerationError,
    generate_project_report,
)
from src.report_generator.version_check import VersionCheck

ASSETS = "04_Report/_RenderedAssets"


class ReportGenerationServiceTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.test_root = Path(self.temporary_directory.name)
        self.version_check_patch = patch(
            "backend.app.services.report_generation.check_application_version",
            return_value=VersionCheck(
                status="current",
                installed_version="0.6.0",
                current_version="0.6.0",
                package=r"\\server\share\generator.zip",
            ),
        )
        self.version_check_patch.start()
        self.addCleanup(self.version_check_patch.stop)
        self.template_path = self.test_root / "template.pptx"
        self.report_path = (
            self.test_root
            / "04_Report"
            / "Thermal_cycle_report_prototype.pptx"
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    @patch(
        "backend.app.services.report_generation."
        "generate_climatic_report"
    )
    def test_generation_returns_report_information(
        self,
        generate_report_mock,
    ):
        generate_report_mock.return_value = self.report_path

        with patch(
            "backend.app.services.report_generation."
            "POWERPOINT_TEMPLATE_PATH",
            self.template_path,
        ):
            result = generate_project_report(self.test_root)

        self.assertTrue(result.success)
        self.assertEqual(
            result.test_root,
            str(self.test_root.resolve()),
        )
        self.assertEqual(
            result.report_path,
            str(self.report_path.resolve()),
        )
        self.assertEqual(
            result.report_name,
            "Thermal_cycle_report_prototype.pptx",
        )
        self.assertEqual(result.rendered_assets_count, 0)
        self.assertEqual(result.rendered_assets, [])
        self.assertEqual(result.errors, [])
        generate_report_mock.assert_called_once_with(
            test_root=self.test_root.resolve(),
            template_path=self.template_path.resolve(),
            selected_rendered_assets=[],
            selected_assembly_photos=[],
            selected_result_photos=[],
        )

    @patch(
        "backend.app.services.report_generation."
        "generate_climatic_report"
    )
    def test_selected_rendered_assets_are_validated_and_forwarded_in_order(
        self,
        generate_report_mock,
    ):
        generate_report_mock.return_value = self.report_path
        assets = self.test_root / ASSETS
        write_image(assets / "chart03_simpati_acquisition_01.png")
        write_image(assets / "graphtec_chart_01.png")
        write_image(assets / "manual.png")
        selection = [
            f"{ASSETS}/manual.png",
            f"{ASSETS}/chart03_simpati_acquisition_01.png",
        ]

        with patch(
            "backend.app.services.report_generation."
            "POWERPOINT_TEMPLATE_PATH",
            self.template_path,
        ):
            result = generate_project_report(self.test_root, selection)

        self.assertTrue(result.success)
        self.assertEqual(result.rendered_assets_count, 2)
        self.assertEqual(result.rendered_assets, selection)
        generate_report_mock.assert_called_once_with(
            test_root=self.test_root.resolve(),
            template_path=self.template_path.resolve(),
            selected_rendered_assets=selection,
            selected_assembly_photos=[],
            selected_result_photos=[],
        )

    @patch(
        "backend.app.services.report_generation."
        "generate_climatic_report"
    )
    def test_empty_selection_is_not_replaced_by_the_inventory(
        self,
        generate_report_mock,
    ):
        generate_report_mock.return_value = self.report_path
        write_image(self.test_root / ASSETS / "graphtec_chart_01.png")

        with patch(
            "backend.app.services.report_generation."
            "POWERPOINT_TEMPLATE_PATH",
            self.template_path,
        ):
            result = generate_project_report(self.test_root, [])

        self.assertEqual(result.rendered_assets_count, 0)
        generate_report_mock.assert_called_once_with(
            test_root=self.test_root.resolve(),
            template_path=self.template_path.resolve(),
            selected_rendered_assets=[],
            selected_assembly_photos=[],
            selected_result_photos=[],
        )

    @patch(
        "backend.app.services.report_generation."
        "generate_climatic_report"
    )
    def test_omitted_selection_uses_every_valid_image(
        self,
        generate_report_mock,
    ):
        generate_report_mock.return_value = self.report_path
        write_image(self.test_root / ASSETS / "graphtec_chart_01.png")
        write_image(self.test_root / ASSETS / "chart03_simpati_acquisition_01.png")
        (self.test_root / ASSETS / "notes.txt").write_text("x", encoding="utf-8")

        with patch(
            "backend.app.services.report_generation."
            "POWERPOINT_TEMPLATE_PATH",
            self.template_path,
        ):
            result = generate_project_report(self.test_root, None)

        expected = [
            f"{ASSETS}/chart03_simpati_acquisition_01.png",
            f"{ASSETS}/graphtec_chart_01.png",
        ]
        self.assertEqual(result.rendered_assets, expected)
        generate_report_mock.assert_called_once_with(
            test_root=self.test_root.resolve(),
            template_path=self.template_path.resolve(),
            selected_rendered_assets=expected,
            selected_assembly_photos=[],
            selected_result_photos=[],
        )

    @patch(
        "backend.app.services.report_generation."
        "generate_climatic_report"
    )
    def test_invalid_selection_is_a_structured_error_before_generation(
        self,
        generate_report_mock,
    ):
        assets = self.test_root / ASSETS
        write_image(assets / "chart.png")
        (assets / "data.csv").write_text("1", encoding="utf-8")
        cases = {
            f"{ASSETS}/missing.png": (404, "report_generation_rendered_asset_not_found"),
            f"{ASSETS}/data.csv": (415, "report_generation_rendered_asset_unsupported"),
            "../outside.png": (400, "report_generation_invalid_rendered_asset"),
            str((assets / "chart.png").resolve()): (400, "report_generation_invalid_rendered_asset"),
            "04_Report/test_metadata.json": (400, "report_generation_invalid_rendered_asset"),
        }

        with patch(
            "backend.app.services.report_generation."
            "POWERPOINT_TEMPLATE_PATH",
            self.template_path,
        ):
            for path, (status, code) in cases.items():
                with self.assertRaises(ReportGenerationError, msg=path) as context:
                    generate_project_report(self.test_root, [path])
                self.assertEqual(context.exception.status_code, status, path)
                self.assertEqual(context.exception.error.code, code, path)

            with self.assertRaises(ReportGenerationError) as context:
                generate_project_report(
                    self.test_root, [f"{ASSETS}/chart.png", f"{ASSETS}/chart.png"]
                )
            self.assertEqual(context.exception.status_code, 400)

        generate_report_mock.assert_not_called()

    @patch(
        "backend.app.services.report_generation."
        "generate_climatic_report"
    )
    def test_expected_generation_error_is_structured(
        self,
        generate_report_mock,
    ):
        generate_report_mock.side_effect = FileNotFoundError(
            "The metadata file was not found."
        )

        with patch(
            "backend.app.services.report_generation."
            "POWERPOINT_TEMPLATE_PATH",
            self.template_path,
        ):
            with self.assertRaises(ReportGenerationError) as context:
                generate_project_report(self.test_root)

        error = context.exception
        self.assertEqual(error.status_code, 400)
        self.assertEqual(
            error.error.code,
            "report_generation_invalid_project",
        )
        self.assertEqual(
            error.error.message,
            "The metadata file was not found.",
        )
        self.assertEqual(error.error.exception_type, "FileNotFoundError")
        generate_report_mock.assert_called_once_with(
            test_root=self.test_root.resolve(),
            template_path=self.template_path.resolve(),
            selected_rendered_assets=[],
            selected_assembly_photos=[],
            selected_result_photos=[],
        )


    def test_missing_metadata_is_a_structured_client_error(self):
        (self.test_root / "04_Report").mkdir()
        self.template_path.write_bytes(b"template")

        with patch(
            "backend.app.services.report_generation."
            "POWERPOINT_TEMPLATE_PATH",
            self.template_path,
        ):
            with self.assertRaises(ReportGenerationError) as context:
                generate_project_report(self.test_root)

        error = context.exception
        self.assertEqual(error.status_code, 400)
        self.assertEqual(error.error.exception_type, "FileNotFoundError")
        self.assertIn("test_metadata.json", error.error.message)
        self.assertEqual(
            list((self.test_root / "04_Report").iterdir()),
            [],
        )

    def test_invalid_metadata_is_a_structured_client_error(self):
        report = self.test_root / "04_Report"
        report.mkdir()
        (report / "test_metadata.json").write_text("{}", encoding="utf-8")
        self.template_path.write_bytes(b"template")

        with patch(
            "backend.app.services.report_generation."
            "POWERPOINT_TEMPLATE_PATH",
            self.template_path,
        ):
            with self.assertRaises(ReportGenerationError) as context:
                generate_project_report(self.test_root)

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(
            context.exception.error.exception_type,
            "MetadataError",
        )

    @patch(
        "backend.app.services.report_generation."
        "generate_climatic_report"
    )
    def test_outdated_version_blocks_generation(self, generate_report_mock):
        with patch(
            "backend.app.services.report_generation.check_application_version",
            return_value=VersionCheck(
                status="outdated",
                installed_version="0.6.0",
                current_version="0.7.0",
                package=r"\\server\share\generator-0.7.0.zip",
            ),
        ):
            with self.assertRaises(ReportGenerationError) as context:
                generate_project_report(self.test_root)

        self.assertEqual(context.exception.status_code, 409)
        self.assertEqual(
            context.exception.error.code,
            "outdated_application_version",
        )
        self.assertIn(r"\\server\share\generator-0.7.0.zip",
                      context.exception.error.message)
        generate_report_mock.assert_not_called()

    @patch(
        "backend.app.services.report_generation."
        "generate_climatic_report"
    )
    def test_unavailable_manifest_does_not_block_generation(
        self,
        generate_report_mock,
    ):
        generate_report_mock.return_value = self.report_path
        with patch(
            "backend.app.services.report_generation.check_application_version",
            return_value=VersionCheck(
                status="unavailable",
                installed_version="0.6.0",
                warning="Manifest unavailable.",
            ),
        ), patch(
            "backend.app.services.report_generation."
            "POWERPOINT_TEMPLATE_PATH",
            self.template_path,
        ):
            result = generate_project_report(self.test_root)

        self.assertTrue(result.success)
        generate_report_mock.assert_called_once()


class ReportGenerationEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.test_root = Path(self.temporary_directory.name)
        self.version_check_patch = patch(
            "backend.app.services.report_generation.check_application_version",
            return_value=VersionCheck(
                status="current",
                installed_version="0.6.0",
                current_version="0.6.0",
                package=r"\\server\share\generator.zip",
            ),
        )
        self.version_check_patch.start()
        self.addCleanup(self.version_check_patch.stop)
        self.template_path = self.test_root / "template.pptx"
        self.report_path = (
            self.test_root
            / "04_Report"
            / "Thermal_cycle_report_prototype.pptx"
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    @patch(
        "backend.app.services.report_generation."
        "generate_climatic_report"
    )
    def test_generate_report_endpoint_returns_report(
        self,
        generate_report_mock,
    ):
        generate_report_mock.return_value = self.report_path

        with patch(
            "backend.app.services.report_generation."
            "POWERPOINT_TEMPLATE_PATH",
            self.template_path,
        ):
            response = self.client.post(
                "/projects/generate-report",
                json={"test_root": str(self.test_root)},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "success": True,
                "test_root": str(self.test_root.resolve()),
                "report_path": str(self.report_path.resolve()),
                "report_name": "Thermal_cycle_report_prototype.pptx",
                "rendered_assets_count": 0,
                "rendered_assets": [],
                "assembly_photos_count": 0,
                "assembly_photos": [],
                "result_photos_count": 0,
                "result_photos": [],
                "errors": [],
            },
        )
        generate_report_mock.assert_called_once_with(
            test_root=self.test_root.resolve(),
            template_path=self.template_path.resolve(),
            selected_rendered_assets=[],
            selected_assembly_photos=[],
            selected_result_photos=[],
        )

    @patch(
        "backend.app.services.report_generation."
        "generate_climatic_report"
    )
    def test_generate_report_endpoint_blocks_outdated_version(
        self,
        generate_report_mock,
    ):
        with patch(
            "backend.app.services.report_generation.check_application_version",
            return_value=VersionCheck(
                status="outdated",
                installed_version="0.6.0",
                current_version="0.7.0",
                package=r"\\server\share\generator-0.7.0.zip",
            ),
        ):
            response = self.client.post(
                "/projects/generate-report",
                json={"test_root": str(self.test_root)},
            )

        self.assertEqual(response.status_code, 409)
        self.assertFalse(response.json()["success"])
        self.assertEqual(
            response.json()["errors"][0]["code"],
            "outdated_application_version",
        )
        self.assertIn(
            r"\\server\share\generator-0.7.0.zip",
            response.json()["errors"][0]["message"],
        )
        generate_report_mock.assert_not_called()

    @patch(
        "backend.app.services.report_generation."
        "generate_climatic_report"
    )
    def test_generate_report_endpoint_uses_the_selected_rendered_assets(
        self,
        generate_report_mock,
    ):
        generate_report_mock.return_value = self.report_path
        assets = self.test_root / ASSETS
        write_image(assets / "chart03_simpati_acquisition_01.png")
        write_image(assets / "graphtec_chart_01.png")
        write_image(assets / "manual.jpg")
        write_image(assets / "unselected.png")

        with patch(
            "backend.app.services.report_generation."
            "POWERPOINT_TEMPLATE_PATH",
            self.template_path,
        ):
            single = self.client.post(
                "/projects/generate-report",
                json={
                    "test_root": str(self.test_root),
                    "selected_rendered_assets": [f"{ASSETS}/manual.jpg"],
                },
            )
            several = self.client.post(
                "/projects/generate-report",
                json={
                    "test_root": str(self.test_root),
                    "selected_rendered_assets": [
                        f"{ASSETS}/graphtec_chart_01.png",
                        f"{ASSETS}/manual.jpg",
                        f"{ASSETS}/chart03_simpati_acquisition_01.png",
                    ],
                },
            )
            empty = self.client.post(
                "/projects/generate-report",
                json={
                    "test_root": str(self.test_root),
                    "selected_rendered_assets": [],
                },
            )

        self.assertEqual(single.status_code, 200)
        self.assertEqual(single.json()["rendered_assets_count"], 1)
        self.assertEqual(single.json()["rendered_assets"], [f"{ASSETS}/manual.jpg"])

        self.assertEqual(several.status_code, 200)
        self.assertEqual(several.json()["rendered_assets_count"], 3)
        self.assertEqual(
            several.json()["rendered_assets"],
            [
                f"{ASSETS}/graphtec_chart_01.png",
                f"{ASSETS}/manual.jpg",
                f"{ASSETS}/chart03_simpati_acquisition_01.png",
            ],
        )
        forwarded = generate_report_mock.call_args_list[1].kwargs["selected_rendered_assets"]
        self.assertEqual(forwarded, several.json()["rendered_assets"])
        self.assertNotIn(f"{ASSETS}/unselected.png", forwarded)

        self.assertEqual(empty.status_code, 200)
        self.assertEqual(empty.json()["rendered_assets_count"], 0)
        self.assertEqual(
            generate_report_mock.call_args_list[2].kwargs["selected_rendered_assets"],
            [],
        )

    @patch(
        "backend.app.services.report_generation."
        "generate_climatic_report"
    )
    def test_generate_report_endpoint_rejects_invalid_selections(
        self,
        generate_report_mock,
    ):
        assets = self.test_root / ASSETS
        write_image(assets / "chart.png")
        (assets / "data.csv").write_text("1", encoding="utf-8")
        write_image(self.test_root / "04_Report" / "outside.png")
        cases = [
            (["../outside.png"], 400),
            ([str((assets / "chart.png").resolve())], 400),
            ([r"C:\\Tests\\chart.png"], 400),
            (["04_Report/outside.png"], 400),
            ([f"{ASSETS}/missing.png"], 404),
            ([f"{ASSETS}/data.csv"], 415),
            ([f"{ASSETS}/chart.png", f"{ASSETS}/chart.png"], 400),
        ]

        with patch(
            "backend.app.services.report_generation."
            "POWERPOINT_TEMPLATE_PATH",
            self.template_path,
        ):
            for selection, status in cases:
                response = self.client.post(
                    "/projects/generate-report",
                    json={
                        "test_root": str(self.test_root),
                        "selected_rendered_assets": selection,
                    },
                )
                self.assertEqual(response.status_code, status, selection)
                self.assertFalse(response.json()["success"])
                self.assertEqual(len(response.json()["errors"]), 1)

        generate_report_mock.assert_not_called()

    @patch(
        "backend.app.services.report_generation."
        "generate_climatic_report"
    )
    def test_generate_report_endpoint_returns_structured_error(
        self,
        generate_report_mock,
    ):
        generate_report_mock.side_effect = ValueError(
            "The PowerPoint template is invalid."
        )

        with patch(
            "backend.app.services.report_generation."
            "POWERPOINT_TEMPLATE_PATH",
            self.template_path,
        ):
            response = self.client.post(
                "/projects/generate-report",
                json={"test_root": str(self.test_root)},
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {
                "success": False,
                "test_root": str(self.test_root.resolve()),
                "report_path": None,
                "report_name": None,
                "rendered_assets_count": 0,
                "rendered_assets": [],
                "assembly_photos_count": 0,
                "assembly_photos": [],
                "result_photos_count": 0,
                "result_photos": [],
                "errors": [
                    {
                        "code": "report_generation_invalid_project",
                        "message": "The PowerPoint template is invalid.",
                        "exception_type": "ValueError",
                    }
                ],
            },
        )
        generate_report_mock.assert_called_once_with(
            test_root=self.test_root.resolve(),
            template_path=self.template_path.resolve(),
            selected_rendered_assets=[],
            selected_assembly_photos=[],
            selected_result_photos=[],
        )


if __name__ == "__main__":
    unittest.main()
