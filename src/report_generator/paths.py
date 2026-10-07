"""
Folder contract of an individual test.

The application receives the root folder of one test (for example
``TEST - 001``) with the following structure::

    TEST - 001
    ├── 01_Inputs
    ├── 02_Evidences
    │   └── <evidence folder>/evidence.json
    ├── 03_Data
    │   ├── 01_SIMPATI
    │   ├── 02_CSV
    │   ├── 03_Datalogger
    │   └── 04_Graphtec
    └── 04_Report
        ├── test_metadata.json
        ├── _RenderedAssets
        └── _Working

``test_metadata.json`` is produced by an external agent. The report
generator only reads it and writes its own outputs under ``04_Report``.
"""

from pathlib import Path


INPUTS_FOLDER_NAME = "01_Inputs"
EVIDENCES_FOLDER_NAME = "02_Evidences"
DATA_FOLDER_NAME = "03_Data"
SIMPATI_FOLDER_NAME = "01_SIMPATI"
CSV_FOLDER_NAME = "02_CSV"
DATALOGGER_FOLDER_NAME = "03_Datalogger"
GRAPHTEC_FOLDER_NAME = "04_Graphtec"
REPORT_FOLDER_NAME = "04_Report"
RENDERED_ASSETS_FOLDER_NAME = "_RenderedAssets"
WORKING_FOLDER_NAME = "_Working"

METADATA_FILENAME = "test_metadata.json"
EVIDENCE_DESCRIPTOR_FILENAME = "evidence.json"


def inputs_directory(test_root: Path) -> Path:
    return Path(test_root) / INPUTS_FOLDER_NAME


def evidences_directory(test_root: Path) -> Path:
    return Path(test_root) / EVIDENCES_FOLDER_NAME


def data_directory(test_root: Path) -> Path:
    return Path(test_root) / DATA_FOLDER_NAME


def simpati_directory(test_root: Path) -> Path:
    return data_directory(test_root) / SIMPATI_FOLDER_NAME


def csv_directory(test_root: Path) -> Path:
    return data_directory(test_root) / CSV_FOLDER_NAME


def datalogger_directory(test_root: Path) -> Path:
    return data_directory(test_root) / DATALOGGER_FOLDER_NAME


def graphtec_directory(test_root: Path) -> Path:
    return data_directory(test_root) / GRAPHTEC_FOLDER_NAME


def report_directory(test_root: Path) -> Path:
    return Path(test_root) / REPORT_FOLDER_NAME


def rendered_assets_directory(test_root: Path) -> Path:
    return report_directory(test_root) / RENDERED_ASSETS_FOLDER_NAME


def working_directory(test_root: Path) -> Path:
    return report_directory(test_root) / WORKING_FOLDER_NAME


def metadata_path(test_root: Path) -> Path:
    return report_directory(test_root) / METADATA_FILENAME
