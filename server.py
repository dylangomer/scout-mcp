"""Scout MCP server — AI-powered dynamic MCP server discovery gateway.

Exposes tools to search the MCP registry, rank servers by relevance using
Claude Haiku, and connect to remote servers on-the-fly.
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager

import httpx
import mcp.types as mcp_types
from fastmcp import FastMCP
from fastmcp.server.context import Context

import proxy
from ranker import filter_http_servers, rank_servers
from schemas import ConnectionInfo, RegistryServer, ScoredServer

log = logging.getLogger(__name__)

DEFAULT_REGISTRY_URL = "https://registry.modelcontextprotocol.io/v0.1/servers"
REGISTRY_SEARCH_LIMIT = 20
REGISTRY_TIMEOUT_SECONDS = 15


def get_registry_url() -> str:
    """Return the registry URL, respecting the SCOUT_REGISTRY_URL environment variable."""
    return os.environ.get("SCOUT_REGISTRY_URL", DEFAULT_REGISTRY_URL)


@asynccontextmanager
async def app_lifespan(_app):
    """FastMCP lifespan: validate required environment variables at startup."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        log.error(
            "ANTHROPIC_API_KEY is required but not set. "
            "Set the environment variable before starting Scout.",
        )
        sys.exit(1)
    yield


app = FastMCP("Scout", lifespan=app_lifespan)


@app.tool
def ping() -> str:
    """Check that Scout is alive and responding."""
    return "pong — Scout is running!"


async def search_registry(query: str) -> list[RegistryServer]:
    """Search the MCP registry with one retry on failure."""
    for attempt in range(2):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    get_registry_url(),
                    params={"search": query, "limit": REGISTRY_SEARCH_LIMIT},
                    timeout=REGISTRY_TIMEOUT_SECONDS,
                )
                resp.raise_for_status()
            servers: list[RegistryServer] = []
            for entry in resp.json().get("servers", []):
                srv = entry.get("server", {})
                remotes = srv.get("remotes", [])
                servers.append(RegistryServer(
                    name=srv.get("name", "unknown"),
                    description=srv.get("description", ""),
                    remote_url=remotes[0]["url"] if remotes else None,
                ))
            return servers
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            if attempt == 0:
                log.warning("Registry request failed, retrying: %s", e)
                await asyncio.sleep(0.5)
                continue
            raise RuntimeError(
                f"Registry unreachable at {get_registry_url()}"
            ) from e


@app.tool
async def scout_find(context: str, max_results: int = 5) -> list[ScoredServer]:
    """Find and rank MCP servers matching your needs.

    Searches the MCP registry, filters to HTTP-reachable servers,
    and ranks them by relevance using AI.
    """
    raw = await search_registry(context)
    http_servers = filter_http_servers(raw)
    ranked = await rank_servers(context, http_servers)
    return ranked[:max_results]


@app.tool
async def scout_connect(name: str, url: str, ctx: Context) -> dict:
    """Connect to a remote MCP server and expose its tools.

    Registers the server's tools under a namespaced prefix (server_name_tool_name)
    to prevent collisions. Fires a tools/list_changed notification so the host
    discovers the new tools immediately.

    Returns instantly from cache if the server is already connected.
    """
    result = proxy.connect(name, url, app)
    if result["status"] == "connected":
        await ctx.send_notification(mcp_types.ToolListChangedNotification())
    return result


@app.tool
def scout_list_active() -> list[ConnectionInfo]:
    """List all MCP servers Scout has connected to in this session."""
    return [
        ConnectionInfo(name=name, url=url)
        for name, url in proxy.get_connections().items()
    ]


@app.tool
async def scout_disconnect(server_name: str, ctx: Context) -> dict:
    """Disconnect a server and remove its tools from the host's tool list."""
    result = proxy.disconnect(server_name, app)
    if result["status"] == "disconnected":
        await ctx.send_notification(mcp_types.ToolListChangedNotification())
    return result


@app.tool
async def scout_acquire(context: str, ctx: Context) -> dict:
    """Find the best MCP server for a task and connect to it immediately."""
    try:
        raw = await search_registry(context)
        http_servers = filter_http_servers(raw)
        if not http_servers:
            return {"status": "no_servers_found", "context": context}
        ranked = await rank_servers(context, http_servers)
        if not ranked:
            return {"status": "no_servers_found", "context": context}
        top = ranked[0]
        result = proxy.connect(top["name"], top["remote_url"], app)
        if result["status"] == "connected":
            await ctx.send_notification(mcp_types.ToolListChangedNotification())
        return {
            "status": result["status"],
            "server": top["name"],
            "url": top["remote_url"],
            "score": top.get("score"),
            "reasoning": top.get("reasoning"),
        }
    except RuntimeError as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    app.run()
