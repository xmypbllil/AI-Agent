# Architecture

## Goal

Desktop LLM Runtime provides a stable Python API that an LLM can use to control a computer. It is
not a single agent and not a fixed workflow engine. It is a runtime surface with execution,
observation, memory, and repair loops around arbitrary model-authored Python.

## Layering

1. `agent` or any external SDK caller decides what task should run next.
2. `runtime` turns tasks into plans and action graphs.
3. `ActionExecutor` executes independent action objects.
4. `BackendManager` scores available backends and selects the best executor.
5. `computer` exposes a stable facade over actions and observations.
6. `memory` records actions, errors, context, and cache entries.

Dependencies point inward through protocols:

```text
agent or SDK caller -> runtime -> action graph -> action executor
                                    -> backend manager -> backend
runtime -> computer facade
runtime -> memory
```

No layer owns a global singleton. Composition happens through `runtime.container.ServiceContainer`.

## Action-Centric Runtime

The runtime is centered on actions, not UI.

```text
Application
-> Task
-> Plan
-> ActionGraph
-> ActionExecutor
-> BackendManager
-> Backend
-> Operating System
```

Actions mutate the world: open, click, type, close, compile, write. Observations inspect the world:
find, screenshot, get text, inspect state. The two paths are separate.

Every action has:

- id;
- inputs and outputs;
- preconditions and postconditions;
- rollback metadata when possible;
- retry policy;
- timeout;
- telemetry;
- screenshot before and after fields.

The first vertical slice is `OpenApplicationAction -> ActionExecutor -> BackendManager ->
MockBackend -> ActionResult`. Each new architectural layer must include an interface, a minimal
implementation, and unit tests.

## Backend Selection

Backends declare capabilities and score actions. The manager chooses the best candidate, not merely
the first available backend. The action scoring contract is:

```python
backend.score(action, context) -> BackendCandidate | None
```

`BackendCandidate` includes the backend name, score, and reason so runtime telemetry can explain
choices such as "selected UIABackend with score 0.95 because it supports process launch and window
verification." The intended fallback order is:

1. UI Automation.
2. Win32 API.
3. Accessibility API.
4. OCR.
5. Vision.

Vision is observation-only. It reports what it sees, where it is, and confidence. It never performs
clicks, typing, or other state-changing actions.

## World Model

`WorldModel` is a cache, not the source of truth. It stores snapshots such as active windows,
processes, UI trees, screen info, clipboard state, current directory, recent actions, and recent
errors. A snapshot can become stale and must be refreshable from observation backends.

## Audit Rules

- Core SDK packages must not import Win32, UI Automation, OCR, Vision, or backend implementations.
- Actions remain declarative and contain intent, inputs, metadata, conditions, retry, timeout, and
  telemetry contracts only.
- `ActionBackend` changes state. `ObservationBackend` reads state. These interfaces must not be
  merged.
- Every new layer needs an interface, a minimal implementation, and a unit test.
- Public facade compatibility is preserved while internals move through actions and backend
  selection.

## Python Execution Runtime

The runtime accepts an `ExecutionRequest` and returns an `ExecutionResult`.

Responsibilities:

- prepare isolated globals for each execution;
- inject only approved services;
- capture stdout/stderr;
- capture exceptions and traceback;
- persist history through a repository protocol;
- provide structured feedback for self-correction.

The first sandbox is process-local and namespace-restricted. The interface deliberately supports a
future out-of-process sandbox without changing callers.

## Computer API

`computer.Computer` is a facade composed from small capability modules. Each capability can also be
used directly.

Modules:

- `apps`: launch/open applications.
- `windows`: enumerate and activate windows.
- `mouse`: pointer movement and clicks.
- `keyboard`: key presses and text entry.
- `files`: filesystem reads/writes under policy.
- `clipboard`: clipboard access.
- `terminal`: command execution.
- `screen`: screenshots and geometry.
- `vision` / `ocr`: perception adapters.
- `processes`: process listing.
- `browser`: URL opening.
- `network`, `audio`, `system`, `packages`, `git`, `python`, `services`, `registry`,
  `environment`: platform services.

The facade has no business logic. It wires capabilities and preserves discoverability for LLMs.

## Agent Loop

The agent package defines replaceable components:

- `Planner`: turns user intent and context into an execution plan.
- `Executor`: runs a step through the runtime.
- `Critic`: evaluates results and decides whether to retry.
- `Memory`: retrieves and stores relevant context.
- `Reflection`: turns failures into improved instructions.
- `AgentLoop`: coordinates the cycle.

The default implementation is intentionally conservative and protocol-oriented.

## Memory

SQLite is the default durable store. It records:

- execution history;
- action events;
- error events;
- cache entries;
- context entries.

Repositories expose typed methods rather than raw SQL to the rest of the system.

## Vision

Vision is optional and adapter-based. Core contracts support:

- OCR;
- text search;
- image matching;
- button/control visual detection.

OpenCV/Pillow/Tesseract-style adapters can be added without leaking dependency choices into
`computer`.

## UI Automation

The `ui` package models Microsoft UI Automation:

- element queries by name, automation id, and control type;
- actions through Invoke, ExpandCollapse, Selection, and Value patterns;
- typed query results and errors.

The initial implementation provides contracts and a null adapter. Native Windows adapters belong
behind these contracts.

## Design Rules

- No god objects.
- No long switches for capability dispatch.
- Dependency injection at boundaries.
- Dataclasses for structured data.
- Enums for controlled vocabularies.
- Protocols for replaceable adapters.
- Absolute imports.
- Full typing.
- Explicit logging.
