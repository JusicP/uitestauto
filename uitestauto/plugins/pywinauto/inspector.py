import logging
from typing import TYPE_CHECKING

# import sys
# sys.coinit_flags = 2  # type: ignore  # COINIT_APARTMENTTHREADED

from pywinauto import Desktop
from pywinauto.findwindows import find_element

from uitestauto.plugins.base import BaseInspector
from uitestauto.models.element import UIElementLocator

from pywinauto.controls.uiawrapper import UIAWrapper
from pywinauto.controls.hwndwrapper import HwndWrapper

logger = logging.getLogger("UiTestAuto")


class PywinautoInspectorBackend(BaseInspector):
    """
    Inspects Windows UI elements using pywinauto.
    Variant is one of "uia" or "win32".
    """

    def __init__(self, variant: str = "uia") -> None:
        self._variant = variant

    def get_top_level_windows(self) -> list[dict]:
        """Return all top-level windows on the desktop."""
        windows = []
        desktop = Desktop(backend=self._variant)
        for win in desktop.windows():
            windows.append({
                "name": win.window_text(),
                "handle": win.handle,
                "process_id": win.process_id(),
            })
        return windows

    def get_window_tree(self, window_name: str | None = None, handle: int | None = None) -> dict | None:
        """Build and return a full recursive element tree for *window_name* or *handle*."""
        try:
            if handle is not None:
                top_window_info = find_element(backend=self._variant, handle=handle)
            elif window_name is not None:
                top_window_info = find_element(backend=self._variant, name=window_name)
            else:
                logger.error(f"[Inspector/{self._variant}] Failed to build UI tree: Need window_name or handle")
                return None

            locator = self._build_locator(top_window_info)
            locator.found_index = 0

            ctrl_type = top_window_info.control_type or "Unknown"
            name = top_window_info.name or ""
            display_text = f"[{ctrl_type}] {name}" if name else f"[{ctrl_type}]"

            root_wrapper = UIAWrapper(top_window_info) if self._variant == "uia" else HwndWrapper(top_window_info)
            root_node = {
                "display": display_text,
                "locators": [locator],
                "element_info": top_window_info,
                "wrapper": root_wrapper,
                "children": [],
            }

            stack = [(top_window_info, [locator], root_node)]
            while stack:
                current_element_info, current_path, parent_dict = stack.pop()

                try:
                    children = current_element_info.children()
                except Exception:
                    children = []

                for child in children:
                    child_locator = self._build_locator(child)
                    criteria = child_locator.to_pywinauto_kwargs()
                    match_count = 0
                    child_locator.found_index = 0

                    for sib in children:
                        if sib is child:
                            child_locator.found_index = match_count
                            break
                        is_match = all(
                            getattr(sib, k, None) == v
                            for k, v in criteria.items()
                        )
                        if is_match:
                            match_count += 1

                    next_path = current_path + [child_locator]

                    c_ctrl = child.control_type or "Unknown"
                    c_name = child.name or ""
                    c_display = f"[{c_ctrl}] {c_name}" if c_name else f"[{c_ctrl}]"

                    c_wrapper = UIAWrapper(child) if self._variant == "uia" else HwndWrapper(child)
                    child_node = {
                        "display": c_display,
                        "locators": next_path,
                        "element_info": child,
                        "wrapper": c_wrapper,
                        "children": [],
                    }
                    parent_dict["children"].append(child_node)

                for child_node in reversed(parent_dict["children"]):
                    stack.append((child_node["element_info"], child_node["locators"], child_node))

        except Exception as e:
            logger.error(f"[Inspector/{self._variant}] Failed to build UI tree: {e}")
            return None

        return root_node

    def _build_locator(self, element_info) -> UIElementLocator:
        """Map a pywinauto element_info to a UIElementLocator."""
        return UIElementLocator(
            auto_id=getattr(element_info, "auto_id", None) or None,
            name=getattr(element_info, "name", None) or None,
            control_type=getattr(element_info, "control_type", None) or None,
            class_name=getattr(element_info, "class_name", None) or None,
            enabled=getattr(element_info, "enabled", None) or None,
            visible=getattr(element_info, "visible", None) or None,
        )

    def highlight_element(self, element):
        element.draw_outline(colour='green', thickness=2)
    
    def dump_tree(self, window_name: str):
        desktop = Desktop(backend=self._variant)
        window = desktop.window(title=window_name)
        window.dump_tree(max_width=None, depth=None)
        