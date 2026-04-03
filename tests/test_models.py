import pytest
from uitestauto.models.element import UIElementLocator, ScenarioStep, ScenarioStepType, ClickValue
from uitestauto.models.project import TestCase, TestSuite, ProjectConfig

def test_ui_element_locator():
    loc = UIElementLocator(name="TestButton", control_type="Button", depth=2)
    assert loc.name == "TestButton"
    assert loc.control_type == "Button"
    assert loc.depth == 2
    
    # Test pywinauto kwargs filtering
    kwargs = loc.to_pywinauto_kwargs()
    assert "name" in kwargs
    assert "control_type" in kwargs
    assert "depth" in kwargs
    assert "auto_id" not in kwargs

def test_scenario_step_click():
    step = ScenarioStep(
        id=1,
        action_type=ScenarioStepType.CLICK,
        value=ClickValue.DOUBLE.value,
        description="Double click target"
    )
    assert step.action_type == "click"
    assert step.value == "double"

def test_scenario_step_type_text():
    step = ScenarioStep(
        id=2, 
        action_type=ScenarioStepType.TYPE_TEXT,
        value="Hello World"
    )
    assert step.value == "Hello World"
    
def test_project_models():
    case = TestCase(name="Login Test")
    suite = TestSuite(name="Smoke Tests")
    suite.cases.append(case)
    config = ProjectConfig(project_name="My Web App")
    config.suites.append(suite)
    
    assert len(config.suites) == 1
    assert len(config.suites[0].cases) == 1
    assert config.suites[0].cases[0].name == "Login Test"
