import pytest

from uitestauto.plugins.base import BaseInspector, BaseRecorder, BaseExecutor, BaseGenerator
from uitestauto.plugins.registry import PluginRegistry
from uitestauto.models.project import TestCase


class MockInspector(BaseInspector):
    def get_top_level_windows(self): return []
    def get_window_tree(self, window_name=None, handle=None): return None
    def dump_tree(self, window_name: str): pass
    def highlight_element(self, element): pass

class MockRecorder(BaseRecorder):
    def start(self): pass
    def stop(self): return []
    def quit(self): pass

class MockExecutor(BaseExecutor):
    def execute(self, step_type, locator_path, value=None, step_id=None,
                ambiguity_resolver=None, post_action_func=None):
        pass

class MockGenerator(BaseGenerator):
    def generate(self, test_case, output_path): return True


def _make_registry_with_mock() -> PluginRegistry:
    registry = PluginRegistry()
    registry.register(
        name="mock_backend",
        inspector_factory=MockInspector,
        recorder_factory=MockRecorder,
        executor_factory=MockExecutor,
        generator_factory=MockGenerator,
    )
    return registry


def test_register_and_list_backends():
    registry = PluginRegistry()
    assert registry.list_backends() == []
    registry.register("a", MockInspector, MockRecorder, MockExecutor, MockGenerator)
    registry.register("b", MockInspector, MockRecorder, MockExecutor, MockGenerator)
    assert registry.list_backends() == ["a", "b"]


def test_is_registered():
    registry = _make_registry_with_mock()
    assert registry.is_registered("mock_backend")
    assert not registry.is_registered("nonexistent")


def test_create_inspector():
    registry = _make_registry_with_mock()
    inspector = registry.create_inspector("mock_backend")
    assert isinstance(inspector, BaseInspector)
    assert isinstance(inspector, MockInspector)


def test_create_recorder():
    registry = _make_registry_with_mock()
    recorder = registry.create_recorder("mock_backend")
    assert isinstance(recorder, BaseRecorder)


def test_create_executor():
    registry = _make_registry_with_mock()
    executor = registry.create_executor("mock_backend")
    assert isinstance(executor, BaseExecutor)


def test_create_generator():
    registry = _make_registry_with_mock()
    generator = registry.create_generator("mock_backend")
    assert isinstance(generator, BaseGenerator)


def test_create_unknown_backend_raises():
    registry = PluginRegistry()
    with pytest.raises(KeyError, match="'unknown'"):
        registry.create_inspector("unknown")


def test_each_create_returns_fresh_instance():
    registry = _make_registry_with_mock()
    i1 = registry.create_inspector("mock_backend")
    i2 = registry.create_inspector("mock_backend")
    assert i1 is not i2


def test_pywinauto_backends_registered():
    """
    Verify that register_pywinauto_backends() registers both expected names.
    """
    from uitestauto.plugins.registry import PluginRegistry
    from uitestauto.plugins.pywinauto import register_pywinauto_backends

    registry = PluginRegistry()
    register_pywinauto_backends(registry)

    backends = registry.list_backends()
    assert "pywinauto_uia" in backends
    assert "pywinauto_win32" in backends
    assert len(backends) == 2


def test_test_case_default_backend():
    case = TestCase(name="MyTest")
    assert case.backend == "pywinauto_uia"


def test_test_case_custom_backend():
    case = TestCase(name="MyTest", backend="pywinauto_win32")
    assert case.backend == "pywinauto_win32"


def test_project_manager_get_backend_for_case():
    from uitestauto.core.project_manager import ProjectManager
    from uitestauto.plugins.registry import plugin_registry
    from uitestauto.plugins.pywinauto import register_pywinauto_backends

    if not plugin_registry.is_registered("pywinauto_uia"):
        register_pywinauto_backends(plugin_registry)

    case = TestCase(name="TempCase", backend="pywinauto_uia")
    pm = ProjectManager()
    insp, rec, exec, gen = pm.get_backend_for_case(case)
    assert isinstance(insp, BaseInspector)
    assert isinstance(rec, BaseRecorder)
    assert isinstance(exec, BaseExecutor)
    assert isinstance(gen, BaseGenerator)
