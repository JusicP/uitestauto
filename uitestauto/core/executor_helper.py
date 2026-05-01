import logging
from typing import Callable

from uitestauto.models.element import UIElementLocator

logger = logging.getLogger("UiTestAuto")


def robust_execute(
    step_type: str,
    locator_path: list[UIElementLocator],
    value: str | None,
    step_id: int | None,
    post_action_func: Callable | None,
    backend_name: str,
    ambiguity_resolver: Callable[[list], int] | None,
) -> None:
    """
    Standalone function used by generated python test scripts.

    The backend_name corresponds to a registered PluginRegistry backend.
    When running in a subprocess (pytest), no Qt resolver may be available, so
    ambiguity_resolver defaults to None - the executor will show its built-in
    Qt dialog if a QApplication is available, otherwise it raises.

    Auto-registers pywinauto backends if the registry is empty (i.e. the
    app's main_window.py was not imported first).
    """
    from uitestauto.plugins.registry import plugin_registry

    if not plugin_registry.list_backends():
        from uitestauto.plugins.pywinauto import register_pywinauto_backends
        register_pywinauto_backends(plugin_registry)

    executor = plugin_registry.create_executor(backend_name)
    executor.execute(
        step_type=step_type,
        locator_path=locator_path,
        value=value,
        step_id=step_id,
        ambiguity_resolver=ambiguity_resolver,
        post_action_func=post_action_func,
    )
