from pydantic import BaseModel, Field


class ProjectInspectionRequest(BaseModel):
    """Path to the test folder to inspect."""

    test_root: str = Field(
        min_length=1,
        description="Full path to the test folder.",
    )


class FileInspectionResult(BaseModel):
    """Inspection result for an expected file."""

    found: bool
    name: str | None = None
    path: str | None = None


class DirectoryInspectionResult(BaseModel):
    """Inspection result for an expected folder."""

    found: bool
    path: str
    file_count: int | None = None


class MetadataInspectionResult(FileInspectionResult):
    """Inspection result for the agent-generated test_metadata.json."""

    valid: bool = False
    error: str | None = None
    errors: list[str] = Field(default_factory=list)
    test_name: str | None = None
    schema_version: str | None = None
    samples_count: int = 0
    equipment_count: int = 0
    climatic_profile_points_count: int = 0
    dut_profile_points_count: int = 0
    test_events_count: int = 0
    setup_images_count: int = 0
    setup_images_found_count: int = 0


class EvidencePhotoResult(BaseModel):
    """Photo referenced by an evidence descriptor."""

    id: str | None = None
    original_name: str | None = None
    saved_name: str
    capture_date: str | None = None
    mime: str | None = None
    size: int | None = None
    path: str
    found: bool


class EvidenceResult(BaseModel):
    """Valid evidence descriptor with resolved photos."""

    id: str | None = None
    type: str | None = None
    title: str | None = None
    reference_type: str | None = None
    reference_value: str | None = None
    notes: str | None = None
    sequence: int | None = None
    schema_version: int | None = None
    folder: str
    declared_folder: str | None = None
    directory: str
    descriptor_path: str
    photos: list[EvidencePhotoResult] = Field(default_factory=list)
    photos_count: int = 0
    photos_found_count: int = 0


class InvalidEvidenceResult(BaseModel):
    """Evidence folder whose descriptor cannot be used."""

    folder: str
    descriptor_path: str
    errors: list[str] = Field(default_factory=list)


class MissingEvidencePhotoResult(BaseModel):
    """Photo referenced by a descriptor but missing on disk."""

    evidence_folder: str
    evidence_title: str | None = None
    saved_name: str
    path: str


class EvidencesInspectionResult(BaseModel):
    """Evidences discovered in 02_Evidences, ordered by sequence."""

    directory: DirectoryInspectionResult
    evidences_count: int = 0
    photos_count: int = 0
    photos_found_count: int = 0
    evidences: list[EvidenceResult] = Field(default_factory=list)
    invalid_evidences: list[InvalidEvidenceResult] = Field(
        default_factory=list
    )
    missing_photos: list[MissingEvidencePhotoResult] = Field(
        default_factory=list
    )


class DataSourceFileResult(BaseModel):
    """Regular file found in a source folder. Its content is not read."""

    name: str
    relative_path: str = Field(
        description="Path relative to the test root, using '/' separators.",
    )
    extension: str = Field(
        description="Lower-case file extension including the dot, or ''.",
    )
    size: int = Field(description="File size in bytes.")


class DataSourceInspectionResult(BaseModel):
    """Optional acquisition source in 03_Data."""

    key: str
    label: str
    found: bool
    available: bool
    path: str
    file_count: int = 0
    files: list[DataSourceFileResult] = Field(default_factory=list)


class SimpatiAcquisitionFileResult(BaseModel):
    """Original SIMPATI export (.x01 to .x99). Its content is not read."""

    index: int = Field(description="Number of the .xNN extension.")
    label: str = Field(description="Acquisition identifier, e.g. x04.")
    name: str
    relative_path: str = Field(
        description="Path relative to the test root, using '/' separators.",
    )
    size: int = Field(description="File size in bytes.")


class DataSourcesInspectionResult(BaseModel):
    """Optional acquisition sources stored in 03_Data.

    SIMPATI, Graphtec and CANoe are data origins; CSV is a file format and
    is not reported as an independent source.
    """

    directory: DirectoryInspectionResult
    simpati: DataSourceInspectionResult
    graphtec: DataSourceInspectionResult
    canoe: DataSourceInspectionResult
    simpati_file: FileInspectionResult = Field(
        description=(
            "First SIMPATI acquisition in numeric order. Kept for "
            "compatibility; use simpati_acquisitions."
        ),
    )
    simpati_acquisitions: list[SimpatiAcquisitionFileResult] = Field(
        default_factory=list,
        description="Every .x01-.x99 acquisition, ordered by its number.",
    )


class ProjectInspectionResponse(BaseModel):
    """Complete result of a test folder inspection."""

    valid: bool
    test_root: str
    inputs_directory: DirectoryInspectionResult
    evidences: EvidencesInspectionResult
    data: DataSourcesInspectionResult
    report_directory: DirectoryInspectionResult
    metadata: MetadataInspectionResult
    powerpoint_template: FileInspectionResult
    errors: list[str]
    warnings: list[str]
