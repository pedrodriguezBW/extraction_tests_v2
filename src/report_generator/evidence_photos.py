"""Selección de las fotografías de evidencia que se insertan en el informe.

Las fotografías de ``02_Evidences`` se reparten entre dos secciones del
informe según el tipo de la evidencia que las declara:

* ``assembly``: evidencias de tipo ``initial``. Se insertan en
  ``2. Test Assembly``. Como máximo se admiten
  :data:`ASSEMBLY_MAX_PHOTOS` fotografías.
* ``results``: el resto de evidencias. Se insertan en ``4. Test Results``,
  una diapositiva (o varias) por evidencia, sin límite de selección.

Una fotografía pertenece siempre a una única sección, por lo que nunca puede
seleccionarse para las dos a la vez.

Cada fotografía se identifica por su ruta relativa al ensayo con separadores
``/``: ``02_Evidences/<carpeta de evidencia>/<savedName>``. El orden de
inserción es siempre el automático (``sequence`` de la evidencia y orden del
array ``photos``), independientemente del orden en que se reciba la
selección.

Este módulo no crea diapositivas: valida la selección y devuelve rutas
absolutas listas para el motor PowerPoint.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable, Sequence

from .evidences import Evidence, EvidenceDiscovery, EvidencePhoto
from .media import is_supported_image, is_temporary_file
from .paths import EVIDENCES_FOLDER_NAME


#: Sección ``2. Test Assembly``.
ASSEMBLY_SECTION = "assembly"

#: Sección ``4. Test Results``.
RESULTS_SECTION = "results"

#: Secciones admitidas, en el orden en que aparecen en el informe.
EVIDENCE_PHOTO_SECTIONS = (ASSEMBLY_SECTION, RESULTS_SECTION)

#: Número máximo de fotografías seleccionables para ``Test Assembly``.
ASSEMBLY_MAX_PHOTOS = 4

#: Número máximo de fotografías de evidencia por diapositiva.
EVIDENCE_PHOTOS_PER_SLIDE = 2

#: Tipo de evidencia cuyas fotografías pertenecen a ``Test Assembly``.
ASSEMBLY_EVIDENCE_TYPE = "initial"

_SECTION_LABELS = {
    ASSEMBLY_SECTION: "Test Assembly",
    RESULTS_SECTION: "Test Results",
}


class EvidencePhotoError(ValueError):
    """Error base de la selección de fotografías de evidencia."""


class EvidencePhotoPathError(EvidencePhotoError):
    """La ruta recibida no es una ruta aceptable de fotografía."""


class EvidencePhotoNotFoundError(EvidencePhotoError):
    """La fotografía no está declarada por ninguna evidencia o no existe."""


class EvidencePhotoUnsupportedError(EvidencePhotoError):
    """El archivo no tiene un formato de imagen admitido."""


class EvidencePhotoSectionError(EvidencePhotoError):
    """La fotografía pertenece a la otra sección del informe."""


class EvidencePhotoLimitError(EvidencePhotoError):
    """Se ha superado el número máximo de fotografías de la sección."""


@dataclass(frozen=True)
class SelectableEvidencePhoto:
    """Fotografía de evidencia que puede insertarse en el informe."""

    #: Evidencia que declara la fotografía.
    evidence: Evidence

    #: Fotografía declarada.
    photo: EvidencePhoto

    #: Ruta relativa al ensayo (``02_Evidences/<carpeta>/<savedName>``).
    relative_path: str

    #: Sección del informe a la que pertenece.
    section: str

    @property
    def path(self) -> Path:
        """Ruta absoluta de la fotografía."""
        return self.photo.path


def evidence_section(evidence: Evidence) -> str:
    """Devuelve la sección del informe a la que pertenece una evidencia."""
    evidence_type = (evidence.type or "").strip().casefold()
    if evidence_type == ASSEMBLY_EVIDENCE_TYPE:
        return ASSEMBLY_SECTION
    return RESULTS_SECTION


def evidence_photo_relative_path(
    evidence: Evidence,
    photo: EvidencePhoto,
) -> str:
    """Ruta relativa al ensayo que identifica una fotografía."""
    return f"{EVIDENCES_FOLDER_NAME}/{evidence.folder_name}/{photo.saved_name}"


def is_selectable_photo(photo: EvidencePhoto) -> bool:
    """Indica si una fotografía existe y tiene un formato admitido."""
    return (
        photo.found
        and is_supported_image(photo.path)
        and not is_temporary_file(photo.path)
    )


def _validate_section(section: str) -> str:
    if section not in EVIDENCE_PHOTO_SECTIONS:
        raise ValueError(
            f"Unknown report section for evidence photos: {section!r}."
        )
    return section


def selectable_evidence_photos(
    discovery: EvidenceDiscovery,
    section: str | None = None,
) -> list[SelectableEvidencePhoto]:
    """Fotografías utilizables, en el orden automático del informe.

    Args:
        discovery: Resultado de :func:`discover_evidences`.
        section: ``assembly``, ``results`` o ``None`` para ambas.
    """
    if section is not None:
        _validate_section(section)

    photos: list[SelectableEvidencePhoto] = []
    for evidence in discovery.evidences:
        evidence_photo_section = evidence_section(evidence)
        if section is not None and evidence_photo_section != section:
            continue
        for photo in evidence.photos:
            if not is_selectable_photo(photo):
                continue
            photos.append(
                SelectableEvidencePhoto(
                    evidence=evidence,
                    photo=photo,
                    relative_path=evidence_photo_relative_path(
                        evidence, photo
                    ),
                    section=evidence_photo_section,
                )
            )
    return photos


def normalize_evidence_photo_path(relative_path: object) -> str:
    """Normaliza y valida la forma de una ruta relativa recibida.

    Se aceptan separadores ``\\`` (rutas copiadas desde Windows), pero se
    rechazan las rutas absolutas, las unidades, los segmentos ``.``/``..``
    y las rutas que no estén dentro de ``02_Evidences/<carpeta>/<archivo>``.
    """
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise EvidencePhotoPathError(
            "The evidence photo path must be a non-empty text value."
        )

    text = relative_path.strip().replace("\\", "/")
    if text.startswith("/") or ":" in text:
        raise EvidencePhotoPathError(
            f"The evidence photo path must be relative: {relative_path}"
        )

    parts = PurePosixPath(text).parts
    if any(part in (".", "..") for part in text.split("/")):
        raise EvidencePhotoPathError(
            "The evidence photo path cannot contain '.' or '..': "
            f"{relative_path}"
        )
    if len(parts) != 3 or parts[0] != EVIDENCES_FOLDER_NAME:
        raise EvidencePhotoPathError(
            "The evidence photo path must have the form "
            f"{EVIDENCES_FOLDER_NAME}/<evidence folder>/<photo>: "
            f"{relative_path}"
        )
    return "/".join(parts)


def _declared_photos(
    discovery: EvidenceDiscovery,
) -> dict[str, tuple[Evidence, EvidencePhoto]]:
    """Todas las fotografías declaradas, indexadas por ruta relativa."""
    return {
        evidence_photo_relative_path(evidence, photo): (evidence, photo)
        for evidence in discovery.evidences
        for photo in evidence.photos
    }


def _confined_path(discovery: EvidenceDiscovery, photo: EvidencePhoto) -> Path:
    """Comprueba que la fotografía, con enlaces resueltos, sigue dentro de
    ``02_Evidences``."""
    evidences_root = Path(discovery.directory).resolve()
    resolved = Path(photo.path).resolve()
    if evidences_root not in resolved.parents:
        raise EvidencePhotoPathError(
            "The evidence photo is not inside "
            f"{EVIDENCES_FOLDER_NAME}: {photo.saved_name}"
        )
    return resolved


def resolve_evidence_photo(
    discovery: EvidenceDiscovery,
    relative_path: str,
) -> SelectableEvidencePhoto:
    """Resuelve una fotografía declarada por una evidencia válida.

    Raises:
        EvidencePhotoPathError: Ruta mal formada o fuera de ``02_Evidences``.
        EvidencePhotoNotFoundError: No la declara ninguna evidencia válida o
            el archivo no existe.
        EvidencePhotoUnsupportedError: El formato no es una imagen admitida.
    """
    key = normalize_evidence_photo_path(relative_path)
    declared = _declared_photos(discovery)

    match = declared.get(key)
    if match is None:
        folded = key.casefold()
        candidates = [
            value for name, value in declared.items()
            if name.casefold() == folded
        ]
        if len(candidates) == 1:
            match = candidates[0]

    if match is None:
        raise EvidencePhotoNotFoundError(
            "The photo is not declared by any valid evidence: "
            f"{relative_path}"
        )

    evidence, photo = match
    if not photo.found:
        raise EvidencePhotoNotFoundError(
            f"The evidence photo was not found on disk: {relative_path}"
        )
    if not is_supported_image(photo.path) or is_temporary_file(photo.path):
        raise EvidencePhotoUnsupportedError(
            f"The evidence photo is not a supported image: {relative_path}"
        )
    _confined_path(discovery, photo)

    return SelectableEvidencePhoto(
        evidence=evidence,
        photo=photo,
        relative_path=evidence_photo_relative_path(evidence, photo),
        section=evidence_section(evidence),
    )


def select_evidence_photos(
    discovery: EvidenceDiscovery,
    section: str,
    selection: Sequence[str] | None,
) -> list[SelectableEvidencePhoto]:
    """Valida la selección de una sección y la devuelve en orden automático.

    * ``None``: no hay selección explícita (scripts de consola o clientes
      antiguos). ``assembly`` usa las :data:`ASSEMBLY_MAX_PHOTOS` primeras
      fotografías válidas; ``results`` usa todas.
    * Lista (aunque esté vacía): selección explícita. Se insertan exactamente
      esas fotografías y ninguna otra.

    Raises:
        EvidencePhotoPathError, EvidencePhotoNotFoundError,
        EvidencePhotoUnsupportedError: Ruta inválida, ajena o inexistente.
        EvidencePhotoSectionError: La fotografía pertenece a la otra sección.
        EvidencePhotoLimitError: Más de :data:`ASSEMBLY_MAX_PHOTOS`
            fotografías para ``Test Assembly`` o rutas duplicadas.
    """
    _validate_section(section)
    available = selectable_evidence_photos(discovery, section)

    if selection is None:
        if section == ASSEMBLY_SECTION:
            return available[:ASSEMBLY_MAX_PHOTOS]
        return available

    if isinstance(selection, (str, bytes)):
        raise EvidencePhotoPathError(
            "The evidence photo selection must be a list of paths."
        )

    chosen: set[str] = set()
    for relative_path in selection:
        resolved = resolve_evidence_photo(discovery, relative_path)
        if resolved.section != section:
            raise EvidencePhotoSectionError(
                f"The photo {resolved.relative_path} belongs to "
                f"{_SECTION_LABELS[resolved.section]}, not to "
                f"{_SECTION_LABELS[section]}."
            )
        if resolved.relative_path in chosen:
            raise EvidencePhotoPathError(
                "The evidence photo is selected more than once: "
                f"{resolved.relative_path}"
            )
        chosen.add(resolved.relative_path)

    if section == ASSEMBLY_SECTION and len(chosen) > ASSEMBLY_MAX_PHOTOS:
        raise EvidencePhotoLimitError(
            f"Test Assembly admits at most {ASSEMBLY_MAX_PHOTOS} photos; "
            f"{len(chosen)} were selected."
        )

    return [photo for photo in available if photo.relative_path in chosen]


def photos_by_evidence(
    photos: Iterable[SelectableEvidencePhoto],
) -> dict[Path, list[Path]]:
    """Agrupa fotografías por descriptor de evidencia conservando el orden."""
    grouped: dict[Path, list[Path]] = {}
    for item in photos:
        grouped.setdefault(item.evidence.descriptor_path, []).append(item.path)
    return grouped
