"""Discovery and safe resolution of SIMPATI acquisitions.

Original SIMPATI exports end in ``.x01`` ... ``.x99``. Every one of them is
an independent acquisition; the indexes do not need to be consecutive.
Files are ordered by the number of their extension, never alphabetically,
so ``.x2`` style ordering problems (``x10`` before ``x2``) cannot happen.
Discovery never opens the files.
"""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath, PureWindowsPath

from ..media import is_temporary_file
from ..paths import simpati_directory
from .models import (
    SimpatiAcquisitionFile,
    SimpatiFileNotFoundError,
    SimpatiPathError,
)

MAX_RELATIVE_PATH_LENGTH = 1024

#: ``.x01`` to ``.x99``; ``.x00``, ``.x100``, ``.xABC``... are not accepted.
_ACQUISITION_SUFFIX = re.compile(r"^\.x(0[1-9]|[1-9][0-9])$", re.IGNORECASE)


def acquisition_index(file_name: str | Path) -> int | None:
    """Return the ``NN`` of a ``.xNN`` acquisition name, or ``None``."""
    suffix = Path(str(file_name)).suffix
    match = _ACQUISITION_SUFFIX.match(suffix)
    return int(match.group(1)) if match else None


def is_acquisition_name(file_name: str | Path) -> bool:
    """Return whether the name ends in a supported ``.x01``-``.x99`` suffix."""
    return acquisition_index(file_name) is not None


def acquisition_sort_key(item: SimpatiAcquisitionFile) -> tuple:
    """Numeric extension order, then a deterministic name tie-break."""
    return (item.index, item.name.casefold(), item.name)


def discover_simpati_acquisitions(
    test_root: str | Path,
) -> list[SimpatiAcquisitionFile]:
    """List every ``.xNN`` acquisition placed directly in ``01_SIMPATI``.

    Subfolders, hidden files and Office lock files are ignored. A missing
    folder returns an empty list: SIMPATI is optional.

    Raises:
        FileNotFoundError: when the test folder does not exist.
        NotADirectoryError: when a path is not a folder.
    """
    project_root = Path(test_root).expanduser().resolve()
    if not project_root.exists():
        raise FileNotFoundError(f"The test folder does not exist: {project_root}")
    if not project_root.is_dir():
        raise NotADirectoryError(
            f"The specified path is not a folder: {project_root}"
        )

    directory = simpati_directory(project_root)
    if not directory.exists():
        return []
    if not directory.is_dir():
        raise NotADirectoryError(
            f"The SIMPATI acquisition path is not a folder:\n{directory}"
        )

    acquisitions: list[SimpatiAcquisitionFile] = []
    for file_path in directory.iterdir():
        index = acquisition_index(file_path.name)
        if index is None or is_temporary_file(file_path):
            continue
        if not file_path.is_file():
            continue
        try:
            size = file_path.stat().st_size
        except OSError:
            continue
        acquisitions.append(
            SimpatiAcquisitionFile(
                path=file_path,
                name=file_path.name,
                relative_path=file_path.relative_to(project_root).as_posix(),
                index=index,
                size=size,
            )
        )
    return sorted(acquisitions, key=acquisition_sort_key)


def resolve_simpati_acquisition(
    test_root: str | Path,
    relative_path: str,
) -> SimpatiAcquisitionFile:
    """Return the discovered acquisition designated by ``relative_path``.

    The path must be relative to the test root, without ``..``, and point
    to a ``.xNN`` file placed directly in ``03_Data/01_SIMPATI``. Files
    from other folders or outside the test are rejected.

    Raises:
        SimpatiPathError: when any check fails.
    """
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise SimpatiPathError("A SIMPATI acquisition must be selected.")
    if len(relative_path) > MAX_RELATIVE_PATH_LENGTH or "\x00" in relative_path:
        raise SimpatiPathError("The file path is invalid.")

    windows_path = PureWindowsPath(relative_path)
    posix_path = PurePosixPath(relative_path.replace("\\", "/"))
    if (
        posix_path.is_absolute()
        or windows_path.is_absolute()
        or windows_path.drive
        or windows_path.root
    ):
        raise SimpatiPathError("Absolute paths are not accepted.")
    if any(part == ".." for part in posix_path.parts):
        raise SimpatiPathError("Paths containing '..' are not accepted.")

    project_root = Path(test_root).expanduser().resolve()
    if not project_root.is_dir():
        raise SimpatiPathError(f"The test folder does not exist: {project_root}")

    source_directory = simpati_directory(project_root).resolve()
    candidate = project_root.joinpath(*posix_path.parts).resolve()

    if candidate.parent != source_directory:
        raise SimpatiPathError(
            "The selected file is not inside 03_Data/01_SIMPATI."
        )
    if not is_acquisition_name(candidate.name):
        raise SimpatiPathError(
            "The selected file is not a SIMPATI acquisition (.x01 to .x99)."
        )
    if is_temporary_file(candidate):
        raise SimpatiPathError("Hidden and temporary files are not accepted.")
    if not candidate.is_file():
        raise SimpatiFileNotFoundError(
            f"The selected SIMPATI acquisition was not found: {relative_path}"
        )

    return SimpatiAcquisitionFile(
        path=candidate,
        name=candidate.name,
        relative_path=candidate.relative_to(project_root).as_posix(),
        index=acquisition_index(candidate.name),
        size=candidate.stat().st_size,
    )
