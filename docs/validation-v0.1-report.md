# Validation v0.1 Report

- Total: 7
- Passed: 4
- Failed: 3

## Scenario Results

### Notepad: open application, write text, read text back, verify

- Status: passed
- Duration: 93.22s
- ActionGraph: OpenApplicationAction, TypeTextAction

Actions:
- `succeeded` via `win32` score `0.85`
  - reason: process created and application window detected
  - duration: 2.16s
  - errors: ()
- `succeeded` via `uia-action` score `0.95`
  - reason: executed through Microsoft UI Automation patterns
  - duration: 90.53s
  - errors: ()

Observations:
- UIA ValuePattern text verification completed.

### Calculator: open application, calculate 1 + 2, observe result

- Status: failed
- Duration: 17.43s
- ActionGraph: OpenApplicationAction, ClickAction, ClickAction, ClickAction, ClickAction

Actions:
- `failed` via `win32` score `0.85`
  - reason: supports process lifecycle through Win32 APIs
  - duration: 17.43s
  - errors: ('No application window detected for process 39524',)

Errors:
- Calculator launch did not produce an observed application window.

Notes:
- Windows Calculator may spawn through an app container with a different window process.

### File workflow: create text, save file, verify existence

- Status: passed
- Duration: 0.00s
- ActionGraph: (none)

Actions:
- No ActionGraph actions recorded.

Observations:
- Created file in temporary directory: runtime-validation.txt

Notes:
- This scenario validates the existing file facade.
- File actions are not yet represented as ActionGraph actions in version 0.1.

### Self-development: open project, read file, modify file, run validation command, verify

- Status: passed
- Duration: 0.19s
- ActionGraph: WriteFileAction, ReadFileAction, EditFileAction, SearchFilesAction, RunCommandAction, ReadFileAction

Actions:
- `succeeded` via `development` score `0.9`
  - reason: executed file/terminal action through development backend
  - duration: 0.00s
  - errors: ()
- `succeeded` via `development` score `0.9`
  - reason: executed file/terminal action through development backend
  - duration: 0.00s
  - errors: ()
- `succeeded` via `development` score `0.9`
  - reason: executed file/terminal action through development backend
  - duration: 0.00s
  - errors: ()
- `succeeded` via `development` score `0.9`
  - reason: executed file/terminal action through development backend
  - duration: 0.00s
  - errors: ()
- `succeeded` via `development` score `0.9`
  - reason: executed file/terminal action through development backend
  - duration: 0.18s
  - errors: ()
- `succeeded` via `development` score `0.9`
  - reason: executed file/terminal action through development backend
  - duration: 0.00s
  - errors: ()

Observations:
- Final content: "VALUE = 'Hello Runtime'\n"
- Validation exit code: 0

### Paint: open application, observe main window, inspect UI availability

- Status: passed
- Duration: 2.59s
- ActionGraph: OpenApplicationAction

Actions:
- `succeeded` via `win32` score `0.85`
  - reason: process created and application window detected
  - duration: 1.94s
  - errors: ()

Observations:
- Window count: 1
- First UI element: window

### Terminal: open cmd, execute simple command, observe output

- Status: failed
- Duration: 26.18s
- ActionGraph: OpenApplicationAction

Actions:
- `succeeded` via `win32` score `0.85`
  - reason: process created and application window detected
  - duration: 15.25s
  - errors: ()

Observations:
- Window count: 0
- Observed text: None

Notes:
- The command is passed at launch time; interactive keyboard input is not evaluated in v0.1.
- Validation output showed command quoting can be mangled before cmd receives the intended input.

### VS Code: open if installed, find window, collect UI observation limitations

- Status: failed
- Duration: 0.00s
- ActionGraph: OpenApplicationAction

Actions:
- `failed` via `win32` score `0.85`
  - reason: supports process lifecycle through Win32 APIs
  - duration: 0.00s
  - errors: ('[WinError 2] Не удается найти указанный файл',)

Errors:
- VS Code did not launch into an observed window from command 'code'.

Notes:
- VS Code may not be installed or the 'code' shim may return before the UI process/window is observed.

## Stable Capabilities

- Notepad E2E path exercises Win32 launch, UIA observation, UIA ValuePattern, and verification.
- File facade can create/read/verify files within a configured root.
- Self-development workflow can write, read, edit, search, and run a validation command through ActionGraph.
- Classic Win32-style application launch/window observation works for at least one application.

## Failed Cases

- Calculator may fail because modern Windows Calculator can use app-container/window process indirection.
- File workflow is not yet modeled as ActionGraph actions.
- No fallback backend is implemented when UIA ValuePattern is unavailable.
- Terminal launch can correlate to a window, but validation still uses PID-window lookup and command quoting remains fragile.
- VS Code may be missing from PATH or require application/runtime command resolution before window correlation can run.

## Missing Abstractions

- Application runtime identity for packaged and multi-process applications.
- Keyboard/input fallback when UIA ValuePattern or InvokePattern is unavailable.
- ActionGraph representation for file workflows.
- Richer verification model for non-text UI results.

## Recommended Next Milestone

- Add KeyboardInputBackend without changing Action/Executor/Plan/Task.
- Add file actions after validation if file workflows need action telemetry.
- Improve error quality by reporting failed action, pattern, fallback candidates, and selected backend.
- Run Notepad reliability 10 times and record pass rate/duration distribution.
- Add package/AppUserModelID evidence for packaged apps and let validation query windows by application_runtime_id.
