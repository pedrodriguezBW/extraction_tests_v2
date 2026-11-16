"""Genera ejemplos reproducibles con datos y plantilla de validación sintéticos.

Ejecutar primero sin argumentos, renderizar las gráficas con el script Node
y ejecutar después con --finish. No modifica carpetas de ensayos reales.
"""

import argparse
import base64
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pptx import Presentation
from pptx.util import Cm
from src.report_generator.generator import generate_climatic_report
from src.report_generator.report_inputs import save_report_inputs
from src.report_generator.simpati.parser import read_simpati_acquisition
from src.report_generator.simpati.channels import classify_channels
from src.report_generator.simpati.tolerances import evaluate_tolerances, ToleranceSettings
from src.report_generator.powerpoint.navigation import add_continuation_slide_frame, remove_shape
from backend.app.services.simpati_inspection import save_project_simpati_chart

OUTPUT = ROOT / "examples/generated"


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def make_template():
    """Replica la geometría del motor sin suplantar la plantilla corporativa."""
    presentation = Presentation()
    presentation.slide_width = Cm(33.87)
    presentation.slide_height = Cm(19.05)
    for number, title in enumerate([
        "IEC validation · SYNTHETIC DATA", "2. Tested Parts", "TEST A", "Contents",
        "1. Test Description", "2. Test Assembly", "3. Test Inputs", "4. Test Results", "5. Conclusions",
    ], 1):
        slide = presentation.slides.add_slide(presentation.slide_layouts[5])
        slide.shapes.title.text = title
        # El marco reutiliza tamaños y tipografía del generador existente.
        add_continuation_slide_frame(slide, title, number)
        for shape in list(slide.shapes):
            if not shape.is_placeholder and shape.has_text_frame and shape.text == title:
                remove_shape(shape)
        if title == "1. Test Description":
            slide.shapes.add_textbox(Cm(2), Cm(4), Cm(20), Cm(1)).text = "Xyz"
        if number == 1:
            slide.shapes.add_textbox(Cm(2.12), Cm(7), Cm(29), Cm(2)).text = "Validation template · Synthetic measurements · Not a test certificate"
    path = OUTPUT / "validation_template.pptx"
    presentation.save(path)
    return path


def prepare():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    template = make_template()
    targets = [23] + [-40] * 31 + list(range(-30, 80, 10)) + [85] * 31 + list(range(70, -40, -10)) + [-40] * 31 + list(range(-30, 80, 10)) + [85] * 31 + [23]
    for phase in ("phase1", "phase2"):
        root = OUTPUT / phase
        metadata = {
            "schema_version": "1.0",
            "test": {"test_name": f"IEC_{phase}_SYNTHETIC", "customer": "Validation example", "phase": "Development",
                     "procedure": "Synthetic temperature cycle used to validate the report generator. The engineer completes final condition and conclusions.",
                     "start_date": "2026-01-01", "end_date": "2026-01-01"},
            "people": {}, "samples": [{"sample_number": 1, "sample_code": "SYNTHETIC-01", "sample_description": "Validation specimen"}],
            "equipment": [], "setup": {"images": []}, "test_events": [],
            "test_facility": {"climatic_chamber": "TECLI00023 - CC TS (OS)"},
            "climatic_inputs": {"minimum_temperature_c": -40, "maximum_temperature_c": 85, "number_of_cycles": 2,
                                "profile_points": [{"sequence": 1, "time_min": 0, "temperature_c": -40},
                                                   {"sequence": 2, "time_min": 30, "temperature_c": -40},
                                                   {"sequence": 3, "time_min": 42, "temperature_c": 85},
                                                   {"sequence": 4, "time_min": 72, "temperature_c": 85}]},
            "dut_controller_inputs": {"profile_points": []},
        }
        write_json(root / "04_Report/test_metadata.json", metadata)
        save_report_inputs(root, {"test_type": "Nb", "measurement_points": [
            {"channel": "A:Temperature [°C]", "location": "Chamber control probe", "sensor_type": "Pt100", "function": "control"},
            {"channel": "Manual TC", "location": "Air beside specimen", "sensor_type": "Type T", "function": "air"},
        ]})
        if phase == "phase1":
            report = generate_climatic_report(root, template, selected_rendered_assets=[])
            (OUTPUT / "IEC_phase1.pptx").write_bytes(report.read_bytes())
        else:
            for index, label in ((1, "OK"), (2, "NOK")):
                source = root / f"03_Data/01_SIMPATI/synthetic_{label}.x{index:02d}"
                source.parent.mkdir(parents=True, exist_ok=True)
                lines = [";A:Temperature;N:Temperature;", ";[°C];[°C];", ""]
                for i, target in enumerate(targets):
                    actual = target + (5 if label == "NOK" and 10 <= i <= 12 else 0)
                    timestamp = datetime(2026, 1, 1) + timedelta(minutes=i)
                    lines.append(f"{timestamp:%d.%m.%Y %H:%M:%S};{actual};{target};")
                source.write_bytes(("\r\n".join(lines) + "\r\n").encode("cp1252"))
                acquisition = read_simpati_acquisition(source)
                channels = classify_channels(acquisition.dataframe)
                evaluation = evaluate_tolerances(acquisition, channels, "Nb", "A:Temperature [°C]")
                model = {"title": f"SIMPATI · Synthetic {label}", "valueAxisLabel": "Temperature (°C)",
                         "timestamps": [value.isoformat() for value in acquisition.dataframe["Timestamp"]],
                         "viewport": {"xStart": 0, "xEnd": len(targets) - 1, "yRange": None},
                         "yBounds": {"minimum": -50, "maximum": 95}, "tolerances": evaluation,
                         "series": [{"id": c.column, "label": c.display_label,
                                     "values": acquisition.dataframe[c.column].tolist(), "primary": True,
                                     "color": "#005a9c", **({"dash": "9 6"} if c.kind == "setpoint" else {})} for c in channels]}
                write_json(OUTPUT / f"chart_{label}.json", model)
    print(OUTPUT)


def finish():
    root = OUTPUT / "phase2"
    selected = []
    for index, label in ((1, "OK"), (2, "NOK")):
        png = (OUTPUT / f"chart_{label}.png").read_bytes()
        saved = save_project_simpati_chart(root, f"03_Data/01_SIMPATI/synthetic_{label}.x{index:02d}",
                                  base64.b64encode(png).decode("ascii"),
                                  ToleranceSettings(test_type="Nb", channel="A:Temperature [°C]"))
        selected.append(saved.relative_path)
    report = generate_climatic_report(root, OUTPUT / "validation_template.pptx", selected_rendered_assets=selected)
    (OUTPUT / "IEC_phase2.pptx").write_bytes(report.read_bytes())
    print(OUTPUT / "IEC_phase2.pptx")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--finish", action="store_true")
    args = parser.parse_args()
    finish() if args.finish else prepare()
