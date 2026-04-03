"""
Data models representing the test management hierarchy: Project -> Suite -> Case.
"""

from pydantic import BaseModel, Field
from uitestauto.models.element import ScenarioStep


class TestCase(BaseModel):
    """
    Represents a single test script containing a sequence of actions.
    The *backend* field names a registered PluginRegistry backend
    """
    name: str = Field(..., description="Name of the test case")
    description: str | None = Field(default=None, description="Purpose of this test case")
    steps: list[ScenarioStep] = Field(default_factory=list, description="List of actions (scenario) to execute in order")
    backend: str = Field(default="pywinauto_uia", description="Plugin backend used to run this test case")
    status: str = Field(default="not_run", exclude=True, description="Transient execution status: not_run, running, passed, failed")

    def add_step(self, step: ScenarioStep):
        self.steps.append(step)


class TestSuite(BaseModel):
    """
    A logical grouping of test cases. 
    """
    name: str = Field(..., description="Name of the test suite")
    cases: list[TestCase] = Field(default_factory=list, description="Test cases belonging to this suite")
    status: str = Field(default="not_run", exclude=True, description="Transient execution status: not_run, running, passed, failed")


class ProjectConfig(BaseModel):
    """
    Global project configuration.
    Saved as a .json file on disk.
    """
    project_name: str = Field(..., description="Name of the project")
    suites: list[TestSuite] = Field(default_factory=list, description="List of test suites in the project")
    status: str = Field(default="not_run", exclude=True, description="Transient execution status: not_run, running, passed, failed")
