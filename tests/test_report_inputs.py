"""Persistencia independiente, compatibilidad y contrato de configuración."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from backend.app.main import app
from project_fixtures import build_test_folder
from simpati_fixtures import copy_fixture, X01_FIXTURE, X04_FIXTURE
from src.report_generator.report_inputs import ReportInputs, load_report_inputs, save_report_inputs, inputs_path
from src.report_generator.standards import chamber_description, description_values
from src.report_generator.version_check import VersionCheck


class ReportInputsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = build_test_folder(Path(self.temp.name) / "TEST - 001")

    def test_new_and_deleted_working_are_empty(self):
        self.assertEqual(load_report_inputs(self.root), (ReportInputs(), []))
        save_report_inputs(self.root, {"test_type": "Nb"})
        shutil.rmtree(inputs_path(self.root).parent)
        self.assertEqual(load_report_inputs(self.root), (ReportInputs(), []))

    def test_roundtrip_preserves_metadata_bytes(self):
        metadata = self.root / "04_Report/test_metadata.json"
        original = metadata.read_bytes()
        saved = save_report_inputs(self.root, {"test_type": "Ab", "measurement_points": [
            {"channel": "A:Temperature [°C]", "location": "Puerta", "function": "control"}]})
        self.assertEqual(load_report_inputs(self.root), (saved, []))
        self.assertEqual(metadata.read_bytes(), original)

    def test_invalid_and_unknown_version_are_ignored_and_preserved(self):
        path = inputs_path(self.root)
        path.parent.mkdir()
        for content in ("{", '{"schema_version": 999}', '{"test_type": "XYZ"}', '[1,2]'):
            path.write_text(content, encoding="utf-8")
            inputs, warnings = load_report_inputs(self.root)
            self.assertEqual(inputs, ReportInputs())
            self.assertTrue(warnings)
            self.assertEqual(path.read_text(encoding="utf-8"), content)

    def test_standard_metadata_has_priority_and_is_optional(self):
        self.assertEqual(description_values({}, {})[1], "—")
        self.assertEqual(description_values({}, {"test_type": "Nb"})[1], "IEC 60068-2-14:2023")
        self.assertEqual(description_values({"test": {"standard": "Customer edition"}}, {"test_type": "Nb"})[1], "Customer edition")

    def test_chamber_tokens(self):
        for token, expected in (("HU", "Humidity"), ("OVEN", "Oven"), ("TS", "Rapid")):
            for chamber in (f"TECLI00023 - CC {token} (OS)", f"tecli00023_cc-{token.lower()}(os)"):
                self.assertTrue(chamber_description(chamber).startswith(expected))
        self.assertEqual(chamber_description("TECLI00023 - CC UNKNOWN (OS)"), "—")
        self.assertEqual(chamber_description("HUMIDITY"), "—")

    @patch("backend.app.api.projects.check_application_version", return_value=VersionCheck(status="current", installed_version="0.6.0"))
    def test_api_load_save_and_selected_log_channels(self, _):
        client = TestClient(app)
        directory = self.root / "03_Data/01_SIMPATI"
        first = copy_fixture(X01_FIXTURE, directory)
        second = copy_fixture(X04_FIXTURE, directory)
        payload = {"test_root": str(self.root), "selected_simpati_files": [first.relative_to(self.root).as_posix()]}
        loaded = client.post("/projects/report-inputs/load", json=payload)
        self.assertEqual(loaded.status_code, 200)
        self.assertTrue(loaded.json()["channels"])
        self.assertEqual(set(loaded.json()["test_types"]), {"Na", "Nb", "Nc", "Ab", "Bb"})
        payload["selected_simpati_files"] = [second.relative_to(self.root).as_posix()]
        self.assertNotEqual(loaded.json()["channels"], client.post("/projects/report-inputs/load", json=payload).json()["channels"])
        saved = client.post("/projects/report-inputs/save", json={"test_root": str(self.root), "inputs": {"test_type": "Nb"}})
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(client.post("/projects/report-inputs/load", json={"test_root": str(self.root)}).json()["inputs"]["test_type"], "Nb")
        self.assertEqual(client.post("/projects/report-inputs/save", json={"test_root": str(self.root), "inputs": {"test_type": "Ad"}}).status_code, 422)
        payload["selected_simpati_files"] = ["../outside.x01"]
        self.assertEqual(client.post("/projects/report-inputs/load", json=payload).status_code, 400)
