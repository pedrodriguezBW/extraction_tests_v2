import sys
import os
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = REPOSITORY_ROOT / "frontend"
os.environ["SPHINX_JS_NODE_MODULES"] = str(
    FRONTEND_ROOT / "node_modules"
)

sys.path.insert(0, str(REPOSITORY_ROOT))


project = "Generador de informes climáticos"
author = "BorgWarner"
copyright = "2026, BorgWarner"

version = "0.6.0"
release = "0.6.0"


extensions = [
    "myst_parser",
    "sphinx_design",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]


source_suffix = {
    ".md": "markdown",
}

root_doc = "index"

exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
]

language = "es"


html_theme = "furo"
html_title = "Documentación del generador de informes climáticos"

html_static_path = ["_static"]
html_show_sourcelink = False
html_show_sphinx = False


myst_enable_extensions = [
    "colon_fence",
    "deflist",
]

myst_heading_anchors = 3


autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
}

autodoc_typehints = "description"
autodoc_preserve_defaults = True


napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = False

# Configuración de Sphinx-JS y TypeDoc
FRONTEND_ROOT = REPOSITORY_ROOT / "frontend"
