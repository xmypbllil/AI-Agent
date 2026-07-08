"""Run validation scenarios for runtime 0.1.

This module intentionally does not add runtime capabilities. It exercises the existing public
facade and action backends, then writes a trace report.

Run manually on Windows:

    python -m evaluations.run_validation
"""

from __future__ import annotations

import json
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from computer import create_default_computer
from runtime.actions import ClickAction, OpenApplicationAction
from runtime.actions.models import ActionResult, ActionStatus
from runtime.observations import WindowLocator
from runtime.ui import Locator, UIControlType


REPORT_PATH = Path("evaluations") / "last-validation-report.json"


@dataclass(slots=True)
class TraceEntry:
    action_id: str
    status: str
    backend: str | None
    score: float
    reason: str | None
    duration: float
    outputs: dict[str, Any]
    errors: tuple[str, ...]


@dataclass(slots=True)
class ScenarioReport:
    task: str
    action_graph: list[str]
    actions: list[TraceEntry] = field(default_factory=list)
    verification_result: bool = False
    duration: float = 0.0
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def trace(result: ActionResult) -> TraceEntry:
    return TraceEntry(
        action_id=result.action_id,
        status=str(result.status),
        backend=result.backend_used,
        score=result.backend_score,
        reason=result.backend_reason,
        duration=result.duration_seconds,
        outputs=dict(result.outputs),
        errors=result.errors,
    )


def run_notepad() -> ScenarioReport:
    started = time.perf_counter()
    computer = create_default_computer()
    result = computer.run("Open Notepad and write Hello Runtime")
    pid = result.action_results[0].outputs.get("pid") if result.action_results else None
    try:
        return ScenarioReport(
            task="Notepad: open application, write text, read text back, verify",
            action_graph=["OpenApplicationAction", "TypeTextAction"],
            actions=[trace(item) for item in result.action_results],
            verification_result=result.verified,
            duration=time.perf_counter() - started,
        )
    finally:
        if isinstance(pid, int) and computer.processes.status(pid) is not None:
            computer.processes.terminate(pid)


def run_calculator() -> ScenarioReport:
    started = time.perf_counter()
    computer = create_default_computer()
    results: list[ActionResult] = []
    pid: int | None = None
    try:
        launch = computer.action_executor.execute(OpenApplicationAction("calc.exe", timeout_seconds=10.0))
        results.append(launch)
        pid_value = launch.outputs.get("pid")
        pid = pid_value if isinstance(pid_value, int) else None
        if launch.status is not ActionStatus.SUCCEEDED or pid is None:
            return ScenarioReport(
                task="Calculator: open application, calculate 1 + 2, observe result",
                action_graph=["OpenApplicationAction", "ClickAction", "ClickAction", "ClickAction", "ClickAction"],
                actions=[trace(item) for item in results],
                verification_result=False,
                duration=time.perf_counter() - started,
                errors=["Calculator launch did not produce an observed application window."],
                notes=["Windows Calculator may spawn through an app container with a different window process."],
            )

        window = WindowLocator(process_id=pid)
        computer.windows.find(window, timeout_seconds=10.0)
        button_names = [
            r"^(One|Один|1)$",
            r"^(Plus|Плюс|\+)$",
            r"^(Two|Два|2)$",
            r"^(Equals|Равно|=)$",
        ]
        for pattern in button_names:
            action = ClickAction(
                Locator(
                    regex=pattern,
                    control_type=UIControlType.BUTTON,
                    process=pid,
                    window=window,
                    visible=True,
                    enabled=True,
                )
            )
            results.append(computer.action_executor.execute(action))

        text = computer.ui.text(Locator(automation_id="CalculatorResults", process=pid))
        verified = text is not None and "3" in text
        return ScenarioReport(
            task="Calculator: open application, calculate 1 + 2, observe result",
            action_graph=["OpenApplicationAction", "ClickAction", "ClickAction", "ClickAction", "ClickAction"],
            actions=[trace(item) for item in results],
            verification_result=verified,
            duration=time.perf_counter() - started,
            notes=[f"Observed result text: {text!r}"],
        )
    finally:
        if pid is not None and computer.processes.status(pid) is not None:
            computer.processes.terminate(pid)


def run_file_workflow() -> ScenarioReport:
    started = time.perf_counter()
    with tempfile.TemporaryDirectory() as directory:
        computer = create_default_computer(root=Path(directory))
        target = Path("runtime-validation.txt")
        content = "Hello Runtime"
        computer.files.write(target, content)
        read_back = computer.files.read(target)
        exists = computer.files.exists(target)
        return ScenarioReport(
            task="File workflow: create text, save file, verify existence",
            action_graph=[],
            verification_result=exists and read_back == content,
            duration=time.perf_counter() - started,
            notes=[
                "This scenario validates the existing file facade.",
                "File actions are not yet represented as ActionGraph actions in version 0.1.",
            ],
        )


def main() -> None:
    reports = [run_notepad(), run_calculator(), run_file_workflow()]
    payload = {
        "summary": {
            "total": len(reports),
            "passed": sum(1 for item in reports if item.verification_result),
            "failed": sum(1 for item in reports if not item.verification_result),
        },
        "scenarios": [asdict(item) for item in reports],
        "assessment": {
            "stable": [
                "Notepad E2E path exercises Win32 launch, UIA observation, UIA ValuePattern, and verification.",
                "File facade can create/read/verify files within a configured root.",
            ],
            "known_issues": [
                "Calculator may fail because modern Windows Calculator can use app-container/window process indirection.",
                "File workflow is not yet modeled as ActionGraph actions.",
                "No fallback backend is implemented when UIA ValuePattern is unavailable.",
            ],
            "recommended_improvements": [
                "Add KeyboardInputBackend without changing Action/Executor/Plan/Task.",
                "Add file actions after validation if file workflows need action telemetry.",
                "Improve error quality by reporting failed action, pattern, fallback candidates, and selected backend.",
                "Run Notepad reliability 10 times and record pass rate/duration distribution.",
            ],
        },
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))
    print(f"report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
