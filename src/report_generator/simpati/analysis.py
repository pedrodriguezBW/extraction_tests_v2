"""Independent analysis of every SIMPATI acquisition of a test.

Each ``.xNN`` file is analyzed on its own: an incompatible or unreadable
file is reported with its error and never prevents the analysis of the
other acquisitions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .channels import classify_channels
from .files import discover_simpati_acquisitions
from .models import (
    STATUS_ERROR,
    STATUS_INCOMPATIBLE,
    STATUS_NO_THERMAL_CHANNELS,
    STATUS_READY,
    SimpatiAcquisitionFile,
    SimpatiAnalysis,
    SimpatiError,
    SimpatiFormatError,
)
from .parser import read_simpati_acquisition


def analyze_simpati_file(acquisition_file: SimpatiAcquisitionFile) -> SimpatiAnalysis:
    """Parse and classify one acquisition, capturing its error if any."""
    try:
        acquisition = read_simpati_acquisition(acquisition_file.path)
    except SimpatiError as error:
        return SimpatiAnalysis(
            file=acquisition_file,
            status=STATUS_INCOMPATIBLE,
            error=error,
        )
    except OSError as error:
        return SimpatiAnalysis(
            file=acquisition_file,
            status=STATUS_ERROR,
            error=error,
        )
    except (ValueError, TypeError, KeyError, UnicodeError) as error:
        return SimpatiAnalysis(
            file=acquisition_file,
            status=STATUS_INCOMPATIBLE,
            error=SimpatiFormatError(str(error) or type(error).__name__),
        )

    channels = classify_channels(acquisition.dataframe)
    status = (
        STATUS_READY
        if any(channel.thermal for channel in channels)
        else STATUS_NO_THERMAL_CHANNELS
    )
    return SimpatiAnalysis(
        file=acquisition_file,
        status=status,
        acquisition=acquisition,
        channels=channels,
    )


@dataclass
class SimpatiAnalysisReport:
    """Result of analyzing every acquisition of a test, in numeric order."""

    analyses: list[SimpatiAnalysis] = field(default_factory=list)

    @property
    def found_count(self) -> int:
        return len(self.analyses)

    @property
    def processed_count(self) -> int:
        return sum(1 for analysis in self.analyses if analysis.processed)

    @property
    def ready_count(self) -> int:
        return sum(1 for analysis in self.analyses if analysis.status == STATUS_READY)

    @property
    def without_thermal_count(self) -> int:
        return sum(
            1
            for analysis in self.analyses
            if analysis.status == STATUS_NO_THERMAL_CHANNELS
        )

    @property
    def incompatible_count(self) -> int:
        return sum(
            1
            for analysis in self.analyses
            if analysis.status in (STATUS_INCOMPATIBLE, STATUS_ERROR)
        )


def analyze_simpati_acquisitions(test_root: str | Path) -> SimpatiAnalysisReport:
    """Discover and analyze every ``.xNN`` acquisition of a test."""
    return SimpatiAnalysisReport(
        analyses=[
            analyze_simpati_file(acquisition_file)
            for acquisition_file in discover_simpati_acquisitions(test_root)
        ]
    )
