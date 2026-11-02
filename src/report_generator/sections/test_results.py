from __future__ import annotations
from pathlib import Path
from pptx import Presentation
from pptx.enum.text import MSO_ANCHOR
from pptx.util import Cm, Pt
from ..evidences import Evidence, EvidenceDiscovery, discover_evidences
from ..evidence_photos import (
    EVIDENCE_PHOTOS_PER_SLIDE,
    RESULTS_SECTION,
    evidence_section,
    is_selectable_photo,
)
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence
from ..rendered_assets import (
    MANUAL_SOURCE,
    UNKNOWN_SOURCE,
    metadata_path_for,
    read_asset_metadata,
)
from ..powerpoint.images import add_centered_image, add_contained_image
from ..powerpoint.layout import add_section_header
from ..powerpoint.navigation import chunk_items, clear_slide_body, create_continuation_slide, find_slide_in_section
from ..powerpoint.styles import (
    COLOR_GRAY,
    COLOR_NAVY,
    CONTENT_LEFT_CM,
    CONTENT_WIDTH_CM,
    FONT_FAMILY,
    FONT_SIZE_LABEL_PT,
    FONT_SIZE_VALUE_PT,
    FOOTER_TOP_CM,
    RESULT_CHARTS_FOOTER_GAP_CM,
    RESULT_CHARTS_PER_SLIDE,
    RESULT_CHARTS_TOP_GAP_CM,
    RESULT_HEADER_TOP_CM,
    RESULT_HORIZONTAL_GAP_CM,
    RESULT_SUBTITLE_HEIGHT_CM,
    RESULT_SUBTITLE_TOP_CM,
)

EMU_PER_CM = 360000

#: Fracción inferior de la diapositiva en la que se buscan los elementos del
#: pie (número, texto de confidencialidad, logotipo del patrón).
FOOTER_SEARCH_FRACTION = 0.75


@dataclass(frozen=True)
class ChartArea:
    """Rectángulo (cm) disponible para las gráficas de una diapositiva."""

    left_cm: float
    top_cm: float
    width_cm: float
    height_cm: float

    @property
    def bottom_cm(self) -> float:
        return self.top_cm + self.height_cm

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


def _result_image_label(image_path: Path) -> str:
    """
    Devuelve la procedencia visible de una imagen.

    Las gráficas SIMPATI guardan en su JSON el identificador ``xNN`` de la
    adquisición de origen; se añade a la etiqueta para distinguir las
    gráficas de varias adquisiciones del mismo ensayo.
    """
    image_path = Path(image_path)
    source = _result_image_source(image_path)
    label = _result_source_label(source)

    if source == "simpati" and metadata_path_for(image_path).is_file():
        acquisition_label = read_asset_metadata(image_path).get(
            "acquisition_label"
        )
        if isinstance(acquisition_label, str) and acquisition_label.strip():
            return f"{label} {acquisition_label.strip()}"

    return label


def _result_images_subtitle(image_paths: Sequence[Path]) -> str:
    """
    Construye el subtítulo de la diapositiva respetando el orden de las imágenes.

    Si hay imágenes de varios orígenes (o de varias adquisiciones SIMPATI),
    muestra cada procedencia una única vez.
    """
    labels: list[str] = []

    for image_path in image_paths:
        label = _result_image_label(Path(image_path))

        if label not in labels:
            labels.append(label)

    if not labels:
        return "Selected result images"

    return " | ".join(labels)


def _add_result_images_header(
    slide,
    image_paths: Sequence[Path],
) -> None:
    """Añade el encabezado secundario y la procedencia de las gráficas."""
    add_section_header(
        slide=slide,
        title="FINAL CHARTS",
        left_cm=CONTENT_LEFT_CM,
        top_cm=RESULT_HEADER_TOP_CM,
        width_cm=CONTENT_WIDTH_CM,
    )

    subtitle_box = slide.shapes.add_textbox(
        Cm(CONTENT_LEFT_CM),
        Cm(RESULT_SUBTITLE_TOP_CM),
        Cm(CONTENT_WIDTH_CM),
        Cm(RESULT_SUBTITLE_HEIGHT_CM),
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

def _cm(value) -> float | None:
    return None if value is None else value / EMU_PER_CM


def _slide_size_cm(slide) -> tuple[float, float]:
    """Tamaño real de la diapositiva según la presentación."""
    presentation = slide.part.package.presentation_part.presentation
    return _cm(presentation.slide_width), _cm(presentation.slide_height)


def _template_shapes(slide):
    """Formas de la diapositiva, de su diseño y de su patrón."""
    layout = slide.slide_layout
    yield from slide.shapes
    yield from layout.shapes
    yield from layout.slide_master.shapes


def _content_columns_cm(slide, slide_width_cm: float) -> tuple[float, float]:
    """
    Margen izquierdo y ancho útil, tomados del marcador de contenido del
    diseño de la plantilla. Si no existe se usan los márgenes corporativos.
    El resultado nunca sobrepasa los márgenes laterales de la diapositiva.
    """
    from pptx.enum.shapes import PP_PLACEHOLDER

    left_cm, width_cm = CONTENT_LEFT_CM, CONTENT_WIDTH_CM

    for placeholder in slide.slide_layout.placeholders:
        if placeholder.placeholder_format.type in (
            PP_PLACEHOLDER.OBJECT,
            PP_PLACEHOLDER.BODY,
        ) and placeholder.width:
            left_cm = _cm(placeholder.left)
            width_cm = _cm(placeholder.width)
            break

    # Márgenes simétricos: el área nunca sale de la diapositiva.
    width_cm = min(width_cm, slide_width_cm - 2 * left_cm)
    return left_cm, width_cm


def _footer_top_cm(slide, slide_height_cm: float) -> float:
    """
    Parte superior del pie: el elemento más alto (número de diapositiva,
    texto de confidencialidad o logotipo) situado en la franja inferior de
    la diapositiva, su diseño o su patrón.
    """
    threshold_cm = slide_height_cm * FOOTER_SEARCH_FRACTION
    tops = [FOOTER_TOP_CM, slide_height_cm]

    for shape in _template_shapes(slide):
        top_cm = _cm(shape.top)
        if top_cm is not None and threshold_cm <= top_cm < slide_height_cm:
            tops.append(top_cm)

    return min(tops)


def result_chart_area(slide) -> ChartArea:
    """
    Espacio útil para las gráficas de ``Test Results``.

    * Arriba: debajo del subtítulo con la procedencia de las gráficas.
    * Abajo: por encima del pie de la plantilla, con un margen de seguridad.
    * Laterales: los del marcador de contenido del diseño.

    Las medidas salen de la plantilla real (tamaño de diapositiva, diseño y
    patrón), no de dimensiones fijas de la imagen.
    """
    slide_width_cm, slide_height_cm = _slide_size_cm(slide)
    left_cm, width_cm = _content_columns_cm(slide, slide_width_cm)
    top_cm = (
        RESULT_SUBTITLE_TOP_CM
        + RESULT_SUBTITLE_HEIGHT_CM
        + RESULT_CHARTS_TOP_GAP_CM
    )
    bottom_cm = (
        _footer_top_cm(slide, slide_height_cm)
        - RESULT_CHARTS_FOOTER_GAP_CM
    )
    return ChartArea(
        left_cm=left_cm,
        top_cm=top_cm,
        width_cm=width_cm,
        height_cm=max(0.0, bottom_cm - top_cm),
    )


def result_chart_boxes(area: ChartArea, count: int) -> list[ChartArea]:
    """
    Reparte el área entre las gráficas de una diapositiva.

    * Una gráfica: todo el ancho útil.
    * Dos gráficas: dos columnas iguales separadas por
      ``RESULT_HORIZONTAL_GAP_CM``; cada una usa toda la altura disponible.

    Nunca se apilan en vertical ni se colocan más de dos por diapositiva.
    """
    if count <= 0:
        return []

    if count == 1:
        return [area]

    if count > RESULT_CHARTS_PER_SLIDE:
        raise ValueError(
            "A Test Results slide holds at most "
            f"{RESULT_CHARTS_PER_SLIDE} charts."
        )

    column_width_cm = (area.width_cm - RESULT_HORIZONTAL_GAP_CM) / 2
    return [
        ChartArea(
            left_cm=area.left_cm
            + index * (column_width_cm + RESULT_HORIZONTAL_GAP_CM),
            top_cm=area.top_cm,
            width_cm=column_width_cm,
            height_cm=area.height_cm,
        )
        for index in range(count)
    ]


def populate_test_results_slide(slide, image_paths):
    count = len(image_paths)

    if not count:
        return

    _add_result_images_header(
        slide=slide,
        image_paths=image_paths,
    )

    # Cada gráfica ocupa el mayor tamaño posible dentro de su caja,
    # centrada y sin deformarse.
    area = result_chart_area(slide)
    for image_path, box in zip(
        image_paths,
        result_chart_boxes(area, count),
    ):
        add_centered_image(
            slide,
            image_path,
            box.left_cm,
            box.top_cm,
            box.width_cm,
            box.height_cm,
        )

def _reference_text(evidence):
    value=(evidence.reference_value or "").strip();kind=(evidence.reference_type or "").strip()
    if not value:return ""
    if not kind or kind.casefold()=="none":return value
    return f"{value} {kind}"

def _event_label(evidence):
    return (evidence.type or "").strip().replace("_"," ").title()

def _add_evidence_text(slide, evidence, continuation: bool = False):
    """Título, tipo/referencia y notas de una evidencia.

    En las diapositivas de continuación se repite el título con ``(cont.)``
    y el tipo/referencia, pero no las notas.
    """
    title = (evidence.title or evidence.folder_name).strip()
    if continuation:
        title = f"{title} (cont.)"
    add_section_header(slide=slide,title=title,left_cm=CONTENT_LEFT_CM,top_cm=4.05,width_cm=CONTENT_WIDTH_CM)
    parts=[x for x in (_event_label(evidence),_reference_text(evidence)) if x]
    if parts:
        box=slide.shapes.add_textbox(Cm(CONTENT_LEFT_CM),Cm(4.85),Cm(CONTENT_WIDTH_CM),Cm(.55));f=box.text_frame;f.clear();f.margin_left=f.margin_right=f.margin_top=f.margin_bottom=0;p=f.paragraphs[0];p.text=" | ".join(parts);p.font.name=FONT_FAMILY;p.font.size=Pt(FONT_SIZE_LABEL_PT);p.font.bold=True;p.font.color.rgb=COLOR_GRAY
    notes=(evidence.notes or "").strip()
    if notes and not continuation:
        box=slide.shapes.add_textbox(Cm(CONTENT_LEFT_CM),Cm(5.45),Cm(CONTENT_WIDTH_CM),Cm(1.10));f=box.text_frame;f.clear();f.word_wrap=True;f.margin_left=f.margin_right=f.margin_top=f.margin_bottom=0;f.vertical_anchor=MSO_ANCHOR.TOP;p=f.paragraphs[0];p.text=notes;p.font.name=FONT_FAMILY;p.font.size=Pt(FONT_SIZE_VALUE_PT);p.font.color.rgb=COLOR_NAVY

def populate_evidence_slide(slide, evidence, image_paths, continuation: bool = False):
    """Rellena una diapositiva de evidencia con, como máximo, dos fotografías.

    Una evidencia sin fotografías seleccionadas conserva su diapositiva con
    el título, la referencia y las notas.
    """
    if len(image_paths) > EVIDENCE_PHOTOS_PER_SLIDE:
        raise ValueError(
            "An evidence slide holds at most "
            f"{EVIDENCE_PHOTOS_PER_SLIDE} photos."
        )
    _add_evidence_text(slide, evidence, continuation)
    if not image_paths:return
    top=6.75;h=9.25
    if len(image_paths)==1:
        width=20.;add_test_result_image(slide,image_paths[0],CONTENT_LEFT_CM+(CONTENT_WIDTH_CM-width)/2,top,width,h);return
    width=(CONTENT_WIDTH_CM-RESULT_HORIZONTAL_GAP_CM)/2
    for i,path in enumerate(image_paths):add_test_result_image(slide,path,CONTENT_LEFT_CM+i*(width+RESULT_HORIZONTAL_GAP_CM),top,width,h)

def _result_evidences(discovery):
    return [e for e in discovery.evidences if evidence_section(e) == RESULTS_SECTION]

def _evidence_photo_paths(evidence, evidence_photo_paths):
    """Fotografías de una evidencia que se insertarán, en orden automático.

    ``None`` (sin selección explícita) usa todas las fotografías válidas.
    """
    if evidence_photo_paths is None:
        return [photo.path for photo in evidence.photos if is_selectable_photo(photo)]
    return [Path(path) for path in evidence_photo_paths.get(evidence.descriptor_path, ())]

def populate_test_results(presentation_path,test_root,evidence_discovery=None,result_image_paths:Sequence[Path]|Iterable[Path]=(),evidence_photo_paths:Mapping[Path,Sequence[Path]]|None=None):
    """Fill ``4. Test Results`` with the selected images and the evidences.

    ``result_image_paths`` is the ordered list of images chosen for the
    report (any PNG, JPG or JPEG of ``04_Report/_RenderedAssets``, whatever
    its origin). The engine inserts exactly these images, in this order, in
    groups of two per slide, creating continuation slides when needed. It
    never scans ``_RenderedAssets`` itself and never filters by name or
    source. An empty list produces the evidence slides only.

    ``evidence_photo_paths`` maps each evidence descriptor path to the
    photos selected for it (already validated, automatic order). Every
    non-initial evidence keeps at least one slide, even without photos;
    photos are placed two per slide with ``(cont.)`` continuation slides.
    ``None`` inserts every valid photo of every evidence.
    """
    presentation_path=Path(presentation_path);test_root=Path(test_root);presentation=Presentation(presentation_path)
    first=find_slide_in_section(presentation=presentation,section_title="TEST A",slide_title="4. Test Results")
    clear_slide_body(slide = first,expected_title="4. Test Results")
    images=[Path(p) for p in (result_image_paths or ())];discovery=evidence_discovery or discover_evidences(test_root);events=_result_evidences(discovery)
    previous=first;used=False
    for group in chunk_items(items=images,chunk_size=RESULT_CHARTS_PER_SLIDE):
        slide=first if not used else create_continuation_slide(presentation=presentation,reference_slide=previous,title="4. Test Results (cont.)");used=True;populate_test_results_slide(slide = slide, image_paths = group);previous=slide
    for evidence in events:
        groups=chunk_items(items=_evidence_photo_paths(evidence, evidence_photo_paths),chunk_size=EVIDENCE_PHOTOS_PER_SLIDE) or [[]]
        for index, group in enumerate(groups):
            slide=first if not used else create_continuation_slide(presentation=presentation,reference_slide=previous,title="4. Test Results (cont.)");used=True;populate_evidence_slide(slide = slide, evidence = evidence, image_paths = group, continuation = index > 0);previous=slide
    presentation.save(presentation_path)
