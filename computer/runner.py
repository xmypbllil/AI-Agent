"""Minimal task runner for the first E2E runtime scenario."""

from __future__ import annotations

from dataclasses import dataclass

from runtime.actions import OpenApplicationAction, TypeTextAction
from runtime.actions.engine import ActionExecutor
from runtime.actions.graph import ActionGraph
from runtime.actions.models import ActionResult, ActionStatus
from runtime.observations import WindowLocator
from runtime.ui import Locator, UIControlType
from runtime.ui.engine import UIObservationExecutor


@dataclass(frozen=True, slots=True)
class RunResult:
    instruction: str
    action_results: tuple[ActionResult, ...]
    verified: bool


@dataclass(frozen=True, slots=True)
class ComputerRunner:
    action_executor: ActionExecutor
    ui_observation_executor: UIObservationExecutor

    def run(self, instruction: str) -> RunResult:
        normalized = instruction.lower()
        if "notepad" not in normalized:
            raise ValueError("The first E2E runner only supports Notepad")
        text = "Hello Runtime"
        graph = ActionGraph(actions=(OpenApplicationAction("notepad.exe"),))
        results = [self.action_executor.execute(action) for action in graph.ordered()]
        if results[-1].status is not ActionStatus.SUCCEEDED:
            return RunResult(instruction=instruction, action_results=tuple(results), verified=False)

        pid = int(results[-1].outputs["pid"])
        locator = Locator(
            control_type=UIControlType.EDIT,
            process=pid,
            window=WindowLocator(process_id=pid),
            visible=True,
            enabled=True,
        )
        type_result = self.action_executor.execute(TypeTextAction(locator=locator, text=text))
        results.append(type_result)
        observed_text = self.ui_observation_executor.text(locator)
        return RunResult(
            instruction=instruction,
            action_results=tuple(results),
            verified=observed_text is not None and text in observed_text,
        )
