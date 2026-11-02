"""Endpoint tests for the evidence photo selection of the report."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from project_fixtures import add_evidence, build_test_folder, write_json
from backend.app.main import app

GENERATE = "backend.app.services.report_generation.generate_climatic_report"
TEMPLATE = "backend.app.services.report_generation.POWERPOINT_TEMPLATE_PATH"


def set_type(directory: Path, type_: str) -> None:
    descriptor = json.loads((directory / "evidence.json").read_text(encoding="utf-8"))
    descriptor["type"] = type_
    write_json(directory / "evidence.json", descriptor)


class EvidencePhotoApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self._tmp = tempfile.TemporaryDirectory()
        self.root = build_test_folder(Path(self._tmp.name) / "TEST - 001")
        initial = add_evidence(self.root, "00_Initial", sequence=0,
                               photos=[f"i{n}.jpg" for n in range(1, 6)])
        set_type(initial, "initial")
        final = add_evidence(self.root, "01_Final", sequence=1, photos=["f1.jpg", "gone.jpg"])
        (final / "gone.jpg").unlink()
        set_type(final, "final")
        self.template = Path(self._tmp.name) / "template.pptx"
        self.template.write_bytes(b"template")
        self.report = self.root / "04_Report" / "report.pptx"

    def tearDown(self):
        self._tmp.cleanup()

    def test_inspection_reports_section_and_relative_paths(self):
        response = self.client.post("/projects/inspect", json={"test_root": str(self.root)})
        self.assertEqual(response.status_code, 200)
        evidences = response.json()["evidences"]
        self.assertEqual(evidences["assembly_max_photos"], 4)
        self.assertEqual(evidences["photos_per_slide"], 2)
        by_folder = {e["folder"]: e for e in evidences["evidences"]}
        self.assertEqual(by_folder["00_Initial"]["report_section"], "assembly")
        self.assertEqual(by_folder["01_Final"]["report_section"], "results")
        photos = by_folder["01_Final"]["photos"]
        self.assertEqual(
            [(p["relative_path"], p["selectable"]) for p in photos],
            [("02_Evidences/01_Final/f1.jpg", True), ("02_Evidences/01_Final/gone.jpg", False)],
        )

    def test_evidence_photo_is_served_and_paths_are_confined(self):
        ok = self.client.get("/projects/evidence-photo",
                             params={"test_root": str(self.root), "relative_path": "02_Evidences/01_Final/f1.jpg"})
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.headers["content-type"], "image/jpeg")
        for path, status in [
            ("02_Evidences/../04_Report/test_metadata.json", 400),
            ("02_Evidences/01_Final/gone.jpg", 404),
            ("02_Evidences/01_Final/evidence.json", 404),
            ("04_Report/_RenderedAssets/x.png", 400),
        ]:
            with self.subTest(path=path):
                response = self.client.get("/projects/evidence-photo",
                                           params={"test_root": str(self.root), "relative_path": path})
                self.assertEqual(response.status_code, status)
                self.assertFalse(response.json()["success"])

    def generate(self, payload):
        with patch(GENERATE, return_value=self.report) as generate_mock, patch(TEMPLATE, self.template):
            response = self.client.post("/projects/generate-report", json={"test_root": str(self.root), **payload})
        return response, generate_mock

    def test_selection_is_forwarded_in_automatic_order(self):
        response, generate_mock = self.generate({
            "selected_assembly_photos": ["02_Evidences/00_Initial/i3.jpg", "02_Evidences/00_Initial/i1.jpg"],
            "selected_result_photos": [],
        })
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["assembly_photos"], ["02_Evidences/00_Initial/i1.jpg", "02_Evidences/00_Initial/i3.jpg"])
        self.assertEqual(body["assembly_photos_count"], 2)
        self.assertEqual(body["result_photos"], [])
        kwargs = generate_mock.call_args.kwargs
        self.assertEqual(kwargs["selected_assembly_photos"], body["assembly_photos"])
        self.assertEqual(kwargs["selected_result_photos"], [])

    def test_omitted_selection_uses_first_four_assembly_photos(self):
        response, _ = self.generate({})
        self.assertEqual(response.json()["assembly_photos_count"], 4)
        self.assertEqual(response.json()["result_photos"], ["02_Evidences/01_Final/f1.jpg"])

    def test_invalid_selections_are_structured_errors(self):
        cases = [
            ({"selected_assembly_photos": [f"02_Evidences/00_Initial/i{n}.jpg" for n in range(1, 6)]},
             400, "report_generation_evidence_photo_limit"),
            ({"selected_assembly_photos": ["02_Evidences/01_Final/f1.jpg"]},
             400, "report_generation_invalid_evidence_photo"),
            ({"selected_result_photos": ["02_Evidences/01_Final/gone.jpg"]},
             404, "report_generation_evidence_photo_not_found"),
            ({"selected_result_photos": ["../outside.jpg"]},
             400, "report_generation_invalid_evidence_photo"),
        ]
        for payload, status, code in cases:
            with self.subTest(payload=payload):
                response, generate_mock = self.generate(payload)
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.json()["errors"][0]["code"], code)
                generate_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
