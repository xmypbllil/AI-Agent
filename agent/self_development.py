"""Minimal self-development demo planner."""

from __future__ import annotations

from dataclasses import dataclass

from agent.action_loop import ActionAgentLoop
from agent.models import AgentSession
from runtime.actions import EditFileAction, ReadFileAction, RunCommandAction, WriteFileAction
from runtime.actions.engine import ActionExecutor
from runtime.actions.graph import ActionGraph


@dataclass(slots=True)
class SelfDevelopmentPlanner:
    path: str

    def decide_next(self, session: AgentSession) -> ActionGraph | None:
        if not session.executed_actions:
            return ActionGraph(
                actions=(
                    WriteFileAction(self.path, "VALUE = \n"),
                    ReadFileAction(self.path),
                    RunCommandAction("python -m compileall .", cwd="."),
                )
            )
        if session.errors:
            return ActionGraph(
                actions=(
                    EditFileAction(self.path, "VALUE = \n", "VALUE = 'fixed'\n"),
                    RunCommandAction("python -m compileall .", cwd="."),
                    ReadFileAction(self.path),
                )
            )
        return None


def verify_compile_and_content(session: AgentSession) -> bool:
    if not session.executed_actions:
        return False
    command_ok = any(
        result.outputs.get("exit_code") == 0
        for result in session.executed_actions
        if "exit_code" in result.outputs
    )
    content_ok = any(
        result.outputs.get("content") == "VALUE = 'fixed'\n"
        for result in session.executed_actions
        if "content" in result.outputs
    )
    return command_ok and content_ok


def create_self_development_loop(executor: ActionExecutor, path: str) -> ActionAgentLoop:
    planner = SelfDevelopmentPlanner(path=path)
    return ActionAgentLoop(
        executor=executor,
        decide_next=planner.decide_next,
        verify=verify_compile_and_content,
        max_iterations=3,
    )
