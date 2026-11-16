import {timestampPosition, type ToleranceResult} from "../types/tolerances";

export type TimedPoint = readonly [string, number | null];

/** Incorpora medidas originales al trazado reducido, sin mover los puntos rojos. */
export function mergeToleranceTrace(
  timestamps: readonly string[], values: readonly (number | null)[], result: ToleranceResult, unit: string,
): TimedPoint[] {
  const points = new Map<number, TimedPoint>();
  timestamps.forEach((timestamp, index) => points.set(Date.parse(timestamp), [timestamp, values[index] ?? null]));
  const display = (value: number | null) => value === null ? null : unit.toLowerCase().includes("f") ? value * 9 / 5 + 32 : value;
  for (const [timestamp, value] of result.excursion_context ?? []) points.set(Date.parse(timestamp), [timestamp, display(value)]);
  for (const segment of result.excursions) {
    for (const [timestamp, value] of segment) points.set(Date.parse(timestamp), [timestamp, display(value)]);
  }
  return [...points.entries()].sort(([a], [b]) => a - b).map(([, point]) => point);
}

/** Dibuja el mismo trazado temporal en el visor y en la exportación. */
export function timedPathSegments(
  points: readonly TimedPoint[], timestamps: readonly string[], start: number, end: number,
  xScale: (index: number) => number, yScale: (value: number) => number,
): string[] {
  const segments: string[] = [];
  let current: string[] = [];
  const flush = () => {if (current.length > 1) segments.push(current.join(" ")); current = [];};
  for (const [timestamp, value] of points) {
    const position = timestampPosition(timestamps, timestamp);
    if (position < start || position > end) continue;
    if (value === null || !Number.isFinite(value)) {flush(); continue;}
    current.push(`${xScale(position)},${yScale(value)}`);
  }
  flush();
  return segments;
}
