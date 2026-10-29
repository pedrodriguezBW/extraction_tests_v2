from __future__ import annotations
from pathlib import Path
from pptx import Presentation
from pptx.enum.text import MSO_ANCHOR
from pptx.util import Cm, Pt
from ..evidences import Evidence, EvidenceDiscovery, discover_evidences
from typing import Iterable, Sequence
from ..rendered_assets import (
    MANUAL_SOURCE,
    UNKNOWN_SOURCE,
    metadata_path_for,
    read_asset_metadata,
)
from ..powerpoint.images import add_contained_image
from ..powerpoint.layout import add_section_header
from ..powerpoint.navigation import chunk_items, clear_slide_body, create_continuation_slide, find_slide_in_section
from ..powerpoint.styles import COLOR_GRAY, COLOR_NAVY, CONTENT_LEFT_CM, CONTENT_WIDTH_CM, FONT_FAMILY, FONT_SIZE_LABEL_PT, FONT_SIZE_VALUE_PT, RESULT_HORIZONTAL_GAP_CM, RESULT_VERTICAL_GAP_CM, SINGLE_CHART_HEIGHT_CM, SINGLE_CHART_WIDTH_CM

def add_test_result_image(slide,image_path,left_cm,top_cm,width_cm,height_cm):
    add_contained_image(slide=slide,image_path=image_path,left_cm=left_cm,top_cm=top_cm,width_cm=width_cm,height_cm=height_cm)

def _result_image_source(image_path: Path) -> str:
    """
    Obtiene el origen informativo de una imagen renderizada.

    El origen se lee exclusivamente desde el archivo JSON complementario.
    El nombre de la imagen no se utiliza para deducir su procedencia.
    """
    image_path = Path(image_path)
    metadata_path = metadata_path_for(image_path)

    if not metadata_path.is_file():
        return MANUAL_SOURCE

    metadata = read_asset_metadata(image_path)
    source = metadata.get("source")

    if isinstance(source, str) and source.strip():
        return source.strip().casefold()

    return UNKNOWN_SOURCE


def _result_source_label(source: str) -> str:
    """Devuelve la etiqueta visible correspondiente a un origen."""
    labels = {
        "simpati": "SIMPATI acquisition",
        "graphtec": "Graphtec acquisition",
        "canoe": "CANoe acquisition",
        "manual": "Additional result images",
        "unknown": "Unknown source",
    }

    normalized_source = source.strip().casefold()

    if normalized_source in labels:
        return labels[normalized_source]

    readable_source = normalized_source.replace("_", " ").strip().title()
    return (
        f"{readable_source} acquisition"
        if readable_source
        else "Unknown source"
    )


def _result_images_subtitle(image_paths: Sequence[Path]) -> str:
    """
    Construye el subtítulo de la diapositiva respetando el orden de las imágenes.

    Si hay imágenes de varios orígenes, muestra cada origen una única vez.
    """
    sources: list[str] = []

    for image_path in image_paths:
        source = _result_image_source(Path(image_path))

        if source not in sources:
            sources.append(source)

    if not sources:
        return "Selected result images"

    return " | ".join(
        _result_source_label(source)
        for source in sources
    )


def _add_result_images_header(
    slide,
    image_paths: Sequence[Path],
) -> None:
    """Añade el encabezado secundario y la procedencia de las gráficas."""
    add_section_header(
        slide=slide,
        title="FINAL CHARTS",
        left_cm=CONTENT_LEFT_CM,
        top_cm=4.05,
        width_cm=CONTENT_WIDTH_CM,
    )

    subtitle_box = slide.shapes.add_textbox(
        Cm(CONTENT_LEFT_CM),
        Cm(4.85),
        Cm(CONTENT_WIDTH_CM),
        Cm(0.55),
    )

    text_frame = subtitle_box.text_frame
    text_frame.clear()
    text_frame.margin_left = 0
    text_frame.margin_right = 0
    text_frame.margin_top = 0
    text_frame.margin_bottom = 0

    paragraph = text_frame.paragraphs[0]
    paragraph.text = _result_images_subtitle(image_paths)
    paragraph.font.name = FONT_FAMILY
    paragraph.font.size = Pt(FONT_SIZE_LABEL_PT)
    paragraph.font.bold = True
    paragraph.font.color.rgb = COLOR_GRAY

def populate_test_results_slide(slide, image_paths):
    count = len(image_paths)

    if not count:
        return

    _add_result_images_header(
        slide=slide,
        image_paths=image_paths,
    )

    top = 5.45
    available_height = 10.95

    if count == 1:
        width = SINGLE_CHART_WIDTH_CM
        chart_height = min(SINGLE_CHART_HEIGHT_CM, available_height,)

        add_test_result_image(
            slide,
            image_paths[0],
            CONTENT_LEFT_CM + (CONTENT_WIDTH_CM - width) / 2,
            top + (available_height - chart_height) / 2,
            width,
            chart_height,
        )
        return

    width = (CONTENT_WIDTH_CM - RESULT_HORIZONTAL_GAP_CM) / 2
    chart_height = 8.25
    image_top = top + (available_height - chart_height) / 2

    for index, image_path in enumerate(image_paths[:2]):
        add_test_result_image(
            slide,
            image_path,
            CONTENT_LEFT_CM
            + index * (width + RESULT_HORIZONTAL_GAP_CM),
            image_top,
            width,
            chart_height,
        )

def _reference_text(evidence):
    value=(evidence.reference_value or "").strip();kind=(evidence.reference_type or "").strip()
    if not value:return ""
    if not kind or kind.casefold()=="none":return value
    return f"{value} {kind}"

def _event_label(evidence):
    return (evidence.type or "").strip().replace("_"," ").title()

def _add_evidence_text(slide,evidence):
    add_section_header(slide=slide,title=(evidence.title or evidence.folder_name).strip(),left_cm=CONTENT_LEFT_CM,top_cm=4.05,width_cm=CONTENT_WIDTH_CM)
    parts=[x for x in (_event_label(evidence),_reference_text(evidence)) if x]
    if parts:
        box=slide.shapes.add_textbox(Cm(CONTENT_LEFT_CM),Cm(4.85),Cm(CONTENT_WIDTH_CM),Cm(.55));f=box.text_frame;f.clear();f.margin_left=f.margin_right=f.margin_top=f.margin_bottom=0;p=f.paragraphs[0];p.text=" | ".join(parts);p.font.name=FONT_FAMILY;p.font.size=Pt(FONT_SIZE_LABEL_PT);p.font.bold=True;p.font.color.rgb=COLOR_GRAY
    notes=(evidence.notes or "").strip()
    if notes:
        box=slide.shapes.add_textbox(Cm(CONTENT_LEFT_CM),Cm(5.45),Cm(CONTENT_WIDTH_CM),Cm(1.10));f=box.text_frame;f.clear();f.word_wrap=True;f.margin_left=f.margin_right=f.margin_top=f.margin_bottom=0;f.vertical_anchor=MSO_ANCHOR.TOP;p=f.paragraphs[0];p.text=notes;p.font.name=FONT_FAMILY;p.font.size=Pt(FONT_SIZE_VALUE_PT);p.font.color.rgb=COLOR_NAVY

def populate_evidence_slide(slide,evidence,image_paths):
    _add_evidence_text(slide,evidence)
    if not image_paths:return
    top=6.75;h=9.25
    if len(image_paths)==1:
        width=20.;add_test_result_image(slide,image_paths[0],CONTENT_LEFT_CM+(CONTENT_WIDTH_CM-width)/2,top,width,h);return
    width=(CONTENT_WIDTH_CM-RESULT_HORIZONTAL_GAP_CM)/2
    for i,path in enumerate(image_paths[:2]):add_test_result_image(slide,path,CONTENT_LEFT_CM+i*(width+RESULT_HORIZONTAL_GAP_CM),top,width,h)

def _result_evidences(discovery):
    return [e for e in discovery.evidences if (e.type or "").strip().casefold()!="initial"]

def populate_test_results(presentation_path,test_root,evidence_discovery=None,result_image_paths:Sequence[Path]|Iterable[Path]=()):
    """Fill ``4. Test Results`` with the selected images and the evidences.

    ``result_image_paths`` is the ordered list of images chosen for the
    report (any PNG, JPG or JPEG of ``04_Report/_RenderedAssets``, whatever
    its origin). The engine inserts exactly these images, in this order, in
    groups of two per slide, creating continuation slides when needed. It
    never scans ``_RenderedAssets`` itself and never filters by name or
    source. An empty list produces the evidence slides only.
    """
    presentation_path=Path(presentation_path);test_root=Path(test_root);presentation=Presentation(presentation_path)
    first=find_slide_in_section(presentation=presentation,section_title="TEST A",slide_title="4. Test Results")
    clear_slide_body(slide = first,expected_title="4. Test Results")
    images=[Path(p) for p in (result_image_paths or ())];discovery=evidence_discovery or discover_evidences(test_root);events=_result_evidences(discovery)
    previous=first;used=False
    for group in chunk_items(items=images,chunk_size=2):
        slide=first if not used else create_continuation_slide(presentation=presentation,reference_slide=previous,title="4. Test Results (cont.)");used=True;populate_test_results_slide(slide = slide, image_paths = group);previous=slide
    for evidence in events:
        groups=chunk_items(items=[p.path for p in evidence.found_photos],chunk_size=4) or [[]]
        for group in groups:
            slide=first if not used else create_continuation_slide(presentation=presentation,reference_slide=previous,title="4. Test Results (cont.)");used=True;populate_evidence_slide(slide = slide, evidence = evidence, image_paths = group);previous=slide
    presentation.save(presentation_path)
