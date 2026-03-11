# Requirements: Scout MCP

**Defined:** 2026-03-11
**Core Value:** The host gets new MCP tools mid-session without any config change — Scout finds, ranks, connects, and proxies transparently.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Discovery

- [x] **DISC-01**: Scout filters out non-HTTP servers (remote_url: None) from registry results before ranking
- [x] **DISC-02**: Scout ranks registry results using Claude Haiku based on user context, returning structured JSON with scores
- [x] **DISC-03**: scout_find(context) tool wraps search + filter + rank into a single call

### Proxy

- [x] **PRXY-01**: Scout connects to a remote HTTP MCP server at runtime using FastMCP ProxyProvider
- [x] **PRXY-02**: Downstream server tools are namespaced (prefixed with server name) to prevent collisions
- [x] **PRXY-03**: Scout fires tools/list_changed notification after connecting a new server so the host discovers new tools
- [x] **PRXY-04**: In-memory connection cache prevents re-connecting to the same server within a session

### Control

- [ ] **CTRL-01**: scout_acquire(context) triggers the full flow: find → rank → connect → proxy in one call
- [ ] **CTRL-02**: scout_list_active() shows all servers Scout has connected to this session
- [ ] **CTRL-03**: scout_disconnect(server_name) removes a proxied server and cleans up its tools

### Configuration

- [x] **CONF-01**: ANTHROPIC_API_KEY is required — Scout validates on startup and fails fast with a clear message if missing
- [x] **CONF-02**: Registry URL is configurable via environment variable with sensible default

### Polish

- [ ] **PLSH-01**: All tools have proper error handling with graceful, informative failure messages
- [ ] **PLSH-02**: README documents architecture, install instructions, and usage examples

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Transport

- **TRNS-01**: Support stdio-based server proxying (spawn local processes)
- **TRNS-02**: Support SSE transport for downstream connections

### Security

- **SECU-01**: OAuth/authentication for downstream servers requiring credentials
- **SECU-02**: Tool allowlist/blocklist for proxied servers

### Deployment

- **DEPL-01**: Deploy Scout as a remote HTTP server (Railway/Prefect Horizon)
- **DEPL-02**: Multi-host session support

### Intelligence

- **INTL-01**: Learning from user behavior to improve ranking over time
- **INTL-02**: Auto-suggest servers based on conversation context without explicit request

## Out of Scope

| Feature | Reason |
|---------|--------|
| Persistent storage / database | In-memory session state sufficient for v1 |
| Web UI or dashboard | CLI/MCP interface only |
| Stdio server proxying | HTTP-only in v1; complexity not justified |
| Remote deployment | Local stdio via Claude Desktop first |
| Demo video recording | Development plan item, not a code requirement |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CONF-01 | Phase 1 | Complete |
| CONF-02 | Phase 1 | Complete |
| DISC-01 | Phase 1 | Complete |
| DISC-02 | Phase 1 | Complete |
| DISC-03 | Phase 1 | Complete |
| PRXY-01 | Phase 2 | Complete |
| PRXY-02 | Phase 2 | Complete |
| PRXY-03 | Phase 2 | Complete |
| PRXY-04 | Phase 2 | Complete |
| CTRL-01 | Phase 3 | Pending |
| CTRL-02 | Phase 3 | Pending |
| CTRL-03 | Phase 3 | Pending |
| PLSH-01 | Phase 4 | Pending |
| PLSH-02 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0

---
*Requirements defined: 2026-03-11*
*Last updated: 2026-03-11 after roadmap revision (Phase 3 split into Phase 3 + Phase 4)*
