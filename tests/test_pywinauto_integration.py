import pytest
import subprocess
import time
import os
import sys

from uitestauto.plugins.pywinauto.executor import PywinautoExecutorBackend
from uitestauto.plugins.pywinauto.inspector import PywinautoInspectorBackend
from uitestauto.models.element import ScenarioStepType

def find_app_path():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "test_apps", "dummy_app_qt.py")

@pytest.fixture(scope="module")
def running_dummy_app():
    process = subprocess.Popen([sys.executable, find_app_path()])
    time.sleep(3)
    yield process
    process.terminate()
    process.wait()

def test_pywinauto_inspector(running_dummy_app):
    inspector = PywinautoInspectorBackend(variant="uia")
    windows = inspector.get_top_level_windows()
    
    dummy_wins = [w for w in windows if w["name"] == "UiTestAuto Dummy App"]
    assert len(dummy_wins) >= 1
    
    app_handle = dummy_wins[0]["handle"]
    tree = inspector.get_window_tree(handle=app_handle)
    
    assert tree is not None
    assert "UiTestAuto Dummy App" in tree["display"]
    
def test_pywinauto_executor(running_dummy_app):
    executor = PywinautoExecutorBackend(pywinauto_backend="uia")
    
    # 1. Type text into entry.
    from uitestauto.models.element import UIElementLocator
    entry_loc = [
        UIElementLocator(name="UiTestAuto Dummy App", control_type="Window"),
        UIElementLocator(control_type="Edit")
    ]
    
    executor.execute(ScenarioStepType.TYPE_TEXT, entry_loc, value="HelloPytest")
    
    # 2. Click submit button.
    btn_loc = [
        UIElementLocator(name="UiTestAuto Dummy App", control_type="Window"),
        UIElementLocator(control_type="Button", found_index=1, depth=10)
    ]
    executor.execute(ScenarioStepType.CLICK, btn_loc, value="left")
    
    # 3. Assert status label updated. Name will be the text itself in UIA
    status_loc = [
        UIElementLocator(name="UiTestAuto Dummy App", control_type="Window"),
        UIElementLocator(control_type="Text", found_index=2, depth=10)
    ]
    executor.execute(ScenarioStepType.ASSERT_EXISTS, status_loc)
