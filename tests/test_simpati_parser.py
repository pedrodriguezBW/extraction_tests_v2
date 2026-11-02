import math
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from simpati_fixtures import (
    X01_FIXTURE,
    X03_CHANNELS,
    X03_ROWS,
    X04_FIXTURE,
    build_simpati_text,
    copy_fixture,
    write_incompatible,
    write_without_thermal,
    write_x03,
)
from src.report_generator.rendered_assets import list_rendered_assets
from src.report_generator.simpati import (
    STATUS_INCOMPATIBLE,
    STATUS_NO_THERMAL_CHANNELS,
    STATUS_READY,
    SimpatiDecodingError,
    SimpatiFormatError,
    SimpatiPathError,
    acquisition_index,
    analyze_simpati_acquisitions,
    chart_prefix,
    classify_channels,
    decode_simpati_bytes,
    discover_simpati_acquisitions,
    get_temperature_channels,
    parse_chart_name,
    parse_simpati_content,
    read_simpati,
    read_simpati_acquisition,
    resolve_simpati_acquisition,
    thermal_channels,
)


def thermal_mapping(dataframe: pd.DataFrame) -> dict[str, str]:
    return {
        channel.display_label: channel.column
        for channel in thermal_channels(classify_channels(dataframe))
    }


class SimpatiDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.test_root = Path(self.temporary_directory.name)
        self.folder = self.test_root / "03_Data" / "01_SIMPATI"
        self.folder.mkdir(parents=True)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def touch(self, name: str) -> Path:
        path = self.folder / name
        path.write_text("x", encoding="utf-8")
        return path

    def test_every_xnn_is_discovered_in_numeric_order(self):
        for name in ("ensayo.x10", "ensayo.x07", "ensayo.x01", "ensayo.x03", "otro.X02"):
            self.touch(name)

        acquisitions = discover_simpati_acquisitions(self.test_root)

        self.assertEqual(
            [item.name for item in acquisitions],
            ["ensayo.x01", "otro.X02", "ensayo.x03", "ensayo.x07", "ensayo.x10"],
        )
        self.assertEqual([item.index for item in acquisitions], [1, 2, 3, 7, 10])
        self.assertEqual([item.label for item in acquisitions], ["x01", "x02", "x03", "x07", "x10"])
        self.assertEqual(
            acquisitions[0].relative_path,
            "03_Data/01_SIMPATI/ensayo.x01",
        )

    def test_only_x01_to_x99_are_acquisitions(self):
        for name in (
            "a.x00", "a.xABC", "a.txt", "a.csv", "a.x100", "a.x1",
            "a.x03.txt", "~$a.x05", ".hidden.x06", "a.x99",
        ):
            self.touch(name)
        (self.folder / "sub.x08").mkdir()

        self.assertEqual(
            [item.name for item in discover_simpati_acquisitions(self.test_root)],
            ["a.x99"],
        )
        self.assertIsNone(acquisition_index("a.x00"))
        self.assertEqual(acquisition_index("A.X42"), 42)

    def test_missing_folder_is_optional(self):
        self.folder.rmdir()
        self.assertEqual(discover_simpati_acquisitions(self.test_root), [])

    def test_missing_test_folder_is_an_error(self):
        with self.assertRaises(FileNotFoundError):
            discover_simpati_acquisitions(self.test_root / "missing")

    def test_resolution_is_confined_to_the_simpati_folder(self):
        self.touch("ensayo.x04")
        outside = self.test_root / "03_Data" / "02_Graphtec"
        outside.mkdir()
        (outside / "other.x04").write_text("x", encoding="utf-8")
        self.touch("notes.txt")

        resolved = resolve_simpati_acquisition(self.test_root, "03_Data/01_SIMPATI/ensayo.x04")
        self.assertEqual(resolved.index, 4)
        self.assertEqual(
            resolve_simpati_acquisition(self.test_root, "03_Data\\01_SIMPATI\\ensayo.x04").name,
            "ensayo.x04",
        )
        for invalid in (
            "",
            "03_Data/02_Graphtec/other.x04",
            "03_Data/01_SIMPATI/../02_Graphtec/other.x04",
            "03_Data/01_SIMPATI/notes.txt",
            str((self.folder / "ensayo.x04").resolve()),
        ):
            with self.subTest(invalid=invalid), self.assertRaises(SimpatiPathError):
                resolve_simpati_acquisition(self.test_root, invalid)


class SimpatiDecodingTests(unittest.TestCase):
    def setUp(self):
        self.text = build_simpati_text(X03_CHANNELS, X03_ROWS)

    def test_supported_encodings_are_detected_by_structure(self):
        cases = {
            "cp1252": self.text.encode("cp1252"),
            "utf-8-sig": self.text.encode("utf-8"),
            "utf-16": self.text.encode("utf-16"),
        }
        for expected, raw in cases.items():
            with self.subTest(encoding=expected):
                lines, encoding, structure = decode_simpati_bytes(raw)
                self.assertEqual(encoding, expected)
                self.assertEqual(structure.channel_count, len(X03_CHANNELS))
                self.assertIn("°C", lines[structure.units_row])

    def test_utf16_without_bom_is_detected(self):
        _lines, encoding, _structure = decode_simpati_bytes(self.text.encode("utf-16-le"))
        self.assertEqual(encoding, "utf-16-le")

    def test_decoding_does_not_depend_on_known_channels(self):
        channels = [("A:Presión", "[bar  ]"), ("N:Presión", "[bar  ]")]
        rows = [["01.01.2025 00:00:00", "1,0", "2,0"]]
        acquisition = parse_simpati_content(
            build_simpati_text(channels, rows).encode("cp1252")
        )
        self.assertEqual(acquisition.encoding, "cp1252")
        self.assertEqual(acquisition.channel_columns, ["A:Presión [bar]", "N:Presión [bar]"])
        self.assertEqual(thermal_channels(classify_channels(acquisition.dataframe)), [])

    def test_latin1_never_accepts_content_without_structure(self):
        for raw in (
            bytes(range(256)) * 50,
            b"just some text\nwithout separators\n",
            "a;b;c\n1;2;3\n".encode("latin-1"),
        ):
            with self.subTest(raw=raw[:20]), self.assertRaises(SimpatiDecodingError):
                decode_simpati_bytes(raw)

    def test_header_without_units_row_is_rejected(self):
        text = "\n".join([
            ";A:Temperature;N:Temperature;",
            "22.02.2024 14:54:19;65,2;-40,0;",
        ])
        with self.assertRaises(SimpatiFormatError):
            parse_simpati_content(text.encode("cp1252"))

    def test_records_without_numbers_are_rejected(self):
        channels = [("A:Temperature", "[°C   ]")]
        rows = [["22.02.2024 14:54:19", "abc"]]
        with self.assertRaises(SimpatiFormatError):
            parse_simpati_content(build_simpati_text(channels, rows).encode("cp1252"))


class SimpatiStructureTests(unittest.TestCase):
    def parse(self, channels, rows, **kwargs):
        return parse_simpati_content(
            build_simpati_text(channels, rows, **kwargs).encode("cp1252"),
            source_file=Path("test.x05"),
            index=5,
        )

    def test_x03_values_stay_aligned_with_their_channels(self):
        acquisition = self.parse(X03_CHANNELS, X03_ROWS)
        dataframe = acquisition.dataframe

        self.assertEqual(dataframe.columns[0], "Timestamp")
        self.assertEqual(dataframe.columns[1], "A:Pos canasta [Pos]")
        last = dataframe.iloc[-1]
        self.assertEqual(last["A:Pos canasta [Pos]"], 2.0)
        self.assertEqual(last["N:Pos canasta [Pos]"], 2.5)
        self.assertEqual(last["A:Temp canast [°C]"], 40.5)
        self.assertEqual(last["N:Temp canast [°C]"], 90.0)
        self.assertEqual(last["-.Lm:Temp cana [°C]"], -91.0)
        self.assertEqual(last["A:Cam fria [°C]"], -49.9)
        self.assertEqual(list(dataframe.columns[-2:]), ["Reservado", "Reservado_2"])

    def test_header_position_is_detected_without_preamble(self):
        acquisition = self.parse(X03_CHANNELS, X03_ROWS, preamble=False)
        self.assertEqual(acquisition.structure.header_row, 0)
        self.assertEqual(acquisition.records_count, 2)
        self.assertEqual(acquisition.structure.preamble, {})

    def test_preamble_is_kept_as_metadata(self):
        acquisition = self.parse(X03_CHANNELS, X03_ROWS, device="Weiss 748~", program="Aging")
        self.assertEqual(
            acquisition.structure.preamble,
            {
                "device": "Weiss 748",
                "program": "Aging",
                "start": "27.08.2024 15:06:03",
                "start_user": "Admin",
                "stop": "25.09.2024 19:08:55",
                "stop_user": "Admin",
            },
        )

    def test_result_metadata(self):
        dataframe = self.parse(X03_CHANNELS, X03_ROWS).dataframe
        self.assertEqual(dataframe.attrs["source_file"], "test.x05")
        self.assertEqual(dataframe.attrs["encoding"], "cp1252")
        self.assertEqual(dataframe.attrs["acquisition_index"], 5)

    def test_missing_trailing_fields_are_filled_and_extra_fields_rejected(self):
        channels = [("A:Temperature", "[°C   ]"), ("N:Temperature", "[°C   ]"), ("Start", "[]")]
        rows = [
            ["01.03.2024 10:00:00", "20,5", "21,0", "1"],
            ["01.03.2024 10:01:00", "20,6"],
            ["01.03.2024 10:02:00", "20,7", "21,0", "1", "99", "98"],
            ["01.03.2024 10:03:00", "20,8", "", "0", "", ""],
        ]
        acquisition = self.parse(channels, rows)
        dataframe = acquisition.dataframe

        self.assertEqual(acquisition.records_count, 3)
        self.assertEqual(acquisition.rejected_count, 1)
        self.assertIn("3 channels", acquisition.rejected_rows[0])
        self.assertEqual(dataframe["A:Temperature [°C]"].tolist(), [20.5, 20.6, 20.8])
        self.assertTrue(math.isnan(dataframe["N:Temperature [°C]"].iloc[1]))
        self.assertTrue(math.isnan(dataframe["Start"].iloc[1]))
        self.assertNotIn(99.0, dataframe.to_numpy().ravel().tolist())

    def test_records_are_sorted_and_duplicates_keep_the_last_one(self):
        channels = [("A:Temperature", "[°C   ]")]
        rows = [
            ["01.03.2024 10:02:00", "3,0"],
            ["01.03.2024 10:00:00", "1,0"],
            ["01.03.2024 10:01:00", "2,0"],
            ["01.03.2024 10:01:00", "2,5"],
            ["31.02.2024 10:00:00", "9,0"],
            ["not a timestamp", "9,0"],
        ]
        acquisition = self.parse(channels, rows)

        self.assertEqual(acquisition.dataframe["A:Temperature [°C]"].tolist(), [1.0, 2.5, 3.0])
        self.assertEqual(acquisition.duplicate_timestamps, 1)
        self.assertEqual(acquisition.rejected_count, 1)
        self.assertEqual(acquisition.skipped_rows, 1)

    def test_duplicate_and_empty_names_are_stable(self):
        channels = [("A:", "[°C   ]"), ("A:", "[     ]"), ("", "[]"), ("Option", "[]"), ("Option", "[]")]
        rows = [["01.03.2024 10:00:00", "1,0", "2,0", "3", "4", "5"]]
        dataframe = self.parse(channels, rows).dataframe
        self.assertEqual(
            list(dataframe.columns),
            ["Timestamp", "A: [°C]", "A:_2", "Unnamed_03", "Option", "Option_2"],
        )

    def test_without_valid_records_is_rejected(self):
        with self.assertRaises(SimpatiFormatError):
            self.parse([("A:Temperature", "[°C   ]")], [["31.02.2024 10:00:00", "1,0"]])


class SimpatiRealFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x01 = read_simpati_acquisition(X01_FIXTURE)
        cls.x04 = read_simpati_acquisition(X04_FIXTURE)

    def test_x01_climatic_profile(self):
        acquisition = self.x01
        self.assertEqual(acquisition.index, 1)
        self.assertEqual(acquisition.encoding, "cp1252")
        self.assertEqual(acquisition.records_count, 9593)
        self.assertEqual(acquisition.rejected_count, 0)
        self.assertEqual(str(acquisition.start), "2024-02-22 14:54:19")
        self.assertEqual(str(acquisition.end), "2024-02-29 06:53:42")
        self.assertEqual(acquisition.structure.preamble["device"], "Weiss 748")
        self.assertEqual(len(acquisition.channel_columns), 59)
        self.assertEqual(
            thermal_mapping(acquisition.dataframe),
            {
                "Chamber temperature": "A:Temperature [°C]",
                "Chamber setpoint": "N:Temperature [°C]",
                "Supply air temperature": "A:T.SupplyAir [°C]",
                "Return air temperature": "A:T.ReturnAir [°C]",
            },
        )
        last = acquisition.dataframe.iloc[-1]
        self.assertEqual(last["A:Temperature [°C]"], 30.5)
        self.assertEqual(last["N:Temperature [°C]"], 120.0)
        self.assertEqual(last["A:T.SupplyAir [°C]"], 24.7)

    def test_x04_thermal_shock_profile(self):
        acquisition = self.x04
        self.assertEqual(acquisition.index, 4)
        self.assertEqual(acquisition.records_count, 17449)
        self.assertEqual(acquisition.structure.preamble["device"], "VOSTCH TS")
        self.assertEqual(len(acquisition.channel_columns), 86)
        self.assertEqual(
            thermal_mapping(acquisition.dataframe),
            {
                "Basket temperature": "A:Temp. Basket [°C]",
                "Basket setpoint": "N:Temp. Basket [°C]",
                "Hot chamber temperature": "A:Hotchamber [°C]",
                "Hot chamber setpoint": "N:Hotchamber [°C]",
                "Cold chamber temperature": "A:Coldchamber [°C]",
                "Cold chamber setpoint": "N:Coldchamber [°C]",
                "Specimen temperature": "A:Temp. specim [°C]",
            },
        )
        last = acquisition.dataframe.iloc[-1]
        self.assertEqual(last["A:Temp. Basket [°C]"], 23.8)
        self.assertEqual(last["A:Coldchamber [°C]"], 8.1)
        self.assertEqual(last["N:Coldchamber [°C]"], -40.0)

    def test_unrecognized_channels_are_kept(self):
        channels = {channel.column: channel for channel in classify_channels(self.x04.dataframe)}
        self.assertIn("A:Cycles", channels)
        self.assertIsNone(channels["A:Cycles"].role)
        self.assertEqual(channels["A:Cycles"].kind, "actual")
        self.assertIn("C:Operating ho [h]", channels)
        self.assertEqual(channels["C:Operating ho [h]"].kind, "counter")
        self.assertIsNone(channels["Temp. Warmcham"].role)
        self.assertEqual(channels["Temp. Warmcham"].kind, "digital")
        self.assertIsNone(channels["-.Lm:Temp. Bas [°C]"].role)

    def test_temperature_shift_in_kelvin_is_not_a_temperature(self):
        channels = {channel.column: channel for channel in classify_channels(self.x01.dataframe)}
        self.assertIsNone(channels["N:Temp.shift [K]"].role)

    def test_compatibility_helpers(self):
        dataframe = read_simpati(X04_FIXTURE)
        self.assertEqual(dataframe.attrs["acquisition_index"], 4)
        self.assertIn("Basket temperature", get_temperature_channels(dataframe))


class SimpatiHistoricalX03Tests(unittest.TestCase):
    def test_x03_keeps_the_historical_thermal_channels(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_x03(Path(directory) / "acquisition.x03")
            dataframe = read_simpati(path)

        self.assertEqual(
            list(thermal_mapping(dataframe)),
            [
                "Basket temperature",
                "Basket setpoint",
                "Hot chamber temperature",
                "Hot chamber setpoint",
                "Cold chamber temperature",
                "Cold chamber setpoint",
            ],
        )
        self.assertEqual(thermal_mapping(dataframe)["Basket temperature"], "A:Temp canast [°C]")


class SimpatiBatchAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.test_root = Path(self.temporary_directory.name)
        self.folder = self.test_root / "03_Data" / "01_SIMPATI"

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_incompatible_acquisition_does_not_stop_the_others(self):
        copy_fixture(X01_FIXTURE, self.folder, "ensayo.x01")
        write_x03(self.folder / "ensayo.x03")
        write_without_thermal(self.folder / "ensayo.x05")
        write_incompatible(self.folder / "ensayo.x07")
        copy_fixture(X04_FIXTURE, self.folder, "ensayo.x10")

        report = analyze_simpati_acquisitions(self.test_root)

        self.assertEqual(
            [(analysis.file.label, analysis.status) for analysis in report.analyses],
            [
                ("x01", STATUS_READY),
                ("x03", STATUS_READY),
                ("x05", STATUS_NO_THERMAL_CHANNELS),
                ("x07", STATUS_INCOMPATIBLE),
                ("x10", STATUS_READY),
            ],
        )
        self.assertEqual(report.found_count, 5)
        self.assertEqual(report.processed_count, 4)
        self.assertEqual(report.ready_count, 3)
        self.assertEqual(report.without_thermal_count, 1)
        self.assertEqual(report.incompatible_count, 1)
        self.assertIsInstance(report.analyses[3].error, SimpatiDecodingError)


class SimpatiChartNameTests(unittest.TestCase):
    def test_chart_names_identify_the_acquisition(self):
        self.assertEqual(chart_prefix(1), "chart_simpati_x01")
        self.assertEqual(chart_prefix(42), "chart_simpati_x42")
        self.assertEqual(parse_chart_name("chart_simpati_x04_12.png"), (4, 12))
        self.assertIsNone(parse_chart_name("chart03_simpati_acquisition_01.png"))

    def test_charts_of_several_acquisitions_keep_a_stable_order(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as directory:
            test_root = Path(directory)
            assets = test_root / "04_Report" / "_RenderedAssets"
            assets.mkdir(parents=True)
            names = [
                "chart_simpati_x10_01.png",
                "chart_simpati_x04_01.png",
                "chart_simpati_x01_10.png",
                "chart_simpati_x01_02.png",
                "chart_simpati_x01_01.png",
            ]
            for name in names:
                Image.new("RGB", (4, 4), "white").save(assets / name, format="PNG")

            ordered = [asset.name for asset in list_rendered_assets(test_root).assets]

        self.assertEqual(
            ordered,
            [
                "chart_simpati_x01_01.png",
                "chart_simpati_x01_02.png",
                "chart_simpati_x01_10.png",
                "chart_simpati_x04_01.png",
                "chart_simpati_x10_01.png",
            ],
        )



class SimpatiConsoleChartTests(unittest.TestCase):
    def test_console_tool_saves_charts_per_acquisition(self):
        import json

        import matplotlib

        matplotlib.use("Agg")
        from src.report_generator.assets.simpati_extractor import (
            chart_title,
            get_temperature_channels,
            save_current_view,
        )

        with tempfile.TemporaryDirectory() as directory:
            test_root = Path(directory)
            source = write_x03(test_root / "03_Data" / "01_SIMPATI" / "ensayo.x03")
            assets = test_root / "04_Report" / "_RenderedAssets"
            assets.mkdir(parents=True)
            acquisition_file = discover_simpati_acquisitions(test_root)[0]
            dataframe = read_simpati(source)
            channels = get_temperature_channels(dataframe)
            title = chart_title(dataframe, acquisition_file)

            paths = [
                save_current_view(
                    dataframe=dataframe,
                    channels=channels,
                    visible_channels=list(channels),
                    x_limits=(0, 1),
                    y_limits=(-50, 100),
                    output_directory=assets,
                    acquisition_file=acquisition_file,
                    title=title,
                )
                for _ in range(2)
            ]
            metadata = json.loads(paths[0].with_suffix(".json").read_text(encoding="utf-8"))

        self.assertEqual(title, "SIMPATI x03 - ensayo.x03 - Temperature profile")
        self.assertEqual(
            [path.name for path in paths],
            ["chart_simpati_x03_01.png", "chart_simpati_x03_02.png"],
        )
        self.assertEqual(metadata["source"], "simpati")
        self.assertEqual(metadata["source_file"], "ensayo.x03")
        self.assertEqual(metadata["acquisition_index"], 3)


class SimpatiReportSubtitleTests(unittest.TestCase):
    def test_subtitle_names_each_source_acquisition_in_order(self):
        import json

        from PIL import Image

        from src.report_generator.sections.test_results import _result_images_subtitle

        with tempfile.TemporaryDirectory() as directory:
            assets = Path(directory)
            paths = []
            for name, metadata in (
                ("chart_simpati_x01_01.png", {"source": "simpati", "acquisition_label": "x01"}),
                ("chart_simpati_x01_02.png", {"source": "simpati", "acquisition_label": "x01"}),
                ("chart_simpati_x04_01.png", {"source": "simpati", "acquisition_label": "x04"}),
                ("chart03_simpati_acquisition_01.png", {"source": "simpati"}),
                ("graphtec_chart_01.png", {"source": "graphtec"}),
            ):
                path = assets / name
                Image.new("RGB", (4, 4), "white").save(path, format="PNG")
                path.with_suffix(".json").write_text(json.dumps(metadata), encoding="utf-8")
                paths.append(path)

            subtitle = _result_images_subtitle(paths)

        self.assertEqual(
            subtitle,
            "SIMPATI acquisition x01 | SIMPATI acquisition x04 | "
            "SIMPATI acquisition | Graphtec acquisition",
        )


if __name__ == "__main__":
    unittest.main()
