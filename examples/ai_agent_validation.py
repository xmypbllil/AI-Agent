"""Run the provider-backed agent on the project validation goal."""

from __future__ import annotations

from pathlib import Path

from agent.mvp import AgentRunner
from agent.providers import create_adapter_from_env
from computer import create_default_computer


def main() -> None:
    computer = create_default_computer(root=Path.cwd())
    agent = AgentRunner(
        adapter=create_adapter_from_env(),
        executor=computer.action_executor,
        trace_path=Path("evaluations") / "last-ai-agent-validation-trace.json",
    )
    result = agent.run("\u043f\u0440\u043e\u0432\u0435\u0440\u044c \u043f\u0440\u043e\u0435\u043a\u0442 \u0438 \u0437\u0430\u043f\u0443\u0441\u0442\u0438 validation")
    print(f"result: {result.session.final_result}")
    print(f"trace: {result.trace_path}")


if __name__ == "__main__":
    main()
