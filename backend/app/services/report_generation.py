from pathlib import Path
from zipfile import BadZipFile

from pptx.exc import PackageNotFoundError
from config import POWERPOINT_TEMPLATE_PATH
from src.report_generator import generate_climatic_report

from ..models.common import ApiError
from ..models.report_generation import ReportGenerationResponse


class ReportGenerationError(Exception):
    """Controlled PowerPoint generation error."""

    def __init__(
        self,
        *,
        test_root: Path,
        status_code: int,
        error: ApiError,
    ) -> None:
        super().__init__(error.message)
        self.test_root = test_root
        self.status_code = status_code
        self.error = error

    def to_response(self) -> ReportGenerationResponse:
        return ReportGenerationResponse(
            success=False,
            test_root=str(self.test_root),
            errors=[self.error],
        )


def _build_generation_error(
    test_root: Path,
    error: Exception,
) -> ReportGenerationError:
    if isinstance(error, PermissionError):
        status_code = 403
        code = "report_generation_permission_denied"
    elif isinstance(
        error,
        (
            FileNotFoundError,
            NotADirectoryError,
            ValueError,
            KeyError,
            TypeError,
            IndexError,
            RuntimeError,
            BadZipFile,
            PackageNotFoundError,
        ),
    ):
        status_code = 400
        code = "report_generation_invalid_project"
    else:
        status_code = 500
        code = "report_generation_failed"

    message = str(error).strip()
    if not message:
        message = "The PowerPoint report could not be generated."

    return ReportGenerationError(
        test_root=test_root,
        status_code=status_code,
        error=ApiError(
            code=code,
            message=message,
            exception_type=type(error).__name__,
        ),
    )


def generate_project_report(
    test_root: str | Path,
) -> ReportGenerationResponse:
    """
    Generate the report with the existing PowerPoint engine.

    The engine reads 04_Report/test_metadata.json and saves the
    PowerPoint directly in 04_Report.
    """
    project_root = Path(test_root).expanduser()

    try:
        project_root = project_root.resolve()
        template_path = Path(
            POWERPOINT_TEMPLATE_PATH
        ).expanduser().resolve()
        output_path = Path(
            generate_climatic_report(
                test_root=project_root,
                template_path=template_path,
            )
        ).resolve()
    except Exception as error:
        raise _build_generation_error(project_root, error) from error

    return ReportGenerationResponse(
        success=True,
        test_root=str(project_root),
        report_path=str(output_path),
        report_name=output_path.name,
        errors=[],
    )
