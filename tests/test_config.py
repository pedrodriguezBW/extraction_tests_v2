import unittest
from pathlib import Path

import config


class ResolveTemplatePathTests(unittest.TestCase):
    def test_uses_default_path_without_environment_variable(self):
        self.assertEqual(
            config.resolve_template_path({}),
            config.DEFAULT_POWERPOINT_TEMPLATE_PATH,
        )

    def test_blank_environment_variable_uses_default_path(self):
        self.assertEqual(
            config.resolve_template_path({config.TEMPLATE_PATH_ENV_VAR: "   "}),
            config.DEFAULT_POWERPOINT_TEMPLATE_PATH,
        )

    def test_environment_variable_overrides_default_path(self):
        environ = {
            config.TEMPLATE_PATH_ENV_VAR: '"C:\\Apps\\plantilla\\informe.pptx"'
        }
        self.assertEqual(
            config.resolve_template_path(environ),
            Path("C:\\Apps\\plantilla\\informe.pptx"),
        )


if __name__ == "__main__":
    unittest.main()
