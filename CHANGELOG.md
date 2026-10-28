# Changelog

All notable project changes are documented in this file.

## [Unreleased]

### Changed

- The `03_Data` contract now contains the data sources `01_SIMPATI`, `02_Graphtec` and `03_CANoe`. CSV is treated as a file format, not as an independent source.
- `POST /projects/inspect` now reports `data.simpati`, `data.graphtec` and `data.canoe` (plus `data.directory` and `data.simpati_file`).
- Each source now returns `files` as a list of objects with `name`, `relative_path` (relative to the test root, using `/`), `extension` (lower case) and `size` (bytes). Only regular files placed directly in the source folder are listed, sorted case-insensitively. Subfolders, hidden files and Office lock files are excluded, and file content is not read.
- **Analyze SIMPATI** is enabled only when SIMPATI is the selected source and the selected file is the detected SIMPATI acquisition.
- Changing the data source clears the selected file and the previous SIMPATI result and preview. Changing the file clears the previous SIMPATI result. No file is analyzed automatically.

### Added

- `Data source` and `File` selectors in `3. Review project resources`, shown after a project inspection.
- A neutral notice for Graphtec and CANoe indicating that reading those sources will be added in a later increment.
- `canoe_directory()` and `CANOE_FOLDER_NAME` in `paths.py`, and `list_data_source_files()` in `data_sources.py`.
- Frontend selection logic in `services/dataSourceSelection.ts` and the `DataSourceSelector` component.
- Backend tests for the source inventory (missing `03_Data`, missing or empty sources, SIMPATI, Graphtec and CANoe files, subfolder exclusion, ordering, relative paths, unchanged SIMPATI behaviour, no file reads) and frontend tests for the selectors and SIMPATI gating.

### Removed

- The obsolete `02_CSV`, `03_Datalogger` and `04_Graphtec` folders from the active contract, together with `csv_directory()`, `datalogger_directory()`, `CSV_FOLDER_NAME`, `DATALOGGER_FOLDER_NAME` and the `csv` and `datalogger` inspection entries.

## [0.5.0] - 2026-10-08

### Changed

- `test_metadata.json` is now generated externally by the Copilot Studio agent from the climatic test input workbook.
- The report application no longer opens the input Excel, extracts metadata, or regenerates `test_metadata.json`.
- Report generation starts from the existing `04_Report/test_metadata.json`.
- The metadata template no longer contains legacy `setup`, `source`, or `extraction` objects.
- Setup and test-state photographs are now discovered independently from `02_Evidences/*/evidence.json`.
- Test Assembly now uses photos from the `initial` evidence state.
- Test Results preserves the real test sequence defined by each evidence descriptor.
- Generated report typography uses a minimum font size of 12 pt.
- Main generated values use 16 pt with increased spacing between fields.
- The completed climatic PowerPoint keeps only the cover, Tested Parts, TEST A, its generated continuations, and the editable Conclusions slide.
- Remaining slides are renumbered after report cleanup.

### Added

- Chronological PowerPoint slides generated from `02_Evidences/*/evidence.json`.
- Evidence titles, references, notes, and photos in Test Results.
- Automatic continuation slides for evidence states with multiple photos.
- PowerPoint pruning tests and generated typography checks.

### Removed

- The legacy Excel metadata extraction workflow.
- The extraction endpoint, services, models, scripts, and frontend extraction step.
- Legacy setup-image references stored inside `test_metadata.json`.
- Dependency on legacy `setup.images` paths during report generation.
- Unused LEG summaries and explanatory template slides from generated reports.
- TEST B, TEST C, Sample Analysis, Teardown, Additional Information, signatures, and trailing empty slides from climatic reports.

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
