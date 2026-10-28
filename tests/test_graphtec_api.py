"""Tests for the Graphtec service and the /projects/graphtec endpoints."""

import base64
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from graphtec_fixtures import ARBITRARY_NAMES, DCW_TEXT, IR_TEXT, write_graphtec_file
from project_fixtures import build_test_folder

from backend.app.main import app
from backend.app.models.graphtec import GraphtecChartSettings
from backend.app.services.graphtec_inspection import (
    MAX_PREVIEW_RECORDS,
    GraphtecServiceError,
    inspect_project_graphtec,
    preview_project_graphtec_chart,
)

GRAPHTEC = "03_Data/02_Graphtec"


def png_from_data_url(data_url: str) -> Image.Image:
    prefix = "data:image/png;base64,"
    assert data_url.startswith(prefix)
    return Image.open(BytesIO(base64.b64decode(data_url[len(prefix):])))


class GraphtecFolderMixin:
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary_directory.name)
        self.test_root = build_test_folder(self.workspace / "TEST - 001")
        write_graphtec_file(self.test_root, "measurement.txt", IR_TEXT)
        self.relative_path = f"{GRAPHTEC}/measurement.txt"
        (self.test_root / "03_Data/01_SIMPATI/acquisition.txt").write_text(IR_TEXT, encoding="utf-8")
        (self.test_root / "03_Data/03_CANoe/trace.txt").write_text(IR_TEXT, encoding="utf-8")
        outside = self.workspace / "outside.txt"
        outside.write_text(IR_TEXT, encoding="utf-8")
        self.outside = outside

    def tearDown(self):
        self.temporary_directory.cleanup()


class GraphtecServiceTests(GraphtecFolderMixin, unittest.TestCase):
    """Service-level checks of the same rules enforced by the endpoints."""

    def error_of(self, relative_path):
        with self.assertRaises(GraphtecServiceError) as context:
            inspect_project_graphtec(self.test_root, relative_path)
        return context.exception

    def test_valid_inspection(self):
        result = inspect_project_graphtec(self.test_root, self.relative_path)

        self.assertTrue(result.success)
        self.assertEqual(result.source, "graphtec")
        self.assertEqual(result.format, "graphtec_txt_tabulated")
        self.assertEqual(result.file_name, "measurement.txt")
        self.assertEqual(result.relative_path, self.relative_path)
        self.assertEqual(result.records_count, 11)
        self.assertEqual(result.test_types, ["IR"])
        self.assertEqual(result.statuses, ["TEST", "PASS"])
        self.assertEqual(result.phases, ["R", "T", "D"])
        self.assertEqual(result.final_result, "PASS")
        self.assertEqual([s.id for s in result.available_series], ["voltage", "resistance"])
        self.assertEqual(result.original_units, {"voltage": ["kV"], "resistance": ["Mohm", "Gohm"]})
        self.assertEqual(result.normalized_units["resistance"], "Mohm")
        self.assertEqual(result.elapsed_time_start, 0.0)
        self.assertEqual(result.elapsed_time_end, 14.8)
        self.assertEqual(result.duration_seconds, 14.8)
        self.assertEqual(result.limited_values_count, 3)
        self.assertEqual(result.default_title, "Graphtec IR - Channel 1")
        self.assertEqual(result.warnings, [])
        self.assertEqual(result.errors, [])
        self.assertEqual(len(result.chart_data.elapsed_time_seconds), 11)
        self.assertEqual(result.chart_data.measurement_operator[7], ">")

    def test_preview_records_are_limited(self):
        lines = IR_TEXT.splitlines()
        body = [lines[0].replace("R=000.0s", f"R={i / 10:05.1f}s") for i in range(60)]
        write_graphtec_file(self.test_root, "long.txt", "\n".join(body) + "\n")

        result = inspect_project_graphtec(self.test_root, f"{GRAPHTEC}/long.txt")

        self.assertEqual(result.records_count, 60)
        self.assertEqual(len(result.preview_records), MAX_PREVIEW_RECORDS)
        self.assertTrue(result.preview_truncated)
        self.assertEqual(len(result.chart_data.elapsed_time_seconds), 60)

    def test_path_with_parent_components(self):
        for path in ("../outside.txt", f"{GRAPHTEC}/../01_SIMPATI/acquisition.txt", "..\\outside.txt"):
            error = self.error_of(path)
            self.assertEqual(error.status_code, 400, path)
            self.assertEqual(error.errors[0].code, "graphtec_invalid_path")

    def test_absolute_paths(self):
        for path in (str(self.outside), str((self.test_root / self.relative_path).resolve()), "C:\\Windows\\win.ini", "/etc/passwd", "\\\\server\\share\\x.txt"):
            error = self.error_of(path)
            self.assertEqual(error.errors[0].code, "graphtec_invalid_path", path)

    def test_external_file_through_a_link_is_rejected(self):
        link = self.test_root / GRAPHTEC / "linked.txt"
        try:
            link.symlink_to(self.outside)
        except (OSError, NotImplementedError):
            self.skipTest("Symbolic links are not available.")
        error = self.error_of(f"{GRAPHTEC}/linked.txt")
        self.assertIn("02_Graphtec", error.errors[0].message)

    def test_simpati_and_canoe_files_are_rejected(self):
        for path in ("03_Data/01_SIMPATI/acquisition.txt", "03_Data/03_CANoe/trace.txt", "04_Report/test_metadata.json"):
            error = self.error_of(path)
            self.assertEqual(error.errors[0].code, "graphtec_invalid_path", path)

    def test_subfolders_and_missing_files_are_rejected(self):
        write_graphtec_file(self.test_root, "archive/old.txt", IR_TEXT)
        for path in (f"{GRAPHTEC}/archive/old.txt", f"{GRAPHTEC}/missing.txt", GRAPHTEC, ""):
            error = self.error_of(path)
            self.assertEqual(error.errors[0].code, "graphtec_invalid_path", path)

    def test_unsupported_extension(self):
        write_graphtec_file(self.test_root, "measurement.csv", IR_TEXT)
        error = self.error_of(f"{GRAPHTEC}/measurement.csv")
        self.assertEqual(error.status_code, 415)
        self.assertEqual(error.errors[0].code, "graphtec_unsupported_format")

    def test_unsupported_content(self):
        write_graphtec_file(self.test_root, "other.txt", "Time;CH1;CH2\n0;1;2\n")
        error = self.error_of(f"{GRAPHTEC}/other.txt")
        self.assertEqual(error.status_code, 415)
        self.assertIn("tab-separated TXT", error.errors[0].message)

    def test_invalid_lines_are_structured_without_traceback(self):
        write_graphtec_file(self.test_root, "broken.txt", IR_TEXT + "1\tIR\tTEST\tbad\t1Mohm\tD=006.0s\n")
        error = self.error_of(f"{GRAPHTEC}/broken.txt")

        self.assertEqual(error.status_code, 400)
        self.assertEqual(error.errors[0].code, "graphtec_invalid_file")
        self.assertTrue(any("Line 12" in e.message for e in error.errors))
        for item in error.errors:
            self.assertNotIn("Traceback", item.message)
            self.assertNotIn('File "', item.message)

    def test_preview_returns_a_png_and_saves_nothing(self):
        response = preview_project_graphtec_chart(
            self.test_root, self.relative_path,
            GraphtecChartSettings(series=["voltage", "resistance"]),
        )

        self.assertTrue(response.success)
        self.assertEqual([a.label for a in response.axes], ["Voltage [kV]", "Resistance [Mohm]"])
        self.assertEqual(response.x_axis_label, "Elapsed time [s]")
        self.assertEqual(response.limited_points, 3)
        with png_from_data_url(response.image_base64) as image:
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.size, (response.width, response.height))
        self.assertFalse((self.test_root / "04_Report" / "_RenderedAssets").exists())

    def test_invalid_chart_configuration(self):
        for settings in (
            GraphtecChartSettings(series=["current"]),
            GraphtecChartSettings(series=["voltage"], time_min=5, time_max=1),
            GraphtecChartSettings(series=["voltage"], time_min=50, time_max=60),
        ):
            with self.assertRaises(GraphtecServiceError) as context:
                preview_project_graphtec_chart(self.test_root, self.relative_path, settings)
            self.assertEqual(context.exception.status_code, 400)
            self.assertEqual(context.exception.errors[0].code, "graphtec_invalid_chart_config")

    def test_name_independence(self):
        results = []
        for name in ARBITRARY_NAMES:
            write_graphtec_file(self.test_root, name, DCW_TEXT)
            result = inspect_project_graphtec(self.test_root, f"{GRAPHTEC}/{name}")
            data = result.model_dump() if hasattr(result, "model_dump") else dict(result.__dict__)
            self.assertEqual(data.pop("file_name"), name)
            self.assertEqual(data.pop("relative_path"), f"{GRAPHTEC}/{name}")
            results.append(data)
        for data in results[1:]:
            self.assertEqual(data, results[0])
        self.assertEqual(results[0]["test_types"], ["DCW"])


class GraphtecEndpointTests(GraphtecFolderMixin, unittest.TestCase):
    """HTTP contract of the /projects/graphtec endpoints."""

    def setUp(self):
        super().setUp()
        self.client = TestClient(app)

    def post(self, path, **body):
        body.setdefault("test_root", str(self.test_root))
        return self.client.post(f"/projects/graphtec/{path}", json=body)

    def chart(self, **chart):
        chart.setdefault("series", ["voltage", "resistance"])
        return chart

    def test_valid_inspection(self):
        response = self.post("inspect", relative_path=self.relative_path)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["source"], "graphtec")
        self.assertEqual(body["format"], "graphtec_txt_tabulated")
        self.assertEqual(body["test_types"], ["IR"])
        self.assertEqual(body["final_result"], "PASS")
        record = body["preview_records"][7]
        self.assertEqual(record["raw_measurement"], ">50Gohm")
        self.assertEqual(record["measurement_operator"], ">")
        self.assertEqual(record["normalized_value"], 50000.0)
        self.assertEqual(record["normalized_unit"], "Mohm")

    def test_parent_path(self):
        response = self.post("inspect", relative_path="../outside.txt")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errors"][0]["code"], "graphtec_invalid_path")

    def test_absolute_path(self):
        response = self.post("inspect", relative_path=str(self.outside))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

    def test_external_file(self):
        response = self.post("inspect", relative_path=f"{GRAPHTEC}/../../../outside.txt")
        self.assertEqual(response.status_code, 400)

    def test_simpati_file(self):
        response = self.post("inspect", relative_path="03_Data/01_SIMPATI/acquisition.txt")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errors"][0]["code"], "graphtec_invalid_path")

    def test_canoe_file(self):
        response = self.post("inspect", relative_path="03_Data/03_CANoe/trace.txt")
        self.assertEqual(response.status_code, 400)

    def test_unsupported_extension(self):
        write_graphtec_file(self.test_root, "measurement.gbd", IR_TEXT)
        response = self.post("inspect", relative_path=f"{GRAPHTEC}/measurement.gbd")
        self.assertEqual(response.status_code, 415)
        self.assertEqual(response.json()["errors"][0]["code"], "graphtec_unsupported_format")

    def test_structured_error_without_traceback(self):
        write_graphtec_file(self.test_root, "broken.txt", "1\tIR\tTEST\t1kV\t1Mohm\tX=1s\n")
        response = self.post("inspect", relative_path=f"{GRAPHTEC}/broken.txt")

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertFalse(body["success"])
        self.assertEqual(body["errors"][0]["code"], "graphtec_invalid_file")
        self.assertNotIn("Traceback", response.text)

    def test_limited_preview(self):
        response = self.post("inspect", relative_path=self.relative_path)
        self.assertLessEqual(len(response.json()["preview_records"]), MAX_PREVIEW_RECORDS)

    def test_valid_chart_preview(self):
        response = self.post("preview-chart", relative_path=self.relative_path, chart=self.chart())

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["image_base64"].startswith("data:image/png;base64,"))
        self.assertEqual([a["position"] for a in body["axes"]], ["left", "right"])

    def test_invalid_configuration(self):
        response = self.post("preview-chart", relative_path=self.relative_path, chart=self.chart(series=["current"]))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errors"][0]["code"], "graphtec_invalid_chart_config")

        response = self.post("preview-chart", relative_path=self.relative_path, chart=self.chart(series=[]))
        self.assertEqual(response.status_code, 422)

    def test_invalid_interval(self):
        response = self.post(
            "preview-chart",
            relative_path=self.relative_path,
            chart=self.chart(time_min=8, time_max=2),
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("start time", response.json()["errors"][0]["message"])

    def test_save_list_open_and_delete(self):
        save = self.post("save-chart", relative_path=self.relative_path, chart=self.chart())
        self.assertEqual(save.status_code, 200)
        self.assertEqual(save.json()["chart_name"], "graphtec_chart_01.png")
        self.assertEqual(save.json()["metadata_name"], "graphtec_chart_01.json")

        listing = self.post("charts")
        self.assertEqual(listing.json()["charts_count"], 1)

        image = self.client.get(
            "/projects/graphtec/chart",
            params={"test_root": str(self.test_root), "chart_name": "graphtec_chart_01.png"},
        )
        self.assertEqual(image.status_code, 200)
        self.assertEqual(image.headers["content-type"], "image/png")

        deleted = self.post("delete-chart", chart_name="graphtec_chart_01.png")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.json()["charts_count"], 0)

        missing = self.post("delete-chart", chart_name="graphtec_chart_01.png")
        self.assertEqual(missing.status_code, 404)

    def test_name_independence(self):
        bodies = []
        for name in ARBITRARY_NAMES:
            write_graphtec_file(self.test_root, name, IR_TEXT)
            body = self.post("inspect", relative_path=f"{GRAPHTEC}/{name}").json()
            body.pop("file_name")
            body.pop("relative_path")
            bodies.append(body)
        for body in bodies[1:]:
            self.assertEqual(body, bodies[0])


if __name__ == "__main__":
    unittest.main()
