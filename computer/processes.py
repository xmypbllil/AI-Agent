"""Process capability."""

from __future__ import annotations

from dataclasses import dataclass

from runtime.actions.models import ActionKind, LaunchProcessAction, ProcessAction
from runtime.actions.engine import ActionExecutor
from runtime.observations import ObservationKind, ProcessObservation, ProcessQuery
from runtime.observations.engine import ObservationExecutor


@dataclass(frozen=True, slots=True)
class Processes:
    action_executor: ActionExecutor
    observation_executor: ObservationExecutor

    def list(self) -> list[ProcessObservation]:
        result = self.observation_executor.observe(ProcessQuery(ObservationKind.PROCESS_LIST))
        return [item for item in result.observations if isinstance(item, ProcessObservation)]

    def find(self, name: str) -> list[ProcessObservation]:
        result = self.observation_executor.observe(ProcessQuery(ObservationKind.PROCESS_FIND, name=name))
        return [item for item in result.observations if isinstance(item, ProcessObservation)]

    def launch(self, command: str, cwd: str | None = None) -> ProcessObservation:
        result = self.action_executor.execute(LaunchProcessAction(command=command, cwd=cwd))
        process = result.observations.get("process")
        if not isinstance(process, ProcessObservation):
            raise RuntimeError("Process launch did not return a process observation")
        return process

    def start(self, command: str, cwd: str | None = None) -> ProcessObservation:
        return self.launch(command=command, cwd=cwd)

    def terminate(self, pid: int, force: bool = False) -> None:
        self.action_executor.execute(ProcessAction(ActionKind.TERMINATE_PROCESS, pid=pid))

    def find_by_name(self, name: str) -> list[ProcessObservation]:
        return self.find(name)

    def wait_started(self, name: str, timeout_seconds: float = 30.0) -> ProcessObservation:
        result = self.action_executor.execute(
            ProcessAction(ActionKind.WAIT_PROCESS_STARTED, name=name, timeout_seconds=timeout_seconds)
        )
        process = result.observations.get("process")
        if not isinstance(process, ProcessObservation):
            raise RuntimeError("Process wait did not return a process observation")
        return process

    def wait_finished(self, pid: int, timeout_seconds: float = 30.0) -> None:
        self.action_executor.execute(ProcessAction(ActionKind.WAIT_PROCESS_FINISHED, pid=pid, timeout_seconds=timeout_seconds))

    def wait_exited(self, pid: int, timeout_seconds: float = 30.0) -> None:
        self.wait_finished(pid=pid, timeout_seconds=timeout_seconds)

    def status(self, pid: int) -> ProcessObservation | None:
        result = self.observation_executor.observe(ProcessQuery(ObservationKind.PROCESS_STATUS, pid=pid))
        observations = [item for item in result.observations if isinstance(item, ProcessObservation)]
        return observations[0] if observations else None
