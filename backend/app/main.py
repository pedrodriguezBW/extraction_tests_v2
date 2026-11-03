from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.report_generator.version import __version__
from src.report_generator.version_check import check_application_version

from .api.projects import router as projects_router


app = FastAPI(
    title="Climatic Report Generator API",
    description=(
        "Backend API for the climatic test report generator."
    ),
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1420",
        "http://127.0.0.1:1420",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://tauri.localhost",
        "tauri://localhost",
        "https://tauri.localhost",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.include_router(projects_router)


@app.get("/health")
def health_check():
    """Check whether the backend is available."""
    version_check = check_application_version()
    return {
        "status": "ok",
        "application": "climatic-report-generator",
        "version": __version__,
        "version_check": {
            "status": version_check.status,
            "installed_version": version_check.installed_version,
            "current_version": version_check.current_version,
            "package": version_check.package,
            "warning": version_check.warning,
        },
    }