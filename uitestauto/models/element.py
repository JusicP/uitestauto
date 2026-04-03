"""
Data models representing UI elements and actions performed on them.
"""

from enum import Enum
from pydantic import BaseModel, Field


class ScenarioStepType(str, Enum):
    CLICK = "click"
    TYPE_TEXT = "type_text"
    WAIT = "wait"
    ASSERT_EXISTS = "assert_exists"
    START_APP = "start_app"
    KILL_APP = "kill_app"
    CUSTOM = "custom"
    MOUSE_OVER = "mouse_over"

class ClickValue(str, Enum):
    LEFT = "left"
    RIGHT = "right"
    DOUBLE = "double"


class UIElementLocator(BaseModel):
    """
    Represents the search criteria for a UI element.
    At least one of these fields should be filled to find an element.
    """
    auto_id: str | None = Field(default=None, description="AutomationId of the element")
    name: str | None = Field(default=None, description="Visible text or Name of the element")
    name_re: str | None = Field(default=None, description="Regex for the visible text or name of the element")
    control_type: str | None = Field(default=None, description="Type of control (e.g., Button, Edit)")
    control_type_re: str | None = Field(default=None, description="Regex for the control type")
    class_name: str | None = Field(default=None, description="Internal class name of the element")
    class_name_re: str | None = Field(default=None, description="Regex for the class name")
    enabled: bool | None = Field(default=None, description="Whether the element is enabled")
    visible: bool | None = Field(default=None, description="Whether the element is visible")
    depth: int | None = Field(default=None, description="Search depth for this locator")

    found_index: int | None = Field(default=None, description="Index to select if multiple identical elements are found")

    def to_pywinauto_kwargs(self) -> dict:
        """
        Converts the locator into a dictionary suitable for pywinauto's .by() method.
        """
        exclude_fields = {}
        
        # Build kwargs, ignoring None values
        kwargs = {k: v for k, v in self.model_dump().items() if v is not None and k not in exclude_fields}
                        
        return kwargs


class ScenarioStep(BaseModel):
    """
    Represents a single step in a test scenario.
    """
    id: int = Field(..., description="Order number or unique identifier of the step")
    action_type: ScenarioStepType = Field(..., description="Action type")
    locators: list[UIElementLocator] = Field(default_factory=list, description="Chain of locators to build a path to the target element")
    
    value: str | None = Field(default=None, description="Value to input (for type_text) or time to wait (for wait)")
    description: str | None = Field(default=None, description="Human-readable description of the step")
    is_ai_suggested: bool = Field(default=False, description="Flag indicating if this step was proposed by AI")
    
    custom_code: str | None = Field(default=None, description="Inline Python code to execute")
