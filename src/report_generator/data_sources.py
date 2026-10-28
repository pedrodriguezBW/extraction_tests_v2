"""Discovery of the optional acquisition sources stored in ``03_Data``.

SIMPATI, Graphtec and CANoe are data origins. CSV is a file format, not an
independent source. Discovery only lists the files of each source folder; it
never opens or reads their content.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .media import is_temporary_file
from .paths import (
    canoe_directory,
    graphtec_directory,
    simpati_directory,
)


@dataclass(frozen=True)
class DataSourceFile:
    """Regular file found directly inside a source folder.

    Only file-system information is collected; the content is not read.
    """

    path: Path
    name: str
    relative_path: str
    extension: str
    size: int


@dataclass(frozen=True)
class DataSource:
    """Content of one acquisition source folder."""

    key: str
    label: str
    directory: Path
    found: bool
    files: list[DataSourceFile] = field(default_factory=list)

    @property
    def available(self) -> bool:
        return self.found and bool(self.files)


DATA_SOURCE_DEFINITIONS = (
    ("simpati", "SIMPATI", simpati_directory),
    ("graphtec", "Graphtec", graphtec_directory),
    ("canoe", "CANoe", canoe_directory),
)


def _file_sort_key(file_path: Path) -> tuple[str, str]:
    """Case-insensitive name order with a deterministic tie-break."""
    return (file_path.name.casefold(), file_path.name)


def list_source_files(directory: Path) -> list[Path]:
    """List the files of a folder recursively, ignoring lock and hidden files.

    Used to count the files of ``01_Inputs``.
    """
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


def list_data_source_files(
    directory: Path,
    test_root: Path,
) -> list[DataSourceFile]:
    """List the regular files placed directly inside a source folder.

    Subfolders and their content, hidden files and Office lock files are
    excluded. Files are ordered alphabetically without distinguishing case.
    ``relative_path`` is expressed relative to the test root with ``/``
    separators. File content is never opened.

    Args:
        directory: Source folder, for example ``03_Data/02_Graphtec``.
        test_root: Root folder of the test.

    Returns:
        The inventory of the source folder, empty when it does not exist.
    """
    if not directory.is_dir():
        return []

    files: list[DataSourceFile] = []
    for file_path in sorted(directory.iterdir(), key=_file_sort_key):
        if not file_path.is_file() or is_temporary_file(file_path):
            continue
        try:
            size = file_path.stat().st_size
        except OSError:
            continue
        files.append(
            DataSourceFile(
                path=file_path,
                name=file_path.name,
                relative_path=file_path.relative_to(test_root).as_posix(),
                extension=file_path.suffix.lower(),
                size=size,
            )
        )
    return files


def discover_data_sources(test_root: Path) -> dict[str, DataSource]:
    """Return the three acquisition sources, available or not."""
    test_root = Path(test_root)
    sources: dict[str, DataSource] = {}

    for key, label, directory_builder in DATA_SOURCE_DEFINITIONS:
        directory = directory_builder(test_root)
        sources[key] = DataSource(
            key=key,
            label=label,
            directory=directory,
            found=directory.is_dir(),
            files=list_data_source_files(directory, test_root),
        )

    return sources
