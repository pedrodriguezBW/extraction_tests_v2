"""Configuración del ingeniero, independiente del metadata de solo lectura."""

import json
import os
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .standards import TEST_TYPES


class MeasurementPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    channel: str = Field(default="", max_length=200)
    location: str = Field(default="", max_length=200)
    sensor_type: str = Field(default="", max_length=200)
    function: Literal["", "specimen", "air", "control"] = ""


class ReportInputs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    test_type: str = ""
    measurement_points: list[MeasurementPoint] = Field(default_factory=list, max_length=500)

    @field_validator("schema_version", mode="before")
    @classmethod
    def exact_schema_version(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError("Versión de configuración desconocida")
        return value

    @field_validator("test_type")
    @classmethod
    def known_test_type(cls, value):
        if value and value not in TEST_TYPES:
            raise ValueError("Tipo de ensayo desconocido")
        return value


def inputs_path(test_root):
    root = Path(test_root).resolve()
    report = root / "04_Report"
    if not root.is_dir() or not report.is_dir():
        raise FileNotFoundError("No existe la carpeta del ensayo o 04_Report")
    path = report / "_Working" / "report_inputs.json"
    if not path.resolve().is_relative_to(report.resolve()):
        raise ValueError("La configuración debe estar dentro de 04_Report")
    return path


def load_report_inputs(test_root):
    """Ignora archivos inválidos con aviso, conservando el original."""
    path = inputs_path(test_root)
    try:
        return ReportInputs.model_validate_json(path.read_text(encoding="utf-8")), []
    except FileNotFoundError:
        return ReportInputs(), []
    except (ValueError, UnicodeError) as error:
        return ReportInputs(), [f"Se ha ignorado report_inputs.json: {error}"]


def save_report_inputs(test_root, inputs):
    """Publica el JSON de forma atómica para evitar guardados parciales."""
    inputs = ReportInputs.model_validate(inputs)
    path = inputs_path(test_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as output:
            temporary = output.name
            json.dump(inputs.model_dump(), output, ensure_ascii=False, indent=2)
        os.replace(temporary, path)
    finally:
        if temporary and Path(temporary).exists():
            Path(temporary).unlink()
    return inputs
