"""Demo: open Notepad and write Hello Runtime through the desktop runtime.

Run manually on Windows:

    python examples/notepad_hello_runtime.py
"""

from __future__ import annotations

from computer import create_default_computer


def main() -> None:
    instruction = "Open Notepad and write Hello Runtime"
    computer = create_default_computer()
    result = computer.run(instruction)
    pid = result.action_results[0].outputs.get("pid") if result.action_results else None

    try:
        print(f"instruction: {result.instruction}")
        print(f"verified: {result.verified}")
        print("actions:")
        for item in result.action_results:
            print(f"  action_id: {item.action_id}")
            print(f"    status: {item.status}")
            print(f"    backend: {item.backend_used}")
            print(f"    score: {item.backend_score}")
            print(f"    reason: {item.backend_reason}")
            print(f"    outputs: {dict(item.outputs)}")
            print(f"    errors: {item.errors}")
    finally:
        if isinstance(pid, int) and computer.processes.status(pid) is not None:
            computer.processes.terminate(pid)


if __name__ == "__main__":
    main()
