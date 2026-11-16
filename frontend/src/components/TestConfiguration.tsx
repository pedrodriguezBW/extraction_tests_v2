import type { ReportInputs, TestCatalog, MeasurementPoint } from "../types/reportInputs";

/** Panel editable con filas manuales y avisos de canales ausentes. */
export function TestConfiguration({inputs, catalog, channels, detected, disabled, warnings, onChange, onSave}: {
  inputs: ReportInputs; catalog: TestCatalog; channels: string[]; detected: boolean;
  disabled: boolean; warnings: string[]; onChange: (value: ReportInputs) => void; onSave: () => void;
}) {
  const update = (index: number, key: keyof MeasurementPoint, value: string) => onChange({
    ...inputs, measurement_points: inputs.measurement_points.map((point, i) => i === index ? {...point, [key]: value} : point),
  });
  return <section className="workflow-section test-configuration">
    <h2>Configuración del ensayo</h2>
    {warnings.map((warning, i) => <p role="status" key={i}>{warning}</p>)}
    <fieldset disabled={disabled}>
      <label>Tipo de ensayo <select value={inputs.test_type} onChange={event => onChange({...inputs, test_type: event.target.value})}>
        <option value="">—</option>
        {Object.entries(catalog).map(([code, entry]) => <option key={code} value={code}>{code} – {entry.name}</option>)}
      </select></label>
      <div style={{overflowX: "auto"}}><table><caption>Puntos de medida</caption>
        <thead><tr>{["Canal", "Ubicación", "Tipo de sensor", "Función", ""].map((label, i) => <th key={i}>{label}</th>)}</tr></thead>
        <tbody>{inputs.measurement_points.map((point, index) => <tr key={index}>
          {(["channel", "location", "sensor_type"] as const).map(key => <td key={key}>
            <input aria-label={`${key} ${index + 1}`} maxLength={200} value={point[key]} onChange={event => update(index, key, event.target.value)}/>
            {key === "channel" && detected && point.channel && !channels.includes(point.channel) && <small>no encontrado en los logs</small>}
          </td>)}
          <td><select aria-label={`Función ${index + 1}`} value={point.function} onChange={event => update(index, "function", event.target.value)}>
            <option value="">—</option><option value="specimen">Espécimen</option><option value="air">Aire</option><option value="control">Control</option>
          </select></td>
          <td><button className="button button--quiet" type="button" onClick={() => onChange({...inputs, measurement_points: inputs.measurement_points.filter((_, i) => i !== index)})}>Borrar</button></td>
        </tr>)}</tbody>
      </table></div>
      <button className="button button--secondary" type="button" disabled={inputs.measurement_points.length >= 500} onClick={() => onChange({...inputs, measurement_points: [...inputs.measurement_points, {channel: "", location: "", sensor_type: "", function: ""}]})}>Añadir fila</button>
      <button className="button button--primary" type="button" onClick={onSave}>Guardar</button>
    </fieldset>
  </section>;
}
