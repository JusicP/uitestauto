import logging
import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from uitestauto.plugins.base import BaseGenerator
from uitestauto.models.project import TestCase

logger = logging.getLogger("UiTestAuto")

# templates in the plugins/pywinauto/templates/ directory
_TEMPLATE_DIR = Path(__file__).parent / "templates"
_TEMPLATE_NAME = "pytest_pywinauto_template.j2"


class PywinautoGeneratorBackend(BaseGenerator):
    """
    Generates pytest scripts for test cases executed via pywinauto.

    The *variant* parameter ("uia" or "win32") is embedded into the
    generated script so the correct pywinauto backend is selected at
    runtime.
    """

    def __init__(self, variant: str = "uia") -> None:
        self._variant = variant
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATE_DIR)),
            keep_trailing_newline=True,
        )

    def generate(self, test_case: TestCase, output_path: str) -> bool:
        try:
            template = self._env.get_template(_TEMPLATE_NAME)
            rendered_code = template.render(
                case=test_case,
                backend_variant=self._variant,
            )

            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(rendered_code)

            logger.info(f"[Generator/{self._variant}] Created test file: {output_path}")
            return True

        except Exception as e:
            logger.error(f"[Generator/{self._variant}] Failed to generate code: {e}")
            return False
