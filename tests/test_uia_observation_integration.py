import os
import platform

import pytest

from runtime.ui import Locator, UIControlType

if platform.system() != "Windows":
    pytest.skip("requires Windows", allow_module_level=True)

pytest.importorskip("comtypes")

from computer import create_default_computer
from runtime.observations import WindowLocator


pytestmark = [
    pytest.mark.integration,
    pytest.mark.windows,
    pytest.mark.skipif(
        os.environ.get("RUN_WINDOWS_INTEGRATION") != "1",
        reason="set RUN_WINDOWS_INTEGRATION=1 to run real desktop integration tests",
    ),
]


def test_uia_observes_notepad_text_area() -> None:
    computer = create_default_computer()
    process = computer.processes.launch("notepad.exe")
    window_locator = WindowLocator(process_id=process.identity.pid)

    try:
        windows = computer.windows.find(window_locator, timeout_seconds=10.0)
        assert windows

        element = computer.ui.find(
            Locator(
                control_type=UIControlType.EDIT,
                process=process.identity.pid,
                window=window_locator,
                visible=True,
                enabled=True,
            )
        )

        assert element is not None
        assert element.identity.control_type is UIControlType.EDIT
        assert element.bounds is not None
    finally:
        if computer.processes.status(process.identity.pid) is not None:
            computer.processes.terminate(process.identity.pid)
