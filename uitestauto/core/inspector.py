"""
UIInspector — thin facade over a BaseInspector backend.

The concrete backend is injected at construction time via the PluginRegistry.
The UI layer (UIBrowserPanel) is responsible for creating UIInspector instances
with the appropriate backend name selected by the user.
"""

from __future__ import annotations

import logging
from uitestauto.plugins.base import BaseInspector

logger = logging.getLogger("UiTestAuto")


class UIInspector:
    """
    Facade that delegates all inspection calls to an injected BaseInspector.
    """

    def __init__(self, backend: BaseInspector) -> None:
        self._backend = backend

    @property
    def backend(self) -> BaseInspector:
        return self._backend

    def get_top_level_windows(self) -> list[dict]:
        return self._backend.get_top_level_windows()

    def get_window_tree(self, window_name: str) -> dict | None:
        return self._backend.get_window_tree(window_name)
    
    def highlight_element(self, element):
        self._backend.highlight_element(element)
