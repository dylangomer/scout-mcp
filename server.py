import os
import sys
import httpx
from contextlib import asynccontextmanager
from fastmcp import FastMCP


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


@mcp.tool
async def find_servers(query: str) -> list[dict]:
    """Search the MCP registry for servers matching a query."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            get_registry_url(),
            params={"search": query, "limit": 10},
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


if __name__ == "__main__":
    mcp.run()
