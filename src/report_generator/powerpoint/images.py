from __future__ import annotations
import re
from pathlib import Path
from PIL import Image
from pptx.util import Cm
from ..paths import rendered_assets_directory

def add_contained_image(
    slide,
    image_path: Path,
    left_cm: float,
    top_cm: float,
    width_cm: float,
    height_cm: float,
) -> None:
    with Image.open(image_path) as image:
        image_width_px, image_height_px = image.size

    image_ratio = image_width_px / image_height_px
    box_ratio = width_cm / height_cm

    if image_ratio > box_ratio:
        # La imagen queda limitada por el ancho del área.
        fitted_width_cm = width_cm
        fitted_height_cm = width_cm / image_ratio
    else:
        # La imagen queda limitada por la altura del área.
        fitted_height_cm = height_cm
        fitted_width_cm = height_cm * image_ratio

    # Centrado horizontal dentro del área 16:9.
    fitted_left_cm = (
        left_cm
        + (width_cm - fitted_width_cm) / 2
    )

    # Alineación superior para acercar la imagen al título.
    fitted_top_cm = top_cm

    slide.shapes.add_picture(
        str(image_path),
        Cm(fitted_left_cm),
        Cm(fitted_top_cm),
        Cm(fitted_width_cm),
        Cm(fitted_height_cm),
    )

def extract_natural_sort_key(file_path):
    """
    Genera una clave de ordenación natural para nombres
    que contienen números.

    Ejemplo:
    chart_2.png aparece antes que chart_10.png.
    """
    name_parts = re.split(
        "([0-9]+)",
        file_path.stem.casefold(),
    )

    return tuple(
        int(part)
        if part.isdigit()
        else part
        for part in name_parts
    )

def find_test_result_charts(test_root):
    """
    Localiza las gráficas de adquisición dentro de:

    04_Report/_RenderedAssets

    Solo selecciona imágenes válidas cuyo nombre contiene
    'simpati_acquisition'.
    """
    test_root = Path(test_root)

    assets_directory = rendered_assets_directory(test_root)

    if not assets_directory.is_dir():
        return []

    supported_extensions = {
        ".png",
        ".jpg",
        ".jpeg",
    }

    result_charts = []

    for file_path in assets_directory.iterdir():
        if not file_path.is_file():
            continue

        if file_path.suffix.casefold() not in supported_extensions:
            continue

        if "simpati_acquisition" not in file_path.stem.casefold():
            continue

        if file_path.stat().st_size <= 0:
            continue

        result_charts.append(file_path)

    result_charts.sort(
        key=extract_natural_sort_key
    )

    return result_charts
