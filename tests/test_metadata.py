import tempfile
import unittest
from pathlib import Path

from project_fixtures import build_test_folder, minimal_metadata, write_image

from src.report_generator.metadata import (
    MetadataError,
    load_test_metadata,
    resolve_setup_images,
    summarize_metadata,
    validate_metadata,
)


class LoadTestMetadataTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.test_root = Path(self.temporary_directory.name)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_existing_valid_json_is_loaded_from_04_report(self):
        build_test_folder(self.test_root)

        metadata = load_test_metadata(self.test_root)

        self.assertEqual(metadata["test"]["test_name"], "K-01")
        self.assertEqual(
            len(metadata["climatic_inputs"]["profile_points"]),
            2,
        )

    def test_missing_json_raises_file_not_found(self):
        (self.test_root / "04_Report").mkdir()

        with self.assertRaises(FileNotFoundError) as context:
            load_test_metadata(self.test_root)

        self.assertIn("test_metadata.json", str(context.exception))

    def test_malformed_json_is_reported_with_position(self):
        report = self.test_root / "04_Report"
        report.mkdir()
        (report / "test_metadata.json").write_text(
            '{"test": ',
            encoding="utf-8",
        )

        with self.assertRaises(MetadataError) as context:
            load_test_metadata(self.test_root)

        self.assertIn("valid JSON", str(context.exception))
        self.assertIn("line 1", str(context.exception))

    def test_json_without_required_structure_is_rejected(self):
        build_test_folder(
            self.test_root,
            metadata={"test": {"test_name": ""}, "samples": {}},
        )

        with self.assertRaises(MetadataError) as context:
            load_test_metadata(self.test_root)

        messages = context.exception.errors
        self.assertTrue(any("test.test_name" in m for m in messages))
        self.assertTrue(any("'people'" in m for m in messages))
        self.assertTrue(any("'samples'" in m for m in messages))


class ValidateMetadataTests(unittest.TestCase):
    def test_minimal_metadata_is_valid(self):
        self.assertEqual(validate_metadata(minimal_metadata()), [])

    def test_non_object_is_invalid(self):
        self.assertEqual(
            validate_metadata([]),
            ["The metadata file must contain a JSON object."],
        )

    def test_profile_points_must_be_objects(self):
        metadata = minimal_metadata(
            climatic_inputs={"profile_points": [1, 2]},
        )

        errors = validate_metadata(metadata)

        self.assertEqual(len(errors), 1)
        self.assertIn("climatic_inputs.profile_points", errors[0])

    def test_summary_counts_profile_points(self):
        summary = summarize_metadata(minimal_metadata())

        self.assertEqual(summary.test_name, "K-01")
        self.assertEqual(summary.climatic_profile_points_count, 2)
        self.assertEqual(summary.dut_profile_points_count, 1)
        self.assertEqual(summary.samples_count, 1)


class ResolveSetupImagesTests(unittest.TestCase):
    def test_existing_and_missing_references_are_separated(self):
        with tempfile.TemporaryDirectory() as directory:
            test_root = Path(directory)
            write_image(test_root / "02_Evidences" / "00_Initial" / "a.png")
            metadata = minimal_metadata(
                setup={
                    "images": [
                        {"relative_path": "02_Evidences/00_Initial/a.png"},
                        {"relative_path": "missing/b.png"},
                        {"relative_path": "../outside.png"},
                        {"file_name": "no_path.png"},
                    ]
                }
            )

            found, missing = resolve_setup_images(metadata, test_root)

        self.assertEqual(
            [path.name for path in found],
            ["a.png"],
        )
        self.assertEqual(missing, ["missing/b.png", "../outside.png"])


if __name__ == "__main__":
    unittest.main()
