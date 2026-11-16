"""Catálogo ampliable de ensayos y lectura de la norma opcional del metadata."""

import re

STANDARD_METADATA_KEY = "standard"
TEST_TYPES = {
    "Na": {"name": "Rapid change of temperature", "standard": "IEC 60068-2-14:2023"},
    "Nb": {"name": "Change of temperature with specified rate of change", "standard": "IEC 60068-2-14:2023"},
    "Nc": {"name": "Rapid change of temperature, two-fluid-bath method", "standard": "IEC 60068-2-14:2023"},
    "Ab": {"name": "Cold for non-heat-dissipating specimens", "standard": "IEC 60068-2-1:2025"},
    "Bb": {"name": "Dry heat for non-heat-dissipating specimens", "standard": "IEC 60068-2-2:2025"},
}


def description_values(metadata, inputs):
    """El metadata prevalece sobre la edición sugerida por el catálogo."""
    entry = TEST_TYPES.get(inputs.get("test_type"), {})
    code = inputs.get("test_type")
    standard = metadata.get("test", {}).get(STANDARD_METADATA_KEY)
    standard = standard.strip() if isinstance(standard, str) else ""
    return (
        f"{code} – {entry['name']}" if entry else "—",
        standard or entry.get("standard") or "—",
    )


def chamber_description(value):
    """Reconoce tokens completos aunque cambien separadores o mayúsculas."""
    tokens = set(re.findall(r"[A-Z]+", str(value).upper()))
    for token, description in (
        ("TS", "Rapid change chamber – 2 compartments, basket"),
        ("OVEN", "Oven – 1 compartment, dampers"),
        ("HU", "Humidity chamber – 1 compartment, dampers"),
    ):
        if token in tokens:
            return description
    return "—"
