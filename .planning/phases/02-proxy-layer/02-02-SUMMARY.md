---
phase: 02-proxy-layer
plan: 02
subsystem: server
tags: [fastmcp, notification, tools-list-changed, scout-connect, tdd]

# Dependency graph
requires:
  - phase: 02-proxy-layer
    plan: 01
    provides: proxy.connect() function that returns status dict
  - fastmcp.server.context.Context for auto-injection
  - mcp.types.ToolListChangedNotification for host notification
provides:
  - scout_connect tool in server.py that calls proxy.connect and fires notification
  - Conditional notification: fires only on new connections (status == "connected")
  - Notification wiring tests in tests/test_server_proxy.py
affects:
  - 03-acquire-tool (Phase 3 scout_acquire may call scout_connect or proxy.connect directly)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "import mcp.types as mcp_types — avoids shadowing by module-level FastMCP instance named mcp"
    - "ctx: Context parameter in @mcp.tool — FastMCP auto-injects Context when annotation present"
    - "Conditional notification: if result['status'] == 'connected' before ctx.send_notification"

key-files:
  created:
    - tests/test_server_proxy.py
  modified:
    - server.py

key-decisions:
  - "Import mcp.types as mcp_types (alias) to avoid shadowing by module-level FastMCP instance named mcp — local variable mcp resolves first in Python lookup"
  - "Test patches proxy.connect (not server.proxy.connect) because server.py imports proxy as a module and calls proxy.connect; patch target must match the namespace where the name is looked up"

patterns-established:
  - "Pattern: AsyncMock(spec=Context) for mock Context in tests — gives send_notification as AsyncMock with correct spec"
  - "Pattern: inspect.signature(server.scout_connect) to verify ctx: Context annotation in test"

requirements-completed: [PRXY-03]

# Metrics
duration: 2min
completed: 2026-03-11
---

# Phase 2 Plan 02: Notification Wiring Summary

**scout_connect tool in server.py calls proxy.connect() and sends ToolListChangedNotification on new connections only, verified by 4 TDD tests with mock Context**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-11T17:19:02Z
- **Completed:** 2026-03-11T17:21:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- server.py has new `scout_connect` tool with `ctx: Context` parameter for FastMCP auto-injection
- Notification fires exactly once per new connection via `ctx.send_notification(mcp_types.ToolListChangedNotification())`
- Cache hits (already_connected status) are silent — no duplicate notifications sent to host
- 4 tests in `tests/test_server_proxy.py` cover: notification on new connection, no notification on cache hit, pass-through return value, and ctx: Context signature verification
- Full test suite: 36 tests pass (32 pre-existing + 4 new), zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing tests for notification wiring** - `74ca51b` (test)
2. **Task 2: Implement scout_connect tool with notification wiring** - `1edca7d` (feat)

_Note: TDD tasks — test commit first (RED), then implementation commit (GREEN)_

## Files Created/Modified

- `server.py` — Added 3 imports (`Context`, `mcp_types`, `proxy`) and `scout_connect` async tool (14 lines)
- `tests/test_server_proxy.py` — 4 unit tests covering PRXY-03 requirement (89 lines)

## Decisions Made

- Imported `mcp.types` as `mcp_types` to avoid name collision with the module-level `mcp` variable (the FastMCP instance). Python resolves local names first, so `mcp.types` inside any function would resolve to the FastMCP instance's `.types` attribute — which does not exist. The alias `mcp_types` is unambiguous.
- Patched `proxy.connect` (not `server.proxy.connect`) in tests. The server module imports `proxy` as a module and calls `proxy.connect(...)`. The correct patch target is `proxy.connect` — the function in its original namespace, which is what `server.py` looks up at call time.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Name collision between mcp module and FastMCP instance variable**
- **Found during:** Task 2, first test run
- **Issue:** Plan specified `mcp.types.ToolListChangedNotification()` but the module-level variable `mcp = FastMCP("Scout", ...)` shadows the `mcp` package name in Python's namespace lookup. At runtime `mcp.types` would look up the `.types` attribute on the FastMCP instance, not on the mcp package.
- **Fix:** Changed `import mcp.types` to `import mcp.types as mcp_types` and updated the call to `mcp_types.ToolListChangedNotification()`
- **Files modified:** server.py
- **Verification:** All 4 tests pass with the alias; `AttributeError: 'FastMCP' object has no attribute 'types'` resolved
- **Committed in:** 1edca7d (Task 2 commit)

## Issues Encountered

- The plan's example code `mcp.types.ToolListChangedNotification()` silently conflicts with the existing module-level `mcp` FastMCP instance. This is a pattern-level pitfall: any FastMCP server that names its instance `mcp` and also imports `mcp.*` submodules must use aliased imports.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `scout_connect` tool fully wired with notification; ready for integration into Claude Desktop workflow
- Phase 3 (03-acquire-tool) can build on `proxy.connect()` and `proxy.disconnect()` directly or via `scout_connect`
- No blockers; PRXY-03 requirement satisfied

---
*Phase: 02-proxy-layer*
*Completed: 2026-03-11*
