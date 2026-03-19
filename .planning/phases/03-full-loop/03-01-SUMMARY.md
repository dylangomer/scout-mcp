---
phase: 03-full-loop
plan: 01
subsystem: api
tags: [fastmcp, mcp, proxy, ranking, search-registry, tdd]

# Dependency graph
requires:
  - phase: 01-intelligence-layer
    provides: search_registry, filter_http_servers, rank_servers pipeline
  - phase: 02-proxy-layer
    provides: proxy.connect, ToolListChangedNotification pattern
provides:
  - scout_acquire tool in server.py — single-call find+rank+connect+notify pipeline
  - tests/test_acquire.py — 5 tests covering all branches of scout_acquire
affects: [04-end-to-end, any phase building on Scout keystone tool]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "scout_acquire chains search_registry -> filter_http_servers -> rank_servers -> proxy.connect"
    - "Guard empty list before indexed access (http_servers and ranked) -> return no_servers_found"
    - "Conditional notification: fire ToolListChangedNotification only on status==connected, not on already_connected"

key-files:
  created:
    - tests/test_acquire.py
  modified:
    - server.py

key-decisions:
  - "scout_acquire returns {status, server, url, score, reasoning} — superset of proxy.connect result, adds ranking metadata"
  - "no_servers_found guard fires before rank_servers call when filter_http_servers returns [] — avoids unnecessary Haiku API call"

patterns-established:
  - "TDD RED/GREEN with separate commits per phase for each tool in server.py"
  - "Patch server.search_registry and server.rank_servers (not ranker.rank_servers) in server-level tests"

requirements-completed: [CTRL-01]

# Metrics
duration: 2min
completed: 2026-03-19
---

# Phase 3 Plan 01: scout_acquire Pipeline Summary

**scout_acquire keystone tool: single-call find+rank+connect+notify pipeline chaining all Scout subsystems with cache-hit fast path and empty-list guards**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-19T13:43:26Z
- **Completed:** 2026-03-19T13:45:18Z
- **Tasks:** 1 (TDD: RED + GREEN commits)
- **Files modified:** 2

## Accomplishments
- Implemented scout_acquire tool in server.py that chains search_registry, filter_http_servers, rank_servers, and proxy.connect in a single call
- Returns {status, server, url, score, reasoning} with full ranking metadata on successful connection
- Cache-hit fast path: returns already_connected without firing ToolListChangedNotification
- Empty-list guards prevent IndexError when no HTTP servers found or ranker returns nothing
- Full test coverage in tests/test_acquire.py (5 tests, all passing)
- Full test suite green: 47 tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: TDD scout_acquire -- failing tests** - `d2db3dd` (test)
2. **Task 1 GREEN: TDD scout_acquire -- implementation** - `405f148` (feat)

_Note: TDD task has two commits (test -> feat) following RED/GREEN protocol_

## Files Created/Modified
- `tests/test_acquire.py` - 5 tests for scout_acquire: happy path, cache hit, no HTTP servers, empty ranked list, signature check
- `server.py` - Added scout_acquire tool (lines 131-151), placed after scout_disconnect and before __main__

## Decisions Made
- scout_acquire returns {status, server, url, score, reasoning} — includes ranking metadata (score, reasoning) that proxy.connect alone does not provide
- Empty http_servers guard fires before rank_servers call — avoids unnecessary Haiku API call when no HTTP-reachable servers exist

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None - server.py had additional tools (scout_list_active, scout_disconnect) added in a previous session that were not visible in the plan's file snapshot. scout_acquire was placed correctly before __main__ as specified.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- scout_acquire tool is live and registered with FastMCP as @mcp.tool
- Full pipeline (find + rank + connect + notify) operational
- Phase 3 Plan 02 (if any) can build on scout_acquire as the keystone tool
- All Scout tools (ping, scout_find, scout_connect, scout_list_active, scout_disconnect, scout_acquire) are now implemented

---
*Phase: 03-full-loop*
*Completed: 2026-03-19*
