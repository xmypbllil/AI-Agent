"""Validate the ActionAgentLoop on real development-style tasks."""

from __future__ import annotations

import json
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from agent.action_loop import ActionAgentLoop
from agent.models import AgentSession
from runtime.actions import EditFileAction, ReadFileAction, RunCommandAction, WriteFileAction
from runtime.actions.engine import ActionExecutor
from runtime.actions.graph import ActionGraph
from runtime.actions.models import ActionResult
from runtime.backends import BackendManager, DevelopmentBackend


REPORT_PATH = Path("evaluations") / "last-agent-loop-validation-report.json"
MARKDOWN_PATH = Path("docs") / "agent-loop-validation-report.md"


@dataclass(slots=True)
class AgentScenarioReport:
    goal: str
    actions: list[dict[str, Any]]
    observations: list[dict[str, Any]]
    errors: list[str]
    repair_steps: list[str]
    final_result: str | None
    duration: float
    verified: bool


def action_trace(result: ActionResult) -> dict[str, Any]:
    return {
        "action_id": result.action_id,
        "status": str(result.status),
        "backend": result.backend_used,
        "score": result.backend_score,
        "reason": result.backend_reason,
        "duration": result.duration_seconds,
        "outputs": dict(result.outputs),
        "errors": result.errors,
    }


def executor(root: Path) -> ActionExecutor:
    return ActionExecutor(
        backend_manager=BackendManager(action_backends=[DevelopmentBackend(root=root)])
    )


def scenario_report(goal: str, session: AgentSession, started: float, repair_steps: list[str]) -> AgentScenarioReport:
    return AgentScenarioReport(
        goal=goal,
        actions=[action_trace(item) for item in session.executed_actions],
        observations=[dict(item) for item in session.observations],
        errors=list(session.errors),
        repair_steps=repair_steps,
        final_result=session.final_result,
        duration=time.perf_counter() - started,
        verified=session.final_result == "verified",
    )


def run_bug_fix_workflow() -> AgentScenarioReport:
    goal = "Bug fix: diagnose syntax error, repair file, run validation"
    started = time.perf_counter()
    repair_steps: list[str] = []
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)

        def decide(session: AgentSession) -> ActionGraph | None:
            if not session.executed_actions:
                return ActionGraph(
                    actions=(
                        WriteFileAction("buggy.py", "VALUE = \n"),
                        ReadFileAction("buggy.py"),
                        RunCommandAction("python -m compileall .", cwd="."),
                    )
                )
            if any("command exited" in item for item in session.errors):
                repair_steps.append("Replace incomplete assignment with a valid string literal.")
                return ActionGraph(
                    actions=(
                        EditFileAction("buggy.py", "VALUE = \n", "VALUE = 'fixed'\n"),
                        RunCommandAction("python -m compileall .", cwd="."),
                        ReadFileAction("buggy.py"),
                    )
                )
            return None

        def verify(session: AgentSession) -> bool:
            return any(result.outputs.get("content") == "VALUE = 'fixed'\n" for result in session.executed_actions)

        session = ActionAgentLoop(executor(root), decide, verify, max_iterations=3).run(goal)
        return scenario_report(goal, session, started, repair_steps)


def run_feature_change_workflow() -> AgentScenarioReport:
    goal = "Feature change: modify existing module, run checks, save trace"
    started = time.perf_counter()
    repair_steps: list[str] = []
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)

        def decide(session: AgentSession) -> ActionGraph | None:
            if not session.executed_actions:
                return ActionGraph(
                    actions=(
                        WriteFileAction("feature.py", "def message():\n    return 'old'\n"),
                        EditFileAction("feature.py", "'old'", "'Hello Runtime'"),
                        RunCommandAction("python -m compileall .", cwd="."),
                        ReadFileAction("feature.py"),
                    )
                )
            return None

        def verify(session: AgentSession) -> bool:
            content_ok = any("Hello Runtime" in str(result.outputs.get("content")) for result in session.executed_actions)
            compile_ok = any(result.outputs.get("exit_code") == 0 for result in session.executed_actions)
            return content_ok and compile_ok

        session = ActionAgentLoop(executor(root), decide, verify, max_iterations=2).run(goal)
        return scenario_report(goal, session, started, repair_steps)


def run_runtime_improvement_workflow() -> AgentScenarioReport:
    goal = "Runtime improvement: find validation failure, propose change, apply, verify"
    started = time.perf_counter()
    repair_steps: list[str] = []
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)

        def decide(session: AgentSession) -> ActionGraph | None:
            if not session.executed_actions:
                return ActionGraph(
                    actions=(
                        WriteFileAction(
                            "validation_notes.md",
                            "- Calculator: PID-window correlation failed\n",
                        ),
                        ReadFileAction("validation_notes.md"),
                    )
                )
            if not any("ApplicationRuntimeIdentity" in str(result.outputs.get("content")) for result in session.executed_actions):
                repair_steps.append("Add proposed ApplicationRuntimeIdentity improvement to validation notes.")
                return ActionGraph(
                    actions=(
                        EditFileAction(
                            "validation_notes.md",
                            "- Calculator: PID-window correlation failed\n",
                            "- Calculator: PID-window correlation failed\n"
                            "- Proposed: ApplicationRuntimeIdentity correlation evidence\n",
                        ),
                        ReadFileAction("validation_notes.md"),
                        RunCommandAction("python -c \"from pathlib import Path; assert 'ApplicationRuntimeIdentity' in Path('validation_notes.md').read_text()\"", cwd="."),
                    )
                )
            return None

        def verify(session: AgentSession) -> bool:
            content_ok = any("ApplicationRuntimeIdentity" in str(result.outputs.get("content")) for result in session.executed_actions)
            command_ok = any(result.outputs.get("exit_code") == 0 for result in session.executed_actions)
            return content_ok and command_ok

        session = ActionAgentLoop(executor(root), decide, verify, max_iterations=3).run(goal)
        return scenario_report(goal, session, started, repair_steps)


def markdown(reports: list[AgentScenarioReport]) -> str:
    lines = [
        "# Agent Loop Validation Report",
        "",
        f"- Total: {len(reports)}",
        f"- Passed: {sum(1 for item in reports if item.verified)}",
        f"- Failed: {sum(1 for item in reports if not item.verified)}",
        "",
    ]
    for report in reports:
        lines.extend(
            [
                f"## {report.goal}",
                "",
                f"- Final result: {report.final_result}",
                f"- Verified: {report.verified}",
                f"- Duration: {report.duration:.2f}s",
                "",
                "Actions:",
            ]
        )
        for action in report.actions:
            lines.extend(
                [
                    f"- `{action['status']}` via `{action['backend']}`",
                    f"  - reason: {action['reason']}",
                    f"  - errors: {action['errors']}",
                ]
            )
        if report.repair_steps:
            lines.extend(["", "Repair steps:"])
            lines.extend(f"- {item}" for item in report.repair_steps)
        if report.errors:
            lines.extend(["", "Errors observed:"])
            lines.extend(f"- {item}" for item in report.errors)
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    reports = [
        run_bug_fix_workflow(),
        run_feature_change_workflow(),
        run_runtime_improvement_workflow(),
    ]
    payload = {
        "summary": {
            "total": len(reports),
            "passed": sum(1 for item in reports if item.verified),
            "failed": sum(1 for item in reports if not item.verified),
        },
        "scenarios": [asdict(item) for item in reports],
    }
    REPORT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    MARKDOWN_PATH.write_text(markdown(reports), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))
    print(f"report: {REPORT_PATH}")
    print(f"markdown: {MARKDOWN_PATH}")


if __name__ == "__main__":
    main()
