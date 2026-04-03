import pytest
import shutil
import json
from pathlib import Path
from unittest.mock import patch
from uitestauto.core.settings import SettingsManager

@pytest.fixture
def tmp_settings_dir(tmp_path):
    with patch("uitestauto.core.settings.Path.home", return_value=tmp_path):
        # Reset the Singleton instance for isolation
        SettingsManager._instance = None
        yield tmp_path
        SettingsManager._instance = None

def test_settings_manager_defaults(tmp_settings_dir):
    sm = SettingsManager()
    assert sm.get_api_key() == ""
    assert sm.get_ai_model() == "gemini-2.5-flash"
    assert sm.get_ai_agent_plugin() == "gemini_agent"

def test_settings_manager_save_load(tmp_settings_dir):
    sm = SettingsManager()
    sm.set_api_key("12345")
    sm.set_ai_model("gemini-3-pro")
    
    # recreate singleton to test file loading
    SettingsManager._instance = None
    sm2 = SettingsManager()
    
    assert sm2.get_api_key() == "12345"
    assert sm2.get_ai_model() == "gemini-3-pro"
