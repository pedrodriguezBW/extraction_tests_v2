from pathlib import Path

from config import POWERPOINT_TEMPLATE_PATH
from src.report_generator.simpati import (
    SimpatiAcquisitionFile,
    discover_simpati_acquisitions,
)
from src.report_generator.data_sources import (
    DataSource,
    discover_data_sources,
    list_source_files,
)
from src.report_generator.evidences import (
    EvidenceDiscovery,
    discover_evidences,
)
from src.report_generator.metadata import (
    MetadataError,
    read_metadata_file,
    resolve_setup_images,
    summarize_metadata,
    validate_metadata,
)
from src.report_generator.paths import (
    DATA_FOLDER_NAME,
    EVIDENCES_FOLDER_NAME,
    INPUTS_FOLDER_NAME,
    METADATA_FILENAME,
    REPORT_FOLDER_NAME,
    data_directory,
    inputs_directory,
    metadata_path,
    report_directory,
)

from ..models.project import (
    DataSourceFileResult,
    DataSourceInspectionResult,
    DataSourcesInspectionResult,
    DirectoryInspectionResult,
    EvidencePhotoResult,
    EvidenceResult,
    EvidencesInspectionResult,
    FileInspectionResult,
    InvalidEvidenceResult,
    MetadataInspectionResult,
    MissingEvidencePhotoResult,
    ProjectInspectionResponse,
    SimpatiAcquisitionFileResult,
)


def _directory_result(
    directory: Path,
    *,
    count_files: bool = False,
) -> DirectoryInspectionResult:
    found = directory.is_dir()
    return DirectoryInspectionResult(
        found=found,
        path=str(directory),
        file_count=(
            len(list_source_files(directory))
            if count_files and found
            else None
        ),
    )


def _file_result(file_path: Path | None) -> FileInspectionResult:
    if file_path is None:
        return FileInspectionResult(found=False)
    return FileInspectionResult(
        found=True,
        name=file_path.name,
        path=str(file_path),
    )


def _inspect_metadata(
    project_root: Path,
    report_is_valid: bool,
    errors: list[str],
    warnings: list[str],
) -> MetadataInspectionResult:
    metadata_file = metadata_path(project_root)
    found = metadata_file.is_file()
    result = MetadataInspectionResult(
        found=found,
        valid=False,
        name=metadata_file.name if found else None,
        path=str(metadata_file),
    )

    if not report_is_valid:
        return result

    if not found:
        message = (
            f"The {METADATA_FILENAME} file was not found: "
            f"{metadata_file}"
        )
        errors.append(message)
        result.error = message
        result.errors = [message]
        return result

    try:
        metadata = read_metadata_file(metadata_file)
    except (MetadataError, FileNotFoundError) as error:
        message = str(error)
        errors.append(message)
        result.error = message
        result.errors = [message]
        return result

    structure_errors = validate_metadata(metadata)
    if structure_errors:
        errors.extend(
            f"{METADATA_FILENAME}: {message}"
            for message in structure_errors
        )
        result.error = structure_errors[0]
        result.errors = structure_errors
        return result

    summary = summarize_metadata(metadata)
    found_images, missing_images = resolve_setup_images(
        metadata,
        project_root,
    )

    if missing_images:
        warnings.append(
            f"{len(missing_images)} of "
            f"{len(found_images) + len(missing_images)} setup photo(s) "
            f"referenced in {METADATA_FILENAME} were not found. "
            "Test Assembly will be generated without them."
        )

    result.valid = True
    result.test_name = summary.test_name
    result.schema_version = summary.schema_version
    result.samples_count = summary.samples_count
    result.equipment_count = summary.equipment_count
    result.climatic_profile_points_count = (
        summary.climatic_profile_points_count
    )
    result.dut_profile_points_count = summary.dut_profile_points_count
    result.test_events_count = summary.test_events_count
    result.setup_images_count = len(found_images) + len(missing_images)
    result.setup_images_found_count = len(found_images)
    return result


def _evidences_result(
    discovery: EvidenceDiscovery,
) -> EvidencesInspectionResult:
    evidences = [
        EvidenceResult(
            id=evidence.id,
            type=evidence.type,
            title=evidence.title,
            reference_type=evidence.reference_type,
            reference_value=evidence.reference_value,
            notes=evidence.notes,
            sequence=evidence.sequence,
            schema_version=evidence.schema_version,
            folder=evidence.folder_name,
            declared_folder=evidence.declared_folder,
            directory=str(evidence.directory),
            descriptor_path=str(evidence.descriptor_path),
            photos=[
                EvidencePhotoResult(
                    id=photo.id,
                    original_name=photo.original_name,
                    saved_name=photo.saved_name,
                    capture_date=photo.capture_date,
                    mime=photo.mime,
                    size=photo.size,
                    path=str(photo.path),
                    found=photo.found,
                )
                for photo in evidence.photos
            ],
            photos_count=len(evidence.photos),
            photos_found_count=len(evidence.found_photos),
        )
        for evidence in discovery.evidences
    ]

    return EvidencesInspectionResult(
        directory=DirectoryInspectionResult(
            found=discovery.found,
            path=str(discovery.directory),
            file_count=None,
        ),
        evidences_count=len(evidences),
        photos_count=discovery.photos_count,
        photos_found_count=discovery.found_photos_count,
        evidences=evidences,
        invalid_evidences=[
            InvalidEvidenceResult(
                folder=invalid.folder_name,
                descriptor_path=str(invalid.descriptor_path),
                errors=invalid.errors,
            )
            for invalid in discovery.invalid_evidences
        ],
        missing_photos=[
            MissingEvidencePhotoResult(
                evidence_folder=missing.evidence_folder,
                evidence_title=missing.evidence_title,
                saved_name=missing.saved_name,
                path=str(missing.path),
            )
            for missing in discovery.missing_photos
        ],
    )


def _source_result(source: DataSource) -> DataSourceInspectionResult:
    return DataSourceInspectionResult(
        key=source.key,
        label=source.label,
        found=source.found,
        available=source.available,
        path=str(source.directory),
        file_count=len(source.files),
        files=[
            DataSourceFileResult(
                name=source_file.name,
                relative_path=source_file.relative_path,
                extension=source_file.extension,
                size=source_file.size,
            )
            for source_file in source.files
        ],
    )


def _simpati_acquisition_result(
    acquisition: SimpatiAcquisitionFile,
) -> SimpatiAcquisitionFileResult:
    return SimpatiAcquisitionFileResult(
        index=acquisition.index,
        label=acquisition.label,
        name=acquisition.name,
        relative_path=acquisition.relative_path,
        size=acquisition.size,
    )


def inspect_project(
    test_root: str | Path,
) -> ProjectInspectionResponse:
    """
    Inspect a test folder without modifying it.

    The inspection validates the agent-generated metadata, discovers
    the evidences and the optional acquisition sources (SIMPATI,
    Graphtec and CANoe, with the inventory of their files), and checks
    the PowerPoint template. Source files are listed but never read. It does not create folders, generate metadata,
    open Excel workbooks, or modify files.

    Only the report folder, a valid test_metadata.json and the template
    are required to generate the report. Missing inputs, evidences or
    data folders are reported as warnings.
    """
    project_root = Path(test_root).expanduser().resolve()

    errors: list[str] = []
    warnings: list[str] = []

    # ==========================================================
    # TEST ROOT
    # ==========================================================
    if not project_root.exists():
        errors.append(
            f"The test folder does not exist: {project_root}"
        )
    elif not project_root.is_dir():
        errors.append(
            f"The specified path is not a folder: {project_root}"
        )

    root_is_valid = project_root.is_dir()

    # ==========================================================
    # 01_INPUTS (informative)
    # ==========================================================
    inputs_path = inputs_directory(project_root)
    if root_is_valid and not inputs_path.is_dir():
        warnings.append(
            f"The {INPUTS_FOLDER_NAME} folder was not found: "
            f"{inputs_path}"
        )

    # ==========================================================
    # 02_EVIDENCES
    # ==========================================================
    discovery = discover_evidences(project_root)

    if root_is_valid:
        if not discovery.found:
            warnings.append(
                f"The {EVIDENCES_FOLDER_NAME} folder was not found: "
                f"{discovery.directory}"
            )
        for invalid in discovery.invalid_evidences:
            warnings.append(
                f"Invalid evidence descriptor in '{invalid.folder_name}': "
                + " ".join(invalid.errors)
            )
        warnings.extend(discovery.warnings)

    # ==========================================================
    # 03_DATA (optional sources)
    # ==========================================================
    data_path = data_directory(project_root)
    sources = discover_data_sources(project_root)
    simpati_acquisitions: list[SimpatiAcquisitionFile] = []

    if root_is_valid:
        if not data_path.is_dir():
            warnings.append(
                f"The {DATA_FOLDER_NAME} folder was not found: "
                f"{data_path}"
            )

        if sources["simpati"].found:
            try:
                simpati_acquisitions = discover_simpati_acquisitions(
                    project_root
                )
            except (FileNotFoundError, NotADirectoryError, OSError) as error:
                warnings.append(str(error))
            else:
                if not simpati_acquisitions:
                    warnings.append(
                        "No SIMPATI acquisition (.x01 to .x99) was found in "
                        f"{sources['simpati'].directory}."
                    )

    # ==========================================================
    # 04_REPORT AND METADATA
    # ==========================================================
    report_path = report_directory(project_root)
    report_is_valid = report_path.is_dir()

    if root_is_valid and not report_path.exists():
        errors.append(
            f"The {REPORT_FOLDER_NAME} folder was not found: "
            f"{report_path}. It must contain the agent-generated "
            f"{METADATA_FILENAME}."
        )
    elif report_path.exists() and not report_is_valid:
        errors.append(
            f"The {REPORT_FOLDER_NAME} path exists but is not a "
            f"folder: {report_path}"
        )

    metadata_result = _inspect_metadata(
        project_root,
        root_is_valid and report_is_valid,
        errors,
        warnings,
    )

    # ==========================================================
    # POWERPOINT TEMPLATE
    # ==========================================================
    template_path = Path(
        POWERPOINT_TEMPLATE_PATH
    ).expanduser()

    if not template_path.is_file():
        errors.append(
            "The configured PowerPoint template was not found: "
            f"{template_path}"
        )
    elif template_path.suffix.lower() != ".pptx":
        errors.append(
            "The configured template is not a .pptx file: "
            f"{template_path}"
        )

    return ProjectInspectionResponse(
        valid=not errors,
        test_root=str(project_root),
        inputs_directory=_directory_result(
            inputs_path,
            count_files=True,
        ),
        evidences=_evidences_result(discovery),
        data=DataSourcesInspectionResult(
            directory=_directory_result(data_path),
            simpati=_source_result(sources["simpati"]),
            graphtec=_source_result(sources["graphtec"]),
            canoe=_source_result(sources["canoe"]),
            simpati_file=_file_result(
                simpati_acquisitions[0].path if simpati_acquisitions else None
            ),
            simpati_acquisitions=[
                _simpati_acquisition_result(acquisition)
                for acquisition in simpati_acquisitions
            ],
        ),
        report_directory=_directory_result(report_path),
        metadata=metadata_result,
        powerpoint_template=FileInspectionResult(
            found=template_path.is_file(),
            name=(
                template_path.name
                if template_path.is_file()
                else None
            ),
            path=(
                str(template_path.resolve())
                if template_path.is_file()
                else str(template_path)
            ),
        ),
        errors=errors,
        warnings=warnings,
    )
