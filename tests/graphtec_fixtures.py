"""Synthetic Graphtec TXT content for the tests.

The lines follow the structure of real tab-separated Graphtec exports. The
file names used in the tests are arbitrary on purpose: no behaviour may
depend on them.
"""

from __future__ import annotations

from pathlib import Path


def line(*fields: str) -> str:
    return "\t".join(fields)


DCW_LINES = [
    line("1", "DCW", "TEST", "0.000kV", "000.0 uA", "I=000.0s"),
    line("1", "DCW", "TEST", "0.012kV", "007.1 uA", "R=000.1s"),
    line("1", "DCW", "TEST", "1.068kV", "009.0 uA", "R=002.5s"),
    line("1", "DCW", "TEST", "2.088kV", "010.5 uA", "R=004.9s"),
    line("1", "DCW", "TEST", "2.149kV", "003.0 uA", "T=000.1s"),
    line("1", "DCW", "TEST", "2.149kV", "002.5 uA", "T=000.4s"),
    line("1", "DCW", "TEST", "2.149kV", "001.7 uA", "T=003.0s"),
    line("1", "DCW", "TEST", "2.137kV", "000.0 uA", "D=000.2s"),
    line("1", "DCW", "TEST", "0.640kV", "000.0 uA", "D=004.8s"),
    line("1", "DCW", "PASS", "2.149kV", "001.7 uA", "D=005.0s"),
]

IR_LINES = [
    line("1", "IR", "TEST", "0.000kV", "000.0Mohm", "R=000.0s"),
    line("1", "IR", "TEST", "0.496kV", "109.6Mohm", "R=002.5s"),
    line("1", "IR", "TEST", "0.971kV", "192.9Mohm", "R=004.9s"),
    line("1", "IR", "TEST", "0.999kV", "693.4Mohm", "T=000.2s"),
    line("1", "IR", "TEST", "0.999kV", "4.298Gohm", "T=000.4s"),
    line("1", "IR", "TEST", "0.999kV", "1.029Gohm", "T=004.9s"),
    line("1", "IR", "TEST", "0.997kV", "1.063Gohm", "D=000.2s"),
    line("1", "IR", "TEST", "0.958kV", ">50Gohm", "D=000.4s"),
    line("1", "IR", "TEST", "0.918kV", ">50Gohm", "D=000.6s"),
    line("1", "IR", "TEST", "0.461kV", ">20Gohm", "D=003.1s"),
    line("1", "IR", "PASS", "0.999kV", "8.794Gohm", "D=005.0s"),
]


def content(lines: list[str], newline: str = "\r\n") -> str:
    return newline.join(lines) + newline


DCW_TEXT = content(DCW_LINES)
IR_TEXT = content(IR_LINES)


def write_graphtec_file(test_root: Path, name: str, text: str) -> Path:
    path = test_root / "03_Data" / "02_Graphtec" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return path


#: Arbitrary names, including some that look meaningful, to prove that the
#: file name is never interpreted.
ARBITRARY_NAMES = [
    "zz.txt",
    "IR_PASS_channel9_2031.TXT",
    "20991231_235959_TC7_D.txt",
    "result FAIL (copy).txt",
    "x.y.z.txt",
]
