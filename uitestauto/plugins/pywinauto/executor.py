import logging
import sys
from typing import Callable

# sys.coinit_flags = 2  # type: ignore  # COINIT_APARTMENTTHREADED

import pywinauto
import pywinauto.mouse as mouse
import pywinauto.keyboard as keyboard
from pywinauto.base_application import WindowSpecification
from pywinauto.base_wrapper import BaseWrapper
from pywinauto.timings import TimeoutError
from pywinauto.findwindows import ElementAmbiguousError, find_elements
from pywinauto.controls.uiawrapper import UIAWrapper

from uitestauto.plugins.base import BaseExecutor
from uitestauto.models.element import ScenarioStepType, UIElementLocator

logger = logging.getLogger("UiTestAuto")


def _get_all_ambiguous_targets(
    locator_path: list[UIElementLocator],
    variant: str,
) -> list[tuple]:
    """
    Traverse the locator path and collect all leaf elements, returning
    a list of (UIAWrapper, [index_at_each_level]).
    """
    if not locator_path:
        return []

    top_kwargs = locator_path[0].to_pywinauto_kwargs()
    top_kwargs.pop("found_index", None)
    eis = find_elements(backend=variant, **top_kwargs)
    current_paths = [(UIAWrapper(ei), [i]) for i, ei in enumerate(eis)]

    for p_locator in locator_path[1:]:
        p_kwargs = p_locator.to_pywinauto_kwargs()
        p_kwargs.pop("found_index", None)
        next_paths = []
        for w, indices in current_paths:
            matches = w.children(**p_kwargs)
            for i, match in enumerate(matches):
                next_paths.append((match, indices + [i]))
        current_paths = next_paths
        if not current_paths:
            return []

    return current_paths


class PywinautoExecutorBackend(BaseExecutor):
    def __init__(self, pywinauto_backend: str = "uia") -> None:
        self._pywinauto_backend = pywinauto_backend

    def execute(
        self,
        step_type: str,
        locator_path: list[UIElementLocator],
        value: str | None = None,
        step_id: int | None = None,
        ambiguity_resolver: Callable[[list], int] | None = None,
        post_action_func: Callable | None = None,
    ) -> None:
        try:
            self._execute_strict(step_type, locator_path, value, step_id, post_action_func)
            return

        except ElementAmbiguousError:
            logger.warning(
                f"[Executor/{self._pywinauto_backend}] Ambiguous element. "
                f"Attempting dynamic resolution for step_id={step_id}..."
            )
            self._resolve_ambiguity(
                step_type, locator_path, value, step_id,
                ambiguity_resolver, post_action_func,
            )
            return

        except Exception:
            logger.exception(f"[Executor/{self._pywinauto_backend}] locator failed.")

        raise Exception("Element could not be found.")

    def _execute_strict(
        self,
        step_type: str,
        locator_path: list[UIElementLocator],
        value: str | None,
        step_id: int | None,
        post_action_func: Callable | None,
    ) -> None:
        target_element: BaseWrapper | None = None

        if locator_path:
            # get top level window
            target_window_spec: WindowSpecification = pywinauto.Desktop(backend=self._pywinauto_backend).window(**locator_path[0].to_pywinauto_kwargs())
            try:
                target_window_spec.set_focus()
            except Exception:
                pass
                
            for locator in locator_path[1:]:
                kwargs = locator.to_pywinauto_kwargs()
                target_window_spec = target_window_spec.by(**kwargs)

            try:
                target_element = target_window_spec.find(timeout=3)
            except TimeoutError:
                assert False, "Element not found"

            if step_type != ScenarioStepType.ASSERT_EXISTS:
                try:
                    target_element.wait_visible(timeout=3, retry_interval=0.5)
                except TimeoutError:
                    assert False, "Element not visible"
            target_element.draw_outline()

        self._perform_action(step_type, value, target_element)

        logger.info(f"[Executor/{self._pywinauto_backend}] Executed {step_type} step")

        if post_action_func:
            post_action_func(target_element)

    def _perform_action(
        self,
        step_type: str,
        value: str | None,
        target_element: BaseWrapper | None,
    ) -> None:
        if step_type == ScenarioStepType.CLICK:
            btn = "right" if value and "right" in value else "left"
            is_double = bool(value and "double" in value)
            if target_element:
                target_element.click_input(button=btn, double=is_double)
            else:
                if not is_double:
                    mouse.click(button=btn)
                else:
                    mouse.double_click(button=btn)

        elif step_type == ScenarioStepType.TYPE_TEXT:
            if target_element:
                target_element.type_keys(value, with_spaces=True)
            else:
                keyboard.send_keys(value, with_spaces=True)

        elif step_type == ScenarioStepType.ASSERT_EXISTS:
            pass  # element was already located above

        elif step_type == ScenarioStepType.MOUSE_OVER:
            if target_element:
                target_element.click_input(button="move")

    def _resolve_ambiguity(
        self,
        step_type: str,
        locator_path: list[UIElementLocator],
        value: str | None,
        step_id: int | None,
        ambiguity_resolver: Callable[[list], int] | None,
        post_action_func: Callable | None,
    ) -> None:
        """
        Ambiguity resolution strategy:

        1. **External callback**: if `ambiguity_resolver` is provided by the
        caller, it is called with the list of path candidates and must return
        the chosen index (or -1 to cancel).

        2. **Built-in Qt dialog**: if no callback is provided and Qt is
        available, AmbiguityResolverDialog is shown. This covers the case where
        the test is started from the app UI or as a subprocess.
        If Qt is not available at all, exception is raised.
        """
        ambiguous_targets = _get_all_ambiguous_targets(locator_path, self._pywinauto_backend)

        if not ambiguous_targets:
            logger.warning(f"[Executor/{self._pywinauto_backend}] Dynamic resolution failed: no ambiguous targets found.")
            raise Exception("Element could not be found.")

        logger.info(f"[Executor/{self._pywinauto_backend}] Found {len(ambiguous_targets)} ambiguous elements.")

        if ambiguity_resolver is not None:
            correct_index = ambiguity_resolver(ambiguous_targets)
        else:
            correct_index = self._qt_resolve(ambiguous_targets)

        if correct_index == -1:
            logger.warning(f"[Executor/{self._pywinauto_backend}] Ambiguity resolution cancelled.")
            raise Exception("Ambiguous element resolution cancelled.")

        target, indices = ambiguous_targets[correct_index]
        indices_str = ",".join(map(str, indices))
        logger.info(f"[Executor/{self._pywinauto_backend}] Resolved with indices: {indices_str}")

        if step_id is not None:
            # signal to app to update locator (heal)
            print(f"UITESTAUTO_HEALED_STEP_INDEX|{step_id}|{indices_str}")
            sys.stdout.flush()

        self._perform_action(step_type, value, target)

        if post_action_func:
            post_action_func(target)

    def _qt_resolve(self, ambiguous_targets: list) -> int:
        """
        Show a built-in Qt dialog to let the user choose an ambiguous element.
        If no QT available, exception is raised.
        """
        try:
            from PySide6.QtWidgets import (
                QApplication, QDialog, QVBoxLayout, QListWidget,
                QPushButton, QLabel, QHBoxLayout,
            )
            from PySide6.QtCore import Qt
        except ImportError:
            raise RuntimeError("Ambiguous element found.")

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        class _AmbiguityResolverDialog(QDialog):
            def __init__(self, targets):
                super().__init__()
                self.setWindowTitle("Ambiguous element found")
                self._targets = targets
                self.setWindowFlags(
                    self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
                )
                self.resize(500, 300)

                layout = QVBoxLayout(self)
                layout.addWidget(QLabel(
                    "Multiple elements match the locator criteria." \
                    "When clicking on the element from the list, it will be highlighted.\n" \
                    "Please select the correct one:"
                ))

                self._list = QListWidget()
                for t, indices in targets:
                    try:
                        rect = t.rectangle()
                        text = t.window_text()[:40] if t.window_text() else ""
                        ctrl = getattr(t.element_info, "control_type", "")
                    except Exception:
                        rect, text, ctrl = "", "", ""
                    self._list.addItem(
                        f"Indices {indices}: [{ctrl}] '{text}' at {rect}"
                    )

                self._list.currentRowChanged.connect(self._on_row_changed)
                layout.addWidget(self._list)

                btn_layout = QHBoxLayout()
                ok_btn = QPushButton("Confirm")
                ok_btn.clicked.connect(self.accept)
                btn_layout.addWidget(ok_btn)
                cancel_btn = QPushButton("Cancel")
                cancel_btn.clicked.connect(self.reject)
                btn_layout.addWidget(cancel_btn)
                layout.addLayout(btn_layout)

            def _on_row_changed(self, row):
                # draw outline of selected element
                if 0 <= row < len(self._targets):
                    try:
                        t, _ = self._targets[row]
                        t.draw_outline()
                    except Exception:
                        pass

            def get_selected(self) -> int:
                return self._list.currentRow()

        dialog = _AmbiguityResolverDialog(ambiguous_targets)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_selected()
        return -1
