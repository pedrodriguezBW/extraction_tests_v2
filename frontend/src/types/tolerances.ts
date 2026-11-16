/** Resultado calculado en el servidor con todos los registros SIMPATI. */
export interface ToleranceSettings { test_type: string; channel: string; reference?: string | null }
export interface ToleranceResult {
  status: "OK" | "NOK" | null;
  channel: string; reference: string; scope: "full_acquisition";
  out_of_tolerance_segments: number;
  ta_c: number | null; tb_c: number | null; t1_minutes: number | null; cycles: number | null;
  plateaus: {start: string; end: string; setpoint_c: number}[];
  excursions: [string, number][][];
  warnings: string[];
}
export function toleranceSummary(result: ToleranceResult): string[] {
  const value = (n: number | null, unit = "") => n === null ? "—" : `${Number(n.toFixed(2))}${unit}`;
  return [
    `Tolerancias: ${result.status ?? "—"}${result.status === "NOK" ? ` (${result.out_of_tolerance_segments} ${result.out_of_tolerance_segments === 1 ? "tramo" : "tramos"} fuera)` : ""}`,
    `TA medida: ${value(result.ta_c, " °C")} · TB medida: ${value(result.tb_c, " °C")}`,
    `t1 medido: ${value(result.t1_minutes, " min")} · Ciclos: ${value(result.cycles)}`,
    "Estabilización (ΔTs ≤ 5 K): —",
    "Adquisición completa · Rampas no evaluadas",
  ];
}

/** Interpola posiciones de tiempo sobre los índices del visor reducido. */
export function timestampPosition(timestamps: readonly string[], timestamp: string): number {
  const time = Date.parse(timestamp);
  let low = 0;
  let high = timestamps.length - 1;
  if (time <= Date.parse(timestamps[low])) return low;
  if (time >= Date.parse(timestamps[high])) return high;
  while (high - low > 1) {
    const middle = Math.floor((low + high) / 2);
    if (Date.parse(timestamps[middle]) <= time) low = middle; else high = middle;
  }
  return low + (time - Date.parse(timestamps[low])) / (Date.parse(timestamps[high]) - Date.parse(timestamps[low]));
}
