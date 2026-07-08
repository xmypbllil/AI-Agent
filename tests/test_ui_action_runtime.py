from runtime.actions import TypeTextAction
from runtime.actions.engine import ActionExecutor
from runtime.actions.models import Action, ActionResult, ActionStatus
from runtime.backends import BackendCapabilities, BackendCandidate, BackendManager, BackendRole
from runtime.ui import Locator


class FakeUIActionBackend:
    def __init__(self) -> None:
        self.typed: str | None = None

    @property
    def name(self) -> str:
        return "fake-ui-action"

    @property
    def role(self) -> BackendRole:
        return BackendRole.UI_AUTOMATION

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(supports_keyboard=True, supports_pattern=True)

    def score_ui_action(self, action: Action, context=None):
        return BackendCandidate(
            backend_name=self.name,
            score=0.9,
            reason="test UI action backend",
        )

    def execute_ui(self, action: Action) -> ActionResult:
        self.typed = str(action.inputs["text"])
        return ActionResult(
            action_id=action.action_id,
            status=ActionStatus.SUCCEEDED,
            backend_used=self.name,
            backend_score=0.9,
            backend_reason="test UI action backend",
            outputs={"text": self.typed},
        )


def test_action_executor_dispatches_type_text_to_ui_action_backend() -> None:
    backend = FakeUIActionBackend()
    executor = ActionExecutor(backend_manager=BackendManager(ui_action_backends=[backend]))

    result = executor.execute(TypeTextAction(locator=Locator(name="Editor"), text="Hello Runtime"))

    assert result.status is ActionStatus.SUCCEEDED
    assert result.backend_used == "fake-ui-action"
    assert backend.typed == "Hello Runtime"
