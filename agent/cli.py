"""Command line entry point for the local computer agent."""

from __future__ import annotations

import argparse
from pathlib import Path

from agent.mvp import AgentRunner
from agent.providers import create_adapter_from_env
from computer import create_default_computer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="computer-agent")
    parser.add_argument("goal", help="Task for the local agent to execute.")
    parser.add_argument(
        "--trace",
        default=str(Path("evaluations") / "last-agent-cli-trace.json"),
        help="Path where the runtime trace will be saved.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    computer = create_default_computer(root=Path.cwd())
    runner = AgentRunner(
        adapter=create_adapter_from_env(),
        executor=computer.action_executor,
        trace_path=Path(args.trace),
    )
    result = runner.run(args.goal)
    print(f"result: {result.session.final_result}")
    print(f"trace: {result.trace_path}")
    if result.session.errors:
        print("errors:")
        for error in result.session.errors:
            print(f"- {error}")
    return 0 if result.verified else 1


if __name__ == "__main__":
    raise SystemExit(main())
