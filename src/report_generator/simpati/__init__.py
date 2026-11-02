"""SIMPATI acquisitions stored in ``03_Data/01_SIMPATI``.

Every original export ``.x01`` ... ``.x99`` is an acquisition. The
extension number only identifies the acquisition; the content alone
decides how it is decoded, which channels it has and which thermal
signals can be represented. Responsibilities are split as follows:

- :mod:`.files`: discovery and safe resolution of the acquisitions.
- :mod:`.decoding`: encoding detection validated by the structure.
- :mod:`.structure`: header, units and records detection.
- :mod:`.parser`: DataFrame construction.
- :mod:`.channels`: semantic classification of the channels.
- :mod:`.analysis`: isolated analysis of every acquisition of a test.
- :mod:`.outputs`: chart names and metadata.
"""

from .analysis import (
    SimpatiAnalysisReport,
    analyze_simpati_acquisitions,
    analyze_simpati_file,
)
from .channels import (
    CHANNEL_PROFILES,
    ChannelProfile,
    classify_channels,
    get_temperature_channels,
    thermal_channels,
)
from .decoding import SUPPORTED_ENCODINGS, decode_simpati_bytes
from .files import (
    acquisition_index,
    discover_simpati_acquisitions,
    is_acquisition_name,
    resolve_simpati_acquisition,
)
from .models import (
    SIMPATI_SOURCE,
    STATUS_ERROR,
    STATUS_INCOMPATIBLE,
    STATUS_NO_THERMAL_CHANNELS,
    STATUS_READY,
    TIMESTAMP_COLUMN,
    TIMESTAMP_FORMAT,
    SimpatiAcquisition,
    SimpatiAcquisitionFile,
    SimpatiAnalysis,
    SimpatiChannel,
    SimpatiDecodingError,
    SimpatiError,
    SimpatiFileNotFoundError,
    SimpatiFormatError,
    SimpatiPathError,
    SimpatiStructure,
    acquisition_label,
)
from .outputs import CHART_PREFIX, chart_metadata, chart_prefix, parse_chart_name
from .parser import (
    build_column_names,
    parse_simpati_content,
    read_simpati,
    read_simpati_acquisition,
)
from .structure import detect_structure

__all__ = [
    "CHANNEL_PROFILES",
    "CHART_PREFIX",
    "ChannelProfile",
    "SIMPATI_SOURCE",
    "STATUS_ERROR",
    "STATUS_INCOMPATIBLE",
    "STATUS_NO_THERMAL_CHANNELS",
    "STATUS_READY",
    "SUPPORTED_ENCODINGS",
    "SimpatiAcquisition",
    "SimpatiAcquisitionFile",
    "SimpatiAnalysis",
    "SimpatiAnalysisReport",
    "SimpatiChannel",
    "SimpatiDecodingError",
    "SimpatiError",
    "SimpatiFileNotFoundError",
    "SimpatiFormatError",
    "SimpatiPathError",
    "SimpatiStructure",
    "TIMESTAMP_COLUMN",
    "TIMESTAMP_FORMAT",
    "acquisition_index",
    "acquisition_label",
    "analyze_simpati_acquisitions",
    "analyze_simpati_file",
    "build_column_names",
    "chart_metadata",
    "chart_prefix",
    "classify_channels",
    "decode_simpati_bytes",
    "detect_structure",
    "discover_simpati_acquisitions",
    "get_temperature_channels",
    "is_acquisition_name",
    "parse_chart_name",
    "parse_simpati_content",
    "read_simpati",
    "read_simpati_acquisition",
    "resolve_simpati_acquisition",
    "thermal_channels",
]
