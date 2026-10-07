"""Helpers that build synthetic test folders for the unit tests."""

import json
from pathlib import Path
from typing import Any

from PIL import Image


def minimal_metadata(**overrides: Any) -> dict[str, Any]:
    """Return the smallest metadata accepted by the report generator."""
    metadata: dict[str, Any] = {
        "schema_version": "1.0",
        "test": {"test_name": "K-01"},
        "people": {},
        "samples": [{"sample_number": 1, "sample_code": "S-1"}],
        "equipment": [],
        "setup": {"images": []},
        "climatic_inputs": {
            "profile_points": [
                {"sequence": 1, "time_min": 0, "temperature_c": 23},
                {"sequence": 2, "time_min": 60, "temperature_c": -40},
            ],
        },
        "dut_controller_inputs": {
            "profile_points": [
                {"sequence": 1, "time_ms": 4, "dut_position_percent": 20},
            ],
        },
        "test_events": [],
    }
    metadata.update(overrides)
    return metadata


def write_json(path: Path, content: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, indent=2), encoding="utf-8")
    return path


def write_image(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 6), "white").save(path)
    return path


def evidence_descriptor(
    *,
    folder: str,
    sequence: int | None,
    photos: list[str],
    title: str | None = None,
) -> dict[str, Any]:
    descriptor: dict[str, Any] = {
        "schemaVersion": 1,
        "id": f"id-{folder}",
        "type": "other",
        "title": title or folder,
        "reference": {"type": "none", "value": ""},
        "notes": "",
        "folder": folder,
        "photos": [
            {
                "id": f"photo-{index}",
                "originalName": f"ORIGINAL_{index}.JPG",
                "savedName": name,
                "captureDate": "2025-10-28T18:43:18",
                "mime": "image/jpeg",
                "size": 10,
            }
            for index, name in enumerate(photos, start=1)
        ],
    }
    if sequence is not None:
        descriptor["sequence"] = sequence
    return descriptor


def add_evidence(
    test_root: Path,
    folder: str,
    *,
    sequence: int | None,
    photos: list[str],
    create_photos: bool = True,
    title: str | None = None,
) -> Path:
    directory = test_root / "02_Evidences" / folder
    write_json(
        directory / "evidence.json",
        evidence_descriptor(
            folder=folder,
            sequence=sequence,
            photos=photos,
            title=title,
        ),
    )
    if create_photos:
        for name in photos:
            write_image(directory / name)
    return directory


def build_test_folder(
    test_root: Path,
    *,
    metadata: dict[str, Any] | None = None,
    data_sources: tuple[str, ...] = (
        "01_SIMPATI",
        "02_CSV",
        "03_Datalogger",
        "04_Graphtec",
    ),
) -> Path:
    """Create the contractual structure of an individual test."""
    (test_root / "01_Inputs").mkdir(parents=True, exist_ok=True)
    (test_root / "02_Evidences").mkdir(exist_ok=True)
    (test_root / "03_Data").mkdir(exist_ok=True)
    for source in data_sources:
        (test_root / "03_Data" / source).mkdir(exist_ok=True)
    (test_root / "04_Report").mkdir(exist_ok=True)

    write_json(
        test_root / "04_Report" / "test_metadata.json",
        metadata if metadata is not None else minimal_metadata(),
    )
    return test_root
