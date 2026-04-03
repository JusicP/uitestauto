from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, 
    QDialogButtonBox, QVBoxLayout
)
from uitestauto.core.settings import SettingsManager
from uitestauto.plugins.registry import plugin_registry

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("UiTestAuto Settings")
        self.setMinimumWidth(400)
        
        self.settings = SettingsManager()
        
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.api_key_input.setText(self.settings.get_api_key())
        form_layout.addRow("Gemini API Key:", self.api_key_input)
        
        self.ai_plugin_input = QComboBox()
        self.ai_plugin_input.addItems(list(plugin_registry._ai_agents.keys()))
        self.ai_plugin_input.setCurrentText(self.settings.get_ai_agent_plugin())
        self.ai_plugin_input.currentTextChanged.connect(self._on_plugin_changed)
        form_layout.addRow("AI Agent Plugin:", self.ai_plugin_input)
        
        self.ai_model_input = QComboBox()
        self._on_plugin_changed(self.ai_plugin_input.currentText())
        form_layout.addRow("AI Model:", self.ai_model_input)
        
        layout.addLayout(form_layout)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def _on_plugin_changed(self, plugin_name: str):
        self.ai_model_input.clear()
        agent_cls = plugin_registry._ai_agents.get(plugin_name)
        
        if agent_cls and hasattr(agent_cls, "supported_models"):
            models = agent_cls.supported_models()
            if models:
                self.ai_model_input.addItems(models)
                
                # check if previously saved model is among the supported ones
                current_settings_model = self.settings.get_ai_model()
                if current_settings_model in models:
                    self.ai_model_input.setCurrentText(current_settings_model)
                return
                
        # fallback if no models are given by class
        self.ai_model_input.addItems(["default"])

    def accept(self):
        self.settings.set_api_key(self.api_key_input.text().strip())
        self.settings.set_ai_model(self.ai_model_input.currentText().strip())
        self.settings.set_ai_agent_plugin(self.ai_plugin_input.currentText().strip())
        super().accept()
