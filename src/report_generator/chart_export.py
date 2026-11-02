"""Formato común de exportación de las gráficas de ``_RenderedAssets``.

Todas las gráficas que la aplicación guarda como imagen para el informe
(Graphtec y la herramienta de consola SIMPATI; el visor SIMPATI del
frontend replica estas mismas cifras en ``services/chartExport.ts``) se
exportan con el mismo tamaño, la misma proporción y la misma tipografía.

Criterio de diseño
------------------
En ``4. Test Results`` las gráficas se colocan de dos en dos, en dos
columnas. Cada columna mide ``(CONTENT_WIDTH_CM - RESULT_HORIZONTAL_GAP_CM)
/ 2`` (unos 14,4 cm en la plantilla corporativa). La figura se diseña con
ese ancho físico, de modo que los tamaños en puntos indicados aquí son los
que se ven en la diapositiva con dos gráficas (con una sola gráfica se ven
algo mayores). La resolución se elige para obtener 1800 × 1125 px
(proporción 1,6:1, unos 317 ppp en la columna).

Este módulo no afecta a las fotografías de evidencias ni a las gráficas
nativas de PowerPoint de ``Test Inputs``.
"""

from __future__ import annotations

from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from typing import Iterator, Sequence, Union

import matplotlib
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

from .powerpoint.styles import CONTENT_WIDTH_CM, RESULT_HORIZONTAL_GAP_CM

# -----------------------------------------------------------------------------
# Tamaño y proporción de exportación
# -----------------------------------------------------------------------------

#: Proporción ancho:alto de todas las gráficas exportadas.
EXPORT_ASPECT_RATIO = 1.6

#: Tamaño en píxeles de las imágenes exportadas.
EXPORT_WIDTH_PX = 1800
EXPORT_HEIGHT_PX = round(EXPORT_WIDTH_PX / EXPORT_ASPECT_RATIO)  # 1125

#: Ancho físico de diseño: una columna de ``Test Results``.
EXPORT_DESIGN_WIDTH_CM = (CONTENT_WIDTH_CM - RESULT_HORIZONTAL_GAP_CM) / 2
EXPORT_DESIGN_WIDTH_IN = EXPORT_DESIGN_WIDTH_CM / 2.54
EXPORT_DESIGN_HEIGHT_IN = EXPORT_DESIGN_WIDTH_IN / EXPORT_ASPECT_RATIO

#: Resolución que convierte el tamaño de diseño en 1800 × 1125 px.
EXPORT_DPI = EXPORT_WIDTH_PX / EXPORT_DESIGN_WIDTH_IN

# -----------------------------------------------------------------------------
# Tipografía y trazos (puntos tal como se ven en la diapositiva)
# -----------------------------------------------------------------------------

FONT_FAMILY = ["Arial", "Liberation Sans", "DejaVu Sans"]
FONT_SIZE_TITLE_PT = 13.0
FONT_SIZE_AXIS_LABEL_PT = 12.0
FONT_SIZE_TICK_PT = 11.0
FONT_SIZE_LEGEND_PT = 11.0
FONT_SIZE_ANNOTATION_PT = 10.0

LINE_WIDTH_PT = 1.8
SECONDARY_LINE_WIDTH_PT = 1.5
MARKER_SIZE_PT = 3.0
GRID_LINE_WIDTH_PT = 0.6
AXES_LINE_WIDTH_PT = 0.8

#: Número máximo de marcas del eje X para que las etiquetas no se solapen.
MAX_X_TICKS = 6

#: Ancho reservado a la izquierda del título para el eje Y (pulgadas).
TITLE_LEFT_RESERVE_IN = 0.9

#: Margen exterior de la figura (pulgadas): el mínimo para no recortar textos.
FIGURE_PAD_IN = 0.04

#: Parámetros de Matplotlib aplicados a cada gráfica exportada.
REPORT_CHART_RC = {
    "font.family": "sans-serif",
    "font.sans-serif": FONT_FAMILY,
    "font.size": FONT_SIZE_TICK_PT,
    "axes.titlesize": FONT_SIZE_TITLE_PT,
    "axes.titleweight": "bold",
    "axes.labelsize": FONT_SIZE_AXIS_LABEL_PT,
    "axes.linewidth": AXES_LINE_WIDTH_PT,
    "axes.titlepad": 6.0,
    "axes.labelpad": 3.0,
    "xtick.labelsize": FONT_SIZE_TICK_PT,
    "ytick.labelsize": FONT_SIZE_TICK_PT,
    "xtick.major.pad": 2.5,
    "ytick.major.pad": 2.5,
    "legend.fontsize": FONT_SIZE_LEGEND_PT,
    "legend.handlelength": 2.2,
    "legend.columnspacing": 1.2,
    "legend.borderaxespad": 0.2,
    "lines.linewidth": LINE_WIDTH_PT,
    "lines.markersize": MARKER_SIZE_PT,
    "grid.linewidth": GRID_LINE_WIDTH_PT,
    "axes.formatter.useoffset": False,
    "figure.constrained_layout.h_pad": FIGURE_PAD_IN,
    "figure.constrained_layout.w_pad": FIGURE_PAD_IN,
    "savefig.facecolor": "white",
}


@contextmanager
def report_chart_style() -> Iterator[None]:
    """Aplica temporalmente el estilo común de exportación."""
    with matplotlib.rc_context(REPORT_CHART_RC):
        yield


def new_report_figure() -> Figure:
    """Crea una figura con el tamaño de exportación y diseño ajustado.

    El diseño ``constrained`` reserva el espacio justo para títulos, ejes y
    leyenda, de modo que no quedan márgenes blancos innecesarios ni textos
    recortados.
    """
    figure = Figure(
        figsize=(EXPORT_DESIGN_WIDTH_IN, EXPORT_DESIGN_HEIGHT_IN),
        dpi=EXPORT_DPI,
        layout="constrained",
    )
    FigureCanvasAgg(figure)
    return figure


def limit_numeric_ticks(axis) -> None:
    """Limita las marcas para evitar solapes y muestra valores completos.

    Sin desplazamiento (``offset``) un rango Y estrecho se lee con sus
    valores reales en lugar de ``+2.0e1``.
    """
    axis.xaxis.set_major_locator(MaxNLocator(nbins=MAX_X_TICKS, min_n_ticks=3))
    axis.yaxis.set_major_locator(MaxNLocator(nbins=6, min_n_ticks=4))
    axis.ticklabel_format(axis="both", style="plain", useOffset=False)


def legend_columns(
    labels: Sequence[str],
    figure: Figure | None = None,
    max_columns: int = 3,
) -> int:
    """Número de columnas de la leyenda para que quepa en el ancho de la figura.

    Con una figura se mide el texto real con su renderizador; sin ella se
    estima con el ancho medio de un carácter. Cada entrada incluye la
    muestra de línea, el espacio hasta el texto y la separación entre
    columnas.
    """
    if not labels:
        return 1

    legend_px = FONT_SIZE_LEGEND_PT * EXPORT_DPI / 72
    extra_em = (
        REPORT_CHART_RC["legend.handlelength"]
        + 0.8  # separación entre la muestra y el texto
        + REPORT_CHART_RC["legend.columnspacing"]
    )
    if figure is not None:
        from matplotlib.font_manager import FontProperties

        renderer = figure.canvas.get_renderer()
        properties = FontProperties(size=FONT_SIZE_LEGEND_PT)
        text_px = max(
            renderer.get_text_width_height_descent(label, properties, ismath=False)[0]
            for label in labels
        )
    else:
        text_px = max(len(label) for label in labels) * 0.55 * legend_px

    entry_px = text_px + extra_em * legend_px
    available_px = EXPORT_WIDTH_PX * 0.97
    columns = int(available_px // entry_px)
    return max(1, min(max_columns, columns, len(labels)))


def add_report_legend(
    figure: Figure,
    handles,
    labels: Sequence[str],
    notes: Sequence[str] = (),
) -> None:
    """Añade la leyenda debajo de la gráfica, completamente visible.

    Las notas (por ejemplo, el significado de los marcadores de límite) se
    escriben como título de la leyenda: el diseño ajustado reserva su
    espacio junto al de la leyenda y nunca se superponen.
    """
    handles = list(handles or [])
    note_text = _wrap_notes(notes)
    if not handles and not note_text:
        return
    labels = list(labels)
    columns = legend_columns(labels, figure) if handles else 1
    if not handles:
        # Solo notas: una entrada invisible permite mostrar el título.
        from matplotlib.lines import Line2D

        handles = [Line2D([], [], linestyle="none")]
        labels = [""]
    legend = figure.legend(
        handles=handles,
        labels=labels,
        loc="outside lower center",
        ncol=columns,
        frameon=False,
        title=note_text or None,
        title_fontproperties={"size": FONT_SIZE_ANNOTATION_PT},
        alignment="left",
    )
    if note_text:
        legend.get_title().set_color("#405566")


def _wrap_notes(notes: Sequence[str]) -> str:
    """Reparte las notas en líneas que caben en el ancho de la figura."""
    import textwrap

    characters_per_line = int(
        EXPORT_DESIGN_WIDTH_IN * 72 / (FONT_SIZE_ANNOTATION_PT * 0.5)
    )
    lines: list[str] = []
    for note in notes:
        lines.extend(textwrap.wrap(note, width=characters_per_line))
    return "\n".join(lines)


def save_report_png(
    figure: Figure,
    target: Union[str, Path, BytesIO],
) -> None:
    """Guarda la figura como PNG de exactamente 1800 × 1125 px.

    No se usa ``bbox_inches="tight"`` para que todas las imágenes tengan el
    mismo tamaño y la misma proporción.
    """
    figure.savefig(target, format="png", dpi=EXPORT_DPI, facecolor="white")


def wrap_title(title: str) -> str:
    """Parte un título largo en varias líneas para que se vea completo."""
    import textwrap

    # El título empieza en el borde izquierdo del área de trazado: se
    # descuenta el espacio de la etiqueta y los valores del eje Y.
    characters_per_line = int(
        (EXPORT_DESIGN_WIDTH_IN - TITLE_LEFT_RESERVE_IN)
        * 72
        / (FONT_SIZE_TITLE_PT * 0.6)
    )
    return "\n".join(
        textwrap.wrap(title, width=characters_per_line) or [title]
    )
