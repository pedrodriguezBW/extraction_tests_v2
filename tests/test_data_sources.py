"""Tests for the discovery of the acquisition sources stored in 03_Data."""

import tempfile
import unittest
from pathlib import Path

from src.report_generator.data_sources import (
    DATA_SOURCE_DEFINITIONS,
    discover_data_sources,
    list_data_source_files,
)


class DataSourceDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.test_root = Path(self.temporary_directory.name) / "TEST - 001"
        self.test_root.mkdir()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _write(self, relative_path: str, content: bytes = b"") -> Path:
        file_path = self.test_root / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)
        return file_path

    def test_only_simpati_graphtec_and_canoe_are_sources(self):
        self.assertEqual(
            [(key, label) for key, label, _ in DATA_SOURCE_DEFINITIONS],
            [
                ("simpati", "SIMPATI"),
                ("graphtec", "Graphtec"),
                ("canoe", "CANoe"),
            ],
        )

    def test_missing_03_data(self):
        sources = discover_data_sources(self.test_root)

        self.assertEqual(list(sources), ["simpati", "graphtec", "canoe"])
        for source in sources.values():
            self.assertFalse(source.found)
            self.assertFalse(source.available)
            self.assertEqual(source.files, [])

    def test_source_directories_follow_the_contract(self):
        sources = discover_data_sources(self.test_root)
        data_root = self.test_root / "03_Data"

        self.assertEqual(sources["simpati"].directory, data_root / "01_SIMPATI")
        self.assertEqual(
            sources["graphtec"].directory,
            data_root / "02_Graphtec",
        )
        self.assertEqual(sources["canoe"].directory, data_root / "03_CANoe")

    def test_file_descriptor_fields(self):
        self._write("03_Data/02_Graphtec/Run.CSV", b"12345")

        source = discover_data_sources(self.test_root)["graphtec"]

        self.assertTrue(source.available)
        source_file = source.files[0]
        self.assertEqual(source_file.name, "Run.CSV")
        self.assertEqual(
            source_file.relative_path,
            "03_Data/02_Graphtec/Run.CSV",
        )
        self.assertEqual(source_file.extension, ".csv")
        self.assertEqual(source_file.size, 5)
        self.assertEqual(
            source_file.path,
            self.test_root / "03_Data" / "02_Graphtec" / "Run.CSV",
        )

    def test_subfolders_hidden_and_lock_files_are_excluded(self):
        directory = self.test_root / "03_Data" / "03_CANoe"
        self._write("03_Data/03_CANoe/trace.blf")
        self._write("03_Data/03_CANoe/old/trace_old.blf")
        self._write("03_Data/03_CANoe/.hidden")
        self._write("03_Data/03_CANoe/~$lock.xlsx")
        (directory / "empty").mkdir()

        files = list_data_source_files(directory, self.test_root)

        self.assertEqual([f.name for f in files], ["trace.blf"])

    def test_order_is_case_insensitive_and_deterministic(self):
        names = ["beta.csv", "Alpha.csv", "alpha2.csv", "BETA2.csv", "gamma"]
        for name in names:
            self._write(f"03_Data/01_SIMPATI/{name}")

        first = discover_data_sources(self.test_root)["simpati"].files
        second = discover_data_sources(self.test_root)["simpati"].files

        expected = ["Alpha.csv", "alpha2.csv", "beta.csv", "BETA2.csv", "gamma"]
        self.assertEqual([f.name for f in first], expected)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
