"""Orquesta la generación del informe PowerPoint de un ensayo climático."""

from pathlib import Path
from typing import Sequence
import warnings

from .evidence_photos import (
    ASSEMBLY_SECTION,
    RESULTS_SECTION,
    SelectableEvidencePhoto,
    photos_by_evidence,
    select_evidence_photos,
)
from .evidences import EvidenceDiscovery, discover_evidences
from .metadata import load_test_metadata
from .report_inputs import load_report_inputs
from .rendered_assets import list_rendered_assets, select_rendered_assets
from .powerpoint.presentation import (
    create_working_presentation,
    prepare_working_directory,
    prune_climatic_report_slides,
    publish_report,
    require_report_directory,
    validate_template_path,
)
from .sections.test_assembly import populate_test_assembly_images
from .sections.test_description import populate_test_description
from .sections.test_inputs import populate_test_inputs
from .sections.test_results import populate_test_results
from .sections.tested_parts import populate_tested_parts


def resolve_result_images(
    test_root,
    selected_rendered_assets: Sequence[str] | None,
) -> list[Path]:
    """Resuelve las imágenes de resultados que se insertarán en el informe.

    ``None`` significa que no se ha realizado ninguna selección (por ejemplo,
    desde los scripts de consola): se utilizan todas las imágenes válidas del
    inventario de ``04_Report/_RenderedAssets`` en su orden estable. Una lista,
    aunque esté vacía, es una selección explícita: se validan exactamente
    esas rutas relativas, se conserva su orden y nunca se añaden otras.

    Raises:
        ValueError: Si alguna ruta seleccionada es inválida, duplicada,
            externa a ``_RenderedAssets``, inexistente o no es una imagen
            admitida (subclases de ``RenderedAssetError``).
    """
    if selected_rendered_assets is None:
        return [asset.path for asset in list_rendered_assets(test_root).assets]
    return select_rendered_assets(test_root, list(selected_rendered_assets))


def resolve_evidence_photo_selection(
    evidence_discovery: EvidenceDiscovery,
    selected_assembly_photos: Sequence[str] | None,
    selected_result_photos: Sequence[str] | None,
) -> tuple[list[SelectableEvidencePhoto], list[SelectableEvidencePhoto]]:
    """Valida las fotografías de evidencia de ``Test Assembly`` y ``Test Results``.

    Cada lista contiene rutas relativas al ensayo
    (``02_Evidences/<carpeta>/<savedName>``). ``None`` mantiene el
    comportamiento sin selección (Assembly: las 4 primeras fotografías de las
    evidencias ``initial``; Results: todas las del resto de evidencias).
    El resultado conserva siempre el orden automático.

    Raises:
        ValueError: Selección inválida (subclases de ``EvidencePhotoError``).
    """
    return (
        select_evidence_photos(
            evidence_discovery, ASSEMBLY_SECTION, selected_assembly_photos
        ),
        select_evidence_photos(
            evidence_discovery, RESULTS_SECTION, selected_result_photos
        ),
    )


def generate_climatic_report(
    test_root,
    template_path,
    selected_rendered_assets: Sequence[str] | None = None,
    selected_assembly_photos: Sequence[str] | None = None,
    selected_result_photos: Sequence[str] | None = None,
):
    """Genera y publica el informe PowerPoint de un ensayo climático.

    La función carga los metadatos del ensayo, descubre las evidencias,
    prepara una copia de trabajo de la plantilla y completa las secciones del
    informe. Después elimina las diapositivas que no pertenecen al alcance del
    informe climático y publica el archivo terminado en ``04_Report``.

    Las fotografías de montaje se obtienen de las evidencias cuyo tipo es
    ``initial`` (como máximo 4, dos por diapositiva). El resto de evidencias
    se incorpora a la sección de resultados mediante su secuencia declarada;
    cada evidencia conserva su diapositiva aunque no tenga fotografías
    seleccionadas y sus fotografías se colocan dos por diapositiva.

    Las imágenes de resultados proceden de ``04_Report/_RenderedAssets`` y se
    reciben como una lista ordenada de rutas relativas al ensayo
    (``04_Report/_RenderedAssets/<archivo>``). El motor inserta exactamente
    esas imágenes, en ese orden, sin importar su origen (SIMPATI, Graphtec,
    manual o futuras fuentes). Una lista vacía genera el informe sin ellas.

    Args:
        test_root: Ruta de la carpeta raíz del ensayo.
        template_path: Ruta de la plantilla PowerPoint utilizada como base.
        selected_rendered_assets: Rutas relativas ordenadas de las imágenes
            seleccionadas. ``None`` (parámetro omitido) incluye todas las
            imágenes válidas del inventario; ``[]`` no incluye ninguna.
        selected_assembly_photos: Fotografías de evidencias ``initial`` para
            ``Test Assembly`` (máximo 4). ``None`` usa las 4 primeras.
        selected_result_photos: Fotografías del resto de evidencias para
            ``Test Results`` (sin límite). ``None`` usa todas.

    Returns:
        Path: Ruta del informe PowerPoint publicado.

    Raises:
        FileNotFoundError: Si falta la carpeta de informe, los metadatos o la
            plantilla PowerPoint.
        ValueError: Si la plantilla, los datos necesarios o la selección de
            imágenes no son válidos.
        PermissionError: Si el informe no puede publicarse por falta de
            permisos o porque el archivo de destino está bloqueado.
    """
    test_root = Path(test_root)
    template_path = Path(template_path)

    metadata = load_test_metadata(test_root)
    evidence_discovery = discover_evidences(test_root)
    assembly_photos, result_photos = resolve_evidence_photo_selection(
        evidence_discovery,
        selected_assembly_photos,
        selected_result_photos,
    )
    result_image_paths = resolve_result_images(test_root, selected_rendered_assets)

    report_directory = require_report_directory(test_root)
    working_directory = prepare_working_directory(test_root)
    validate_template_path(template_path)
    working_path = create_working_presentation(
        template_path,
        working_directory,
        metadata,
    )

    report_inputs, input_warnings = load_report_inputs(test_root)
    for message in input_warnings:
        warnings.warn(message, UserWarning, stacklevel=2)
    populate_test_description(working_path, metadata, report_inputs.model_dump())
    populate_tested_parts(working_path, metadata)
    populate_test_assembly_images(
        presentation_path=working_path,
        metadata=metadata,
        image_paths=[photo.path for photo in assembly_photos],
        report_inputs=report_inputs.model_dump(),
    )
    populate_test_inputs(working_path, metadata)
    populate_test_results(
        presentation_path=working_path,
        test_root=test_root,
        evidence_discovery=evidence_discovery,
        result_image_paths=result_image_paths,
        evidence_photo_paths=photos_by_evidence(result_photos),
    )

    prune_climatic_report_slides(working_path)
    return publish_report(working_path, report_directory)
