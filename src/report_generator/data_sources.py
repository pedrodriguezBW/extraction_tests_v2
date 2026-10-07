"""Discovery of the optional acquisition sources stored in ``03_Data``."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .media import is_temporary_file
from .paths import (
    csv_directory,
    datalogger_directory,
    graphtec_directory,
    simpati_directory,
)


@dataclass(frozen=True)
class DataSource:
    """Content of one acquisition source folder."""

    key: str
    label: str
    directory: Path
    found: bool
    files: list[Path] = field(default_factory=list)

    @property
    def available(self) -> bool:
        return self.found and bool(self.files)


DATA_SOURCE_DEFINITIONS = (
    ("simpati", "SIMPATI", simpati_directory),
    ("csv", "CSV", csv_directory),
    ("datalogger", "Datalogger", datalogger_directory),
    ("graphtec", "Graphtec", graphtec_directory),
)


def list_source_files(directory: Path) -> list[Path]:
    """List the files of a source folder, ignoring lock and hidden files."""
    if not directory.is_dir():
        return []

    return sorted(
        (
            file_path
            for file_path in directory.rglob("*")
            if file_path.is_file() and not is_temporary_file(file_path)
        ),
        key=lambda file_path: str(file_path).casefold(),
    )


def discover_data_sources(test_root: Path) -> dict[str, DataSource]:
    """Return the four acquisition sources, available or not."""
    test_root = Path(test_root)
    sources: dict[str, DataSource] = {}

    for key, label, directory_builder in DATA_SOURCE_DEFINITIONS:
        directory = directory_builder(test_root)
        sources[key] = DataSource(
            key=key,
            label=label,
            directory=directory,
            found=directory.is_dir(),
            files=list_source_files(directory),
        )

    return sources
