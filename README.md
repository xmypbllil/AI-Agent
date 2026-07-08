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

## Local Agent CLI

The first runnable agent loop is available as a provider-neutral CLI:

```powershell
computer-agent "python -m compileall agent computer runtime"
```

For development without installing the package, run the module directly:

```powershell
python -m agent.cli "python -m compileall agent computer runtime"
```

The CLI flow is intentionally small:

1. receives a goal;
2. asks an `LLMAdapter` for an `ActionGraph`;
3. executes the graph through the existing `ActionExecutor` and `BackendManager`;
4. writes a JSON trace to `evaluations/last-agent-cli-trace.json`;
5. returns `verified` or `failed`.

The adapter interface is provider-neutral:

```python
class LLMAdapter(Protocol):
    def generate_plan(self, goal: str, context: Mapping[str, Any]) -> ActionGraph: ...
    def decide_next_action(self, observations: Mapping[str, Any]) -> ActionGraph | None: ...
```

The bundled `LocalMvpAdapter` is deterministic and exists only to make the local CLI executable
without OpenAI, Anthropic, Google, or any other model SDK.

To use a real provider-backed adapter, set environment variables before running the same CLI:

```powershell
$env:LLM_PROVIDER = "openai"
$env:API_KEY = "..."
computer-agent "проверь проект и запусти validation"
```

Optional settings:

```powershell
$env:LLM_MODEL = "gpt-4.1-mini"
$env:LLM_BASE_URL = "https://api.openai.com/v1/chat/completions"
```

Provider adapters live in `agent`, not in `runtime`. The Runtime remains model-agnostic; it only
receives typed `ActionGraph` objects and executes them through existing backends.
