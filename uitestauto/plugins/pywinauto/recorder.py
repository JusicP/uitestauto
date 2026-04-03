import logging
import time

# import sys
# sys.coinit_flags = 2  # type: ignore  # COINIT_APARTMENTTHREADED

from pywinauto_recorder import Recorder
from pywinauto_recorder.recorder import (
    ClickEvent,
    IconSet,
    _clean_events,
    _process_events,
    _overlay_add_mode_icon,
)
from pywinauto_recorder.core import get_entry, get_entry_list

from uitestauto.plugins.base import BaseRecorder
from uitestauto.models.element import UIElementLocator, ScenarioStep, ScenarioStepType

logger = logging.getLogger("UiTestAuto")


class _RecorderNoCode(Recorder):
    """
    Internal subclass of pywinauto_recorder.Recorder that suppresses file
    output and instead exposes the recorded steps as a list of ScenarioSteps.
    """

    def __init__(self) -> None:
        super().__init__()
        self.step_list: list[ScenarioStep] = []

    def stop_recording(self) -> None:  # type: ignore[override]
        if self.mode == "Record" and len(self.event_list) > 2:
            events = list(self.event_list)
            self.event_list = []
            self.mode = "Stop"
            time.sleep(0.6)
            if self.started_recording_with_keyboard:
                _clean_events(events, remove_first_up=True)
            else:
                _clean_events(events)
            self.started_recording_with_keyboard = False
            _process_events(events, process_menu_click=self.process_menu_click_mode)
            _clean_events(events)
            self.step_list = self._events_to_ui_action(
                events,
                relative_coordinate_mode=self.relative_coordinate_mode,
            )
            return
        self.main_overlay.clear_all()
        _overlay_add_mode_icon(self.main_overlay, IconSet.hicon_stop, 10, 10)
        self.main_overlay.refresh()
        self.mode = "Stop"

    def _events_to_ui_action(
        self, events, relative_coordinate_mode
    ) -> list[ScenarioStep]:
        # Pre-processing: deduplicate consecutive hovering (ElementEvent) over the same element.
        # Pattern: [MoveEvent*, ElementEvent(path=P), MoveEvent*, ElementEvent(path=P), ...]
        # → keep only the *first* ElementEvent for each contiguous run of the
        # Non-ElementEvent events (Click, SendKeys, …) are always kept and they
        # also break a run.
        deduped: list = []
        last_element_path: str | None = None

        for event in events:
            ev_type = type(event).__name__

            if ev_type == "ElementEvent":
                path = getattr(event, "path", None)
                if path != last_element_path:
                    # new element
                    deduped.append(event)
                    last_element_path = path
            elif ev_type == "MoveEvent":
                pass
            else:
                deduped.append(event)
                last_element_path = None  # break the hover run

        steps: list[ScenarioStep] = []
        last_time = None

        for event in deduped:
            ev_type = type(event).__name__

            event_time = getattr(event, "time", None)
            if last_time is not None and event_time is not None:
                wait_time = event_time - last_time
                if wait_time > 0.5:
                    steps.append(
                        ScenarioStep(
                            id=len(steps) + 1,
                            action_type=ScenarioStepType.WAIT,
                            locators=[],
                            value=str(round(wait_time, 2)),
                            description=f"Wait for {round(wait_time, 2)} seconds",
                        )
                    )
            if event_time is not None:
                last_time = event_time

            # Build locators
            name = None
            control_type = None
            locators: list[UIElementLocator] = []

            if hasattr(event, "path") and event.path:
                entry_list = get_entry_list(event.path)
                if entry_list:
                    str_name, str_type, _, _ = get_entry(entry_list[-1])
                    name = str_name or None
                    control_type = str_type or None

                    for entry in entry_list[:-1]:
                        p_name, p_type, _, _ = get_entry(entry)
                        loc = UIElementLocator()
                        if p_name:
                            loc.name = p_name
                        if p_type:
                            loc.control_type = p_type
                        locators.append(loc)

                    locators.append(UIElementLocator(name=name, control_type=control_type))

            if ev_type == "ElementEvent":
                steps.append(
                    ScenarioStep(
                        id=len(steps) + 1,
                        action_type=ScenarioStepType.MOUSE_OVER,
                        locators=locators,
                        description=f"Mouse over '{name or control_type or 'element'}'",
                    )
                )

            elif isinstance(event, ClickEvent):
                if event.click_count >= 2:
                    val_str = "double"
                elif getattr(event, "button", "left") == "right":
                    val_str = "right"
                else:
                    val_str = "left"
                
                steps.append(
                    ScenarioStep(
                        id=len(steps) + 1,
                        action_type=ScenarioStepType.CLICK,
                        locators=locators,
                        value=val_str,
                        description=f"Click ({val_str}) on '{name}'",
                    )
                )

            elif ev_type == "SendKeysEvent":
                keys = getattr(event, "line", getattr(event, "keys", ""))
                steps.append(
                    ScenarioStep(
                        id=len(steps) + 1,
                        action_type=ScenarioStepType.TYPE_TEXT,
                        locators=[],
                        value=keys,
                        description=f"Type '{keys}'",
                    )
                )

        return steps

    def quit(self):
        """
        The function clears the main and info overlays, sets the mode to 'Quit', and then joins the thread.
        """
        self.main_overlay.clear_all()
        self.main_overlay.refresh()
        self.mode = 'Quit'
        self.join(5)
        del self.element_info_tooltip
        print("Quit")



class PywinautoRecorderBackend(BaseRecorder):
    """
    Records UI interactions using pywinauto_recorder and maps them to
    UiTestAuto ScenarioSteps.
    """

    def __init__(self, pywinauto_backend: str = "uia") -> None:
        self._pywinauto_backend = pywinauto_backend
        self._recorder: _RecorderNoCode | None = None

    def start(self) -> None:
        logger.info(f"[Recorder/{self._pywinauto_backend}] Starting recorder")
        if not self._recorder:
            self._recorder = _RecorderNoCode()
            self._recorder.start_recording()

    def stop(self) -> list[ScenarioStep]:
        if not self._recorder:
            return []
        logger.info(f"[Recorder/{self._pywinauto_backend}] Stopping recorder")
        self._recorder.stop_recording()
        steps = self._recorder.step_list
        logger.info(f"[Recorder/{self._pywinauto_backend}] Captured {len(steps)} steps")
        return steps

    def quit(self) -> None:
        if self._recorder:
            logger.info(f"[Recorder/{self._pywinauto_backend}] Quitting recorder")
            self._recorder.quit()
            self._recorder = None
            logger.info(f"[Recorder/{self._pywinauto_backend}] Recorder stopped.")

    @property
    def is_active(self) -> bool:
        return self._recorder is not None
