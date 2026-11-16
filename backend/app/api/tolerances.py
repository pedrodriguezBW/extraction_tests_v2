"""Evaluación SIMPATI con resolución completa."""

from fastapi import APIRouter, HTTPException

from src.report_generator.simpati.files import resolve_simpati_acquisition
from src.report_generator.simpati.tolerances import evaluate_tolerances, ToleranceSettings
from ..services.simpati_inspection import _analyze

router = APIRouter(prefix="/projects/simpati", tags=["projects"])


class ToleranceRequest(ToleranceSettings):
    test_root: str
    relative_path: str


def evaluate_project_tolerances(test_root, relative_path, settings):
    analysis = _analyze(resolve_simpati_acquisition(test_root, relative_path))
    if analysis.acquisition is None:
        raise ValueError("No se ha podido leer la adquisición SIMPATI")
    return evaluate_tolerances(analysis.acquisition, analysis.channels, settings.test_type, settings.channel, settings.reference)


@router.post("/tolerances")
def tolerances(request: ToleranceRequest):
    try:
        return evaluate_project_tolerances(request.test_root, request.relative_path, request)
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
