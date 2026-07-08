from runtime.actions import EditFileAction, ReadFileAction, RunCommandAction, WriteFileAction
from runtime.actions.engine import ActionExecutor
from runtime.actions.models import ActionStatus
from runtime.backends import BackendManager, DevelopmentBackend


def test_development_backend_reads_edits_and_runs_command(tmp_path) -> None:
    executor = ActionExecutor(
        backend_manager=BackendManager(
            action_backends=[DevelopmentBackend(root=tmp_path)],
        )
    )

    write = executor.execute(WriteFileAction("pkg/example.py", "VALUE = 'old'\n"))
    read = executor.execute(ReadFileAction("pkg/example.py"))
    edit = executor.execute(EditFileAction("pkg/example.py", "'old'", "'new'"))
    command = executor.execute(RunCommandAction("python -m compileall pkg", cwd="."))

    assert write.status is ActionStatus.SUCCEEDED
    assert read.outputs["content"] == "VALUE = 'old'\n"
    assert edit.outputs["replacements"] == 1
    assert command.outputs["exit_code"] == 0
