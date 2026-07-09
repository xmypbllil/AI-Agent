from pathlib import Path
from typing import Any, Mapping

from agent.llm import LocalMvpAdapter
from agent.mvp import AgentRunner
from runtime.actions import ActionGraph, ReadFileAction, WriteFileAction
from runtime.actions.models import Action, ActionKind, ActionResult, ActionStatus
from runtime.backends.models import BackendCapabilities, BackendCandidate, BackendRole
from runtime.backends import BackendManager, DevelopmentBackend
from runtime.actions.engine import ActionExecutor
from runtime.ui.locator import Locator


class SequencedAdapter:
    def __init__(self, graphs: list[ActionGraph]) -> None:
        self.graphs = graphs
        self.next_calls: list[tuple[str, str, int]] = []

    def generate_plan(self, goal: str, context: Mapping[str, Any]) -> ActionGraph:
        return self.graphs[0]

    def decide_next_action(
        self,
        goal: str,
        observations: Mapping[str, Any],
        previous_actions: tuple[Any, ...],
        reason: str,
    ) -> ActionGraph | None:
        self.next_calls.append((goal, reason, len(previous_actions)))
        index = len(self.next_calls)
        return self.graphs[index] if index < len(self.graphs) else None


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


class FakeUIObservationExecutor:
    def __init__(self, ui_backend: FakeTypeTextBackend) -> None:
        self.ui_backend = ui_backend

    def text(self, locator: Locator) -> str | None:
        return self.ui_backend.typed_text[-1] if self.ui_backend.typed_text else None


class EmptyUIObservationExecutor:
    def text(self, locator: Locator) -> str | None:
        return None


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
        ui_observation_executor=FakeUIObservationExecutor(ui_backend),
        trace_path=trace_path,
    )

    result = runner.run("\u043e\u0442\u043a\u0440\u043e\u0439 \u0431\u043b\u043e\u043a\u043d\u043e\u0442 \u0438 \u043d\u0430\u043f\u0438\u0448\u0438 Hello Runtime")

    assert result.verified
    assert ui_backend.typed_text == ["Hello Runtime"]
    assert result.session.current_plan == ("open_application", "type_text")
    trace = trace_path.read_text(encoding="utf-8")
    assert "open_application" in trace
    assert "type_text" in trace


def test_agent_runner_does_not_verify_type_text_without_ui_readback(tmp_path: Path) -> None:
    ui_backend = FakeTypeTextBackend()
    executor = ActionExecutor(
        backend_manager=BackendManager(
            action_backends=[FakeOpenApplicationBackend()],
            ui_action_backends=[ui_backend],
        )
    )
    runner = AgentRunner(
        adapter=LocalMvpAdapter(),
        executor=executor,
        ui_observation_executor=EmptyUIObservationExecutor(),
        trace_path=tmp_path / "trace.json",
    )

    result = runner.run(
        "\u041e\u0442\u043a\u0440\u043e\u0439 \u0431\u043b\u043e\u043a\u043d\u043e\u0442 "
        "\u0438 \u043d\u0430\u043f\u0438\u0448\u0438 Hello Runtime"
    )

    assert not result.verified
    assert result.session.final_result == "failed"
    assert ui_backend.typed_text == ["Hello Runtime"]


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


def test_agent_runner_production_demo_file_with_cyrillic_content(tmp_path: Path) -> None:
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
        "\u0421\u043e\u0437\u0434\u0430\u0439 \u0444\u0430\u0439\u043b demo.txt "
        "\u0441 \u0442\u0435\u043a\u0441\u0442\u043e\u043c "
        "\u041f\u0440\u0438\u0432\u0435\u0442, \u0430\u0433\u0435\u043d\u0442! "
        "\u0438 \u043f\u0440\u043e\u0432\u0435\u0440\u044c \u0447\u0442\u043e "
        "\u0444\u0430\u0439\u043b \u0441\u043e\u0434\u0435\u0440\u0436\u0438\u0442 "
        "\u044d\u0442\u043e\u0442 \u0442\u0435\u043a\u0441\u0442"
    )

    assert result.verified
    assert (tmp_path / "demo.txt").read_text(encoding="utf-8") == "\u041f\u0440\u0438\u0432\u0435\u0442, \u0430\u0433\u0435\u043d\u0442!"
    assert result.session.current_plan == ("write_file", "read_file")
    trace = trace_path.read_text(encoding="utf-8")
    assert "demo.txt" in trace
    assert "\u041f\u0440\u0438\u0432\u0435\u0442, \u0430\u0433\u0435\u043d\u0442!" in trace
    assert "verified_files" in trace


def test_agent_runner_production_project_report(tmp_path: Path) -> None:
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
        "\u041f\u0440\u043e\u0430\u043d\u0430\u043b\u0438\u0437\u0438\u0440\u0443\u0439 "
        "\u043f\u0440\u043e\u0435\u043a\u0442 \u0438 \u0441\u043e\u0437\u0434\u0430\u0439 report.md"
    )

    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert result.verified
    assert "# Project Report" in report
    assert "Desktop LLM Runtime" in report
    assert result.session.current_plan == ("write_file", "read_file")
    trace = trace_path.read_text(encoding="utf-8")
    assert "report.md" in trace
    assert "verified_files" in trace


def test_planner_reads_file_without_file_keyword() -> None:
    graph = LocalMvpAdapter().generate_plan(
        "\u043f\u0440\u043e\u0447\u0438\u0442\u0430\u0439 readme.md",
        {},
    )

    actions = graph.ordered()
    assert [action.kind for action in actions] == [ActionKind.READ_FILE]
    assert actions[0].inputs["path"] == "readme.md"


def test_planner_finds_file_by_name() -> None:
    graph = LocalMvpAdapter().generate_plan(
        "\u043d\u0430\u0439\u0434\u0438 \u0444\u0430\u0439\u043b pyproject.toml",
        {},
    )

    actions = graph.ordered()
    assert [action.kind for action in actions] == [ActionKind.SEARCH_FILES]
    assert actions[0].inputs["pattern"] == "pyproject.toml"


def test_planner_finds_text_in_project() -> None:
    graph = LocalMvpAdapter().generate_plan(
        "\u043d\u0430\u0439\u0434\u0438 \u0442\u0435\u043a\u0441\u0442 ActionGraph "
        "\u0432 \u043f\u0440\u043e\u0435\u043a\u0442\u0435",
        {},
    )

    actions = graph.ordered()
    assert [action.kind for action in actions] == [ActionKind.RUN_COMMAND]
    command = str(actions[0].inputs["command"])
    assert command.startswith('python -c "import base64; exec(')


def test_planner_edits_file_when_replacement_is_provided() -> None:
    graph = LocalMvpAdapter().generate_plan(
        "\u0438\u0437\u043c\u0435\u043d\u0438 \u0444\u0430\u0439\u043b sample.txt "
        "\u0437\u0430\u043c\u0435\u043d\u0438 old \u043d\u0430 new",
        {},
    )

    actions = graph.ordered()
    assert [action.kind for action in actions] == [ActionKind.EDIT_FILE, ActionKind.READ_FILE]
    assert actions[0].inputs["path"] == "sample.txt"
    assert actions[0].inputs["old"] == "old"
    assert actions[0].inputs["new"] == "new"


def test_planner_creates_folder_with_existing_command_action() -> None:
    graph = LocalMvpAdapter().generate_plan(
        "\u0441\u043e\u0437\u0434\u0430\u0439 \u043f\u0430\u043f\u043a\u0443 output",
        {},
    )

    actions = graph.ordered()
    assert [action.kind for action in actions] == [ActionKind.RUN_COMMAND]
    assert actions[0].inputs["command"] == 'cmd /c mkdir "output"'


def test_planner_shows_current_folder_with_existing_command_action() -> None:
    graph = LocalMvpAdapter().generate_plan(
        "\u043f\u043e\u043a\u0430\u0436\u0438 \u0442\u0435\u043a\u0443\u0449\u0443\u044e "
        "\u043f\u0430\u043f\u043a\u0443",
        {},
    )

    actions = graph.ordered()
    assert [action.kind for action in actions] == [ActionKind.RUN_COMMAND]
    assert actions[0].inputs["command"] == "cd"


def test_planner_opens_paint_application() -> None:
    graph = LocalMvpAdapter().generate_plan("\u043e\u0442\u043a\u0440\u043e\u0439 paint", {})

    actions = graph.ordered()
    assert [action.kind for action in actions] == [ActionKind.OPEN_APPLICATION]
    assert actions[0].inputs["target"] == "mspaint.exe"


def test_planner_closes_notepad_without_opening_new_instance() -> None:
    graph = LocalMvpAdapter().generate_plan(
        "\u0437\u0430\u043a\u0440\u043e\u0439 \u0431\u043b\u043e\u043a\u043d\u043e\u0442",
        {},
    )

    actions = graph.ordered()
    assert [action.kind for action in actions] == [ActionKind.CLOSE_WINDOW]
    assert actions[0].inputs["locator"].class_name == "Notepad"


def test_agent_loop_replans_from_read_to_write_and_verify(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("seed", encoding="utf-8")
    adapter = SequencedAdapter(
        [
            ActionGraph(actions=(ReadFileAction("source.txt"),)),
            ActionGraph(actions=(WriteFileAction("result.txt", "done"), ReadFileAction("result.txt"))),
        ]
    )
    runner = AgentRunner(
        adapter=adapter,
        executor=ActionExecutor(
            backend_manager=BackendManager(action_backends=[DevelopmentBackend(root=tmp_path)])
        ),
        trace_path=tmp_path / "trace.json",
    )

    result = runner.run("read source.txt and create result.txt")

    assert result.verified
    assert (tmp_path / "result.txt").read_text(encoding="utf-8") == "done"
    assert result.session.current_plan == ("read_file", "write_file", "read_file")
    assert result.session.completed_goals == ["files"]
    assert adapter.next_calls[0][0] == "read source.txt and create result.txt"
    assert "pending: files" in adapter.next_calls[0][1]


def test_agent_loop_reads_file_then_creates_report(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Runtime notes", encoding="utf-8")
    adapter = SequencedAdapter(
        [
            ActionGraph(actions=(ReadFileAction("README.md"),)),
            ActionGraph(actions=(WriteFileAction("report.md", "# Report\n\nRuntime notes"), ReadFileAction("report.md"))),
        ]
    )
    runner = AgentRunner(
        adapter=adapter,
        executor=ActionExecutor(
            backend_manager=BackendManager(action_backends=[DevelopmentBackend(root=tmp_path)])
        ),
        trace_path=tmp_path / "trace.json",
    )

    result = runner.run("read README.md and create report.md")

    assert result.verified
    assert "# Report" in (tmp_path / "report.md").read_text(encoding="utf-8")
    trace = (tmp_path / "trace.json").read_text(encoding="utf-8")
    assert '"replans_count": 1' in trace
    assert '"evaluation_reason": "goal achieved"' in trace


def test_agent_loop_replanner_writes_created_file_after_reading_source(tmp_path: Path) -> None:
    source = tmp_path / "runtime" / "actions" / "engine.py"
    source.parent.mkdir(parents=True)
    source.write_text("class ActionExecutor: ...\n", encoding="utf-8")
    runner = AgentRunner(
        adapter=LocalMvpAdapter(),
        executor=ActionExecutor(
            backend_manager=BackendManager(action_backends=[DevelopmentBackend(root=tmp_path)])
        ),
        trace_path=tmp_path / "trace.json",
    )

    result = runner.run(
        "\u043f\u0440\u043e\u0447\u0438\u0442\u0430\u0439 runtime/actions/engine.py "
        "\u0438 \u0441\u043e\u0437\u0434\u0430\u0439 engine-notes.md"
    )

    assert result.verified
    assert (tmp_path / "engine-notes.md").exists()
    assert result.session.current_plan == ("read_file", "write_file", "read_file")
    trace = (tmp_path / "trace.json").read_text(encoding="utf-8")
    assert "engine-notes.md" in trace


def test_agent_loop_does_not_verify_partial_file_goal(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Runtime notes", encoding="utf-8")
    adapter = SequencedAdapter([ActionGraph(actions=(ReadFileAction("README.md"),))])
    runner = AgentRunner(
        adapter=adapter,
        executor=ActionExecutor(
            backend_manager=BackendManager(action_backends=[DevelopmentBackend(root=tmp_path)])
        ),
        trace_path=tmp_path / "trace.json",
    )

    result = runner.run("read README.md and create missing_report.md")

    assert not result.verified
    assert result.session.final_result == "failed"
    assert "files" in result.session.pending_goals


def test_agent_loop_multi_step_execution_records_goal_state(tmp_path: Path) -> None:
    adapter = SequencedAdapter(
        [
            ActionGraph(actions=(WriteFileAction("first.txt", "one"), ReadFileAction("first.txt"))),
            ActionGraph(actions=(WriteFileAction("second.txt", "two"), ReadFileAction("second.txt"))),
        ]
    )
    runner = AgentRunner(
        adapter=adapter,
        executor=ActionExecutor(
            backend_manager=BackendManager(action_backends=[DevelopmentBackend(root=tmp_path)])
        ),
        trace_path=tmp_path / "trace.json",
        max_steps=3,
    )

    result = runner.run("create first.txt and second.txt")

    assert result.verified
    assert (tmp_path / "first.txt").exists()
    assert (tmp_path / "second.txt").exists()
    assert result.session.goal_state["actions_ok"] is True
