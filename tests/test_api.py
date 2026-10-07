import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from project_fixtures import add_evidence, build_test_folder

from backend.app.main import app


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
                "version": "0.4.0",
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
                "csv",
                "datalogger",
                "graphtec",
                "simpati_file",
            },
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
        project_routes = {
            (method, route.path)
            for route in app.routes
            if getattr(route, "path", "").startswith("/projects/")
            for method in getattr(route, "methods", set())
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
