"""Tolerancias en meseta sobre datos sintéticos y exportaciones reales."""

import json
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

import pandas as pd
from simpati_fixtures import X01_FIXTURE, X04_FIXTURE
from src.report_generator.simpati.channels import classify_channels
from src.report_generator.simpati.parser import read_simpati_acquisition
from src.report_generator.simpati.tolerances import evaluate_tolerances
from fastapi.testclient import TestClient
from backend.app.main import app
from simpati_fixtures import copy_fixture
from test_simpati_inspection import build_png_data_url
from src.report_generator.version_check import VersionCheck


def synthetic_acquisition():
    # Dos ciclos completos delimitados por rampas y temperatura ambiente.
    targets = [23] + [-40] * 31 + list(range(-30, 80, 10)) + [85] * 31 + list(range(70, -40, -10)) + [-40] * 31 + list(range(-30, 80, 10)) + [85] * 31 + [23]
    frame = pd.DataFrame({"Timestamp": pd.date_range("2026-01-01", periods=len(targets), freq="min"),
                          "A:Temperature [°C]": targets, "N:Temperature [°C]": targets})
    return SimpleNamespace(dataframe=frame, rejected_count=0)


class ToleranceTests(unittest.TestCase):
    def evaluate(self, acquisition, test_type="Nb", **kwargs):
        return evaluate_tolerances(acquisition, classify_channels(acquisition.dataframe), test_type, "A:Temperature [°C]", **kwargs)

    def test_plateaus_ok_and_complete_cycles(self):
        result = self.evaluate(synthetic_acquisition())
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["cycles"], 2)
        self.assertEqual(result["t1_minutes"], 30)
        self.assertEqual((result["ta_c"], result["tb_c"]), (-40, 85))
        self.assertIsNone(result["stabilization_delta_ts_k"])

    def test_excursions_grouped_and_ramps_and_settling_excluded(self):
        acquisition = synthetic_acquisition()
        acquisition.dataframe.loc[1:4, "A:Temperature [°C]"] = 1000
        acquisition.dataframe.loc[33:40, "A:Temperature [°C]"] = 1000
        self.assertEqual(self.evaluate(acquisition)["status"], "OK")
        acquisition.dataframe.loc[10:11, "A:Temperature [°C]"] = -37
        acquisition.dataframe.loc[15, "A:Temperature [°C]"] = -43
        result = self.evaluate(acquisition)
        self.assertEqual(result["status"], "NOK")
        self.assertEqual(result["out_of_tolerance_segments"], 2)
        self.assertEqual(len(result["excursions"][0]), 2)
        context = dict(result["excursion_context"])
        for i in (9, 10, 11, 12, 14, 15, 16):
            self.assertEqual(context[acquisition.dataframe["Timestamp"].iloc[i].isoformat()],
                             acquisition.dataframe["A:Temperature [°C]"].iloc[i])

    def test_boundary_is_inclusive_and_missing_measurements_prevent_ok(self):
        acquisition = synthetic_acquisition()
        acquisition.dataframe.loc[10, "A:Temperature [°C]"] = -38
        self.assertEqual(self.evaluate(acquisition)["status"], "OK")
        acquisition.dataframe.loc[10, "A:Temperature [°C]"] = float("nan")
        result = self.evaluate(acquisition)
        self.assertIsNone(result["status"])
        self.assertEqual(result["cycles"], 2)
        self.assertEqual(result["t1_minutes"], 30)

    def test_long_exposure_settles_at_fifteen_minutes(self):
        acquisition = synthetic_acquisition()
        acquisition.dataframe["Timestamp"] = pd.date_range("2026-01-01", periods=len(acquisition.dataframe), freq="10min")
        acquisition.dataframe.loc[2, "A:Temperature [°C]"] = -30
        self.assertEqual(self.evaluate(acquisition)["status"], "OK")
        acquisition.dataframe.loc[3, "A:Temperature [°C]"] = -30
        self.assertEqual(self.evaluate(acquisition)["status"], "NOK")

    def test_gaps_and_short_logs_never_claim_ok(self):
        acquisition = synthetic_acquisition()
        acquisition.dataframe.loc[20:, "Timestamp"] += pd.Timedelta(hours=1)
        self.assertIsNone(self.evaluate(acquisition)["status"])
        acquisition = synthetic_acquisition()
        acquisition.dataframe = acquisition.dataframe.iloc[:4]
        self.assertIsNone(self.evaluate(acquisition)["status"])

    def test_gap_does_not_erase_complete_cycles_in_other_blocks(self):
        acquisition = synthetic_acquisition()
        acquisition.dataframe.loc[20:, "Timestamp"] += pd.Timedelta(hours=1)
        result = self.evaluate(acquisition)
        self.assertEqual(result["cycles"], 1)
        self.assertTrue(result["cycles_partial"])
        self.assertEqual(result["t1_minutes"], 30)

    def test_pair_cannot_cross_gap_between_complete_plateaus(self):
        acquisition = synthetic_acquisition()
        acquisition.dataframe = acquisition.dataframe.iloc[:75].copy()
        acquisition.dataframe.loc[36:, "Timestamp"] += pd.Timedelta(hours=1)
        result = self.evaluate(acquisition)
        self.assertEqual(result["complete_plateaus_count"], 2)
        self.assertIsNone(result["cycles"])
        self.assertTrue(result["cycles_partial"])

    def test_cycles_can_start_with_hot_plateau(self):
        acquisition = synthetic_acquisition()
        for column in ("A:Temperature [°C]", "N:Temperature [°C]"):
            acquisition.dataframe[column] = 45 - acquisition.dataframe[column]
        result = self.evaluate(acquisition)
        self.assertEqual(result["cycles"], 2)

    def test_exact_five_minute_plateaus_count_without_tolerance_window(self):
        targets = [23] + [-40] * 6 + [23] + [85] * 6 + [23]
        acquisition = SimpleNamespace(dataframe=pd.DataFrame({
            "Timestamp": pd.date_range("2026-01-01", periods=len(targets), freq="min"),
            "A:Temperature [°C]": targets, "N:Temperature [°C]": targets}), rejected_count=0)
        result = self.evaluate(acquisition)
        self.assertEqual(result["cycles"], 1)
        self.assertEqual(result["t1_minutes"], 5)
        self.assertIsNone(result["status"])

    def test_different_hot_and_cold_durations_are_reported_separately(self):
        targets = [23] + [-40] * 31 + [23] + [85] * 46 + [23]
        acquisition = SimpleNamespace(dataframe=pd.DataFrame({
            "Timestamp": pd.date_range("2026-01-01", periods=len(targets), freq="min"),
            "A:Temperature [°C]": targets, "N:Temperature [°C]": targets}), rejected_count=0)
        result = self.evaluate(acquisition)
        self.assertIsNone(result["t1_minutes"])
        self.assertEqual(result["t1_low_minutes"], 30)
        self.assertEqual(result["t1_high_minutes"], 45)
        self.assertEqual(result["cycles"], 1)

    def test_rejected_rows_do_not_erase_observed_metrics(self):
        acquisition = synthetic_acquisition()
        acquisition.rejected_count = 1
        result = self.evaluate(acquisition)
        self.assertEqual(result["cycles"], 2)
        self.assertEqual(result["t1_minutes"], 30)
        self.assertTrue(result["cycles_partial"])
        self.assertIsNone(result["status"])

    def test_cold_and_dry_heat_only_evaluate_relevant_extreme(self):
        acquisition = synthetic_acquisition()
        acquisition.dataframe.loc[50, "A:Temperature [°C]"] = 100
        self.assertEqual(self.evaluate(acquisition, "Ab")["status"], "OK")
        hot = self.evaluate(acquisition, "Bb")
        self.assertEqual(hot["status"], "NOK")
        self.assertIsNone(hot["ta_c"])
        self.assertIsNone(hot["cycles"])

    def test_missing_type_and_ambiguous_reference_are_rejected(self):
        acquisition = synthetic_acquisition()
        with self.assertRaises(ValueError):
            self.evaluate(acquisition, "")
        acquisition.dataframe["A:Temp specimen [°C]"] = 20
        acquisition.dataframe["N:Temp basket [°C]"] = 20
        channels = classify_channels(acquisition.dataframe)
        with self.assertRaises(ValueError):
            evaluate_tolerances(acquisition, channels, "Na", "A:Temp specimen [°C]")

    def test_fahrenheit_uses_two_kelvin_band(self):
        acquisition = synthetic_acquisition()
        acquisition.dataframe = acquisition.dataframe.rename(columns={"A:Temperature [°C]": "A:Temperature [°F]", "N:Temperature [°C]": "N:Temperature [°F]"})
        for column in ("A:Temperature [°F]", "N:Temperature [°F]"):
            acquisition.dataframe[column] = acquisition.dataframe[column] * 1.8 + 32
        acquisition.dataframe.loc[10, "A:Temperature [°F]"] += 3.7
        result = evaluate_tolerances(acquisition, classify_channels(acquisition.dataframe), "Nb", "A:Temperature [°F]")
        self.assertEqual(result["status"], "NOK")

    def test_real_logs_use_full_resolution_and_are_json_serializable(self):
        for path, role in ((X01_FIXTURE, "chamber_temperature"), (X04_FIXTURE, "basket_temperature")):
            acquisition = read_simpati_acquisition(path)
            channels = classify_channels(acquisition.dataframe)
            channel = next(c for c in channels if c.role == role)
            result = evaluate_tolerances(acquisition, channels, "Nb", channel.column)
            self.assertEqual(result["scope"], "full_acquisition")
            self.assertTrue(result["plateaus"])
            if path == X04_FIXTURE:
                self.assertGreater(result["cycles"], 0)
                self.assertGreater(result["complete_plateaus_count"], 0)
            json.dumps(result, allow_nan=False)

    @patch("backend.app.api.projects.check_application_version", return_value=VersionCheck(status="current", installed_version="0.6.0"))
    def test_api_persists_recomputed_full_resolution_result_with_png(self, _):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "04_Report").mkdir()
            path = copy_fixture(X01_FIXTURE, root / "03_Data/01_SIMPATI")
            acquisition = read_simpati_acquisition(path)
            channels = classify_channels(acquisition.dataframe)
            channel = next(c for c in channels if c.role == "chamber_temperature")
            request = {"test_root": str(root), "relative_path": path.relative_to(root).as_posix(),
                       "test_type": "Nb", "channel": channel.column}
            client = TestClient(app)
            preview = client.post("/projects/simpati/tolerances", json=request)
            self.assertEqual(preview.status_code, 200)
            saved = client.post("/projects/simpati/save-chart", json={
                "test_root": str(root), "relative_path": request["relative_path"], "image_base64": build_png_data_url(),
                "tolerances": {"test_type": "Nb", "channel": channel.column}})
            self.assertEqual(saved.status_code, 200)
            companions = list((root / "04_Report/_RenderedAssets").glob("*.json"))
            self.assertEqual(len(companions), 1)
            self.assertEqual(json.loads(companions[0].read_text(encoding="utf-8"))["tolerances"], preview.json())
