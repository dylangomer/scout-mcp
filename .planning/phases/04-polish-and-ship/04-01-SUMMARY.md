---
phase: 04-polish-and-ship
plan: 01
subsystem: api
tags: [error-handling, fastmcp, python, tdd, structured-response]

# Dependency graph
requires:
  - phase: 03-full-loop
    provides: scout_find and scout_acquire tools that call search_registry
provides:
  - try/except guards in scout_find and scout_acquire returning structured error dicts
  - tests/test_error_handling.py with TestScoutFindErrorHandling and TestScoutAcquireErrorHandling
affects: [04-polish-and-ship]

# Tech tracking
tech-stack:
  added: []
  patterns: [two-tier except pattern: RuntimeError first then broad Exception fallback]

key-files:
  created: [tests/test_error_handling.py]
  modified: [server.py]

key-decisions:
  - "Catch RuntimeError specifically before broad Exception — search_registry raises RuntimeError for registry failures, broad Exception is only for truly unexpected errors"
  - "Return {'status': 'error', 'message': str(e)} matching existing status-dict convention — no ToolError or McpError, consistent with all other tool returns"
  - "Wrap entire scout_acquire body in try/except — ensures notification is never sent when error occurs, without needing extra guard logic"
  - "Updated scout_find return type annotation to list[dict] | dict — accurately reflects the new possible return shape"

patterns-established:
  - "Two-tier error catch: except RuntimeError as e (specific) then except Exception as e (broad fallback with prefixed message)"
  - "Error shape: {'status': 'error', 'message': str(e)} consistent with existing status-dict convention"

requirements-completed: [PLSH-01]

# Metrics
duration: 3min
completed: 2026-03-19
---

# Phase 4 Plan 01: Error Handling for scout_find and scout_acquire Summary

**try/except guards added to scout_find and scout_acquire returning {"status": "error", "message": ...} dicts instead of propagating raw RuntimeError to FastMCP**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-19T15:34:02Z
- **Completed:** 2026-03-19T15:37:00Z
- **Tasks:** 2 (TDD RED + TDD GREEN)
- **Files modified:** 2

## Accomplishments
- Added two-tier try/except to scout_find: catches RuntimeError first, then broad Exception with prefixed message
- Added two-tier try/except to scout_acquire: same pattern, entire body wrapped so notification never fires on error
- Updated scout_find return type annotation to list[dict] | dict
- Created tests/test_error_handling.py with 5 tests covering both tools and both error tiers
- All 52 tests pass (47 existing + 5 new) with zero regressions

## Task Commits

Each task was committed atomically:

1. **TDD RED: Failing tests for error handling** - `5562d92` (test)
2. **TDD GREEN: Implement error handling** - `1e8a457` (feat)

_Note: TDD tasks have two commits (test → feat)_

## Files Created/Modified
- `tests/test_error_handling.py` - Error path tests for scout_find and scout_acquire (TestScoutFindErrorHandling, TestScoutAcquireErrorHandling)
- `server.py` - try/except guards added to scout_find and scout_acquire; scout_find return type updated to list[dict] | dict

## Decisions Made
- Catch RuntimeError specifically before broad Exception — search_registry raises RuntimeError for registry failures; broad Exception handles truly unexpected errors with a prefixed message for distinction
- Return {"status": "error", "message": ...} matching existing status-dict convention — no ToolError or McpError, host LLM can reason about the error like any other tool result
- Wrap entire scout_acquire body in try/except — ensures notification is never sent when error occurs without needing an extra early-return guard
- Updated scout_find return type annotation to list[dict] | dict to accurately reflect the new possible return shape

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Error handling complete for scout_find and scout_acquire (PLSH-01 satisfied)
- Ready for remaining polish-and-ship tasks

---
*Phase: 04-polish-and-ship*
*Completed: 2026-03-19*

## Self-Check: PASSED

- FOUND: tests/test_error_handling.py
- FOUND: server.py
- FOUND: .planning/phases/04-polish-and-ship/04-01-SUMMARY.md
- FOUND commit: 5562d92 (test — RED phase)
- FOUND commit: 1e8a457 (feat — GREEN phase)
