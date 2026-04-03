"""
RecorderManager — thin facade over a BaseRecorder backend.

The concrete backend is created from the active test case's backend name
via the PluginRegistry. The UI layer (main_window.py) is responsible for
instantiating and driving the RecorderManager.
"""

from __future__ import annotations

import logging
from uitestauto.plugins.base import BaseRecorder
from uitestauto.models.element import ScenarioStep

logger = logging.getLogger("UiTestAuto")


class RecorderManager:
    """
    Manages a single BaseRecorder instance lifecycle (start / stop / quit).
    """

    def __init__(self, backend: BaseRecorder) -> None:
        self._backend = backend
        self._active = False

    @property
    def is_recording(self) -> bool:
        return self._active

    def start_recording(self) -> None:
        logger.info("[RecorderManager] Starting recorder")
        self._backend.start()
        self._active = True

    def stop_recording(self) -> list[ScenarioStep]:
        logger.info("[RecorderManager] Stopping recorder")
        steps = self._backend.stop()
        logger.info("[RecorderManager] Quitting recorder")
        self._backend.quit()
        self._active = False
        logger.info("[RecorderManager] Recording stopped.")
        return steps