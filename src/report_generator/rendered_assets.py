"""Shared storage helpers for images saved in ``04_Report/_RenderedAssets``.

Used by the SIMPATI and Graphtec chart flows so that folder creation, PNG
validation, safe naming, listing and deletion are implemented once.

Which images the PowerPoint includes is decided separately by
:func:`report_generator.powerpoint.images.find_test_result_charts`.
"""

from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path
from typing import Callable, Iterable, Union

from PIL import Image

from .paths import rendered_assets_directory, report_directory

MAX_IMAGE_BYTES = 15 * 1024 * 1024
MAX_IMAGE_DIMENSION = 8000
MAX_CHART_NUMBER = 9999


def prepare_rendered_assets_directory(test_root: Union[str, Path]) -> Path:
    """
    Return ``04_Report/_RenderedAssets``, creating it when needed.

    The report folder itself must already exist because it holds the
    agent-generated ``test_metadata.json``.
    """
    test_root = Path(test_root).expanduser().resolve()
    output_directory = report_directory(test_root)

    if not output_directory.is_dir():
        raise FileNotFoundError(
            "The report folder was not found:\n"
            f"{output_directory}"
        )

    assets_directory = rendered_assets_directory(test_root)

    if assets_directory.exists() and not assets_directory.is_dir():
        raise NotADirectoryError(
            "The rendered assets path is not a directory:\n"
            f"{assets_directory}"
        )

    assets_directory.mkdir(exist_ok=True)

    return assets_directory


def validate_png_bytes(image_bytes: bytes) -> bytes:
    """Check that ``image_bytes`` is a non-empty PNG within the limits."""
    if not image_bytes:
        raise ValueError("The PNG image is empty.")

    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ValueError("The PNG image exceeds the 15 MB limit.")

    with Image.open(BytesIO(image_bytes)) as image:
        if image.format != "PNG":
            raise ValueError("The chart must be a PNG image.")
        if (
            image.width > MAX_IMAGE_DIMENSION
            or image.height > MAX_IMAGE_DIMENSION
        ):
            raise ValueError(
                "The PNG image dimensions exceed the allowed limit."
            )
        image.verify()

    return image_bytes


def chart_file_name(prefix: str, number: int) -> str:
    return f"{prefix}_{number:02d}.png"


def build_next_chart_path(
    output_directory: Path,
    prefix: str,
    companion_suffixes: Iterable[str] = (),
) -> Path:
    """Return the first ``<prefix>_NN.png`` path that is free.

    A number is free when neither the PNG nor any companion file with the
    given suffixes (for example ``.json``) exists.
    """
    output_directory.mkdir(parents=True, exist_ok=True)
    suffixes = tuple(companion_suffixes)

    for chart_number in range(1, MAX_CHART_NUMBER + 1):
        candidate = output_directory / chart_file_name(prefix, chart_number)
        if candidate.exists():
            continue
        if any(candidate.with_suffix(suffix).exists() for suffix in suffixes):
            continue
        return candidate

    raise FileExistsError("No free chart name is available.")


def write_new_chart(
    output_directory: Path,
    prefix: str,
    image_bytes: bytes,
    companions: Callable[[Path], Iterable[tuple[Path, bytes]]] | None = None,
    companion_suffixes: Iterable[str] = (),
) -> Path:
    """Write a PNG under a new generated name without overwriting anything.

    Files are created in exclusive mode, so an existing chart is never
    replaced, even if two saves run at the same time. ``companions`` may
    return extra files (for example a metadata JSON) written next to the
    image; if one of them cannot be written the image is removed again.
    """
    validate_png_bytes(image_bytes)
    suffixes = tuple(companion_suffixes)

    for _attempt in range(MAX_CHART_NUMBER):
        chart_path = build_next_chart_path(output_directory, prefix, suffixes)
        try:
            with open(chart_path, "xb") as handle:
                handle.write(image_bytes)
        except FileExistsError:
            continue

        written: list[Path] = []
        try:
            for companion_path, content in (companions(chart_path) if companions else []):
                with open(companion_path, "xb") as handle:
                    handle.write(content)
                written.append(companion_path)
        except Exception:
            for path in written:
                path.unlink(missing_ok=True)
            chart_path.unlink(missing_ok=True)
            raise
        return chart_path

    raise FileExistsError("No free chart name is available.")


def find_charts_with_prefix(test_root: Union[str, Path], prefix: str) -> list[Path]:
    """List ``<prefix>_NN.png`` images in ``_RenderedAssets`` in number order."""
    assets_directory = rendered_assets_directory(Path(test_root))
    if not assets_directory.is_dir():
        return []

    pattern = re.compile(rf"^{re.escape(prefix)}_(\d+)\.png$", re.IGNORECASE)
    charts = []
    for file_path in assets_directory.iterdir():
        match = pattern.match(file_path.name)
        if match and file_path.is_file() and file_path.stat().st_size > 0:
            charts.append((int(match.group(1)), file_path))
    return [path for _, path in sorted(charts)]


def resolve_saved_chart(
    test_root: Union[str, Path],
    chart_name: str,
    finder: Callable[[Path], list[Path]],
) -> Path | None:
    """Resolve ``chart_name`` only if ``finder`` lists it in _RenderedAssets.

    Returns ``None`` when the chart is not part of the listed set.

    Raises:
        ValueError: when the name contains a path or the file is outside
            ``04_Report/_RenderedAssets``.
    """
    project_root = Path(test_root).expanduser().resolve()
    requested_name = Path(chart_name).name
    if not chart_name or requested_name != chart_name or chart_name in {".", ".."}:
        raise ValueError("The chart name is invalid.")

    chart_path = next(
        (c for c in finder(project_root) if c.name == requested_name),
        None,
    )
    if chart_path is None:
        return None

    resolved = chart_path.resolve()
    if resolved.parent != rendered_assets_directory(project_root).resolve():
        raise ValueError("The chart path is outside 04_Report/_RenderedAssets.")
    return resolved
