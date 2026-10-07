import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from project_fixtures import (
    add_evidence,
    build_test_folder,
    minimal_metadata,
)

from backend.app.services.project_inspection import (
    inspect_project,
)


class ProjectInspectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary_directory.name)
        self.test_root = build_test_folder(self.workspace / "TEST - 001")

        add_evidence(
            self.test_root,
            "99_Final",
            sequence=6,
            photos=["final.jpg"],
        )
        add_evidence(
            self.test_root,
            "00_Initial",
            sequence=0,
            photos=["initial_01.jpg", "initial_02.jpg"],
        )

        self.simpati_file = (
            self.test_root
            / "03_Data"
            / "01_SIMPATI"
            / "acquisition.x03"
        )
        self.simpati_file.write_text(
            "test acquisition",
            encoding="utf-8",
        )
        (self.test_root / "03_Data" / "02_CSV" / "log.CSV").write_text(
            "a,b\n1,2\n",
            encoding="utf-8",
        )

        self.template_path = self.workspace / "template.pptx"
        self.template_path.write_bytes(b"test template")

        self.template_patch = patch(
            "backend.app.services.project_inspection."
            "POWERPOINT_TEMPLATE_PATH",
            self.template_path,
        )
        self.template_patch.start()

    def tearDown(self):
        self.template_patch.stop()
        self.temporary_directory.cleanup()

    def test_valid_project_is_detected(self):
        result = inspect_project(self.test_root)

        self.assertTrue(result.valid)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])
        self.assertTrue(result.inputs_directory.found)
        self.assertTrue(result.report_directory.found)
        self.assertTrue(result.metadata.found)
        self.assertTrue(result.metadata.valid)
        self.assertEqual(result.metadata.test_name, "K-01")
        self.assertEqual(
            Path(result.metadata.path),
            self.test_root.resolve() / "04_Report" / "test_metadata.json",
        )
        self.assertEqual(result.metadata.climatic_profile_points_count, 2)
        self.assertTrue(result.powerpoint_template.found)

    def test_evidences_are_returned_in_sequence_order(self):
        result = inspect_project(self.test_root)

        evidences = result.evidences
        self.assertTrue(evidences.directory.found)
        self.assertEqual(evidences.evidences_count, 2)
        self.assertEqual(
            [evidence.folder for evidence in evidences.evidences],
            ["00_Initial", "99_Final"],
        )
        self.assertEqual(evidences.photos_count, 3)
        self.assertEqual(evidences.photos_found_count, 3)
        first_photo = evidences.evidences[0].photos[0]
        self.assertEqual(first_photo.saved_name, "initial_01.jpg")
        self.assertTrue(first_photo.found)
        self.assertEqual(
            Path(first_photo.path),
            self.test_root.resolve()
            / "02_Evidences"
            / "00_Initial"
            / "initial_01.jpg",
        )

    def test_data_sources_are_reported(self):
        result = inspect_project(self.test_root)

        self.assertTrue(result.data.directory.found)
        self.assertTrue(result.data.simpati.available)
        self.assertTrue(result.data.simpati_file.found)
        self.assertEqual(result.data.simpati_file.name, "acquisition.x03")
        self.assertTrue(result.data.csv.available)
        self.assertEqual(result.data.csv.files, ["log.CSV"])
        self.assertTrue(result.data.datalogger.found)
        self.assertFalse(result.data.datalogger.available)
        self.assertFalse(result.data.graphtec.available)

    def test_missing_data_sources_are_optional(self):
        for source in ("01_SIMPATI", "02_CSV", "03_Datalogger", "04_Graphtec"):
            folder = self.test_root / "03_Data" / source
            for file_path in folder.iterdir():
                file_path.unlink()
            folder.rmdir()

        result = inspect_project(self.test_root)

        self.assertTrue(result.valid)
        self.assertEqual(result.warnings, [])
        for source in (
            result.data.simpati,
            result.data.csv,
            result.data.datalogger,
            result.data.graphtec,
        ):
            self.assertFalse(source.found)
            self.assertFalse(source.available)
        self.assertFalse(result.data.simpati_file.found)

    def test_empty_simpati_folder_is_only_a_warning(self):
        self.simpati_file.unlink()

        result = inspect_project(self.test_root)

        self.assertTrue(result.valid)
        self.assertFalse(result.data.simpati_file.found)
        self.assertTrue(
            any(
                "No .x03 file was found" in warning
                for warning in result.warnings
            )
        )

    def test_missing_metadata_blocks_generation(self):
        (self.test_root / "04_Report" / "test_metadata.json").unlink()

        result = inspect_project(self.test_root)

        self.assertFalse(result.valid)
        self.assertFalse(result.metadata.found)
        self.assertFalse(result.metadata.valid)
        self.assertIn("test_metadata.json", result.metadata.error)
        self.assertTrue(
            any("test_metadata.json" in error for error in result.errors)
        )

    def test_invalid_metadata_blocks_generation(self):
        (self.test_root / "04_Report" / "test_metadata.json").write_text(
            "[1, 2",
            encoding="utf-8",
        )

        result = inspect_project(self.test_root)

        self.assertFalse(result.valid)
        self.assertTrue(result.metadata.found)
        self.assertFalse(result.metadata.valid)
        self.assertIn("valid JSON", result.metadata.error)

    def test_metadata_with_wrong_structure_blocks_generation(self):
        (self.test_root / "04_Report" / "test_metadata.json").write_text(
            '{"test": {}}',
            encoding="utf-8",
        )

        result = inspect_project(self.test_root)

        self.assertFalse(result.valid)
        self.assertTrue(result.metadata.found)
        self.assertFalse(result.metadata.valid)
        self.assertTrue(result.metadata.errors)

    def test_missing_report_folder_is_an_error(self):
        report = self.test_root / "04_Report"
        (report / "test_metadata.json").unlink()
        report.rmdir()

        result = inspect_project(self.test_root)

        self.assertFalse(result.valid)
        self.assertFalse(result.report_directory.found)
        self.assertTrue(
            any("04_Report folder was not found" in e for e in result.errors)
        )

    def test_missing_photo_and_invalid_descriptor_are_warnings(self):
        add_evidence(
            self.test_root,
            "03_Incident",
            sequence=3,
            photos=["missing.jpg"],
            create_photos=False,
        )
        broken = self.test_root / "02_Evidences" / "04_Broken"
        broken.mkdir()
        (broken / "evidence.json").write_text("{", encoding="utf-8")

        result = inspect_project(self.test_root)

        self.assertTrue(result.valid)
        self.assertEqual(result.evidences.evidences_count, 3)
        self.assertEqual(
            [m.saved_name for m in result.evidences.missing_photos],
            ["missing.jpg"],
        )
        self.assertEqual(
            [i.folder for i in result.evidences.invalid_evidences],
            ["04_Broken"],
        )
        self.assertTrue(
            any("missing.jpg" in warning for warning in result.warnings)
        )
        self.assertTrue(
            any("04_Broken" in warning for warning in result.warnings)
        )

    def test_missing_setup_photos_in_metadata_are_warned(self):
        metadata = minimal_metadata(
            setup={"images": [{"relative_path": "old/photo.jpg"}]}
        )
        (self.test_root / "04_Report" / "test_metadata.json").write_text(
            json.dumps(metadata),
            encoding="utf-8",
        )

        result = inspect_project(self.test_root)

        self.assertTrue(result.valid)
        self.assertEqual(result.metadata.setup_images_count, 1)
        self.assertEqual(result.metadata.setup_images_found_count, 0)
        self.assertTrue(
            any("setup photo" in warning for warning in result.warnings)
        )

    def test_missing_optional_top_level_folders_are_warnings(self):
        (self.test_root / "01_Inputs").rmdir()

        result = inspect_project(self.test_root)

        self.assertTrue(result.valid)
        self.assertFalse(result.inputs_directory.found)
        self.assertTrue(
            any("01_Inputs" in warning for warning in result.warnings)
        )

    def test_missing_template_is_an_error(self):
        self.template_path.unlink()

        result = inspect_project(self.test_root)

        self.assertFalse(result.valid)
        self.assertFalse(result.powerpoint_template.found)

    def test_missing_project_is_invalid(self):
        result = inspect_project(self.workspace / "missing_project")

        self.assertFalse(result.valid)
        self.assertTrue(result.errors)
        self.assertIn(
            "does not exist",
            result.errors[0].lower(),
        )

    def test_inspection_does_not_modify_the_project(self):
        before = sorted(
            path.relative_to(self.test_root).as_posix()
            for path in self.test_root.rglob("*")
        )

        inspect_project(self.test_root)

        after = sorted(
            path.relative_to(self.test_root).as_posix()
            for path in self.test_root.rglob("*")
        )
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
