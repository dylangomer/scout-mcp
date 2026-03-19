# Scout MCP

AI-powered dynamic tool discovery for MCP hosts.

Scout is an MCP server that acts as a gateway for runtime tool discovery. Connect your MCP host (Claude Desktop, Cursor, or any MCP-compatible client) to Scout once, and Scout handles finding, ranking, connecting to, and proxying downstream MCP servers on demand — mid-session, without any config change or restart.


## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Claude Desktop (or any MCP host)                           │
│                                                             │
│  "Find me a GitHub integration"                             │
└──────────────────────────┬──────────────────────────────────┘
                           │  stdio (MCP protocol)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Scout MCP Server (server.py)                               │
│                                                             │
│  Tools: scout_find, scout_connect, scout_acquire,           │
│         scout_list_active, scout_disconnect, ping           │
└───────────┬────────────────────────────────────────────────-┘
            │                             │
            ▼                             ▼
┌───────────────────────┐   ┌────────────────────────────────┐
│  MCP Registry         │   │  Remote MCP Servers (HTTP)     │
│                       │   │                                │
│  registry.model       │   │  github-mcp                   │
│  contextprotocol.io   │   │  slack-mcp                    │
│                       │   │  weather-mcp  ...              │
│  Claude Haiku ranks   │   │                                │
│  results by relevance │   │  Tools proxied under Scout's   │
│                       │   │  namespace (server_name_tool)  │
└───────────────────────┘   └────────────────────────────────┘
```

**Data flow:** The host sends a natural language request to Scout. Scout queries the MCP registry, uses Claude Haiku to rank results by relevance, connects to the best matching server over HTTP, and proxies its tools back to the host under a namespaced prefix. The host discovers the new tools immediately via a `tools/list_changed` notification.


## Prerequisites

- Python 3.14 or later
- [uv](https://docs.astral.sh/uv/) — Python package manager and runner
- Claude Desktop (or any MCP-compatible host)
- Anthropic API key — required for Claude Haiku ranking


## Install

```bash
git clone https://github.com/YOUR_USERNAME/scout-mcp.git
cd scout-mcp
uv sync
```

`uv sync` creates a virtual environment and installs all dependencies defined in `pyproject.toml`.


## Claude Desktop Configuration

Add Scout to your Claude Desktop config file:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "scout": {
      "command": "uv",
      "args": ["run", "python", "server.py"],
      "cwd": "/absolute/path/to/scout-mcp",
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-your-key-here"
      }
    }
  }
}
```

Replace `/absolute/path/to/scout-mcp` with the actual path to your cloned repository. The `cwd` field is required — Claude Desktop needs it to locate `server.py` and the project's virtual environment.

Restart Claude Desktop after editing the config. Scout starts as a subprocess and appears as a connected MCP server.


## Usage

Scout exposes six tools. You interact with them through natural language in Claude Desktop; Claude calls the tools on your behalf.

### scout_find — search for servers

Prompt: "Find me MCP servers for GitHub integration"

Scout queries the registry, ranks results with Haiku, and returns up to 5 matches:

```python
[
  {
    "name": "github-mcp",
    "description": "GitHub API integration for MCP",
    "remote_url": "https://mcp.example.com/github",
    "score": 0.95,
    "reasoning": "Direct GitHub API access, matches request exactly"
  },
  ...
]
```

### scout_connect — connect to a specific server

Prompt: "Connect to github-mcp at https://mcp.example.com/github"

Scout connects and registers the server's tools under the `github_mcp_` prefix:

```python
{
  "status": "connected",
  "name": "github-mcp",
  "url": "https://mcp.example.com/github"
}
```

After connection, the host receives a `tools/list_changed` notification and can immediately call tools like `github_mcp_create_issue` or `github_mcp_list_repos`.

### scout_acquire — find and connect in one step

Prompt: "I need a weather API"

Scout finds, ranks, and connects to the best match in a single call:

```python
{
  "status": "connected",
  "server": "weather-mcp",
  "url": "https://mcp.example.com/weather",
  "score": 0.88,
  "reasoning": "Provides current weather and forecast data via API"
}
```

### scout_list_active — see connected servers

Prompt: "What servers does Scout have connected?"

```python
[
  {"name": "github-mcp", "url": "https://mcp.example.com/github"},
  {"name": "weather-mcp", "url": "https://mcp.example.com/weather"}
]
```

### scout_disconnect — remove a server

Prompt: "Disconnect weather-mcp"

```python
{"status": "disconnected", "name": "weather-mcp"}
```

Scout removes the server's proxied tools and sends a `tools/list_changed` notification.


## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | — | API key for Claude Haiku ranking. Scout exits at startup if not set. |
| `SCOUT_REGISTRY_URL` | No | `https://registry.modelcontextprotocol.io/v0.1/servers` | MCP server registry endpoint. Override for testing or alternate registries. |


## Tools Reference

| Tool | Description |
|------|-------------|
| `scout_find` | Search and rank MCP servers by relevance to a natural language query |
| `scout_connect` | Connect to a remote HTTP MCP server and expose its tools under a namespaced prefix |
| `scout_acquire` | Find, rank, and connect in a single call — the fastest path to new tools |
| `scout_list_active` | List all servers Scout has connected to in the current session |
| `scout_disconnect` | Remove a connected server and its proxied tools |
| `ping` | Health check — returns `"pong"` to confirm Scout is running |
