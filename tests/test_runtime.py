from computer import create_default_computer
from runtime import ExecutionRequest, PythonRuntime, ServiceContainer


def test_runtime_executes_python_and_captures_stdout() -> None:
    container = ServiceContainer()
    runtime = PythonRuntime(container=container)

    result = runtime.execute(ExecutionRequest(code='print("hello")'))

    assert result.ok
    assert result.stdout == "hello\n"


def test_runtime_captures_traceback() -> None:
    runtime = PythonRuntime(container=ServiceContainer())

    result = runtime.execute(ExecutionRequest(code='raise Exception("boom")'))

    assert not result.ok
    assert result.error_type == "Exception"
    assert result.traceback is not None


def test_runtime_injects_computer_api(tmp_path) -> None:
    container = ServiceContainer()
    computer = create_default_computer(root=tmp_path)
    container.register_instance("computer", computer)
    runtime = PythonRuntime(container=container)

    result = runtime.execute(
        ExecutionRequest(code='computer.files.write("note.txt", "ok")\nprint(computer.files.read("note.txt"))')
    )

    assert result.ok
    assert result.stdout == "ok\n"
