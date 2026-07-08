import os
import platform

import pytest

if platform.system() != "Windows":
    pytest.skip("requires Windows", allow_module_level=True)

pytest.importorskip("comtypes")

from computer import create_default_computer


pytestmark = [
    pytest.mark.integration,
    pytest.mark.windows,
    pytest.mark.skipif(
        os.environ.get("RUN_WINDOWS_INTEGRATION") != "1",
        reason="set RUN_WINDOWS_INTEGRATION=1 to run real desktop integration tests",
    ),
]


def test_e2e_open_notepad_and_write_hello_runtime() -> None:
    computer = create_default_computer()
    result = computer.run("Open Notepad and write Hello Runtime")
    pid = result.action_results[0].outputs.get("pid")

    try:
        assert result.verified
        assert result.action_results[-1].backend_used == "uia-action"
    finally:
        if isinstance(pid, int) and computer.processes.status(pid) is not None:
            computer.processes.terminate(pid)
