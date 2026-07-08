# Validation

Validation mode does not add new runtime capabilities. It runs real scenarios against version 0.1
and records traces, failures, and improvement candidates.

Run manually on Windows:

```bash
python -m evaluations.run_validation
```

The report is written to:

```text
evaluations/last-validation-report.json
```

## Scenarios

### Notepad

- Open application.
- Type text.
- Read text back through UI Automation observation.
- Verify result.

Expected runtime path:

```text
OpenApplicationAction -> Win32Backend
TypeTextAction -> UIAActionBackend
Verification -> UIAObservationBackend
```

### Calculator

- Open application.
- Execute `1 + 2 =`.
- Read result through observation.
- Verify result.

This scenario is intentionally included as a stress case. Modern Windows Calculator may route
windows through app-container infrastructure, so process/window correlation can fail in version 0.1.
The proposed model fix is documented in
[Application Runtime Identity](proposals/application-runtime-identity.md).

### File Workflow

- Create text.
- Save file.
- Verify file exists and content matches.

In version 0.1 this validates the existing file facade. File operations are not yet represented as
ActionGraph actions.

## Metrics To Track

- Reliability: pass rate over repeated runs.
- Duration: task start, launch, window detected, UI element found, completed.
- Error quality: failed action, reason, fallback candidates, selected backend, final result.
- Backend extensibility: add a backend without changing Action, Executor, Plan, or Task.

## Version Tag

The repository currently has no commits. After the first commit is created, tag the accepted
validation milestone:

```bash
git tag v0.1-validation
```
