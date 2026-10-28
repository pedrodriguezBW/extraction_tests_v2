"""Descubre y valida las evidencias de un ensayo.

Cada subcarpeta de ``02_Evidences`` puede contener un descriptor
``evidence.json`` generado por la herramienta de captura de evidencias. Los
descriptores se descubren dinámicamente, se validan y se ordenan mediante
``sequence``.

Los nombres de las carpetas solo se utilizan como último criterio de desempate
y como ubicación física de las fotografías. Nunca se interpretan para deducir
el tipo ni el orden de una evidencia.

Este módulo no crea diapositivas. Produce un resultado estructurado que pueden
utilizar el backend, el frontend y las secciones del informe PowerPoint.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .media import is_supported_image, is_temporary_file
from .paths import EVIDENCE_DESCRIPTOR_FILENAME, evidences_directory


#: Versiones del esquema ``evidence.json`` admitidas por la aplicación.
SUPPORTED_EVIDENCE_SCHEMA_VERSIONS = frozenset({1})

_TEXT_FIELDS = ("id", "type", "title", "notes", "folder")
_PHOTO_TEXT_FIELDS = ("id", "originalName", "captureDate", "mime")


@dataclass(frozen=True)
class EvidencePhoto:
    """Representa una fotografía declarada por un descriptor de evidencia."""

    #: Nombre con el que la fotografía está guardada.
    saved_name: str

    #: Ruta resuelta del archivo.
    path: Path

    #: Indica si el archivo existe.
    found: bool

    #: Identificador declarado de la fotografía.
    id: str | None = None

    #: Nombre original del archivo.
    original_name: str | None = None

    #: Fecha y hora de captura declaradas.
    capture_date: str | None = None

    #: Tipo MIME declarado.
    mime: str | None = None

    #: Tamaño declarado del archivo en bytes.
    size: int | None = None


@dataclass(frozen=True)
class Evidence:
    """Representa un descriptor válido y sus fotografías resueltas."""

    #: Carpeta física que contiene la evidencia.
    directory: Path

    #: Ruta del descriptor ``evidence.json``.
    descriptor_path: Path

    #: Nombre real de la carpeta de la evidencia.
    folder_name: str

    #: Versión declarada del esquema.
    schema_version: int | None = None

    #: Identificador de la evidencia.
    id: str | None = None

    #: Tipo de evidencia.
    type: str | None = None

    #: Título visible de la evidencia.
    title: str | None = None

    #: Tipo de referencia temporal o funcional.
    reference_type: str | None = None

    #: Valor asociado a la referencia.
    reference_value: str | None = None

    #: Notas declaradas para la evidencia.
    notes: str | None = None

    #: Posición cronológica de la evidencia.
    sequence: int | None = None

    #: Nombre de carpeta declarado dentro del descriptor.
    declared_folder: str | None = None

    #: Fotografías declaradas por la evidencia.
    photos: list[EvidencePhoto] = field(default_factory=list)

    @property
    def found_photos(self) -> list[EvidencePhoto]:
        """Devuelve las fotografías cuyo archivo existe."""
        return [photo for photo in self.photos if photo.found]

    @property
    def missing_photos(self) -> list[EvidencePhoto]:
        """Devuelve las fotografías cuyo archivo no se ha encontrado."""
        return [photo for photo in self.photos if not photo.found]


@dataclass(frozen=True)
class InvalidEvidence:
    """Representa una carpeta cuyo descriptor no puede utilizarse."""

    #: Carpeta física inspeccionada.
    directory: Path

    #: Ruta del descriptor no válido.
    descriptor_path: Path

    #: Nombre de la carpeta de la evidencia.
    folder_name: str

    #: Errores detectados durante la lectura o validación.
    errors: list[str]


@dataclass(frozen=True)
class MissingEvidencePhoto:
    """Representa una fotografía declarada que no existe en disco."""

    #: Carpeta de la evidencia.
    evidence_folder: str

    #: Título de la evidencia.
    evidence_title: str | None

    #: Nombre esperado del archivo.
    saved_name: str

    #: Ruta esperada de la fotografía.
    path: Path


@dataclass(frozen=True)
class EvidenceDiscovery:
    """Contiene el resultado de inspeccionar ``02_Evidences``."""

    #: Ruta de la carpeta de evidencias.
    directory: Path

    #: Indica si la carpeta de evidencias existe.
    found: bool

    #: Evidencias válidas ordenadas por secuencia.
    evidences: list[Evidence] = field(default_factory=list)

    #: Evidencias cuyos descriptores no son válidos.
    invalid_evidences: list[InvalidEvidence] = field(default_factory=list)

    #: Advertencias no bloqueantes detectadas durante la inspección.
    warnings: list[str] = field(default_factory=list)

    @property
    def photos_count(self) -> int:
        """Devuelve el número total de fotografías declaradas."""
        return sum(len(evidence.photos) for evidence in self.evidences)

    @property
    def found_photos_count(self) -> int:
        """Devuelve el número total de fotografías encontradas."""
        return sum(
            len(evidence.found_photos) for evidence in self.evidences
        )

    @property
    def missing_photos(self) -> list[MissingEvidencePhoto]:
        """Devuelve la información agregada de las fotografías ausentes."""
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

    def found_photo_paths_for_type(self, evidence_type: str) -> list[Path]:
        """Obtiene las fotografías válidas de un tipo de evidencia.

        Args:
            evidence_type: Tipo de evidencia que se debe seleccionar.

        Returns:
            Rutas de las fotografías existentes con un formato compatible.
        """
        normalized_type = evidence_type.strip().casefold()
        return [
            photo.path
            for evidence in self.evidences
            if (evidence.type or "").strip().casefold() == normalized_type
            for photo in evidence.found_photos
            if is_supported_image(photo.path)
        ]


def _is_integer(value: Any) -> bool:
    """Comprueba si un valor es un entero y no un booleano."""
    return isinstance(value, int) and not isinstance(value, bool)


def _optional_text(value: Any) -> str | None:
    """Convierte un valor opcional a texto sin modificar los valores nulos."""
    if value is None:
        return None
    return str(value)


def _is_plain_file_name(name: str) -> bool:
    """Rechaza nombres que podrían escapar de la carpeta de evidencia."""
    return (
        bool(name.strip())
        and name not in (".", "..")
        and "/" not in name
        and "\\" not in name
        and ":" not in name
        and Path(name).name == name
    )


def _read_descriptor(descriptor_path: Path) -> Any:
    """Lee un descriptor de evidencia y devuelve su contenido JSON."""
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
    """Devuelve los errores estructurales de un descriptor de evidencia."""
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
    """Separa una referencia en su tipo y su valor opcionales."""
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
    """Construye una evidencia validada y resuelve sus fotografías."""
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
    """Construye la clave utilizada para ordenar las evidencias."""
    if evidence.sequence is None:
        return (1, 0, evidence.folder_name.casefold())
    return (0, evidence.sequence, evidence.folder_name.casefold())


def _collect_warnings(evidences: list[Evidence]) -> list[str]:
    """Recopila advertencias no bloqueantes de evidencias válidas."""
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
    """Descubre, valida y ordena las evidencias de un ensayo.

    La función solo lee archivos. Las carpetas ausentes, los descriptores no
    válidos y las fotografías que faltan se reflejan en el resultado en lugar
    de provocar una excepción.

    Args:
        test_root: Ruta de la carpeta raíz del ensayo.

    Returns:
        Resultado estructurado de la inspección de ``02_Evidences``.
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
