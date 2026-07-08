# Desktop LLM Runtime

Desktop LLM Runtime is a modular Python runtime for letting an LLM execute typed Python code
against a Windows desktop.

The project is designed as a platform, not a scenario-specific agent. The LLM writes Python such as:

```python
computer.apps.open("Visual Studio Code")
computer.files.read("main.py")
computer.terminal.run("git status")
computer.screen.capture()
```

The runtime executes the code, records the result, captures failures, and gives the calling agent
enough structured context to repair and retry.

## Architecture

The codebase is split into independent packages:

- `runtime`: execution sandbox, dependency injection, logging, execution history, error capture.
- `computer`: public desktop API for apps, files, terminal, screen, processes, browser, and system.
- `agent`: planner, executor, critic, loop, reflection contracts.
- `memory`: SQLite-backed action/error/cache/context storage.
- `vision`: OCR/image/text/button search ports and adapters.
- `ui`: Microsoft UI Automation ports and typed patterns.

See [docs/architecture.md](docs/architecture.md) for the full design.

## Status

Version 0.1 includes the first real end-to-end desktop runtime path:

```python
computer.run("Open Notepad and write Hello Runtime")
```

That path opens Notepad with the Win32 backend, locates the edit control through Microsoft UI
Automation, writes text through UIA `ValuePattern`, reads the value back through observation, and
returns a verified runtime result.

See [docs/release-0.1.md](docs/release-0.1.md) and
[examples/notepad_hello_runtime.py](examples/notepad_hello_runtime.py).

Validation scenarios are documented in [docs/validation.md](docs/validation.md).
