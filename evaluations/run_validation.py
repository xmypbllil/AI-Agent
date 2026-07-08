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
from runtime.actions import ClickAction, EditFileAction, ReadFileAction, RunCommandAction, SearchFilesAction, WriteFileAction, OpenApplicationAction
from runtime.actions.models import ActionResult, ActionStatus
from runtime.observations import WindowLocator
from runtime.ui import Locator, UIControlType


REPORT_PATH = Path("evaluations") / "last-validation-report.json"
MARKDOWN_REPORT_PATH = Path("docs") / "validation-v0.1-report.md"


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
    observations: list[str] = field(default_factory=list)
    screenshots: list[str] = field(default_factory=list)


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
            observations=["UIA ValuePattern text verification completed."],
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
                observations=[],
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
            observations=[f"Calculator result text: {text!r}"],
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
            observations=[f"Created file in temporary directory: {target}"],
        )


def run_self_development_workflow() -> ScenarioReport:
    started = time.perf_counter()
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        computer = create_default_computer(root=root)
        actions = [
            WriteFileAction("project/module.py", "VALUE = 'old'\n"),
            ReadFileAction("project/module.py"),
            EditFileAction("project/module.py", "'old'", "'Hello Runtime'"),
            SearchFilesAction("*.py", "project"),
            RunCommandAction("python -m compileall project", cwd="."),
            ReadFileAction("project/module.py"),
        ]
        results = [computer.action_executor.execute(action) for action in actions]
        final_content = results[-1].outputs.get("content") if results else None
        command_result = results[-2].outputs if len(results) >= 2 else {}
        verified = (
            all(item.status is ActionStatus.SUCCEEDED for item in results)
            and final_content == "VALUE = 'Hello Runtime'\n"
            and command_result.get("exit_code") == 0
        )
        return ScenarioReport(
            task="Self-development: open project, read file, modify file, run validation command, verify",
            action_graph=[
                "WriteFileAction",
                "ReadFileAction",
                "EditFileAction",
                "SearchFilesAction",
                "RunCommandAction",
                "ReadFileAction",
            ],
            actions=[trace(item) for item in results],
            verification_result=verified,
            duration=time.perf_counter() - started,
            observations=[
                f"Final content: {final_content!r}",
                f"Validation exit code: {command_result.get('exit_code')!r}",
            ],
        )


def run_paint() -> ScenarioReport:
    started = time.perf_counter()
    computer = create_default_computer()
    results: list[ActionResult] = []
    pid: int | None = None
    try:
        launch = computer.action_executor.execute(OpenApplicationAction("mspaint.exe", timeout_seconds=10.0))
        results.append(launch)
        pid_value = launch.outputs.get("pid")
        pid = pid_value if isinstance(pid_value, int) else None
        if launch.status is not ActionStatus.SUCCEEDED or pid is None:
            return ScenarioReport(
                task="Paint: open application, observe main window, inspect UI availability",
                action_graph=["OpenApplicationAction"],
                actions=[trace(item) for item in results],
                verification_result=False,
                duration=time.perf_counter() - started,
                errors=["Paint launch did not produce an observed application window."],
            )

        window = WindowLocator(process_id=pid)
        windows = computer.windows.find(window, timeout_seconds=10.0)
        first_element = computer.ui.find(Locator(process=pid, window=window, visible=True))
        return ScenarioReport(
            task="Paint: open application, observe main window, inspect UI availability",
            action_graph=["OpenApplicationAction"],
            actions=[trace(item) for item in results],
            verification_result=bool(windows and first_element),
            duration=time.perf_counter() - started,
            observations=[
                f"Window count: {len(windows)}",
                f"First UI element: {first_element.identity.control_type if first_element else None}",
            ],
        )
    finally:
        if pid is not None and computer.processes.status(pid) is not None:
            computer.processes.terminate(pid)


def run_terminal() -> ScenarioReport:
    started = time.perf_counter()
    computer = create_default_computer()
    results: list[ActionResult] = []
    pid: int | None = None
    try:
        launch = computer.action_executor.execute(
            OpenApplicationAction('cmd.exe /k "echo Hello Runtime"', timeout_seconds=10.0)
        )
        results.append(launch)
        pid_value = launch.outputs.get("pid")
        pid = pid_value if isinstance(pid_value, int) else None
        if launch.status is not ActionStatus.SUCCEEDED or pid is None:
            return ScenarioReport(
                task="Terminal: open cmd, execute simple command, observe output",
                action_graph=["OpenApplicationAction"],
                actions=[trace(item) for item in results],
                verification_result=False,
                duration=time.perf_counter() - started,
                errors=["cmd launch did not produce an observed window."],
            )

        window = WindowLocator(process_id=pid)
        windows = computer.windows.find(window, timeout_seconds=10.0)
        text = computer.ui.text(Locator(process=pid, window=window, visible=True))
        return ScenarioReport(
            task="Terminal: open cmd, execute simple command, observe output",
            action_graph=["OpenApplicationAction"],
            actions=[trace(item) for item in results],
            verification_result=text is not None and "Hello Runtime" in text,
            duration=time.perf_counter() - started,
            observations=[f"Window count: {len(windows)}", f"Observed text: {text!r}"],
            notes=[
                "The command is passed at launch time; interactive keyboard input is not evaluated in v0.1.",
                "Validation output showed command quoting can be mangled before cmd receives the intended input.",
            ],
        )
    finally:
        if pid is not None and computer.processes.status(pid) is not None:
            computer.processes.terminate(pid)


def run_vscode() -> ScenarioReport:
    started = time.perf_counter()
    computer = create_default_computer()
    results: list[ActionResult] = []
    pid: int | None = None
    try:
        launch = computer.action_executor.execute(OpenApplicationAction("code", timeout_seconds=10.0))
        results.append(launch)
        pid_value = launch.outputs.get("pid")
        pid = pid_value if isinstance(pid_value, int) else None
        if launch.status is not ActionStatus.SUCCEEDED or pid is None:
            return ScenarioReport(
                task="VS Code: open if installed, find window, collect UI observation limitations",
                action_graph=["OpenApplicationAction"],
                actions=[trace(item) for item in results],
                verification_result=False,
                duration=time.perf_counter() - started,
                errors=["VS Code did not launch into an observed window from command 'code'."],
                notes=["VS Code may not be installed or the 'code' shim may return before the UI process/window is observed."],
            )

        window = WindowLocator(process_id=pid)
        windows = computer.windows.find(window, timeout_seconds=10.0)
        element = computer.ui.find(Locator(process=pid, window=window, visible=True))
        return ScenarioReport(
            task="VS Code: open if installed, find window, collect UI observation limitations",
            action_graph=["OpenApplicationAction"],
            actions=[trace(item) for item in results],
            verification_result=bool(windows and element),
            duration=time.perf_counter() - started,
            observations=[
                f"Window count: {len(windows)}",
                f"First UI element: {element.identity.control_type if element else None}",
            ],
            notes=["Multi-process Electron apps are expected to stress PID-to-window correlation."],
        )
    finally:
        if pid is not None and computer.processes.status(pid) is not None:
            computer.processes.terminate(pid)


def markdown_report(payload: dict[str, Any]) -> str:
    lines = [
        "# Validation v0.1 Report",
        "",
        f"- Total: {payload['summary']['total']}",
        f"- Passed: {payload['summary']['passed']}",
        f"- Failed: {payload['summary']['failed']}",
        "",
        "## Scenario Results",
        "",
    ]
    for scenario in payload["scenarios"]:
        status = "passed" if scenario["verification_result"] else "failed"
        lines.extend(
            [
                f"### {scenario['task']}",
                "",
                f"- Status: {status}",
                f"- Duration: {scenario['duration']:.2f}s",
                f"- ActionGraph: {', '.join(scenario['action_graph']) or '(none)'}",
                "",
                "Actions:",
            ]
        )
        if scenario["actions"]:
            for action in scenario["actions"]:
                lines.extend(
                    [
                        f"- `{action['status']}` via `{action['backend']}` score `{action['score']}`",
                        f"  - reason: {action['reason']}",
                        f"  - duration: {action['duration']:.2f}s",
                        f"  - errors: {action['errors']}",
                    ]
                )
        else:
            lines.append("- No ActionGraph actions recorded.")
        if scenario["observations"]:
            lines.extend(["", "Observations:"])
            lines.extend(f"- {item}" for item in scenario["observations"])
        if scenario["errors"]:
            lines.extend(["", "Errors:"])
            lines.extend(f"- {item}" for item in scenario["errors"])
        if scenario["notes"]:
            lines.extend(["", "Notes:"])
            lines.extend(f"- {item}" for item in scenario["notes"])
        lines.append("")

    lines.extend(
        [
            "## Stable Capabilities",
            "",
            *[f"- {item}" for item in payload["assessment"]["stable"]],
            "",
            "## Failed Cases",
            "",
            *[f"- {item}" for item in payload["assessment"]["known_issues"]],
            "",
            "## Missing Abstractions",
            "",
            "- Application runtime identity for packaged and multi-process applications.",
            "- Keyboard/input fallback when UIA ValuePattern or InvokePattern is unavailable.",
            "- ActionGraph representation for file workflows.",
            "- Richer verification model for non-text UI results.",
            "",
            "## Recommended Next Milestone",
            "",
            *[f"- {item}" for item in payload["assessment"]["recommended_improvements"]],
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    reports = [
        run_notepad(),
        run_calculator(),
        run_file_workflow(),
        run_self_development_workflow(),
        run_paint(),
        run_terminal(),
        run_vscode(),
    ]
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
                "Self-development workflow can write, read, edit, search, and run a validation command through ActionGraph.",
                "Classic Win32-style application launch/window observation works for at least one application.",
            ],
            "known_issues": [
                "Calculator may fail because modern Windows Calculator can use app-container/window process indirection.",
                "File workflow is not yet modeled as ActionGraph actions.",
                "No fallback backend is implemented when UIA ValuePattern is unavailable.",
                "Terminal launch can correlate to a window, but validation still uses PID-window lookup and command quoting remains fragile.",
                "VS Code may be missing from PATH or require application/runtime command resolution before window correlation can run.",
            ],
            "recommended_improvements": [
                "Add KeyboardInputBackend without changing Action/Executor/Plan/Task.",
                "Add file actions after validation if file workflows need action telemetry.",
                "Improve error quality by reporting failed action, pattern, fallback candidates, and selected backend.",
                "Run Notepad reliability 10 times and record pass rate/duration distribution.",
                "Add package/AppUserModelID evidence for packaged apps and let validation query windows by application_runtime_id.",
            ],
        },
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    MARKDOWN_REPORT_PATH.write_text(markdown_report(payload), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))
    print(f"report: {REPORT_PATH}")
    print(f"markdown: {MARKDOWN_REPORT_PATH}")


if __name__ == "__main__":
    main()
