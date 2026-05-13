from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTreeWidget, 
                               QTreeWidgetItem, QPushButton, QLineEdit,
                               QHeaderView, QHBoxLayout, QMessageBox, QAbstractItemView,
                               QMenu)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QShortcut, QKeySequence

from uitestauto.models.project import TestCase
from uitestauto.models.element import ScenarioStep, ScenarioStepType
from uitestauto.core.project_manager import ProjectManager
from uitestauto.ui.dialogs.scenario_step_editor import ScenarioStepEditorDialog


class TestCaseScenarioEditorPanel(QWidget):
    """
    All test case actions are here
    """
    def __init__(self):
        super().__init__()
        self.project_manager = ProjectManager()
        self.current_test_case = self.project_manager.get_current_test_case()
        self.setup_ui()
        self.load_test_case(self.current_test_case)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Header Region
        self.header_label = QLabel(f"<h3>Test Case: {self.current_test_case.name if self.current_test_case else '-'}</h3>")
        layout.addWidget(self.header_label)

        # Toolbar Region
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        
        self.btn_move_up = QPushButton("Move up")
        self.btn_move_down = QPushButton("Move down")
        self.btn_duplicate = QPushButton("Duplicate")
        self.btn_delete = QPushButton("Delete")
        
        self.btn_add_action = QPushButton("Add Action")
        
        self.btn_move_up.clicked.connect(self.move_step_up)
        self.btn_move_down.clicked.connect(self.move_step_down)
        self.btn_duplicate.clicked.connect(self.duplicate_selected_step)
        self.btn_delete.clicked.connect(self.delete_selected_step)
        self.btn_add_action.clicked.connect(self.add_new_action)

        toolbar_layout.addWidget(self.btn_move_up)
        toolbar_layout.addWidget(self.btn_move_down)
        toolbar_layout.addWidget(self.btn_duplicate)
        toolbar_layout.addWidget(self.btn_delete)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.btn_add_action)
        
        toolbar_widget = QWidget()
        toolbar_widget.setLayout(toolbar_layout)
        layout.addWidget(toolbar_widget)

        # Content Region (Tree as List)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["#", "Action", "Target / Locator", "Value / Data", "Description"])
        
        # Shortcut for Delete
        self.shortcut_del = QShortcut(QKeySequence(Qt.Key.Key_Delete), self.tree)
        self.shortcut_del.activated.connect(self.delete_selected_step)
        
        # Tree configuration for List look
        self.tree.setRootIsDecorated(False) # Hide expand/collapse arrows
        self.tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setAlternatingRowColors(True)
        
        # Column resizing
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # Action
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)      # Target
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)      # Value
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)          # Description
        self.tree.setColumnWidth(2, 150)
        self.tree.setColumnWidth(3, 150)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)

        layout.addWidget(self.tree)
        
    @Slot(TestCase)
    def load_test_case(self, case: TestCase):
        self.current_test_case = case
        if self.current_test_case:
            self.header_label.setText(f"<h3>Test case: {self.current_test_case.name}</h3>")
            self.refresh_list()
        else:
            self.header_label.setText(f"<h3>Test case: -</h3>")
            self.tree.clear()

    def refresh_list(self):
        self.tree.clear()
        if not self.current_test_case:
            return
            
        for i, step in enumerate(self.current_test_case.steps):
            step.id = i + 1
            self._insert_item(step)
            
    def _insert_item(self, step: ScenarioStep):
        # Action string
        action_name = step.action_type.upper()
        action_icon = "🖱 " if "click" in action_name.lower() else "⌨ " if "input" in action_name.lower() else "⚙ "
        action_str = f"{action_icon}{action_name}"
        
        # Target string
        if step.action_type == ScenarioStepType.CUSTOM:
            if step.custom_code:
                first_line = step.custom_code.splitlines()[0] if step.custom_code else "..."
                target_str = f"Code: {first_line}"
            else:
                target_str = "[Empty custom code]"
        elif step.action_type != ScenarioStepType.WAIT and step.locators:
            last_loc = step.locators[-1]
            node_name = last_loc.name or last_loc.auto_id or last_loc.control_type or "Unknown"
            node_name = " ".join(node_name.splitlines())
            # Display parent depth indicator
            if len(step.locators) > 1:
                target_str = f"[{len(step.locators) - 1} parents] > {node_name}"
            else:
                target_str = node_name
        else:
            target_str = "-"
            
        if len(target_str) > 80:
            target_str = target_str[:77] + "..."

        if step.is_ai_suggested:
            step_idx_str = f"{step.id} [AI]"
        else:
            step_idx_str = str(step.id)

        # Create Tree Item
        item = QTreeWidgetItem(self.tree, [step_idx_str, action_str, target_str, "", ""])
        item.setData(0, Qt.ItemDataRole.UserRole, step)
        
        # Column 3: Data Input (QLineEdit)
        value_edit = QLineEdit(step.value if step.value else "")
        value_edit.setCursorPosition(0)
        value_edit.textChanged.connect(lambda text, s=step: self.update_step_value(s, text))
        self.tree.setItemWidget(item, 3, value_edit)

        # Column 4: Description (QLineEdit)
        desc_edit = QLineEdit(step.description if step.description else "")
        desc_edit.setCursorPosition(0)
        desc_edit.textChanged.connect(lambda text, s=step: self.update_step_description(s, text))
        self.tree.setItemWidget(item, 4, desc_edit)

    @Slot(ScenarioStep)
    def on_step_added(self, step: ScenarioStep):
        if not self.current_test_case:
            return
            
        step.id = len(self.current_test_case.steps) + 1
        self.current_test_case.add_step(step)
        self.project_manager.mark_dirty()
        self._insert_item(step)
        self.tree.scrollToBottom()

    def on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        step = item.data(0, Qt.ItemDataRole.UserRole)
        if step:
            self.edit_action(step)

    def show_context_menu(self, position):
        item = self.tree.itemAt(position)
        if not item: return
        
        menu = QMenu()
        menu.addAction("Edit Action").triggered.connect(lambda: self.edit_action(item.data(0, Qt.ItemDataRole.UserRole)))
        menu.addAction("Duplicate").triggered.connect(self.duplicate_selected_step)
        menu.addSeparator()
        menu.addAction("Move up").triggered.connect(self.move_step_up)
        menu.addAction("Move down").triggered.connect(self.move_step_down)
        menu.addSeparator()
        menu.addAction("Delete").triggered.connect(self.delete_selected_step)
        
        menu.exec(self.tree.viewport().mapToGlobal(position))

    def edit_action(self, step: ScenarioStep):
        dlg = ScenarioStepEditorDialog(self, step)
        if dlg.exec():
            # Apply changes
            # TODO: copy all fields?
            new_step = dlg.step
            step.action_type = new_step.action_type
            step.value = new_step.value
            step.description = new_step.description
            step.locators = new_step.locators
            step.custom_code = new_step.custom_code
            
            self.project_manager.mark_dirty()
            self.refresh_list()
            
    def add_new_action(self):
        if not self.current_test_case:
            QMessageBox.warning(self, "Error", "No active test case selected.")
            return
            
        step = ScenarioStep(id=0, action_type=ScenarioStepType.CLICK, locators=[], value="", description="")
        dlg = ScenarioStepEditorDialog(self, step)
        if dlg.exec():
            self.on_step_added(dlg.step)

    def update_step_value(self, step: ScenarioStep, text: str):
        if step.value != text:
            step.value = text
            self.project_manager.mark_dirty()

    def update_step_description(self, step: ScenarioStep, text: str):
        if step.description != text:
            step.description = text
            self.project_manager.mark_dirty()

    def move_step_up(self):
        if not self.current_test_case: return
        item = self.tree.currentItem()
        if not item: return
        
        index = self.tree.indexOfTopLevelItem(item)
        if index > 0:
            # Modify list
            steps = self.current_test_case.steps
            steps[index - 1], steps[index] = steps[index], steps[index - 1]
            self.project_manager.mark_dirty()
            self.refresh_list()
            # Restore selection
            self.tree.setCurrentItem(self.tree.topLevelItem(index - 1))

    def move_step_down(self):
        if not self.current_test_case: return
        item = self.tree.currentItem()
        if not item: return
        
        index = self.tree.indexOfTopLevelItem(item)
        steps = self.current_test_case.steps
        if index < len(steps) - 1:
            # Modify list
            steps[index + 1], steps[index] = steps[index], steps[index + 1]
            self.project_manager.mark_dirty()
            self.refresh_list()
            # Restore selection
            self.tree.setCurrentItem(self.tree.topLevelItem(index + 1))

    def duplicate_selected_step(self):
        if not self.current_test_case: return
        item = self.tree.currentItem()
        if not item: return
        
        step = item.data(0, Qt.ItemDataRole.UserRole)
        if step in self.current_test_case.steps:
            # Create a deep copy
            new_step = step.model_copy(deep=True)
            # Find insertion index (right after selected)
            index = self.tree.indexOfTopLevelItem(item)
            
            # Reassign IDs (handled automatically in refresh_list based on list order)
            self.current_test_case.steps.insert(index + 1, new_step)
            self.project_manager.mark_dirty()
            self.refresh_list()
            self.tree.setCurrentItem(self.tree.topLevelItem(index + 1))

    def delete_selected_step(self):
        if not self.current_test_case: return
        item = self.tree.currentItem()
        if not item: return
        
        step = item.data(0, Qt.ItemDataRole.UserRole)
        if step in self.current_test_case.steps:
            reply = QMessageBox.question(
                self,
                "Confirm Delete",
                f"Delete Step {step.id}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.current_test_case.steps.remove(step)
                self.project_manager.mark_dirty()
                self.refresh_list()


