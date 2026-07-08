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
    ApplicationIdentity,
    ApplicationRuntimeIdentity,
    Bounds,
    ProcessIdentity,
    ProcessObservation,
    ProcessStatus,
    ProcessTreeObservation,
    WindowIdentity,
    WindowOwnershipObservation,
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
                application, process_tree, window_observation, ownership = self._wait_for_application_window(
                    root_pid=process.pid,
                    target=target,
                    started_at=started_at,
                    timeout_seconds=action.timeout_seconds,
                )
                observations["application"] = application
                observations["process_tree"] = process_tree
                observations["window"] = window_observation
                observations["ownership"] = ownership
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

    def _wait_for_application_window(
        self,
        root_pid: int,
        target: str,
        started_at: datetime,
        timeout_seconds: float,
    ) -> tuple[ApplicationRuntimeIdentity, ProcessTreeObservation, WindowObservation, WindowOwnershipObservation]:
        deadline = time.monotonic() + min(timeout_seconds, self.window_wait_seconds)
        last_tree = self._process_tree(root_pid)
        while time.monotonic() < deadline:
            last_tree = self._process_tree(root_pid)
            process_ids = {item.identity.pid for item in last_tree.processes}
            windows = [self._window_observation(item) for item in self.window_driver.list()]
            match, reasons = self._correlate_window(windows, process_ids, target)
            if match is not None:
                runtime_id = f"app-runtime:{root_pid}:{self._process_name(target)}"
                ownership = WindowOwnershipObservation(
                    window=match.identity,
                    application_runtime_id=runtime_id,
                    process_id=match.identity.process_id,
                    confidence=0.85,
                    reasons=tuple(reasons),
                )
                identity = WindowIdentity(
                    title=match.identity.title,
                    process_id=match.identity.process_id,
                    class_name=match.identity.class_name,
                    runtime_window_id=match.identity.runtime_window_id,
                    application_runtime_id=runtime_id,
                    app_user_model_id=match.identity.app_user_model_id,
                    package_family_name=match.identity.package_family_name,
                )
                match = WindowObservation(
                    identity=identity,
                    bounds=match.bounds,
                    visible=match.visible,
                    active=match.active,
                    observed_at=match.observed_at,
                    metadata=match.metadata,
                    owner=ownership,
                )
                application = ApplicationRuntimeIdentity(
                    runtime_id=runtime_id,
                    application=ApplicationIdentity(
                        name=self._process_name(target),
                        executable=self._process_name(target),
                        path=self._process_path(target),
                    ),
                    root_process_id=root_pid,
                    process_ids=tuple(sorted(process_ids)),
                    window_ids=(match.identity,),
                    started_at=started_at,
                    correlation_keys=tuple(reasons),
                )
                return application, last_tree, match, ownership
            time.sleep(self.poll_interval_seconds)
        raise TimeoutError(f"No application window detected for process {root_pid}")

    def _process_tree(self, root_pid: int) -> ProcessTreeObservation:
        details = self.process_driver.details()
        by_pid = {
            int(item["ProcessId"]): item
            for item in details
            if item.get("ProcessId", "").isdigit()
        }
        children_by_parent: dict[int, list[int]] = {}
        for pid, item in by_pid.items():
            parent = item.get("ParentProcessId", "")
            if parent.isdigit():
                children_by_parent.setdefault(int(parent), []).append(pid)

        discovered = {root_pid}
        queue = [root_pid]
        while queue:
            current = queue.pop(0)
            for child in children_by_parent.get(current, []):
                if child not in discovered:
                    discovered.add(child)
                    queue.append(child)

        observations: list[ProcessObservation] = []
        parent_by_pid: dict[int, int] = {}
        for pid in sorted(discovered):
            item = by_pid.get(pid, {})
            name = item.get("Name") or str(pid)
            parent_text = item.get("ParentProcessId", "")
            parent_pid = int(parent_text) if parent_text.isdigit() else None
            if parent_pid is not None:
                parent_by_pid[pid] = parent_pid
            observations.append(
                ProcessObservation(
                    identity=ProcessIdentity(pid=pid, name=name, parent_pid=parent_pid),
                    path=item.get("ExecutablePath") or None,
                    status=ProcessStatus.RUNNING,
                    command_line=item.get("CommandLine") or None,
                    parent_pid=parent_pid,
                    metadata={"pid": pid},
                )
            )
        root = observations[0].identity if observations else ProcessIdentity(pid=root_pid, name=str(root_pid))
        return ProcessTreeObservation(
            root=root,
            processes=tuple(observations),
            parent_by_pid=parent_by_pid,
        )

    def _correlate_window(
        self,
        windows: list[WindowObservation],
        process_ids: set[int],
        target: str,
    ) -> tuple[WindowObservation | None, list[str]]:
        target_name = self._process_name(target).lower()
        for window in windows:
            if window.identity.process_id in process_ids:
                return window, [f"window_process_id={window.identity.process_id}", "process_tree_match"]
        for window in windows:
            process_id = window.identity.process_id
            if process_id is None:
                continue
            detail = self._process_detail(process_id)
            name = (detail.get("Name") or "").lower()
            path = (detail.get("ExecutablePath") or "").lower()
            command_line = (detail.get("CommandLine") or "").lower()
            if target_name and (target_name == name or target_name in path or target_name in command_line):
                return window, [
                    f"window_process_id={process_id}",
                    f"process_name_or_path_matches={target_name}",
                ]
        return None, []

    def _process_detail(self, pid: int) -> dict[str, str]:
        for item in self.process_driver.details():
            if item.get("ProcessId") == str(pid):
                return item
        return {}

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
                runtime_window_id=f"win32:{getattr(window, 'handle')}",
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
