project = "Generador de informes climáticos"
author = "BorgWarner"

version = "0.5.0"
release = "0.5.0"

extensions = [
    "myst_parser",
]

source_suffix = {
    ".md": "markdown",
}

root_doc = "index"
language = "es"

exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
]

html_theme = "furo"
html_title = "Documentación del generador de informes climáticos"
html_show_sourcelink = False
html_show_sphinx = False

myst_heading_anchors = 3
