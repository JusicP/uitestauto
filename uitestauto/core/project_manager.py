from typing import Callable, Tuple
from uitestauto.models.project import ProjectConfig, TestSuite, TestCase
from uitestauto.plugins.registry import plugin_registry
from uitestauto.plugins.base import BaseInspector, BaseRecorder, BaseHealer, BaseGenerator

class ProjectManager:
    """
    Singleton-like manager for the current active project.
    Holds the root ProjectConfig and provides helpers to get the active test case.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ProjectManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.config: ProjectConfig | None = None
        self.active_suite: TestSuite | None = None
        self.active_case: TestCase | None = None
        self.current_filepath: str | None = None
        
        self.is_dirty: bool = False
        self.dirty_callback: Callable | None = None
        self.history: list[str] = []
        self.history_index: int = -1

    def get_current_test_case(self) -> TestCase | None:
        return self.active_case

    def get_current_suite(self) -> TestSuite | None:
        return self.active_suite

    def set_active_case(self, case: TestCase | None):
        self.active_case = case

    def mark_dirty(self):
        self.is_dirty = True
        
        if not self.config:
            if self.dirty_callback:
                self.dirty_callback()
            return
            
        # Snapshot state for Undo/Redo
        current_state = self.config.model_dump_json()
        
        # If we are not at the end of history and we made a change, truncate the future
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]
            
        # Avoid saving identical consecutive states
        if not self.history or self.history[-1] != current_state:
            self.history.append(current_state)
            self.history_index += 1
            
        if self.dirty_callback:
            self.dirty_callback()
            
    def mark_clean(self):
        self.is_dirty = False
        if self.dirty_callback:
            self.dirty_callback()

    def undo(self) -> bool:
        if self.history_index > 0:
            self.history_index -= 1
            self._restore_from_snapshot(self.history[self.history_index])
            # State is strictly dirty if we undo, as it changes from the current saved file
            self.is_dirty = True
            if self.dirty_callback: self.dirty_callback()
            return True
        return False

    def redo(self) -> bool:
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self._restore_from_snapshot(self.history[self.history_index])
            self.is_dirty = True
            if self.dirty_callback: self.dirty_callback()
            return True
        return False
        
    def _restore_from_snapshot(self, json_data: str):
        # Save old active names to try to restore them
        old_suite_name = self.active_suite.name if self.active_suite else None
        old_case_name = self.active_case.name if self.active_case else None
        
        self.config = ProjectConfig.model_validate_json(json_data)
        
        # Re-attach active suite/case by name, or fallback to defaults
        self.active_suite = None
        self.active_case = None
        
        for s in self.config.suites:
            if s.name == old_suite_name:
                self.active_suite = s
                for c in s.cases:
                    if c.name == old_case_name:
                        self.active_case = c
                        break
                break
                
        if self.config.suites and not self.active_suite:
            self.active_suite = self.config.suites[0]
            if self.active_suite.cases:
                self.active_case = self.active_suite.cases[0]

    def save_project(self, filepath: str):
        """Saves the current ProjectConfig to a JSON file."""
        if not self.config:
            return
        
        import json
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.config.model_dump_json(indent=4, exclude_none=True))
        self.current_filepath = filepath
        self.mark_clean()

    def load_project(self, filepath: str):
        """Loads a ProjectConfig from a JSON file and resets active selections."""
        with open(filepath, 'r', encoding='utf-8') as f:
            json_data = f.read()
            self.config = ProjectConfig.model_validate_json(json_data)
        
        self.current_filepath = filepath
        self.history = [json_data]
        self.history_index = 0
            
        # Reset active selections
        if self.config.suites:
            self.active_suite = self.config.suites[0]
            if self.active_suite.cases:
                self.active_case = self.active_suite.cases[0]
            else:
                self.active_case = None
        else:
            self.active_suite = None
            self.active_case = None
            
        self.mark_clean()

    def get_backend_for_case(
        self, case: TestCase
    ) -> Tuple[BaseInspector, BaseRecorder, BaseHealer, BaseGenerator]:
        """
        Resolve and return fresh backend instances for the given TestCase.
        The backend name (e.g. 'pywinauto_uia') is read from case.backend.
        Raises KeyError if the backend is not registered.
        """
        name = case.backend
        inspector = plugin_registry.create_inspector(name)
        recorder = plugin_registry.create_recorder(name)
        healer = plugin_registry.create_healer(name)
        generator = plugin_registry.create_generator(name)
        return inspector, recorder, healer, generator
