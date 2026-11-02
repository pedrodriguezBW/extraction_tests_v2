from pydantic import BaseModel, Field

from .common import ApiError


class ReportGenerationRequest(BaseModel):
    """PowerPoint generation request.

    ``selected_rendered_assets`` is the ordered list of images of
    ``04_Report/_RenderedAssets`` to insert in Test Results, identified by
    their relative path as returned by ``POST /projects/rendered-assets``.
    The order is preserved in the PowerPoint. An empty list generates the
    report without result images; it is never replaced by the whole
    inventory. When the field is omitted (``null``) no selection was made
    and every valid image of the inventory is included, which keeps the
    behaviour of older clients and of the console scripts.
    """

    test_root: str = Field(
        min_length=1,
        description="Full path to the test folder.",
    )
    selected_rendered_assets: list[str] | None = Field(
        default=None,
        max_length=500,
        description=(
            "Ordered relative paths of the selected images, e.g. "
            "04_Report/_RenderedAssets/graphtec_chart_01.png. [] means no "
            "images; null means no selection was made (all valid images)."
        ),
    )
    selected_assembly_photos: list[str] | None = Field(
        default=None,
        max_length=500,
        description=(
            "Evidence photos (type initial) for 2. Test Assembly, as "
            "02_Evidences/<folder>/<savedName>. At most 4 are accepted. "
            "[] means no photos; null means the first 4 valid photos."
        ),
    )
    selected_result_photos: list[str] | None = Field(
        default=None,
        max_length=5000,
        description=(
            "Evidence photos (any type except initial) for 4. Test Results, "
            "as 02_Evidences/<folder>/<savedName>. No limit. The automatic "
            "order (evidence sequence, then photo order) is always used. "
            "[] means no photos (evidence slides are kept); null means all."
        ),
    )


class ReportGenerationResponse(BaseModel):
    """Result of generating a PowerPoint report."""

    success: bool
    test_root: str
    report_path: str | None = None
    report_name: str | None = None
    rendered_assets_count: int = 0
    rendered_assets: list[str] = Field(
        default_factory=list,
        description="Relative paths of the images inserted, in slide order.",
    )
    assembly_photos_count: int = 0
    assembly_photos: list[str] = Field(
        default_factory=list,
        description="Evidence photos inserted in Test Assembly, in order.",
    )
    result_photos_count: int = 0
    result_photos: list[str] = Field(
        default_factory=list,
        description="Evidence photos inserted in Test Results, in order.",
    )
    errors: list[ApiError] = Field(default_factory=list)
