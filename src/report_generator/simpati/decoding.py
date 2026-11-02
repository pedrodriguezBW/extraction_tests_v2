"""Decoding of SIMPATI exports validated by their structure.

A decoding is only accepted when the decoded text has a recognizable
SIMPATI structure (header, units and timestamped records). Not raising a
``UnicodeDecodeError`` is not enough: ``latin-1`` decodes any byte
sequence, so it is only a last resort and, like every other candidate, it
must produce a valid structure without control characters.
"""

from __future__ import annotations

import codecs
import unicodedata

from .models import SimpatiDecodingError, SimpatiFormatError, SimpatiStructure
from .structure import detect_structure

#: Encodings tried, in order, after the UTF-16 detection.
SUPPORTED_ENCODINGS = (
    "utf-8-sig",
    "cp1252",
    "latin-1",
)

_ALLOWED_CONTROLS = {"\t", "\n", "\r", "\x0b", "\x0c"}


def _utf16_candidates(raw_data: bytes) -> list[str]:
    if raw_data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return ["utf-16"]
    sample = raw_data[:4096]
    if len(sample) >= 4 and sample.count(b"\x00") >= len(sample) // 4:
        even_zeros = sample[0::2].count(0)
        odd_zeros = sample[1::2].count(0)
        return ["utf-16-be"] if even_zeros > odd_zeros else ["utf-16-le"]
    return []


def _has_control_characters(text: str) -> bool:
    return any(
        unicodedata.category(character) == "Cc"
        and character not in _ALLOWED_CONTROLS
        for character in set(text)
    )


def decode_simpati_bytes(
    raw_data: bytes,
) -> tuple[list[str], str, SimpatiStructure]:
    """Decode an export and return its lines, encoding and structure.

    Raises:
        SimpatiDecodingError: when no supported encoding yields a valid
            SIMPATI structure.
    """
    if not raw_data.strip():
        raise SimpatiDecodingError("The SIMPATI file is empty.")

    candidates = _utf16_candidates(raw_data) + list(SUPPORTED_ENCODINGS)
    reasons: list[str] = []

    for encoding in candidates:
        try:
            text = raw_data.decode(encoding)
        except UnicodeDecodeError:
            reasons.append(f"{encoding}: not decodable")
            continue
        if _has_control_characters(text):
            reasons.append(f"{encoding}: unexpected control characters")
            continue
        lines = text.splitlines()
        try:
            structure = detect_structure(lines)
        except SimpatiFormatError as error:
            reasons.append(f"{encoding}: {error}")
            continue
        return lines, encoding, structure

    detail = "; ".join(dict.fromkeys(reasons))
    raise SimpatiDecodingError(
        "The file does not have a recognizable SIMPATI structure in any "
        f"supported encoding ({detail})."
    )
