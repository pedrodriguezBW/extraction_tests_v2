import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.report_generation import (
    ReportGenerationError,
    generate_project_report,
)


class ReportGenerationServiceTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.test_root = Path(self.temporary_directory.name)
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
        self.assertEqual(result.errors, [])
        generate_report_mock.assert_called_once_with(
            test_root=self.test_root.resolve(),
            template_path=self.template_path.resolve(),
        )

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


class ReportGenerationEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.test_root = Path(self.temporary_directory.name)
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
                "errors": [],
            },
        )
        generate_report_mock.assert_called_once_with(
            test_root=self.test_root.resolve(),
            template_path=self.template_path.resolve(),
        )

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
        )


if __name__ == "__main__":
    unittest.main()
