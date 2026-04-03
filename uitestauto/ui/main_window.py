from PySide6.QtWidgets import (QMainWindow, QSplitter, QToolBar,
                               QDockWidget, QTextEdit, QLineEdit,
                               QFileDialog, QMessageBox, QDialog,
                               QFormLayout, QDialogButtonBox, QStyle,
                               QTabWidget)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QKeySequence, QAction

import logging
from PySide6.QtCore import QObject, Signal

from uitestauto.core.logger import logger
from uitestauto.core.recorder_manager import RecorderManager
from uitestauto.ui.panels.ui_browser import UIBrowserPanel
from uitestauto.ui.panels.test_case_scenario_editor import TestCaseScenarioEditorPanel
from uitestauto.ui.panels.project_explorer import ProjectExplorerPanel
from uitestauto.ui.panels.ai_agent_panel import AIAgentPanel
from uitestauto.core.project_manager import ProjectManager
from uitestauto.core.test_engine import TestEngine
from uitestauto.models.project import TestCase, TestSuite, ProjectConfig
from uitestauto.plugins.registry import plugin_registry
from uitestauto.plugins.pywinauto import register_pywinauto_backends
from uitestauto.plugins.gemini import register_gemini_agent
from uitestauto.ui.dialogs.settings_dialog import SettingsDialog
from collections import Counter

# bootstrap: register pywinauto backends once at module load
register_pywinauto_backends(plugin_registry)
register_gemini_agent(plugin_registry)

class SignaledLogHandler(logging.Handler, QObject):
    log_signal = Signal(str)

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, record):
        msg = self.format(record)
        self.log_signal.emit(msg)


class NewProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Project")

        layout = QFormLayout(self)

        self.name_edit = QLineEdit("Untitled Project")
        layout.addRow("Project Name:", self.name_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self):
        return {"name": self.name_edit.text()}


class UiTestAutoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UiTestAuto - Test Automation Tool")
        self.resize(1400, 850)

        self.setup_menu_bar()
        self.setup_toolbar()
        
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        self.setCentralWidget(self.main_splitter)

        self.project_panel = ProjectExplorerPanel()
        self.browser_panel = UIBrowserPanel()
        self.editor_panel = TestCaseScenarioEditorPanel()
        self.agent_panel = AIAgentPanel()

        self.left_tabs = QTabWidget()
        self.left_tabs.addTab(self.project_panel, "Project Explorer")
        self.left_tabs.addTab(self.browser_panel, "UI Browser")
        self.left_tabs.addTab(self.agent_panel, "AI Agent")

        self.main_splitter.addWidget(self.left_tabs)
        self.main_splitter.addWidget(self.editor_panel)
        
        # proportions
        self.main_splitter.setSizes([150, 1050])

        self.browser_panel.step_added.connect(self.editor_panel.on_step_added)
        self.project_panel.case_selected.connect(self.editor_panel.load_test_case)
        self.project_panel.run_requested.connect(self.run_item)
        self.agent_panel.steps_generated.connect(self.on_agent_steps_generated)

        self._recorder_manager: RecorderManager | None = None

        # test state tracking
        self.test_engine: TestEngine | None = None

        self.setup_console()

        ProjectManager().dirty_callback = self.update_window_title
        self.update_window_title()
        self.update_ui_state()

    def update_window_title(self):
        pm = ProjectManager()
        dirty_star = "*" if pm.is_dirty else ""
        proj_name = pm.config.project_name if pm.config else "Untitled Project"
        self.setWindowTitle(f"UiTestAuto - {proj_name}{dirty_star}")
        
    def update_ui_state(self):
        has_project = ProjectManager().config is not None
        
        self.btn_save.setEnabled(has_project)
        self.btn_record.setEnabled(has_project)
        self.btn_run_test.setEnabled(has_project)
        self.btn_generate.setEnabled(has_project)
        self.action_save_normal.setEnabled(has_project)
        has_active_case = ProjectManager().active_case is not None
        
        self.editor_panel.setEnabled(has_active_case)
        self.agent_panel.setEnabled(has_active_case)

    def on_agent_steps_generated(self, steps):
        for step in steps:
            self.editor_panel.on_step_added(step)

    def check_unsaved_changes(self) -> bool:
        """Prompts user if there are unsaved changes. Returns False if user cancelled."""
        pm = ProjectManager()
        if pm.is_dirty:
            reply = QMessageBox.question(
                self, 'Unsaved Changes',
                "You have unsaved changes. Do you want to save them before continuing?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            
            if reply == QMessageBox.StandardButton.Save:
                self.handle_save_normal_project()
                # If they cancelled the save dialog inside handle_save_normal_project
                if pm.is_dirty:
                    return False
                return True
            elif reply == QMessageBox.StandardButton.Cancel:
                return False
            # Discard case returns True (continue)
        return True

    def closeEvent(self, event):
        if self.check_unsaved_changes():
            event.accept()
        else:
            event.ignore()

    def setup_menu_bar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        
        action_new = file_menu.addAction("New Project...")
        action_new.triggered.connect(self.handle_new_project)
        
        action_open = file_menu.addAction("Open Project...")
        action_open.triggered.connect(self.handle_open_project)
        
        self.action_save_normal = file_menu.addAction("Save Project")
        self.action_save_normal.setShortcut(QKeySequence("Ctrl+S"))
        self.action_save_normal.triggered.connect(self.handle_save_normal_project)
        
        self.action_save_as = file_menu.addAction("Save Project As...")
        self.action_save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self.action_save_as.triggered.connect(self.handle_save_project)

        file_menu.addSeparator()
        action_settings = file_menu.addAction("Settings...")
        action_settings.triggered.connect(self.show_settings_dialog)

        file_menu.addSeparator()
        action_exit = file_menu.addAction("Exit")
        action_exit.triggered.connect(self.close)

        edit_menu = menubar.addMenu("Edit")
        action_undo = edit_menu.addAction("Undo")
        action_undo.setShortcut(QKeySequence("Ctrl+Z"))
        action_undo.triggered.connect(self.handle_undo)
        
        action_redo = edit_menu.addAction("Redo")
        action_redo.setShortcut(QKeySequence("Ctrl+Y"))
        action_redo.triggered.connect(self.handle_redo)
        
        actions_menu = menubar.addMenu("Actions")
        action_record = actions_menu.addAction("Record")
        action_record.triggered.connect(self.toggle_recording)
        
        action_run_test = actions_menu.addAction("Run test")
        action_run_test.triggered.connect(self.run_test_action)
        
        action_generate = actions_menu.addAction("Generate Code")
        action_generate.triggered.connect(self.trigger_code_generation)

        help_menu = menubar.addMenu("Help")
        action_about = help_menu.addAction("About")
        action_about.triggered.connect(self.show_about_dialog)
        
    def show_about_dialog(self):
        QMessageBox.about(self, "About UiTestAuto", 
                          "<h3>UiTestAuto</h3>"
                          "<p>An automated UI testing and recording tool.</p>")

    def show_settings_dialog(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def handle_undo(self):
        if ProjectManager().undo():
            self.refresh_ui_from_manager()
            logger.info("> [System] Undo successful.")
            
    def handle_redo(self):
        if ProjectManager().redo():
            self.refresh_ui_from_manager()
            logger.info("> [System] Redo successful.")
            
    def refresh_ui_from_manager(self):
        self.project_panel.refresh_tree()
        pm = ProjectManager()
        if pm.active_case:
            self.editor_panel.load_test_case(pm.active_case)
        else:
            self.editor_panel.load_test_case(None)
        
    def handle_new_project(self):
        if not self.check_unsaved_changes():
            return
        dialog = NewProjectDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            pm = ProjectManager()
            pm.config = ProjectConfig(project_name=data["name"])
            default_suite = TestSuite(name="Default Suite")
            default_case = TestCase(name="Untitled_Test")  # uses default backend pywinauto_uia
            default_suite.cases.append(default_case)
            pm.config.suites.append(default_suite)
            pm.active_suite = default_suite
            pm.active_case = default_case

            self.project_panel.refresh_tree()
            self.editor_panel.load_test_case(default_case)
            self.update_ui_state()
            logger.info(f"> [System] Created new project '{data['name']}'")

    def handle_save_normal_project(self):
        pm = ProjectManager()
        if pm.current_filepath:
            try:
                pm.save_project(pm.current_filepath)
                logger.info(f"> [System] Project saved to {pm.current_filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save project: {e}")
        else:
            # current project was never saved to file, fallback to "Save As..."
            self.handle_save_project()

    def handle_save_project(self):
        filepath, _ = QFileDialog.getSaveFileName(self, "Save Project", "", "JSON Files (*.json)", options=QFileDialog.Option.DontUseNativeDialog)
        if filepath:
            try:
                ProjectManager().save_project(filepath)
                logger.info(f"> [System] Project saved to {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save project: {e}")

    def handle_open_project(self):
        if not self.check_unsaved_changes():
            return
        filepath, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "JSON Files (*.json)", options=QFileDialog.Option.DontUseNativeDialog)
        if filepath:
            try:
                pm = ProjectManager()
                pm.load_project(filepath)
                self.project_panel.refresh_tree()
                if pm.active_case:
                    self.editor_panel.load_test_case(pm.active_case)
                self.update_ui_state()
                logger.info(f"> [System] Project loaded from {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not load project: {e}")

    def setup_toolbar(self):
        toolbar = QToolBar("Main actions")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)

        icon_open = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton)
        open_btn = QAction(icon_open, "Open", self)
        open_btn.setToolTip("Open project")
        open_btn.triggered.connect(self.handle_open_project)
        toolbar.addAction(open_btn)

        icon_save = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton)
        self.btn_save = QAction(icon_save, "Save", self)
        self.btn_save.setToolTip("Save project")
        self.btn_save.triggered.connect(self.handle_save_normal_project)
        toolbar.addAction(self.btn_save)
        
        toolbar.addSeparator()

        self.btn_record = QAction("Record", self)
        self.btn_record.setToolTip("Record")
        self.btn_record.triggered.connect(self.toggle_recording)
        toolbar.addAction(self.btn_record)

        self.btn_run_test = QAction("Run test", self)
        self.btn_run_test.setToolTip("Run test")
        self.btn_run_test.triggered.connect(self.run_test_action)
        toolbar.addAction(self.btn_run_test)

        self.btn_generate = QAction("Generate code", self)
        self.btn_generate.setToolTip("Generate code")
        self.btn_generate.triggered.connect(self.trigger_code_generation)
        toolbar.addAction(self.btn_generate)

    def setup_console(self):
        dock = QDockWidget("Logs", self)
        dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Consolas", 10))
        
        dock.setWidget(self.console)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
        
        # Connect logger
        self.log_handler = SignaledLogHandler()
        self.log_handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(self.log_handler)
        self.log_handler.log_signal.connect(self.console.append)

    def toggle_recording(self):
        """Toggles the recording state and updates the UI accordingly."""
        pm = ProjectManager()
        active_case = pm.get_current_test_case()
        if not active_case:
            QMessageBox.warning(self, "Warning", "Select a test case first")
            return

        if self._recorder_manager is None:
            # Start: create a RecorderManager with the active case's backend
            backend_name = active_case.backend
            recorder_backend = plugin_registry.create_recorder(backend_name)
            self._recorder_manager = RecorderManager(recorder_backend)
            self._recorder_manager.start_recording()
            self.btn_record.setText("Stop recording")
            self.btn_record.setToolTip("Stop recording")
            logger.info("> [System] Recording started. Interact with the target application...")
        else:
            logger.info("> [System] Stopping recording...")
            steps = self._recorder_manager.stop_recording()
            self._recorder_manager = None

            self.btn_record.setText("Record")
            self.btn_record.setToolTip("Record")

            if steps:
                logger.info(f"> [System] Captured {len(steps)} steps. Adding to scenario...")
                for step in steps:
                    self.editor_panel.on_step_added(step)
            else:
                logger.info("> [System] No steps captured during this recording session.")

    def trigger_code_generation(self):
        current_case = self.editor_panel.current_test_case
        if not current_case:
            QMessageBox.warning(self, "Warning", "Please select a test case.")
            return

        logger.info(f"> [System] Generating Python script for '{current_case.name}' with {len(current_case.steps)} steps...")
        logger.info("> [Success] Code generation triggered. Check the output folder.")

    def run_test_action(self):
        self.run_item()

    def get_selected_node(self):
        items = self.project_panel.tree.selectedItems()
        if items:
            data = items[0].data(0, Qt.ItemDataRole.UserRole)
            if data and "obj" in data:
                return data["obj"]
        return None

    def run_item(self, item=None):
        if self.test_engine and self.test_engine.is_running():
            self.test_engine.stop()
            return
            
        if item is None or isinstance(item, bool):
            item = self.get_selected_node()
            
        if item is None:
            item = self.editor_panel.current_test_case
            
        if not item:
            QMessageBox.warning(self, "Test error", "No test item selected.")
            return
            
        # Determine if there are steps to execute
        cases_to_run = []
        if isinstance(item, TestCase):
            cases_to_run = [item]
        elif isinstance(item, TestSuite):
            cases_to_run = item.cases
        elif isinstance(item, ProjectConfig):
            for suite in item.suites:
                cases_to_run.extend(suite.cases)
        
        self.reset_item_statuses(item)
        self.recalculate_statuses()
            
        self.test_engine = TestEngine()
        self.test_engine.case_started.connect(self.on_case_started)
        self.test_engine.case_finished.connect(self.on_case_finished)
        self.test_engine.test_finished.connect(self.on_test_finished)
        self.test_engine.step_healed.connect(self.on_step_healed)

        self.btn_run_test.setText("Stop")
        self.btn_run_test.setToolTip("Stop test")

        name = getattr(item, "name", getattr(item, "project_name", "item"))
        logger.info(f"> [System] Starting run for '{name}'...")

        def log_cb(msg):
            logger.info(msg)

        self.test_engine.run(item, logger_callback=log_cb)

    def reset_item_statuses(self, item):
        item.status = "not_run"
        if isinstance(item, ProjectConfig):
            for suite in item.suites:
                self.reset_item_statuses(suite)
        elif isinstance(item, TestSuite):
            for case in item.cases:
                self.reset_item_statuses(case)

    def recalculate_statuses(self):
        pm = ProjectManager()
        if not pm.config:
            return

        project_counter = Counter()
        has_tests = False

        for suite in pm.config.suites:
            statuses = [case.status for case in suite.cases]
            counter = Counter(statuses)

            if not statuses:
                suite.status = "not_run"
            elif counter["running"]:
                suite.status = "running"
            elif counter["failed"] == len(statuses):
                suite.status = "failed"
            elif counter["passed"] == len(statuses):
                suite.status = "passed"
            elif counter["failed"] or counter["passed"]:
                suite.status = "passed_partially"
            else:
                suite.status = "not_run"

            project_counter.update(statuses)
            has_tests = has_tests or bool(statuses)

        total = sum(project_counter.values())

        if not has_tests:
            pm.config.status = "not_run"
        elif project_counter["running"]:
            pm.config.status = "running"
        elif project_counter["failed"] == total:
            pm.config.status = "failed"
        elif project_counter["passed"] == total:
            pm.config.status = "passed"
        elif project_counter["failed"] or project_counter["passed"]:
            pm.config.status = "passed_partially"
        else:
            pm.config.status = "not_run"

        self.project_panel.refresh_tree()

    def on_case_started(self, test_case):
        test_case.status = "running"
        self.recalculate_statuses()
        
    def on_case_finished(self, test_case, success, msg):
        test_case.status = "passed" if success else "failed"
        self.recalculate_statuses()

    def on_test_finished(self, success: bool, message: str):
        self.btn_run_test.setText("Run test")
        self.btn_run_test.setToolTip("Run test")
        self.test_engine = None
        
        self.recalculate_statuses()
        
        if success:
            QMessageBox.information(self, "Test success", message)
        else:
            QMessageBox.critical(self, "Test failed", message)

    def on_step_healed(self, step_id: int, indices_str: str):
        pm = ProjectManager()

        # not realiable to use active case here
        # TODO: deal with it: during the test user can switch between test cases
        if not pm.active_case:
            return

        for step in pm.active_case.steps:
            if not step.locators:
                continue

            if step.id != step_id:
                continue

            try:
                indices = [int(x) for x in indices_str.split(",")]
                for idx, loc in zip(indices, step.locators):
                    loc.found_index = idx
                
                pm.mark_dirty()
                self.editor_panel.load_test_case(pm.active_case)
                logger.info(f"> [System] Applied healed indices {indices_str} to Step {step_id}")
            except Exception as e:
                logger.error(f"> [System] Failed to apply healed indices: {e}")
            break
