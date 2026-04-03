from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, 
                               QMenu, QMessageBox, QDialog, QFormLayout,
                               QLineEdit, QDialogButtonBox, QComboBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from uitestauto.core.project_manager import ProjectManager
from uitestauto.models.project import ProjectConfig, TestSuite, TestCase
from uitestauto.plugins.registry import plugin_registry
from qt_material_icons import MaterialIcon

class ProjectPropertiesDialog(QDialog):
    def __init__(self, parent=None, config: ProjectConfig | None = None):
        super().__init__(parent)
        self.setWindowTitle("Project Properties")
        layout = QFormLayout(self)
        self.name_edit = QLineEdit(config.project_name if config else "Untitled Project")
        layout.addRow("Name:", self.name_edit)
        btn = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        btn.accepted.connect(self.accept)
        btn.rejected.connect(self.reject)
        layout.addRow(btn)

class SuitePropertiesDialog(QDialog):
    def __init__(self, parent=None, suite: TestSuite | None= None):
        super().__init__(parent)
        self.setWindowTitle("Suite Properties")
        layout = QFormLayout(self)
        self.name_edit = QLineEdit(suite.name if suite else "New Suite")
        layout.addRow("Name:", self.name_edit)
        
        btn = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        btn.accepted.connect(self.accept)
        btn.rejected.connect(self.reject)
        layout.addRow(btn)

class CasePropertiesDialog(QDialog):
    def __init__(self, parent=None, case: TestCase | None = None):
        super().__init__(parent)
        self.setWindowTitle("Case Properties")
        layout = QFormLayout(self)
        self.name_edit = QLineEdit(case.name if case else "New Case")
        self.desc_edit = QLineEdit(case.description if case and case.description else "")
        layout.addRow("Name:", self.name_edit)
        layout.addRow("Description:", self.desc_edit)

        self.backend_combo = QComboBox()
        for name in plugin_registry.list_backends():
            self.backend_combo.addItem(name)
        if case:
            idx = self.backend_combo.findText(case.backend)
            if idx >= 0:
                self.backend_combo.setCurrentIndex(idx)
        layout.addRow("Backend:", self.backend_combo)

        btn = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        btn.accepted.connect(self.accept)
        btn.rejected.connect(self.reject)
        layout.addRow(btn)

class ProjectExplorerPanel(QWidget):
    case_selected = Signal(TestCase)
    run_requested = Signal(object)

    def __init__(self):
        super().__init__()
        self.project_manager = ProjectManager()
        self.setup_ui()
        self.refresh_tree()

    def setup_ui(self):
        # TODO: empty view with open project button and text "No project opened"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)

        # TODO: drag and drop to move test cases and test suites
        # FIXME: is it necessary?
        # self.tree.setDragEnabled(True)
        # self.tree.setAcceptDrops(True)
        # self.tree.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        
        # project tree context menu
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)
        
        # process tree item click
        self.tree.itemClicked.connect(self.on_item_clicked)
        
        layout.addWidget(self.tree)

        # icons
        self.not_run_icon = MaterialIcon('circle')

        self.failed_icon = MaterialIcon('x_circle')
        color = QColor('red')
        self.failed_icon.set_color(color)

        self.passed_icon = MaterialIcon('check_circle')
        color = QColor('green')
        self.passed_icon.set_color(color)

        self.passed_partially_icon = MaterialIcon('circle')
        color = QColor('red')
        self.passed_partially_icon.set_color(color)

        self.running_icon = MaterialIcon('circle')
        color = QColor('yellow')
        self.running_icon.set_color(color)

    def get_icon_for_status(self, status: str):
        if status == "passed":
            return self.passed_icon
        elif status == "passed_partially":
            return self.passed_partially_icon
        elif status == "failed":
            return self.failed_icon
        elif status == "running":
            return self.running_icon
        else:
            return self.not_run_icon

    def refresh_tree(self):
        """
        Refreshes the tree view based on the current state of ProjectManager.
        """
        self.tree.clear()
        config = self.project_manager.config
        
        if not config:
            return
            
        root_item = QTreeWidgetItem([config.project_name])
        root_item.setIcon(0, self.get_icon_for_status(config.status))
        # store tree node types: project, suite, case
        root_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "project", "obj": config})
        self.tree.addTopLevelItem(root_item)
        
        for suite in config.suites:
            suite_item = QTreeWidgetItem([suite.name])
            suite_item.setIcon(0, self.get_icon_for_status(suite.status))
            suite_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "suite", "obj": suite})
            root_item.addChild(suite_item)
            
            for case in suite.cases:
                case_item = QTreeWidgetItem([case.name])
                case_item.setIcon(0, self.get_icon_for_status(case.status))
                case_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "case", "obj": case, "parent_suite": suite})
                suite_item.addChild(case_item)
                
        self.tree.expandAll()

    def on_item_clicked(self, item: QTreeWidgetItem, column: int):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "case":
            case = data["obj"]
            self.project_manager.set_active_case(case)
            self.case_selected.emit(case)

    def open_context_menu(self, position):
        if not self.project_manager.config:
            # no project - no context menu
            return

        item = self.tree.itemAt(position)
        menu = QMenu()
        
        if not item:
            # click in empty space — add Test Suite to project
            action_add_suite = menu.addAction("Add test suite")
            action = menu.exec(self.tree.viewport().mapToGlobal(position))
            if action == action_add_suite:
                self.add_suite()
            return
            
        data = item.data(0, Qt.ItemDataRole.UserRole)
        node_type = data.get("type") if data else None
        
        if node_type == "project":
            obj = data.get("obj", self.project_manager.config)
            act_run = menu.addAction("Run selected test")
            menu.addSeparator()
            act_add_suite = menu.addAction("Add test suite")
            act_edit = menu.addAction("Edit project properties")
            
            action = menu.exec(self.tree.viewport().mapToGlobal(position))
            if action == act_run:
                self.run_requested.emit(obj)
            elif action == act_add_suite:
                self.add_suite()
            elif action == act_edit:
                dlg = ProjectPropertiesDialog(self, self.project_manager.config)
                if dlg.exec():
                    self.project_manager.config.project_name = dlg.name_edit.text()
                    self.project_manager.mark_dirty()
                    self.refresh_tree()
                
        elif node_type == "suite":
            suite = data["obj"]
            act_run = menu.addAction("Run selected test")
            menu.addSeparator()
            act_add_case = menu.addAction("Add test case")
            act_edit = menu.addAction("Edit suite properties")
            menu.addSeparator()
            act_delete = menu.addAction("Delete suite")
            
            action = menu.exec(self.tree.viewport().mapToGlobal(position))
            if action == act_run:
                self.run_requested.emit(suite)
            elif action == act_add_case:
                self.add_case(suite)
            elif action == act_edit:
                dlg = SuitePropertiesDialog(self, suite)
                if dlg.exec():
                    suite.name = dlg.name_edit.text()
                    self.project_manager.mark_dirty()
                    self.refresh_tree()
            elif action == act_delete:
                if QMessageBox.question(self, "Confirm", "Delete this suite and all its cases?") == QMessageBox.StandardButton.Yes:
                    if self.project_manager.active_case in suite.cases:
                        self.project_manager.set_active_case(None)
                        self.case_selected.emit(None)
                        
                    self.project_manager.config.suites.remove(suite)
                    self.project_manager.mark_dirty()
                    self.refresh_tree()
                    
        elif node_type == "case":
            case = data["obj"]
            suite = data["parent_suite"]
            act_run = menu.addAction("Run selected test")
            menu.addSeparator()
            act_edit = menu.addAction("Edit case properties")
            act_delete = menu.addAction("Delete case")
            
            action = menu.exec(self.tree.viewport().mapToGlobal(position))
            if action == act_run:
                self.run_requested.emit(case)
            elif action == act_edit:
                dlg = CasePropertiesDialog(self, case)
                if dlg.exec():
                    case.name = dlg.name_edit.text()
                    case.description = dlg.desc_edit.text()
                    case.backend = dlg.backend_combo.currentText()
                    self.project_manager.mark_dirty()
                    self.refresh_tree()
            elif action == act_delete:
                suite.cases.remove(case)
                if self.project_manager.active_case == case:
                    self.project_manager.set_active_case(None)
                    self.case_selected.emit(None)
                self.project_manager.mark_dirty()
                self.refresh_tree()

    def add_suite(self):
        if not self.project_manager.config:
            return

        dlg = SuitePropertiesDialog(self)
        if dlg.exec():
            new_suite = TestSuite(name=dlg.name_edit.text())
            self.project_manager.config.suites.append(new_suite)
            self.project_manager.mark_dirty()
            self.refresh_tree()

    def add_case(self, suite: TestSuite):
        dlg = CasePropertiesDialog(self)
        if dlg.exec():
            new_case = TestCase(
                name=dlg.name_edit.text(),
                description=dlg.desc_edit.text(),
                backend=dlg.backend_combo.currentText(),
            )
            suite.cases.append(new_case)
            self.project_manager.mark_dirty()
            self.refresh_tree()
