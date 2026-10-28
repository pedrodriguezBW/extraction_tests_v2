"""Define la estructura de carpetas de un ensayo individual.

La aplicación recibe la carpeta raíz de un ensayo, por ejemplo
``TEST - 001``, con la siguiente estructura::

    TEST - 001
    ├── 01_Inputs
    ├── 02_Evidences
    │   └── <carpeta de evidencia>/evidence.json
    ├── 03_Data
    │   ├── 01_SIMPATI
    │   ├── 02_Graphtec
    │   └── 03_CANoe
    └── 04_Report
        ├── test_metadata.json
        ├── _RenderedAssets
        └── _Working

SIMPATI, Graphtec y CANoe son orígenes de datos. CSV es un formato de
archivo y no se trata como una fuente independiente.

Un proceso externo genera ``test_metadata.json``. El generador de informes se
limita a leerlo y escribe sus propias salidas dentro de ``04_Report``.
"""

from pathlib import Path


#: Nombre de la carpeta que contiene los archivos de entrada del ensayo.
INPUTS_FOLDER_NAME = "01_Inputs"

#: Nombre de la carpeta que contiene las evidencias del ensayo.
EVIDENCES_FOLDER_NAME = "02_Evidences"

#: Nombre de la carpeta que agrupa las fuentes de adquisición.
DATA_FOLDER_NAME = "03_Data"

#: Nombre de la subcarpeta de adquisiciones SIMPATI.
SIMPATI_FOLDER_NAME = "01_SIMPATI"

#: Nombre de la subcarpeta de adquisiciones Graphtec.
GRAPHTEC_FOLDER_NAME = "02_Graphtec"

#: Nombre de la subcarpeta de adquisiciones CANoe.
CANOE_FOLDER_NAME = "03_CANoe"

#: Nombre de la carpeta que contiene los recursos y salidas del informe.
REPORT_FOLDER_NAME = "04_Report"

#: Nombre de la carpeta que almacena los recursos gráficos renderizados.
RENDERED_ASSETS_FOLDER_NAME = "_RenderedAssets"

#: Nombre de la carpeta utilizada para montar el informe en curso.
WORKING_FOLDER_NAME = "_Working"

#: Nombre del archivo de metadatos generado externamente.
METADATA_FILENAME = "test_metadata.json"

#: Nombre del descriptor utilizado en cada carpeta de evidencia.
EVIDENCE_DESCRIPTOR_FILENAME = "evidence.json"


def inputs_directory(test_root: Path) -> Path:
    """Obtiene la carpeta de archivos de entrada del ensayo.

    Args:
        test_root: Ruta de la carpeta raíz del ensayo.

    Returns:
        Ruta de ``01_Inputs``.
    """
    return Path(test_root) / INPUTS_FOLDER_NAME


def evidences_directory(test_root: Path) -> Path:
    """Obtiene la carpeta de evidencias del ensayo.

    Args:
        test_root: Ruta de la carpeta raíz del ensayo.

    Returns:
        Ruta de ``02_Evidences``.
    """
    return Path(test_root) / EVIDENCES_FOLDER_NAME


def data_directory(test_root: Path) -> Path:
    """Obtiene la carpeta que agrupa las fuentes de adquisición.

    Args:
        test_root: Ruta de la carpeta raíz del ensayo.

    Returns:
        Ruta de ``03_Data``.
    """
    return Path(test_root) / DATA_FOLDER_NAME


def simpati_directory(test_root: Path) -> Path:
    """Obtiene la carpeta de adquisiciones SIMPATI.

    Args:
        test_root: Ruta de la carpeta raíz del ensayo.

    Returns:
        Ruta de ``03_Data/01_SIMPATI``.
    """
    return data_directory(test_root) / SIMPATI_FOLDER_NAME


def graphtec_directory(test_root: Path) -> Path:
    """Obtiene la carpeta de adquisiciones Graphtec.

    Args:
        test_root: Ruta de la carpeta raíz del ensayo.

    Returns:
        Ruta de ``03_Data/02_Graphtec``.
    """
    return data_directory(test_root) / GRAPHTEC_FOLDER_NAME


def canoe_directory(test_root: Path) -> Path:
    """Obtiene la carpeta de adquisiciones CANoe.

    Args:
        test_root: Ruta de la carpeta raíz del ensayo.

    Returns:
        Ruta de ``03_Data/03_CANoe``.
    """
    return data_directory(test_root) / CANOE_FOLDER_NAME


def report_directory(test_root: Path) -> Path:
    """Obtiene la carpeta principal del informe.

    Args:
        test_root: Ruta de la carpeta raíz del ensayo.

    Returns:
        Ruta de ``04_Report``.
    """
    return Path(test_root) / REPORT_FOLDER_NAME


def rendered_assets_directory(test_root: Path) -> Path:
    """Obtiene la carpeta de recursos gráficos renderizados.

    Args:
        test_root: Ruta de la carpeta raíz del ensayo.

    Returns:
        Ruta de ``04_Report/_RenderedAssets``.
    """
    return report_directory(test_root) / RENDERED_ASSETS_FOLDER_NAME


def working_directory(test_root: Path) -> Path:
    """Obtiene la carpeta de trabajo utilizada para montar el informe.

    Args:
        test_root: Ruta de la carpeta raíz del ensayo.

    Returns:
        Ruta de ``04_Report/_Working``.
    """
    return report_directory(test_root) / WORKING_FOLDER_NAME


def metadata_path(test_root: Path) -> Path:
    """Obtiene la ruta del archivo de metadatos del ensayo.

    Args:
        test_root: Ruta de la carpeta raíz del ensayo.

    Returns:
        Ruta de ``04_Report/test_metadata.json``.
    """
    return report_directory(test_root) / METADATA_FILENAME
