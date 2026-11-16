/** Datos persistidos del ingeniero. El metadata permanece de solo lectura. */
export interface MeasurementPoint {
  channel: string;
  location: string;
  sensor_type: string;
  function: "" | "specimen" | "air" | "control";
}
export interface ReportInputs {
  schema_version: 1;
  test_type: string;
  measurement_points: MeasurementPoint[];
}
export type TestCatalog = Record<string, {name: string; standard: string}>;
export const emptyInputs = (): ReportInputs => ({schema_version: 1, test_type: "", measurement_points: []});

/** Conserva las filas existentes y añade los canales recién detectados. */
export function mergeChannels(inputs: ReportInputs, channels: string[]): ReportInputs {
  const existing = new Set(inputs.measurement_points.map(point => point.channel));
  return {...inputs, measurement_points: [...inputs.measurement_points,
    ...[...new Set(channels)].filter(channel => !existing.has(channel)).map(channel => ({channel, location: "", sensor_type: "", function: "" as const}))]};
}
