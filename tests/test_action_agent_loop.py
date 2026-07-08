from agent import create_self_development_loop
from runtime.actions.engine import ActionExecutor
from runtime.backends import BackendManager, DevelopmentBackend


def test_self_development_loop_repairs_compile_failure(tmp_path) -> None:
    executor = ActionExecutor(
        backend_manager=BackendManager(action_backends=[DevelopmentBackend(root=tmp_path)])
    )
    loop = create_self_development_loop(executor=executor, path="module.py")

    session = loop.run("Read project file, modify code, run compileall, verify success")

    assert session.final_result == "verified"
    assert any("command exited" in item for item in session.errors)
    assert (tmp_path / "module.py").read_text(encoding="utf-8") == "VALUE = 'fixed'\n"
