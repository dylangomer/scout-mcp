# Roadmap: Scout MCP

## Overview

Scout delivers AI-powered dynamic tool discovery for MCP hosts. Phase 1 (foundation: registry search + ping) is complete. The remaining work adds Haiku-based ranking (Phase 1 here), runtime HTTP proxying via ProxyProvider (Phase 2), the full scout_acquire control loop (Phase 3), and error handling plus documentation polish (Phase 4).

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3, 4): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Intelligence Layer** - Haiku ranking pipeline with env config and scout_find tool (completed 2026-03-11)
- [ ] **Phase 2: Proxy Layer** - Dynamic HTTP proxy connection management with namespace safety and session cache
- [x] **Phase 3: Full Loop** - scout_acquire end-to-end pipeline, scout_list_active, scout_disconnect, and in-memory caching (completed 2026-03-19)
- [ ] **Phase 4: Polish and Ship** - Error handling across all tools, env var config hardening, README with architecture diagram and install instructions

## Phase Details

### Phase 1: Intelligence Layer
**Goal**: Users can ask Scout to find the best MCP server for a task and get a ranked, scored list back
**Depends on**: Foundation (previous Phase 1 — already complete: find_servers, ping)
**Requirements**: CONF-01, CONF-02, DISC-01, DISC-02, DISC-03
**Success Criteria** (what must be TRUE):
  1. Scout fails fast at startup with a clear error if ANTHROPIC_API_KEY is missing
  2. Registry URL is configurable via environment variable; the default points to the live registry
  3. scout_find(context) returns a ranked, scored list of HTTP-reachable servers filtered of stdio-only entries
  4. Ranking uses Claude Haiku asynchronously — no blocking of the stdio event loop
**Plans**: 3 plans

Plans:
- [ ] 01-01-PLAN.md — Environment config, startup validation, and test infrastructure (CONF-01, CONF-02)
- [ ] 01-02-PLAN.md — Haiku ranker module with HTTP filter, scoring, and fallback (DISC-01, DISC-02)
- [ ] 01-03-PLAN.md — scout_find tool wiring search + filter + rank pipeline (DISC-03)

### Phase 2: Proxy Layer
**Goal**: Scout can connect to a remote MCP server at runtime and transparently expose its tools to the host
**Depends on**: Phase 1
**Requirements**: PRXY-01, PRXY-02, PRXY-03, PRXY-04
**Success Criteria** (what must be TRUE):
  1. Scout connects to a remote HTTP MCP server and the host immediately sees its tools without a restart
  2. Tools from different downstream servers never collide — each is prefixed with its server name
  3. After connecting, a tools/list_changed notification fires so the host refreshes its tool list
  4. Calling scout_find or scout_acquire for a server already connected returns instantly from cache without re-fetching
**Plans**: 2 plans

Plans:
- [ ] 02-01-PLAN.md — ProxyProvider connection manager with namespace, cache, and disconnect (PRXY-01, PRXY-02, PRXY-04)
- [ ] 02-02-PLAN.md — scout_connect tool with tools/list_changed notification wiring (PRXY-03)

### Phase 3: Full Loop
**Goal**: A single scout_acquire(context) call handles the entire find-rank-connect-proxy pipeline and users have full runtime control over active connections
**Depends on**: Phase 2
**Requirements**: CTRL-01, CTRL-02, CTRL-03
**Success Criteria** (what must be TRUE):
  1. scout_acquire(context) with a natural-language description connects the best matching server and its tools are immediately usable
  2. scout_list_active() shows all servers Scout has connected to this session
  3. scout_disconnect(server_name) removes a server's tools from the host's tool list cleanly
**Plans**: 2 plans

Plans:
- [ ] 03-01-PLAN.md — scout_acquire pipeline with cache-hit fast path and notification (CTRL-01)
- [ ] 03-02-PLAN.md — scout_list_active and scout_disconnect control tools (CTRL-02, CTRL-03)

### Phase 4: Polish and Ship
**Goal**: Scout is production-ready with clean error handling across all tools and complete documentation for new users
**Depends on**: Phase 3
**Requirements**: PLSH-01, PLSH-02
**Success Criteria** (what must be TRUE):
  1. Every tool returns a clear, human-readable message on failure — no raw stack traces or silent errors
  2. All environment variable configuration is validated with helpful guidance when misconfigured
  3. README documents architecture, install steps, and a working usage example end-to-end
**Plans**: 2 plans

Plans:
- [ ] 04-01-PLAN.md — Error handling for scout_find and scout_acquire with TDD (PLSH-01)
- [ ] 04-02-PLAN.md — README with architecture diagram, install instructions, usage examples (PLSH-02)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Intelligence Layer | 3/3 | Complete   | 2026-03-11 |
| 2. Proxy Layer | 2/2 | Complete | 2026-03-11 |
| 3. Full Loop | 2/2 | Complete   | 2026-03-19 |
| 4. Polish and Ship | 0/2 | Not started | - |
