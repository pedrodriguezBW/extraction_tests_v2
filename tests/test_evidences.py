import tempfile
import unittest
from pathlib import Path

from project_fixtures import add_evidence, evidence_descriptor, write_json

from src.report_generator.evidences import discover_evidences


class EvidenceDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.test_root = Path(self.temporary_directory.name)
        (self.test_root / "02_Evidences").mkdir()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_missing_evidences_folder_is_reported_without_error(self):
        (self.test_root / "02_Evidences").rmdir()

        discovery = discover_evidences(self.test_root)

        self.assertFalse(discovery.found)
        self.assertEqual(discovery.evidences, [])

    def test_descriptors_are_discovered_dynamically(self):
        add_evidence(
            self.test_root,
            "Initial state",
            sequence=0,
            photos=["first.jpg", "second.jpg"],
        )

        discovery = discover_evidences(self.test_root)

        self.assertTrue(discovery.found)
        self.assertEqual(len(discovery.evidences), 1)
        evidence = discovery.evidences[0]
        self.assertEqual(evidence.title, "Initial state")
        self.assertEqual(evidence.reference_type, "none")
        self.assertEqual(evidence.schema_version, 1)
        self.assertEqual(discovery.photos_count, 2)
        self.assertEqual(discovery.found_photos_count, 2)
        self.assertEqual(
            evidence.photos[0].path,
            self.test_root / "02_Evidences" / "Initial state" / "first.jpg",
        )
        self.assertEqual(evidence.photos[0].original_name, "ORIGINAL_1.JPG")
        self.assertEqual(discovery.warnings, [])

    def test_evidences_are_ordered_by_sequence_not_folder_name(self):
        add_evidence(self.test_root, "A_final", sequence=6, photos=[])
        add_evidence(self.test_root, "Z_initial", sequence=0, photos=[])
        add_evidence(self.test_root, "M_inspection", sequence=2, photos=[])
        add_evidence(self.test_root, "B_unordered", sequence=None, photos=[])

        discovery = discover_evidences(self.test_root)

        self.assertEqual(
            [evidence.folder_name for evidence in discovery.evidences],
            ["Z_initial", "M_inspection", "A_final", "B_unordered"],
        )
        self.assertTrue(
            any("has no sequence" in w for w in discovery.warnings)
        )

    def test_duplicate_sequence_is_warned(self):
        add_evidence(self.test_root, "first", sequence=1, photos=[])
        add_evidence(self.test_root, "second", sequence=1, photos=[])

        discovery = discover_evidences(self.test_root)

        self.assertEqual(len(discovery.evidences), 2)
        self.assertTrue(
            any("share sequence 1" in w for w in discovery.warnings)
        )

    def test_referenced_but_missing_photo_is_reported(self):
        directory = add_evidence(
            self.test_root,
            "03_Incident",
            sequence=3,
            photos=["present.jpg", "absent.jpg"],
            create_photos=False,
        )
        (directory / "present.jpg").write_bytes(b"jpeg")

        discovery = discover_evidences(self.test_root)

        evidence = discovery.evidences[0]
        self.assertEqual(
            [photo.found for photo in evidence.photos],
            [True, False],
        )
        self.assertEqual(discovery.found_photos_count, 1)
        self.assertEqual(
            [missing.saved_name for missing in discovery.missing_photos],
            ["absent.jpg"],
        )
        self.assertTrue(
            any("missing photo: absent.jpg" in w for w in discovery.warnings)
        )

    def test_invalid_json_descriptor_is_reported(self):
        directory = self.test_root / "02_Evidences" / "broken"
        directory.mkdir()
        (directory / "evidence.json").write_text("{", encoding="utf-8")

        discovery = discover_evidences(self.test_root)

        self.assertEqual(discovery.evidences, [])
        self.assertEqual(len(discovery.invalid_evidences), 1)
        self.assertEqual(discovery.invalid_evidences[0].folder_name, "broken")
        self.assertIn("valid JSON", discovery.invalid_evidences[0].errors[0])

    def test_descriptor_with_invalid_fields_is_reported(self):
        descriptor = evidence_descriptor(
            folder="bad",
            sequence=1,
            photos=["../escape.jpg"],
        )
        descriptor["sequence"] = "first"
        descriptor["schemaVersion"] = 99
        write_json(
            self.test_root / "02_Evidences" / "bad" / "evidence.json",
            descriptor,
        )

        discovery = discover_evidences(self.test_root)

        self.assertEqual(discovery.evidences, [])
        errors = discovery.invalid_evidences[0].errors
        self.assertTrue(any("'sequence'" in e for e in errors))
        self.assertTrue(any("schemaVersion 99" in e for e in errors))
        self.assertTrue(any("savedName" in e for e in errors))

    def test_folder_without_descriptor_is_warned_and_ignored(self):
        (self.test_root / "02_Evidences" / "loose_photos").mkdir()

        discovery = discover_evidences(self.test_root)

        self.assertEqual(discovery.evidences, [])
        self.assertEqual(discovery.invalid_evidences, [])
        self.assertTrue(
            any("no evidence.json" in w for w in discovery.warnings)
        )

    def test_photos_resolve_from_physical_folder(self):
        descriptor = evidence_descriptor(
            folder="renamed_by_agent",
            sequence=0,
            photos=["photo.jpg"],
        )
        write_json(
            self.test_root / "02_Evidences" / "actual" / "evidence.json",
            descriptor,
        )
        (self.test_root / "02_Evidences" / "actual" / "photo.jpg").write_bytes(
            b"jpeg"
        )

        discovery = discover_evidences(self.test_root)

        evidence = discovery.evidences[0]
        self.assertEqual(evidence.folder_name, "actual")
        self.assertEqual(evidence.declared_folder, "renamed_by_agent")
        self.assertTrue(evidence.photos[0].found)
        self.assertTrue(
            any("declares the folder" in w for w in discovery.warnings)
        )


if __name__ == "__main__":
    unittest.main()
