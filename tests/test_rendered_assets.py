"""Tests for the generic inventory of ``04_Report/_RenderedAssets``.

The inventory lists every compatible image whatever its origin, confines
every client path to the folder and feeds the PowerPoint with exactly the
selected images, in the selected order.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from project_fixtures import build_test_folder, write_image

from src.report_generator.generator import (
    generate_climatic_report,
    resolve_result_images,
)
from src.report_generator.rendered_assets import (
    RenderedAssetNotFoundError,
    RenderedAssetPathError,
    RenderedAssetUnsupportedError,
    delete_rendered_asset,
    list_rendered_assets,
    relative_asset_path,
    resolve_rendered_asset,
    select_rendered_assets,
)

ASSETS = "04_Report/_RenderedAssets"


def rel(name: str) -> str:
    return f"{ASSETS}/{name}"


def write_jpeg(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (10, 4), "white").save(path, format="JPEG")
    return path


def write_gif(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("P", (4, 4)).save(path, format="GIF")
    return path


class RenderedAssetInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.test_root = Path(self.temporary_directory.name)
        (self.test_root / "04_Report").mkdir()
        self.assets = self.test_root / ASSETS

    def tearDown(self):
        self.temporary_directory.cleanup()

    def names(self):
        return [a.name for a in list_rendered_assets(self.test_root).assets]

    def test_missing_rendered_assets_folder(self):
        inventory = list_rendered_assets(self.test_root)

        self.assertFalse(inventory.exists)
        self.assertEqual(inventory.assets, [])
        self.assertEqual(inventory.warnings, [])

    def test_empty_rendered_assets_folder(self):
        self.assets.mkdir()

        inventory = list_rendered_assets(self.test_root)

        self.assertTrue(inventory.exists)
        self.assertEqual(inventory.assets, [])
        self.assertEqual(inventory.warnings, [])

    def test_png_jpg_and_jpeg_are_detected(self):
        write_image(self.assets / "a.png")
        write_jpeg(self.assets / "b.jpg")
        write_jpeg(self.assets / "c.jpeg")

        assets = list_rendered_assets(self.test_root).assets

        self.assertEqual([a.name for a in assets], ["a.png", "b.jpg", "c.jpeg"])
        self.assertEqual([a.extension for a in assets], [".png", ".jpg", ".jpeg"])
        self.assertTrue(all(a.size > 0 for a in assets))

    def test_upper_case_extensions_are_accepted(self):
        write_image(self.assets / "UPPER.PNG")
        write_jpeg(self.assets / "Photo.JPG")
        write_jpeg(self.assets / "Mixed.Jpeg")

        assets = list_rendered_assets(self.test_root).assets

        self.assertEqual([a.name for a in assets], ["Mixed.Jpeg", "Photo.JPG", "UPPER.PNG"])
        self.assertEqual([a.extension for a in assets], [".jpeg", ".jpg", ".png"])

    def test_subdirectories_are_excluded(self):
        write_image(self.assets / "nested" / "inner.png")
        write_image(self.assets / "top.png")

        inventory = list_rendered_assets(self.test_root)

        self.assertEqual([a.name for a in inventory.assets], ["top.png"])
        self.assertEqual(inventory.warnings, [])

    def test_data_files_are_ignored_with_a_warning(self):
        self.assets.mkdir()
        write_image(self.assets / "chart.png")
        (self.assets / "data.csv").write_text("a,b\n", encoding="utf-8")
        (self.assets / "notes.txt").write_text("x", encoding="utf-8")
        (self.assets / "vector.svg").write_text("<svg/>", encoding="utf-8")
        (self.assets / "doc.pdf").write_bytes(b"%PDF-1.4")
        (self.assets / "chart.json").write_text("{}", encoding="utf-8")
        (self.assets / "orphan.json").write_text("{}", encoding="utf-8")
        write_gif(self.assets / "anim.gif")
        (self.assets / "~$lock.png").write_bytes(b"x")
        (self.assets / ".hidden.png").write_bytes(b"x")

        inventory = list_rendered_assets(self.test_root)

        self.assertEqual([a.name for a in inventory.assets], ["chart.png"])
        self.assertEqual(
            sorted(w.name for w in inventory.warnings),
            ["anim.gif", "data.csv", "doc.pdf", "notes.txt", "vector.svg"],
        )
        self.assertTrue(all(w.code == "unsupported_file" for w in inventory.warnings))

    def test_image_extension_with_invalid_content_is_a_warning(self):
        self.assets.mkdir()
        write_image(self.assets / "good.png")
        (self.assets / "fake.png").write_bytes(b"not an image")
        (self.assets / "empty.jpg").write_bytes(b"")
        # A GIF renamed as PNG is not accepted either.
        write_gif(self.assets / "renamed.png")

        inventory = list_rendered_assets(self.test_root)

        self.assertEqual([a.name for a in inventory.assets], ["good.png"])
        self.assertEqual(
            sorted((w.name, w.code) for w in inventory.warnings),
            [
                ("empty.jpg", "invalid_image"),
                ("fake.png", "invalid_image"),
                ("renamed.png", "invalid_image"),
            ],
        )

    def test_order_is_natural_and_deterministic(self):
        for name in ("img_10.png", "img_2.png", "b.jpg", "A.png", "img_1.png"):
            write_image(self.assets / name)

        first = self.names()
        second = self.names()

        self.assertEqual(first, ["A.png", "b.jpg", "img_1.png", "img_2.png", "img_10.png"])
        self.assertEqual(first, second)

    def test_relative_paths_use_the_test_root_and_slashes(self):
        write_image(self.assets / "chart.png")

        asset = list_rendered_assets(self.test_root).assets[0]

        self.assertEqual(asset.relative_path, "04_Report/_RenderedAssets/chart.png")
        self.assertEqual(asset.path, (self.assets / "chart.png").resolve())

    def test_simpati_source_comes_from_metadata(self):
        write_image(self.assets / "chart03_simpati_acquisition_01.png")
        (self.assets / "chart03_simpati_acquisition_01.json").write_text(
            json.dumps({"source": "simpati"}), encoding="utf-8"
        )

        asset = list_rendered_assets(self.test_root).assets[0]

        self.assertEqual(asset.source, "simpati")
        self.assertEqual(asset.metadata_name, "chart03_simpati_acquisition_01.json")

    def test_graphtec_source_comes_from_metadata(self):
        write_image(self.assets / "graphtec_chart_01.png")
        (self.assets / "graphtec_chart_01.json").write_text(
            json.dumps({"source": "graphtec", "test_type": "IR"}), encoding="utf-8"
        )

        asset = list_rendered_assets(self.test_root).assets[0]

        self.assertEqual(asset.source, "graphtec")

    def test_manual_image_without_metadata(self):
        write_jpeg(self.assets / "photo from camera.jpg")
        # A name that looks like a chart is still "manual" without metadata:
        # the origin is never deduced from the name.
        write_image(self.assets / "graphtec_chart_99.png")
        write_image(self.assets / "nameless.png")
        (self.assets / "nameless.json").write_text(json.dumps({"x": 1}), encoding="utf-8")

        assets = {a.name: a for a in list_rendered_assets(self.test_root).assets}

        self.assertEqual(assets["photo from camera.jpg"].source, "manual")
        self.assertIsNone(assets["photo from camera.jpg"].metadata_name)
        self.assertEqual(assets["graphtec_chart_99.png"].source, "manual")
        self.assertEqual(assets["nameless.png"].source, "unknown")

    def test_mixed_origins_are_listed_together(self):
        write_image(self.assets / "chart03_simpati_acquisition_01.png")
        (self.assets / "chart03_simpati_acquisition_01.json").write_text(
            json.dumps({"source": "simpati"}), encoding="utf-8"
        )
        write_image(self.assets / "graphtec_chart_01.png")
        (self.assets / "graphtec_chart_01.json").write_text(
            json.dumps({"source": "graphtec"}), encoding="utf-8"
        )
        write_jpeg(self.assets / "manual.jpg")

        assets = list_rendered_assets(self.test_root).assets

        self.assertEqual(
            [(a.name, a.source) for a in assets],
            [
                ("chart03_simpati_acquisition_01.png", "simpati"),
                ("graphtec_chart_01.png", "graphtec"),
                ("manual.jpg", "manual"),
            ],
        )


class RenderedAssetResolutionTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.test_root = Path(self.temporary_directory.name) / "TEST - 001"
        self.assets = self.test_root / ASSETS
        write_image(self.assets / "chart.png")
        write_jpeg(self.assets / "photo.jpg")
        # Files that must never be reachable.
        write_image(self.test_root / "04_Report" / "outside_assets.png")
        write_image(self.test_root / "02_Evidences" / "01" / "evidence.png")
        write_image(self.assets / "nested" / "deep.png")
        self.external = write_image(Path(self.temporary_directory.name) / "external.png")

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_safe_open_returns_the_confined_path(self):
        resolved = resolve_rendered_asset(self.test_root, rel("chart.png"))

        self.assertEqual(resolved, (self.assets / "chart.png").resolve())
        # Backslashes from a Windows client are accepted.
        self.assertEqual(
            resolve_rendered_asset(self.test_root, r"04_Report\_RenderedAssets\photo.jpg"),
            (self.assets / "photo.jpg").resolve(),
        )

    def test_safe_delete_removes_image_and_metadata(self):
        (self.assets / "chart.json").write_text("{}", encoding="utf-8")

        deleted = delete_rendered_asset(self.test_root, rel("chart.png"))

        self.assertEqual(deleted, (self.assets / "chart.png").resolve())
        self.assertFalse((self.assets / "chart.png").exists())
        self.assertFalse((self.assets / "chart.json").exists())
        self.assertTrue((self.assets / "photo.jpg").exists())

    def test_absolute_paths_are_rejected(self):
        for path in (
            str((self.assets / "chart.png").resolve()),
            r"C:\Tests\TEST - 001\04_Report\_RenderedAssets\chart.png",
            "/04_Report/_RenderedAssets/chart.png",
            r"\04_Report\_RenderedAssets\chart.png",
        ):
            with self.assertRaises(RenderedAssetPathError, msg=path):
                resolve_rendered_asset(self.test_root, path)

    def test_parent_components_are_rejected(self):
        for path in (
            "../external.png",
            "04_Report/_RenderedAssets/../outside_assets.png",
            "04_Report/_RenderedAssets/nested/../chart.png",
            "./04_Report/_RenderedAssets/chart.png",
        ):
            with self.assertRaises(RenderedAssetPathError, msg=path):
                resolve_rendered_asset(self.test_root, path)
        self.assertTrue(self.external.exists())

    def test_external_files_are_rejected(self):
        link = self.assets / "link.png"
        try:
            os.symlink(self.external, link)
        except (OSError, NotImplementedError):
            self.skipTest("Symbolic links are not available.")

        with self.assertRaises(RenderedAssetPathError):
            resolve_rendered_asset(self.test_root, rel("link.png"))
        self.assertNotIn("link.png", [a.name for a in list_rendered_assets(self.test_root).assets])

    def test_files_outside_rendered_assets_are_rejected(self):
        for path in (
            "04_Report/outside_assets.png",
            "02_Evidences/01/evidence.png",
            "04_Report/_RenderedAssets/nested/deep.png",
            "chart.png",
            "04_Report/test_metadata.json",
        ):
            with self.assertRaises(RenderedAssetPathError, msg=path):
                resolve_rendered_asset(self.test_root, path)
            with self.assertRaises(RenderedAssetPathError, msg=path):
                delete_rendered_asset(self.test_root, path)
        self.assertTrue((self.test_root / "04_Report" / "outside_assets.png").exists())

    def test_missing_and_unsupported_assets(self):
        (self.assets / "data.csv").write_text("1", encoding="utf-8")
        (self.assets / "fake.png").write_bytes(b"nope")
        (self.assets / "chart.json").write_text("{}", encoding="utf-8")

        with self.assertRaises(RenderedAssetNotFoundError):
            resolve_rendered_asset(self.test_root, rel("missing.png"))
        with self.assertRaises(RenderedAssetUnsupportedError):
            resolve_rendered_asset(self.test_root, rel("data.csv"))
        with self.assertRaises(RenderedAssetUnsupportedError):
            resolve_rendered_asset(self.test_root, rel("fake.png"))
        with self.assertRaises(RenderedAssetUnsupportedError):
            delete_rendered_asset(self.test_root, rel("chart.json"))
        self.assertTrue((self.assets / "chart.json").exists())
        with self.assertRaises(RenderedAssetPathError):
            resolve_rendered_asset(self.test_root, "")
        with self.assertRaises(RenderedAssetPathError):
            resolve_rendered_asset(self.test_root / "missing", rel("chart.png"))

    def test_missing_rendered_assets_folder_is_not_found(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "04_Report").mkdir()
            with self.assertRaises(RenderedAssetNotFoundError):
                resolve_rendered_asset(root, rel("chart.png"))

    def test_selection_keeps_order_and_rejects_duplicates(self):
        selected = select_rendered_assets(
            self.test_root, [rel("photo.jpg"), rel("chart.png")]
        )
        self.assertEqual(
            selected,
            [(self.assets / "photo.jpg").resolve(), (self.assets / "chart.png").resolve()],
        )
        self.assertEqual(select_rendered_assets(self.test_root, []), [])

        with self.assertRaises(RenderedAssetPathError):
            select_rendered_assets(self.test_root, [rel("chart.png"), rel("chart.png")])
        with self.assertRaises(RenderedAssetPathError):
            select_rendered_assets(
                self.test_root,
                [rel("chart.png"), r"04_Report\_RenderedAssets\CHART.PNG"],
            )
        with self.assertRaises(RenderedAssetPathError):
            select_rendered_assets(self.test_root, rel("chart.png"))
        with self.assertRaises(RenderedAssetNotFoundError):
            select_rendered_assets(self.test_root, [rel("chart.png"), rel("gone.png")])


class ResultImageResolutionTests(unittest.TestCase):
    """``None`` means no selection (all valid images); a list is explicit."""

    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.test_root = Path(self.temporary_directory.name)
        self.assets = self.test_root / ASSETS
        self.simpati = write_image(self.assets / "chart03_simpati_acquisition_01.png")
        self.graphtec = write_image(self.assets / "graphtec_chart_01.png")
        self.manual = write_jpeg(self.assets / "manual.jpeg")
        (self.assets / "ignored.txt").write_text("x", encoding="utf-8")

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_omitted_selection_uses_the_whole_inventory(self):
        self.assertEqual(
            resolve_result_images(self.test_root, None),
            [p.resolve() for p in (self.simpati, self.graphtec, self.manual)],
        )

    def test_empty_selection_means_no_images(self):
        self.assertEqual(resolve_result_images(self.test_root, []), [])

    def test_explicit_selection_is_used_as_is(self):
        self.assertEqual(
            resolve_result_images(
                self.test_root,
                [rel("manual.jpeg"), rel("chart03_simpati_acquisition_01.png")],
            ),
            [self.manual.resolve(), self.simpati.resolve()],
        )


class ReportGenerationSelectionTests(unittest.TestCase):
    """End-to-end: the PowerPoint contains exactly the selected images.

    The real ``populate_test_results`` runs against a minimal template with
    the ``TEST A`` section; the other sections are patched because they
    need the corporate template.
    """

    OTHER_SECTIONS = (
        "prune_climatic_report_slides",
        "populate_test_description",
        "populate_tested_parts",
        "populate_test_assembly_images",
        "populate_test_inputs",
    )

    @classmethod
    def setUpClass(cls):
        cls.temporary_directory = tempfile.TemporaryDirectory()
        base = Path(cls.temporary_directory.name)
        cls.template_path = base / "template.pptx"
        _build_template(cls.template_path)

    @classmethod
    def tearDownClass(cls):
        cls.temporary_directory.cleanup()

    def setUp(self):
        for name in self.OTHER_SECTIONS:
            patcher = patch(f"src.report_generator.generator.{name}")
            patcher.start()
            self.addCleanup(patcher.stop)
        self.case_directory = tempfile.TemporaryDirectory()
        self.test_root = Path(self.case_directory.name) / "TEST - 001"
        build_test_folder(self.test_root)
        self.assets = self.test_root / ASSETS
        self.simpati = write_image(self.assets / "chart03_simpati_acquisition_01.png")
        (self.assets / "chart03_simpati_acquisition_01.json").write_text(
            json.dumps({"source": "simpati"}), encoding="utf-8"
        )
        self.graphtec = write_image(self.assets / "graphtec_chart_01.png")
        (self.assets / "graphtec_chart_01.json").write_text(
            json.dumps({"source": "graphtec"}), encoding="utf-8"
        )
        self.jpg = write_jpeg(self.assets / "manual_photo.jpg")
        self.jpeg = write_jpeg(self.assets / "manual_photo.jpeg")
        self.wide = self.assets / "wide.png"
        Image.new("RGB", (400, 100), "white").save(self.wide)
        self.tall = self.assets / "tall.png"
        Image.new("RGB", (100, 400), "white").save(self.tall)

    def tearDown(self):
        self.case_directory.cleanup()

    def generate(self, selection):
        output = generate_climatic_report(
            test_root=self.test_root,
            template_path=self.template_path,
            selected_rendered_assets=selection,
        )
        return Path(output)

    def result_pictures(self, output):
        """Pictures of the Test Results slides, in slide and insertion order."""
        from pptx import Presentation
        from pptx.enum.shapes import MSO_SHAPE_TYPE

        pictures = []
        for slide in Presentation(output).slides:
            title = _slide_title(slide)
            if not title.startswith("4. Test Results"):
                continue
            for shape in slide.shapes:
                if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                    pictures.append((title, shape))
        return pictures

    def test_single_image(self):
        output = self.generate([rel("graphtec_chart_01.png")])

        pictures = self.result_pictures(output)
        self.assertEqual(len(pictures), 1)
        self.assertEqual(pictures[0][0], "4. Test Results")
        self.assertEqual(pictures[0][1].image.sha1, _sha1(self.graphtec))

    def test_mixed_sources_and_formats_keep_selection_order(self):
        selection = [
            rel("manual_photo.jpg"),
            rel("graphtec_chart_01.png"),
            rel("manual_photo.jpeg"),
            rel("chart03_simpati_acquisition_01.png"),
        ]

        output = self.generate(selection)

        pictures = self.result_pictures(output)

        self.assertEqual(len(pictures), 4)

        self.assertEqual(
            [picture[1].image.sha1 for picture in pictures],
            [
                _sha1(self.jpg),
                _sha1(self.graphtec),
                _sha1(self.jpeg),
                _sha1(self.simpati),
            ],
        )

        self.assertEqual(
            [picture[0] for picture in pictures],
            [
                "4. Test Results",
                "4. Test Results",
                "4. Test Results (cont.)",
                "4. Test Results (cont.)",
            ],
        )

    def test_only_selected_images_are_inserted(self):
        """Unselected images on disk (any prefix or origin) never appear."""
        output = self.generate([rel("manual_photo.jpg")])

        hashes = [p[1].image.sha1 for p in self.result_pictures(output)]
        self.assertEqual(hashes, [_sha1(self.jpg)])
        self.assertNotIn(_sha1(self.simpati), hashes)
        self.assertNotIn(_sha1(self.graphtec), hashes)

    def test_empty_selection_generates_the_report_without_images(self):
        output = self.generate([])

        self.assertTrue(output.is_file())
        self.assertEqual(self.result_pictures(output), [])
        titles = [_slide_title(s) for s in _slides(output)]
        self.assertIn("4. Test Results", titles)
        self.assertIn("Conclusions", titles)

    def test_continuations_are_created_for_more_than_two_images(self):
        selection = [
            rel("manual_photo.jpg"),
            rel("graphtec_chart_01.png"),
            rel("manual_photo.jpeg"),
            rel("chart03_simpati_acquisition_01.png"),
            rel("wide.png"),
            rel("tall.png"),
        ]

        output = self.generate(selection)

        pictures = self.result_pictures(output)

        self.assertEqual(len(pictures), 6)

        self.assertEqual(
            [picture[0] for picture in pictures],
            [
                "4. Test Results",
                "4. Test Results",
                "4. Test Results (cont.)",
                "4. Test Results (cont.)",
                "4. Test Results (cont.)",
                "4. Test Results (cont.)",
            ],
        )

        self.assertEqual(
            [picture[1].image.sha1 for picture in pictures],
            [
                _sha1(self.jpg),
                _sha1(self.graphtec),
                _sha1(self.jpeg),
                _sha1(self.simpati),
                _sha1(self.wide),
                _sha1(self.tall),
            ],
        )

    def test_aspect_ratio_is_preserved(self):
        output = self.generate([rel("wide.png"), rel("tall.png")])

        for _title, shape in self.result_pictures(output):
            with Image.open(self.wide if shape.image.sha1 == _sha1(self.wide) else self.tall) as image:
                expected = image.width / image.height
            self.assertAlmostEqual(shape.width / shape.height, expected, places=2)

    def test_invalid_selection_is_rejected_before_writing(self):
        for selection, error in (
            ([rel("chart03_simpati_acquisition_01.png")] * 2, RenderedAssetPathError),
            (["../outside.png"], RenderedAssetPathError),
            ([str(self.graphtec.resolve())], RenderedAssetPathError),
            (["04_Report/test_metadata.json"], RenderedAssetPathError),
            ([rel("gone.png")], RenderedAssetNotFoundError),
        ):
            with self.assertRaises(error, msg=selection):
                self.generate(selection)
        self.assertEqual(list((self.test_root / "04_Report").glob("*.pptx")), [])

    def test_omitted_selection_keeps_console_script_behaviour(self):
        output = generate_climatic_report(
            test_root=self.test_root,
            template_path=self.template_path,
        )

        hashes = [p[1].image.sha1 for p in self.result_pictures(output)]
        self.assertEqual(
            hashes,
            [_sha1(p) for p in (self.simpati, self.graphtec, self.jpeg, self.jpg, self.tall, self.wide)],
        )


def _sha1(path: Path) -> str:
    import hashlib

    return hashlib.sha1(path.read_bytes()).hexdigest()


def _slides(output: Path):
    from pptx import Presentation

    return list(Presentation(output).slides)


def _slide_title(slide) -> str:
    texts = []
    for shape in slide.shapes:
        if shape.has_text_frame and shape.text_frame.text.strip():
            texts.append(shape.text_frame.text.strip())
    return texts[0] if texts else ""


def _build_template(template_path: Path) -> None:
    """Build a minimal template: cover, TEST A, 4. Test Results, Conclusions."""
    from pptx import Presentation

    presentation = Presentation()
    layout = presentation.slide_layouts[5]  # Title Only
    for title in ("Cover", "TEST A", "4. Test Results", "Conclusions"):
        slide = presentation.slides.add_slide(layout)
        slide.shapes.title.text = title
    presentation.save(template_path)


if __name__ == "__main__":
    unittest.main()
