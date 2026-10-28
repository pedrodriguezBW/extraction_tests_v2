"""Registry of the supported Graphtec file formats.

Each format is a separate module exposing ``FORMAT_ID``, ``FORMAT_LABEL``,
``SUPPORTED_EXTENSIONS``, ``matches(text)`` and ``parse(text)``. Another
Graphtec format is known to exist; it is not implemented yet and must be
added as a new module in :data:`GRAPHTEC_FORMATS` instead of extending the
TXT parser.

Format selection uses the file content. The extension only restricts which
formats may be tried; the rest of the file name is never interpreted.
"""

from __future__ import annotations

from pathlib import Path

from . import txt_tabulated
from .models import (
    GraphtecAcquisition,
    GraphtecFormatError,
    GraphtecUnsupportedFormatError,
)

GRAPHTEC_FORMATS = (txt_tabulated,)

#: Maximum size accepted for one Graphtec file.
MAX_GRAPHTEC_FILE_BYTES = 20 * 1024 * 1024

SUPPORTED_ENCODINGS = ("utf-8-sig", "cp1252", "latin-1")


def supported_extensions() -> frozenset[str]:
    extensions: set[str] = set()
    for module in GRAPHTEC_FORMATS:
        extensions.update(module.SUPPORTED_EXTENSIONS)
    return frozenset(extensions)


def decode_content(data: bytes) -> str:
    if b"\x00" in data:
        raise GraphtecUnsupportedFormatError(
            "The file is binary and does not match a supported Graphtec format."
        )
    for encoding in SUPPORTED_ENCODINGS:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise GraphtecUnsupportedFormatError("The file encoding is not supported.")


def parse_graphtec_content(text: str, extension: str) -> GraphtecAcquisition:
    """Select the format from the content and parse it."""
    extension = extension.casefold()
    candidates = [
        module
        for module in GRAPHTEC_FORMATS
        if extension in module.SUPPORTED_EXTENSIONS
    ]
    if not candidates:
        allowed = ", ".join(sorted(supported_extensions()))
        raise GraphtecUnsupportedFormatError(
            f"Unsupported Graphtec file type '{extension or '(none)'}'. "
            f"Supported: {allowed}."
        )
    if not text.strip():
        raise GraphtecFormatError("The Graphtec file is empty.")
    for module in candidates:
        if module.matches(text):
            return module.parse(text)
    raise GraphtecUnsupportedFormatError(
        "The file content does not match a supported Graphtec format. "
        "Only the tab-separated TXT format is supported in this version."
    )


def read_graphtec_file(file_path: Path) -> GraphtecAcquisition:
    """Read and parse a Graphtec file without modifying it."""
    file_path = Path(file_path)
    size = file_path.stat().st_size
    if size > MAX_GRAPHTEC_FILE_BYTES:
        raise GraphtecUnsupportedFormatError(
            "The Graphtec file exceeds the 20 MB limit."
        )
    text = decode_content(file_path.read_bytes())
    return parse_graphtec_content(text, file_path.suffix)
