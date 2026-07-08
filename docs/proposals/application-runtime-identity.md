# Proposal: Application Runtime Identity

Status: proposed

Scope: observation model only. No implementation in this proposal.

## Problem

Version 0.1 models the relationship as:

```text
Process PID -> Window
```

This works for classic Win32 applications such as Notepad. Validation showed that it does not cover
modern Windows packaged applications such as Calculator. A launched process can be a broker,
launcher, app-container host, or short-lived process, while the visible window is owned by a
different process.

Special-casing `calc.exe` would make the architecture brittle. The runtime needs to model:

```text
Window -> Application runtime entity
Application runtime entity -> process tree / package / windows
```

## Goals

- Support classic Win32 applications.
- Support packaged Windows applications.
- Support multi-process applications such as browsers, IDEs, Electron apps, and TIA Portal.
- Preserve existing `ProcessObservation` and `WindowObservation` compatibility.
- Keep platform-specific handles and APIs inside backend adapters.

## Non-Goals

- No implementation in this step.
- No new actions or public facade methods.
- No Calculator special-case.
- No UI Automation expansion.

## Proposed Runtime Identities

### ApplicationIdentity

Stable-ish identity for the installed or launchable application.

Fields:

- `name`: human readable application name.
- `executable`: executable name if known, for example `notepad.exe`.
- `path`: executable path if known.
- `package_family_name`: Windows packaged app identity if known.
- `app_user_model_id`: Windows AppUserModelID if known.
- `publisher`: package publisher if known.
- `metadata`: backend-specific non-authoritative data.

### ApplicationRuntimeIdentity

Identity for one running application instance.

Fields:

- `runtime_id`: runtime-generated stable id for this observed instance.
- `application`: `ApplicationIdentity`.
- `root_process_id`: initial or best-known root process id.
- `process_ids`: all correlated process ids.
- `window_ids`: all correlated window identities.
- `started_at`: when the runtime first observed or launched it.
- `correlation_keys`: evidence used to associate processes and windows.
- `metadata`: backend-specific non-authoritative data.

### ProcessTreeObservation

Observation of process relationships.

Fields:

- `root`: `ProcessIdentity`.
- `processes`: tuple of `ProcessObservation`.
- `parent_by_pid`: mapping child pid -> parent pid.
- `observed_at`.
- `metadata`.

### WindowOwnership

Correlation evidence between a window and an application runtime entity.

Fields:

- `window`: `WindowIdentity`.
- `application_runtime_id`: id of the owning runtime entity if known.
- `process_id`: direct owner pid if known.
- `confidence`: correlation confidence.
- `reasons`: tuple of evidence strings.
- `metadata`.

## Changes To Existing Models

### ProcessIdentity

Keep existing fields:

- `pid`
- `name`

Add optional fields:

- `parent_pid`
- `session_id`
- `application_runtime_id`

Compatibility:

Existing code that reads `pid` and `name` keeps working.

### ProcessObservation

Keep existing fields:

- `identity`
- `path`
- `started_at`
- `status`
- `observed_at`
- `metadata`

Add optional fields:

- `command_line`
- `parent_pid`
- `package_family_name`
- `app_user_model_id`
- `application_runtime_id`

Compatibility:

Existing construction remains valid because new fields are optional.

### WindowIdentity

Keep existing fields:

- `title`
- `process_id`
- `class_name`

Add optional fields:

- `runtime_window_id`
- `application_runtime_id`
- `app_user_model_id`
- `package_family_name`

Compatibility:

`process_id` remains available for classic Win32 apps, but is no longer the only ownership link.

### WindowObservation

Keep existing fields:

- `identity`
- `bounds`
- `visible`
- `active`
- `observed_at`
- `metadata`

Add optional fields:

- `owner`: `WindowOwnership | None`
- `z_order`
- `display_id`

Compatibility:

Existing code that reads `identity.process_id` keeps working.

## Correlation Keys

Backends should produce correlation evidence rather than hard-coded decisions.

Potential Windows keys:

- launched pid;
- process parent/child relationship;
- executable path;
- command line;
- package family name;
- AppUserModelID;
- window process id;
- window class name;
- window title;
- UIA process id;
- shell app/window metadata when available;
- time proximity between launch and first window observation.

Example:

```text
ApplicationRuntimeIdentity(
  runtime_id="app-runtime:...",
  process_ids=(18740, 9120),
  window_ids=(...),
  correlation_keys=(
    "launch_pid=18740",
    "package_family_name=Microsoft.WindowsCalculator_...",
    "window_process_id=9120",
    "observed_within=2.1s",
  )
)
```

## Backend Responsibilities

Backends should:

- observe process trees;
- observe package identity where available;
- observe windows;
- produce correlation candidates with confidence and reasons;
- map native handles to runtime identities without exposing handles as primary identity.

Backends should not:

- special-case application names in core runtime;
- require ActionExecutor changes for packaged app support;
- expose HWND, UIA objects, or package APIs in runtime models as authoritative identity.

## WorldModel Changes

`WorldModel` should eventually cache:

- `applications`: tuple of application runtime observations;
- `processes`: tuple of process observations;
- `process_trees`: tuple of process tree observations;
- `windows`: tuple of window observations;
- `ownership`: tuple of window ownership observations.

The model remains a cache. It can be stale and refreshed from observation backends.

## Test Plan

### Notepad

Purpose: classic single-process Win32 application.

Expected:

- launched pid equals or directly correlates with window process id;
- one application runtime entity;
- one main window;
- confidence high.

Assertions:

- `ApplicationRuntimeIdentity.process_ids` includes launched pid;
- main `WindowObservation.identity.application_runtime_id` is set;
- legacy `WindowObservation.identity.process_id` remains populated.

### Calculator

Purpose: packaged Windows application.

Expected:

- launched pid may not own final window;
- package identity or AppUserModelID links window to application runtime entity;
- process tree/window ownership correlation succeeds without app-name special-case.

Assertions:

- runtime entity is created even if launched pid and window pid differ;
- correlation reasons include package/app model evidence or process tree evidence;
- Calculator validation can find the visible window through application runtime identity.

### Multi-Process Application

Candidates:

- browser;
- Visual Studio Code;
- Electron-based sample app.

Expected:

- multiple process ids correlate to one runtime application entity;
- multiple windows or UI trees can belong to the same runtime entity;
- active window ownership resolves to application runtime identity.

Assertions:

- `process_ids` contains more than one pid;
- at least one window has `application_runtime_id`;
- closing the main window updates or stales the runtime entity.

## Migration Path

1. Add optional identity fields to observation models.
2. Add application runtime observation models.
3. Teach Win32 backend to emit process tree and window ownership evidence.
4. Update WorldModel to cache application runtime entities.
5. Update Calculator validation to use application runtime correlation.
6. Keep legacy PID-based lookups working.

## Tag Recommendation

After creating the first repository commit, tag the validation milestone:

```bash
git tag v0.1-validation
```

Do not create the tag before the initial commit; there is currently no commit object to tag.
