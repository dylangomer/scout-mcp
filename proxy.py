"""Proxy connection manager — connect, disconnect, cache, and namespace remote MCP servers."""
from fastmcp.server.providers.proxy import ProxyProvider, ProxyClient

# Module-level state: maps server name to raw ProxyProvider and its URL.
_connections: dict[str, ProxyProvider] = {}
_urls: dict[str, str] = {}


def connect(name: str, url: str, mcp) -> dict:
    """Connect to a remote MCP server and register it as a namespaced provider.

    If the server is already connected, returns immediately with already_connected status.
    Returns {"status": "connected", "name": name, "url": url} on success.
    """
    if name in _connections:
        return {"status": "already_connected", "name": name, "url": _urls[name]}
    # Bind url via default argument to avoid lambda closure trap
    provider = ProxyProvider(lambda u=url: ProxyClient(u))
    mcp.add_provider(provider, namespace=name)
    _connections[name] = provider
    _urls[name] = url
    return {"status": "connected", "name": name, "url": url}


def is_connected(name: str) -> bool:
    """Return True if the named server is currently connected."""
    return name in _connections


def disconnect(name: str, mcp) -> dict:
    """Disconnect a previously connected server and remove it from the provider list.

    Returns {"status": "disconnected", "name": name} on success.
    Returns {"status": "not_found", "name": name} if the server is not connected.
    """
    if name not in _connections:
        return {"status": "not_found", "name": name}

    raw_provider = _connections[name]

    # Find the wrapped provider entry in mcp.providers.
    # FastMCP wraps the raw ProxyProvider in a _WrappedProvider when namespace= is applied.
    # The wrapped entry stores the original via its ._inner attribute.
    wrapped_entry = None
    for entry in mcp.providers:
        if getattr(entry, "_inner", None) is raw_provider:
            wrapped_entry = entry
            break

    if wrapped_entry is not None:
        mcp.providers.remove(wrapped_entry)

    del _connections[name]
    del _urls[name]
    return {"status": "disconnected", "name": name}


def get_connections() -> dict[str, str]:
    """Return a copy of the name->url mapping for all active connections."""
    return dict(_urls)
