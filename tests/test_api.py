import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from project_fixtures import add_evidence, build_test_folder

from backend.app.main import app

from src.report_generator.version import __version__


class HealthEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "ok",
                "application": "climatic-report-generator",
                "version": __version__,
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
                ("POST", "/projects/generate-report"),
                ("POST", "/projects/simpati/inspect"),
                ("POST", "/projects/simpati/save-chart"),
                ("POST", "/projects/simpati/charts"),
                ("GET", "/projects/simpati/chart"),
                ("POST", "/projects/simpati/delete-chart"),
            },
        )

if __name__ == "__main__":
    unittest.main()
