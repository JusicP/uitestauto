# UiTestAuto
A desktop UI test automation tool for Windows with a GUI, AI-assisted test generation, and a plugin-based architecture.

## Main features
- **Visual test builder** – create, edit, and manage test suites and test cases through a GUI.
- **UI inspector** – browse the live element tree of any running Windows application to discover and select UI elements.
- **Action recorder** – record user interactions (mouse clicks, keystrokes) and convert them into replayable scenario steps automatically.
- **Test executor** – run test cases step-by-step with real-time status feedback; supports basic self-healing via an ambiguity resolver when multiple matching elements are found.
- **Test generator** – export test cases as standalone `pytest` scripts.
- **AI Agent** – describe a goal in natural language and let an AI agent autonomously interact with the target application, producing a verified sequence of test steps.
- **Architecture** – all subsystems (Inspector, Recorder, Executor, Generator and AI Agent) are defined as abstract base classes and wired together through a central plugin registry, making it straightforward to add new implementations.

### Plugins
Plugins are registered at startup through a shared `plugin_registry` singleton:

```python
from uitestauto.plugins.registry import plugin_registry
from uitestauto.plugins.pywinauto import register_pywinauto_backends

register_pywinauto_backends(plugin_registry)

inspector = plugin_registry.create_inspector("pywinauto_uia")
executor  = plugin_registry.create_executor("pywinauto_uia")
```

### Supported test scenario step types
| Type | Description |
|---|---|
| `click` | Left-, right-, or double-click on an element. |
| `type_text` | Type a string into an element or via global keyboard input. |
| `mouse_over` | Move the mouse over an element. |
| `assert_exists` | Assert that an element matching the locator is present. |
| `wait` | Pause execution for a given duration. |
| `start_app` / `kill_app` | Launch or terminate an application by path or name. |
| `custom` | Execute arbitrary inline Python code. |

## Installation
Requirements: Python 3.14 (other versions might work but are not tested), Windows 10+.

```bash
# 1. Clone the repository
git clone <repo-url>
cd uitestauto

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

## Usage
### Launch the GUI

```bash
python main.py
```

### Run generated tests
Generated test scripts are regular pytest scripts:

```bash
pytest path/to/generated_test.py
```

### AI Agent
1. Open **Settings**, enter your Google Gemini API key and select AI model.
2. Select the target window in **AI Agent** tab.
3. Describe your goal (e.g. *"Open Notepad, type Hello World, and save the file"*).
4. The agent will autonomously observe the UI, plan actions, and execute them, producing a sequence of test steps.

## Testing
```bash
pytest tests/
```

## Extending with a New Backend
1. Implement `BaseInspector`, `BaseRecorder`, `BaseExecutor`, and `BaseGenerator` from `uitestauto.plugins.base`.
2. Create a registration helper (following the pattern in `uitestauto/plugins/pywinauto/__init__.py`).
3. Call `register_<your_backend>(plugin_registry)` at application startup.
4. The new backend name will appear in the UI backend selector.

## Known issues
- AI agent can only interact with specific window that is selected in the dropdown menu.
- Recorder is a little bit slow and not very accurate.
- Sometimes it is necessary to adjust the element locators created by Inspector (actual for Google Chrome, need to correct `found_index`)
- Element locator properties with `_re` sometimes not working
- Recorded keyboard input needs some preprocessing before sending to window (or just right after recording) 
- Something wrong with COM initialization. Because of this, copying and pasting text in the GUI doesn't work.
