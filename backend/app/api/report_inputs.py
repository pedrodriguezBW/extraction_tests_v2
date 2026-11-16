"""Operaciones de la configuración del ensayo."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.report_generator.report_inputs import ReportInputs, load_report_inputs, save_report_inputs
from src.report_generator.standards import TEST_TYPES
from .projects import _outdated_version_response
from ..services.simpati_inspection import _analyze
from src.report_generator.simpati.files import resolve_simpati_acquisition
from src.report_generator.simpati.models import SimpatiError

router = APIRouter(prefix="/projects", tags=["projects"])


class InputsRequest(BaseModel):
    test_root: str
    inputs: ReportInputs | None = None
    selected_simpati_files: list[str] = Field(default_factory=list, max_length=100)


@router.post("/report-inputs/load")
def load_inputs(request: InputsRequest):
    try:
        inputs, warnings = load_report_inputs(request.test_root)
        channels = []
        for relative_path in request.selected_simpati_files:
            analysis = _analyze(resolve_simpati_acquisition(request.test_root, relative_path))
            if analysis.error:
                warnings.append(str(analysis.error))
            channels.extend(channel.column for channel in analysis.thermal_channels)
        return {"inputs": inputs, "warnings": warnings, "test_types": TEST_TYPES,
                "channels": list(dict.fromkeys(channels))}
    except (OSError, ValueError, SimpatiError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/report-inputs/save")
def save_inputs(request: InputsRequest):
    version_error = _outdated_version_response()
    if version_error is not None:
        return version_error
    if request.inputs is None:
        raise HTTPException(status_code=422, detail="Falta la configuración")
    try:
        return {"inputs": save_report_inputs(request.test_root, request.inputs)}
    except (OSError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
