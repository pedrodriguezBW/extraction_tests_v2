"""Names and metadata of the charts generated from SIMPATI acquisitions.

Charts are stored in ``04_Report/_RenderedAssets`` as
``chart_simpati_xNN_MM.png``: ``NN`` is the acquisition index and ``MM``
the chart number of that acquisition. Charts of different acquisitions
never collide, keep a natural order (``x01`` charts before ``x04``
charts, ``_02`` before ``_10``) and are generic rendered assets for the
report. A companion JSON records the source file of each chart.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from .models import SIMPATI_SOURCE, SimpatiAcquisitionFile, acquisition_label

#: Common prefix of every SIMPATI chart.
CHART_PREFIX = "chart_simpati"

#: Version of the companion metadata written next to each chart.
METADATA_SCHEMA_VERSION = 2

_CHART_NAME = re.compile(
    rf"^{CHART_PREFIX}_x(?P<index>\d{{2}})_(?P<number>\d+)\.png$",
    re.IGNORECASE,
)


def chart_prefix(index: int) -> str:
    """``chart_simpati_x04`` for acquisition ``.x04``."""
    return f"{CHART_PREFIX}_{acquisition_label(index)}"


def parse_chart_name(name: str) -> tuple[int, int] | None:
    """Return ``(acquisition index, chart number)`` of a chart name."""
    match = _CHART_NAME.match(name)
    if match is None:
        return None
    return int(match.group("index")), int(match.group("number"))


def chart_metadata(
    chart_name: str,
    image_size: int,
    acquisition_file: SimpatiAcquisitionFile,
) -> dict:
    """Companion metadata linking a chart to its source acquisition."""
    return {
        "schema_version": METADATA_SCHEMA_VERSION,
        "source": SIMPATI_SOURCE,
        "chart_name": chart_name,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "size": image_size,
        "source_file": acquisition_file.name,
        "source_relative_path": acquisition_file.relative_path,
        "acquisition_index": acquisition_file.index,
        "acquisition_label": acquisition_file.label,
    }
