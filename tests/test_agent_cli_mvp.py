from pathlib import Path

from agent.llm import LocalMvpAdapter
from agent.mvp import AgentRunner
from runtime.actions.models import ActionKind
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
