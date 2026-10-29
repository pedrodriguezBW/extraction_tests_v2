"""Shared storage for images saved in ``04_Report/_RenderedAssets``.

``_RenderedAssets`` is the generic repository of rendered images that can be
selected for the PowerPoint. SIMPATI and Graphtec write their charts here,
and images copied into the folder by hand are accepted too. The origin of an
image is kept only as informative metadata (``source``): it never decides
whether the image can be included in the report.

This module implements once:

* folder creation and PNG validation for the chart generators;
* non-overwriting chart names with optional companion files;
* the generic inventory (:func:`list_rendered_assets`);
* safe resolution of one asset from a client-provided relative path
  (:func:`resolve_rendered_asset`) and of an ordered selection
  (:func:`select_rendered_assets`);
* safe deletion (:func:`delete_rendered_asset`).

Which images the PowerPoint includes is decided by the caller, who passes
the validated selection explicitly to the report generator.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Callable, Iterable, Sequence, Union

from PIL import Image, UnidentifiedImageError

from .media import is_temporary_file
from .paths import (
    RENDERED_ASSETS_FOLDER_NAME,
    REPORT_FOLDER_NAME,
    rendered_assets_directory,
    report_directory,
)

MAX_IMAGE_BYTES = 15 * 1024 * 1024
MAX_IMAGE_DIMENSION = 8000
MAX_CHART_NUMBER = 9999
MAX_RELATIVE_PATH_LENGTH = 1024

#: Image extensions accepted in the report (compared case-insensitively).
REPORT_IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg"})

#: Pillow formats that match the accepted extensions.
_REPORT_IMAGE_FORMATS = frozenset({"PNG", "JPEG"})

#: Suffix of the optional metadata file written next to a generated chart.
METADATA_SUFFIX = ".json"

#: ``source`` reported for a compatible image without origin metadata.
MANUAL_SOURCE = "manual"

#: ``source`` reported when metadata exists but does not name the origin.
UNKNOWN_SOURCE = "unknown"

#: Relative folder of the rendered assets, as sent by the client.
RENDERED_ASSETS_RELATIVE_PATH = (
    f"{REPORT_FOLDER_NAME}/{RENDERED_ASSETS_FOLDER_NAME}"
)


class RenderedAssetError(ValueError):
    """Base error for rendered asset operations."""


class RenderedAssetPathError(RenderedAssetError):
    """The relative path is not an acceptable rendered asset path."""


class RenderedAssetNotFoundError(RenderedAssetError):
    """The rendered asset does not exist."""


class RenderedAssetUnsupportedError(RenderedAssetError):
    """The file is not a supported report image."""


@dataclass(frozen=True)
class RenderedAsset:
    """One image of ``_RenderedAssets`` that can be selected for the report."""

    #: File name, for display.
    name: str
    #: Path relative to the test root with ``/`` separators. It identifies
    #: the asset in every request (open, delete, report generation).
    relative_path: str
    #: Lower-case extension including the dot.
    extension: str
    #: File size in bytes.
    size: int
    #: Informative origin: ``simpati``, ``graphtec``, ``manual``, ...
    source: str
    #: Absolute path on the server. Never sent to the client as an input.
    path: Path
    #: Name of the companion metadata file, when it exists.
    metadata_name: str | None = None


@dataclass(frozen=True)
class RenderedAssetWarning:
    """A file of ``_RenderedAssets`` that is not a selectable image."""

    name: str
    code: str
    message: str


@dataclass(frozen=True)
class RenderedAssetInventory:
    """Selectable images and structured warnings, in a stable order."""

    directory: Path
    exists: bool
    assets: list[RenderedAsset] = field(default_factory=list)
    warnings: list[RenderedAssetWarning] = field(default_factory=list)

    @property
    def relative_paths(self) -> list[str]:
        return [asset.relative_path for asset in self.assets]


def prepare_rendered_assets_directory(test_root: Union[str, Path]) -> Path:
    """
    Return ``04_Report/_RenderedAssets``, creating it when needed.

    The report folder itself must already exist because it holds the
    agent-generated ``test_metadata.json``.
    """
    test_root = Path(test_root).expanduser().resolve()
    output_directory = report_directory(test_root)

    if not output_directory.is_dir():
        raise FileNotFoundError(
            "The report folder was not found:\n"
            f"{output_directory}"
        )

    assets_directory = rendered_assets_directory(test_root)

    if assets_directory.exists() and not assets_directory.is_dir():
        raise NotADirectoryError(
            "The rendered assets path is not a directory:\n"
            f"{assets_directory}"
        )

    assets_directory.mkdir(exist_ok=True)

    return assets_directory


def validate_png_bytes(image_bytes: bytes) -> bytes:
    """Check that ``image_bytes`` is a non-empty PNG within the limits."""
    if not image_bytes:
        raise ValueError("The PNG image is empty.")

    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ValueError("The PNG image exceeds the 15 MB limit.")

    with Image.open(BytesIO(image_bytes)) as image:
        if image.format != "PNG":
            raise ValueError("The chart must be a PNG image.")
        if (
            image.width > MAX_IMAGE_DIMENSION
            or image.height > MAX_IMAGE_DIMENSION
        ):
            raise ValueError(
                "The PNG image dimensions exceed the allowed limit."
            )
        image.verify()

    return image_bytes


def chart_file_name(prefix: str, number: int) -> str:
    return f"{prefix}_{number:02d}.png"


def build_next_chart_path(
    output_directory: Path,
    prefix: str,
    companion_suffixes: Iterable[str] = (),
) -> Path:
    """Return the first ``<prefix>_NN.png`` path that is free.

    A number is free when neither the PNG nor any companion file with the
    given suffixes (for example ``.json``) exists.
    """
    output_directory.mkdir(parents=True, exist_ok=True)
    suffixes = tuple(companion_suffixes)

    for chart_number in range(1, MAX_CHART_NUMBER + 1):
        candidate = output_directory / chart_file_name(prefix, chart_number)
        if candidate.exists():
            continue
        if any(candidate.with_suffix(suffix).exists() for suffix in suffixes):
            continue
        return candidate

    raise FileExistsError("No free chart name is available.")


def write_new_chart(
    output_directory: Path,
    prefix: str,
    image_bytes: bytes,
    companions: Callable[[Path], Iterable[tuple[Path, bytes]]] | None = None,
    companion_suffixes: Iterable[str] = (),
) -> Path:
    """Write a PNG under a new generated name without overwriting anything.

    Files are created in exclusive mode, so an existing chart is never
    replaced, even if two saves run at the same time. ``companions`` may
    return extra files (for example a metadata JSON) written next to the
    image; if one of them cannot be written the image is removed again.
    """
    validate_png_bytes(image_bytes)
    suffixes = tuple(companion_suffixes)

    for _attempt in range(MAX_CHART_NUMBER):
        chart_path = build_next_chart_path(output_directory, prefix, suffixes)
        try:
            with open(chart_path, "xb") as handle:
                handle.write(image_bytes)
        except FileExistsError:
            continue

        written: list[Path] = []
        try:
            for companion_path, content in (companions(chart_path) if companions else []):
                with open(companion_path, "xb") as handle:
                    handle.write(content)
                written.append(companion_path)
        except Exception:
            for path in written:
                path.unlink(missing_ok=True)
            chart_path.unlink(missing_ok=True)
            raise
        return chart_path

    raise FileExistsError("No free chart name is available.")


def _natural_sort_key(name: str) -> tuple:
    """Natural order: ``chart_2.png`` before ``chart_10.png``."""
    parts = re.split(r"([0-9]+)", name.casefold())
    return tuple(int(part) if part.isdigit() else part for part in parts)


def asset_sort_key(name: str) -> tuple:
    """Stable, deterministic order of the inventory (natural, then exact)."""
    return (_natural_sort_key(name), name)


def is_report_image_name(name: str) -> bool:
    """Return whether the extension is accepted, ignoring case."""
    return Path(name).suffix.casefold() in REPORT_IMAGE_EXTENSIONS


def validate_report_image_file(file_path: Path) -> None:
    """Check that ``file_path`` is a readable PNG or JPEG image.

    Raises:
        RenderedAssetUnsupportedError: when the extension or the content is
            not a supported image.
    """
    if not is_report_image_name(file_path.name):
        raise RenderedAssetUnsupportedError(
            f"The file is not a supported report image (PNG, JPG or JPEG): "
            f"{file_path.name}"
        )
    try:
        with Image.open(file_path) as image:
            image_format = image.format
            image.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as error:
        raise RenderedAssetUnsupportedError(
            f"The file is not a valid image: {file_path.name}"
        ) from error
    if image_format not in _REPORT_IMAGE_FORMATS:
        raise RenderedAssetUnsupportedError(
            f"The image format {image_format or 'unknown'} is not supported "
            f"in the report: {file_path.name}"
        )


def metadata_path_for(image_path: Path) -> Path:
    """Return the companion metadata path of an image (``<stem>.json``)."""
    return image_path.with_suffix(METADATA_SUFFIX)


def read_asset_metadata(image_path: Path) -> dict:
    """Read the companion metadata of an image; ``{}`` when absent/invalid."""
    metadata_path = metadata_path_for(image_path)
    try:
        content = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return content if isinstance(content, dict) else {}


def _metadata_names(directory: Path) -> set[str]:
    """Lower-case stems of the ``.json`` files in the folder."""
    return {
        path.stem.casefold()
        for path in directory.iterdir()
        if path.is_file() and path.suffix.casefold() == METADATA_SUFFIX
    }


def _asset_source(image_path: Path, metadata: dict) -> str:
    """Informative origin of an image.

    The companion metadata wins. Without metadata the image is reported as
    ``manual``: a compatible image placed in the folder by hand. The name is
    never used to decide whether the image can be included.
    """
    if metadata:
        source = metadata.get("source")
        if isinstance(source, str) and source.strip():
            return source.strip().casefold()
        return UNKNOWN_SOURCE
    return MANUAL_SOURCE


def relative_asset_path(name: str) -> str:
    """Return ``04_Report/_RenderedAssets/<name>``."""
    return f"{RENDERED_ASSETS_RELATIVE_PATH}/{name}"


def list_rendered_assets(test_root: Union[str, Path]) -> RenderedAssetInventory:
    """List the selectable images of ``04_Report/_RenderedAssets``.

    Only regular PNG, JPG and JPEG files placed directly in the folder are
    returned, in a stable natural order, after checking that their content
    is a valid image. Subfolders, hidden and temporary files are ignored.
    Companion ``.json`` metadata files are read for the ``source`` but are
    not listed. Any other file, or an image file with invalid content,
    produces a structured warning instead of blocking the listing.
    """
    project_root = Path(test_root).expanduser().resolve()
    directory = rendered_assets_directory(project_root)
    if not directory.is_dir():
        return RenderedAssetInventory(directory=directory, exists=False)

    directory = directory.resolve()
    metadata_stems = _metadata_names(directory)
    assets: list[RenderedAsset] = []
    warnings: list[RenderedAssetWarning] = []

    for file_path in sorted(directory.iterdir(), key=lambda p: asset_sort_key(p.name)):
        name = file_path.name
        if is_temporary_file(file_path):
            continue
        if file_path.is_dir():
            continue
        if not file_path.is_file():
            continue
        if file_path.resolve().parent != directory:
            # A link to a file outside the folder is never listed.
            continue
        suffix = file_path.suffix.casefold()
        if suffix == METADATA_SUFFIX:
            # Companion metadata of a chart: never an image of the report.
            continue
        if suffix not in REPORT_IMAGE_EXTENSIONS:
            warnings.append(
                RenderedAssetWarning(
                    name=name,
                    code="unsupported_file",
                    message=(
                        f"{name} is not a PNG, JPG or JPEG image and is "
                        "not available for the report."
                    ),
                )
            )
            continue
        try:
            validate_report_image_file(file_path)
        except RenderedAssetUnsupportedError as error:
            warnings.append(
                RenderedAssetWarning(
                    name=name,
                    code="invalid_image",
                    message=str(error),
                )
            )
            continue

        metadata = read_asset_metadata(file_path)
        has_metadata = file_path.stem.casefold() in metadata_stems
        assets.append(
            RenderedAsset(
                name=name,
                relative_path=relative_asset_path(name),
                extension=suffix,
                size=file_path.stat().st_size,
                source=_asset_source(file_path, metadata if has_metadata else {}),
                path=file_path,
                metadata_name=(
                    metadata_path_for(file_path).name if has_metadata else None
                ),
            )
        )

    return RenderedAssetInventory(
        directory=directory,
        exists=True,
        assets=assets,
        warnings=warnings,
    )


def normalize_asset_relative_path(relative_path: str) -> PurePosixPath:
    """Validate the shape of a client path and return it in POSIX form.

    Rejects empty, oversized, absolute paths (POSIX or Windows, including
    drive letters) and any ``..`` component. Does not touch the disk.
    """
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise RenderedAssetPathError("A rendered asset path is required.")
    if len(relative_path) > MAX_RELATIVE_PATH_LENGTH or "\x00" in relative_path:
        raise RenderedAssetPathError("The rendered asset path is invalid.")

    windows_path = PureWindowsPath(relative_path)
    posix_path = PurePosixPath(relative_path.replace("\\", "/"))
    if (
        posix_path.is_absolute()
        or windows_path.is_absolute()
        or windows_path.drive
        or windows_path.root
    ):
        raise RenderedAssetPathError("Absolute paths are not accepted.")
    raw_parts = relative_path.replace("\\", "/").split("/")
    if any(part in {"..", "."} for part in raw_parts):
        raise RenderedAssetPathError(
            "Paths containing '.' or '..' components are not accepted."
        )
    if any(not part.strip() for part in raw_parts):
        raise RenderedAssetPathError("The rendered asset path is invalid.")
    return posix_path


def resolve_rendered_asset(
    test_root: Union[str, Path],
    relative_path: str,
) -> Path:
    """Return the absolute path of one selectable image.

    Checks, in order: the test root exists; ``relative_path`` is relative
    and free of ``..``; the rebuilt path, with links resolved, is a direct
    child of ``04_Report/_RenderedAssets``; it is a regular, non-hidden
    file; its extension is accepted; its content is a valid image.

    Raises:
        RenderedAssetPathError: for invalid or external paths.
        RenderedAssetNotFoundError: when the asset does not exist.
        RenderedAssetUnsupportedError: when it is not a supported image.
    """
    project_root = Path(test_root).expanduser().resolve()
    if not project_root.is_dir():
        raise RenderedAssetPathError(
            f"The test folder does not exist: {project_root}"
        )

    posix_path = normalize_asset_relative_path(relative_path)
    assets_directory = rendered_assets_directory(project_root)
    if not assets_directory.is_dir():
        raise RenderedAssetNotFoundError(
            "The rendered assets folder does not exist: "
            f"{RENDERED_ASSETS_RELATIVE_PATH}"
        )
    assets_directory = assets_directory.resolve()

    candidate = project_root.joinpath(*posix_path.parts)
    resolved = candidate.resolve()
    if resolved.parent != assets_directory:
        raise RenderedAssetPathError(
            "The rendered asset is not inside "
            f"{RENDERED_ASSETS_RELATIVE_PATH}: {relative_path}"
        )
    if is_temporary_file(resolved):
        raise RenderedAssetPathError(
            "Hidden and temporary files are not accepted."
        )
    if not resolved.exists():
        raise RenderedAssetNotFoundError(
            f"The rendered asset was not found: {relative_path}"
        )
    if not resolved.is_file():
        raise RenderedAssetPathError(
            f"The rendered asset is not a regular file: {relative_path}"
        )
    validate_report_image_file(resolved)
    return resolved


def select_rendered_assets(
    test_root: Union[str, Path],
    relative_paths: Sequence[str],
) -> list[Path]:
    """Validate an ordered selection and return its absolute paths.

    The order of ``relative_paths`` is preserved. Duplicates (after path
    normalization, compared case-insensitively) are rejected, and every
    entry goes through :func:`resolve_rendered_asset`. An empty selection
    returns an empty list: the caller must not replace it with the whole
    inventory.
    """
    if isinstance(relative_paths, (str, bytes)):
        raise RenderedAssetPathError(
            "The selection must be a list of rendered asset paths."
        )

    selected: list[Path] = []
    seen: set[str] = set()
    for relative_path in relative_paths:
        if not isinstance(relative_path, str):
            raise RenderedAssetPathError(
                "Every selected rendered asset must be a relative path."
            )
        key = normalize_asset_relative_path(relative_path).as_posix().casefold()
        if key in seen:
            raise RenderedAssetPathError(
                f"The rendered asset is selected more than once: {relative_path}"
            )
        seen.add(key)
        selected.append(resolve_rendered_asset(test_root, relative_path))
    return selected


def delete_rendered_asset(
    test_root: Union[str, Path],
    relative_path: str,
) -> Path:
    """Delete one selectable image and its companion metadata file.

    The path goes through :func:`resolve_rendered_asset` first, so only
    supported images directly inside ``_RenderedAssets`` can be deleted.
    Returns the path of the deleted image.
    """
    image_path = resolve_rendered_asset(test_root, relative_path)
    metadata_path = metadata_path_for(image_path)
    image_path.unlink()
    if metadata_path.is_file() and metadata_path.parent == image_path.parent:
        metadata_path.unlink()
    return image_path


def find_charts_with_prefix(test_root: Union[str, Path], prefix: str) -> list[Path]:
    """List ``<prefix>_NN.png`` images in ``_RenderedAssets`` in number order.

    Kept for the chart generators that need to know their own files (for
    example to avoid collisions). It is not used to decide what the report
    includes.
    """
    assets_directory = rendered_assets_directory(Path(test_root))
    if not assets_directory.is_dir():
        return []

    pattern = re.compile(rf"^{re.escape(prefix)}_(\d+)\.png$", re.IGNORECASE)
    charts = []
    for file_path in assets_directory.iterdir():
        match = pattern.match(file_path.name)
        if match and file_path.is_file() and file_path.stat().st_size > 0:
            charts.append((int(match.group(1)), file_path))
    return [path for _, path in sorted(charts)]
