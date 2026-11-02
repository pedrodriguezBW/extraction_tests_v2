# Changelog

All notable project changes are documented in this file.

## [Unreleased]

### Changed

- Evidence photos: the user chooses which photos of `02_Evidences` go into the report, in two clearly separated zones. **2. Test Assembly** receives the photos of the `initial` evidences (at most 4); **4. Test Results** receives the photos of every other evidence (no limit). Both sections place **two photos per slide**: Test Assembly puts photos 3 and 4 on a `2. Test Assembly (cont.)` slide right after the main one, and Test Results creates `<title> (cont.)` slides per evidence. An evidence without selected photos keeps its slide (title, reference and notes). The order is always automatic (evidence sequence, then photo order).
- Fixed: Test Results grouped evidence photos by four but only drew the first two of each group, so photos 3 and 4 of every group were lost.
- `POST /projects/inspect` adds `report_section` per evidence, `relative_path` and `selectable` per photo, and `assembly_max_photos` / `photos_per_slide`.
- `POST /projects/generate-report` accepts `selected_assembly_photos` and `selected_result_photos` (`02_Evidences/<folder>/<savedName>`), validated before generating (limit of 4 in Assembly, photos of the other zone, duplicates, invalid, missing or unsupported files are structured errors); `null` keeps the previous behaviour (first 4 initial photos, every other photo). The response adds `assembly_photos(_count)` and `result_photos(_count)`.

- Report charts (`_RenderedAssets`): every chart saved by the application (SIMPATI viewer, SIMPATI console tool and Graphtec) is exported as 1800 × 1125 px (1.6:1), designed for the width of one Test Results column (≈14.4 cm). Larger title (13 pt), axis labels (12 pt), tick values and legend (11 pt), thicker lines (1.8 pt), minimal margins, complete titles and legends, non-overlapping X labels (SIMPATI dates on two lines) and full values on narrow Y ranges. Shared settings in `src/report_generator/chart_export.py` and `frontend/src/services/chartExport.ts`. Evidence photos and the native Test Inputs charts are unchanged.
- Test Results: chart size and position are computed from the real template (content placeholder, subtitle and footer/logo) instead of fixed dimensions. Up to two charts per slide in two columns, each as large as possible, centered and undistorted; a single chart uses the full useful width; more than two charts create continuation slides.

- Chart viewer: the **Start** and **End** sliders below the chart are removed. The axes are adjusted by dragging directly on the plot: a horizontal selection narrows the time interval, a vertical selection sets the value range and a diagonal (rectangular) selection adjusts both axes. The value axis is no longer auto-fitted to the visible time interval: it shows the full range of the active channels until the user zooms it, exactly like the time axis. **Reset view** and a double-click on the chart restore the full view. **Save current chart** saves exactly the visible view (time interval, value range, active channels, title and legend) without recalculating the limits. The zoom logic lives in the shared module `frontend/src/services/chartZoom.ts`; series are clipped to the plot area and the value labels gain decimals only when a narrow range is zoomed.

- SIMPATI: the `.x03`-specific extractor is replaced by a generic parser (`src/report_generator/simpati/`). Every original export `.x01`-`.x99` of `03_Data/01_SIMPATI` is discovered (gaps allowed, numeric order) and analyzed independently. The encoding is accepted only when the content has a valid SIMPATI structure (header, units row, timestamped records), so it no longer depends on `A:Temp canast`; headers, units and channels are built from the file content and every channel is kept. Thermal channels are recognized through extendable alias profiles (chamber temperature and setpoint, supply and return air, basket, hot and cold chamber, specimen).
- SIMPATI: fixed a column shift of the previous parser, which named the empty timestamp header as a channel and assigned each channel the values of the next column.
- `POST /projects/simpati/inspect` accepts an optional `relative_path` and returns `acquisitions` (index, file, encoding, records, interval, channels, thermal channels, status and error of every acquisition) with the counters `found_count`, `processed_count`, `ready_count`, `without_thermal_count` and `incompatible_count`, plus the preview of the selected acquisition. Finding several acquisitions is no longer an error and an incompatible file never invalidates the others.
- `POST /projects/simpati/save-chart` requires the source acquisition (`relative_path`) and saves `chart_simpati_xNN_MM.png`; its JSON records `source_file`, `source_relative_path`, `acquisition_index` and `acquisition_label`. Charts of different acquisitions never collide and keep their order in Report images and in the PowerPoint, whose subtitle names the source acquisition (for example `SIMPATI acquisition x01 | SIMPATI acquisition x04`).
- `POST /projects/inspect` adds `data.simpati_acquisitions`; `data.simpati_file` now points to the first acquisition and is kept for compatibility.
- Frontend: **Analyze SIMPATI** accepts any detected `.xNN` acquisition and shows the list of acquisitions (`SimpatiAcquisitions.tsx`) with **Open** to load any of them in the existing chart editor; the editor styles channels by thermal role and draws the source acquisition in the chart title.

- `04_Report/_RenderedAssets` is now the generic repository of report images. Every PNG, JPG or JPEG placed directly in the folder (SIMPATI chart, Graphtec chart, manual copy or a future source) can be selected for the PowerPoint; the origin is kept only as informative metadata (`source`) and never decides whether an image is valid.
- `POST /projects/generate-report` accepts `selected_rendered_assets`, the ordered list of relative paths to insert in Test Results. The PowerPoint includes exactly those images in that order; an empty list generates the report without result images and is never replaced by the inventory. When the field is omitted every valid image is included (console scripts). The response reports `rendered_assets_count` and `rendered_assets`.
- The PowerPoint engine no longer scans `_RenderedAssets` nor filters by the `simpati_acquisition` name: `populate_test_results` receives `result_image_paths` explicitly and `generate_climatic_report` receives `selected_rendered_assets`. `find_test_result_charts` was removed.
- `POST /projects/simpati/save-chart` and `POST /projects/graphtec/save-chart` now return the refreshed generic inventory (`assets`, `assets_count`, `warnings`) and the `relative_path` of the saved image. SIMPATI charts are saved with a JSON metadata file (`source: simpati`) like Graphtec charts.
- The frontend replaces the SIMPATI-only saved chart list with a single **Report images** section (`RenderedAssets.tsx`, `services/renderedAssetSelection.ts`): one row per image with an accessible checkbox (checked by default), thumbnail, name, source, size, state, **Open image** and **Delete**, plus **Select all**, **Clear selection** and a `N of M images selected for the report.` counter. The selection survives inventory refreshes, new images are selected by default and deleted images leave the selection.
- The `03_Data` contract now contains the data sources `01_SIMPATI`, `02_Graphtec` and `03_CANoe`. CSV is treated as a file format, not as an independent source.
- `POST /projects/inspect` now reports `data.simpati`, `data.graphtec` and `data.canoe` (plus `data.directory` and `data.simpati_file`).
- Each source now returns `files` as a list of objects with `name`, `relative_path` (relative to the test root, using `/`), `extension` (lower case) and `size` (bytes). Only regular files placed directly in the source folder are listed, sorted case-insensitively. Subfolders, hidden files and Office lock files are excluded, and file content is not read.
- **Analyze SIMPATI** is enabled only when SIMPATI is the selected source and the selected file is a detected SIMPATI acquisition.
- Changing the data source clears the selected file and the previous SIMPATI result and preview. Changing the file clears the previous SIMPATI result. No file is analyzed automatically.

### Added

- `GET /projects/evidence-photo` to serve one photo declared by a valid evidence (path confined to `02_Evidences`).
- Engine module `src/report_generator/evidence_photos.py` (`select_evidence_photos`, `resolve_evidence_photo`, `selectable_evidence_photos`, `ASSEMBLY_MAX_PHOTOS`, `EVIDENCE_PHOTOS_PER_SLIDE`).
- Frontend **Evidence photos** section (`components/EvidencePhotos.tsx`, `services/evidencePhotoSelection.ts`): two colour-coded panels with zone badges on each thumbnail, per-zone counters (`3 / 4 selected`, `5 of 7 selected`), **Select all** / **Clear selection** per zone and **Select** / **Clear** per evidence, the 4-photo lock in Test Assembly, and a summary of the photo/slide split next to **Generate PowerPoint**. User guide page `evidence-photos.md`.
- Tests: `tests/test_evidence_photos.py`, `tests/test_evidence_photos_api.py`, `evidencePhotoSelection.test.ts`, `EvidencePhotos.test.tsx`.

- `POST /projects/rendered-assets` (inventory with structured warnings for unsupported files), `GET /projects/rendered-asset` and `POST /projects/rendered-assets/delete`. Every client path is validated on the server: relative, without `.`/`..`, confined to `04_Report/_RenderedAssets`, existing regular file, accepted extension (case-insensitive) and valid image content.
- Engine helpers in `rendered_assets.py`: `list_rendered_assets`, `resolve_rendered_asset`, `select_rendered_assets`, `delete_rendered_asset`.
- Backend tests for the inventory, path security, selection validation and end-to-end insertion of selected images; frontend tests for the selection reducer and the **Report images** component; user guide page `report-images.md`.
- `Data source` and `File` selectors in `3. Review project resources`, shown after a project inspection.
- A neutral notice for CANoe indicating that reading this source will be added in a later increment.
- `canoe_directory()` and `CANOE_FOLDER_NAME` in `paths.py`, and `list_data_source_files()` in `data_sources.py`.
- Frontend selection logic in `services/dataSourceSelection.ts` and the `DataSourceSelector` component.
- Backend tests for the source inventory (missing `03_Data`, missing or empty sources, SIMPATI, Graphtec and CANoe files, subfolder exclusion, ordering, relative paths, unchanged SIMPATI behaviour, no file reads) and frontend tests for the selectors and SIMPATI gating.
- Initial Graphtec support for the tab-separated TXT format (no header, six fields per line) with DCW (current in uA) and IR (resistance in Mohm or Gohm, normalized to Mohm) tests, TEST and PASS statuses and I, R, T and D phases.
- Accumulated `elapsed_time_seconds` across phases, whose time counter restarts at every phase change. A phase time that goes back inside a phase is reported with its line number.
- Limited measurements such as `>50Gohm` keep their operator and are drawn at the normalized threshold with a distinct marker and a note; they are never shown as exact values.
- `Analyze Graphtec`, a Graphtec summary, chart configuration (series, title, legend, phase separators and elapsed time range), `Preview chart` and `Save chart` in the desktop interface.
- `POST /projects/graphtec/inspect`, `/preview-chart`, `/save-chart`, `/charts`, `/delete-chart` and `GET /projects/graphtec/chart`. The server confines every file to `03_Data/02_Graphtec`.
- Graphtec charts saved in `04_Report/_RenderedAssets` as `graphtec_chart_NN.png` with a JSON metadata file (source, relative path, test type, series, time range and units). Once saved they are regular report images that the user can select for the PowerPoint.
- Shared `rendered_assets.py` helpers for folder creation, PNG validation, non-overwriting chart names, listing and safe resolution, now also used by SIMPATI.

### Notes

- File names are never interpreted: test type, channel, units, phases, times and result come only from the file content.
- Another Graphtec format exists and is not supported yet; it returns a controlled unsupported-format error.

### Removed

- `POST /projects/simpati/charts`, `GET /projects/simpati/chart`, `POST /projects/simpati/delete-chart`, `POST /projects/graphtec/charts`, `GET /projects/graphtec/chart` and `POST /projects/graphtec/delete-chart`, replaced by the generic rendered-assets endpoints. `SavedSimpatiCharts.tsx` and the `listSimpatiCharts`/`fetchSimpatiChart`/`deleteSimpatiChart`/`listGraphtecCharts`/`fetchGraphtecChart`/`deleteGraphtecChart` API functions were replaced by `listRenderedAssets`, `fetchRenderedAsset` and `deleteRenderedAsset`.
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
