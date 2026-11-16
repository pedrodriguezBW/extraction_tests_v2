import os
from pathlib import Path

LABORATORY_NAME = "STC"


TEMPLATE_PATH_ENV_VAR = "REPORT_TEMPLATE_PATH"
"""Variable de entorno que permite usar otra plantilla PowerPoint.

La define el lanzador del paquete instalable para apuntar a la copia de la
plantilla incluida en la instalacion. Si no existe, se usa la ruta de
desarrollo.
"""

DEFAULT_POWERPOINT_TEMPLATE_PATH = Path(
    r"C:\Users\pedrodriguez\OneDrive - BorgWarner\Tools\Automation\TR0NNN-YYMMDDXX-LEG_NAME-1 Rev. A  Highly Confidential 1.pptx"
)


def resolve_template_path(environ=None) -> Path:
    """Devuelve la plantilla indicada en el entorno o la ruta por defecto."""
    environ = os.environ if environ is None else environ
    value = (environ.get(TEMPLATE_PATH_ENV_VAR) or "").strip().strip('"')
    return Path(value) if value else DEFAULT_POWERPOINT_TEMPLATE_PATH


POWERPOINT_TEMPLATE_PATH = resolve_template_path()
