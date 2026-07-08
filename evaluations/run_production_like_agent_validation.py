"""Production-like AgentLoop validation on the current project.

Scenario:
Analyze an existing validation failure, apply a minimal project change, run checks, and save trace.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from agent.action_loop import ActionAgentLoop
from agent.models import AgentSession
from runtime.actions import EditFileAction, ReadFileAction, RunCommandAction
from runtime.actions.engine import ActionExecutor
from runtime.actions.graph import ActionGraph
from runtime.actions.models import ActionResult
from runtime.backends import BackendManager, DevelopmentBackend


REPORT_PATH = Path("evaluations") / "last-production-like-agent-report.json"
MARKDOWN_PATH = Path("docs") / "production-like-agent-validation-report.md"
TARGET_FILE = "evaluations/run_validation.py"
OLD_COMMAND = 'OpenApplicationAction(\'cmd.exe /k "echo Hello Runtime"\', timeout_seconds=10.0)'
NEW_COMMAND = "OpenApplicationAction('cmd.exe /k echo Hello Runtime', timeout_seconds=10.0)"


@dataclass(slots=True)
class ProductionLikeReport:
    goal: str
    plan: list[str]
    actions: list[dict[str, Any]]
    observations: list[dict[str, Any]]
    errors: list[str]
    repairs: list[str]
    final_result: str | None
    duration: float
    verified: bool
    limitations: list[str]


def trace(result: ActionResult) -> dict[str, Any]:
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


class ProductionLikePlanner:
    def __init__(self) -> None:
        self.repairs: list[str] = []

    def decide(self, session: AgentSession) -> ActionGraph | None:
        if not session.executed_actions:
            return ActionGraph(
                actions=(
                    ReadFileAction("docs/validation-v0.1-report.md"),
                    ReadFileAction(TARGET_FILE),
                )
            )
        if not any("run_terminal" in str(result.outputs.get("command")) for result in session.executed_actions):
            target_content = next(
                (
                    str(result.outputs.get("content"))
                    for result in session.executed_actions
                    if result.outputs.get("path", "").endswith(TARGET_FILE.replace("/", "\\"))
                ),
                "",
            )
            actions = []
            if OLD_COMMAND in target_content:
                actions.append(EditFileAction(TARGET_FILE, OLD_COMMAND, NEW_COMMAND))
            elif NEW_COMMAND in target_content:
                self.repairs.append("Confirmed quoted cmd echo command was already replaced.")
            actions.extend(
                (
                    RunCommandAction("python -m compileall evaluations", cwd="."),
                    RunCommandAction(
                        "python -c \"from evaluations.run_validation import run_terminal; "
                        "r=run_terminal(); print(r.verification_result); print(r.errors); print(r.observations)\"",
                        cwd=".",
                        timeout_seconds=60.0,
                    ),
                )
            )
            return ActionGraph(actions=tuple(actions))
        if any(result.outputs.get("exit_code") == 0 for result in session.executed_actions):
            self.repairs.append("Replaced quoted cmd echo command with unquoted cmd arguments.")
            return None
        return None


def verify(session: AgentSession) -> bool:
    file_changed = any(
        result.outputs.get("replacements") == 1
        for result in session.executed_actions
    )
    already_fixed = any(
        result.outputs.get("path", "").endswith(TARGET_FILE.replace("/", "\\"))
        and NEW_COMMAND in str(result.outputs.get("content"))
        for result in session.executed_actions
    )
    compile_ok = any(
        result.outputs.get("command") == "python -m compileall evaluations"
        and result.outputs.get("exit_code") == 0
        for result in session.executed_actions
    )
    terminal_validation_verified = any(
        "run_terminal" in str(result.outputs.get("command"))
        and result.outputs.get("exit_code") == 0
        and "\nTrue\n" in str(result.outputs.get("stdout"))
        for result in session.executed_actions
    )
    return (file_changed or already_fixed) and compile_ok and terminal_validation_verified


def repair_steps(session: AgentSession, planner: ProductionLikePlanner) -> list[str]:
    repairs = list(planner.repairs)
    if any(result.outputs.get("replacements") == 1 for result in session.executed_actions):
        repairs.append("Replaced quoted cmd echo command with unquoted cmd arguments.")
    elif any(NEW_COMMAND in str(result.outputs.get("content")) for result in session.executed_actions):
        repairs.append("Confirmed quoted cmd echo command was already replaced.")
    return list(dict.fromkeys(repairs))


def production_plan() -> list[str]:
    return [
        "read validation report",
        "read failing validation file",
        "apply minimal repair when needed",
        "run compileall",
        "run terminal validation",
    ]


def markdown(report: ProductionLikeReport) -> str:
    lines = [
        "# Production-Like Agent Validation Report",
        "",
        f"- Goal: {report.goal}",
        f"- Final result: {report.final_result}",
        f"- Verified: {report.verified}",
        f"- Duration: {report.duration:.2f}s",
        "",
        "## Plan",
        "",
        *[f"- {item}" for item in report.plan],
        "",
        "## Actions",
        "",
    ]
    for action in report.actions:
        lines.extend(
            [
                f"- `{action['status']}` via `{action['backend']}`",
                f"  - reason: {action['reason']}",
                f"  - duration: {action['duration']:.2f}s",
                f"  - errors: {action['errors']}",
            ]
        )
    lines.extend(["", "## Repairs", ""])
    lines.extend(f"- {item}" for item in report.repairs)
    lines.extend(["", "## Errors", ""])
    lines.extend(f"- {item}" for item in report.errors or ["None"])
    lines.extend(["", "## Real Runtime Limitations", ""])
    lines.extend(f"- {item}" for item in report.limitations)
    return "\n".join(lines)


def main() -> None:
    started = time.perf_counter()
    planner = ProductionLikePlanner()
    executor = ActionExecutor(
        backend_manager=BackendManager(action_backends=[DevelopmentBackend(root=Path.cwd())])
    )
    loop = ActionAgentLoop(
        executor=executor,
        decide_next=planner.decide,
        verify=verify,
        max_iterations=2,
    )
    goal = "Analyze current validation failure, apply minimal fix, run checks, save report"
    session = loop.run(goal)
    report = ProductionLikeReport(
        goal=goal,
        plan=production_plan(),
        actions=[trace(result) for result in session.executed_actions],
        observations=[dict(item) for item in session.observations],
        errors=list(session.errors),
        repairs=repair_steps(session, planner),
        final_result=session.final_result,
        duration=time.perf_counter() - started,
        verified=session.final_result == "verified",
        limitations=[
            "The loop used a deterministic planner, not an LLM planner.",
            "The terminal scenario still depends on window/process observation behavior after command launch.",
            "The command repair makes cmd print Hello Runtime, but terminal UI observation still does not verify it.",
            "The runtime can edit and validate project code, but semantic diagnosis is still encoded in the planner.",
            "The local validation environment does not currently provide pytest.",
        ],
    )
    REPORT_PATH.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
    MARKDOWN_PATH.write_text(markdown(report), encoding="utf-8")
    print(json.dumps({"verified": report.verified, "final_result": report.final_result}, indent=2))
    print(f"report: {REPORT_PATH}")
    print(f"markdown: {MARKDOWN_PATH}")


if __name__ == "__main__":
    main()
