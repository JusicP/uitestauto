import pytest
import os
import tempfile
from uitestauto.core.project_manager import ProjectManager
from uitestauto.models.project import ProjectConfig

@pytest.fixture
def clean_pm():
    ProjectManager._instance = None
    pm = ProjectManager()
    pm.config = ProjectConfig(project_name="Test")
    pm.mark_dirty() # Initial snapshot
    yield pm
    ProjectManager._instance = None

def test_project_manager_undo_redo(clean_pm):
    # Make a change and snapshot
    clean_pm.config.project_name = "Changed"
    clean_pm.mark_dirty()
    
    assert clean_pm.config.project_name == "Changed"
    
    # Undo it
    assert clean_pm.undo() is True
    assert clean_pm.config.project_name == "Test"
    
    # Redo it
    assert clean_pm.redo() is True
    assert clean_pm.config.project_name == "Changed"

def test_project_manager_save_load(clean_pm):
    # Temp file for testing
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        clean_pm.save_project(path)
        assert os.path.exists(path)
        
        # Load in a fresh instance
        ProjectManager._instance = None
        new_pm = ProjectManager()
        new_pm.load_project(path)
        
        assert new_pm.config is not None
        assert new_pm.config.project_name == "Test"
    finally:
        os.remove(path)
