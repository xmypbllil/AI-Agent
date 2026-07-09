# Architecture Review

## 1. Python sandbox is not a real isolation boundary

1. File: `runtime/executor.py`, `runtime/sandbox.py`
2. Reason: `PythonRuntime.execute()` runs model-authored code with in-process `exec()`, and `LocalSandbox` only limits the initial builtin namespace. There is no process isolation, CPU/memory limit, filesystem policy, cancellation, import policy, or syscall boundary. For a project whose core goal is safe desktop automation, this makes the runtime boundary mostly advisory.
3. Proposed fix: Introduce an out-of-process sandbox implementation behind the existing `Sandbox` protocol. Run submitted code in a worker process with a strict timeout, explicit IPC request/response schema, limited injected services, resource limits, and a filesystem policy. Keep `LocalSandbox` only as a test/dev adapter.

## 2. ActionGraph models a graph but executes only a linear list

1. File: `runtime/actions/graph.py`, `runtime/actions/engine.py`
2. Reason: `ActionGraph` has `edges`, but `ordered()` ignores them and returns actions in insertion order. Preconditions, postconditions, rollback, and graph dependencies are therefore declared in the model but not enforced by the executor. This creates a misleading contract for planners and backend authors.
3. Proposed fix: Implement graph validation and topological ordering. Reject missing nodes, cycles, duplicate action ids, and unsatisfied dependencies. Move graph-level execution into an executor that evaluates preconditions, supports dependency-aware skipping, and records why each action ran or did not run.

## 3. Action contracts are mostly untyped dictionaries

1. File: `runtime/actions/models.py`
2. Reason: The base `Action` stores inputs and outputs as `Mapping[str, Any]`, while concrete action classes manually set dataclass fields through repeated `object.__setattr__` calls. This weakens static guarantees, spreads input validation into backends, and makes it easy for LLM adapters to produce malformed actions that fail late.
3. Proposed fix: Replace generic `inputs` payloads with typed action dataclasses per action kind, or use typed payload models attached to each action. Add a central action registry that validates construction, serializes/deserializes plans, and exposes schemas to LLM adapters and tests.

## 4. Backend selection has no policy layer or fallback execution

1. File: `runtime/backends/manager.py`, `runtime/actions/engine.py`
2. Reason: `BackendManager` selects the highest-scoring backend and `ActionExecutor` executes only that backend. If the selected backend fails, lower-ranked candidates are never tried. Backend roles and capability metadata exist, but they are not used as a policy beyond sorting by score.
3. Proposed fix: Add a backend execution policy that can try candidates in order, classify failures as retryable/non-retryable, and record candidate attempts in telemetry. Make role order, platform availability, and capability requirements part of selection rather than relying only on backend-provided scores.

## 5. Public computer facade bypasses the action runtime

1. File: `computer/__init__.py`, `computer/apps.py`, `computer/terminal.py`
2. Reason: Some public capabilities route through `ActionExecutor`, while others call platform APIs or `subprocess` directly. For example, `Apps.open()` can fall back to `subprocess.Popen(..., shell=True)`, and `Terminal.run()` executes commands outside the action/backend/history path. This fragments policy, telemetry, replay, and safety.
3. Proposed fix: Route all state-changing public methods through typed actions and backend selection. Keep direct driver calls only inside backend implementations. If direct convenience APIs remain, make them thin wrappers around action construction and execution so history, policy, and permissions are consistent.

## 6. Composition is hard-coded in the facade instead of an application runtime

1. File: `computer/__init__.py`
2. Reason: `create_default_computer()` detects the platform, imports Windows backends, constructs backend lists, creates executors, and creates the public facade in one function. This mixes platform discovery, dependency injection, runtime policy, and user-facing API construction, making alternate runtimes difficult to test or extend.
3. Proposed fix: Move composition into a dedicated runtime bootstrap module with explicit configuration objects. Split platform discovery, backend registration, service container construction, and facade creation. Let tests and applications provide a backend registry instead of relying on `create_default_computer()` defaults.

## 7. Development backend is both a backend and an unrestricted local command runner

1. File: `runtime/backends/development.py`
2. Reason: `DevelopmentBackend` handles file mutation and shell command execution with `shell=True`. Its `role` is `MOCK`, although it performs real filesystem and process side effects. Path confinement exists for file paths and cwd, but command behavior itself is not modeled as a permissioned capability.
3. Proposed fix: Split file actions and command actions into separate backends with separate roles and policies. Replace shell-string execution with argv-based command execution where possible, add an allow/deny policy for shell usage, and expose command risk classification in `ActionResult.telemetry`.

## 8. Agent planning mixes provider interface, regex parser, and task-specific heuristics

1. File: `agent/llm.py`, `agent/replanner.py`
2. Reason: `LocalMvpAdapter` contains a growing set of regex-based parsers for files, folders, UI text, application control, validation, reporting, and command fallback. Replanning separately duplicates goal parsing and string normalization. This makes the agent layer brittle and difficult to evolve into provider-neutral planning.
3. Proposed fix: Introduce a typed goal interpretation layer that turns user text into a small intermediate intent model. Let both local and provider-backed planners consume that model and emit action schemas. Keep MVP regex rules in one parser module with tests, not inside the LLM adapter contract.

## 9. Goal verification is coupled to ad hoc observation dictionaries

1. File: `agent/mvp.py`
2. Reason: `AgentRunner` and `GoalEvaluator` pass mutable `dict[str, Any]` observations with keys such as `expected_files`, `verified_files`, `typed`, `last_pid`, and `command_results`. Verification depends on string keys and path matching rather than typed observations or reusable contracts.
3. Proposed fix: Add typed goal-state and verification models. Make each action result produce typed facts, then let verifiers consume those facts through a stable interface. Separate trace writing, observation aggregation, and goal evaluation into distinct collaborators.

## 10. World model is a passive cache without refresh or invalidation semantics

1. File: `runtime/world/model.py`, `runtime/observations/engine.py`
2. Reason: `WorldModel` stores snapshots and has a `stale` flag, but observation executors do not use it to decide when to refresh, expire, merge, or invalidate state. Updates are keyed by partial identity such as window title and process id, which can collide or become stale after process/window lifecycle changes.
3. Proposed fix: Define world-model ownership rules: typed entity ids, timestamps, TTLs, invalidation on mutating actions, and explicit refresh queries. Make observation executors read from and refresh the cache through a service API instead of directly appending loosely matched observations.

## Additional persistence concern

`memory/sqlite.py` is currently disconnected from the main runtime and agent flows. Once the action/runtime architecture is tightened, persistence should be integrated through repository protocols for execution history, action events, errors, and context rather than remaining a separate utility store.
