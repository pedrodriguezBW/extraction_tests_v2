import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse

from project_fixtures import add_evidence, build_test_folder

from backend.app.main import app

from src.report_generator.version import __version__
from src.report_generator.version_check import VersionCheck


class HealthEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.version_check_patch = patch(
            "backend.app.main.check_application_version",
            return_value=VersionCheck(
                status="current",
                installed_version=__version__,
                current_version=__version__,
                package=(
                    r"\\vigvsfil1.global.borgwarner.net"
                    r"\vigproductengineering\ToolingVersions\generator.zip"
                ),
            ),
        )
        self.version_check_patch.start()
        self.addCleanup(self.version_check_patch.stop)

    def test_health_endpoint(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "ok",
                "application": "climatic-report-generator",
                "version": __version__,
                "version_check": {
                    "status": "current",
                    "installed_version": __version__,
                    "current_version": __version__,
                    "package": (
                        r"\\vigvsfil1.global.borgwarner.net"
                        r"\vigproductengineering\ToolingVersions\generator.zip"
                    ),
                    "warning": None,
                },
            },
        )

    def test_vite_development_origin_is_allowed(self):
        response = self.client.options(
            "/health",
            headers={
                "Origin": "http://localhost:1420",
                "Access-Control-Request-Method": "GET",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            "http://localhost:1420",
        )


class OutdatedVersionWriteProtectionTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.blocked_response = JSONResponse(
            status_code=409,
            content={"detail": "Update required; application is read-only."},
        )

    def test_chart_save_and_asset_delete_endpoints_are_blocked(self):
        requests = [
            (
                "/projects/simpati/save-chart",
                {
                    "test_root": r"C:\Tests\TEST - 001",
                    "relative_path": "03_Data/01_SIMPATI/acquisition.x01",
                    "image_base64": "aW1hZ2U=",
                },
            ),
            (
                "/projects/graphtec/save-chart",
                {
                    "test_root": r"C:\Tests\TEST - 001",
                    "relative_path": "03_Data/02_Graphtec/acquisition.txt",
                    "chart": {"series": ["voltage"]},
                },
            ),
            (
                "/projects/rendered-assets/delete",
                {
                    "test_root": r"C:\Tests\TEST - 001",
                    "relative_path": (
                        "04_Report/_RenderedAssets/chart.png"
                    ),
                },
            ),
        ]

        with patch(
            "backend.app.api.projects._outdated_version_response",
            return_value=self.blocked_response,
        ):
            for url, body in requests:
                with self.subTest(url=url):
                    response = self.client.post(url, json=body)
                    self.assertEqual(response.status_code, 409)
                    self.assertEqual(
                        response.json()["detail"],
                        "Update required; application is read-only.",
                    )


class ProjectInspectionEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.temporary_directory = tempfile.TemporaryDirectory()
        workspace = Path(self.temporary_directory.name)
        self.test_root = build_test_folder(workspace / "TEST - 001")
        add_evidence(
            self.test_root,
            "00_Initial",
            sequence=0,
            photos=["initial.jpg"],
        )
        self.template_path = workspace / "template.pptx"
        self.template_path.write_bytes(b"template")

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_inspect_endpoint_returns_new_contract(self):
        with patch(
            "backend.app.services.project_inspection."
            "POWERPOINT_TEMPLATE_PATH",
            self.template_path,
        ):
            response = self.client.post(
                "/projects/inspect",
                json={"test_root": str(self.test_root)},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["valid"])
        self.assertTrue(body["metadata"]["found"])
        self.assertTrue(body["metadata"]["valid"])
        self.assertEqual(body["evidences"]["evidences_count"], 1)
        self.assertEqual(body["evidences"]["photos_found_count"], 1)
        self.assertEqual(
            set(body["data"]),
            {
                "directory",
                "simpati",
                "graphtec",
                "canoe",
                "simpati_file",
                "simpati_acquisitions",
            },
        )
        self.assertEqual(
            body["data"]["simpati"]["files"],
            [],
        )
        self.assertEqual(
            Path(body["data"]["canoe"]["path"]),
            (self.test_root / "03_Data" / "03_CANoe").resolve(),
        )

    def test_inspect_endpoint_returns_source_file_inventory(self):
        graphtec = self.test_root / "03_Data" / "02_Graphtec"
        (graphtec / "b_run.csv").write_bytes(b"12345")
        (graphtec / "A_run.CSV").write_bytes(b"123")
        (graphtec / "nested").mkdir()

        with patch(
            "backend.app.services.project_inspection."
            "POWERPOINT_TEMPLATE_PATH",
            self.template_path,
        ):
            response = self.client.post(
                "/projects/inspect",
                json={"test_root": str(self.test_root)},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        source = body["data"]["graphtec"]
        self.assertTrue(source["found"])
        self.assertEqual(source["file_count"], 2)
        self.assertEqual(
            source["files"],
            [
                {
                    "name": "A_run.CSV",
                    "relative_path": "03_Data/02_Graphtec/A_run.CSV",
                    "extension": ".csv",
                    "size": 3,
                },
                {
                    "name": "b_run.csv",
                    "relative_path": "03_Data/02_Graphtec/b_run.csv",
                    "extension": ".csv",
                    "size": 5,
                },
            ],
        )
        self.assertNotIn("input_workbook", body)
        self.assertNotIn("setup_images", body)

    def test_inspect_endpoint_rejects_empty_path(self):
        response = self.client.post(
            "/projects/inspect",
            json={"test_root": ""},
        )

        self.assertEqual(response.status_code, 422)

    def test_project_routes_match_the_agent_metadata_workflow(self):
        openapi_paths = app.openapi()["paths"]

        project_routes = {
            (method.upper(), path)
            for path, operations in openapi_paths.items()
            if path.startswith("/projects/")
            for method in operations
            if method.lower()
            in {
                "get",
                "post",
                "put",
                "patch",
                "delete",
                "options",
                "head",
            }
        }

        self.assertEqual(
            project_routes,
            {
                ("POST", "/projects/inspect"),
                ("POST", "/projects/report-inputs/load"),
                ("POST", "/projects/report-inputs/save"),
                ("POST", "/projects/simpati/tolerances"),
                ("GET", "/projects/evidence-photo"),
                ("POST", "/projects/generate-report"),
                ("POST", "/projects/simpati/inspect"),
                ("POST", "/projects/simpati/save-chart"),
                ("POST", "/projects/rendered-assets"),
                ("GET", "/projects/rendered-asset"),
                ("POST", "/projects/rendered-assets/delete"),
                ("POST", "/projects/graphtec/inspect"),
                ("POST", "/projects/graphtec/preview-chart"),
                ("POST", "/projects/graphtec/save-chart"),
            },
        )

if __name__ == "__main__":
    unittest.main()
