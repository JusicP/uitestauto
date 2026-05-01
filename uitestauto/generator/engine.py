"""
TestGenerator — thin facade over a BaseGenerator backend.

Kept for backward compatibility. The UI layer (main_window.py / test_engine.py)
should prefer using the generator obtained from the PluginRegistry directly.
"""

from uitestauto.plugins.base import BaseGenerator
from uitestauto.models.project import TestCase


class TestGenerator:
    """
    Facade that delegates code generation to an injected BaseGenerator.
    """

    def __init__(self, backend: BaseGenerator) -> None:
        self._backend = backend

    def generate_pytest_file(self, test_case: TestCase, output_path: str) -> bool:
        return self._backend.generate(test_case, output_path)
