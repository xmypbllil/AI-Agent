"""Python runtime executor."""

from __future__ import annotations

import contextlib
import io
import logging
import traceback
from dataclasses import dataclass
from dataclasses import field
from typing import Any

from runtime.container import ServiceContainer
from runtime.history import ExecutionHistory, InMemoryExecutionHistory
from runtime.models import ExecutionRequest, ExecutionResult, ExecutionStatus
from runtime.sandbox import LocalSandbox, Sandbox

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class PythonRuntime:
    """Executes model-authored Python and returns structured feedback."""

    container: ServiceContainer
    sandbox: Sandbox = field(default_factory=LocalSandbox)
    history: ExecutionHistory = field(default_factory=InMemoryExecutionHistory)

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        stdout = io.StringIO()
        stderr = io.StringIO()
        globals_dict = self.sandbox.globals_for(self.container.namespace())
        locals_dict: dict[str, Any] = {}

        LOGGER.info("Executing request %s", request.request_id)
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exec(request.code, globals_dict, locals_dict)
            result = ExecutionResult(
                request_id=request.request_id,
                status=ExecutionStatus.SUCCEEDED,
                stdout=stdout.getvalue(),
                stderr=stderr.getvalue(),
                value=locals_dict.get("_"),
                metadata=request.metadata,
            )
        except Exception as exc:  # noqa: BLE001 - runtime must capture arbitrary model errors.
            result = ExecutionResult(
                request_id=request.request_id,
                status=ExecutionStatus.FAILED,
                stdout=stdout.getvalue(),
                stderr=stderr.getvalue(),
                error_type=type(exc).__name__,
                error_message=str(exc),
                traceback=traceback.format_exc(),
                metadata=request.metadata,
            )
            LOGGER.warning("Execution failed for %s: %s", request.request_id, exc)

        self.history.append(result)
        return result
