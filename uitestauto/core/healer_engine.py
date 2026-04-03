"""
HealerEngine — thin facade over a BaseHealer backend +
standalone robust_execute() helper for use inside generated pytest scripts.

The *ambiguity_resolver* callback is injected by the UI layer (main_window.py)
and forwarded to the backend. This keeps the entire core layer free of PySide6.
"""

import logging
from typing import Callable

from uitestauto.plugins.base import BaseHealer
from uitestauto.models.element import UIElementLocator

logger = logging.getLogger("UiTestAuto")


class HealerEngine:
    """
    Facade that delegates step execution to an injected BaseHealer.
    """

    def __init__(
        self,
        backend: BaseHealer,
        ambiguity_resolver: Callable[[list], int] | None = None,
    ) -> None:
        self._backend = backend
        self._ambiguity_resolver = ambiguity_resolver

    def execute(
        self,
        step_type: str,
        locator_path: list[UIElementLocator],
        value: str | None = None,
        step_id: int | None = None,
        post_action_func: Callable | None = None,
    ) -> None:
        self._backend.execute(
            step_type=step_type,
            locator_path=locator_path,
            value=value,
            step_id=step_id,
            ambiguity_resolver=self._ambiguity_resolver,
            post_action_func=post_action_func,
        )


# ---------------------------------------------------------------------------
# Standalone function used inside generated pytest scripts via:
#   from uitestauto.core.healer_engine import robust_execute
# The backend name is resolved at call time from the active plugin registry.
# ---------------------------------------------------------------------------

def robust_execute(
    step_type: str,
    locator_path: list[UIElementLocator],
    value: str | None = None,
    step_id: int | None = None,
    post_action_func: Callable | None = None,
    backend_name: str = "pywinauto_uia",
    ambiguity_resolver: Callable[[list], int] | None = None,
) -> None:
    """
    Standalone entry point used by generated pytest scripts.

    The backend_name corresponds to a registered PluginRegistry backend.
    When running in a subprocess (pytest), no Qt resolver is available, so
    ambiguity_resolver defaults to None — the healer will show its built-in
    Qt dialog if a QApplication is running, otherwise it raises.

    Auto-registers pywinauto backends if the registry is empty (i.e. the
    app's main_window.py was not imported first, which is the normal case
    for subprocess pytest runs).
    """
    from uitestauto.plugins.registry import plugin_registry

    if not plugin_registry.list_backends():
        from uitestauto.plugins.pywinauto import register_pywinauto_backends
        register_pywinauto_backends(plugin_registry)

    healer = plugin_registry.create_healer(backend_name)
    healer.execute(
        step_type=step_type,
        locator_path=locator_path,
        value=value,
        step_id=step_id,
        ambiguity_resolver=ambiguity_resolver,
        post_action_func=post_action_func,
    )
