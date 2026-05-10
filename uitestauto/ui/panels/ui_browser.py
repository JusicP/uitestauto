"""
UI browser panel.
Displays the UI tree of a selected target application.
"""

from PySide6.QtWidgets import (QMessageBox, QWidget, QVBoxLayout, QHBoxLayout,
                               QComboBox, QPushButton, QTreeWidget,
                               QTreeWidgetItem, QMenu, QHeaderView, QSplitter,
                               QFormLayout, QLineEdit, QGroupBox, QLabel)
from PySide6.QtCore import Qt, Signal

from uitestauto.plugins.registry import plugin_registry
from uitestauto.plugins.base import BaseInspector
from uitestauto.core.project_manager import ProjectManager
from uitestauto.models.element import UIElementLocator, ScenarioStep, ScenarioStepType


class UIBrowserPanel(QWidget):
    step_added = Signal(ScenarioStep)

    def __init__(self):
        super().__init__()
        self._inspector: BaseInspector | None = None
        self._current_backend_name: str | None = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        backend_layout = QHBoxLayout()
        backend_layout.addWidget(QLabel("Inspector backend:"))

        self.backend_combo = QComboBox()
        self.backend_combo.setToolTip(
            "Select the backend used to inspect the target application's UI.\n"
            "Should match the TestCase backend to avoid step incompatibility."
        )
        self._populate_backend_combo()
        self.backend_combo.currentIndexChanged.connect(self._on_backend_changed)
        backend_layout.addWidget(self.backend_combo, stretch=1)
        layout.addLayout(backend_layout)

        control_layout = QHBoxLayout()

        self.window_combo = QComboBox()
        self.window_combo.setPlaceholderText("Select target window...")
        self.window_combo.currentIndexChanged.connect(self.on_window_selected)
        control_layout.addWidget(self.window_combo, stretch=1)

        self.btn_refresh = QPushButton("Refresh top window list")
        self.btn_refresh.clicked.connect(self.populate_windows)
        control_layout.addWidget(self.btn_refresh)

        self.btn_inspect = QPushButton("Inspect")
        self.btn_inspect.clicked.connect(self.inspect_selected_window)
        control_layout.addWidget(self.btn_inspect)

        self.btn_dump_tree = QPushButton("Dump tree")
        self.btn_dump_tree.clicked.connect(self.dump_tree)
        control_layout.addWidget(self.btn_dump_tree)

        layout.addLayout(control_layout)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["UI Elements Tree"])
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tree.setMinimumWidth(100)

        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.splitter.addWidget(self.tree)

        self.attr_group = QGroupBox("Selected element attributes")
        self.attr_layout = QFormLayout(self.attr_group)
        self.attr_layout.setContentsMargins(5, 5, 5, 5)

        self.attr_auto_id = QLineEdit(); self.attr_auto_id.setReadOnly(True)
        self.attr_name = QLineEdit();    self.attr_name.setReadOnly(True)
        self.attr_type = QLineEdit();    self.attr_type.setReadOnly(True)
        self.attr_class = QLineEdit();   self.attr_class.setReadOnly(True)
        self.attr_rect = QLineEdit();    self.attr_rect.setReadOnly(True)

        self.attr_layout.addRow("Auto ID:",      self.attr_auto_id)
        self.attr_layout.addRow("Name:",         self.attr_name)
        self.attr_layout.addRow("Control type:", self.attr_type)
        self.attr_layout.addRow("Class name:",   self.attr_class)
        self.attr_layout.addRow("Rect:",         self.attr_rect)

        self.splitter.addWidget(self.attr_group)
        layout.addWidget(self.splitter)

        # initialize inspector with first available backend
        self._on_backend_changed(0)

    def _populate_backend_combo(self):
        self.backend_combo.clear()
        for name in plugin_registry.list_backends():
            self.backend_combo.addItem(name)

    def _on_backend_changed(self, index: int):
        name = self.backend_combo.currentText()
        if not name or name == self._current_backend_name:
            return
        self._current_backend_name = name
        try:
            self._inspector = plugin_registry.create_inspector(name)
        except KeyError as e:
            QMessageBox.critical(self, "Backend error", str(e))
            self._inspector = None
        
        # Clear the tree when backend changes
        self.tree.clear()
        self.window_combo.clear()
        if self._inspector:
            self.populate_windows()

    def current_backend_name(self) -> str | None:
        return self._current_backend_name

    def populate_windows(self):
        if not self._inspector:
            return
        self.window_combo.clear()
        windows = self._inspector.get_top_level_windows()
        for win in windows:
            self.window_combo.addItem(win["name"], userData=win)

    def on_window_selected(self, index: int):
        if index >= 0:
            self.inspect_selected_window(quiet=True)

    def inspect_selected_window(self, quiet=False):
        if not self._inspector:
            return
        selected_data = self.window_combo.currentData()
        if not selected_data:
            if not quiet:
                QMessageBox.warning(self, "Warning", "Please select a window.")
            return

        window_title = selected_data["name"]
        self.tree.clear()

        # TODO: get window tree by handle or pid idk
        tree_data = self._inspector.get_window_tree(window_title)
        if not tree_data:
            QMessageBox.information(
                self, "Info",
                "No window found. Possible reasons:\n"
                "1. Window may be closed.\n"
                "2. Window name may have changed.\n"
                "3. There are two or more windows with the same name.\n"
                "Try to refresh the top window list or make sure there is "
                "only one window with such name."
            )
            return

        root_display = " ".join(tree_data.get("display", "Unknown").splitlines())
        root_item = QTreeWidgetItem(self.tree, [root_display])
        root_item.setData(0, Qt.ItemDataRole.UserRole, tree_data["locators"])
        root_item.setData(1, Qt.ItemDataRole.UserRole, tree_data.get("wrapper"))

        stack = [(root_item, tree_data)]
        while stack:
            parent_item, node_data = stack.pop()

            def format_text(text: str) -> str:
                text = " ".join(text.splitlines())
                return text if len(text) <= 100 else text[:97] + "..."

            children_items = []
            for child_data in node_data.get("children", []):
                display_text = format_text(child_data.get("display", "Unknown"))
                item = QTreeWidgetItem([display_text])
                item.setData(0, Qt.ItemDataRole.UserRole, child_data["locators"])
                item.setData(1, Qt.ItemDataRole.UserRole, child_data.get("wrapper"))
                children_items.append(item)
                stack.append((item, child_data))

            if children_items:
                parent_item.addChildren(children_items)

        self.tree.expandToDepth(1)

    def dump_tree(self):
        if not self._inspector:
            return

        self._inspector.dump_tree(self.window_combo.currentData()["name"])

    def on_item_clicked(self, item: QTreeWidgetItem, column: int):
        locators: list[UIElementLocator] = item.data(0, Qt.ItemDataRole.UserRole)
        element = item.data(1, Qt.ItemDataRole.UserRole)
        if locators:
            loc = locators[-1]
            self.attr_auto_id.setText(getattr(loc, "auto_id", None) or "")
            self.attr_name.setText(getattr(loc, "name", None) or "")
            self.attr_type.setText(getattr(loc, "control_type", None) or "")
            self.attr_class.setText(getattr(loc, "class_name", None) or "")
            for w in (self.attr_auto_id, self.attr_name, self.attr_type, self.attr_class):
                w.setCursorPosition(0)
        else:
            for w in (self.attr_auto_id, self.attr_name, self.attr_type, self.attr_class):
                w.setText("")

        if element:
            if self._inspector:
                self._inspector.highlight_element(element)
            try:
                element.draw_outline(colour='green', thickness=2)
            except Exception:
                pass
                
            try:
                rect = element.rectangle()
                self.attr_rect.setText(
                    f"L:{rect.left}, T:{rect.top}, R:{rect.right}, B:{rect.bottom} "
                    f"(W:{rect.width()}, H:{rect.height()})"
                )
                self.attr_rect.setCursorPosition(0)
            except Exception:
                self.attr_rect.setText("")
        else:
            self.attr_rect.setText("")

    def show_context_menu(self, position):
        if not ProjectManager().config:
            return

        item = self.tree.itemAt(position)
        if not item:
            return

        locators: list[UIElementLocator] = item.data(0, Qt.ItemDataRole.UserRole)
        wrapper = item.data(1, Qt.ItemDataRole.UserRole)
        if not locators:
            return

        menu = QMenu()
        action_click  = menu.addAction("Add 'Click' step")
        action_type   = menu.addAction("Add 'Type text' step")
        action_assert = menu.addAction("Add 'Assert exists' step")

        selected_action = menu.exec(self.tree.viewport().mapToGlobal(position))

        if selected_action == action_click:
            self.create_and_emit_action(ScenarioStepType.CLICK, locators, wrapper)
        elif selected_action == action_type:
            self.create_and_emit_action(ScenarioStepType.TYPE_TEXT, locators, wrapper)
        elif selected_action == action_assert:
            self.create_and_emit_action(ScenarioStepType.ASSERT_EXISTS, locators, wrapper)

    def create_and_emit_action(
        self,
        action_type: ScenarioStepType,
        locators: list[UIElementLocator],
        wrapper
    ):
        """
        Constructs a ScenarioStep and emits it to the Scenario Editor.
        Checks for backend mismatch between the Inspector backend and the active TestCase backend.
        """
        pm = ProjectManager()
        active_case = pm.get_current_test_case()

        if active_case and self._current_backend_name:
            case_backend = active_case.backend
            inspector_backend = self._current_backend_name
            if case_backend != inspector_backend:
                QMessageBox.critical(
                    self,
                    "Backend mismatch",
                    f"The Inspector is using backend '{inspector_backend}', "
                    f"but the active TestCase uses backend '{case_backend}'.\n\n"
                    "Select proper backend in the Inspector panel."
                )
                return

        new_step = ScenarioStep(
            id=0,
            action_type=action_type,
            locators=locators,
        )
        self.step_added.emit(new_step)
