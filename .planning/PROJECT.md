# Scout MCP

## What This Is

Scout is an MCP server that acts as a gateway for dynamic tool discovery. Instead of manually configuring MCP servers in a config file and restarting, Scout lets the AI find and proxy the right server mid-session. A host (Claude Desktop, Cursor, etc.) connects to Scout once at startup, and Scout handles discovering, ranking, connecting to, and proxying downstream MCP servers on demand.

## Core Value

The host gets new tools mid-session without any config change — Scout finds the right MCP server, connects to it, and proxies its tools back transparently.

## Requirements

### Validated

- ✓ FastMCP server running with ping tool — Phase 1
- ✓ Registry search via find_servers(query) hitting registry.modelcontextprotocol.io — Phase 1

### Active

- [ ] Rank registry results using Claude Haiku based on user context
- [ ] Wrap search + rank into a single scout_find(context) tool
- [ ] Connect to remote HTTP MCP servers at runtime via FastMCP Client
- [ ] Re-register downstream server tools on Scout dynamically
- [ ] Route tool calls transparently to downstream servers (proxy pattern)
- [ ] End-to-end flow: scout_acquire(context) triggers find → rank → connect → proxy
- [ ] List active server connections via scout_list_active()
- [ ] Disconnect servers via scout_disconnect(server_name)
- [ ] In-memory caching of connected servers (avoid re-fetching)
- [ ] Proper error handling with graceful failure messages
- [ ] Environment variable configuration (ANTHROPIC_API_KEY, registry URL)
- [ ] Clean README with architecture, install instructions

### Out of Scope

- Stdio server proxying — complexity not justified for v1, HTTP-only
- OAuth/authentication for downstream servers — no auth servers in v1
- Persistent storage / database — in-memory session state only
- Remote deployment (Railway/Horizon) — local stdio via Claude Desktop first
- Web UI or dashboard — CLI/MCP interface only
- Multi-host support — single host session at a time

## Context

- Phase 1 is complete: server.py has ping() and find_servers() tools, wired into Claude Desktop
- Project uses uv with fastmcp>=3.1.0, anthropic>=0.84.0, httpx>=0.28.1
- MCP registry API at registry.modelcontextprotocol.io/v0.1/servers returns server listings with name, description, and remote URLs
- Scout runs as a stdio process launched by Claude Desktop via claude_desktop_config.json
- FastMCP provides both server (@mcp.tool decorator) and Client classes for programmatic MCP connections

## Constraints

- **API Key**: ANTHROPIC_API_KEY required for Haiku ranking — core functionality depends on it
- **Transport**: HTTP-only for downstream server connections in v1
- **Runtime**: Python 3.14+, managed by uv
- **Hosting**: Local stdio transport via Claude Desktop config (not remote deployment)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| FastMCP for server framework | Handles MCP protocol complexity, 70% market share | ✓ Good |
| Haiku for ranking | Cheap/fast, used as utility function not primary intelligence | — Pending |
| HTTP-only proxy in v1 | Simpler implementation, covers remote server use case | — Pending |
| API key required (not optional) | Ranking is core value prop, degraded mode not useful | — Pending |
| In-memory state only | Session-scoped, no persistence needed for v1 | — Pending |

---
*Last updated: 2026-03-11 after initialization*
