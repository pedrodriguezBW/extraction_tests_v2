"""Severidades aplicadas sobre registros completos; nunca sobre el muestreo del visor."""

from statistics import median
import math

from ..standards import TEST_TYPES
from pydantic import BaseModel, Field


class ToleranceSettings(BaseModel):
    test_type: str = Field(max_length=10)
    channel: str = Field(max_length=200)
    reference: str | None = Field(default=None, max_length=200)


def _consistent_duration(durations):
    """Solo resume duraciones comparables; conserva frío/calor por separado."""
    if not durations:
        return None
    central = median(durations)
    return central if max(durations) - min(durations) <= 0.1 * central else None


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
    # Un hueco o una consigna ausente impiden enlazar ciclos entre bloques.
    blocks = [0] * len(times)
    for i in range(1, len(times)):
        interrupted = (not 0 < times[i] - times[i - 1] <= 3 * period
                       or not math.isfinite(setpoints[i - 1]) or not math.isfinite(setpoints[i]))
        blocks[i] = blocks[i - 1] + int(interrupted)
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
    result = {"schema_version": 1, "algorithm": "extreme-plateaus-v2", "test_type": test_type,
              "channel": actual.column, "reference": reference.column, "tolerance_k": 2,
              "scope": "full_acquisition", "status": None, "out_of_tolerance_segments": 0,
              "ta_c": None, "tb_c": None, "t1_minutes": None, "cycles": None,
              "t1_low_minutes": None, "t1_high_minutes": None, "cycles_partial": False,
              "complete_plateaus_count": 0,
              "excursion_context": [],
              "stabilization_delta_ts_k": None, "plateaus": [], "excursions": [], "warnings": []}
    if low is None or (test_type in {"Na", "Nb", "Nc"} and high - low < 4):
        result["warnings"].append("No hay mesetas extremas suficientes para una evaluación fiable")
        return result
    temperatures = {"low": [], "high": []}
    durations = {"low": [], "high": []}
    sequence = []
    reference_incomplete = any(blocks) or acquisition.rejected_count > 0 or any(not math.isfinite(v) for v in setpoints)
    measurement_incomplete = False
    partial_plateaus = False
    excursion_indexes = set()
    for start, end, duration, target in groups:
        level = "low" if abs(target - low) <= 0.05 else "high" if abs(target - high) <= 0.05 else None
        if level is None or (test_type == "Ab" and level != "low") or (test_type == "Bb" and abs(target - high) > 0.05):
            continue
        if test_type == "Bb":
            level = "high"
        # La duración y el recuento dependen de la consigna, no de que haya
        # medidas válidas después del asentamiento ni de que cumplan ±2 K.
        complete = (start > 0 and end < len(times) - 1
                    and blocks[start - 1] == blocks[start] == blocks[end] == blocks[end + 1])
        if complete:
            durations[level].append(duration / 60)
            sequence.append((level, blocks[start]))
        else:
            partial_plateaus = True
        settling = max(300, min(900, 0.1 * duration))
        evaluated = [i for i in range(start, end + 1) if times[i] >= times[start] + settling]
        if len(evaluated) < 2:
            measurement_incomplete = True
            continue
        result["plateaus"].append({"start": frame["Timestamp"].iloc[evaluated[0]].isoformat(),
                                   "end": frame["Timestamp"].iloc[end].isoformat(), "setpoint_c": target})
        excursion = []
        for i in evaluated:
            value = values[i]
            if not math.isfinite(value):
                measurement_incomplete = True
            if math.isfinite(value):
                temperatures[level].append(value)
            outside = math.isfinite(value) and abs(value - target) > 2
            if outside:
                excursion_indexes.add(i)
                excursion.append([frame["Timestamp"].iloc[i].isoformat(), value])
            elif excursion:
                result["excursions"].append(excursion)
                excursion = []
        if excursion:
            result["excursions"].append(excursion)
    result["out_of_tolerance_segments"] = len(result["excursions"])
    # El visor reducido debe dibujar también los picos que motivan el NOK,
    # junto con sus muestras vecinas; no basta con superponer un marcador.
    context_indexes = sorted({neighbor for i in excursion_indexes
                              for neighbor in (i - 1, i, i + 1) if 0 <= neighbor < len(times)})
    result["excursion_context"] = [
        [frame["Timestamp"].iloc[i].isoformat(), values[i] if math.isfinite(values[i]) else None]
        for i in context_indexes
    ]
    if result["plateaus"]:
        incomplete = reference_incomplete or measurement_incomplete
        result["status"] = "NOK" if result["excursions"] else None if incomplete else "OK"
    result["ta_c"] = min(temperatures["low"], default=None)
    result["tb_c"] = max(temperatures["high"], default=None)
    result["t1_minutes"] = _consistent_duration(durations["low"] + durations["high"])
    result["t1_low_minutes"] = _consistent_duration(durations["low"])
    result["t1_high_minutes"] = _consistent_duration(durations["high"])
    result["complete_plateaus_count"] = len(sequence)
    if test_type in {"Na", "Nb", "Nc"}:
        # Cada par completo de extremos opuestos cuenta una vez, empiece
        # por frío o por calor. Nunca se reutilizan mesetas ni cruzan huecos.
        pending = None
        count = 0
        for level, block in sequence:
            if pending is not None and pending[1] == block and pending[0] != level:
                count += 1
                pending = None
            else:
                pending = (level, block)
        result["cycles_partial"] = reference_incomplete or partial_plateaus or pending is not None
        result["cycles"] = count if count or not result["cycles_partial"] else None
        if result["cycles_partial"]:
            result["warnings"].append("Recuento parcial: solo se cuentan pares completos observados dentro de cada tramo continuo de consigna")
    if reference_incomplete:
        result["warnings"].append("Hay interrupciones de consigna o registros descartados; los cálculos conservan solo las mesetas completas observadas")
    if measurement_incomplete:
        result["warnings"].append("Faltan medidas para evaluar tolerancias; esto no anula las duraciones ni los ciclos obtenidos de la consigna")
    if not sequence:
        result["warnings"].append("No se observan mesetas completas delimitadas por cambios de consigna")
    elif result["t1_minutes"] is None:
        result["warnings"].append("Las duraciones no son uniformes; se muestran por separado las de frío y calor cuando son comparables")
    return result
