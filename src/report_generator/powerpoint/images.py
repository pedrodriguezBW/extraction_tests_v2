"""Image helpers for the PowerPoint engine.

The engine never discovers images on its own: the images of Test Results
are passed explicitly, already validated, by the caller (see
``sections.test_results.populate_test_results``).
"""

from __future__ import annotations
import re
from pathlib import Path
from PIL import Image
from pptx.util import Cm

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
