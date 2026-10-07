from __future__ import annotations
import re
import shutil
from pathlib import Path
from typing import Any
from pptx import Presentation
from ..metadata import load_test_metadata  # noqa: F401  (re-exported)
from ..paths import report_directory, working_directory


_INVALID_FILENAME_CHARACTERS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def require_report_directory(test_root: Path) -> Path:
    """Return ``04_Report`` or fail when it does not exist."""
    output_directory = report_directory(test_root)

    if not output_directory.is_dir():
        raise FileNotFoundError(
            f"The report folder was not found: {output_directory}"
        )

    return output_directory


def prepare_working_directory(test_root: Path) -> Path:
    """Create ``04_Report/_Working`` inside an existing report folder."""
    require_report_directory(test_root)
    output_directory = working_directory(test_root)

    output_directory.mkdir(parents=True, exist_ok=True)

    return output_directory

def validate_template_path(template_path: Path) -> None:
    if not template_path.is_file():
        raise FileNotFoundError(
            f"The PowerPoint template was not found: {template_path}"
        )

    if template_path.suffix.lower() != ".pptx":
        raise ValueError(
            f"The template must be a .pptx file: {template_path}"
        )


def build_report_filename(test_name: str) -> str:
    """Build a Windows-safe report file name from the test name."""
    safe_name = _INVALID_FILENAME_CHARACTERS.sub("_", str(test_name))
    safe_name = safe_name.strip().rstrip(".")

    if not safe_name:
        raise ValueError(
            "The test name cannot be used as a report file name."
        )

    return f"{safe_name}_report_prototype.pptx"


def create_working_presentation(
    template_path: Path,
    working_directory: Path,
    metadata: dict[str, Any],
) -> Path:
    test_name = metadata["test"]["test_name"]
    output_filename = build_report_filename(test_name)
    output_path = working_directory / output_filename

    shutil.copy2(template_path, output_path)

    return output_path


def publish_report(
    working_path: Path,
    report_directory: Path,
) -> Path:
    """
    Move the completed presentation from ``_Working`` to ``04_Report``.

    The final file only appears in ``04_Report`` once every section has
    been generated, and it replaces a previous report with the same
    name. A previous report that is open in PowerPoint raises
    ``PermissionError`` and is left untouched.
    """
    output_path = Path(report_directory) / Path(working_path).name
    Path(working_path).replace(output_path)
    return output_path

def inspect_slide_shapes(
    presentation_path: Path,
    slide_number: int,
) -> None:
    presentation = Presentation(presentation_path)

    slide_index = slide_number - 1

    if slide_index < 0 or slide_index >= len(presentation.slides):
        raise IndexError(
            f"The presentation does not contain slide {slide_number}. "
            f"Total number of slides: {len(presentation.slides)}"
        )

    slide = presentation.slides[slide_index]

    print(f"\nSlide {slide_number} inspection")
    print(f"Number of elements: {len(slide.shapes)}")

    for shape_index, shape in enumerate(slide.shapes):
        shape_name = shape.name
        shape_type = shape.shape_type

        left_cm = shape.left / 360000
        top_cm = shape.top / 360000
        width_cm = shape.width / 360000
        height_cm = shape.height / 360000

        text = None

        if shape.has_text_frame:
            text = shape.text.strip()

        print(
            f"\nElement {shape_index}"
            f"\n  Name: {shape_name}"
            f"\n  Type: {shape_type}"
            f"\n  Position: x={left_cm:.2f} cm, y={top_cm:.2f} cm"
            f"\n  Size: {width_cm:.2f} × {height_cm:.2f} cm"
            f"\n  Text: {text!r}"
        )
