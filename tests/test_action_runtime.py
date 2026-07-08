from runtime.actions import OpenApplicationAction
from runtime.actions.engine import ActionExecutor
from runtime.actions.models import Action, ActionResult, ActionStatus
from runtime.backends import (
    BackendCapabilities,
    BackendCandidate,
    BackendManager,
    BackendRole,
    MockBackend,
)
from computer import create_default_computer
from runtime.observations import ProcessIdentity, ProcessObservation, ProcessStatus
from runtime.world import WorldModel


def test_open_application_vertical_slice_uses_best_backend() -> None:
    low_confidence = MockBackend(confidence=0.2)
    high_confidence = MockBackend(confidence=0.9)
    manager = BackendManager(action_backends=[low_confidence, high_confidence])
    executor = ActionExecutor(backend_manager=manager)

    result = executor.execute(OpenApplicationAction("notepad.exe"))

    assert result.status is ActionStatus.SUCCEEDED
    assert result.backend_name == "mock"
    assert result.backend_reason == "supports open application action in mock runtime"
    assert high_confidence.opened_applications == ["notepad.exe"]
    assert low_confidence.opened_applications == []


def test_backend_manager_reports_missing_capability() -> None:
    manager = BackendManager()

    try:
        manager.select_action_backend(OpenApplicationAction("notepad.exe"))
    except Exception as exc:
        assert "No backend" in str(exc)
    else:
        raise AssertionError("Expected missing backend error")


def test_computer_apps_open_uses_action_executor_without_breaking_api() -> None:
    computer = create_default_computer(use_mock_backend=True)

    process_id = computer.apps.open("demo-app")

    assert process_id == 0
    assert computer.action_executor.history[-1].outputs["target"] == "demo-app"


def test_action_result_created_with_runtime_telemetry() -> None:
    manager = BackendManager(action_backends=[MockBackend(confidence=0.7)])
    executor = ActionExecutor(backend_manager=manager)

    result = executor.execute(OpenApplicationAction("demo-app"))

    assert result.started_at is not None
    assert result.finished_at is not None
    assert result.duration_seconds >= 0
    assert result.backend_used == "mock"
    assert result.backend_score == 0.7
    assert result.errors == ()
    assert result.observations == {}
    assert result.screenshots == {}


class ObservingBackend:
    @property
    def name(self) -> str:
        return "observing"

    @property
    def role(self) -> BackendRole:
        return BackendRole.MOCK

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(supports_open_application=True)

    def score(self, action: Action, context=None):
        return BackendCandidate(
            backend_name=self.name,
            score=0.5,
            reason="test backend emits process observation",
        )

    def execute(self, action: Action) -> ActionResult:
        return ActionResult(
            action_id=action.action_id,
            status=ActionStatus.SUCCEEDED,
            backend_used=self.name,
            observations={
                "process": ProcessObservation(
                    identity=ProcessIdentity(pid=123, name="demo"),
                    status=ProcessStatus.RUNNING,
                )
            },
        )


def test_action_executor_applies_observations_to_world_model() -> None:
    world = WorldModel()
    executor = ActionExecutor(
        backend_manager=BackendManager(action_backends=[ObservingBackend()]),
        world=world,
    )

    executor.execute(OpenApplicationAction("demo"))

    assert not world.stale
    assert world.snapshot.data["processes"][0].identity.pid == 123
