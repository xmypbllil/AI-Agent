"""Win32 action backend adapter."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from computer.backends.windows.processes import WindowsProcessDriver
from computer.backends.windows.windows import WindowsWindowDriver
from runtime.actions.models import Action, ActionKind, ActionResult, ActionStatus
from runtime.backends.models import BackendCapabilities, BackendCandidate, BackendRole
from runtime.observations import (
    Bounds,
    ProcessIdentity,
    ProcessObservation,
    ProcessStatus,
    WindowIdentity,
    WindowLocator,
    WindowObservation,
)
from runtime.observations.queries import ObservationKind, ObservationQuery, ObservationResult


@dataclass(slots=True)
class Win32Backend:
    """Adapter that maps runtime actions to Windows process/window APIs."""

    process_driver: WindowsProcessDriver = field(default_factory=WindowsProcessDriver)
    window_driver: WindowsWindowDriver = field(default_factory=WindowsWindowDriver)
    window_wait_seconds: float = 10.0
    poll_interval_seconds: float = 0.25

    @property
    def name(self) -> str:
        return "win32"

    @property
    def role(self) -> BackendRole:
        return BackendRole.WIN32

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            supports_open_application=True,
            supports_processes=True,
            supports_window_search=True,
        )

    def score(self, action: Action, context: object | None = None) -> BackendCandidate | None:
        if action.kind not in {
            ActionKind.OPEN_APPLICATION,
            ActionKind.LAUNCH_PROCESS,
            ActionKind.TERMINATE_PROCESS,
            ActionKind.WAIT_PROCESS_STARTED,
            ActionKind.WAIT_PROCESS_FINISHED,
            ActionKind.ACTIVATE_WINDOW,
            ActionKind.CLOSE_WINDOW,
            ActionKind.MINIMIZE_WINDOW,
            ActionKind.RESTORE_WINDOW,
        }:
            return None
        return BackendCandidate(
            backend_name=self.name,
            score=0.85,
            reason="supports process and window lifecycle through Win32 APIs",
        )

    def score_observation(
        self,
        query: ObservationQuery,
        context: object | None = None,
    ) -> BackendCandidate | None:
        if query.kind not in {
            ObservationKind.PROCESS_LIST,
            ObservationKind.PROCESS_FIND,
            ObservationKind.PROCESS_STATUS,
            ObservationKind.WINDOW_LIST,
            ObservationKind.WINDOW_ACTIVE,
            ObservationKind.WINDOW_FIND,
        }:
            return None
        return BackendCandidate(
            backend_name=self.name,
            score=0.85,
            reason="supports process and window observation through Win32 APIs",
        )

    def execute(self, action: Action) -> ActionResult:
        started_at = datetime.now(tz=UTC)
        started = time.perf_counter()
        if action.kind is ActionKind.OPEN_APPLICATION:
            return self._launch_application(action, started_at, started)
        if action.kind is ActionKind.LAUNCH_PROCESS:
            return self._launch_process(action, started_at, started, wait_for_window=False)
        if action.kind is ActionKind.TERMINATE_PROCESS:
            return self._terminate_process(action, started_at, started)
        if action.kind is ActionKind.WAIT_PROCESS_STARTED:
            return self._wait_process_started(action, started_at, started)
        if action.kind is ActionKind.WAIT_PROCESS_FINISHED:
            return self._wait_process_finished(action, started_at, started)
        if action.kind in {
            ActionKind.ACTIVATE_WINDOW,
            ActionKind.CLOSE_WINDOW,
            ActionKind.MINIMIZE_WINDOW,
            ActionKind.RESTORE_WINDOW,
        }:
            return self._window_action(action, started_at, started)
        return ActionResult(
            action_id=action.action_id,
            status=ActionStatus.FAILED,
            started_at=started_at,
            finished_at=datetime.now(tz=UTC),
            backend_used=self.name,
            backend_score=0.0,
            errors=(f"Unsupported action: {action.kind}",),
        )

    def observe(self, query: ObservationQuery) -> ObservationResult:
        try:
            observations = self._observe(query)
            return ObservationResult(
                query_id=query.query_id,
                backend_used=self.name,
                backend_score=0.85,
                backend_reason="observed process/window state through Win32 APIs",
                observations=tuple(observations),
            )
        except Exception as exc:  # noqa: BLE001 - adapter converts native failures to result.
            return ObservationResult(
                query_id=query.query_id,
                backend_used=self.name,
                backend_score=0.85,
                backend_reason="observed process/window state through Win32 APIs",
                errors=(str(exc),),
            )

    def _launch_application(self, action: Action, started_at: datetime, started: float) -> ActionResult:
        return self._launch_process(action, started_at, started, wait_for_window=True)

    def _launch_process(
        self,
        action: Action,
        started_at: datetime,
        started: float,
        wait_for_window: bool,
    ) -> ActionResult:
        target = str(action.inputs.get("target") or action.inputs.get("command"))
        cwd = action.inputs.get("cwd")
        telemetry: dict[str, object] = {"stages": ("launch_requested",)}
        try:
            process = self.process_driver.start(target, cwd=str(cwd) if cwd else None)
            telemetry["stages"] = (*telemetry["stages"], "process_created")
            process_observation = self._process_observation(
                pid=process.pid,
                name=self._process_name(target),
                path=self._process_path(target),
                started_at=started_at,
            )
            telemetry["stages"] = (*telemetry["stages"], "process_observed")
            observations: dict[str, object] = {"process": process_observation}
            reason = "process created and observed"
            if wait_for_window:
                window_observation = self._wait_for_window(process.pid, timeout_seconds=action.timeout_seconds)
                observations["window"] = window_observation
                telemetry["stages"] = (*telemetry["stages"], "application_window_detected")
                reason = "process created and application window detected"
            return ActionResult(
                action_id=action.action_id,
                status=ActionStatus.SUCCEEDED,
                started_at=started_at,
                finished_at=datetime.now(tz=UTC),
                duration_seconds=time.perf_counter() - started,
                backend_used=self.name,
                backend_score=0.85,
                backend_reason=reason,
                outputs={"pid": process.pid, "target": target},
                observations=observations,
                telemetry=telemetry,
            )
        except Exception as exc:  # noqa: BLE001
            return ActionResult(
                action_id=action.action_id,
                status=ActionStatus.FAILED,
                started_at=started_at,
                finished_at=datetime.now(tz=UTC),
                backend_used=self.name,
                backend_score=0.0,
                backend_reason="supports process lifecycle through Win32 APIs",
                errors=(str(exc),),
                telemetry=telemetry,
            )

    def _terminate_process(self, action: Action, started_at: datetime, started: float) -> ActionResult:
        pid = int(action.inputs["pid"])
        try:
            self.process_driver.terminate(pid, force=True)
            return ActionResult(
                action_id=action.action_id,
                status=ActionStatus.SUCCEEDED,
                started_at=started_at,
                finished_at=datetime.now(tz=UTC),
                duration_seconds=time.perf_counter() - started,
                backend_used=self.name,
                backend_score=0.85,
                backend_reason="terminated process through Win32 APIs",
                outputs={"pid": pid},
            )
        except Exception as exc:  # noqa: BLE001
            return ActionResult(
                action_id=action.action_id,
                status=ActionStatus.FAILED,
                started_at=started_at,
                finished_at=datetime.now(tz=UTC),
                duration_seconds=time.perf_counter() - started,
                backend_used=self.name,
                backend_score=0.85,
                backend_reason="supports process termination through Win32 APIs",
                errors=(str(exc),),
            )

    def _wait_process_started(self, action: Action, started_at: datetime, started: float) -> ActionResult:
        name = str(action.inputs["name"])
        process = self.process_driver.wait_started(name, timeout_seconds=action.timeout_seconds)
        return ActionResult(
            action_id=action.action_id,
            status=ActionStatus.SUCCEEDED,
            started_at=started_at,
            finished_at=datetime.now(tz=UTC),
            duration_seconds=time.perf_counter() - started,
            backend_used=self.name,
            backend_score=0.85,
            backend_reason="observed process start through Win32 APIs",
            outputs={"pid": process.pid, "name": name},
            observations={"process": self._process_observation(process.pid, process.name)},
        )

    def _wait_process_finished(self, action: Action, started_at: datetime, started: float) -> ActionResult:
        pid = int(action.inputs["pid"])
        self.process_driver.wait_exited(pid, timeout_seconds=action.timeout_seconds)
        return ActionResult(
            action_id=action.action_id,
            status=ActionStatus.SUCCEEDED,
            started_at=started_at,
            finished_at=datetime.now(tz=UTC),
            duration_seconds=time.perf_counter() - started,
            backend_used=self.name,
            backend_score=0.85,
            backend_reason="observed process finish through Win32 APIs",
            outputs={"pid": pid},
            observations={
                "process": ProcessObservation(
                    identity=ProcessIdentity(pid=pid, name=str(action.inputs.get("name") or "")),
                    status=ProcessStatus.EXITED,
                )
            },
        )

    def _window_action(self, action: Action, started_at: datetime, started: float) -> ActionResult:
        window = self._resolve_window(action.inputs.get("locator"))
        handle = int(window.metadata["platform_handle"])
        if action.kind is ActionKind.ACTIVATE_WINDOW:
            self.window_driver.activate_handle(handle)
        elif action.kind is ActionKind.CLOSE_WINDOW:
            self.window_driver.close(handle)
        elif action.kind is ActionKind.MINIMIZE_WINDOW:
            self.window_driver.minimize(handle)
        elif action.kind is ActionKind.RESTORE_WINDOW:
            self.window_driver.restore(handle)
        return ActionResult(
            action_id=action.action_id,
            status=ActionStatus.SUCCEEDED,
            started_at=started_at,
            finished_at=datetime.now(tz=UTC),
            duration_seconds=time.perf_counter() - started,
            backend_used=self.name,
            backend_score=0.85,
            backend_reason=f"performed {action.kind} through Win32 APIs",
            observations={"window": window},
        )

    def _observe(self, query: ObservationQuery) -> list[object]:
        if query.kind is ObservationKind.PROCESS_LIST:
            return [self._process_observation(item.pid, item.name) for item in self.process_driver.list()]
        if query.kind is ObservationKind.PROCESS_FIND:
            name = str(query.inputs.get("name") or "")
            return [self._process_observation(item.pid, item.name) for item in self.process_driver.find_by_name(name)]
        if query.kind is ObservationKind.PROCESS_STATUS:
            pid = int(query.inputs["pid"])
            return [
                self._process_observation(item.pid, item.name)
                for item in self.process_driver.list()
                if item.pid == pid
            ]
        if query.kind is ObservationKind.WINDOW_LIST:
            return [self._window_observation(item) for item in self.window_driver.list()]
        if query.kind is ObservationKind.WINDOW_ACTIVE:
            active = self.window_driver.active()
            return [] if active is None else [self._window_observation(active, active=True)]
        if query.kind is ObservationKind.WINDOW_FIND:
            locator = query.inputs.get("locator")
            return [item for item in self._observe(ObservationQuery(ObservationKind.WINDOW_LIST)) if self._matches_window(item, locator)]
        return []

    def _wait_for_window(self, pid: int, timeout_seconds: float) -> WindowObservation:
        deadline = time.monotonic() + min(timeout_seconds, self.window_wait_seconds)
        while time.monotonic() < deadline:
            for window in self.window_driver.list():
                if window.process_id != pid:
                    continue
                rect = window.rect
                bounds = None
                if rect is not None:
                    bounds = Bounds(
                        left=rect.left,
                        top=rect.top,
                        width=rect.width,
                        height=rect.height,
                    )
                return WindowObservation(
                    identity=WindowIdentity(
                        title=window.title,
                        process_id=window.process_id,
                        class_name=window.class_name,
                    ),
                    bounds=bounds,
                    visible=True,
                    active=self.window_driver.active() == window,
                    metadata={"platform_handle": window.handle},
                )
            time.sleep(self.poll_interval_seconds)
        raise TimeoutError(f"No application window detected for process {pid}")

    def _resolve_window(self, locator: object | None) -> WindowObservation:
        matches = [item for item in self._observe(ObservationQuery(ObservationKind.WINDOW_LIST)) if self._matches_window(item, locator)]
        if not matches:
            raise LookupError(f"Window not found: {locator}")
        return matches[0]

    def _matches_window(self, window: object, locator: object | None) -> bool:
        if not isinstance(window, WindowObservation):
            return False
        if locator is None:
            return True
        if not isinstance(locator, WindowLocator):
            return False
        if locator.title is not None and locator.title.lower() not in window.identity.title.lower():
            return False
        if locator.process_id is not None and locator.process_id != window.identity.process_id:
            return False
        if locator.class_name is not None and locator.class_name != window.identity.class_name:
            return False
        return True

    def _process_observation(
        self,
        pid: int,
        name: str,
        path: str | None = None,
        started_at: datetime | None = None,
    ) -> ProcessObservation:
        return ProcessObservation(
            identity=ProcessIdentity(pid=pid, name=name),
            path=path,
            started_at=started_at,
            status=ProcessStatus.RUNNING,
            metadata={"pid": pid},
        )

    def _window_observation(self, window: object, active: bool = False) -> WindowObservation:
        rect = getattr(window, "rect", None)
        bounds = None
        if rect is not None:
            bounds = Bounds(left=rect.left, top=rect.top, width=rect.width, height=rect.height)
        return WindowObservation(
            identity=WindowIdentity(
                title=getattr(window, "title"),
                process_id=getattr(window, "process_id"),
                class_name=getattr(window, "class_name"),
            ),
            bounds=bounds,
            visible=True,
            active=active,
            metadata={"platform_handle": getattr(window, "handle")},
        )

    def _process_name(self, target: str) -> str:
        return Path(target.split()[0]).name

    def _process_path(self, target: str) -> str | None:
        first = target.split()[0]
        return str(Path(first)) if "\\" in first or "/" in first else None
