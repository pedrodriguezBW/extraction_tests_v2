"""SIMPATI acquisitions used by the tests.

The real exports provided by the testing laboratory are stored unmodified
in ``tests/fixtures/simpati``:

- ``240222_11371_Aging.x01``: climatic chamber (Temperature, supply and
  return air).
- ``240327_11371_RD_Aging.x04``: thermal shock chamber (basket, hot and
  cold chambers, cycles and specimen temperature).

``build_simpati_text`` writes small synthetic exports with the same
structure, for example an ``.x03`` with the Spanish channel names of the
historical thermal shock chamber.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Sequence

FIXTURES_DIRECTORY = Path(__file__).resolve().parent / "fixtures" / "simpati"
X01_FIXTURE = FIXTURES_DIRECTORY / "240222_11371_Aging.x01"
X04_FIXTURE = FIXTURES_DIRECTORY / "240327_11371_RD_Aging.x04"

#: Header of a historical ``.x03`` (Spanish thermal shock chamber).
X03_CHANNELS: list[tuple[str, str]] = [
    ("A:Pos canasta ", "[Pos  ]"),
    ("N:Pos canasta ", "[Pos  ]"),
    ("A:Temp canast ", "[°C   ]"),
    ("N:Temp canast ", "[°C   ]"),
    ("-.Lm:Temp cana", "[°C   ]"),
    ("+.Lm:Temp cana", "[°C   ]"),
    ("A:Cam calient ", "[°C   ]"),
    ("N:Cam calient ", "[°C   ]"),
    ("A:Cam fria    ", "[°C   ]"),
    ("N:Cam fria    ", "[°C   ]"),
    ("A:Reserve     ", "[°C   ]"),
    ("Start         ", "[]"),
    ("Reservado     ", "[]"),
    ("Reservado     ", "[]"),
]

#: Records of the synthetic ``.x03``: every value is unique per column so
#: that any shift between names and values is detected.
X03_ROWS: list[list[str]] = [
    ["27.08.2024 15:06:03", "1,0", "1,5", "21,5", "22,0", "-90,0", "230,0", "80,1", "82,0", "-35,2", "-36,0", "0,0", "1", "0", "0"],
    ["27.08.2024 15:07:03", "2,0", "2,5", "40,5", "90,0", "-91,0", "231,0", "90,1", "90,0", "-49,9", "-40,0", "0,0", "1", "0", "0"],
]


def build_simpati_text(
    channels: Sequence[tuple[str, str]],
    rows: Sequence[Sequence[str]],
    *,
    device: str = "4136 Weis~",
    program: str = "---",
    preamble: bool = True,
) -> str:
    """Return a ``;`` separated export with the SIMPATI layout."""
    lines: list[str] = []
    if preamble:
        lines += [
            f"{device};Progr.: {program};",
            "",
            "Start:;27.08.2024;15:06:03;Admin;",
            "Stop:;25.09.2024;19:08:55;Admin;",
            "",
        ]
    lines.append(";" + ";".join(name for name, _ in channels) + ";")
    lines.append(";" + ";".join(unit for _, unit in channels) + ";")
    lines.append("")
    lines += [";".join(row) + ";" for row in rows]
    return "\r\n".join(lines) + "\r\n"


def write_x03(path: Path, encoding: str = "cp1252") -> Path:
    """Write the synthetic historical ``.x03``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(build_simpati_text(X03_CHANNELS, X03_ROWS).encode(encoding))
    return path


def write_without_thermal(path: Path) -> Path:
    """Valid SIMPATI export without any recognizable thermal channel."""
    channels = [("A:Basketpositi", "[     ]"), ("N:Basketpositi", "[     ]"), ("Start", "[]")]
    rows = [
        ["01.03.2024 10:00:00", "1,0", "1,0", "1"],
        ["01.03.2024 10:01:00", "2,0", "2,0", "0"],
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(build_simpati_text(channels, rows).encode("cp1252"))
    return path


def write_incompatible(path: Path) -> Path:
    """``.xNN`` file whose content is not a SIMPATI export."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x00\x01\x02binary\xff\xfe content without structure\n" * 20)
    return path


def copy_fixture(fixture: Path, directory: Path, name: str | None = None) -> Path:
    """Copy a real export into a test folder, unmodified."""
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (name or fixture.name)
    shutil.copyfile(fixture, target)
    return target
