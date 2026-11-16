"""Severidades aplicadas sobre registros completos; nunca sobre el muestreo del visor."""

from statistics import median
import math

from ..standards import TEST_TYPES
from pydantic import BaseModel, Field


class ToleranceSettings(BaseModel):
    test_type: str = Field(max_length=10)
    channel: str = Field(max_length=200)
    reference: str | None = Field(default=None, max_length=200)


def evaluate_tolerances(acquisition, channels, test_type, channel_column, reference_column=None):
    """Evalúa mesetas extremas, excluye rampas, asentamiento y huecos temporales.

    Una meseta conserva la consigna a ±0,05 K de su primer valor. Los huecos
    mayores que tres periodos de muestreo separan tramos. Las mesetas de los
    extremos del archivo se consideran censuradas para duración y ciclos.
    """
    if test_type not in TEST_TYPES:
        raise ValueError("Seleccione un tipo de ensayo")
    actual = next((c for c in channels if c.column == channel_column and c.thermal and c.kind == "actual"), None)
    if actual is None:
        raise ValueError("Seleccione un canal térmico de medida")
    references = [c for c in channels if c.thermal and c.kind == "setpoint"]
    if reference_column:
        references = [c for c in references if c.column == reference_column]
    else:
        family = (actual.role or "").replace("_temperature", "")
        matching = [c for c in references if c.role == family + "_setpoint"]
        references = matching or references
    if len(references) != 1:
        raise ValueError("Seleccione una consigna inequívoca para el canal evaluado")
    reference = references[0]
    frame = acquisition.dataframe
    times = [value.timestamp() for value in frame["Timestamp"]]
    actual_values = frame[actual.column].tolist()
    nominal = frame[reference.column].tolist()
    # La banda es de 2 K, también cuando el archivo usa grados Fahrenheit.
    def celsius(value, unit):
        value = float(value)
        return (value - 32) * 5 / 9 if "f" in unit.lower() else value
    values = [celsius(v, actual.unit) for v in actual_values]
    setpoints = [celsius(v, reference.unit) for v in nominal]
    deltas = [b - a for a, b in zip(times, times[1:]) if b > a]
    period = median(deltas) if deltas else 0
    groups = []
    start = None
    for i in range(len(times) + 1):
        valid = i < len(times) and math.isfinite(setpoints[i])
        continues = (valid and start is not None and i > 0
                     and 0 < times[i] - times[i - 1] <= 3 * period
                     and abs(setpoints[i] - setpoints[start]) <= 0.05)
        if start is not None and not continues:
            end = i - 1
            duration = times[end] - times[start]
            if duration >= 300:
                groups.append((start, end, duration, setpoints[start]))
            start = None
        if valid and start is None:
            start = i
    low = min((g[3] for g in groups), default=None)
    high = max((g[3] for g in groups), default=None)
    result = {"schema_version": 1, "algorithm": "extreme-plateaus-v1", "test_type": test_type,
              "channel": actual.column, "reference": reference.column, "tolerance_k": 2,
              "scope": "full_acquisition", "status": None, "out_of_tolerance_segments": 0,
              "ta_c": None, "tb_c": None, "t1_minutes": None, "cycles": None,
              "stabilization_delta_ts_k": None, "plateaus": [], "excursions": [], "warnings": []}
    if low is None or (test_type in {"Na", "Nb", "Nc"} and high - low < 4):
        result["warnings"].append("No hay mesetas extremas suficientes para una evaluación fiable")
        return result
    temperatures = {"low": [], "high": []}
    durations = []
    sequence = []
    incomplete = any(delta > 3 * period for delta in deltas) or acquisition.rejected_count > 0
    for start, end, duration, target in groups:
        level = "low" if abs(target - low) <= 0.05 else "high" if abs(target - high) <= 0.05 else None
        if level is None or (test_type == "Ab" and level != "low") or (test_type == "Bb" and abs(target - high) > 0.05):
            continue
        if test_type == "Bb":
            level = "high"
        settling = max(300, min(900, 0.1 * duration))
        evaluated = [i for i in range(start, end + 1) if times[i] >= times[start] + settling]
        if len(evaluated) < 2:
            continue
        result["plateaus"].append({"start": frame["Timestamp"].iloc[evaluated[0]].isoformat(),
                                   "end": frame["Timestamp"].iloc[end].isoformat(), "setpoint_c": target})
        if start > 0 and end < len(times) - 1 and times[start] - times[start - 1] <= 3 * period and times[end + 1] - times[end] <= 3 * period:
            durations.append(duration / 60)
            sequence.append(level)
        excursion = []
        for i in evaluated:
            value = values[i]
            if not math.isfinite(value):
                incomplete = True
            if math.isfinite(value):
                temperatures[level].append(value)
            outside = math.isfinite(value) and abs(value - target) > 2
            if outside:
                excursion.append([frame["Timestamp"].iloc[i].isoformat(), value])
            elif excursion:
                result["excursions"].append(excursion)
                excursion = []
        if excursion:
            result["excursions"].append(excursion)
    result["out_of_tolerance_segments"] = len(result["excursions"])
    if result["plateaus"]:
        result["status"] = "NOK" if result["excursions"] else None if incomplete else "OK"
    result["ta_c"] = min(temperatures["low"], default=None)
    result["tb_c"] = max(temperatures["high"], default=None)
    if durations and max(durations) - min(durations) <= 0.1 * median(durations):
        result["t1_minutes"] = median(durations)
    if test_type in {"Na", "Nb", "Nc"}:
        # Solo cuentan pares frío/calor completos, sin reutilizar mesetas.
        pending = False
        count = 0
        for level in sequence:
            if level == "low":
                pending = True
            elif pending:
                count += 1
                pending = False
        result["cycles"] = count
    if incomplete:
        result["t1_minutes"] = None
        result["cycles"] = None
        result["warnings"].append("Hay huecos o medidas ausentes; no se puede declarar OK")
    return result
