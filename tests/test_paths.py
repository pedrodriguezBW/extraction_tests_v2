import unittest
from pathlib import Path

from src.report_generator import paths
from src.report_generator.paths import (
    canoe_directory,
    data_directory,
    evidences_directory,
    graphtec_directory,
    inputs_directory,
    metadata_path,
    rendered_assets_directory,
    report_directory,
    simpati_directory,
    working_directory,
)


class ReportPathTests(unittest.TestCase):
    def setUp(self):
        self.test_root = Path("TEST - 001")

    def test_top_level_directories(self):
        self.assertEqual(
            inputs_directory(self.test_root),
            self.test_root / "01_Inputs",
        )
        self.assertEqual(
            evidences_directory(self.test_root),
            self.test_root / "02_Evidences",
        )
        self.assertEqual(
            data_directory(self.test_root),
            self.test_root / "03_Data",
        )
        self.assertEqual(
            report_directory(self.test_root),
            self.test_root / "04_Report",
        )

    def test_data_source_directories(self):
        data_root = self.test_root / "03_Data"
        self.assertEqual(
            simpati_directory(self.test_root),
            data_root / "01_SIMPATI",
        )
        self.assertEqual(
            graphtec_directory(self.test_root),
            data_root / "02_Graphtec",
        )
        self.assertEqual(
            canoe_directory(self.test_root),
            data_root / "03_CANoe",
        )

    def test_data_source_folder_names_match_the_contract(self):
        self.assertEqual(
            (
                paths.SIMPATI_FOLDER_NAME,
                paths.GRAPHTEC_FOLDER_NAME,
                paths.CANOE_FOLDER_NAME,
            ),
            ("01_SIMPATI", "02_Graphtec", "03_CANoe"),
        )

    def test_report_outputs_live_in_04_report(self):
        report_root = self.test_root / "04_Report"
        self.assertEqual(
            metadata_path(self.test_root),
            report_root / "test_metadata.json",
        )
        self.assertEqual(
            rendered_assets_directory(self.test_root),
            report_root / "_RenderedAssets",
        )
        self.assertEqual(
            working_directory(self.test_root),
            report_root / "_Working",
        )

    def test_paths_accept_text_roots(self):
        self.assertEqual(
            metadata_path("TEST - 001"),
            Path("TEST - 001") / "04_Report" / "test_metadata.json",
        )

    def test_folder_names_match_the_contract(self):
        self.assertEqual(
            {
                paths.INPUTS_FOLDER_NAME,
                paths.EVIDENCES_FOLDER_NAME,
                paths.DATA_FOLDER_NAME,
                paths.REPORT_FOLDER_NAME,
            },
            {"01_Inputs", "02_Evidences", "03_Data", "04_Report"},
        )
        self.assertEqual(
            paths.EVIDENCE_DESCRIPTOR_FILENAME,
            "evidence.json",
        )

if __name__ == "__main__":
    unittest.main()
