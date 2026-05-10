"""
Abstract Base Classes for UiTestAuto plugin backends.

Each subsystem (Inspector, Recorder, Executor, Generator, ...) is defined here
as an abstract base class.
"""

from abc import ABC, abstractmethod
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from uitestauto.models.element import ScenarioStep, UIElementLocator
    from uitestauto.models.project import TestCase


class BaseInspector(ABC):
    """
    Windows enumeration and element tree building.
    """

    @abstractmethod
    def get_top_level_windows(self) -> list[dict]:  # TODO: typing
        """
        Returns a list of dicts with at least:
          { "name": str, "handle": int, "process_id": int }
        """

    @abstractmethod
    def get_window_tree(self, window_name: str | None = None, handle: int | None = None) -> dict | None:  # TODO: typing
        """
        Builds and returns a tree dict for the given window:
          {
            "display": str,
            "locators": list[UIElementLocator],
            "element_info": <native element object>,
            "children": [ <same structure>, ... ]
          }
        Returns None if the window cannot be found.
        """
    
    @abstractmethod
    def highlight_element(self, element):
        """
        Highlight an element.
        """
    
    @abstractmethod
    def dump_tree(self, window_name: str):
        """
        Dump the UI tree somewhere.
        # TODO: pass filename
        """


class BaseRecorder(ABC):
    """
    UI actions recording.
    Capturing input events and map them to ScenarioSteps.
    """

    @abstractmethod
    def start(self) -> None:
        """Begin recording user interactions."""

    @abstractmethod
    def stop(self) -> list["ScenarioStep"]:
        """
        Stop recording and return the captured steps.
        """

    @abstractmethod
    def quit(self) -> None:
        """Release all resources held by the recorder."""


class BaseExecutor(ABC):
    """
    Step executor.
    Implementations attempt to locate an element and perform an action,
    maybe recovering from bad situations (healing).
    """

    @abstractmethod
    def execute(
        self,
        step_type: str,
        locator_path: list["UIElementLocator"],
        value: str | None,
        step_id: int | None,
        ambiguity_resolver: Callable[[list], int] | None,
        post_action_func: Callable | None = None,
    ) -> None:
        """
        Execute a single step.
        """


class BaseGenerator(ABC):
    """
    Test script generator.
    Renders a TestCase into a test file.
    """

    @abstractmethod
    def generate(self, test_case: "TestCase", output_path: str) -> bool:
        """
        Render test_case into a test script at output_path.
        Returns True on success, False on failure.
        """


class BaseAIAgent(ABC):
    """
    AI Agent.
    Run reasoning loop to fulfill a user goal on a target window.
    """
    
    @classmethod
    def supported_models(cls) -> list[str]:
        """Return a list of AI models supported by this agent plugin."""
        return []

    @abstractmethod
    def run(
        self,
        user_goal: str,
        target_window_title: str,
        backend_name: str,
        log_callback: Callable[[str], None]
    ) -> list["ScenarioStep"]:
        """
        Execute the agent reasoning loop until the goal is achieved or it fails/cancels.
        Returns a list of ScenarioSteps that were successfully executed.
        """
        
    @abstractmethod
    def stop(self) -> None:
        """
        Stop loop.
        """
