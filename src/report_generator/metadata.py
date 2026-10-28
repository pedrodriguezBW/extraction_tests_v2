"""Lee y valida el archivo ``test_metadata.json`` generado externamente.

El generador de informes no extrae datos del archivo Excel. Un proceso externo
crea ``04_Report/test_metadata.json`` y este módulo se limita a leerlo y
validarlo; nunca lo crea ni lo reescribe.

La validación se limita de forma intencionada a la estructura consumida por el
motor de PowerPoint. Los valores funcionales se conservan tal como aparecen en
el archivo.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .paths import metadata_path


class MetadataError(ValueError):
    """Indica que ``test_metadata.json`` no puede utilizarse.

    Attributes:
        errors: Errores estructurales asociados a la excepción.
    """

    def __init__(self, message: str, errors: list[str] | None = None):
        """Inicializa el error de metadatos.

        Args:
            message: Mensaje principal del error.
            errors: Errores estructurales detectados. Si no se indican, se
                utiliza el mensaje principal como único elemento.
        """
        super().__init__(message)
        self.errors = list(errors or [message])


@dataclass(frozen=True)
class MetadataSummary:
    """Resume la información relevante de un archivo de metadatos válido."""

    #: Nombre del ensayo.
    test_name: str | None = None

    #: Versión declarada del esquema.
    schema_version: str | None = None

    #: Número de muestras.
    samples_count: int = 0

    #: Número de equipos.
    equipment_count: int = 0

    #: Número de puntos del perfil climático.
    climatic_profile_points_count: int = 0

    #: Número de puntos del perfil DUT.
    dut_profile_points_count: int = 0

    #: Número de eventos del ensayo.
    test_events_count: int = 0

    #: Imágenes de montaje declaradas en los metadatos.
    setup_images: list[dict[str, Any]] = field(default_factory=list)


# Secciones que deben ser objetos JSON cuando están presentes.
_OBJECT_SECTIONS = (
    "people",
    "test_facility",
    "setup",
    "climatic_inputs",
    "dut_controller_inputs",
)

# Secciones que deben ser listas de objetos JSON cuando están presentes.
_LIST_SECTIONS = (
    "samples",
    "equipment",
    "test_events",
)

# Listas de puntos consumidas por las gráficas nativas de PowerPoint.
_PROFILE_SECTIONS = (
    "climatic_inputs",
    "dut_controller_inputs",
)


def read_metadata_file(metadata_file: Path) -> dict[str, Any]:
    """Lee un archivo de metadatos y comprueba que contiene un objeto JSON.

    Args:
        metadata_file: Ruta del archivo ``test_metadata.json``.

    Returns:
        Contenido del archivo como diccionario.

    Raises:
        FileNotFoundError: Si el archivo no existe.
        MetadataError: Si el archivo no utiliza UTF-8, no contiene JSON válido,
            no puede leerse o su raíz no es un objeto JSON.
    """
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
    """Comprueba si un valor es una lista formada únicamente por objetos."""
    return isinstance(value, list) and all(
        isinstance(item, dict) for item in value
    )


def validate_metadata(metadata: Any) -> list[str]:
    """Devuelve los errores estructurales que impiden generar el informe.

    Una lista vacía indica que el generador puede consumir los metadatos.

    Args:
        metadata: Contenido que se debe validar.

    Returns:
        Mensajes de error estructural detectados.
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
    """Construye un resumen compacto de metadatos ya validados.

    Args:
        metadata: Metadatos válidos del ensayo.

    Returns:
        Resumen con identificadores y recuentos utilizados por la inspección.
    """

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
    """Carga y valida ``04_Report/test_metadata.json``.

    Args:
        test_root: Ruta de la carpeta raíz del ensayo.

    Returns:
        Metadatos validados del ensayo.

    Raises:
        FileNotFoundError: Si ``test_metadata.json`` no existe.
        MetadataError: Si el archivo no puede utilizarse para generar el
            informe.
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
    """Resuelve las fotografías referenciadas mediante ``setup.images``.

    Cada ``relative_path`` se resuelve dentro de la carpeta del ensayo. Las
    referencias que apuntan fuera de esa carpeta se consideran ausentes.

    Args:
        metadata: Metadatos del ensayo.
        test_root: Ruta de la carpeta raíz del ensayo.

    Returns:
        Una tupla con las rutas existentes, conservando el orden de los
        metadatos, y las referencias que no se han encontrado.
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
