import base64
import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from backend.app.main import app
from backend.app.services.simpati_inspection import (
    SimpatiChartSaveError,
    SimpatiInspectionError,
    clear_analysis_cache,
    inspect_project_simpati,
    save_project_simpati_chart,
)
from simpati_fixtures import (
    X01_FIXTURE,
    X04_FIXTURE,
    copy_fixture,
    write_incompatible,
    write_without_thermal,
    write_x03,
)
from src.report_generator.assets.simpati_extractor import (
    find_simpati_files,
    prepare_rendered_assets_directory,
)
from src.report_generator.rendered_assets import list_rendered_assets

SIMPATI = "03_Data/01_SIMPATI"
ASSETS = "04_Report/_RenderedAssets"


def build_png_data_url() -> str:
    image_buffer = BytesIO()
    Image.new("RGB", (8, 6), "white").save(image_buffer, format="PNG")
    encoded_image = base64.b64encode(image_buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded_image}"


class SimpatiTestFolder(unittest.TestCase):
    def setUp(self):
        clear_analysis_cache()
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.test_root = Path(self.temporary_directory.name)
        (self.test_root / "04_Report").mkdir()
        self.folder = self.test_root / "03_Data" / "01_SIMPATI"
        self.folder.mkdir(parents=True)

    def tearDown(self):
        self.temporary_directory.cleanup()
        clear_analysis_cache()


class SimpatiInspectionServiceTests(SimpatiTestFolder):
    def setUp(self):
        super().setUp()
        copy_fixture(X01_FIXTURE, self.folder, "ensayo.x01")
        write_x03(self.folder / "ensayo.x03")
        copy_fixture(X04_FIXTURE, self.folder, "ensayo.x04")

    def test_every_acquisition_is_listed_in_numeric_order(self):
        result = inspect_project_simpati(self.test_root)

        self.assertTrue(result.success)
        self.assertTrue(result.available)
        self.assertEqual(
            [(item.label, item.file_name, item.status) for item in result.acquisitions],
            [
                ("x01", "ensayo.x01", "ready"),
                ("x03", "ensayo.x03", "ready"),
                ("x04", "ensayo.x04", "ready"),
            ],
        )
        self.assertEqual(result.found_count, 3)
        self.assertEqual(result.processed_count, 3)
        self.assertEqual(result.ready_count, 3)
        self.assertEqual(result.incompatible_count, 0)
        x01 = result.acquisitions[0]
        self.assertEqual(x01.relative_path, f"{SIMPATI}/ensayo.x01")
        self.assertEqual(x01.encoding, "cp1252")
        self.assertEqual(x01.records_count, 9593)
        self.assertEqual(x01.acquisition_start, "2024-02-22T14:54:19")
        self.assertEqual(x01.acquisition_end, "2024-02-29T06:53:42")
        self.assertEqual(x01.device, "Weiss 748")
        self.assertEqual(x01.channels_count, 59)
        self.assertEqual(
            x01.thermal_channels,
            [
                "Chamber temperature",
                "Chamber setpoint",
                "Supply air temperature",
                "Return air temperature",
            ],
        )
        self.assertIsNone(x01.error)

    def test_first_ready_acquisition_is_previewed_by_default(self):
        result = inspect_project_simpati(self.test_root)

        self.assertEqual(result.selected_relative_path, f"{SIMPATI}/ensayo.x01")
        self.assertEqual(result.selected_index, 1)
        self.assertEqual(result.file_name, "ensayo.x01")
        self.assertEqual(result.records_count, 9593)
        self.assertEqual(len(result.preview_timestamps), 1200)
        self.assertTrue(all(len(c.values) == 1200 for c in result.thermal_channels))

    def test_selected_acquisition_is_previewed(self):
        result = inspect_project_simpati(self.test_root, f"{SIMPATI}/ensayo.x04")

        self.assertEqual(result.selected_index, 4)
        self.assertEqual(result.selected_status, "ready")
        self.assertEqual(result.file_name, "ensayo.x04")
        self.assertEqual(
            result.file_path,
            str((self.folder / "ensayo.x04").resolve()),
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
                "Specimen temperature",
            ],
        )
        self.assertEqual(result.thermal_channels[0].source_column, "A:Temp. Basket [°C]")
        self.assertEqual(result.thermal_channels[0].role, "basket_temperature")
        advanced = [channel.source_column for channel in result.advanced_channels]
        self.assertIn("A:Cycles", advanced)
        self.assertNotIn("A:Temp. Basket [°C]", advanced)
        self.assertEqual(len(result.channels), 86)

    def test_x03_preview_keeps_the_historical_channels(self):
        result = inspect_project_simpati(self.test_root, f"{SIMPATI}/ensayo.x03")

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
        basket = result.thermal_channels[0]
        self.assertEqual(basket.source_column, "A:Temp canast [°C]")
        self.assertEqual(basket.values, [21.5, 40.5])
        self.assertEqual(result.preview_timestamps, ["2024-08-27T15:06:03", "2024-08-27T15:07:03"])
        self.assertIn("A:Pos canasta [Pos]", [c.label for c in result.advanced_channels])

    def test_incompatible_acquisition_is_isolated(self):
        write_incompatible(self.folder / "ensayo.x07")
        write_without_thermal(self.folder / "ensayo.x09")

        result = inspect_project_simpati(self.test_root)

        self.assertEqual(
            [(item.label, item.status) for item in result.acquisitions],
            [
                ("x01", "ready"),
                ("x03", "ready"),
                ("x04", "ready"),
                ("x07", "incompatible"),
                ("x09", "no_thermal_channels"),
            ],
        )
        incompatible = result.acquisitions[3]
        self.assertEqual(incompatible.error.code, "simpati_acquisition_incompatible")
        self.assertIn("ensayo.x07", incompatible.error.message)
        self.assertEqual(incompatible.records_count, 0)
        self.assertEqual(result.found_count, 5)
        self.assertEqual(result.processed_count, 4)
        self.assertEqual(result.without_thermal_count, 1)
        self.assertEqual(result.incompatible_count, 1)
        self.assertEqual(result.selected_index, 1)
        self.assertEqual(result.errors, [])

    def test_selecting_an_incompatible_acquisition_reports_its_error(self):
        write_incompatible(self.folder / "ensayo.x07")

        result = inspect_project_simpati(self.test_root, f"{SIMPATI}/ensayo.x07")

        self.assertTrue(result.success)
        self.assertEqual(result.selected_status, "incompatible")
        self.assertEqual(result.thermal_channels, [])
        self.assertEqual(result.preview_timestamps, [])
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0].code, "simpati_acquisition_incompatible")
        self.assertEqual(len(result.acquisitions), 4)

    def test_acquisition_without_thermal_channels_is_previewed(self):
        write_without_thermal(self.folder / "ensayo.x09")

        result = inspect_project_simpati(self.test_root, f"{SIMPATI}/ensayo.x09")

        self.assertEqual(result.selected_status, "no_thermal_channels")
        self.assertEqual(result.thermal_channels, [])
        self.assertEqual(
            [c.source_column for c in result.advanced_channels],
            ["A:Basketpositi", "N:Basketpositi", "Start"],
        )

    def test_invalid_selection_is_structured(self):
        (self.test_root / "03_Data" / "02_Graphtec").mkdir()
        (self.test_root / "03_Data" / "02_Graphtec" / "a.x01").write_text("x")
        (self.folder / "notes.txt").write_text("x")

        for relative_path in (
            "03_Data/02_Graphtec/a.x01",
            f"{SIMPATI}/notes.txt",
            f"{SIMPATI}/../02_Graphtec/a.x01",
        ):
            with self.subTest(relative_path=relative_path):
                with self.assertRaises(SimpatiInspectionError) as context:
                    inspect_project_simpati(self.test_root, relative_path)
                self.assertEqual(context.exception.status_code, 400)
                self.assertEqual(
                    context.exception.error.code,
                    "simpati_inspection_invalid_path",
                )


class SimpatiOptionalTests(SimpatiTestFolder):
    def test_missing_simpati_is_optional(self):
        result = inspect_project_simpati(self.test_root)

        self.assertTrue(result.success)
        self.assertFalse(result.available)
        self.assertEqual(result.acquisitions, [])
        self.assertEqual(result.errors, [])

    def test_missing_folder_is_optional(self):
        self.folder.rmdir()
        result = inspect_project_simpati(self.test_root)
        self.assertFalse(result.available)

    def test_missing_test_folder_is_structured(self):
        with self.assertRaises(SimpatiInspectionError) as context:
            inspect_project_simpati(self.test_root / "missing")
        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.error.code, "simpati_inspection_invalid_file")

    def test_compatibility_helper_lists_every_acquisition(self):
        write_x03(self.folder / "b.x03")
        write_x03(self.folder / "a.x12")
        (self.folder / "readme.txt").write_text("x")
        self.assertEqual(
            [path.name for path in find_simpati_files(self.test_root)],
            ["b.x03", "a.x12"],
        )


class SimpatiChartSaveTests(SimpatiTestFolder):
    def setUp(self):
        super().setUp()
        write_x03(self.folder / "ensayo.x01")
        write_x03(self.folder / "ensayo.x04")

    def save(self, name="ensayo.x04"):
        return save_project_simpati_chart(
            self.test_root,
            f"{SIMPATI}/{name}",
            build_png_data_url(),
        )

    def test_chart_is_saved_with_its_acquisition_index(self):
        result = self.save()

        expected_path = self.test_root / ASSETS / "chart_simpati_x04_01.png"
        self.assertTrue(result.success)
        self.assertEqual(result.chart_name, "chart_simpati_x04_01.png")
        self.assertEqual(result.chart_path, str(expected_path.resolve()))
        self.assertEqual(result.relative_path, f"{ASSETS}/chart_simpati_x04_01.png")
        self.assertEqual(result.source_relative_path, f"{SIMPATI}/ensayo.x04")
        self.assertEqual(result.acquisition_index, 4)
        metadata = json.loads(expected_path.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["source"], "simpati")
        self.assertEqual(metadata["source_file"], "ensayo.x04")
        self.assertEqual(metadata["source_relative_path"], f"{SIMPATI}/ensayo.x04")
        self.assertEqual(metadata["acquisition_index"], 4)
        self.assertEqual(metadata["acquisition_label"], "x04")
        self.assertEqual(
            [(a.name, a.source, a.relative_path) for a in result.assets],
            [("chart_simpati_x04_01.png", "simpati", f"{ASSETS}/chart_simpati_x04_01.png")],
        )

    def test_charts_of_different_acquisitions_never_collide(self):
        names = [
            self.save("ensayo.x04").chart_name,
            self.save("ensayo.x01").chart_name,
            self.save("ensayo.x04").chart_name,
            self.save("ensayo.x01").chart_name,
        ]

        self.assertEqual(
            names,
            [
                "chart_simpati_x04_01.png",
                "chart_simpati_x01_01.png",
                "chart_simpati_x04_02.png",
                "chart_simpati_x01_02.png",
            ],
        )
        self.assertEqual(
            [a.name for a in list_rendered_assets(self.test_root).assets],
            [
                "chart_simpati_x01_01.png",
                "chart_simpati_x01_02.png",
                "chart_simpati_x04_01.png",
                "chart_simpati_x04_02.png",
            ],
        )

    def test_saved_charts_never_overwrite_and_keep_natural_order(self):
        assets_directory = self.test_root / ASSETS
        assets_directory.mkdir()
        for chart_number in (10, 2):
            Image.new("RGB", (8, 6), "white").save(
                assets_directory / f"chart_simpati_x04_{chart_number:02d}.png"
            )
        legacy = assets_directory / "chart03_simpati_acquisition_01.png"
        Image.new("RGB", (8, 6), "white").save(legacy)

        result = self.save()

        self.assertEqual(result.chart_name, "chart_simpati_x04_01.png")
        self.assertEqual(
            [a.name for a in result.assets],
            [
                "chart03_simpati_acquisition_01.png",
                "chart_simpati_x04_01.png",
                "chart_simpati_x04_02.png",
                "chart_simpati_x04_10.png",
            ],
        )

    def test_chart_is_not_saved_without_report_folder(self):
        (self.test_root / "04_Report").rmdir()

        with self.assertRaises(SimpatiChartSaveError) as context:
            self.save()

        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("04_Report", context.exception.error.message)
        self.assertFalse((self.test_root / "04_Report").exists())

    def test_invalid_chart_image_is_structured(self):
        with self.assertRaises(SimpatiChartSaveError) as context:
            save_project_simpati_chart(
                self.test_root,
                f"{SIMPATI}/ensayo.x04",
                base64.b64encode(b"not a png").decode("ascii"),
            )

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.error.code, "simpati_chart_invalid_image")

    def test_invalid_source_acquisition_is_structured(self):
        for relative_path in (f"{SIMPATI}/missing.x02", "03_Data/other.x04", f"{SIMPATI}/a.txt"):
            with self.subTest(relative_path=relative_path):
                with self.assertRaises(SimpatiChartSaveError) as context:
                    save_project_simpati_chart(self.test_root, relative_path, build_png_data_url())
                self.assertEqual(context.exception.status_code, 400)
                self.assertEqual(context.exception.error.code, "simpati_chart_invalid_source")
        self.assertFalse((self.test_root / ASSETS).exists())

    def test_saved_chart_is_deleted_through_the_generic_inventory(self):
        first = self.save()
        second = self.save()

        from backend.app.services.rendered_assets import delete_project_rendered_asset

        result = delete_project_rendered_asset(self.test_root, first.relative_path)

        self.assertFalse(Path(first.chart_path).exists())
        self.assertFalse(Path(first.chart_path).with_suffix(".json").exists())
        self.assertEqual([a.relative_path for a in result.assets], [second.relative_path])

    def test_rendered_assets_folder_is_created_inside_04_report(self):
        assets = prepare_rendered_assets_directory(self.test_root)
        self.assertEqual(assets, (self.test_root / ASSETS).resolve())
        self.assertTrue(assets.is_dir())


class SimpatiEndpointTests(SimpatiTestFolder):
    def setUp(self):
        super().setUp()
        self.client = TestClient(app)
        copy_fixture(X01_FIXTURE, self.folder, "ensayo.x01")
        write_incompatible(self.folder / "ensayo.x02")
        copy_fixture(X04_FIXTURE, self.folder, "ensayo.x04")

    def test_endpoint_lists_every_acquisition(self):
        response = self.client.post(
            "/projects/simpati/inspect",
            json={"test_root": str(self.test_root)},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["available"])
        self.assertEqual(
            [(item["label"], item["status"]) for item in body["acquisitions"]],
            [("x01", "ready"), ("x02", "incompatible"), ("x04", "ready")],
        )
        self.assertEqual(body["acquisitions"][1]["error"]["code"], "simpati_acquisition_incompatible")
        self.assertEqual(body["selected_relative_path"], f"{SIMPATI}/ensayo.x01")
        self.assertEqual(body["file_name"], "ensayo.x01")

    def test_endpoint_previews_the_requested_acquisition(self):
        response = self.client.post(
            "/projects/simpati/inspect",
            json={"test_root": str(self.test_root), "relative_path": f"{SIMPATI}/ensayo.x04"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["selected_index"], 4)
        self.assertEqual(body["thermal_channels"][0]["label"], "Basket temperature")

    def test_endpoint_returns_structured_path_error(self):
        response = self.client.post(
            "/projects/simpati/inspect",
            json={"test_root": str(self.test_root), "relative_path": "../outside.x01"},
        )

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertFalse(body["success"])
        self.assertEqual(body["errors"][0]["code"], "simpati_inspection_invalid_path")

    def test_endpoint_treats_missing_simpati_as_optional(self):
        for path in self.folder.iterdir():
            path.unlink()

        response = self.client.post(
            "/projects/simpati/inspect",
            json={"test_root": str(self.test_root)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["available"])
        self.assertEqual(response.json()["errors"], [])

    def test_save_chart_endpoint_names_the_chart_after_its_acquisition(self):
        response = self.client.post(
            "/projects/simpati/save-chart",
            json={
                "test_root": str(self.test_root),
                "relative_path": f"{SIMPATI}/ensayo.x04",
                "image_base64": build_png_data_url(),
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["chart_name"], "chart_simpati_x04_01.png")
        self.assertEqual(body["acquisition_index"], 4)

    def test_save_chart_endpoint_requires_the_source_acquisition(self):
        response = self.client.post(
            "/projects/simpati/save-chart",
            json={"test_root": str(self.test_root), "image_base64": build_png_data_url()},
        )
        self.assertEqual(response.status_code, 422)

    def test_saved_chart_is_served_by_the_generic_endpoints(self):
        save = self.client.post(
            "/projects/simpati/save-chart",
            json={
                "test_root": str(self.test_root),
                "relative_path": f"{SIMPATI}/ensayo.x01",
                "image_base64": build_png_data_url(),
            },
        ).json()

        list_response = self.client.post(
            "/projects/rendered-assets",
            json={"test_root": str(self.test_root)},
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(
            [asset["relative_path"] for asset in list_response.json()["assets"]],
            [save["relative_path"]],
        )

        open_response = self.client.get(
            "/projects/rendered-asset",
            params={"test_root": str(self.test_root), "relative_path": save["relative_path"]},
        )
        self.assertEqual(open_response.status_code, 200)

        delete_response = self.client.post(
            "/projects/rendered-assets/delete",
            json={"test_root": str(self.test_root), "relative_path": save["relative_path"]},
        )
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(delete_response.json()["assets"], [])


if __name__ == "__main__":
    unittest.main()
