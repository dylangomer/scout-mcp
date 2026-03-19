---
phase: 03-full-loop
plan: 02
subsystem: api
tags: [fastmcp, mcp, proxy, tools, control-plane]

# Dependency graph
requires:
  - phase: 02-proxy-layer
    provides: proxy.get_connections() and proxy.disconnect() functions used by these tools
  - phase: 03-full-loop
    plan: 01
    provides: scout_acquire notification pattern (same guard-on-success approach)
provides:
  - scout_list_active tool: returns [{name, url}] for all active connections
  - scout_disconnect tool: removes server, fires ToolListChangedNotification on success only
affects: [03-full-loop, end-to-end integration tests]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sync tool for read-only operations on synchronous proxy state (scout_list_active)"
    - "Async tool with conditional notification guard: fire notification only on status == specific_value"
    - "TDD red-green cycle: write failing tests, commit, implement, all green, commit"

key-files:
  created:
    - tests/test_scout_control.py
  modified:
    - server.py

key-decisions:
  - "scout_list_active is sync (def not async def) — proxy.get_connections() is sync, no await needed"
  - "scout_disconnect guards ToolListChangedNotification on status == disconnected — mirrors scout_connect guard pattern"
  - "scout_disconnect parameter named server_name (not name) to distinguish from scout_connect's name parameter"

patterns-established:
  - "Control plane tools (list/disconnect) follow same guard-notification pattern as scout_connect"
  - "Sync tools acceptable in FastMCP when no async work required"

requirements-completed: [CTRL-02, CTRL-03]

# Metrics
duration: 2min
completed: 2026-03-19
---

# Phase 3 Plan 02: scout_list_active and scout_disconnect Summary

**Sync list-active and async disconnect control-plane MCP tools with conditional ToolListChangedNotification guard on disconnect success**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-19T13:43:23Z
- **Completed:** 2026-03-19T13:46:09Z
- **Tasks:** 1 (TDD with RED + GREEN sub-commits)
- **Files modified:** 2

## Accomplishments
- scout_list_active synchronous tool returns [{name, url}] from proxy.get_connections() live on each call
- scout_disconnect async tool removes server via proxy.disconnect() and fires ToolListChangedNotification only on "disconnected" status (not "not_found")
- 6 new tests covering both tools: empty/populated list, sync check, success notification, not_found no-notification, signature inspection
- Full suite of 47 tests green (41 pre-existing + 6 new)

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests for scout_list_active and scout_disconnect** - `f883c67` (test)
2. **Task 1 GREEN: Implement scout_list_active and scout_disconnect in server.py** - `405f148` (feat, shared with 03-01 GREEN)

_Note: TDD tasks have RED commit (f883c67) and GREEN commit (405f148). The GREEN commit was auto-applied by editor and bundled with plan 03-01 GREEN implementation._

## Files Created/Modified
- `tests/test_scout_control.py` - 6 tests: TestListActive (3) and TestDisconnect (3)
- `server.py` - Added scout_list_active (sync @mcp.tool) and scout_disconnect (async @mcp.tool) after scout_connect

## Decisions Made
- scout_list_active is a regular function (def), not async — proxy.get_connections() is synchronous, no coroutine overhead needed
- scout_disconnect named parameter `server_name` (not `name`) to avoid confusion with scout_connect's `name` parameter
- Notification guard pattern: `if result["status"] == "disconnected"` — identical guard approach to scout_connect's `status == "connected"` check

## Deviations from Plan

None - plan executed exactly as written. Implementation matches the specification in the plan's `<implementation>` block verbatim.

## Issues Encountered

None. Editor auto-applied both plan 03-01 (scout_acquire) and plan 03-02 (scout_list_active + scout_disconnect) implementations before the 03-01 GREEN commit, resulting in both being bundled in commit 405f148. This did not affect correctness — all 47 tests pass, implementations are correct.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Control plane is complete: scout_find (discover), scout_connect (connect), scout_list_active (list), scout_disconnect (remove)
- scout_acquire (from plan 03-01) completes the one-shot acquisition flow
- Full end-to-end loop ready for integration testing
- All 5 MCP tools implemented and tested (ping, scout_find, scout_connect, scout_list_active, scout_disconnect, scout_acquire = 6 total)

---
*Phase: 03-full-loop*
*Completed: 2026-03-19*
