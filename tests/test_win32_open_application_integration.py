import os
import platform

import pytest

from runtime.actions.engine import ActionExecutor
from runtime.actions.models import ActionStatus, OpenApplicationAction
from runtime.backends import BackendManager
from runtime.observations import ProcessObservation, WindowLocator, WindowObservation
from runtime.world import WorldModel

if platform.system() != "Windows":
    pytest.skip("requires Windows", allow_module_level=True)

from computer.backends.windows import Win32Backend
from computer import create_default_computer


pytestmark = [
    pytest.mark.integration,
    pytest.mark.windows,
    pytest.mark.skipif(
        os.environ.get("RUN_WINDOWS_INTEGRATION") != "1",
        reason="set RUN_WINDOWS_INTEGRATION=1 to run real desktop integration tests",
    ),
]


def test_open_application_action_launches_process_observes_window_and_updates_world() -> None:
    world = WorldModel()
    backend = Win32Backend(window_wait_seconds=10.0)
    executor = ActionExecutor(
        backend_manager=BackendManager(action_backends=[backend]),
        world=world,
    )

    result = executor.execute(OpenApplicationAction("notepad.exe", timeout_seconds=10.0))

    try:
        assert result.status is ActionStatus.SUCCEEDED
        assert result.backend_used == "win32"
        assert result.backend_reason is not None
        assert result.outputs["pid"] > 0
        assert isinstance(result.observations["process"], ProcessObservation)
        assert isinstance(result.observations["window"], WindowObservation)
        assert not world.stale
        assert world.snapshot.data["processes"]
        assert world.snapshot.data["windows"]
    finally:
        pid = result.outputs.get("pid")
        if isinstance(pid, int):
            backend.process_driver.terminate(pid, force=True)


def test_process_and_window_runtime_flow() -> None:
    computer = create_default_computer()
    process = computer.processes.launch("notepad.exe")
    locator = WindowLocator(process_id=process.identity.pid)

    try:
        windows = computer.windows.find(locator, timeout_seconds=10.0)
        assert process.identity.pid > 0
        assert computer.processes.status(process.identity.pid) is not None
        assert windows
        assert windows[0].identity.process_id == process.identity.pid

        computer.windows.activate(locator)
        active = computer.windows.active()
        assert active is not None
        assert active.identity.process_id == process.identity.pid

        computer.windows.close(locator)
        computer.processes.wait_finished(process.identity.pid, timeout_seconds=10.0)
        assert computer.processes.status(process.identity.pid) is None
    finally:
        if computer.processes.status(process.identity.pid) is not None:
            computer.processes.terminate(process.identity.pid)
