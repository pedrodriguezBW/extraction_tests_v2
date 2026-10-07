"""Neutral helpers for image files used by the report generator."""

from pathlib import Path


SUPPORTED_IMAGE_EXTENSIONS = frozenset(
    {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
)


def is_supported_image(file_path: Path) -> bool:
    """Return whether the file extension is a supported image type."""
    return Path(file_path).suffix.casefold() in SUPPORTED_IMAGE_EXTENSIONS


def is_temporary_file(file_path: Path) -> bool:
    """Return whether the file is an Office lock file or hidden file."""
    name = Path(file_path).name
    return name.startswith("~$") or name.startswith(".")
