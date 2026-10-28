import type { DataSourceFileResult, DataSourceKey } from "../types/project";
import {
  formatFileSize,
  type DataSourceOption,
} from "../services/dataSourceSelection";

/**
 * Propiedades del selector de fuente y archivo de `03_Data`.
 */
export interface DataSourceSelectorProps {
  /** Fuentes mostradas: SIMPATI, Graphtec y CANoe. */
  options: DataSourceOption[];

  /** Fuente seleccionada o `null`. */
  selectedSourceKey: DataSourceKey | null;

  /** Archivos de la fuente seleccionada. */
  files: DataSourceFileResult[];

  /** `relative_path` del archivo seleccionado o `null`. */
  selectedFileRelativePath: string | null;

  /** Deshabilita el selector de archivo. */
  fileSelectorDisabled: boolean;

  /** Explicación cuando no hay archivos seleccionables. */
  fileHint: string | null;

  /** Mensaje neutral para fuentes cuya lectura todavía no existe. */
  pendingMessage: string | null;

  /** Deshabilita ambos selectores mientras otra operación está en curso. */
  disabled: boolean;

  /** Se invoca al elegir otra fuente. */
  onSourceChange: (sourceKey: DataSourceKey | null) => void;

  /** Se invoca al elegir otro archivo. */
  onFileChange: (fileRelativePath: string | null) => void;
}

function sourceOptionText(option: DataSourceOption): string {
  if (!option.found) {
    return `${option.label} (folder not found)`;
  }
  return `${option.label} (${option.fileCount} file${
    option.fileCount === 1 ? "" : "s"
  })`;
}

/**
 * Selector de la fuente de datos y de uno de sus archivos.
 *
 * Solo gestiona la selección: no lee el contenido del archivo ni inicia
 * ningún análisis.
 */
export function DataSourceSelector({
  options,
  selectedSourceKey,
  files,
  selectedFileRelativePath,
  fileSelectorDisabled,
  fileHint,
  pendingMessage,
  disabled,
  onSourceChange,
  onFileChange,
}: DataSourceSelectorProps) {
  return (
    <div className="data-source-selector">
      <div className="data-source-selector__fields">
        <div className="data-source-selector__field">
          <label htmlFor="data-source">Data source</label>
          <select
            id="data-source"
            value={selectedSourceKey ?? ""}
            disabled={disabled}
            onChange={(event) =>
              onSourceChange(
                event.target.value === ""
                  ? null
                  : (event.target.value as DataSourceKey),
              )
            }
          >
            <option value="">Select a source</option>
            {options.map((option) => (
              <option key={option.key} value={option.key}>
                {sourceOptionText(option)}
              </option>
            ))}
          </select>
        </div>

        <div className="data-source-selector__field">
          <label htmlFor="data-source-file">File</label>
          <select
            id="data-source-file"
            value={selectedFileRelativePath ?? ""}
            disabled={disabled || fileSelectorDisabled}
            onChange={(event) =>
              onFileChange(
                event.target.value === "" ? null : event.target.value,
              )
            }
          >
            <option value="">
              {selectedSourceKey === null
                ? "Select a source first"
                : fileSelectorDisabled
                  ? "No files available"
                  : "Select a file"}
            </option>
            {files.map((file) => (
              <option
                key={file.relative_path}
                value={file.relative_path}
                title={file.relative_path}
              >
                {`${file.name} (${formatFileSize(file.size)})`}
              </option>
            ))}
          </select>
        </div>
      </div>

      {fileHint && <p className="action-hint">{fileHint}</p>}
      {pendingMessage && (
        <p className="data-source-selector__pending" role="status">
          {pendingMessage}
        </p>
      )}
    </div>
  );
}
