from pydantic import BaseModel, Field

from .common import ApiError


class ReportGenerationResponse(BaseModel):
    """Result of generating a PowerPoint report."""

    success: bool
    test_root: str
    report_path: str | None = None
    report_name: str | None = None
    errors: list[ApiError] = Field(default_factory=list)
