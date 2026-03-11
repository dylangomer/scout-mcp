---
phase: 02-proxy-layer
plan: 01
subsystem: proxy
tags: [fastmcp, proxy-provider, proxy-client, namespace, in-memory-cache]

# Dependency graph
requires:
  - phase: 01-intelligence-layer
    provides: ranker.py filter/rank pipeline and FastMCP server scaffolding used as test base
provides:
  - proxy.py module with connect(), is_connected(), disconnect(), get_connections()
  - In-memory _connections/_urls cache preventing duplicate provider registration
  - ProxyProvider + add_provider(namespace=name) pattern for namespaced tool forwarding
affects:
  - 02-proxy-layer/02-02 (scout_acquire tool will call proxy.connect() directly)
  - 03-acquire-tool (Phase 3 entry point for connecting to discovered servers)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ProxyProvider(lambda u=url: ProxyClient(u)) — default-arg binding prevents lambda closure bug"
    - "_WrappedProvider._inner — internal attribute for finding wrapped provider in mcp.providers for removal"
    - "Module-level dict cache with _connections/_urls for O(1) duplicate prevention"

key-files:
  created:
    - proxy.py
    - tests/test_proxy.py
  modified: []

key-decisions:
  - "Use _WrappedProvider._inner (not .provider) to find the raw provider in mcp.providers during disconnect — discovered by source inspection of FastMCP 3.1.0 wrapped_provider module"
  - "Test verifies lambda binding by calling provider.client_factory() and comparing transport.url on two separately-created providers"

patterns-established:
  - "Pattern: _reset_cache() helper clears both _connections and _urls dicts before each test — avoids module-level state leakage between test methods"
  - "Pattern: spy_add_provider wraps original method to capture namespace= kwarg while preserving real behavior"

requirements-completed: [PRXY-01, PRXY-02, PRXY-04]

# Metrics
duration: 2min
completed: 2026-03-11
---

# Phase 2 Plan 01: Proxy Connection Manager Summary

**ProxyConnectionManager in proxy.py using FastMCP ProxyProvider with namespace= and module-level dict cache, verified by 11 TDD tests covering connect, cache, disconnect, and get_connections**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-11T17:13:33Z
- **Completed:** 2026-03-11T17:15:52Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- proxy.py implements all 4 public functions: connect(), is_connected(), disconnect(), get_connections()
- connect() registers namespaced ProxyProvider on FastMCP instance; lambda default-arg binding avoids closure bug
- disconnect() correctly identifies and removes _WrappedProvider using ._inner attribute (not .provider)
- 11 tests cover all behaviors; full suite (32 tests) passes with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing tests for proxy connection manager** - `8e02bb8` (test)
2. **Task 2: Implement proxy connection manager** - `20c10b4` (feat)

_Note: TDD tasks — test commit first (RED), then implementation commit (GREEN)_

## Files Created/Modified

- `proxy.py` - ProxyConnectionManager: connect, is_connected, disconnect, get_connections with module-level cache
- `tests/test_proxy.py` - 11 unit tests covering PRXY-01, PRXY-02, PRXY-04 requirements

## Decisions Made

- Used `_WrappedProvider._inner` to match wrapped entries in `mcp.providers` during disconnect. The plan said to check `.provider` attribute but direct source inspection of FastMCP 3.1.0 revealed the attribute is `._inner`. Fixed inline as Rule 1 (bug in plan's internal reference, not in external behavior).
- Test for lambda binding calls `provider.client_factory()` and inspects `client.transport.url` (not `client._url` as initially drafted). ProxyClient wraps URL in a `StreamableHttpTransport` accessible via `.transport.url`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan specified wrong attribute name for _WrappedProvider inner provider**
- **Found during:** Task 2 (implementing disconnect)
- **Issue:** Plan said `getattr(entry, "provider", None)` to find raw provider in wrapped entry, but FastMCP 3.1.0 uses `._inner` not `.provider`
- **Fix:** Changed lookup from `.provider` to `._inner`; verified by running Python and inspecting the actual attribute list of `_WrappedProvider`
- **Files modified:** proxy.py
- **Verification:** test_disconnect_removes_provider passes; mcp.providers shrinks by 1 after disconnect
- **Committed in:** 20c10b4 (Task 2 commit)

**2. [Rule 1 - Bug] Test used wrong ProxyClient URL attribute (_url vs transport.url)**
- **Found during:** Task 2 (running tests, fixing test_connect_binds_url_in_lambda)
- **Issue:** Test used `client._url` which does not exist; URL is stored in `client.transport.url`
- **Fix:** Updated test to use `str(client.transport.url)` for URL comparison
- **Files modified:** tests/test_proxy.py
- **Verification:** test_connect_binds_url_in_lambda passes with two providers showing distinct transport URLs
- **Committed in:** 20c10b4 (Task 2 commit — updated test was re-staged with implementation)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 — wrong internal attribute names in plan spec)
**Impact on plan:** Both fixes necessary for correct behavior; no scope creep. Plan's attribute references matched older or hypothetical FastMCP internals; source inspection resolved both.

## Issues Encountered

- FastMCP's `_WrappedProvider` stores the inner provider as `._inner` (private), not `.provider`. This is an internal implementation detail not documented in the research. The research correctly flagged to verify mcp.providers list mutation but did not document the attribute name.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- proxy.connect(), is_connected(), disconnect(), get_connections() ready for Phase 3 (scout_acquire tool)
- The tools/list_changed notification (PRXY-03) is scoped to Phase 2 Plan 02 or the scout_acquire tool in Phase 3
- No blockers; all Phase 2 Plan 01 requirements satisfied

---
*Phase: 02-proxy-layer*
*Completed: 2026-03-11*
