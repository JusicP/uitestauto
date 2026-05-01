import json
from pathlib import Path


class SettingsManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_settings()
        return cls._instance
        
    def _init_settings(self):
        # Store settings in the user's home directory
        self._settings_dir = Path.home() / ".uitestauto"
        self._settings_dir.mkdir(parents=True, exist_ok=True)
        self._settings_file = self._settings_dir / "settings.json"
        
        self._data = {}
        self._load()

    def _load(self):
        if self._settings_file.exists():
            try:
                with open(self._settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self._data.update(data)
            except Exception:
                pass
                
    def _save(self):
        try:
            with open(self._settings_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=4)
        except Exception:
            pass

    def get_api_key(self) -> str:
        return self._data.get("api_key", "")
        
    def set_api_key(self, api_key: str):
        self._data["api_key"] = api_key
        self._save()

    def get_ai_model(self) -> str:
        return self._data.get("ai_model", "gemini-2.5-flash")
        
    def set_ai_model(self, model: str):
        self._data["ai_model"] = model
        self._save()

    def get_ai_agent_plugin(self) -> str:
        return self._data.get("ai_agent_plugin", "gemini_agent")
        
    def set_ai_agent_plugin(self, agent_plugin_name: str):
        self._data["ai_agent_plugin"] = agent_plugin_name
        self._save()
