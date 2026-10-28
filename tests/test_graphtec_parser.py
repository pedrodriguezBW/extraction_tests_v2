"""Tests for the tab-separated Graphtec TXT parser and the elapsed time."""

import tempfile
import unittest
from pathlib import Path

from graphtec_fixtures import (
    ARBITRARY_NAMES,
    DCW_LINES,
    DCW_TEXT,
    IR_LINES,
    IR_TEXT,
    content,
    line,
)

from src.report_generator.graphtec import (
    GraphtecFormatError,
    GraphtecUnsupportedFormatError,
    parse_graphtec_content,
    read_graphtec_file,
)
from src.report_generator.graphtec.timeline import compute_elapsed_times
from src.report_generator.graphtec import txt_tabulated


def parse(text: str):
    return parse_graphtec_content(text, ".txt")


class captured_error:
    """Context manager that captures a Graphtec error and its line issues."""

    def __init__(self, exception_type):
        self.exception_type = exception_type
        self.exception = None
        self.issues: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None or not issubclass(exc_type, self.exception_type):
            raise AssertionError(f"{self.exception_type.__name__} not raised")
        self.exception = exc
        self.issues = exc.issues
        return True


class GraphtecParserTests(unittest.TestCase):
    def test_valid_dcw(self):
        acquisition = parse(DCW_TEXT)

        self.assertEqual(acquisition.format_id, "graphtec_txt_tabulated")
        self.assertEqual(acquisition.test_type, "DCW")
        self.assertEqual(acquisition.channel, 1)
        self.assertEqual(len(acquisition.records), len(DCW_LINES))
        record = acquisition.records[5]
        self.assertEqual(record.channel, 1)
        self.assertEqual(record.test_type, "DCW")
        self.assertEqual(record.status, "TEST")
        self.assertEqual(record.raw_voltage, "2.149kV")
        self.assertEqual(record.voltage_value, 2.149)
        self.assertEqual(record.voltage_unit, "kV")
        self.assertEqual(record.raw_measurement, "002.5 uA")
        self.assertIsNone(record.measurement_operator)
        self.assertEqual(record.measurement_value, 2.5)
        self.assertEqual(record.phase, "T")
        self.assertEqual(record.phase_time_seconds, 0.4)

    def test_dcw_current_in_microamperes(self):
        record = parse(DCW_TEXT).records[3]

        self.assertEqual(record.measurement_quantity, "current")
        self.assertEqual(record.measurement_unit, "uA")
        self.assertEqual(record.normalized_unit, "uA")
        self.assertEqual(record.normalized_value, 10.5)

    def test_valid_ir_with_mohm(self):
        record = parse(IR_TEXT).records[1]

        self.assertEqual(record.test_type, "IR")
        self.assertEqual(record.measurement_quantity, "resistance")
        self.assertEqual(record.raw_measurement, "109.6Mohm")
        self.assertEqual(record.measurement_value, 109.6)
        self.assertEqual(record.measurement_unit, "Mohm")
        self.assertEqual(record.normalized_value, 109.6)
        self.assertEqual(record.normalized_unit, "Mohm")

    def test_valid_ir_with_gohm_is_normalized_to_mohm(self):
        record = parse(IR_TEXT).records[4]

        self.assertEqual(record.raw_measurement, "4.298Gohm")
        self.assertEqual(record.measurement_value, 4.298)
        self.assertEqual(record.measurement_unit, "Gohm")
        self.assertEqual(record.normalized_value, 4298.0)
        self.assertEqual(record.normalized_unit, "Mohm")

    def test_gohm_conversion_factor(self):
        text = content([line("1", "IR", "TEST", "1.000kV", "1Gohm", "T=000.1s")])

        self.assertEqual(parse(text).records[0].normalized_value, 1000.0)

    def test_greater_than_operator_is_kept_and_not_exact(self):
        record = parse(IR_TEXT).records[7]

        self.assertEqual(record.raw_measurement, ">50Gohm")
        self.assertEqual(record.measurement_operator, ">")
        self.assertEqual(record.measurement_value, 50.0)
        self.assertEqual(record.measurement_unit, "Gohm")
        self.assertEqual(record.normalized_value, 50000.0)
        self.assertEqual(record.normalized_unit, "Mohm")
        self.assertTrue(record.is_limited)
        self.assertFalse(parse(IR_TEXT).records[6].is_limited)

    def test_test_and_pass_statuses(self):
        acquisition = parse(IR_TEXT)

        self.assertEqual(acquisition.ordered_unique("status"), ["TEST", "PASS"])

    def test_final_result_pass(self):
        self.assertEqual(parse(IR_TEXT).final_result, "PASS")
        self.assertEqual(parse(DCW_TEXT).final_result, "PASS")
        self.assertEqual(parse(IR_TEXT).warnings, [])

    def test_missing_result_is_a_warning(self):
        acquisition = parse(content(IR_LINES[:-1]))

        self.assertIsNone(acquisition.final_result)
        self.assertTrue(any("No result record" in w for w in acquisition.warnings))

    def test_phases_i_r_t_d(self):
        self.assertEqual(parse(DCW_TEXT).ordered_unique("phase"), ["I", "R", "T", "D"])
        self.assertEqual(parse(IR_TEXT).ordered_unique("phase"), ["R", "T", "D"])

    def test_time_restarts_with_each_phase(self):
        records = parse(DCW_TEXT).records

        self.assertEqual(
            [(r.phase, r.phase_time_seconds, r.elapsed_time_seconds) for r in records],
            [
                ("I", 0.0, 0.0),
                ("R", 0.1, 0.1),
                ("R", 2.5, 2.5),
                ("R", 4.9, 4.9),
                ("T", 0.1, 5.0),
                ("T", 0.4, 5.3),
                ("T", 3.0, 7.9),
                ("D", 0.2, 8.1),
                ("D", 4.8, 12.7),
                ("D", 5.0, 12.9),
            ],
        )

    def test_elapsed_time_is_monotonic(self):
        for text in (DCW_TEXT, IR_TEXT):
            elapsed = [r.elapsed_time_seconds for r in parse(text).records]
            self.assertEqual(elapsed, sorted(elapsed))

    def test_phase_time_going_back_inside_a_phase_is_an_error(self):
        text = content([
            line("1", "IR", "TEST", "0.1kV", "1Mohm", "R=000.5s"),
            line("1", "IR", "TEST", "0.1kV", "1Mohm", "R=000.2s"),
        ])

        with captured_error(GraphtecFormatError) as error:
            parse(text)
        self.assertTrue(any("Line 2" in issue and "goes back" in issue for issue in error.issues))

    def test_repeated_phase_letter_starts_a_new_segment(self):
        text = content([
            line("1", "IR", "TEST", "0.1kV", "1Mohm", "R=001.0s"),
            line("1", "IR", "TEST", "0.1kV", "1Mohm", "T=002.0s"),
            line("1", "IR", "TEST", "0.1kV", "1Mohm", "R=000.5s"),
        ])

        records = compute_elapsed_times(parse(text).records)
        self.assertEqual([r.elapsed_time_seconds for r in records], [1.0, 3.0, 3.5])

    def test_empty_file(self):
        for text in ("", "\r\n\r\n", "   \n\t\n"):
            with self.assertRaises(GraphtecFormatError) as context:
                parse(text)
            self.assertIn("empty", str(context.exception))

    def test_blank_lines_are_ignored_and_line_numbers_kept(self):
        text = "\r\n" + IR_LINES[0] + "\r\n\r\n" + IR_LINES[1] + "\r\n"

        records = parse(text).records
        self.assertEqual([r.line_number for r in records], [2, 4])

    def test_wrong_field_count_reports_every_line(self):
        text = content([
            DCW_LINES[0],
            "1\tDCW\tTEST\t0.1kV\t1.0 uA",
            DCW_LINES[1],
            "1\tDCW\tTEST\t0.1kV\t1.0 uA\tR=000.2s\textra",
        ])

        with captured_error(GraphtecFormatError) as error:
            parse(text)
        self.assertTrue(any(i.startswith("Line 2:") and "found 5" in i for i in error.issues))
        self.assertTrue(any(i.startswith("Line 4:") and "found 7" in i for i in error.issues))

    def test_first_line_without_six_fields_is_unsupported_format(self):
        with self.assertRaises(GraphtecUnsupportedFormatError):
            parse("Date,Time,CH1\n2026-07-08,15:11:30,0.1\n")

    def test_invalid_voltage(self):
        text = content([line("1", "DCW", "TEST", "abc", "1.0 uA", "R=000.1s")])
        with captured_error(GraphtecFormatError) as error:
            parse(text)
        self.assertIn("Line 1: invalid voltage 'abc'.", error.issues)

    def test_unsupported_voltage_unit(self):
        text = content([line("1", "DCW", "TEST", "2.1V", "1.0 uA", "R=000.1s")])
        with captured_error(GraphtecFormatError) as error:
            parse(text)
        self.assertTrue(any("unsupported voltage unit 'V'" in i for i in error.issues))

    def test_invalid_measurement(self):
        text = content([line("1", "IR", "TEST", "1.0kV", "lots", "R=000.1s")])
        with captured_error(GraphtecFormatError) as error:
            parse(text)
        self.assertIn("Line 1: invalid measurement 'lots'.", error.issues)

    def test_unsupported_measurement_unit(self):
        cases = [
            ("IR", "5.0kohm"),
            ("IR", "5.0mohm"),
            ("DCW", "1.0 mA"),
            ("DCW", "5.0Mohm"),
        ]
        for test_type, measurement in cases:
            text = content([line("1", test_type, "TEST", "1.0kV", measurement, "R=000.1s")])
            with captured_error(GraphtecFormatError) as error:
                parse(text)
            self.assertTrue(
                any("unsupported unit" in i for i in error.issues),
                (test_type, measurement, error.issues),
            )

    def test_unsupported_test_type(self):
        text = content([line("1", "ACW", "TEST", "1.0kV", "1.0 uA", "R=000.1s")])
        with captured_error(GraphtecFormatError) as error:
            parse(text)
        self.assertTrue(any("unsupported test type 'ACW'" in i for i in error.issues))

    def test_unsupported_status(self):
        text = content([line("1", "IR", "FAIL", "1.0kV", "1Mohm", "R=000.1s")])
        with captured_error(GraphtecFormatError) as error:
            parse(text)
        self.assertTrue(any("unsupported status 'FAIL'" in i for i in error.issues))

    def test_invalid_phase(self):
        for phase in ("X=000.1s", "R:000.1s", "R=000.1", "R=-1s", "RR=1s"):
            text = content([line("1", "IR", "TEST", "1.0kV", "1Mohm", phase)])
            with captured_error(GraphtecFormatError) as error:
                parse(text)
            self.assertTrue(
                any("phase" in i for i in error.issues), (phase, error.issues)
            )

    def test_invalid_channel(self):
        text = content([line("A", "IR", "TEST", "1.0kV", "1Mohm", "R=000.1s")])
        with captured_error(GraphtecFormatError) as error:
            parse(text)
        self.assertTrue(any("invalid channel" in i for i in error.issues))

    def test_mixed_dcw_and_ir_is_an_error(self):
        text = content([DCW_LINES[1], IR_LINES[1]])
        with captured_error(GraphtecFormatError) as error:
            parse(text)
        self.assertTrue(any("Line 2" in i and "one test type" in i for i in error.issues))

    def test_mixed_channels_is_an_error(self):
        text = content([IR_LINES[1], IR_LINES[2].replace("1\t", "2\t", 1)])
        with captured_error(GraphtecFormatError) as error:
            parse(text)
        self.assertTrue(any("channel 2" in i for i in error.issues))

    def test_unsupported_extension(self):
        with self.assertRaises(GraphtecUnsupportedFormatError):
            parse_graphtec_content(IR_TEXT, ".csv")

    def test_binary_content_is_unsupported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.txt"
            path.write_bytes(b"\x00\x01\x02GBD")
            with self.assertRaises(GraphtecUnsupportedFormatError):
                read_graphtec_file(path)

    def test_arbitrary_file_names_do_not_change_the_result(self):
        with tempfile.TemporaryDirectory() as directory:
            results = []
            for name in ARBITRARY_NAMES:
                path = Path(directory) / name
                path.write_text(IR_TEXT, encoding="utf-8")
                acquisition = read_graphtec_file(path)
                results.append(
                    (
                        acquisition.test_type,
                        acquisition.channel,
                        acquisition.final_result,
                        [r.__dict__ for r in acquisition.records],
                    )
                )
            for result in results[1:]:
                self.assertEqual(result, results[0])
            self.assertEqual(results[0][0], "IR")
            self.assertEqual(results[0][1], 1)
            self.assertEqual(results[0][2], "PASS")

    def test_same_name_with_different_content_follows_the_content(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "IR_measurement.txt"
            path.write_text(DCW_TEXT, encoding="utf-8")
            self.assertEqual(read_graphtec_file(path).test_type, "DCW")

    def test_parser_module_declares_the_format(self):
        self.assertEqual(txt_tabulated.FORMAT_ID, "graphtec_txt_tabulated")
        self.assertIn(".txt", txt_tabulated.SUPPORTED_EXTENSIONS)
        self.assertTrue(txt_tabulated.matches(IR_TEXT))
        self.assertFalse(txt_tabulated.matches("a;b;c\n"))


if __name__ == "__main__":
    unittest.main()
