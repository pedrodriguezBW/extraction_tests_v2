import type {
  SimpatiAcquisitionSummary,
  SimpatiInspectionResponse,
} from "../types/simpati";
import { simpatiStatusLabel } from "../services/dataSourceSelection";

/**
 * Propiedades de la lista de adquisiciones SIMPATI.
 */
export interface SimpatiAcquisitionsProps {
  /** Resultado del análisis de todas las adquisiciones. */
  result: SimpatiInspectionResponse;

  /** Deshabilita la selección mientras hay otra operación en curso. */
  disabled: boolean;

  /** Abre una adquisición en el editor de gráficas. */
  onSelect: (relativePath: string) => void;
}

function formatInterval(acquisition: SimpatiAcquisitionSummary): string {
  if (!acquisition.acquisition_start || !acquisition.acquisition_end) {
    return "Not available";
  }
  const format = (value: string) => value.replace("T", " ");
  return `${format(acquisition.acquisition_start)} – ${format(acquisition.acquisition_end)}`;
}

function statusClass(acquisition: SimpatiAcquisitionSummary): string {
  switch (acquisition.status) {
    case "ready":
      return "simpati-status simpati-status--ready";
    case "no_thermal_channels":
      return "simpati-status simpati-status--warning";
    default:
      return "simpati-status simpati-status--error";
  }
}

/**
 * Lista todas las adquisiciones SIMPATI `.xNN` del ensayo con su estado.
 *
 * Cada adquisición se analiza de forma independiente: una adquisición
 * incompatible muestra su error sin impedir abrir las demás en el editor
 * de gráficas.
 */
export function SimpatiAcquisitions({
  result,
  disabled,
  onSelect,
}: SimpatiAcquisitionsProps) {
  return (
    <div className="simpati-acquisitions">
      <p className="simpati-acquisitions__summary" role="status">
        <span>{result.found_count} found</span>
        <span>{result.processed_count} processed</span>
        <span>{result.ready_count} with representable channels</span>
        <span>{result.without_thermal_count} without representable channels</span>
        <span>{result.incompatible_count} incompatible</span>
      </p>

      <div className="simpati-acquisitions__scroll">
        <table className="simpati-acquisitions__table">
          <caption className="sr-only">SIMPATI acquisitions</caption>
          <thead>
            <tr>
              <th scope="col">Index</th>
              <th scope="col">File</th>
              <th scope="col">Encoding</th>
              <th scope="col">Records</th>
              <th scope="col">Time interval</th>
              <th scope="col">Channels</th>
              <th scope="col">Thermal channels</th>
              <th scope="col">Status</th>
              <th scope="col">
                <span className="sr-only">Action</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {result.acquisitions.map((acquisition) => {
              const selected =
                acquisition.relative_path === result.selected_relative_path;
              return (
                <tr
                  key={acquisition.relative_path}
                  className={selected ? "is-selected" : undefined}
                  aria-selected={selected}
                >
                  <td>
                    <strong>{acquisition.label}</strong>
                  </td>
                  <td>
                    <span title={acquisition.relative_path}>
                      {acquisition.file_name}
                    </span>
                  </td>
                  <td>{acquisition.encoding ?? "—"}</td>
                  <td>{acquisition.records_count}</td>
                  <td>{formatInterval(acquisition)}</td>
                  <td>{acquisition.channels_count}</td>
                  <td>
                    {acquisition.thermal_channels.length > 0
                      ? acquisition.thermal_channels.join(", ")
                      : "None"}
                  </td>
                  <td>
                    <span className={statusClass(acquisition)}>
                      {simpatiStatusLabel(acquisition.status)}
                    </span>
                    {acquisition.error && (
                      <span className="simpati-acquisitions__error" role="alert">
                        {acquisition.error.message}
                      </span>
                    )}
                    {acquisition.rejected_rows > 0 && (
                      <span className="simpati-acquisitions__warning">
                        {acquisition.rejected_rows} incompatible record
                        {acquisition.rejected_rows === 1 ? "" : "s"} ignored
                      </span>
                    )}
                  </td>
                  <td>
                    <button
                      className="button button--quiet"
                      type="button"
                      disabled={disabled || selected}
                      onClick={() => onSelect(acquisition.relative_path)}
                    >
                      {selected ? "Selected" : "Open"}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
