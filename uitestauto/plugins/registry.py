"""
PluginRegistry is a central registry for UiTestAuto backend plugins.

Usage:
    from uitestauto.plugins.registry import plugin_registry
    from uitestauto.plugins.pywinauto import register_pywinauto_backends

    register_pywinauto_backends(plugin_registry)

    inspector = plugin_registry.create_inspector("pywinauto_uia")
"""

from dataclasses import dataclass
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from uitestauto.plugins.base import (
        BaseInspector,
        BaseRecorder,
        BaseHealer,
        BaseGenerator,
        BaseAIAgent,
    )


@dataclass
class _BackendEntry:
    inspector_factory: Callable[[], "BaseInspector"]
    recorder_factory: Callable[[], "BaseRecorder"]
    healer_factory: Callable[[], "BaseHealer"]
    generator_factory: Callable[[], "BaseGenerator"]


class PluginRegistry:
    """
    Registry that maps backend names to factory callables.

    Each backend name maps to four factories - one per subsystem.
    Factories are called fresh every time a create_* method
    is invoked, so callers own the resulting instance.
    """

    def __init__(self) -> None:
        self._backends: dict[str, _BackendEntry] = {}
        self._ai_agents: dict[str, Callable[[], "BaseAIAgent"]] = {}

    def register(
        self,
        name: str,
        inspector_factory: Callable[[], "BaseInspector"],
        recorder_factory: Callable[[], "BaseRecorder"],
        healer_factory: Callable[[], "BaseHealer"],
        generator_factory: Callable[[], "BaseGenerator"],
    ) -> None:
        """Register a full backend under *name*."""
        self._backends[name] = _BackendEntry(
            inspector_factory=inspector_factory,
            recorder_factory=recorder_factory,
            healer_factory=healer_factory,
            generator_factory=generator_factory,
        )

    def _get(self, name: str) -> _BackendEntry:
        if name not in self._backends:
            available = ", ".join(self._backends) or "<none>"
            raise KeyError(
                f"Backend '{name}' is not registered. "
                f"Available backends: {available}"
            )
        return self._backends[name]

    def create_inspector(self, name: str) -> "BaseInspector":
        return self._get(name).inspector_factory()

    def create_recorder(self, name: str) -> "BaseRecorder":
        return self._get(name).recorder_factory()

    def create_healer(self, name: str) -> "BaseHealer":
        return self._get(name).healer_factory()

    def create_generator(self, name: str) -> "BaseGenerator":
        return self._get(name).generator_factory()

    def register_ai_agent(self, name: str, factory: Callable[[], "BaseAIAgent"]) -> None:
        self._ai_agents[name] = factory
        
    def create_ai_agent(self, name: str) -> "BaseAIAgent":
        if name not in self._ai_agents:
            available = ", ".join(self._ai_agents) or "<none>"
            raise KeyError(
                f"AI Agent '{name}' is not registered. "
                f"Available agents: {available}"
            )
        return self._ai_agents[name]()

    def list_backends(self) -> list[str]:
        """Return sorted list of all registered backend names."""
        return sorted(self._backends.keys())

    def is_registered(self, name: str) -> bool:
        return name in self._backends


plugin_registry = PluginRegistry()
