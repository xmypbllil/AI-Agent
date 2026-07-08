"""Demo: agent loop edits a tiny project and repairs compile failure.

Run from the repository root:

    python -m examples.self_development_loop
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from agent import create_self_development_loop
from runtime.actions.engine import ActionExecutor
from runtime.backends import BackendManager, DevelopmentBackend


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        executor = ActionExecutor(
            backend_manager=BackendManager(
                action_backends=[DevelopmentBackend(root=root)],
            )
        )
        loop = create_self_development_loop(executor=executor, path="module.py")
        session = loop.run("Read project file, modify code, run compileall, verify success")

        print(f"goal: {session.goal}")
        print(f"final_result: {session.final_result}")
        print(f"errors: {session.errors}")
        print("actions:")
        for result in session.executed_actions:
            print(f"  {result.status} {result.backend_used} {result.outputs}")


if __name__ == "__main__":
    main()
