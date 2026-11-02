import builtins
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
        (self.test_root / "03_Data" / "02_Graphtec" / "log.CSV").write_text(
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
        self.assertEqual(
            [source_file.name for source_file in result.data.simpati.files],
            ["acquisition.x03"],
        )
        self.assertTrue(result.data.graphtec.available)
        self.assertEqual(
            [source_file.name for source_file in result.data.graphtec.files],
            ["log.CSV"],
        )
        self.assertTrue(result.data.canoe.found)
        self.assertFalse(result.data.canoe.available)
        self.assertEqual(result.data.canoe.files, [])

    def test_missing_data_sources_are_optional(self):
        for source in ("01_SIMPATI", "02_Graphtec", "03_CANoe"):
            folder = self.test_root / "03_Data" / source
            for file_path in folder.iterdir():
                file_path.unlink()
            folder.rmdir()

        result = inspect_project(self.test_root)

        self.assertTrue(result.valid)
        self.assertEqual(result.warnings, [])
        for source in (
            result.data.simpati,
            result.data.graphtec,
            result.data.canoe,
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
                "No SIMPATI acquisition (.x01 to .x99) was found" in warning
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



class DataSourceFileInventoryTests(unittest.TestCase):
    """Inventory of 03_Data returned by the project inspection."""

    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary_directory.name)
        self.test_root = build_test_folder(
            self.workspace / "TEST - 001",
            data_sources=(),
        )
        self.data_root = self.test_root / "03_Data"

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

    def _sources(self, result):
        return {
            "simpati": result.data.simpati,
            "graphtec": result.data.graphtec,
            "canoe": result.data.canoe,
        }

    def _write(self, relative_path: str, content: bytes = b"") -> Path:
        file_path = self.test_root / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)
        return file_path

    def test_missing_03_data_reports_three_missing_sources(self):
        self.data_root.rmdir()

        result = inspect_project(self.test_root)

        self.assertTrue(result.valid)
        self.assertFalse(result.data.directory.found)
        self.assertTrue(
            any("03_Data" in warning for warning in result.warnings)
        )
        sources = self._sources(result)
        self.assertEqual(list(sources), ["simpati", "graphtec", "canoe"])
        for source in sources.values():
            self.assertFalse(source.found)
            self.assertFalse(source.available)
            self.assertEqual(source.file_count, 0)
            self.assertEqual(source.files, [])
        self.assertFalse(result.data.simpati_file.found)

    def test_03_data_without_source_folders(self):
        result = inspect_project(self.test_root)

        self.assertTrue(result.valid)
        self.assertTrue(result.data.directory.found)
        self.assertEqual(result.warnings, [])
        root = self.test_root.resolve()
        expected_paths = {
            "simpati": root / "03_Data" / "01_SIMPATI",
            "graphtec": root / "03_Data" / "02_Graphtec",
            "canoe": root / "03_Data" / "03_CANoe",
        }
        for key, source in self._sources(result).items():
            self.assertEqual(source.key, key)
            self.assertFalse(source.found)
            self.assertEqual(Path(source.path), expected_paths[key])
            self.assertEqual(source.files, [])

    def test_three_empty_sources(self):
        for folder in ("01_SIMPATI", "02_Graphtec", "03_CANoe"):
            (self.data_root / folder).mkdir()

        result = inspect_project(self.test_root)

        self.assertTrue(result.valid)
        labels = {
            key: source.label
            for key, source in self._sources(result).items()
        }
        self.assertEqual(
            labels,
            {"simpati": "SIMPATI", "graphtec": "Graphtec", "canoe": "CANoe"},
        )
        for source in self._sources(result).values():
            self.assertTrue(source.found)
            self.assertFalse(source.available)
            self.assertEqual(source.file_count, 0)
            self.assertEqual(source.files, [])

    def test_one_simpati_file_is_detected(self):
        self._write("03_Data/01_SIMPATI/acquisition.csv", b"x" * 125)

        result = inspect_project(self.test_root)

        source = result.data.simpati
        self.assertTrue(source.found)
        self.assertTrue(source.available)
        self.assertEqual(source.file_count, 1)
        self.assertEqual(
            source.files[0].model_dump(),
            {
                "name": "acquisition.csv",
                "relative_path": "03_Data/01_SIMPATI/acquisition.csv",
                "extension": ".csv",
                "size": 125,
            },
        )

    def test_several_graphtec_files_are_detected(self):
        self._write("03_Data/02_Graphtec/run_02.csv", b"12")
        self._write("03_Data/02_Graphtec/run_01.gbd", b"1")
        self._write("03_Data/02_Graphtec/notes", b"123")

        result = inspect_project(self.test_root)

        source = result.data.graphtec
        self.assertTrue(source.available)
        self.assertEqual(source.file_count, 3)
        self.assertEqual(
            [
                (f.name, f.extension, f.size)
                for f in source.files
            ],
            [
                ("notes", "", 3),
                ("run_01.gbd", ".gbd", 1),
                ("run_02.csv", ".csv", 2),
            ],
        )

    def test_one_canoe_file_is_detected(self):
        self._write("03_Data/03_CANoe/trace.blf", b"1234")

        result = inspect_project(self.test_root)

        source = result.data.canoe
        self.assertTrue(source.available)
        self.assertEqual(
            [f.relative_path for f in source.files],
            ["03_Data/03_CANoe/trace.blf"],
        )
        self.assertEqual(source.files[0].size, 4)

    def test_subfolders_are_not_listed(self):
        self._write("03_Data/02_Graphtec/run.csv")
        self._write("03_Data/02_Graphtec/archive/old_run.csv")
        (self.data_root / "02_Graphtec" / "empty_folder").mkdir()

        result = inspect_project(self.test_root)

        source = result.data.graphtec
        self.assertEqual(source.file_count, 1)
        self.assertEqual(
            [f.relative_path for f in source.files],
            ["03_Data/02_Graphtec/run.csv"],
        )

    def test_files_are_sorted_case_insensitively(self):
        for name in ("b.csv", "C.csv", "a.csv", "B2.csv", "A1.csv"):
            self._write(f"03_Data/03_CANoe/{name}")

        first = inspect_project(self.test_root)
        second = inspect_project(self.test_root)

        names = [f.name for f in first.data.canoe.files]
        self.assertEqual(names, ["a.csv", "A1.csv", "b.csv", "B2.csv", "C.csv"])
        self.assertEqual(
            names,
            [f.name for f in second.data.canoe.files],
        )

    def test_relative_paths_start_at_the_test_root(self):
        self._write("03_Data/01_SIMPATI/acquisition.x03")
        self._write("03_Data/02_Graphtec/run.csv")
        self._write("03_Data/03_CANoe/trace.asc")

        result = inspect_project(self.test_root)

        root = self.test_root.resolve()
        for source in self._sources(result).values():
            for source_file in source.files:
                self.assertTrue(
                    source_file.relative_path.startswith("03_Data/")
                )
                self.assertNotIn("\\", source_file.relative_path)
                self.assertFalse(Path(source_file.relative_path).is_absolute())
                self.assertTrue(
                    (root / source_file.relative_path).is_file()
                )

    def test_simpati_behaviour_is_preserved(self):
        self._write("03_Data/01_SIMPATI/acquisition.x03", b"data")
        self._write("03_Data/01_SIMPATI/readme.txt", b"notes")

        result = inspect_project(self.test_root)

        self.assertTrue(result.valid)
        self.assertTrue(result.data.simpati_file.found)
        self.assertEqual(result.data.simpati_file.name, "acquisition.x03")
        self.assertEqual(
            [f.name for f in result.data.simpati.files],
            ["acquisition.x03", "readme.txt"],
        )

    def test_every_simpati_acquisition_is_listed_in_numeric_order(self):
        for name in ("run.x10", "run.x07", "run.x01", "run.x03", "run.x00", "run.xABC", "run.csv"):
            self._write(f"03_Data/01_SIMPATI/{name}", b"data")

        result = inspect_project(self.test_root)

        self.assertTrue(result.valid)
        self.assertEqual(
            [(item.label, item.name, item.index) for item in result.data.simpati_acquisitions],
            [
                ("x01", "run.x01", 1),
                ("x03", "run.x03", 3),
                ("x07", "run.x07", 7),
                ("x10", "run.x10", 10),
            ],
        )
        self.assertEqual(
            result.data.simpati_acquisitions[0].relative_path,
            "03_Data/01_SIMPATI/run.x01",
        )
        # The compatibility field points to the first acquisition.
        self.assertEqual(result.data.simpati_file.name, "run.x01")
        self.assertFalse(
            any("SIMPATI" in warning for warning in result.warnings)
        )

    def test_inspection_does_not_read_source_files(self):
        self._write("03_Data/01_SIMPATI/notes.txt", b"a;b")
        self._write("03_Data/02_Graphtec/run.csv", b"a,b")
        self._write("03_Data/03_CANoe/trace.asc", b"date")
        data_root = str(self.data_root.resolve())
        original_open = Path.open
        original_builtin_open = builtins.open

        def guard(target) -> None:
            if str(Path(target).resolve()).startswith(data_root):
                raise AssertionError(f"Source file was opened: {target}")

        def guarded_path_open(path_self, *args, **kwargs):
            guard(path_self)
            return original_open(path_self, *args, **kwargs)

        def guarded_builtin_open(file, *args, **kwargs):
            if isinstance(file, (str, Path)):
                guard(file)
            return original_builtin_open(file, *args, **kwargs)

        with patch.object(Path, "open", guarded_path_open), patch(
            "builtins.open", guarded_builtin_open
        ):
            result = inspect_project(self.test_root)

        self.assertEqual(result.data.simpati.file_count, 1)
        self.assertEqual(result.data.graphtec.file_count, 1)
        self.assertEqual(result.data.canoe.file_count, 1)

if __name__ == "__main__":
    unittest.main()
