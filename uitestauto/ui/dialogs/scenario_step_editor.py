from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QComboBox, QLineEdit, 
                               QDialogButtonBox, QWidget, QListWidget, QGroupBox, QHBoxLayout, 
                               QPushButton, QListWidgetItem, QScrollArea, QSplitter,
                               QTextEdit, QStackedWidget, QSizePolicy)
from PySide6.QtCore import Qt
from uitestauto.models.element import ScenarioStep, UIElementLocator, ScenarioStepType, ClickValue

class ScenarioStepEditorDialog(QDialog):
    def __init__(self, parent, step: ScenarioStep):
        super().__init__(parent)
        self.setWindowTitle("Scenario step editor")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        
        # deep copy action so we can modify it safely without updating original model until OK is pressed
        self.step = step.model_copy(deep=True)
            
        self.current_selected_node = None  # index
        self.loc_edits: dict[str, QLineEdit] = {}  # Holds reference to QLineEdits for the currently displayed node
        
        self.setup_ui()
        self.refresh_list()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Top section: basic action info
        basic_group = QGroupBox("Action information")
        basic_layout = QFormLayout(basic_group)
        
        self.combo_type = QComboBox()
        self.combo_type.addItems([s.value for s in ScenarioStepType])
        self.combo_type.setCurrentText(self.step.action_type)
        self.combo_type.currentTextChanged.connect(self.on_action_type_changed)
        basic_layout.addRow("Action type:", self.combo_type)
        
        self.value_widget_stack = QStackedWidget()
        
        self.edit_value_text = QTextEdit(self.step.value if self.step.value else "")
        self.edit_value_text.setMaximumHeight(60)
        
        self.edit_value_combo = QComboBox()
        self.edit_value_combo.addItems([e.value for e in ClickValue])

        self.value_widget_stack.addWidget(self.edit_value_text) # index 0
        self.value_widget_stack.addWidget(self.edit_value_combo) # index 1
        
        basic_layout.addRow("Value/Data:", self.value_widget_stack)
        
        self.edit_desc = QTextEdit(self.step.description if self.step.description else "")
        self.edit_desc.setMaximumHeight(60)
        basic_layout.addRow("Description:", self.edit_desc)
        
        self.edit_custom_code = QTextEdit("")
        self.edit_custom_code.setPlainText(self.step.custom_code if self.step.custom_code else "")
        self.edit_custom_code.setMaximumHeight(80)
        basic_layout.addRow("Custom code (inline):", self.edit_custom_code)
        
        layout.addWidget(basic_group)
        self.on_action_type_changed(self.combo_type.currentText())
        
        # Middle section: locator path list
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: list of locators
        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(0,0,0,0)
        
        self.locator_list = QListWidget()
        self.locator_list.currentRowChanged.connect(self.on_locator_selected)
        list_layout.addWidget(self.locator_list)
        
        btn_layout = QHBoxLayout()
        self.btn_add_locator = QPushButton("Add")
        self.btn_del_locator = QPushButton("Remove")
        self.btn_move_up = QPushButton("Up")
        self.btn_move_down = QPushButton("Down")
        
        self.btn_add_locator.clicked.connect(self.add_locator)
        self.btn_del_locator.clicked.connect(self.remove_locator)
        self.btn_move_up.clicked.connect(self.move_up_locator)
        self.btn_move_down.clicked.connect(self.move_down_locator)
        
        btn_layout.addWidget(self.btn_add_locator)
        btn_layout.addWidget(self.btn_del_locator)
        btn_layout.addWidget(self.btn_move_up)
        btn_layout.addWidget(self.btn_move_down)
        list_layout.addLayout(btn_layout)
        
        splitter.addWidget(list_container)
        
        # Right side: editable properties for selected locator
        self.props_container = QGroupBox("Locator properties")
        self.props_layout = QVBoxLayout(self.props_container)
        
        self.props_scroll = QScrollArea()
        self.props_scroll.setWidgetResizable(True)
        self.props_widget = QWidget()
        self.props_form = QFormLayout(self.props_widget)
        self.props_scroll.setWidget(self.props_widget)
        self.props_layout.addWidget(self.props_scroll)
        
        splitter.addWidget(self.props_container)
        splitter.setSizes([300, 500])
        layout.addWidget(splitter, stretch=1)
        
        # bottom
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        btn_box.accepted.connect(self.accept_dialog)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def refresh_list(self):
        """
        Rebuilds the locator list and restores the selection.
        """
        old_row = self.locator_list.currentRow()
        self.locator_list.clear()
        
        for i, loc in enumerate(self.step.locators):
            ctype = loc.control_type or ""
            name = loc.name or ""
            display_str = f"[{ctype}] {name}" if ctype or name else "[]"
            item = QListWidgetItem(f"Locator {i}: {display_str}")
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.locator_list.addItem(item)
            
        if old_row >= 0 and old_row < self.locator_list.count():
            self.locator_list.setCurrentRow(old_row)
        elif self.locator_list.count() > 0:
            self.locator_list.setCurrentRow(self.locator_list.count() - 1)
            
    def add_locator(self):
        self.save_current_props()
        self.step.locators.append(UIElementLocator())
        self.refresh_list()
        self.locator_list.setCurrentRow(self.locator_list.count() - 1)

    def remove_locator(self):
        item = self.locator_list.currentItem()
        if not item: return
        index = item.data(Qt.ItemDataRole.UserRole)
            
        self.current_selected_node = None
        self.loc_edits.clear()
        
        self.step.locators.pop(index)
        self.refresh_list()
        
    def move_up_locator(self):
        item = self.locator_list.currentItem()
        if not item: return
        index = item.data(Qt.ItemDataRole.UserRole)
        if index == 0: return
        
        self.save_current_props()
        locs = self.step.locators
        locs[index - 1], locs[index] = locs[index], locs[index - 1]
        
        self.current_selected_node = None
        self.refresh_list()
        self.locator_list.setCurrentRow(index - 1)
        
    def on_action_type_changed(self, new_type: str):
        if new_type == ScenarioStepType.CLICK:
            self.value_widget_stack.setCurrentIndex(1)
            self.value_widget_stack.setFixedHeight(self.edit_value_combo.sizeHint().height())
            if self.step.value and self.step.value in [e.value for e in ClickValue]:
                 self.edit_value_combo.setCurrentText(self.step.value)
        else:
            self.value_widget_stack.setCurrentIndex(0)
            self.value_widget_stack.setMinimumHeight(0)
            self.value_widget_stack.setMaximumHeight(60)
        
    def move_down_locator(self):
        item = self.locator_list.currentItem()
        if not item: return
        index = item.data(Qt.ItemDataRole.UserRole)
        if index >= len(self.step.locators) - 1: return
        
        self.save_current_props()
        locs = self.step.locators
        locs[index + 1], locs[index] = locs[index], locs[index + 1]
        
        self.current_selected_node = None
        self.refresh_list()
        self.locator_list.setCurrentRow(index + 1)

    def on_locator_selected(self, row: int):
        if row < 0: return
        item = self.locator_list.item(row)
        if not item: return
        
        self.save_current_props()
        
        self.current_selected_node = item.data(Qt.ItemDataRole.UserRole)
        self.build_props_form()
        
    def build_props_form(self):
        """
        Constructs QLineEdits for the currently selected locator node.
        """
        if self.current_selected_node is None: return
        
        while self.props_form.count():
            child = self.props_form.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        self.loc_edits.clear()
        
        index = self.current_selected_node
        fields = ["auto_id", "name", "name_re", "control_type", "control_type_re", "class_name", "class_name_re", "found_index", "enabled", "visible"]
        
        loc = self.step.locators[index]
        for f in fields:
            val = getattr(loc, f, None)
            edit = QLineEdit(str(val) if val is not None else "")
            edit.textChanged.connect(self.schedule_list_refresh)
            self.loc_edits[f] = edit
            self.props_form.addRow(f + ":", edit)
                
    def schedule_list_refresh(self):
        self.save_current_props()
        
        if self.current_selected_node is None: return
        index = self.current_selected_node
        item = self.locator_list.currentItem()
        if not item: return
        
        loc = self.step.locators[index]
        ctype = loc.control_type or ""
        name = loc.name or ""
        display_str = f"[{ctype}] {name}" if ctype or name else "[]"
        item.setText(f"Locator {index}: {display_str}")
            
    def save_current_props(self):
        """Saves values from QLineEdits to the action object."""
        if self.current_selected_node is None or not self.loc_edits:
            return
            
        index = self.current_selected_node
        
        def process_val(val_str, field_name):
            if not val_str: return None
            if field_name == "found_index":
                try:
                    return int(val_str)
                except ValueError:
                    return None
            return val_str
        
        loc = self.step.locators[index]
        for f, edit in self.loc_edits.items():
            val = process_val(edit.text(), f)
            setattr(loc, f, val)

    def accept_dialog(self):
        # save whatever is currently being edited
        self.save_current_props()
        
        self.step.action_type = ScenarioStepType(self.combo_type.currentText())
        
        if self.step.action_type == ScenarioStepType.CLICK:
            self.step.value = self.edit_value_combo.currentText()
        else:
            self.step.value = self.edit_value_text.toPlainText() if self.edit_value_text.toPlainText() else None
            
        self.step.description = self.edit_desc.toPlainText() if self.edit_desc.toPlainText() else None
        
        c = self.edit_custom_code.toPlainText().strip()
        self.step.custom_code = c if c else None
        
        self.accept()
