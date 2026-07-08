"""Typed desktop API exposed to model-authored Python."""

from __future__ import annotations

from dataclasses import dataclass
import platform
from pathlib import Path
from typing import NamedTuple

from computer.apps import Apps
from computer.audio import Audio
from computer.browser import Browser
from computer.clipboard import Clipboard
from computer.environment import Environment
from computer.files import Files
from computer.git import Git
from computer.keyboard import Keyboard
from computer.mouse import Mouse
from computer.network import Network
from computer.ocr import Ocr
from computer.packages import Packages
from computer.ports import ClipboardDriver, KeyboardDriver, MouseDriver, ScreenDriver, WindowDriver
from computer.processes import Processes
from computer.python import Python
from computer.registry import Registry
from computer.runner import ComputerRunner, RunResult
from computer.screen import Screen
from computer.services import Services
from computer.system import System
from computer.terminal import Terminal
from computer.ui import UI
from computer.vision import Vision
from computer.windows import Windows
from runtime.actions.engine import ActionExecutor
from runtime.backends.ports import ActionBackend
from runtime.backends import BackendManager, DevelopmentBackend, MockBackend
from runtime.observations.engine import ObservationExecutor
from runtime.backends.ports import ObservationBackend
from runtime.ui.ports import UIObservationBackend
from runtime.ui.ports import UIActionBackend
from runtime.ui.engine import UIObservationExecutor
from runtime.world import WorldModel


class _DesktopDrivers(NamedTuple):
    clipboard: ClipboardDriver | None = None
    keyboard: KeyboardDriver | None = None
    mouse: MouseDriver | None = None
    screen: ScreenDriver | None = None
    windows: WindowDriver | None = None
    action_backend: ActionBackend | None = None
    observation_backend: ObservationBackend | None = None
    ui_observation_backend: UIObservationBackend | None = None
    ui_action_backend: UIActionBackend | None = None


def _windows_drivers() -> _DesktopDrivers:
    if platform.system() != "Windows":
        return _DesktopDrivers()
    from computer.backends.windows import (  # noqa: PLC0415 - platform-specific lazy import.
        WindowsClipboardDriver,
        WindowsKeyboardDriver,
        WindowsMouseDriver,
        WindowsScreenDriver,
        WindowsWindowDriver,
        Win32Backend,
    )
    try:
        from computer.backends.windows.uia_backend import UIAObservationBackend  # noqa: PLC0415
        from computer.backends.windows.uia_action_backend import UIAActionBackend  # noqa: PLC0415
    except ImportError:
        UIAObservationBackend = None  # type: ignore[assignment]
        UIAActionBackend = None  # type: ignore[assignment]
    ui_observation_backend = UIAObservationBackend() if UIAObservationBackend else None
    ui_action_backend = (
        UIAActionBackend(observation_backend=ui_observation_backend)
        if UIAActionBackend and ui_observation_backend
        else None
    )

    win32_backend = Win32Backend()
    return _DesktopDrivers(
        clipboard=WindowsClipboardDriver(),
        keyboard=WindowsKeyboardDriver(),
        mouse=WindowsMouseDriver(),
        screen=WindowsScreenDriver(),
        windows=WindowsWindowDriver(),
        action_backend=win32_backend,
        observation_backend=win32_backend,
        ui_observation_backend=ui_observation_backend,
        ui_action_backend=ui_action_backend,
    )


@dataclass(frozen=True, slots=True)
class Computer:
    apps: Apps
    windows: Windows
    mouse: Mouse
    keyboard: Keyboard
    files: Files
    clipboard: Clipboard
    terminal: Terminal
    screen: Screen
    vision: Vision
    ocr: Ocr
    processes: Processes
    ui: UI
    browser: Browser
    network: Network
    audio: Audio
    system: System
    packages: Packages
    git: Git
    python: Python
    services: Services
    registry: Registry
    environment: Environment
    action_executor: ActionExecutor
    observation_executor: ObservationExecutor
    ui_observation_executor: UIObservationExecutor
    runner: ComputerRunner

    def run(self, instruction: str) -> RunResult:
        return self.runner.run(instruction)
    backend_manager: BackendManager
    world: WorldModel


def create_default_computer(root: Path | None = None, use_mock_backend: bool = False) -> Computer:
    terminal = Terminal(cwd=root)
    drivers = _windows_drivers()
    world = WorldModel()
    action_backends: list[ActionBackend] = []
    if drivers.action_backend is not None and not use_mock_backend:
        action_backends.append(drivers.action_backend)
    if use_mock_backend or not action_backends:
        action_backends.append(MockBackend())
    action_backends.append(DevelopmentBackend(root=root or Path.cwd()))
    observation_backends: list[ObservationBackend] = []
    if drivers.observation_backend is not None and not use_mock_backend:
        observation_backends.append(drivers.observation_backend)
    ui_observation_backends: list[UIObservationBackend] = []
    if drivers.ui_observation_backend is not None and not use_mock_backend:
        ui_observation_backends.append(drivers.ui_observation_backend)
    ui_action_backends: list[UIActionBackend] = []
    if drivers.ui_action_backend is not None and not use_mock_backend:
        ui_action_backends.append(drivers.ui_action_backend)
    backend_manager = BackendManager(
        action_backends=action_backends,
        observation_backends=observation_backends,
        ui_observation_backends=ui_observation_backends,
        ui_action_backends=ui_action_backends,
    )
    action_executor = ActionExecutor(backend_manager=backend_manager, world=world)
    observation_executor = ObservationExecutor(backend_manager=backend_manager, world=world)
    ui_observation_executor = UIObservationExecutor(backend_manager=backend_manager)
    runner = ComputerRunner(
        action_executor=action_executor,
        ui_observation_executor=ui_observation_executor,
    )
    return Computer(
        apps=Apps(action_executor=action_executor),
        windows=Windows(action_executor=action_executor, observation_executor=observation_executor),
        mouse=Mouse(driver=drivers.mouse),
        keyboard=Keyboard(driver=drivers.keyboard),
        files=Files(root=root),
        clipboard=Clipboard(driver=drivers.clipboard),
        terminal=terminal,
        screen=Screen(driver=drivers.screen),
        vision=Vision(),
        ocr=Ocr(),
        processes=Processes(action_executor=action_executor, observation_executor=observation_executor),
        ui=UI(observation_executor=ui_observation_executor),
        browser=Browser(),
        network=Network(),
        audio=Audio(),
        system=System(),
        packages=Packages(),
        git=Git(terminal=terminal),
        python=Python(),
        services=Services(),
        registry=Registry(),
        environment=Environment(),
        action_executor=action_executor,
        observation_executor=observation_executor,
        ui_observation_executor=ui_observation_executor,
        runner=runner,
        backend_manager=backend_manager,
        world=world,
    )


__all__ = ["Computer", "create_default_computer"]
