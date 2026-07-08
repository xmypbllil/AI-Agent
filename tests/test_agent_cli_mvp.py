from pathlib import Path
from typing import Any, Mapping

from agent.llm import LocalMvpAdapter
from agent.mvp import AgentRunner
from runtime.actions.models import Action, ActionKind, ActionResult, ActionStatus
from runtime.backends.models import BackendCapabilities, BackendCandidate, BackendRole
from runtime.backends import BackendManager, DevelopmentBackend
from runtime.actions.engine import ActionExecutor


def test_local_mvp_adapter_generates_command_graph() -> None:
    graph = LocalMvpAdapter().generate_plan("python -m compileall agent", {})

    actions = graph.ordered()
    assert len(actions) == 1
    assert actions[0].kind is ActionKind.RUN_COMMAND
    assert actions[0].inputs["command"] == "python -m compileall agent"


def test_agent_runner_executes_goal_and_writes_trace(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    target.write_text("VALUE = 1\n", encoding="utf-8")
    executor = ActionExecutor(
        backend_manager=BackendManager(action_backends=[DevelopmentBackend(root=tmp_path)])
    )
    trace_path = tmp_path / "trace.json"
    runner = AgentRunner(
        adapter=LocalMvpAdapter(),
        executor=executor,
        trace_path=trace_path,
    )

    result = runner.run("python -m compileall module.py")

    assert result.verified
    assert trace_path.exists()
    assert "python -m compileall module.py" in trace_path.read_text(encoding="utf-8")


class FakeOpenApplicationBackend:
    @property
    def name(self) -> str:
        return "fake-open"

    @property
    def role(self) -> BackendRole:
        return BackendRole.MOCK

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(supports_open_application=True)

    def score(
        self,
        action: Action,
        context: Mapping[str, Any] | None = None,
    ) -> BackendCandidate | None:
        if action.kind is not ActionKind.OPEN_APPLICATION:
            return None
        return BackendCandidate(self.name, 0.99, "fake open application")

    def execute(self, action: Action) -> ActionResult:
        return ActionResult(
            action_id=action.action_id,
            status=ActionStatus.SUCCEEDED,
            backend_used=self.name,
            backend_score=0.99,
            outputs={"pid": 1234, "target": action.inputs["target"]},
        )


class FakeTypeTextBackend:
    def __init__(self) -> None:
        self.typed_text: list[str] = []

    @property
    def name(self) -> str:
        return "fake-ui"

    @property
    def role(self) -> BackendRole:
        return BackendRole.MOCK

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(supports_text=True)

    def score_ui_action(
        self,
        action: Action,
        context: Mapping[str, Any] | None = None,
    ) -> BackendCandidate | None:
        if action.kind is not ActionKind.TYPE_TEXT:
            return None
        return BackendCandidate(self.name, 0.99, "fake type text")

    def execute_ui(self, action: Action) -> ActionResult:
        self.typed_text.append(str(action.inputs["text"]))
        return ActionResult(
            action_id=action.action_id,
            status=ActionStatus.SUCCEEDED,
            backend_used=self.name,
            backend_score=0.99,
            outputs={"text": action.inputs["text"]},
        )


def test_agent_runner_continues_from_open_application_to_type_text(tmp_path: Path) -> None:
    ui_backend = FakeTypeTextBackend()
    executor = ActionExecutor(
        backend_manager=BackendManager(
            action_backends=[FakeOpenApplicationBackend()],
            ui_action_backends=[ui_backend],
        )
    )
    trace_path = tmp_path / "trace.json"
    runner = AgentRunner(
        adapter=LocalMvpAdapter(),
        executor=executor,
        trace_path=trace_path,
    )

    result = runner.run("\u043e\u0442\u043a\u0440\u043e\u0439 \u0431\u043b\u043e\u043a\u043d\u043e\u0442 \u0438 \u043d\u0430\u043f\u0438\u0448\u0438 Hello Runtime")

    assert result.verified
    assert ui_backend.typed_text == ["Hello Runtime"]
    assert result.session.current_plan == ("open_application", "type_text")
    trace = trace_path.read_text(encoding="utf-8")
    assert "open_application" in trace
    assert "type_text" in trace


def test_agent_runner_creates_and_verifies_file_from_russian_goal(tmp_path: Path) -> None:
    executor = ActionExecutor(
        backend_manager=BackendManager(action_backends=[DevelopmentBackend(root=tmp_path)])
    )
    trace_path = tmp_path / "trace.json"
    runner = AgentRunner(
        adapter=LocalMvpAdapter(),
        executor=executor,
        trace_path=trace_path,
    )

    result = runner.run(
        "\u0421\u043e\u0437\u0434\u0430\u0439 \u0444\u0430\u0439\u043b test_agent.txt "
        "\u0441 \u0442\u0435\u043a\u0441\u0442\u043e\u043c Hello Agent "
        "\u0438 \u043f\u0440\u043e\u0432\u0435\u0440\u044c \u0447\u0442\u043e \u043e\u043d \u0441\u0443\u0449\u0435\u0441\u0442\u0432\u0443\u0435\u0442"
    )

    assert result.verified
    assert (tmp_path / "test_agent.txt").read_text(encoding="utf-8") == "Hello Agent"
    assert result.session.current_plan == ("write_file", "read_file")
    trace = trace_path.read_text(encoding="utf-8")
    assert "write_file" in trace
    assert "read_file" in trace
    assert "Hello Agent" in trace
