import json
import unittest
from pathlib import Path

TAURI_CONF = Path(__file__).resolve().parents[1] / "frontend" / "src-tauri" / "tauri.conf.json"


class TauriCspTests(unittest.TestCase):
    def test_img_src_allows_data_urls_for_chart_previews(self):
        """Las vistas previas Graphtec llegan como data:image/png;base64."""
        csp = json.loads(TAURI_CONF.read_text(encoding="utf-8"))["app"]["security"]["csp"]
        directives = {
            part.split()[0]: part.split()[1:]
            for part in csp.split(";")
            if part.strip()
        }
        self.assertIn("data:", directives["img-src"])


if __name__ == "__main__":
    unittest.main()
