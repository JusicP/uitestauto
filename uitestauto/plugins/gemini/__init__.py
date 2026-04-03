from uitestauto.plugins.registry import PluginRegistry
from uitestauto.plugins.gemini.agent import GeminiAIAgent

def register_gemini_agent(registry: PluginRegistry) -> None:
    registry.register_ai_agent("gemini_agent", GeminiAIAgent)
