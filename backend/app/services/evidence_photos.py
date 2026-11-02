"""Safe access to the evidence photos of ``02_Evidences``.

Only photos declared by a valid ``evidence.json`` can be served. The path
received from the client is validated and rebuilt on the server, so it can
never point outside ``02_Evidences``.
"""

from __future__ import annotations

from pathlib import Path

from src.report_generator.evidence_photos import (
    EvidencePhotoNotFoundError,
    EvidencePhotoPathError,
    EvidencePhotoUnsupportedError,
    resolve_evidence_photo,
)
from src.report_generator.evidences import discover_evidences

from ..models.common import ApiError
from ..models.project import EvidencePhotoErrorResponse

#: Media types served for the evidence photo formats.
EVIDENCE_PHOTO_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}


class EvidencePhotoServiceError(Exception):
    """Controlled error converted into a structured API response."""

    def __init__(
        self,
        *,
        test_root: Path | str,
        status_code: int,
        error: ApiError,
    ) -> None:
        super().__init__(error.message)
        self.test_root = str(test_root)
        self.status_code = status_code
        self.error = error

    def to_response(self) -> EvidencePhotoErrorResponse:
        return EvidencePhotoErrorResponse(
            success=False,
            test_root=self.test_root,
            errors=[self.error],
        )


def _service_error(
    test_root: Path | str,
    error: Exception,
) -> EvidencePhotoServiceError:
    if isinstance(error, EvidencePhotoNotFoundError):
        status, code = 404, "evidence_photo_not_found"
    elif isinstance(error, EvidencePhotoUnsupportedError):
        status, code = 415, "evidence_photo_unsupported"
    elif isinstance(error, EvidencePhotoPathError):
        status, code = 400, "evidence_photo_invalid_path"
    elif isinstance(error, PermissionError):
        status, code = 403, "evidence_photo_permission_denied"
    elif isinstance(error, (FileNotFoundError, NotADirectoryError, ValueError)):
        status, code = 400, "evidence_photo_invalid_request"
    else:
        status, code = 500, "evidence_photo_failed"
    message = str(error).strip() or "The evidence photo could not be opened."
    return EvidencePhotoServiceError(
        test_root=test_root,
        status_code=status,
        error=ApiError(
            code=code,
            message=message,
            exception_type=type(error).__name__,
        ),
    )


def resolve_project_evidence_photo(
    test_root: str | Path,
    relative_path: str,
) -> Path:
    """Resolve one evidence photo for viewing. Rejects anything else."""
    try:
        project_root = Path(test_root).expanduser().resolve()
        if not project_root.is_dir():
            raise EvidencePhotoPathError(
                f"The test folder does not exist: {project_root}"
            )
        discovery = discover_evidences(project_root)
        return resolve_evidence_photo(discovery, relative_path).path.resolve()
    except Exception as error:
        raise _service_error(test_root, error) from error


def evidence_photo_media_type(image_path: Path) -> str:
    return EVIDENCE_PHOTO_MEDIA_TYPES.get(
        image_path.suffix.casefold(),
        "application/octet-stream",
    )
