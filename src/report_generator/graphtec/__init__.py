"""Graphtec acquisitions stored in ``03_Data/02_Graphtec``.

Only the tab-separated TXT format is supported in this version. Another
Graphtec format exists and will be added as a separate format module.
The file name is never interpreted.
"""

from .charts import (
    GraphtecChartConfig,
    GraphtecChartConfigError,
    available_series,
    default_chart_config,
    default_title,
    render_graphtec_chart,
    validate_chart_config,
)
from .files import GraphtecPathError, resolve_graphtec_file
from .formats import parse_graphtec_content, read_graphtec_file
from .models import (
    GRAPHTEC_SOURCE,
    GraphtecAcquisition,
    GraphtecError,
    GraphtecFormatError,
    GraphtecRecord,
    GraphtecUnsupportedFormatError,
)

__all__ = [
    "GRAPHTEC_SOURCE",
    "GraphtecAcquisition",
    "GraphtecChartConfig",
    "GraphtecChartConfigError",
    "GraphtecError",
    "GraphtecFormatError",
    "GraphtecPathError",
    "GraphtecRecord",
    "GraphtecUnsupportedFormatError",
    "available_series",
    "default_chart_config",
    "default_title",
    "parse_graphtec_content",
    "read_graphtec_file",
    "render_graphtec_chart",
    "resolve_graphtec_file",
    "validate_chart_config",
]
