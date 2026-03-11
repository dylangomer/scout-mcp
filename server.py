import asyncio
import os
import sys
import httpx
from contextlib import asynccontextmanager
from fastmcp import FastMCP
from fastmcp.server.context import Context

import mcp.types as mcp_types
import proxy
from ranker import filter_http_servers, rank_servers


def get_registry_url() -> str:
    """Return the registry URL, respecting the SCOUT_REGISTRY_URL environment variable."""
    return os.environ.get(
        "SCOUT_REGISTRY_URL",
        "https://registry.modelcontextprotocol.io/v0.1/servers",
    )


# Module-level constant kept for backward compatibility; use get_registry_url() at call sites.
REGISTRY_URL = get_registry_url()


@asynccontextmanager
async def app_lifespan(server):
    """FastMCP lifespan: validate required environment variables at startup."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "ERROR: ANTHROPIC_API_KEY is required but not set. "
            "Set the environment variable before starting Scout.",
            file=sys.stderr,
        )
        sys.exit(1)
    yield


mcp = FastMCP("Scout", lifespan=app_lifespan)


@mcp.tool
def ping() -> str:
    """Check that Scout is alive and responding."""
    return "pong — Scout is running!"


async def search_registry(query: str) -> list[dict]:
    """Search the MCP registry with one retry on failure."""
    for attempt in range(2):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    get_registry_url(),
                    params={"search": query, "limit": 20},
                    timeout=15,
                )
                resp.raise_for_status()
            servers = []
            for entry in resp.json().get("servers", []):
                server = entry.get("server", {})
                remotes = server.get("remotes", [])
                servers.append({
                    "name": server.get("name", "unknown"),
                    "description": server.get("description", ""),
                    "remote_url": remotes[0]["url"] if remotes else None,
                })
            return servers
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            if attempt == 0:
                await asyncio.sleep(0.5)
                continue
            raise RuntimeError(
                f"Registry unreachable at {get_registry_url()}"
            ) from e


@mcp.tool
async def scout_find(context: str, max_results: int = 5) -> list[dict]:
    """Find and rank MCP servers matching your needs.

    Searches the MCP registry, filters to HTTP-reachable servers,
    and ranks them by relevance using AI.
    """
    # Step 1: Search registry
    raw = await search_registry(context)
    # Step 2: Filter — keep only HTTP-reachable servers
    http_servers = filter_http_servers(raw)
    # Step 3: Rank with Haiku (or fall back to unranked)
    ranked = await rank_servers(context, http_servers)
    # Step 4: Limit results
    return ranked[:max_results]


@mcp.tool
async def scout_connect(name: str, url: str, ctx: Context) -> dict:
    """Connect to a remote MCP server and expose its tools.

    Registers the server's tools under a namespaced prefix (server_name_tool_name)
    to prevent collisions. Fires a tools/list_changed notification so the host
    discovers the new tools immediately.

    Returns instantly from cache if the server is already connected.
    """
    result = proxy.connect(name, url, mcp)
    if result["status"] == "connected":
        await ctx.send_notification(mcp_types.ToolListChangedNotification())
    return result


if __name__ == "__main__":
    mcp.run()
