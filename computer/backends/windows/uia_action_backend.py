"""Microsoft UI Automation action backend."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping

from computer.backends.windows.mouse import WindowsMouseDriver
from computer.backends.windows.uia_backend import UIAObservationBackend, UIAutomationClient
from computer.models import MouseButton, Point
from runtime.actions.models import Action, ActionKind, ActionResult, ActionStatus
from runtime.backends.models import BackendCapabilities, BackendCandidate, BackendRole
from runtime.ui import Locator

UIA_InvokePatternId = 10000
UIA_ValuePatternId = 10002


@dataclass(slots=True)
class UIAActionBackend:
    observation_backend: UIAObservationBackend = field(default_factory=UIAObservationBackend)
    mouse_driver: WindowsMouseDriver = field(default_factory=WindowsMouseDriver)

    @property
    def name(self) -> str:
        return "uia-action"

    @property
    def role(self) -> BackendRole:
        return BackendRole.UI_AUTOMATION

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            supports_click=True,
            supports_keyboard=True,
            supports_pattern=True,
            supports_tree=True,
            supports_text=True,
        )

    def score_ui_action(
        self,
        action: Action,
        context: Mapping[str, Any] | None = None,
    ) -> BackendCandidate | None:
        if action.kind not in {ActionKind.CLICK, ActionKind.TYPE_TEXT}:
            return None
        return BackendCandidate(
            backend_name=self.name,
            score=0.95,
            reason="supports UIA InvokePattern/ValuePattern for basic UI actions",
        )

    def execute_ui(self, action: Action) -> ActionResult:
        started_at = datetime.now(tz=UTC)
        try:
            if action.kind is ActionKind.CLICK:
                return self._click(action, started_at)
            if action.kind is ActionKind.TYPE_TEXT:
                return self._type_text(action, started_at)
            return self._failure(action, started_at, f"Unsupported UI action: {action.kind}")
        except Exception as exc:  # noqa: BLE001 - COM/native failures become runtime result.
            return self._failure(action, started_at, str(exc))

    def _click(self, action: Action, started_at: datetime) -> ActionResult:
        locator = self._locator(action)
        element = self.observation_backend._element_for(locator)
        pattern = element.GetCurrentPattern(UIA_InvokePatternId)
        if pattern:
            pattern.QueryInterface(UIAutomationClient.IUIAutomationInvokePattern).Invoke()
        else:
            observation = self.observation_backend._observation(element)
            if observation.bounds is None:
                raise RuntimeError("Cannot click element without bounds")
            point = Point(
                x=observation.bounds.left + observation.bounds.width // 2,
                y=observation.bounds.top + observation.bounds.height // 2,
            )
            self.mouse_driver.click(point=point, button=MouseButton.LEFT)
        return self._success(action, started_at)

    def _type_text(self, action: Action, started_at: datetime) -> ActionResult:
        locator = self._locator(action)
        text = str(action.inputs["text"])
        element = self.observation_backend._element_for(locator)
        pattern = element.GetCurrentPattern(UIA_ValuePatternId)
        if not pattern:
            raise RuntimeError("Element does not support ValuePattern")
        pattern.QueryInterface(UIAutomationClient.IUIAutomationValuePattern).SetValue(text)
        observation = self.observation_backend._observation(element)
        return self._success(action, started_at, observations={"element": observation}, outputs={"text": text})

    def _locator(self, action: Action) -> Locator:
        locator = action.inputs["locator"]
        if not isinstance(locator, Locator):
            raise TypeError("UI action locator must be runtime.ui.Locator")
        return locator

    def _success(
        self,
        action: Action,
        started_at: datetime,
        outputs: Mapping[str, object] | None = None,
        observations: Mapping[str, object] | None = None,
    ) -> ActionResult:
        return ActionResult(
            action_id=action.action_id,
            status=ActionStatus.SUCCEEDED,
            started_at=started_at,
            finished_at=datetime.now(tz=UTC),
            backend_used=self.name,
            backend_score=0.95,
            backend_reason="executed through Microsoft UI Automation patterns",
            outputs={} if outputs is None else outputs,
            observations={} if observations is None else observations,
        )

    def _failure(self, action: Action, started_at: datetime, error: str) -> ActionResult:
        return ActionResult(
            action_id=action.action_id,
            status=ActionStatus.FAILED,
            started_at=started_at,
            finished_at=datetime.now(tz=UTC),
            backend_used=self.name,
            backend_score=0.95,
            backend_reason="supports UIA InvokePattern/ValuePattern for basic UI actions",
            errors=(error,),
        )
