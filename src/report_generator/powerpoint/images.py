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

def fit_image_size(
    image_width_px: int,
    image_height_px: int,
    box_width_cm: float,
    box_height_cm: float,
) -> tuple[float, float]:
    """
    Calcula el mayor tamaño de la imagen que cabe en el área sin deformarla.

    La imagen queda limitada por el ancho o por el alto del área según su
    relación de aspecto, nunca por ambos a la vez.
    """
    if image_width_px <= 0 or image_height_px <= 0:
        raise ValueError("The image has no valid size.")

    image_ratio = image_width_px / image_height_px

    if image_ratio >= box_width_cm / box_height_cm:
        return box_width_cm, box_width_cm / image_ratio

    return box_height_cm * image_ratio, box_height_cm


def add_centered_image(
    slide,
    image_path: Path,
    left_cm: float,
    top_cm: float,
    width_cm: float,
    height_cm: float,
):
    """
    Inserta la imagen con el mayor tamaño posible dentro del área indicada,
    conservando su relación de aspecto y centrada en ambos ejes.

    Se usa para las gráficas de ``Test Results``. Las fotografías siguen
    usando ``add_contained_image`` (alineación superior).
    """
    with Image.open(image_path) as image:
        image_width_px, image_height_px = image.size

    fitted_width_cm, fitted_height_cm = fit_image_size(
        image_width_px,
        image_height_px,
        width_cm,
        height_cm,
    )

    return slide.shapes.add_picture(
        str(image_path),
        Cm(left_cm + (width_cm - fitted_width_cm) / 2),
        Cm(top_cm + (height_cm - fitted_height_cm) / 2),
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
