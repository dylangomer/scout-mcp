"""Proxy connection manager — connect, disconnect, cache, and namespace remote MCP servers."""

import logging

from fastmcp import FastMCP
from fastmcp.server.providers.proxy import ProxyClient, ProxyProvider

log = logging.getLogger(__name__)

# Module-level state: maps server name to raw ProxyProvider and its URL.
_connections: dict[str, ProxyProvider] = {}
_urls: dict[str, str] = {}


def connect(name: str, url: str, app: FastMCP) -> dict:
    """Connect to a remote MCP server and register it as a namespaced provider.

    If the server is already connected at the same URL, returns already_connected.
    If the name is cached but the URL differs, disconnects the old server and reconnects.
    Returns {"status": "connected", "name": name, "url": url} on success.
    """
    if name in _connections:
        if _urls[name] == url:
            return {"status": "already_connected", "name": name, "url": _urls[name]}
        # Same name, different URL — reconnect to the new endpoint.
        log.info("Reconnecting '%s': URL changed from %s to %s", name, _urls[name], url)
        disconnect(name, app)
    # Bind url via default argument to avoid lambda closure trap
    provider = ProxyProvider(lambda u=url: ProxyClient(u))
    app.add_provider(provider, namespace=name)
    _connections[name] = provider
    _urls[name] = url
    return {"status": "connected", "name": name, "url": url}


def is_connected(name: str) -> bool:
    """Return True if the named server is currently connected."""
    return name in _connections


def disconnect(name: str, app: FastMCP) -> dict:
    """Disconnect a previously connected server and remove it from the provider list.

    Returns {"status": "disconnected", "name": name} on success.
    Returns {"status": "not_found", "name": name} if the server is not connected.
    """
    if name not in _connections:
        return {"status": "not_found", "name": name}

    raw_provider = _connections[name]

    # Find the wrapped provider entry in app.providers.
    # FastMCP wraps the raw ProxyProvider in a _WrappedProvider when namespace= is applied.
    # The wrapped entry stores the original via its ._inner attribute.
    wrapped_entry = None
    for entry in app.providers:
        if getattr(entry, "_inner", None) is raw_provider:
            wrapped_entry = entry
            break

    if wrapped_entry is not None:
        app.providers.remove(wrapped_entry)
    else:
        log.warning(
            "Provider for '%s' not found in app.providers — "
            "cache cleared but provider may leak",
            name,
        )

    del _connections[name]
    del _urls[name]
    return {"status": "disconnected", "name": name}


def get_connections() -> dict[str, str]:
    """Return a copy of the name->url mapping for all active connections."""
    return dict(_urls)
