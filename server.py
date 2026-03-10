from fastmcp import FastMCP

mcp = FastMCP("Scout")


@mcp.tool
def ping() -> str:
    """Check that Scout is alive and responding."""
    return "pong — Scout is running!"


if __name__ == "__main__":
    mcp.run()
