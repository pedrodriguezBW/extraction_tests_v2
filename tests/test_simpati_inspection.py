import base64
import json
import tempfile
import unittest
from datetime import datetime
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from fastapi.testclient import TestClient
from PIL import Image

from backend.app.main import app
from backend.app.services.simpati_inspection import (
    SimpatiChartSaveError,
    SimpatiInspectionError,
    inspect_project_simpati,
    save_project_simpati_chart,
)
from src.report_generator.assets.simpati_extractor import (
    SimpatiError,
    SimpatiFileNotFoundError,
    SimpatiFormatError,
    find_simpati_file,
    prepare_rendered_assets_directory,
)
from src.report_generator.rendered_assets import list_rendered_assets


def build_dataframe() -> pd.DataFrame:
    dataframe = pd.DataFrame(
        {
            "Timestamp": [
                datetime(2026, 9, 23, 8, 0, 0),
                datetime(2026, 9, 23, 10, 30, 0),
            ],
            "A:Temp canast [°C]": [21.5, 22.0],
            "N:Temp canast [°C]": [22.0, 22.0],
            "A:Cam calient [°C]": [80.0, 81.0],
            "N:Cam calient [°C]": [82.0, 82.0],
            "A:Cam fria [°C]": [-35.0, -34.0],
            "N:Cam fria [°C]": [-36.0, -36.0],
            "A:Pos canasta [%]": [0.0, 100.0],
        }
    )
    dataframe.attrs["encoding"] = "cp1252"
    return dataframe


def build_png_data_url() -> str:
    image_buffer = BytesIO()
    Image.new("RGB", (8, 6), "white").save(
        image_buffer,
        format="PNG",
    )
    encoded_image = base64.b64encode(
        image_buffer.getvalue()
    ).decode("ascii")
    return f"data:image/png;base64,{encoded_image}"


class SimpatiInspectionServiceTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.test_root = Path(self.temporary_directory.name)
        (self.test_root / "04_Report").mkdir()
        self.simpati_file = (
            self.test_root
            / "03_Data"
            / "01_SIMPATI"
            / "acquisition.x03"
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    @patch(
        "backend.app.services.simpati_inspection.read_simpati"
    )
    @patch(
        "backend.app.services.simpati_inspection.find_simpati_file"
    )
    def test_inspection_returns_acquisition_summary(
        self,
        find_simpati_mock,
        read_simpati_mock,
    ):
        find_simpati_mock.return_value = self.simpati_file
        read_simpati_mock.return_value = build_dataframe()

        result = inspect_project_simpati(self.test_root)

        self.assertTrue(result.success)
        self.assertTrue(result.available)
        self.assertEqual(result.file_name, "acquisition.x03")
        self.assertEqual(
            result.file_path,
            str(self.simpati_file.resolve()),
        )
        self.assertEqual(result.encoding, "cp1252")
        self.assertEqual(result.records_count, 2)
        self.assertEqual(
            result.acquisition_start,
            "2026-09-23T08:00:00",
        )
        self.assertEqual(
            result.acquisition_end,
            "2026-09-23T10:30:00",
        )
        self.assertEqual(
            result.channels,
            [
                "A:Temp canast [°C]",
                "N:Temp canast [°C]",
                "A:Cam calient [°C]",
                "N:Cam calient [°C]",
                "A:Cam fria [°C]",
                "N:Cam fria [°C]",
                "A:Pos canasta [%]",
            ],
        )
        self.assertEqual(
            [channel.label for channel in result.thermal_channels],
            [
                "Basket temperature",
                "Basket setpoint",
                "Hot chamber temperature",
                "Hot chamber setpoint",
                "Cold chamber temperature",
                "Cold chamber setpoint",
            ],
        )
        self.assertEqual(
            [channel.label for channel in result.advanced_channels],
            ["A:Pos canasta [%]"],
        )
        self.assertEqual(len(result.preview_timestamps), 2)
        find_simpati_mock.assert_called_once_with(
            self.test_root.resolve()
        )
        read_simpati_mock.assert_called_once_with(self.simpati_file)

    @patch(
        "backend.app.services.simpati_inspection.read_simpati"
    )
    @patch(
        "backend.app.services.simpati_inspection.find_simpati_file"
    )
    def test_missing_simpati_is_optional(
        self,
        find_simpati_mock,
        read_simpati_mock,
    ):
        find_simpati_mock.side_effect = SimpatiFileNotFoundError(
            "No .x03 file was found."
        )

        result = inspect_project_simpati(self.test_root)

        self.assertTrue(result.success)
        self.assertFalse(result.available)
        self.assertEqual(result.records_count, 0)
        self.assertEqual(result.channels, [])
        self.assertEqual(result.preview_timestamps, [])
        self.assertEqual(result.thermal_channels, [])
        self.assertEqual(result.advanced_channels, [])
        self.assertEqual(result.errors, [])
        read_simpati_mock.assert_not_called()

    @patch(
        "backend.app.services.simpati_inspection.read_simpati"
    )
    @patch(
        "backend.app.services.simpati_inspection.find_simpati_file"
    )
    def test_invalid_simpati_error_is_structured(
        self,
        find_simpati_mock,
        read_simpati_mock,
    ):
        find_simpati_mock.return_value = self.simpati_file
        read_simpati_mock.side_effect = SimpatiFormatError(
            "The SIMPATI channel header could not be identified."
        )

        with self.assertRaises(SimpatiInspectionError) as context:
            inspect_project_simpati(self.test_root)

        error = context.exception
        self.assertEqual(error.status_code, 400)
        self.assertEqual(
            error.error.code,
            "simpati_inspection_invalid_file",
        )
        self.assertEqual(
            error.error.message,
            "The SIMPATI channel header could not be identified.",
        )
        self.assertEqual(error.error.exception_type, "SimpatiFormatError")

    def test_chart_is_saved_as_a_rendered_asset(self):
        result = save_project_simpati_chart(
            self.test_root,
            build_png_data_url(),
        )

        expected_path = (
            self.test_root
            / "04_Report"
            / "_RenderedAssets"
            / "chart03_simpati_acquisition_01.png"
        )
        self.assertTrue(result.success)
        self.assertEqual(result.chart_name, expected_path.name)
        self.assertEqual(
            result.chart_path,
            str(expected_path.resolve()),
        )
        self.assertEqual(
            result.relative_path,
            "04_Report/_RenderedAssets/chart03_simpati_acquisition_01.png",
        )
        self.assertTrue(expected_path.is_file())
        metadata = json.loads(
            expected_path.with_suffix(".json").read_text(encoding="utf-8")
        )
        self.assertEqual(metadata["source"], "simpati")
        # The saved chart is part of the generic inventory.
        self.assertEqual(
            [(a.name, a.source) for a in list_rendered_assets(self.test_root).assets],
            [("chart03_simpati_acquisition_01.png", "simpati")],
        )
        self.assertEqual(result.assets_count, 1)
        self.assertEqual(
            [(a.name, a.source, a.relative_path) for a in result.assets],
            [(
                "chart03_simpati_acquisition_01.png",
                "simpati",
                "04_Report/_RenderedAssets/chart03_simpati_acquisition_01.png",
            )],
        )

    def test_chart_is_not_saved_without_report_folder(self):
        (self.test_root / "04_Report").rmdir()

        with self.assertRaises(SimpatiChartSaveError) as context:
            save_project_simpati_chart(
                self.test_root,
                build_png_data_url(),
            )

        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("04_Report", context.exception.error.message)
        self.assertFalse((self.test_root / "04_Report").exists())

    def test_invalid_chart_image_is_structured(self):
        invalid_image = base64.b64encode(b"not a png").decode("ascii")

        with self.assertRaises(SimpatiChartSaveError) as context:
            save_project_simpati_chart(
                self.test_root,
                invalid_image,
            )

        error = context.exception
        self.assertEqual(error.status_code, 400)
        self.assertEqual(
            error.error.code,
            "simpati_chart_invalid_image",
        )

    def test_saved_charts_never_overwrite_and_keep_natural_order(self):
        assets_directory = (
            self.test_root
            / "04_Report"
            / "_RenderedAssets"
        )
        assets_directory.mkdir()
        for chart_number in (10, 2):
            chart_path = assets_directory / (
                f"chart03_simpati_acquisition_{chart_number:02d}.png"
            )
            Image.new("RGB", (8, 6), "white").save(chart_path)

        result = save_project_simpati_chart(
            self.test_root,
            build_png_data_url(),
        )

        self.assertEqual(result.chart_name, "chart03_simpati_acquisition_01.png")
        self.assertEqual(
            [a.name for a in result.assets],
            [
                "chart03_simpati_acquisition_01.png",
                "chart03_simpati_acquisition_02.png",
                "chart03_simpati_acquisition_10.png",
            ],
        )

    def test_saved_chart_is_deleted_through_the_generic_inventory(self):
        first = save_project_simpati_chart(
            self.test_root,
            build_png_data_url(),
        )
        second = save_project_simpati_chart(
            self.test_root,
            build_png_data_url(),
        )

        from backend.app.services.rendered_assets import (
            delete_project_rendered_asset,
        )

        result = delete_project_rendered_asset(
            self.test_root,
            first.relative_path,
        )

        self.assertFalse(Path(first.chart_path).exists())
        self.assertFalse(Path(first.chart_path).with_suffix(".json").exists())
        self.assertEqual(result.assets_count, 1)
        self.assertEqual(
            [a.relative_path for a in result.assets],
            [second.relative_path],
        )


class SimpatiFolderTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.test_root = Path(self.temporary_directory.name)
        self.simpati_directory = self.test_root / "03_Data" / "01_SIMPATI"

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_acquisition_is_found_in_03_data(self):
        self.simpati_directory.mkdir(parents=True)
        acquisition = self.simpati_directory / "acquisition.x03"
        acquisition.write_text("data", encoding="utf-8")

        self.assertEqual(
            find_simpati_file(self.test_root),
            acquisition.resolve(),
        )

    def test_missing_simpati_folder_is_optional(self):
        with self.assertRaises(SimpatiFileNotFoundError) as context:
            find_simpati_file(self.test_root)

        self.assertIn("01_SIMPATI", str(context.exception))

    def test_several_acquisitions_are_ambiguous(self):
        self.simpati_directory.mkdir(parents=True)
        (self.simpati_directory / "a.x03").write_text("a", encoding="utf-8")
        (self.simpati_directory / "b.x03").write_text("b", encoding="utf-8")

        with self.assertRaises(SimpatiError):
            find_simpati_file(self.test_root)

    def test_rendered_assets_folder_is_created_inside_04_report(self):
        (self.test_root / "04_Report").mkdir()

        assets_directory = prepare_rendered_assets_directory(self.test_root)

        self.assertEqual(
            assets_directory,
            self.test_root.resolve() / "04_Report" / "_RenderedAssets",
        )
        self.assertTrue(assets_directory.is_dir())

    def test_rendered_assets_require_04_report(self):
        with self.assertRaises(FileNotFoundError):
            prepare_rendered_assets_directory(self.test_root)

        self.assertFalse((self.test_root / "04_Report").exists())


class SimpatiInspectionEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.test_root = Path(self.temporary_directory.name)
        (self.test_root / "04_Report").mkdir()
        self.simpati_file = (
            self.test_root
            / "03_Data"
            / "01_SIMPATI"
            / "acquisition.x03"
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    @patch(
        "backend.app.services.simpati_inspection.read_simpati"
    )
    @patch(
        "backend.app.services.simpati_inspection.find_simpati_file"
    )
    def test_endpoint_returns_acquisition_summary(
        self,
        find_simpati_mock,
        read_simpati_mock,
    ):
        find_simpati_mock.return_value = self.simpati_file
        read_simpati_mock.return_value = build_dataframe()

        response = self.client.post(
            "/projects/simpati/inspect",
            json={"test_root": str(self.test_root)},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertTrue(body["available"])
        self.assertEqual(body["file_name"], "acquisition.x03")
        self.assertEqual(body["encoding"], "cp1252")
        self.assertEqual(body["records_count"], 2)
        self.assertEqual(
            [channel["label"] for channel in body["thermal_channels"]],
            [
                "Basket temperature",
                "Basket setpoint",
                "Hot chamber temperature",
                "Hot chamber setpoint",
                "Cold chamber temperature",
                "Cold chamber setpoint",
            ],
        )
        self.assertEqual(len(body["preview_timestamps"]), 2)

    @patch(
        "backend.app.services.simpati_inspection.read_simpati"
    )
    @patch(
        "backend.app.services.simpati_inspection.find_simpati_file"
    )
    def test_endpoint_treats_missing_simpati_as_optional(
        self,
        find_simpati_mock,
        read_simpati_mock,
    ):
        find_simpati_mock.side_effect = SimpatiFileNotFoundError(
            "No .x03 file was found."
        )

        response = self.client.post(
            "/projects/simpati/inspect",
            json={"test_root": str(self.test_root)},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertFalse(body["available"])
        self.assertEqual(body["records_count"], 0)
        self.assertEqual(body["channels"], [])
        self.assertEqual(body["errors"], [])
        read_simpati_mock.assert_not_called()

    @patch(
        "backend.app.services.simpati_inspection.read_simpati"
    )
    @patch(
        "backend.app.services.simpati_inspection.find_simpati_file"
    )
    def test_endpoint_returns_structured_format_error(
        self,
        find_simpati_mock,
        read_simpati_mock,
    ):
        find_simpati_mock.return_value = self.simpati_file
        read_simpati_mock.side_effect = SimpatiFormatError(
            "The SIMPATI file is invalid."
        )

        response = self.client.post(
            "/projects/simpati/inspect",
            json={"test_root": str(self.test_root)},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["errors"],
            [
                {
                    "code": "simpati_inspection_invalid_file",
                    "message": "The SIMPATI file is invalid.",
                    "exception_type": "SimpatiFormatError",
                }
            ],
        )

    def test_save_chart_endpoint_returns_saved_path(self):
        response = self.client.post(
            "/projects/simpati/save-chart",
            json={
                "test_root": str(self.test_root),
                "image_base64": build_png_data_url(),
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(
            body["chart_name"],
            "chart03_simpati_acquisition_01.png",
        )
        self.assertTrue(Path(body["chart_path"]).is_file())
        self.assertEqual(body["assets_count"], 1)
        self.assertEqual(body["assets"][0]["source"], "simpati")

    def test_saved_chart_is_served_by_the_generic_endpoints(self):
        save_response = self.client.post(
            "/projects/simpati/save-chart",
            json={
                "test_root": str(self.test_root),
                "image_base64": build_png_data_url(),
            },
        )
        relative_path = save_response.json()["relative_path"]

        list_response = self.client.post(
            "/projects/rendered-assets",
            json={"test_root": str(self.test_root)},
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["assets_count"], 1)
        self.assertEqual(
            list_response.json()["assets"][0]["relative_path"], relative_path
        )

        open_response = self.client.get(
            "/projects/rendered-asset",
            params={
                "test_root": str(self.test_root),
                "relative_path": relative_path,
            },
        )
        self.assertEqual(open_response.status_code, 200)
        self.assertEqual(open_response.headers["content-type"], "image/png")

        delete_response = self.client.post(
            "/projects/rendered-assets/delete",
            json={
                "test_root": str(self.test_root),
                "relative_path": relative_path,
            },
        )
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(delete_response.json()["assets_count"], 0)


if __name__ == "__main__":
    unittest.main()
