import json
import logging
from abc import abstractmethod
from typing import Callable, Any
from pydantic import BaseModel

from uitestauto.models.element import ScenarioStepType, UIElementLocator, ScenarioStep
from uitestauto.plugins.registry import plugin_registry
from uitestauto.plugins.base import BaseAIAgent
from uitestauto.ai.prompts import AGENT_SYSTEM_PROMPT_TEMPLATE

logger = logging.getLogger("UiTestAuto")


class AgentAction(BaseModel):
    action_type: ScenarioStepType
    element_id: int | None = None
    value: str | None = None
    description: str | None = None


class AgentResponse(BaseModel):
    thought: str
    action: AgentAction | None = None
    is_goal_reached: bool = False


def get_dynamic_prompt() -> str:
    schema = AgentResponse.model_json_schema()
    
    if "$defs" in schema and "ScenarioStepType" in schema["$defs"]:
        enum_vals = schema["$defs"]["ScenarioStepType"].get("enum", [])
        enum_vals = [v for v in enum_vals if v not in ("start_app", "kill_app")]
        schema["$defs"]["ScenarioStepType"]["enum"] = enum_vals
        
    schema_str = json.dumps(schema, indent=2)
    return AGENT_SYSTEM_PROMPT_TEMPLATE.replace("{schema_json}", schema_str)


class AbstractReActAgent(BaseAIAgent):
    def __init__(self):
        self.is_running = False

    @abstractmethod
    def _ask_llm(self, prompt: str) -> AgentResponse:
        """Query the LLM and return the parsed structured response."""
        pass
        
    def _flatten_ui_tree_with_map(self, tree_node: dict | None, next_id: int, locator_map: dict[int, list[UIElementLocator]]) -> tuple[list[dict], int]:
        """Flattens the UI tree recursively, assigning unique IDs and mapping them to full locator paths."""
        if not tree_node:
            return [], next_id
            
        elements = []
        
        # Flatten current node
        locators = tree_node.get("locators", [])
        if locators:
            current_id = next_id
            next_id += 1
            locator_map[current_id] = locators
            
            # Take the last locator which represents the actual element itself
            # We only extract fields useful for the AI to limit tokens
            loc_dict = locators[-1].model_dump(exclude_none=True)
            subset = {}
            for k in ["auto_id", "name", "control_type", "class_name", "enabled", "visible"]:
                if k in loc_dict:
                    subset[k] = loc_dict[k]
                    
            elements.append({
                "id": current_id,
                **subset
            })
            
        # Recurse for children
        for child in tree_node.get("children", []):
            child_elems, next_id = self._flatten_ui_tree_with_map(child, next_id, locator_map)
            elements.extend(child_elems)
            
        return elements, next_id

    def run(
        self,
        user_goal: str, 
        target_window_title: str, 
        backend_name: str,
        log_callback: Callable[[str], None] = lambda _: None
    ) -> list[ScenarioStep]:
        """
        Runs the AI agent to generate a list of scenario steps using a standard ReAct Loop.
        Delegates the actual LLM generation to `_ask_llm`.
        """
        self.is_running = True
        
        inspector = plugin_registry.create_inspector(backend_name)
        executor = plugin_registry.create_executor(backend_name)
        history_of_actions: list[Any] = []
        successful_steps: list[ScenarioStep] = []
        
        log_callback(f"[Agent] Starting task: '{user_goal}' on window: '{target_window_title}'")
        
        # Resolve target window handle once to ensure stability against dynamic title changes
        target_handle: int | None = None
        for win in inspector.get_top_level_windows():
            if win.get("name") == target_window_title:
                target_handle = win.get("handle")
                break
                
        if not target_handle:
            log_callback(f"[Agent] WARNING: Could not resolve handle for '{target_window_title}'. Using name fallback.")
        
        iteration = 0
        max_iterations = 10
        
        while self.is_running and iteration < max_iterations:
            iteration += 1
            log_callback(f"\n[Agent] Iteration {iteration}/{max_iterations}")
            
            # OBSERVE
            log_callback("[Agent] OBSERVE: Fetching UI Elements...")
            if target_handle:
                ui_tree = inspector.get_window_tree(handle=target_handle)
            else:
                ui_tree = inspector.get_window_tree(window_name=target_window_title)
            
            if not ui_tree:
                error_msg = f"Failed to find window '{target_window_title}' or its elements."
                log_callback(f"[Agent] ERROR: {error_msg}")
                history_of_actions.append(error_msg)
                current_ui_json = "[]"
                element_map: dict[int, list[UIElementLocator]] = {}
            else:
                element_map = {}
                flat_elements, _ = self._flatten_ui_tree_with_map(ui_tree, 1, element_map)
                current_ui_json = json.dumps(flat_elements, indent=2)
                log_callback(f"[Agent] OBSERVE: Found {len(flat_elements)} UI elements.")
                
            # REASON
            prompt = (
                f"{get_dynamic_prompt()}\n\n"
                f"USER_GOAL: {user_goal}\n\n"
                f"ACTION_HISTORY:\n{json.dumps(history_of_actions, indent=2)}\n\n"
                f"CURRENT_UI_ELEMENTS:\n{current_ui_json}\n\n"
                "Please provide your next JSON steps:"
            )
            
            log_callback("[Agent] REASON: Asking Agent for next action...")
            try:
                agent_res = self._ask_llm(prompt)
            except Exception as e:
                log_callback(f"[Agent] Error querying or parsing LLM response: {e}")
                history_of_actions.append(f"System error: {e}")
                break
                
            log_callback(f"[Agent] THOUGHT: {agent_res.thought}")
            
            # ACT
            act = agent_res.action
            if act:
                assert act is not None
                log_callback(f"[Agent] ACT: {act.action_type} - {act.description}")
                
                step_locators: list[UIElementLocator] = []
                if act.element_id is not None:
                    eid = act.element_id
                    step_locators = element_map.get(eid, [])
                    if not step_locators:
                        msg = f"Hallucinated element_id: {act.element_id}. Must use an ID from the list."
                        log_callback(f"[Agent] WARNING: {msg}")
                        history_of_actions.append(msg)
                        continue
                
                step = ScenarioStep(
                    id=iteration,
                    action_type=act.action_type,
                    locators=step_locators,
                    value=act.value,
                    description=act.description,
                    is_ai_suggested=True
                )
                
                # Form locator_path for executor
                locator_path = [loc.to_pywinauto_kwargs() for loc in step.locators]
                
                try:
                    executor.execute(
                        step_type=step.action_type.value,
                        locator_path=locator_path,
                        value=step.value,
                        step_id=step.id,
                        ambiguity_resolver=None
                    )
                    success_msg = f"Successfully executed: {step.description}"
                    log_callback(f"[Agent] ACT Success: {success_msg}")
                    history_of_actions.append({"status": "SUCCESS", "action": step.model_dump()})
                    successful_steps.append(step)
                except Exception as e:
                    error_msg = f"Failed to execute: {step.description}. Error: {e}"
                    log_callback(f"[Agent] ACT Failed: {error_msg}")
                    history_of_actions.append({"status": "FAILED", "action": step.model_dump(), "error": str(e)})

            if agent_res.is_goal_reached:
                log_callback("[Agent] goal reached")
                break
                
            if not act and not agent_res.is_goal_reached:
                msg = "No action provided but goal not reached."
                log_callback(f"[Agent] WARNING: {msg}")
                history_of_actions.append(msg)
                continue

        self.is_running = False
        log_callback("[Agent] Finished running.")
        return successful_steps

    def stop(self) -> None:
        self.is_running = False
