# Validation Summary

Last run:

- Total: 3
- Passed: 2
- Failed: 1

## Results

### Notepad

Status: passed

- `OpenApplicationAction -> Win32Backend`
- `TypeTextAction -> UIAActionBackend`
- Verification: text read back successfully.
- Duration: about 1.06s.

### Calculator

Status: failed

Failure:

```text
No application window detected for process
```

Current interpretation:

Modern Windows Calculator may launch through app-container infrastructure where the process that is
created is not the process that owns the final visible window. The runtime needs a better
process/window correlation strategy for packaged applications.

### File Workflow

Status: passed

- File created.
- Content read back.
- Existence verified.

Limitation:

File workflow currently validates the file facade, not ActionGraph file actions.

## Stable

- Notepad E2E path works through Win32 launch, UIA observation, UIA ValuePattern, and verification.
- File facade works within a configured root.

## Problems Found

- Packaged Windows apps can break simple PID-to-window correlation.
- File operations are not yet action graph actions.
- No fallback backend exists when UIA ValuePattern is unavailable.

## Architecture Proposal

The Calculator failure should not be fixed with an app-specific special case. The proposed direction
is to introduce application runtime identity and correlation evidence:

[Application Runtime Identity](../docs/proposals/application-runtime-identity.md)

## Recommended Next Validation Work

- Run Notepad E2E 10 times and record pass rate and duration distribution.
- Improve error quality around failed action, reason, fallback candidates, and selected backend.
- Add a `KeyboardInputBackend` later without changing Action, Executor, Plan, or Task.
