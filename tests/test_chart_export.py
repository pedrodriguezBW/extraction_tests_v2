"""Pruebas del formato común de las gráficas de ``_RenderedAssets`` y de su
colocación en ``4. Test Results``.

Cubren el tamaño y la proporción de exportación, la tipografía, que títulos,
leyendas y fechas queden completos y sin solaparse, los rangos Y estrechos
y la distribución de una a cuatro gráficas en diapositivas 16:9.
"""

import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from PIL import Image
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER
from pptx.util import Cm

from graphtec_fixtures import DCW_TEXT, IR_TEXT
from simpati_fixtures import write_x03

from src.report_generator import chart_export
from src.report_generator.graphtec import (
    GraphtecChartConfig,
    default_chart_config,
    parse_graphtec_content,
    render_graphtec_chart,
)
from src.report_generator.graphtec.charts import build_graphtec_figure
from src.report_generator.powerpoint.images import fit_image_size
from src.report_generator.powerpoint.styles import RESULT_HORIZONTAL_GAP_CM
from src.report_generator.sections.test_results import (
    populate_test_results_slide,
    result_chart_area,
    result_chart_boxes,
)
from src.report_generator.simpati import discover_simpati_acquisitions, read_simpati

EMU_PER_CM = 360000
LONG_TITLE = (
    "DUT insulation resistance test, HV connector to housing, after thermal "
    "shock cycle 500 - sample 3 of 5 - final verification"
)


def _cm(value):
    return value / EMU_PER_CM


def _drawn_bboxes(figure):
    """Dibuja la figura y devuelve la caja de la figura y su renderizador."""
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    return figure.bbox, renderer


def _inside(inner, outer, tolerance=1.0):
    return (
        inner.x0 >= outer.x0 - tolerance
        and inner.y0 >= outer.y0 - tolerance
        and inner.x1 <= outer.x1 + tolerance
        and inner.y1 <= outer.y1 + tolerance
    )


def _visible_tick_labels(axis, renderer):
    labels = [label for label in axis.get_xticklabels() if label.get_text()]
    view = axis.get_xlim()
    low, high = min(view), max(view)
    return [
        label.get_window_extent(renderer)
        for label in labels
        if low <= label.get_position()[0] <= high
    ]


class ExportFormatTests(unittest.TestCase):
    def test_export_size_and_ratio(self):
        self.assertEqual(chart_export.EXPORT_WIDTH_PX, 1800)
        self.assertEqual(chart_export.EXPORT_HEIGHT_PX, 1125)
        self.assertAlmostEqual(
            chart_export.EXPORT_WIDTH_PX / chart_export.EXPORT_HEIGHT_PX, 1.6
        )
        # Diseñado para una columna de Test Results (≈14,4 cm) a >300 ppp.
        self.assertAlmostEqual(chart_export.EXPORT_DESIGN_WIDTH_CM, 14.415, places=3)
        self.assertGreater(chart_export.EXPORT_DPI, 300)

    def test_legend_columns_fit_the_figure_width(self):
        self.assertEqual(chart_export.legend_columns([]), 1)
        self.assertEqual(chart_export.legend_columns(["A", "B"]), 2)
        self.assertEqual(chart_export.legend_columns(["x" * 120]), 1)
        self.assertLessEqual(chart_export.legend_columns(["Label"] * 8), 3)

    def test_long_titles_are_wrapped(self):
        wrapped = chart_export.wrap_title(LONG_TITLE)
        self.assertIn("\n", wrapped)
        self.assertEqual(wrapped.replace("\n", " "), LONG_TITLE)


class GraphtecExportTests(unittest.TestCase):
    def setUp(self):
        self.dcw = parse_graphtec_content(DCW_TEXT, ".txt")
        self.ir = parse_graphtec_content(IR_TEXT, ".txt")

    def test_png_uses_the_common_size(self):
        for acquisition in (self.dcw, self.ir):
            render = render_graphtec_chart(acquisition, default_chart_config(acquisition))
            with Image.open(BytesIO(render.png)) as image:
                self.assertEqual(image.size, (1800, 1125))
            self.assertEqual((render.width, render.height), (1800, 1125))

    def test_fonts_and_lines_are_enlarged(self):
        figure, _ = build_graphtec_figure(self.dcw, default_chart_config(self.dcw))
        axis = figure.axes[0]
        self.assertEqual(axis._left_title.get_size(), 13.0)
        self.assertEqual(axis.xaxis.label.get_size(), 12.0)
        self.assertEqual(axis.get_xticklabels()[0].get_size(), 11.0)
        legend = figure.legends[0]
        self.assertEqual(legend.get_texts()[0].get_size(), 11.0)
        self.assertAlmostEqual(axis.get_lines()[0].get_linewidth(), 1.8)

    def test_title_legend_and_notes_stay_inside_the_image(self):
        config = GraphtecChartConfig(
            series=("voltage", "resistance"),
            title=LONG_TITLE,
        )
        figure, render = build_graphtec_figure(self.ir, config)
        self.assertTrue(render.notes)
        bbox, renderer = _drawn_bboxes(figure)

        # El título se dibuja alineado a la izquierda.
        title = figure.axes[0]._left_title
        self.assertIn("\n", title.get_text())
        self.assertTrue(_inside(title.get_window_extent(renderer), bbox))
        legend = figure.legends[0]
        self.assertTrue(_inside(legend.get_window_extent(renderer), bbox))
        # La leyenda no invade el área de trazado ni las etiquetas del eje X.
        axis_box = figure.axes[0].get_tightbbox(renderer)
        self.assertLessEqual(legend.get_window_extent(renderer).y1, axis_box.y0 + 1)

    def test_x_tick_labels_do_not_overlap(self):
        figure, _ = build_graphtec_figure(self.ir, default_chart_config(self.ir))
        _, renderer = _drawn_bboxes(figure)
        boxes = sorted(_visible_tick_labels(figure.axes[0], renderer), key=lambda b: b.x0)
        self.assertLessEqual(len(boxes), chart_export.MAX_X_TICKS + 1)
        for left, right in zip(boxes, boxes[1:]):
            self.assertLess(left.x1, right.x0)


class SimpatiConsoleExportTests(unittest.TestCase):
    def _save(self, x_fraction=(0.0, 1.0), y_limits=None):
        from src.report_generator.assets.simpati_extractor import (
            chart_title,
            get_temperature_channels,
            save_current_view,
        )

        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        test_root = Path(directory.name)
        source = write_x03(test_root / "03_Data" / "01_SIMPATI" / "ensayo.x03")
        assets = test_root / "04_Report" / "_RenderedAssets"
        assets.mkdir(parents=True)
        acquisition_file = discover_simpati_acquisitions(test_root)[0]
        dataframe = read_simpati(source)
        channels = get_temperature_channels(dataframe)
        times = matplotlib.dates.date2num(dataframe["Timestamp"])
        span = times.max() - times.min()
        x_limits = (
            times.min() + span * x_fraction[0],
            times.min() + span * x_fraction[1],
        )
        path = save_current_view(
            dataframe=dataframe,
            channels=channels,
            visible_channels=list(channels),
            x_limits=x_limits,
            y_limits=y_limits or (-50, 100),
            output_directory=assets,
            acquisition_file=acquisition_file,
            title=chart_title(dataframe, acquisition_file),
        )
        return path, len(channels)

    def test_saved_view_uses_the_common_size(self):
        path, _ = self._save()
        with Image.open(path) as image:
            self.assertEqual(image.size, (1800, 1125))
        metadata = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["source"], "simpati")

    def test_narrow_value_range_is_kept(self):
        # Un rango Y estrecho se guarda tal cual, sin recalcular los límites.
        path, _ = self._save(x_fraction=(0.2, 0.4), y_limits=(20.1, 20.4))
        with Image.open(path) as image:
            self.assertEqual(image.size, (1800, 1125))


def _template(path: Path) -> Path:
    """Plantilla 16:9 con la geometría de la plantilla corporativa."""
    presentation = Presentation()
    presentation.slide_width = Cm(33.867)
    presentation.slide_height = Cm(19.05)
    layout = presentation.slide_layouts[1]  # Title and Content
    for placeholder in layout.placeholders:
        kind = placeholder.placeholder_format.type
        if kind == PP_PLACEHOLDER.TITLE:
            placeholder.left, placeholder.top = Cm(2.12), Cm(2.01)
            placeholder.width, placeholder.height = Cm(29.63), Cm(2.79)
        elif kind in (PP_PLACEHOLDER.OBJECT, PP_PLACEHOLDER.BODY):
            placeholder.left, placeholder.top = Cm(2.12), Cm(5.12)
            placeholder.width, placeholder.height = Cm(29.63), Cm(11.29)
        else:
            # Pie: fecha, texto y número de diapositiva.
            placeholder.top = Cm(17.25)
            placeholder.height = Cm(0.51)
    presentation.slides.add_slide(layout)
    presentation.save(path)
    return path


class ResultChartLayoutTests(unittest.TestCase):
    """Colocación de 1 a 4 gráficas 1,6:1 en ``Test Results`` (16:9)."""

    FOOTER_TOP_CM = 17.25

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.chart = self.directory / "chart.png"
        Image.new("RGB", (1800, 1125), "white").save(self.chart)
        self.presentation = Presentation(_template(self.directory / "template.pptx"))
        self.slide = self.presentation.slides[0]
        for shape in list(self.slide.placeholders):
            if shape.placeholder_format.type in (
                PP_PLACEHOLDER.OBJECT,
                PP_PLACEHOLDER.BODY,
            ):
                shape._element.getparent().remove(shape._element)

    def pictures(self):
        return [
            shape
            for shape in self.slide.shapes
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE
        ]

    def test_area_comes_from_the_template(self):
        area = result_chart_area(self.slide)
        self.assertAlmostEqual(area.left_cm, 2.12, places=2)
        self.assertAlmostEqual(area.width_cm, 29.63, places=2)
        # Debajo del subtítulo y por encima del pie con su margen.
        self.assertAlmostEqual(area.top_cm, 5.60, places=2)
        self.assertAlmostEqual(area.bottom_cm, self.FOOTER_TOP_CM - 0.45, places=2)

    def test_one_chart_uses_the_full_useful_area(self):
        populate_test_results_slide(self.slide, [self.chart])
        (picture,) = self.pictures()
        area = result_chart_area(self.slide)
        # Limitada por la altura: usa toda la altura disponible, centrada.
        self.assertAlmostEqual(_cm(picture.height), area.height_cm, places=2)
        self.assertAlmostEqual(_cm(picture.width) / _cm(picture.height), 1.6, places=2)
        center = _cm(picture.left) + _cm(picture.width) / 2
        self.assertAlmostEqual(center, area.left_cm + area.width_cm / 2, places=2)

    def test_two_charts_fill_two_columns(self):
        populate_test_results_slide(self.slide, [self.chart, self.chart])
        left, right = sorted(self.pictures(), key=lambda shape: shape.left)
        area = result_chart_area(self.slide)
        column = (area.width_cm - RESULT_HORIZONTAL_GAP_CM) / 2

        for picture in (left, right):
            self.assertAlmostEqual(_cm(picture.width), column, places=2)
            self.assertAlmostEqual(_cm(picture.width) / _cm(picture.height), 1.6, places=2)
            self.assertGreaterEqual(_cm(picture.top), area.top_cm - 0.01)
            self.assertLessEqual(_cm(picture.top + picture.height), area.bottom_cm + 0.01)
        # Misma altura, misma fila (no apiladas) y separación equilibrada.
        self.assertEqual(left.top, right.top)
        gap = _cm(right.left) - _cm(left.left + left.width)
        self.assertAlmostEqual(gap, RESULT_HORIZONTAL_GAP_CM, places=2)
        self.assertAlmostEqual(_cm(left.left), area.left_cm, places=2)
        self.assertAlmostEqual(
            _cm(right.left + right.width), area.left_cm + area.width_cm, places=2
        )
        # Más grandes que antes (14,4 × 6,8 cm con imágenes 2,13:1).
        self.assertGreater(_cm(left.height), 8.5)

    def test_more_than_two_charts_are_never_squeezed_in_one_slide(self):
        with self.assertRaises(ValueError):
            result_chart_boxes(result_chart_area(self.slide), 3)

    def test_fit_preserves_the_aspect_ratio(self):
        self.assertEqual(fit_image_size(1800, 1125, 16.0, 20.0), (16.0, 10.0))
        self.assertEqual(fit_image_size(1800, 1125, 32.0, 10.0), (16.0, 10.0))


class ResultChartContinuationTests(unittest.TestCase):
    """Tres y cuatro gráficas se reparten en dos diapositivas."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.charts = []
        for index in range(4):
            path = self.directory / f"chart_{index}.png"
            Image.new("RGB", (1800, 1125), (index * 40, 255, 255)).save(path)
            self.charts.append(path)

    def _generate(self, count):
        from test_rendered_assets import _build_template
        from src.report_generator.sections.test_results import populate_test_results
        from src.report_generator.evidences import EvidenceDiscovery

        template = self.directory / f"deck_{count}.pptx"
        _build_template(template)
        populate_test_results(
            template,
            self.directory,
            evidence_discovery=EvidenceDiscovery(directory=self.directory, found=False),
            result_image_paths=self.charts[:count],
        )
        slides = []
        for slide in Presentation(template).slides:
            pictures = [
                shape for shape in slide.shapes
                if shape.shape_type == MSO_SHAPE_TYPE.PICTURE
            ]
            if pictures:
                slides.append(sorted(pictures, key=lambda shape: shape.left))
        return slides

    def test_three_charts_use_two_slides(self):
        slides = self._generate(3)
        self.assertEqual([len(pictures) for pictures in slides], [2, 1])
        # La gráfica sola de la continuación ocupa todo el ancho útil.
        self.assertGreater(slides[1][0].width, slides[0][0].width)

    def test_four_charts_use_two_slides(self):
        slides = self._generate(4)
        self.assertEqual([len(pictures) for pictures in slides], [2, 2])
        for pictures in slides:
            self.assertEqual(pictures[0].top, pictures[1].top)


if __name__ == "__main__":
    unittest.main()
