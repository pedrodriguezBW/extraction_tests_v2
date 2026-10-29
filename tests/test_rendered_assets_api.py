"""Service and endpoint tests for the generic rendered assets API."""

import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from project_fixtures import write_image

from backend.app.main import app
from backend.app.services.rendered_assets import (
    RenderedAssetServiceError,
    delete_project_rendered_asset,
    list_project_rendered_assets,
    resolve_project_rendered_asset,
)

ASSETS = "04_Report/_RenderedAssets"


def rel(name: str) -> str:
    return f"{ASSETS}/{name}"


def write_jpeg(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (10, 4), "white").save(path, format="JPEG")
    return path


class RenderedAssetServiceTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.test_root = Path(self.temporary_directory.name) / "TEST - 001"
        (self.test_root / "04_Report").mkdir(parents=True)
        self.assets = self.test_root / ASSETS

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_missing_folder_is_an_empty_successful_listing(self):
        response = list_project_rendered_assets(self.test_root)

        self.assertTrue(response.success)
        self.assertFalse(response.directory_found)
        self.assertEqual(response.assets_count, 0)
        self.assertEqual(response.assets, [])
        self.assertEqual(response.warnings, [])

    def test_listing_mixes_sources_and_reports_warnings(self):
        write_image(self.assets / "chart03_simpati_acquisition_01.png")
        (self.assets / "chart03_simpati_acquisition_01.json").write_text(
            json.dumps({"source": "simpati"}), encoding="utf-8"
        )
        write_image(self.assets / "graphtec_chart_01.png")
        (self.assets / "graphtec_chart_01.json").write_text(
            json.dumps({"source": "graphtec"}), encoding="utf-8"
        )
        write_jpeg(self.assets / "manual.JPG")
        (self.assets / "data.csv").write_text("1", encoding="utf-8")
        (self.assets / "broken.png").write_bytes(b"x")

        response = list_project_rendered_assets(self.test_root)

        self.assertTrue(response.success)
        self.assertTrue(response.directory_found)
        self.assertEqual(response.assets_count, 3)
        self.assertEqual(
            [(a.name, a.relative_path, a.extension, a.source) for a in response.assets],
            [
                (
                    "chart03_simpati_acquisition_01.png",
                    rel("chart03_simpati_acquisition_01.png"),
                    ".png",
                    "simpati",
                ),
                ("graphtec_chart_01.png", rel("graphtec_chart_01.png"), ".png", "graphtec"),
                ("manual.JPG", rel("manual.JPG"), ".jpg", "manual"),
            ],
        )
        self.assertEqual(
            sorted((w.name, w.code) for w in response.warnings),
            [("broken.png", "invalid_image"), ("data.csv", "unsupported_file")],
        )

    def test_missing_test_folder_is_a_structured_error(self):
        with self.assertRaises(RenderedAssetServiceError) as context:
            list_project_rendered_assets(self.test_root / "missing")

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.error.code, "rendered_asset_invalid_path")

    def test_resolve_and_delete_are_confined(self):
        image = write_image(self.assets / "chart.png")
        (self.assets / "chart.json").write_text("{}", encoding="utf-8")
        outside = write_image(self.test_root / "04_Report" / "outside.png")

        self.assertEqual(
            resolve_project_rendered_asset(self.test_root, rel("chart.png")),
            image.resolve(),
        )
        for path, status in (
            ("../outside.png", 400),
            (str(image.resolve()), 400),
            ("04_Report/outside.png", 400),
            (rel("missing.png"), 404),
            (rel("chart.json"), 415),
        ):
            with self.assertRaises(RenderedAssetServiceError, msg=path) as context:
                resolve_project_rendered_asset(self.test_root, path)
            self.assertEqual(context.exception.status_code, status, path)
            with self.assertRaises(RenderedAssetServiceError, msg=path):
                delete_project_rendered_asset(self.test_root, path)

        response = delete_project_rendered_asset(self.test_root, rel("chart.png"))

        self.assertTrue(response.success)
        self.assertEqual(response.deleted_relative_path, rel("chart.png"))
        self.assertEqual(response.assets_count, 0)
        self.assertFalse(image.exists())
        self.assertFalse((self.assets / "chart.json").exists())
        self.assertTrue(outside.exists())


class RenderedAssetEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.test_root = Path(self.temporary_directory.name) / "TEST - 001"
        (self.test_root / "04_Report").mkdir(parents=True)
        self.assets = self.test_root / ASSETS

    def tearDown(self):
        self.temporary_directory.cleanup()

    def list_assets(self):
        return self.client.post(
            "/projects/rendered-assets", json={"test_root": str(self.test_root)}
        )

    def test_listing_endpoint(self):
        write_image(self.assets / "chart03_simpati_acquisition_01.png")
        write_jpeg(self.assets / "photo.jpeg")
        (self.assets / "notes.txt").write_text("x", encoding="utf-8")

        response = self.list_assets()

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["assets_count"], 2)
        self.assertEqual(
            [a["relative_path"] for a in body["assets"]],
            [rel("chart03_simpati_acquisition_01.png"), rel("photo.jpeg")],
        )
        self.assertEqual([a["source"] for a in body["assets"]], ["manual", "manual"])
        self.assertEqual(body["warnings"][0]["name"], "notes.txt")

    def test_listing_without_folder(self):
        response = self.list_assets()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["assets_count"], 0)
        self.assertFalse(response.json()["directory_found"])

    def test_open_endpoint_serves_png_and_jpeg(self):
        write_image(self.assets / "chart.png")
        write_jpeg(self.assets / "photo.jpg")

        png = self.client.get(
            "/projects/rendered-asset",
            params={"test_root": str(self.test_root), "relative_path": rel("chart.png")},
        )
        jpg = self.client.get(
            "/projects/rendered-asset",
            params={"test_root": str(self.test_root), "relative_path": rel("photo.jpg")},
        )

        self.assertEqual(png.status_code, 200)
        self.assertEqual(png.headers["content-type"], "image/png")
        self.assertEqual(jpg.status_code, 200)
        self.assertEqual(jpg.headers["content-type"], "image/jpeg")

    def test_open_endpoint_rejects_unsafe_paths(self):
        write_image(self.assets / "chart.png")
        write_image(self.test_root / "04_Report" / "outside.png")
        (self.assets / "data.csv").write_text("1", encoding="utf-8")
        cases = [
            ("../outside.png", 400),
            ("04_Report/_RenderedAssets/../outside.png", 400),
            (str((self.assets / "chart.png").resolve()), 400),
            ("04_Report/outside.png", 400),
            (rel("missing.png"), 404),
            (rel("data.csv"), 415),
        ]

        for path, status in cases:
            response = self.client.get(
                "/projects/rendered-asset",
                params={"test_root": str(self.test_root), "relative_path": path},
            )
            self.assertEqual(response.status_code, status, path)
            self.assertFalse(response.json()["success"])

    def test_delete_endpoint(self):
        write_image(self.assets / "chart.png")
        (self.assets / "chart.json").write_text("{}", encoding="utf-8")
        write_image(self.assets / "other.png")

        response = self.client.post(
            "/projects/rendered-assets/delete",
            json={"test_root": str(self.test_root), "relative_path": rel("chart.png")},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["deleted_relative_path"], rel("chart.png"))
        self.assertEqual([a["name"] for a in body["assets"]], ["other.png"])
        self.assertFalse((self.assets / "chart.png").exists())
        self.assertFalse((self.assets / "chart.json").exists())

        again = self.client.post(
            "/projects/rendered-assets/delete",
            json={"test_root": str(self.test_root), "relative_path": rel("chart.png")},
        )
        self.assertEqual(again.status_code, 404)

        outside = self.client.post(
            "/projects/rendered-assets/delete",
            json={"test_root": str(self.test_root), "relative_path": "../x.png"},
        )
        self.assertEqual(outside.status_code, 400)


if __name__ == "__main__":
    unittest.main()
