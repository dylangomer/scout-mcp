import httpx
from fastmcp import FastMCP

mcp = FastMCP("Scout")

REGISTRY_URL = "https://registry.modelcontextprotocol.io/v0.1/servers"


@mcp.tool
def ping() -> str:
    """Check that Scout is alive and responding."""
    return "pong — Scout is running!"


@mcp.tool
async def find_servers(query: str) -> list[dict]:
    """Search the MCP registry for servers matching a query."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            REGISTRY_URL,
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
