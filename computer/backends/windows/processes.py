"""Windows process driver."""

from __future__ import annotations

import csv
import shlex
import subprocess
import time
from dataclasses import dataclass
from io import StringIO

from computer.errors import DesktopOperationError, ElementNotFoundError, TimeoutExpiredError
from computer.models import ProcessInfo


@dataclass(frozen=True, slots=True)
class WindowsProcessDriver:
    poll_interval_seconds: float = 0.25

    def list(self) -> list[ProcessInfo]:
        completed = subprocess.run(
            ["tasklist", "/fo", "csv", "/v", "/nh"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if completed.returncode != 0:
            raise DesktopOperationError(completed.stderr.strip() or "tasklist failed")
        rows = csv.reader(StringIO(completed.stdout))
        processes: list[ProcessInfo] = []
        for row in rows:
            if len(row) < 9 or not row[1].isdigit():
                continue
            window_title = None if row[8] == "N/A" else row[8]
            processes.append(ProcessInfo(pid=int(row[1]), name=row[0], window_title=window_title))
        return processes

    def details(self) -> list[dict[str, str]]:
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_Process | "
                "Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine | "
                "ConvertTo-Csv -NoTypeInformation",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if completed.returncode != 0:
            return []
        return list(csv.DictReader(StringIO(completed.stdout)))

    def start(self, command: str, cwd: str | None = None) -> ProcessInfo:
        args = shlex.split(command, posix=False)
        process = subprocess.Popen(args, cwd=cwd, shell=False)
        return ProcessInfo(pid=int(process.pid), name=command)

    def terminate(self, pid: int, force: bool = False) -> None:
        args = ["taskkill", "/pid", str(pid)]
        if force:
            args.append("/f")
        completed = subprocess.run(args, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise DesktopOperationError(completed.stderr.strip() or f"Failed to terminate {pid}")

    def find_by_name(self, name: str) -> list[ProcessInfo]:
        expected = name.lower()
        return [item for item in self.list() if item.name.lower() == expected]

    def wait_started(self, name: str, timeout_seconds: float = 30.0) -> ProcessInfo:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            matches = self.find_by_name(name)
            if matches:
                return matches[0]
            time.sleep(self.poll_interval_seconds)
        raise TimeoutExpiredError(f"Process did not start within {timeout_seconds}s: {name}")

    def wait_exited(self, pid: int, timeout_seconds: float = 30.0) -> None:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if not self._exists(pid):
                return
            time.sleep(self.poll_interval_seconds)
        raise TimeoutExpiredError(f"Process did not exit within {timeout_seconds}s: {pid}")

    def _exists(self, pid: int) -> bool:
        completed = subprocess.run(
            ["tasklist", "/fi", f"PID eq {pid}", "/fo", "csv", "/nh"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        return str(pid) in completed.stdout

    def require(self, name: str) -> ProcessInfo:
        matches = self.find_by_name(name)
        if not matches:
            raise ElementNotFoundError(f"Process not found: {name}")
        return matches[0]
