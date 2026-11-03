"""Comprobación de la versión publicada del generador."""

import json
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

from .version import __version__


VERSION_MANIFEST_PATH = (
    Path(
        r"\\vigvsfil1.global.borgwarner.net\vigproductengineering"
        r"\Documentacion_I+D\R&T\ToolingVersions"
    )
    / "generador-informes.json"
)


@dataclass(frozen=True)
class VersionCheck:
    status: str
    installed_version: str
    current_version: str | None = None
    package: str | None = None
    warning: str | None = None


def check_application_version(
    manifest_path: Path = VERSION_MANIFEST_PATH,
) -> VersionCheck:
    """Compara la versión instalada con el manifiesto compartido."""
    manifest_path = Path(manifest_path)

    try:
        with manifest_path.open(encoding="utf-8") as manifest_file:
            manifest = json.load(manifest_file)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return VersionCheck(
            status="unavailable",
            installed_version=__version__,
            warning=f"Could not read {manifest_path}: {error}",
        )

    if not isinstance(manifest, dict):
        return _invalid_manifest(manifest_path)

    current_version = manifest.get("version")
    package = manifest.get("package")
    if (
        not isinstance(current_version, str)
        or not current_version.strip()
        or not isinstance(package, str)
        or not package.strip()
    ):
        return _invalid_manifest(manifest_path)

    package = package.strip()
    package_path = PureWindowsPath(package)
    if not package_path.is_absolute() or not package_path.anchor.startswith("\\\\"):
        return _invalid_manifest(manifest_path)

    current_version = current_version.strip()
    status = (
        "current"
        if current_version == __version__
        else "outdated"
    )
    return VersionCheck(
        status=status,
        installed_version=__version__,
        current_version=current_version,
        package=package,
    )


def _invalid_manifest(manifest_path: Path) -> VersionCheck:
    return VersionCheck(
        status="unavailable",
        installed_version=__version__,
        warning=(
            f"{manifest_path} must contain a non-empty 'version' and a "
            "UNC 'package' path."
        ),
    )
