import json
import tempfile
import unittest
from pathlib import Path

from src.report_generator.version import __version__
from src.report_generator.version_check import check_application_version


PACKAGE_PATH = (
    r"\\vigvsfil1.global.borgwarner.net\vigproductengineering"
    r"\Documentacion_I+D\R&T\ToolingVersions\generador-informes.zip"
)


class ApplicationVersionCheckTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.manifest_path = Path(self.temporary_directory.name) / "manifest.json"

    def tearDown(self):
        self.temporary_directory.cleanup()

    def write_manifest(self, content):
        self.manifest_path.write_text(
            json.dumps(content),
            encoding="utf-8",
        )

    def test_matching_version_is_current(self):
        self.write_manifest(
            {"version": __version__, "package": PACKAGE_PATH}
        )

        result = check_application_version(self.manifest_path)

        self.assertEqual(result.status, "current")
        self.assertEqual(result.installed_version, __version__)
        self.assertEqual(result.current_version, __version__)
        self.assertEqual(result.package, PACKAGE_PATH)
        self.assertIsNone(result.warning)

    def test_different_version_is_outdated(self):
        self.write_manifest(
            {"version": "99.0.0", "package": PACKAGE_PATH}
        )

        result = check_application_version(self.manifest_path)

        self.assertEqual(result.status, "outdated")
        self.assertEqual(result.current_version, "99.0.0")
        self.assertEqual(result.package, PACKAGE_PATH)

    def test_unreadable_manifest_is_non_blocking(self):
        result = check_application_version(self.manifest_path)

        self.assertEqual(result.status, "unavailable")
        self.assertIsNotNone(result.warning)

    def test_invalid_json_is_non_blocking(self):
        self.manifest_path.write_text("{", encoding="utf-8")

        result = check_application_version(self.manifest_path)

        self.assertEqual(result.status, "unavailable")
        self.assertIn("Could not read", result.warning)

    def test_invalid_manifest_shape_is_non_blocking(self):
        self.write_manifest({"version": __version__, "package": "package.zip"})

        result = check_application_version(self.manifest_path)

        self.assertEqual(result.status, "unavailable")
        self.assertIn("UNC 'package' path", result.warning)
