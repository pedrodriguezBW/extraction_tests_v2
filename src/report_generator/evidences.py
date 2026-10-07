"""
Discovery and validation of test evidences.

Every sub-folder of ``02_Evidences`` may contain an ``evidence.json``
descriptor written by the evidence capture tool. Descriptors are
discovered dynamically, validated, and ordered by ``sequence``. Folder
names are only used as a last tie-breaker and as the physical location
of the photos; they are never parsed to infer the evidence type or
order.

This module does not create slides. It produces a structured result
that the backend, the frontend and future PowerPoint sections can use.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .media import is_supported_image, is_temporary_file
from .paths import EVIDENCE_DESCRIPTOR_FILENAME, evidences_directory


SUPPORTED_EVIDENCE_SCHEMA_VERSIONS = frozenset({1})

_TEXT_FIELDS = ("id", "type", "title", "notes", "folder")
_PHOTO_TEXT_FIELDS = ("id", "originalName", "captureDate", "mime")


@dataclass(frozen=True)
class EvidencePhoto:
    """Photo referenced by an evidence descriptor."""

    saved_name: str
    path: Path
    found: bool
    id: str | None = None
    original_name: str | None = None
    capture_date: str | None = None
    mime: str | None = None
    size: int | None = None


@dataclass(frozen=True)
class Evidence:
    """Valid evidence descriptor with its resolved photos."""

    directory: Path
    descriptor_path: Path
    folder_name: str
    schema_version: int | None = None
    id: str | None = None
    type: str | None = None
    title: str | None = None
    reference_type: str | None = None
    reference_value: str | None = None
    notes: str | None = None
    sequence: int | None = None
    declared_folder: str | None = None
    photos: list[EvidencePhoto] = field(default_factory=list)

    @property
    def found_photos(self) -> list[EvidencePhoto]:
        return [photo for photo in self.photos if photo.found]

    @property
    def missing_photos(self) -> list[EvidencePhoto]:
        return [photo for photo in self.photos if not photo.found]


@dataclass(frozen=True)
class InvalidEvidence:
    """Evidence folder whose descriptor cannot be used."""

    directory: Path
    descriptor_path: Path
    folder_name: str
    errors: list[str]


@dataclass(frozen=True)
class MissingEvidencePhoto:
    """Photo referenced by a descriptor but absent on disk."""

    evidence_folder: str
    evidence_title: str | None
    saved_name: str
    path: Path


@dataclass(frozen=True)
class EvidenceDiscovery:
    """Result of inspecting ``02_Evidences``."""

    directory: Path
    found: bool
    evidences: list[Evidence] = field(default_factory=list)
    invalid_evidences: list[InvalidEvidence] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def photos_count(self) -> int:
        return sum(len(evidence.photos) for evidence in self.evidences)

    @property
    def found_photos_count(self) -> int:
        return sum(
            len(evidence.found_photos) for evidence in self.evidences
        )

    @property
    def missing_photos(self) -> list[MissingEvidencePhoto]:
        return [
            MissingEvidencePhoto(
                evidence_folder=evidence.folder_name,
                evidence_title=evidence.title,
                saved_name=photo.saved_name,
                path=photo.path,
            )
            for evidence in self.evidences
            for photo in evidence.missing_photos
        ]


def _is_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _is_plain_file_name(name: str) -> bool:
    """Reject names that would escape the evidence folder."""
    return (
        bool(name.strip())
        and name not in (".", "..")
        and "/" not in name
        and "\\" not in name
        and ":" not in name
        and Path(name).name == name
    )


def _read_descriptor(descriptor_path: Path) -> Any:
    try:
        with descriptor_path.open("r", encoding="utf-8-sig") as file:
            return json.load(file)
    except UnicodeDecodeError as error:
        raise ValueError(
            f"{EVIDENCE_DESCRIPTOR_FILENAME} is not valid UTF-8."
        ) from error
    except json.JSONDecodeError as error:
        raise ValueError(
            f"{EVIDENCE_DESCRIPTOR_FILENAME} does not contain valid "
            f"JSON: line {error.lineno}, column {error.colno}."
        ) from error
    except OSError as error:
        raise ValueError(
            f"{EVIDENCE_DESCRIPTOR_FILENAME} could not be read: {error}"
        ) from error


def _validate_descriptor(descriptor: Any) -> list[str]:
    if not isinstance(descriptor, dict):
        return ["The descriptor must contain a JSON object."]

    errors: list[str] = []

    schema_version = descriptor.get("schemaVersion")
    if schema_version is not None:
        if not _is_integer(schema_version):
            errors.append("'schemaVersion' must be an integer.")
        elif schema_version not in SUPPORTED_EVIDENCE_SCHEMA_VERSIONS:
            errors.append(
                f"Unsupported schemaVersion {schema_version}."
            )

    sequence = descriptor.get("sequence")
    if sequence is not None and not _is_integer(sequence):
        errors.append("'sequence' must be an integer.")

    for field_name in _TEXT_FIELDS:
        value = descriptor.get(field_name)
        if value is not None and not isinstance(value, str):
            errors.append(f"'{field_name}' must be a text value.")

    reference = descriptor.get("reference")
    if reference is not None and not isinstance(reference, (dict, str)):
        errors.append("'reference' must be an object or a text value.")

    photos = descriptor.get("photos")
    if photos is None:
        return errors

    if not isinstance(photos, list):
        errors.append("'photos' must be a list.")
        return errors

    for index, photo in enumerate(photos, start=1):
        label = f"Photo {index}"

        if not isinstance(photo, dict):
            errors.append(f"{label} must be an object.")
            continue

        saved_name = photo.get("savedName")
        if not isinstance(saved_name, str) or not saved_name.strip():
            errors.append(f"{label} has no 'savedName'.")
        elif not _is_plain_file_name(saved_name):
            errors.append(
                f"{label} 'savedName' must be a file name inside the "
                "evidence folder."
            )

        for field_name in _PHOTO_TEXT_FIELDS:
            value = photo.get(field_name)
            if value is not None and not isinstance(value, str):
                errors.append(
                    f"{label} '{field_name}' must be a text value."
                )

        size = photo.get("size")
        if size is not None and (not _is_integer(size) or size < 0):
            errors.append(
                f"{label} 'size' must be a non-negative integer."
            )

    return errors


def _reference_parts(reference: Any) -> tuple[str | None, str | None]:
    if isinstance(reference, dict):
        return (
            _optional_text(reference.get("type")),
            _optional_text(reference.get("value")),
        )
    if isinstance(reference, str):
        return None, reference
    return None, None


def _build_evidence(
    directory: Path,
    descriptor_path: Path,
    descriptor: dict[str, Any],
) -> Evidence:
    reference_type, reference_value = _reference_parts(
        descriptor.get("reference")
    )

    photos = [
        EvidencePhoto(
            saved_name=photo["savedName"],
            path=directory / photo["savedName"],
            found=(directory / photo["savedName"]).is_file(),
            id=photo.get("id"),
            original_name=photo.get("originalName"),
            capture_date=photo.get("captureDate"),
            mime=photo.get("mime"),
            size=photo.get("size"),
        )
        for photo in descriptor.get("photos") or []
    ]

    return Evidence(
        directory=directory,
        descriptor_path=descriptor_path,
        folder_name=directory.name,
        schema_version=descriptor.get("schemaVersion"),
        id=descriptor.get("id"),
        type=descriptor.get("type"),
        title=descriptor.get("title"),
        reference_type=reference_type,
        reference_value=reference_value,
        notes=descriptor.get("notes"),
        sequence=descriptor.get("sequence"),
        declared_folder=descriptor.get("folder"),
        photos=photos,
    )


def _sort_key(evidence: Evidence) -> tuple[int, int, str]:
    if evidence.sequence is None:
        return (1, 0, evidence.folder_name.casefold())
    return (0, evidence.sequence, evidence.folder_name.casefold())


def _collect_warnings(evidences: list[Evidence]) -> list[str]:
    warnings: list[str] = []
    seen_sequences: dict[int, str] = {}
    seen_ids: dict[str, str] = {}

    for evidence in evidences:
        folder = evidence.folder_name

        if evidence.sequence is None:
            warnings.append(
                f"Evidence '{folder}' has no sequence. It is listed "
                "after the evidences with a sequence."
            )
        elif evidence.sequence in seen_sequences:
            warnings.append(
                f"Evidences '{seen_sequences[evidence.sequence]}' and "
                f"'{folder}' share sequence {evidence.sequence}."
            )
        else:
            seen_sequences[evidence.sequence] = folder

        if evidence.id:
            if evidence.id in seen_ids:
                warnings.append(
                    f"Evidences '{seen_ids[evidence.id]}' and "
                    f"'{folder}' share the id {evidence.id}."
                )
            else:
                seen_ids[evidence.id] = folder

        if (
            evidence.declared_folder
            and evidence.declared_folder != folder
        ):
            warnings.append(
                f"Evidence '{folder}' declares the folder "
                f"'{evidence.declared_folder}'. Photos are resolved "
                "from the folder that contains the descriptor."
            )

        for photo in evidence.photos:
            if not photo.found:
                warnings.append(
                    f"Evidence '{folder}' references a missing photo: "
                    f"{photo.saved_name}"
                )
            elif not is_supported_image(photo.path):
                warnings.append(
                    f"Evidence '{folder}' references a file with an "
                    f"unsupported image format: {photo.saved_name}"
                )

    return warnings


def discover_evidences(test_root: Path) -> EvidenceDiscovery:
    """
    Discover, validate and order the evidences of a test.

    The function only reads files. Missing folders, invalid descriptors
    and missing photos are reported in the result instead of raising.
    """
    directory = evidences_directory(Path(test_root))

    if not directory.is_dir():
        return EvidenceDiscovery(directory=directory, found=False)

    evidences: list[Evidence] = []
    invalid_evidences: list[InvalidEvidence] = []
    warnings: list[str] = []

    subdirectories = sorted(
        (
            child
            for child in directory.iterdir()
            if child.is_dir() and not is_temporary_file(child)
        ),
        key=lambda child: child.name.casefold(),
    )

    for evidence_directory in subdirectories:
        descriptor_path = (
            evidence_directory / EVIDENCE_DESCRIPTOR_FILENAME
        )

        if not descriptor_path.is_file():
            warnings.append(
                f"The evidence folder '{evidence_directory.name}' has "
                f"no {EVIDENCE_DESCRIPTOR_FILENAME} file and was ignored."
            )
            continue

        try:
            descriptor = _read_descriptor(descriptor_path)
        except ValueError as error:
            invalid_evidences.append(
                InvalidEvidence(
                    directory=evidence_directory,
                    descriptor_path=descriptor_path,
                    folder_name=evidence_directory.name,
                    errors=[str(error)],
                )
            )
            continue

        errors = _validate_descriptor(descriptor)
        if errors:
            invalid_evidences.append(
                InvalidEvidence(
                    directory=evidence_directory,
                    descriptor_path=descriptor_path,
                    folder_name=evidence_directory.name,
                    errors=errors,
                )
            )
            continue

        evidences.append(
            _build_evidence(
                evidence_directory,
                descriptor_path,
                descriptor,
            )
        )

    evidences.sort(key=_sort_key)
    warnings.extend(_collect_warnings(evidences))

    return EvidenceDiscovery(
        directory=directory,
        found=True,
        evidences=evidences,
        invalid_evidences=invalid_evidences,
        warnings=warnings,
    )
