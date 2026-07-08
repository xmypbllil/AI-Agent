# Version 0.1

Version 0.1 proves the first end-to-end desktop runtime path:

```text
Task
-> Plan / ActionGraph
-> ActionExecutor
-> BackendManager
-> Windows backend
-> Observation
-> WorldModel / verification
```

The accepted demo scenario is:

```python
computer.run("Open Notepad and write Hello Runtime")
```

## Implemented

- Action-centric runtime with `Action`, `ActionGraph`, `ActionExecutor`, `ActionResult`, retry
  metadata, backend telemetry, observations, and screenshots fields.
- Backend scoring through `BackendManager`.
- World model cache with stale/update semantics.
- Process and window runtime:
  - process list/find/launch/terminate/wait/status;
  - window list/active/find/activate/close/minimize/restore/bounds/size;
  - `WindowLocator`.
- UI runtime contracts:
  - `Locator`;
  - `UIElementIdentity`;
  - `UIElementObservation`;
  - `UIElementBounds`;
  - `UIElementState`;
  - `UIControlType`;
  - `UITreeSnapshot`.
- UI Automation observation:
  - `computer.ui.find(locator)`;
  - `find_all`;
  - `exists`;
  - `text`;
  - `bounds`;
  - `children`.
- First UI actions:
  - `ClickAction`;
  - `TypeTextAction`;
  - UIA `InvokePattern` / `ValuePattern` adapter.
- First E2E user-facing runner:
  - `computer.run("Open Notepad and write Hello Runtime")`.

## Available Backends

- `MockBackend`
  - Used by unit tests and non-Windows-safe smoke scenarios.
- `Win32Backend`
  - Process lifecycle.
  - Window lifecycle.
  - Process/window observations.
- `UIAObservationBackend`
  - Microsoft UI Automation tree observation.
  - Locator-based element lookup.
- `UIAActionBackend`
  - Minimal UI actions through Microsoft UI Automation patterns.

## Architectural Boundaries

- `computer` is a facade.
- Runtime core does not import Win32, UI Automation, OCR, Vision, or provider-specific LLM APIs.
- UIA and Win32 are adapters under `computer.backends.windows`.
- Vision remains observation-only and is not used as a primary interaction mechanism.
- `WorldModel` is a cache, not the source of truth.

## Limitations

- Windows 11 is the only implemented OS backend.
- UIA action support is intentionally minimal.
- The runner supports only the first accepted demo scenario.
- OCR and Vision backends are contracts/placeholders, not part of the 0.1 E2E path.
- Integration tests are opt-in because they interact with the real desktop.
- Local `pytest` requires installing development dependencies with `.[dev]`.

## Demo Trace Shape

The demo prints:

- instruction;
- verification status;
- action id;
- action status;
- selected backend;
- backend score;
- backend reason;
- outputs;
- errors.
