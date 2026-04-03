from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTextEdit, QPushButton, QLabel, QMessageBox,
    QComboBox, QSizePolicy
)
from PySide6.QtCore import QThread, Signal

from uitestauto.plugins.registry import plugin_registry
from uitestauto.core.logger import logger
from uitestauto.core.project_manager import ProjectManager
from uitestauto.core.settings import SettingsManager

class AIAgentWorker(QThread):
    log_signal = Signal(str)
    finished_signal = Signal(list, bool, str)  # steps, success, message
    
    def __init__(self, backend_name: str, target_window: str, goal: str):
        super().__init__()
        self.backend_name = backend_name
        self.target_window = target_window
        self.goal = goal
        self.runner = None
        
    def run(self):
        try:
            settings = SettingsManager()
            agent_plugin_name = settings.get_ai_agent_plugin()
            self.runner = plugin_registry.create_ai_agent(agent_plugin_name)
            
            # Forward logs from runner to the UI thread
            def log_callback(msg):
                self.log_signal.emit(msg)
                logger.info(msg)
                
            steps = self.runner.run(self.goal, self.target_window, self.backend_name, log_callback)
            
            self.finished_signal.emit(steps, True, "Agent execution finished.")
        except Exception as e:
            self.finished_signal.emit([], False, f"Agent execution failed: {e}")
            
    def stop(self):
        if self.runner:
            self.runner.is_running = False
            self.log_signal.emit("[System] Stopping agent execution...")


class AIAgentPanel(QWidget):
    steps_generated = Signal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.worker = None
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)

        form_layout = QFormLayout()

        target_layout = QHBoxLayout()
        self.target_window_input = QComboBox()
        self.target_window_input.setEditable(True)

        self.target_window_input.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        self.target_window_input.setMinimumWidth(100)
        
        self.btn_refresh_targets = QPushButton("↻")
        self.btn_refresh_targets.setToolTip("Refresh window list")
        self.btn_refresh_targets.clicked.connect(self.refresh_targets)
        self.btn_refresh_targets.setMaximumWidth(30)
        target_layout.addWidget(self.target_window_input)
        target_layout.addWidget(self.btn_refresh_targets)
        
        form_layout.addRow("Target window:", target_layout)
        
        self.goal_input = QTextEdit()
        self.goal_input.setPlaceholderText("e.g. Type 1234 and click '='")
        self.goal_input.setMaximumHeight(80)
        self.goal_input.setMinimumWidth(100)
        form_layout.addRow("Goal:", self.goal_input)
        
        layout.addLayout(form_layout)
        
        btn_layout = QHBoxLayout()
        self.btn_run = QPushButton("Run thinking")
        self.btn_run.clicked.connect(self.toggle_agent)
        btn_layout.addWidget(self.btn_run)
        
        self.btn_clear = QPushButton("Clear console")
        self.btn_clear.clicked.connect(self.clear_console)
        btn_layout.addWidget(self.btn_clear)
        
        layout.addLayout(btn_layout)
        
        layout.addWidget(QLabel("Agent output:"))
        
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setMinimumWidth(100)
        font = self.console.font()
        font.setFamily("Consolas")
        font.setPointSize(9)
        self.console.setFont(font)
        layout.addWidget(self.console, stretch=1)
        
    def refresh_targets(self):
        pm = ProjectManager()
        active_case = pm.get_current_test_case()
        backend_name = active_case.backend if active_case else "pywinauto_uia"
        
        try:
            inspector = plugin_registry.create_inspector(backend_name)
            windows = inspector.get_top_level_windows()
            
            # FIXME: needed?
            # Store whatever the user typed or selected previously
            # current = self.target_window_input.currentText()
            
            self.target_window_input.clear()

            # FIXME: needed?
            names = set()
            for win in windows:
                n = win.get("name", "").strip()
                if n:
                    names.add(n)
                    
            sorted_names = sorted(list(names))
            self.target_window_input.addItems(sorted_names)
            
            # if current:
            #    self.target_window_input.setCurrentText(current)
                
        except Exception as e:
            logger.error(f"[Agent] Failed to refresh UI windows: {e}")
        
    def clear_console(self):
        self.console.clear()
        
    def log_message(self, msg: str):
        self.console.append(msg)
        
    def toggle_agent(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.btn_run.setText("Stopping...")
            self.btn_run.setEnabled(False)
            return
            
        target = self.target_window_input.currentText().strip()
        goal = self.goal_input.toPlainText().strip()
        
        if not target or not goal:
            QMessageBox.warning(self, "Missing fields", "Please provide both target window and a Prompt/Goal.")
            return
            
        pm = ProjectManager()
        active_case = pm.get_current_test_case()
        if not active_case:
            QMessageBox.warning(self, "No test case", "Please select a test case from the Project Explorer first.")
            return
            
        backend_name = active_case.backend
        
        if not plugin_registry.is_registered(backend_name):
            QMessageBox.warning(self, "Backend error", f"Backend '{backend_name}' is not registered.")
            return

        self.console.clear()
        self.btn_run.setText("Stop thinking")
        
        self.worker = AIAgentWorker(backend_name, target, goal)
        self.worker.log_signal.connect(self.log_message)
        self.worker.finished_signal.connect(self.on_agent_finished)
        self.worker.start()
        
    def on_agent_finished(self, steps, success, message):
        self.btn_run.setText("Run thinking")
        self.btn_run.setEnabled(True)
        
        if success:
            self.log_message(f"\n> {message}")
            if steps:
                self.log_message(f"> Found {len(steps)} successful steps.")
                self.steps_generated.emit(steps)
        else:
            self.log_message(f"\n> ERROR: {message}")
            QMessageBox.critical(self, "Agent error", message)
