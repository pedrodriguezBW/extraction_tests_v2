# Changelog

All notable project changes are documented in this file.

## [0.4.0] - 2026-10-07

### Added

- Support for the per-test folder contract `01_Inputs`, `02_Evidences`,
  `03_Data` (`01_SIMPATI`, `02_CSV`, `03_Datalogger`, `04_Graphtec`) and
  `04_Report`.
- Validation of the agent-generated `04_Report/test_metadata.json`.
- Dynamic discovery and validation of `02_Evidences/*/evidence.json`
  descriptors, ordered by `sequence`, with resolved photos, invalid
  descriptors and missing photos reported.
- Detection of the SIMPATI, CSV, Datalogger and Graphtec sources.
- `3. Review project resources` step in the desktop interface with the
  metadata status, evidences, photos, data sources and template.
- Tests for paths, metadata, evidences, inspection, generation output and
  the SIMPATI folders.

### Changed

- The inspection endpoint returns the new project contract.
- Report generation reads `04_Report/test_metadata.json`, assembles the
  presentation in `04_Report/_Working` and saves the final PowerPoint
  directly in `04_Report`.
- SIMPATI acquisitions are read from `03_Data/01_SIMPATI`, and saved charts
  are stored in `04_Report/_RenderedAssets`. Saving a chart requires an
  existing `04_Report` folder.
- Report generation is enabled when the inspection is valid and
  `test_metadata.json` exists and is valid.
- `run_pipeline.py` only generates the report from the existing JSON.
- Report file names replace characters that Windows does not allow.
- Updated the application version to `0.4.0`.

### Removed

- Excel metadata extraction: `extract_metadata.py`, the
  `src/report_generator/extractor/` package, its backend model and service,
  the extraction endpoint, and the related frontend types, states, buttons
  and summaries.
- The `openpyxl` requirement, which only the extractor used.
- The previous `99_ReportGenerator` folder hierarchy.

## [0.3.0] - 2026-09-23

### Added

- Added `POST /projects/generate-report` to generate an editable PowerPoint
  through the existing report engine and configured template.
- Added structured report-generation success and error responses.
- Added backend service and endpoint tests with mocked report generation.
- Added the `4. Generate report` step to the desktop interface.
- Added typed frontend API support for report generation.
- Added report name and output path presentation after successful generation.

### Changed

- Enabled PowerPoint generation only after successful metadata extraction.
- Added loading and duplicate-request protection during report generation.
- Updated the application version to `0.3.0`.

## [0.2.1] - 2026-09-23

### Changed

- Translated all user-facing frontend and backend messages into English.
- Kept missing optional resources, including SIMPATI, as neutral states.
- Improved long path display with visual truncation and full-path tooltips.
- Limited the Retry action to backend connection failures.
- Changed the extraction action to `Extract data again` after success.
- Preserved the compact sticky header and the existing visual design.
- Updated application and extractor version information to `0.2.1`.

## [0.2.0] - 2026-09-23

### Added

- FastAPI backend exposing the report generation engine.
- Backend health-check endpoint.
- Test folder structure and file inspection.
- Metadata extraction through the API.
- Desktop interface built with React, TypeScript, and Tauri.
- Native test folder selection.
- Visual presentation of errors, warnings, and optional resources.
- Extracted metadata summary.
- Automated tests for the backend and its endpoints.

### Changed

- Centralized test folder paths and directory names.
- Reused Excel blank-value and empty-row validation.
- Reused DUT content detection and Excel references.
- Unified path input across console scripts.
- Added unit tests for paths, blank values, and DUT content.
- Displayed missing humidity and actuation values as `-`.
- Created native, editable climatic and DUT charts in PowerPoint.
- Removed Excel screenshot export from report generation.
- Added Microsoft PowerPoint axis identifier compatibility.
- Evolved the console scripts into a frontend-API-engine architecture.
- Improved the visual handling of states and warnings.
- Prepared the project for a future web application migration.

## [0.1.0] - 2026-09-18

### Added

- Automatic metadata extraction from the input workbook.
- Read-only XLSM loading without modifying the original file.
- Generation of `test_metadata.json`.
- Workbook traceability through path, size, date, and SHA-256.
- Extraction of general data, samples, equipment, climatic parameters,
  DUT profiles, and events.
- Setup photo inventory.
- Export of charts embedded in Excel.
- SIMPATI acquisition chart processing.
- Automatic generation of an editable PowerPoint from a template.
- Dynamic Tested Parts generation.
- Test Description generation.
- Test Assembly generation with photos and equipment.
- Climatic and DUT Test Inputs generation.
- Paginated climatic and DUT profile tables.
- Profile chart slide.
- Dynamic Test Results chart layout.
- Automatic continuation slides.
- Separation into extraction, PowerPoint, section, and asset modules.
- Centralized template path in `config.py`.
- Separate and complete execution through:
  - `extract_metadata.py`
  - `generate_report.py`
  - `run_pipeline.py`

### Functional principles

- The application represents source data faithfully.
- The application does not interpret or correct business data.
- The application writes exclusively under `99_ReportGenerator`.
- The original Excel workbook is not modified.
- The generated PowerPoint remains editable.
