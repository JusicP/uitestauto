from uitestauto.plugins.pywinauto.inspector import PywinautoInspectorBackend
from uitestauto.plugins.pywinauto.recorder import PywinautoRecorderBackend
from uitestauto.plugins.pywinauto.healer import PywinautoHealerBackend
from uitestauto.plugins.pywinauto.generator import PywinautoGeneratorBackend
from uitestauto.plugins.registry import PluginRegistry


def _make_factories(variant: str):
    def inspector_factory() -> PywinautoInspectorBackend:
        return PywinautoInspectorBackend(variant)
    def recorder_factory() -> PywinautoRecorderBackend:
        return PywinautoRecorderBackend(variant)
    def healer_factory() -> PywinautoHealerBackend:
        return PywinautoHealerBackend(variant)
    def generator_factory() -> PywinautoGeneratorBackend:
        return PywinautoGeneratorBackend(variant)
    return inspector_factory, recorder_factory, healer_factory, generator_factory


def register_pywinauto_backends(registry: PluginRegistry) -> None:
    """Register pywinauto_uia and pywinauto_win32 into the given registry."""
    for variant in ("uia", "win32"):
        insp, rec, heal, gen = _make_factories(variant)
        registry.register(
            name=f"pywinauto_{variant}",
            inspector_factory=insp,
            recorder_factory=rec,
            healer_factory=heal,
            generator_factory=gen,
        )


__all__ = [
    "register_pywinauto_backends",
    "PywinautoInspectorBackend",
    "PywinautoRecorderBackend",
    "PywinautoHealerBackend",
    "PywinautoGeneratorBackend",
]
