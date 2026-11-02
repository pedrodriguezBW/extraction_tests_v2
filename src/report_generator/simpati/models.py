"""Data model shared by the SIMPATI acquisition modules.

A SIMPATI acquisition is an original ``.xNN`` export (``.x01`` to ``.x99``)
stored in ``03_Data/01_SIMPATI``. The extension number only identifies the
acquisition inside the test: it never decides how the file is parsed nor
which channels it contains. Everything is obtained from the file content.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd


#: Source identifier used in API responses and saved chart metadata.
SIMPATI_SOURCE = "simpati"

#: Name of the timestamp column of every parsed acquisition.
TIMESTAMP_COLUMN = "Timestamp"

#: Timestamp format written by SIMPATI in the first field of each record.
TIMESTAMP_FORMAT = "%d.%m.%Y %H:%M:%S"

#: Field separator of the SIMPATI text exports.
FIELD_SEPARATOR = ";"

#: Analysis status of an acquisition with representable thermal channels.
STATUS_READY = "ready"

#: Analysis status of a valid acquisition without known thermal channels.
STATUS_NO_THERMAL_CHANNELS = "no_thermal_channels"

#: Analysis status of a file whose content is not a SIMPATI acquisition.
STATUS_INCOMPATIBLE = "incompatible"

#: Analysis status of a file that could not be read (permissions, I/O...).
STATUS_ERROR = "error"


class SimpatiError(Exception):
    """Base class for controlled SIMPATI errors."""


class SimpatiFileNotFoundError(SimpatiError):
    """No SIMPATI acquisition (or not the requested one) was found."""


class SimpatiFormatError(SimpatiError):
    """The content does not have a recognizable SIMPATI structure."""


class SimpatiDecodingError(SimpatiFormatError):
    """No supported encoding produces a valid SIMPATI structure."""


class SimpatiPathError(SimpatiError):
    """The requested path is not an acceptable SIMPATI acquisition."""


@dataclass(frozen=True)
class SimpatiAcquisitionFile:
    """Original ``.xNN`` file found in ``03_Data/01_SIMPATI``.

    Only file-system information is collected; the content is not read.
    """

    path: Path
    name: str
    relative_path: str
    index: int
    size: int

    @property
    def label(self) -> str:
        """Short identifier shown to the user, for example ``x04``."""
        return acquisition_label(self.index)


def acquisition_label(index: int) -> str:
    """Return the ``xNN`` identifier of an acquisition index."""
    return f"x{index:02d}"


@dataclass(frozen=True)
class SimpatiHeaderField:
    """One column described by the header and units rows."""

    position: int
    raw_name: str
    raw_unit: str


@dataclass(frozen=True)
class SimpatiStructure:
    """Structural description of a decoded SIMPATI export.

    Row numbers are 0-based indexes into the decoded lines.
    """

    header_row: int
    units_row: int
    first_data_row: int
    fields: tuple[SimpatiHeaderField, ...]
    preamble: dict[str, str] = field(default_factory=dict)

    @property
    def channel_count(self) -> int:
        return len(self.fields)


@dataclass(frozen=True)
class SimpatiChannel:
    """Column of a parsed acquisition and its semantic classification.

    ``role`` is ``None`` when the channel is not recognized by any profile.
    Unrecognized channels are always kept in the parsed result.
    """

    column: str
    name: str
    unit: str
    kind: str
    base_name: str
    role: str | None = None
    label: str | None = None
    thermal: bool = False
    has_data: bool = True

    @property
    def display_label(self) -> str:
        return self.label or self.column


@dataclass
class SimpatiAcquisition:
    """Structural result of parsing one SIMPATI acquisition."""

    source_file: Path
    encoding: str
    index: int | None
    dataframe: pd.DataFrame
    structure: SimpatiStructure
    rejected_rows: list[str] = field(default_factory=list)
    rejected_count: int = 0
    skipped_rows: int = 0
    duplicate_timestamps: int = 0

    @property
    def label(self) -> str | None:
        return None if self.index is None else acquisition_label(self.index)

    @property
    def channel_columns(self) -> list[str]:
        return [
            str(column)
            for column in self.dataframe.columns
            if str(column) != TIMESTAMP_COLUMN
        ]

    @property
    def records_count(self) -> int:
        return len(self.dataframe)

    @property
    def start(self) -> datetime | None:
        if self.dataframe.empty:
            return None
        return self.dataframe[TIMESTAMP_COLUMN].iloc[0].to_pydatetime()

    @property
    def end(self) -> datetime | None:
        if self.dataframe.empty:
            return None
        return self.dataframe[TIMESTAMP_COLUMN].iloc[-1].to_pydatetime()


@dataclass
class SimpatiAnalysis:
    """Isolated analysis of one discovered acquisition.

    ``acquisition`` and ``channels`` are only set when the file could be
    parsed. ``error`` describes why it could not.
    """

    file: SimpatiAcquisitionFile
    status: str
    acquisition: SimpatiAcquisition | None = None
    channels: list[SimpatiChannel] = field(default_factory=list)
    error: SimpatiError | OSError | None = None

    @property
    def thermal_channels(self) -> list[SimpatiChannel]:
        return [channel for channel in self.channels if channel.thermal]

    @property
    def processed(self) -> bool:
        return self.acquisition is not None
