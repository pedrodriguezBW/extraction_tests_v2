"""Tests for Graphtec chart rendering and saved Graphtec charts."""

import base64
import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from PIL import Image

from graphtec_fixtures import (
    ARBITRARY_NAMES,
    DCW_TEXT,
    IR_TEXT,
    write_graphtec_file,
)
from project_fixtures import build_test_folder

from backend.app.models.graphtec import GraphtecChartSettings
from backend.app.services.graphtec_inspection import (
    GraphtecServiceError,
    save_project_graphtec_chart,
)
from backend.app.services.rendered_assets import (
    RenderedAssetServiceError,
    delete_project_rendered_asset,
    list_project_rendered_assets,
)
from backend.app.services.simpati_inspection import save_project_simpati_chart
from src.report_generator.graphtec import (
    GraphtecChartConfig,
    GraphtecChartConfigError,
    available_series,
    default_chart_config,
    parse_graphtec_content,
    read_graphtec_file,
    render_graphtec_chart,
)
from src.report_generator.graphtec.charts import build_graphtec_figure
from src.report_generator.rendered_assets import list_rendered_assets


def acquisition(text):
    return parse_graphtec_content(text, ".txt")


def config(**values):
    values.setdefault("title", "")
    return GraphtecChartConfig(**values)


def y_labels(figure):
    return [axis.get_ylabel() for axis in figure.axes if axis.get_ylabel()]


class GraphtecChartTests(unittest.TestCase):
    def setUp(self):
        self.dcw = acquisition(DCW_TEXT)
        self.ir = acquisition(IR_TEXT)

    def test_available_series(self):
        self.assertEqual(
            [(s.id, s.unit, s.axis) for s in available_series(self.dcw)],
            [("voltage", "kV", "left"), ("current", "uA", "right")],
        )
        self.assertEqual(
            [(s.id, s.unit, s.axis) for s in available_series(self.ir)],
            [("voltage", "kV", "left"), ("resistance", "Mohm", "right")],
        )

    def test_default_configuration(self):
        dcw = default_chart_config(self.dcw)
        ir = default_chart_config(self.ir)

        self.assertEqual(dcw.series, ("voltage", "current"))
        self.assertEqual(ir.series, ("voltage", "resistance"))
        self.assertTrue(dcw.show_legend)
        self.assertIsNone(dcw.time_min)
        self.assertIsNone(dcw.time_max)
        self.assertEqual(dcw.title, "Graphtec DCW - Channel 1")

    def test_dcw_chart_with_voltage_and_current(self):
        figure, render = build_graphtec_figure(self.dcw, default_chart_config(self.dcw))

        self.assertEqual([s.id for s in render.series], ["voltage", "current"])
        self.assertEqual(
            [(a.position, a.label) for a in render.axes],
            [("left", "Voltage [kV]"), ("right", "Current [uA]")],
        )
        self.assertEqual(y_labels(figure), ["Voltage [kV]", "Current [uA]"])

    def test_ir_chart_with_voltage_and_resistance(self):
        figure, render = build_graphtec_figure(self.ir, default_chart_config(self.ir))

        self.assertEqual(
            [(a.position, a.label) for a in render.axes],
            [("left", "Voltage [kV]"), ("right", "Resistance [Mohm]")],
        )
        self.assertEqual(y_labels(figure), ["Voltage [kV]", "Resistance [Mohm]"])

    def test_current_and_resistance_never_share_a_chart(self):
        with self.assertRaises(GraphtecChartConfigError):
            build_graphtec_figure(self.dcw, config(series=("voltage", "resistance")))
        with self.assertRaises(GraphtecChartConfigError):
            build_graphtec_figure(self.ir, config(series=("current",)))

    def test_x_axis_is_elapsed_time(self):
        figure, render = build_graphtec_figure(self.dcw, default_chart_config(self.dcw))

        self.assertEqual(figure.axes[0].get_xlabel(), "Elapsed time [s]")
        line = figure.axes[0].lines[0]
        self.assertEqual(
            list(line.get_xdata()),
            [r.elapsed_time_seconds for r in self.dcw.records if r.status == "TEST"],
        )

    def test_two_y_axes_for_two_quantities(self):
        figure, _ = build_graphtec_figure(self.ir, default_chart_config(self.ir))

        self.assertEqual(len(figure.axes), 2)

    def test_single_axis_for_a_single_series(self):
        for series in ("voltage", "resistance"):
            figure, render = build_graphtec_figure(self.ir, config(series=(series,)))
            self.assertEqual(len(figure.axes), 1, series)
            self.assertEqual(len(render.axes), 1)
            self.assertEqual(render.axes[0].position, "left")

        _, render = build_graphtec_figure(self.ir, config(series=("resistance",)))
        self.assertEqual(render.axes[0].label, "Resistance [Mohm]")

    def test_full_time_range(self):
        figure, render = build_graphtec_figure(self.dcw, default_chart_config(self.dcw))

        self.assertTrue(render.full_range)
        self.assertEqual((render.time_start, render.time_end), (0.0, 12.9))
        self.assertEqual(render.records_plotted, len(self.dcw.records))
        left, right = figure.axes[0].get_xlim()
        self.assertLess(left, 0.0)
        self.assertGreater(right, 12.9)

    def test_cropped_time_range(self):
        figure, render = build_graphtec_figure(
            self.dcw, config(series=("voltage",), time_min=5.0, time_max=8.1)
        )

        self.assertFalse(render.full_range)
        self.assertEqual((render.time_start, render.time_end), (5.0, 8.1))
        xs = list(figure.axes[0].lines[0].get_xdata())
        self.assertEqual(xs, [5.0, 5.3, 7.9, 8.1])

    def test_invalid_time_ranges(self):
        for time_min, time_max in ((5.0, 5.0), (8.0, 2.0), (-1.0, None), (None, float("nan")), (100.0, 200.0)):
            with self.assertRaises(GraphtecChartConfigError, msg=(time_min, time_max)):
                build_graphtec_figure(
                    self.dcw, config(series=("voltage",), time_min=time_min, time_max=time_max)
                )

    def test_value_ranges_fix_each_y_axis(self):
        figure, render = build_graphtec_figure(
            self.ir,
            config(
                series=("voltage", "resistance"),
                value_ranges=(("voltage", 0.2, 0.6), ("resistance", 10.0, 900.0)),
            ),
        )

        self.assertEqual(figure.axes[0].get_ylim(), (0.2, 0.6))
        self.assertEqual(figure.axes[1].get_ylim(), (10.0, 900.0))
        self.assertEqual(
            render.value_ranges,
            (("voltage", 0.2, 0.6), ("resistance", 10.0, 900.0)),
        )

    def test_value_range_of_a_single_series_uses_the_left_axis(self):
        figure, _ = build_graphtec_figure(
            self.ir,
            config(series=("resistance",), value_ranges=(("resistance", 5.0, 50.0),)),
        )

        self.assertEqual(figure.axes[0].get_ylim(), (5.0, 50.0))

    def test_value_ranges_are_optional_and_ordered_by_series(self):
        figure, render = build_graphtec_figure(
            self.ir,
            config(
                series=("voltage", "resistance"),
                value_ranges=(("resistance", 1.0, 2.0),),
            ),
        )

        self.assertEqual(render.value_ranges, (("resistance", 1.0, 2.0),))
        self.assertEqual(figure.axes[1].get_ylim(), (1.0, 2.0))
        self.assertNotEqual(figure.axes[0].get_ylim(), (1.0, 2.0))

    def test_invalid_value_ranges(self):
        for ranges in (
            (("current", 0.0, 1.0),),
            (("voltage", 1.0, 1.0),),
            (("voltage", 2.0, 1.0),),
            (("voltage", float("nan"), 1.0),),
            (("voltage", 0.0, float("inf")),),
            (("voltage", 0.0, 1.0), ("voltage", 0.0, 2.0)),
            (("voltage", "x", 1.0),),
        ):
            with self.assertRaises(GraphtecChartConfigError, msg=ranges):
                build_graphtec_figure(
                    self.ir, config(series=("voltage",), value_ranges=ranges)
                )

    def test_invalid_series_configuration(self):
        for series in ((), ("temperature",)):
            with self.assertRaises(GraphtecChartConfigError):
                build_graphtec_figure(self.dcw, config(series=series))
        with self.assertRaises(GraphtecChartConfigError):
            build_graphtec_figure(self.dcw, config(series=("voltage",), title="x" * 201))

    def test_excluding_a_series(self):
        figure, render = build_graphtec_figure(self.dcw, config(series=("current",)))

        self.assertEqual([s.id for s in render.series], ["current"])
        self.assertEqual(y_labels(figure), ["Current [uA]"])
        labels = [line.get_label() for line in figure.axes[0].lines]
        self.assertFalse(any(label.startswith("Voltage") for label in labels))

    def test_limited_values_use_a_special_marker(self):
        figure, render = build_graphtec_figure(self.ir, default_chart_config(self.ir))

        self.assertEqual(render.limited_points, 3)
        self.assertEqual(
            render.notes,
            ["Limit marker indicates a value greater than the displayed threshold."],
        )
        resistance_axis = figure.axes[1]
        limit_lines = [l for l in resistance_axis.lines if "limit" in l.get_label()]
        self.assertEqual(len(limit_lines), 1)
        limit = limit_lines[0]
        self.assertEqual(limit.get_marker(), "^")
        self.assertEqual(limit.get_linestyle(), "None")
        self.assertEqual(list(limit.get_ydata()), [50000.0, 50000.0, 20000.0])

        measured = next(l for l in resistance_axis.lines if l.get_label() == "Resistance [Mohm]")
        ys = list(measured.get_ydata())
        self.assertNotIn(50000.0, ys)
        self.assertNotIn(20000.0, ys)
        self.assertTrue(any(y != y for y in ys))  # NaN breaks the measured line

        # La nota se muestra con la leyenda, debajo de la gráfica.
        notes = figure.legends[0].get_title().get_text()
        self.assertIn(
            "Limit marker indicates a value greater than the displayed threshold.",
            notes.replace("\n", " "),
        )

    def test_limit_note_only_when_resistance_is_drawn(self):
        _, render = build_graphtec_figure(self.ir, config(series=("voltage",)))

        self.assertEqual(render.limited_points, 0)
        self.assertEqual(render.notes, [])

    def test_result_records_are_separate_markers(self):
        figure, render = build_graphtec_figure(self.dcw, default_chart_config(self.dcw))

        self.assertEqual(render.result_points, 1)
        markers = [l for l in figure.axes[0].lines if "PASS record" in l.get_label()]
        self.assertEqual(len(markers), 1)
        self.assertEqual(list(markers[0].get_xdata()), [12.9])
        voltage = figure.axes[0].lines[0]
        self.assertNotIn(12.9, list(voltage.get_xdata()))

    def test_phase_separators(self):
        figure, render = build_graphtec_figure(self.dcw, default_chart_config(self.dcw))

        self.assertEqual(
            [(m.phase, m.elapsed_time_seconds) for m in render.phase_markers],
            [("I", 0.0), ("R", 0.1), ("T", 5.0), ("D", 8.1)],
        )
        labels = [t.get_text().strip() for t in figure.axes[0].texts]
        self.assertEqual(labels, ["I", "R", "T", "D"])
        vertical = [l for l in figure.axes[0].lines if list(l.get_xdata()) in ([0.1, 0.1], [5.0, 5.0], [8.1, 8.1])]
        self.assertEqual(len(vertical), 3)

    def test_phase_separators_can_be_hidden(self):
        figure, render = build_graphtec_figure(
            self.dcw, config(series=("voltage",), show_phase_separators=False)
        )

        self.assertEqual(render.phase_markers, [])
        self.assertEqual(len(figure.axes[0].texts), 0)

    def test_legend_toggle_and_title(self):
        # La leyenda es de la figura (debajo de la gráfica) para que el
        # diseño ajustado reserve su espacio y se vea completa.
        figure, _ = build_graphtec_figure(self.dcw, config(series=("voltage",), title="My chart"))
        self.assertEqual(len(figure.legends), 1)
        self.assertEqual(figure.axes[0].get_title(loc="left"), "My chart")

        figure, _ = build_graphtec_figure(
            self.dcw, config(series=("voltage",), show_legend=False)
        )
        self.assertEqual(figure.legends, [])
        self.assertEqual(figure.axes[0].get_title(loc="left"), "Graphtec DCW - Channel 1")

    def test_png_is_valid_and_not_empty(self):
        render = render_graphtec_chart(self.ir, default_chart_config(self.ir))

        self.assertGreater(len(render.png), 1000)
        with Image.open(BytesIO(render.png)) as image:
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.size, (render.width, render.height))
            colors = image.convert("L").getextrema()
            self.assertNotEqual(colors[0], colors[1])


class GraphtecSavedChartTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.test_root = build_test_folder(Path(self.temporary_directory.name) / "TEST - 001")
        self.source = write_graphtec_file(self.test_root, "measurement.txt", IR_TEXT)
        self.relative_path = "03_Data/02_Graphtec/measurement.txt"
        self.assets = self.test_root / "04_Report" / "_RenderedAssets"

    def tearDown(self):
        self.temporary_directory.cleanup()

    def save(self, **chart):
        chart.setdefault("series", ["voltage", "resistance"])
        return save_project_graphtec_chart(
            self.test_root, self.relative_path, GraphtecChartSettings(**chart)
        )

    def test_chart_is_saved_in_rendered_assets_with_metadata(self):
        original = self.source.read_bytes()
        response = self.save(time_min=1.0, time_max=9.0, title="Insulation")

        self.assertTrue(response.success)
        self.assertEqual(response.chart_name, "graphtec_chart_01.png")
        chart_path = Path(response.chart_path)
        self.assertEqual(chart_path.parent, self.assets.resolve())
        with Image.open(chart_path) as image:
            self.assertEqual(image.format, "PNG")

        metadata = json.loads((self.assets / "graphtec_chart_01.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["source"], "graphtec")
        self.assertEqual(metadata["source_file"]["relative_path"], self.relative_path)
        self.assertEqual(metadata["test_type"], "IR")
        self.assertEqual([s["id"] for s in metadata["series"]], ["voltage", "resistance"])
        self.assertEqual(metadata["units"], {"voltage": "kV", "resistance": "Mohm", "elapsed_time_seconds": "s"})
        self.assertEqual(metadata["time_range"]["start"], 1.0)
        self.assertEqual(metadata["time_range"]["end"], 9.0)
        self.assertNotIn("included_in_powerpoint", metadata)
        self.assertEqual(
            response.relative_path, "04_Report/_RenderedAssets/graphtec_chart_01.png"
        )
        self.assertEqual(self.source.read_bytes(), original)

    def test_saved_chart_reproduces_the_zoomed_view(self):
        response = self.save(
            time_min=2.0,
            time_max=6.0,
            value_ranges={
                "voltage": {"minimum": 0.1, "maximum": 0.9},
                "resistance": {"minimum": 100.0, "maximum": 2000.0},
            },
        )

        self.assertTrue(response.success)
        metadata = json.loads((self.assets / "graphtec_chart_01.json").read_text(encoding="utf-8"))
        self.assertEqual(
            metadata["value_ranges"],
            {
                "voltage": {"minimum": 0.1, "maximum": 0.9},
                "resistance": {"minimum": 100.0, "maximum": 2000.0},
            },
        )
        self.assertEqual(metadata["time_range"]["start"], 2.0)
        self.assertEqual(metadata["time_range"]["end"], 6.0)

    def test_saving_without_value_ranges_keeps_the_automatic_range(self):
        self.save()

        metadata = json.loads((self.assets / "graphtec_chart_01.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["value_ranges"], {})

    def test_chart_name_does_not_use_the_source_name(self):
        write_graphtec_file(self.test_root, "IR_PASS_TC9.txt", IR_TEXT)
        response = save_project_graphtec_chart(
            self.test_root,
            "03_Data/02_Graphtec/IR_PASS_TC9.txt",
            GraphtecChartSettings(series=["voltage"]),
        )

        self.assertEqual(response.chart_name, "graphtec_chart_01.png")
        self.assertNotIn("TC9", response.chart_name)

    def test_saving_never_overwrites(self):
        first = self.save()
        first_bytes = Path(first.chart_path).read_bytes()
        second = self.save(series=["voltage"])

        self.assertEqual(second.chart_name, "graphtec_chart_02.png")
        self.assertEqual(Path(first.chart_path).read_bytes(), first_bytes)
        self.assertEqual(second.assets_count, 2)

    def test_existing_unrelated_files_are_not_overwritten(self):
        self.assets.mkdir(parents=True)
        (self.assets / "graphtec_chart_01.json").write_text("{}", encoding="utf-8")
        (self.assets / "chart03_simpati_acquisition_01.png").write_bytes(b"simpati")

        response = self.save()

        self.assertEqual(response.chart_name, "graphtec_chart_02.png")
        self.assertEqual((self.assets / "graphtec_chart_01.json").read_text(encoding="utf-8"), "{}")
        self.assertEqual((self.assets / "chart03_simpati_acquisition_01.png").read_bytes(), b"simpati")

    def test_saved_charts_are_listed_and_deleted_with_metadata(self):
        self.save()
        self.save(series=["voltage"])

        listing = list_project_rendered_assets(self.test_root)
        self.assertEqual(
            [(a.name, a.source, a.metadata_name) for a in listing.assets],
            [
                ("graphtec_chart_01.png", "graphtec", "graphtec_chart_01.json"),
                ("graphtec_chart_02.png", "graphtec", "graphtec_chart_02.json"),
            ],
        )

        response = delete_project_rendered_asset(
            self.test_root, "04_Report/_RenderedAssets/graphtec_chart_01.png"
        )
        self.assertEqual(response.assets_count, 1)
        self.assertFalse((self.assets / "graphtec_chart_01.png").exists())
        self.assertFalse((self.assets / "graphtec_chart_01.json").exists())

    def test_delete_rejects_invalid_paths(self):
        self.assets.mkdir(parents=True)
        (self.assets / "chart03_simpati_acquisition_01.png").write_bytes(b"x")
        for path in (
            "04_Report/_RenderedAssets/chart03_simpati_acquisition_01.png",  # not an image
            "04_Report/_RenderedAssets/../test_metadata.json",
            "04_Report/_RenderedAssets/missing.png",
            "04_Report/test_metadata.json",
        ):
            with self.assertRaises(RenderedAssetServiceError, msg=path):
                delete_project_rendered_asset(self.test_root, path)
        self.assertTrue((self.assets / "chart03_simpati_acquisition_01.png").exists())
        self.assertTrue((self.test_root / "04_Report" / "test_metadata.json").exists())

    def test_graphtec_charts_are_selectable_for_the_powerpoint(self):
        self.save()

        assets = list_rendered_assets(self.test_root).assets
        self.assertEqual([(a.name, a.source) for a in assets], [("graphtec_chart_01.png", "graphtec")])

    def test_simpati_and_graphtec_charts_share_the_inventory(self):
        buffer = BytesIO()
        Image.new("RGB", (8, 6), "white").save(buffer, format="PNG")
        image = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")

        acquisition = self.test_root / "03_Data" / "01_SIMPATI" / "acquisition.x03"
        acquisition.write_text("SIMPATI", encoding="utf-8")

        self.save()
        simpati = save_project_simpati_chart(
            self.test_root, "03_Data/01_SIMPATI/acquisition.x03", image
        )
        graphtec = self.save(series=["voltage"])

        self.assertEqual(simpati.chart_name, "chart_simpati_x03_01.png")
        self.assertEqual(
            [(a.name, a.source) for a in graphtec.assets],
            [
                ("chart_simpati_x03_01.png", "simpati"),
                ("graphtec_chart_01.png", "graphtec"),
                ("graphtec_chart_02.png", "graphtec"),
            ],
        )
        self.assertEqual(
            [a.name for a in list_project_rendered_assets(self.test_root).assets],
            [a.name for a in graphtec.assets],
        )

    def test_saving_requires_04_report(self):
        report = self.test_root / "04_Report"
        (report / "test_metadata.json").unlink()
        report.rmdir()

        with self.assertRaises(GraphtecServiceError) as context:
            self.save()
        self.assertEqual(context.exception.status_code, 400)
        self.assertFalse(report.exists())

    def test_chart_does_not_depend_on_the_file_name(self):
        renders = []
        for name in ARBITRARY_NAMES:
            path = write_graphtec_file(self.test_root, name, DCW_TEXT)
            data = read_graphtec_file(path)
            figure, render = build_graphtec_figure(data, default_chart_config(data))
            renders.append(
                (
                    render.title,
                    [a.label for a in render.axes],
                    render.phase_markers,
                    list(figure.axes[0].lines[0].get_ydata()),
                )
            )
        for render in renders[1:]:
            self.assertEqual(render, renders[0])
        self.assertEqual(renders[0][0], "Graphtec DCW - Channel 1")

if __name__ == "__main__":
    unittest.main()
