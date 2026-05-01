import subprocess
import os
import sys
import threading
from typing import Callable, Union

from PySide6.QtCore import QObject, Signal

from uitestauto.models.project import TestCase, TestSuite, ProjectConfig
from uitestauto.plugins.registry import plugin_registry
from uitestauto.core.logger import logger


class TestEngine(QObject):
    """
    Executes a stored TestCase, TestSuite, or ProjectConfig (contains TestSuite)
    by generating a python test script (currently we are limited to pytest) via the PluginRegistry's
    Generator backend and running it via subprocess, piping output to the given logger callback.

    The *ambiguity_resolver* callable is forwarded into the generated script's
    environment via stdout protocol (UITESTAUTO_HEALED_STEP_INDEX).
    By default, in a subprocess context, ambiguity resolution relies on the user responding
    through a dialog shown by the subprocess (not available here without
    embedded Qt), so the healed index is communicated back via stdout parsing.
    """

    case_started = Signal(TestCase)
    case_finished = Signal(TestCase, bool, str)
    test_finished = Signal(bool, str)       # success, message
    step_healed = Signal(int, str)          # step_id, comma-separated indices

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = None
        self.is_stopped = False

    def run(
        self,
        item: Union[TestCase, TestSuite, ProjectConfig],
        logger_callback: Callable[[str], None] | None = None,
        ambiguity_resolver: Callable[[list], int] | None = None,
    ):
        """
        Generate and execute the given test item.

        For each TestCase, the generator is resolved from PluginRegistry using
        the TestCase's backend field (e.g. "pywinauto_uia").
        """
        self.is_stopped = False

        cases_to_run: list[TestCase] = []
        if isinstance(item, TestCase):
            cases_to_run = [item]
        elif isinstance(item, TestSuite):
            cases_to_run = item.cases
        elif isinstance(item, ProjectConfig):
            for suite in item.suites:
                cases_to_run.extend(suite.cases)

        if not cases_to_run:
            if logger_callback:
                logger_callback("[Test] No test cases to run.")
            self.test_finished.emit(True, "No test cases to run.")
            return

        if logger_callback:
            logger_callback(
                f"[Test] Starting batch execution of {len(cases_to_run)} test cases."
            )

        def run_proc():
            overall_success = True

            for test_case in cases_to_run:
                if self.is_stopped:
                    if logger_callback:
                        logger_callback("[Test] Batch execution stopped by user.")
                    self.test_finished.emit(False, "Batch execution stopped by user.")
                    return

                if logger_callback:
                    logger_callback(f"[Test] Starting scenario: {test_case.name}")

                self.case_started.emit(test_case)

                # Resolve generator from the registry using the case's backend
                try:
                    generator = plugin_registry.create_generator(test_case.backend)
                except KeyError as e:
                    msg = f"Backend '{test_case.backend}' is not registered: {e}"
                    if logger_callback:
                        logger_callback(f"[Test error] {msg}")
                    overall_success = False
                    self.case_finished.emit(test_case, False, msg)
                    continue

                output_file = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "..", "..", "temp_run.py")
                )
                success = generator.generate(test_case, output_file)

                if not success:
                    if logger_callback:
                        logger_callback(
                            f"[Test error] Failed to generate script for {test_case.name}."
                        )
                    overall_success = False
                    self.case_finished.emit(
                        test_case, False, "Failed to generate python test script."
                    )
                    continue

                if logger_callback:
                    logger_callback(f"[Test] Running script for {test_case.name}...")

                try:
                    self.process = subprocess.Popen(
                        [sys.executable, "-m", "pytest", output_file, "-v", "-s"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        encoding="utf-8",
                        errors="replace",
                    )

                    if self.process.stdout:
                        for line in self.process.stdout:
                            line_str = line.strip()
                            if line_str.startswith("UITESTAUTO_HEALED_STEP_INDEX|"):
                                try:
                                    parts = line_str.split("|")
                                    step_id = int(parts[1])
                                    indices_str = parts[2]
                                    self.step_healed.emit(step_id, indices_str)
                                    if logger_callback:
                                        logger_callback(
                                            f"[TestEngine] Detected healed step {step_id} "
                                            f"with indices {indices_str}"
                                        )
                                except Exception as e:
                                    if logger_callback:
                                        logger_callback(
                                            f"[TestEngine] Failed to parse healed index: {e}"
                                        )
                            else:
                                if logger_callback:
                                    logger_callback(f"[PyTest] {line_str}")

                    self.process.wait()

                    if self.is_stopped:
                        if logger_callback:
                            logger_callback("[Test] Test stopped by user.")
                        self.case_finished.emit(test_case, False, "Test stopped by user.")
                        self.test_finished.emit(False, "Test stopped by user.")
                        return

                    if self.process.returncode == 0:
                        if logger_callback:
                            logger_callback(
                                f"[Test] Scenario '{test_case.name}' completed successfully."
                            )
                        self.case_finished.emit(
                            test_case, True, "Scenario completed successfully."
                        )
                    else:
                        msg = (
                            f"Scenario '{test_case.name}' finished with errors, "
                            f"code {self.process.returncode}."
                        )
                        if logger_callback:
                            logger_callback(f"[Test] {msg}")
                        overall_success = False
                        self.case_finished.emit(test_case, False, msg)

                except Exception as e:
                    if not self.is_stopped:
                        if logger_callback:
                            logger_callback(f"[Test fatal error] {str(e)}")
                        overall_success = False
                        self.case_finished.emit(
                            test_case, False, f"Fatal error: {str(e)}"
                        )
                finally:
                    self.process = None

            if overall_success:
                self.test_finished.emit(True, "All tests completed successfully.")
            else:
                self.test_finished.emit(False, "Some tests failed during execution.")

        test_thread = threading.Thread(target=run_proc, daemon=True)
        test_thread.start()

    def stop(self):
        """Stop the currently running pytest subprocess."""
        if self.process and self.process.poll() is None:
            self.is_stopped = True
            logger.info("> [System] Stopping test process...")
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()

    def is_running(self) -> bool:
        return self.process is not None
