"""
Reading and validation of the agent-generated ``test_metadata.json``.

The report generator no longer extracts data from Excel. The metadata
file is produced by an external agent and stored in
``04_Report/test_metadata.json``. This module only reads and validates
it; it never creates or rewrites it.

The validation is intentionally limited to the structure that the
PowerPoint engine relies on. Business values are represented exactly
as they appear in the file.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .paths import metadata_path


class MetadataError(ValueError):
    """Raised when ``test_metadata.json`` cannot be used."""

    def __init__(self, message: str, errors: list[str] | None = None):
        super().__init__(message)
        self.errors = list(errors or [message])


@dataclass(frozen=True)
class MetadataSummary:
    """Compact information about a valid metadata file."""

    test_name: str | None = None
    schema_version: str | None = None
    samples_count: int = 0
    equipment_count: int = 0
    climatic_profile_points_count: int = 0
    dut_profile_points_count: int = 0
    test_events_count: int = 0
    setup_images: list[dict[str, Any]] = field(default_factory=list)


# Sections that must be JSON objects when present.
_OBJECT_SECTIONS = (
    "people",
    "test_facility",
    "setup",
    "climatic_inputs",
    "dut_controller_inputs",
)

# Sections that must be lists of JSON objects when present.
_LIST_SECTIONS = (
    "samples",
    "equipment",
    "test_events",
)

# Profile point lists consumed by the native PowerPoint charts.
_PROFILE_SECTIONS = (
    "climatic_inputs",
    "dut_controller_inputs",
)


def read_metadata_file(metadata_file: Path) -> dict[str, Any]:
    """Read a metadata file and check that it contains a JSON object."""
    metadata_file = Path(metadata_file)

    if not metadata_file.is_file():
        raise FileNotFoundError(
            f"The metadata file was not found: {metadata_file}"
        )

    try:
        with metadata_file.open("r", encoding="utf-8") as file:
            metadata = json.load(file)
    except UnicodeDecodeError as error:
        raise MetadataError(
            "The metadata file is not valid UTF-8."
        ) from error
    except json.JSONDecodeError as error:
        raise MetadataError(
            "The metadata file does not contain valid JSON: "
            f"line {error.lineno}, column {error.colno}."
        ) from error
    except OSError as error:
        raise MetadataError(
            f"The metadata file could not be read: {error}"
        ) from error

    if not isinstance(metadata, dict):
        raise MetadataError(
            "The metadata file must contain a JSON object."
        )

    return metadata


def _is_list_of_objects(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, dict) for item in value
    )


def validate_metadata(metadata: Any) -> list[str]:
    """
    Return the structural errors that prevent report generation.

    An empty list means that the generator can consume the metadata.
    """
    if not isinstance(metadata, dict):
        return ["The metadata file must contain a JSON object."]

    errors: list[str] = []

    test_data = metadata.get("test")
    if not isinstance(test_data, dict):
        errors.append(
            "The metadata must contain a 'test' object."
        )
    else:
        test_name = test_data.get("test_name")
        if not isinstance(test_name, str) or not test_name.strip():
            errors.append(
                "The metadata field 'test.test_name' must be a "
                "non-empty text."
            )

    if not isinstance(metadata.get("people"), dict):
        errors.append(
            "The metadata must contain a 'people' object."
        )

    for section in _OBJECT_SECTIONS:
        value = metadata.get(section)
        if value is not None and not isinstance(value, dict):
            errors.append(
                f"The metadata section '{section}' must be an object."
            )

    for section in _LIST_SECTIONS:
        value = metadata.get(section)
        if value is not None and not _is_list_of_objects(value):
            errors.append(
                f"The metadata section '{section}' must be a list "
                "of objects."
            )

    for section in _PROFILE_SECTIONS:
        section_data = metadata.get(section)
        if not isinstance(section_data, dict):
            continue
        points = section_data.get("profile_points")
        if points is not None and not _is_list_of_objects(points):
            errors.append(
                f"The metadata field '{section}.profile_points' must "
                "be a list of objects."
            )

    setup_data = metadata.get("setup")
    if isinstance(setup_data, dict):
        images = setup_data.get("images")
        if images is not None and not _is_list_of_objects(images):
            errors.append(
                "The metadata field 'setup.images' must be a list "
                "of objects."
            )

    return errors


def summarize_metadata(metadata: dict[str, Any]) -> MetadataSummary:
    """Build a compact summary of an already validated metadata file."""

    def count(value: Any) -> int:
        return len(value) if isinstance(value, list) else 0

    test_data = metadata.get("test") or {}
    climatic_inputs = metadata.get("climatic_inputs") or {}
    dut_inputs = metadata.get("dut_controller_inputs") or {}
    setup_data = metadata.get("setup") or {}

    test_name = test_data.get("test_name")
    schema_version = metadata.get("schema_version")

    return MetadataSummary(
        test_name=str(test_name) if test_name is not None else None,
        schema_version=(
            str(schema_version) if schema_version is not None else None
        ),
        samples_count=count(metadata.get("samples")),
        equipment_count=count(metadata.get("equipment")),
        climatic_profile_points_count=count(
            climatic_inputs.get("profile_points")
        ),
        dut_profile_points_count=count(dut_inputs.get("profile_points")),
        test_events_count=count(metadata.get("test_events")),
        setup_images=list(setup_data.get("images") or []),
    )


def load_test_metadata(test_root: Path) -> dict[str, Any]:
    """
    Load and validate ``04_Report/test_metadata.json``.

    Raises ``FileNotFoundError`` when the file does not exist and
    ``MetadataError`` when it cannot be used for report generation.
    """
    metadata = read_metadata_file(metadata_path(Path(test_root)))
    errors = validate_metadata(metadata)

    if errors:
        raise MetadataError(
            "The metadata file is not valid: " + " ".join(errors),
            errors,
        )

    return metadata


def resolve_setup_images(
    metadata: dict[str, Any],
    test_root: Path,
) -> tuple[list[Path], list[str]]:
    """
    Resolve the setup photos referenced by ``setup.images``.

    Each ``relative_path`` is resolved inside the test folder. Returns
    the existing image paths, in metadata order, and the references
    that could not be found. References that point outside the test
    folder are treated as missing.
    """
    test_root = Path(test_root)
    root = test_root.resolve()
    found: list[Path] = []
    missing: list[str] = []

    setup_data = metadata.get("setup") or {}
    images = setup_data.get("images") if isinstance(setup_data, dict) else []

    for image_data in images or []:
        if not isinstance(image_data, dict):
            continue

        relative_path = image_data.get("relative_path")
        if not isinstance(relative_path, str) or not relative_path.strip():
            continue

        image_path = test_root / Path(relative_path)
        resolved = image_path.resolve()

        if (
            resolved != root
            and root in resolved.parents
            and image_path.is_file()
        ):
            found.append(image_path)
        else:
            missing.append(relative_path)

    return found, missing
