"""Safe resolution of a Graphtec file selected by the user.

The client sends ``test_root`` and a ``relative_path`` taken from the
project inspection. The path is rebuilt and confined to
``03_Data/02_Graphtec`` before any file is opened.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath

from ..media import is_temporary_file
from ..paths import graphtec_directory
from .models import GraphtecError

MAX_RELATIVE_PATH_LENGTH = 1024


class GraphtecPathError(GraphtecError):
    """The requested path is not an acceptable Graphtec file."""


def resolve_graphtec_file(test_root: str | Path, relative_path: str) -> Path:
    """Return the absolute path of a Graphtec file inside the test.

    Checks, in order:

    1. ``relative_path`` is a non-empty relative path without ``..``.
    2. ``test_root`` exists and is a folder.
    3. The rebuilt path, with links resolved, is a direct child of
       ``03_Data/02_Graphtec``. Files from SIMPATI, CANoe, other folders or
       outside the test are rejected.
    4. It is a regular, non-hidden file.

    Raises:
        GraphtecPathError: when any check fails.
    """
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise GraphtecPathError("A Graphtec file must be selected.")
    if len(relative_path) > MAX_RELATIVE_PATH_LENGTH or "\x00" in relative_path:
        raise GraphtecPathError("The file path is invalid.")

    windows_path = PureWindowsPath(relative_path)
    posix_path = PurePosixPath(relative_path.replace("\\", "/"))
    if (
        posix_path.is_absolute()
        or windows_path.is_absolute()
        or windows_path.drive
        or windows_path.root
    ):
        raise GraphtecPathError("Absolute paths are not accepted.")
    if any(part == ".." for part in posix_path.parts):
        raise GraphtecPathError("Paths containing '..' are not accepted.")

    project_root = Path(test_root).expanduser().resolve()
    if not project_root.is_dir():
        raise GraphtecPathError(f"The test folder does not exist: {project_root}")

    source_directory = graphtec_directory(project_root).resolve()
    candidate = project_root.joinpath(*posix_path.parts).resolve()

    if candidate.parent != source_directory:
        raise GraphtecPathError(
            "The selected file is not inside 03_Data/02_Graphtec."
        )
    if not candidate.is_file():
        raise GraphtecPathError(
            f"The selected Graphtec file was not found: {relative_path}"
        )
    if is_temporary_file(candidate):
        raise GraphtecPathError("Hidden and temporary files are not accepted.")
    return candidate


def relative_to_test_root(test_root: str | Path, file_path: Path) -> str:
    return file_path.relative_to(Path(test_root).expanduser().resolve()).as_posix()
