"""Tests for proxy.py — ProxyConnectionManager: connect, is_connected, disconnect, get_connections."""
from unittest.mock import patch, MagicMock

import pytest
from fastmcp import FastMCP

import proxy as proxy_mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

URL1 = "https://server1.example.com/mcp"
URL2 = "https://server2.example.com/mcp"
URL3 = "https://server3.example.com/mcp"


def _fresh_mcp():
    """Return a fresh FastMCP instance isolated from other tests."""
    return FastMCP("test")


def _reset_cache():
    """Clear module-level connection cache between tests."""
    proxy_mod._connections.clear()
    proxy_mod._urls.clear()


# ---------------------------------------------------------------------------
# TestConnect
# ---------------------------------------------------------------------------

class TestConnect:
    """PRXY-01: connect() registers a ProxyProvider on the FastMCP instance."""

    async def test_connect_adds_provider(self):
        """connect("myserver", url, mcp) adds a provider to mcp.providers and returns connected status."""
        _reset_cache()
        mcp = _fresh_mcp()
        initial_count = len(mcp.providers)

        result = proxy_mod.connect("myserver", URL1, mcp)

        assert result == {"status": "connected", "name": "myserver", "url": URL1}
        assert len(mcp.providers) == initial_count + 1

    async def test_connect_uses_non_deprecated_import(self):
        """proxy.py must import ProxyProvider from fastmcp.server.providers.proxy (not fastmcp.server.proxy)."""
        import ast
        import inspect

        source = inspect.getsource(proxy_mod)
        tree = ast.parse(source)

        deprecated_path = "fastmcp.server.proxy"
        canonical_path = "fastmcp.server.providers.proxy"

        # Walk all import nodes and verify deprecated path is not used
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert deprecated_path != module, (
                    f"proxy.py uses deprecated import path '{deprecated_path}'. "
                    f"Use '{canonical_path}' instead."
                )

    async def test_connect_binds_url_in_lambda(self):
        """ProxyProvider factory binds URL at creation time (no lambda closure trap)."""
        _reset_cache()
        mcp = _fresh_mcp()

        # Connect two servers with different URLs
        proxy_mod.connect("server1", URL1, mcp)
        proxy_mod.connect("server2", URL2, mcp)

        # Verify both providers were registered (not just one)
        assert len(mcp.providers) >= 2

        # Retrieve the raw providers from the cache and verify they have distinct factory outputs
        provider1 = proxy_mod._connections["server1"]
        provider2 = proxy_mod._connections["server2"]

        # Each provider's client_factory should produce a client bound to its specific URL
        client1 = provider1._client_factory()
        client2 = provider2._client_factory()

        assert client1._url != client2._url, (
            f"Lambda closure bug: both providers use the same URL ({client1._url}). "
            "Use 'lambda u=url: ProxyClient(u)' to bind at creation time."
        )


# ---------------------------------------------------------------------------
# TestNamespace
# ---------------------------------------------------------------------------

class TestNamespace:
    """PRXY-02: connect() calls mcp.add_provider with namespace=name."""

    async def test_namespace_applied(self):
        """connect() passes namespace=name to mcp.add_provider."""
        _reset_cache()
        mcp = _fresh_mcp()
        calls = []

        original_add_provider = mcp.add_provider

        def spy_add_provider(provider, namespace=None, **kwargs):
            calls.append({"provider": provider, "namespace": namespace})
            return original_add_provider(provider, namespace=namespace, **kwargs)

        with patch.object(mcp, "add_provider", side_effect=spy_add_provider):
            proxy_mod.connect("myserver", URL1, mcp)

        assert len(calls) == 1
        assert calls[0]["namespace"] == "myserver", (
            f"Expected namespace='myserver', got namespace={calls[0]['namespace']!r}"
        )


# ---------------------------------------------------------------------------
# TestCache
# ---------------------------------------------------------------------------

class TestCache:
    """PRXY-04: In-memory cache prevents re-connecting to the same server."""

    async def test_cache_prevents_reconnect(self):
        """Calling connect() twice with the same name returns already_connected on the second call."""
        _reset_cache()
        mcp = _fresh_mcp()
        calls = []

        original_add_provider = mcp.add_provider

        def spy_add_provider(provider, namespace=None, **kwargs):
            calls.append(namespace)
            return original_add_provider(provider, namespace=namespace, **kwargs)

        with patch.object(mcp, "add_provider", side_effect=spy_add_provider):
            result1 = proxy_mod.connect("myserver", URL1, mcp)
            result2 = proxy_mod.connect("myserver", URL2, mcp)

        assert result1["status"] == "connected"
        assert result2 == {"status": "already_connected", "name": "myserver", "url": URL1}
        assert len(calls) == 1, (
            f"add_provider was called {len(calls)} times; expected exactly 1 (cache should block second call)"
        )

    async def test_is_connected_true(self):
        """is_connected('myserver') returns True after connect('myserver', ...)."""
        _reset_cache()
        mcp = _fresh_mcp()
        proxy_mod.connect("myserver", URL1, mcp)

        assert proxy_mod.is_connected("myserver") is True

    async def test_is_connected_false(self):
        """is_connected('unknown') returns False for a name that was never connected."""
        _reset_cache()

        assert proxy_mod.is_connected("unknown") is False


# ---------------------------------------------------------------------------
# TestDisconnect
# ---------------------------------------------------------------------------

class TestDisconnect:
    """disconnect() removes the provider from mcp.providers and clears cache."""

    async def test_disconnect_removes_provider(self):
        """disconnect('myserver', mcp) removes the provider from mcp.providers and clears the cache."""
        _reset_cache()
        mcp = _fresh_mcp()
        initial_count = len(mcp.providers)

        proxy_mod.connect("myserver", URL1, mcp)
        assert len(mcp.providers) == initial_count + 1

        result = proxy_mod.disconnect("myserver", mcp)

        assert result == {"status": "disconnected", "name": "myserver"}
        assert len(mcp.providers) == initial_count
        assert proxy_mod.is_connected("myserver") is False

    async def test_disconnect_unknown_returns_not_found(self):
        """disconnect('unknown', mcp) returns {'status': 'not_found'} when name is not connected."""
        _reset_cache()
        mcp = _fresh_mcp()

        result = proxy_mod.disconnect("unknown", mcp)

        assert result == {"status": "not_found", "name": "unknown"}


# ---------------------------------------------------------------------------
# TestGetConnections
# ---------------------------------------------------------------------------

class TestGetConnections:
    """get_connections() returns a name->url mapping for all active connections."""

    async def test_get_connections_returns_name_url_map(self):
        """After connecting two servers, get_connections() returns {server1: url1, server2: url2}."""
        _reset_cache()
        mcp = _fresh_mcp()
        proxy_mod.connect("server1", URL1, mcp)
        proxy_mod.connect("server2", URL2, mcp)

        result = proxy_mod.get_connections()

        assert result == {"server1": URL1, "server2": URL2}

    async def test_get_connections_empty(self):
        """Before any connections, get_connections() returns {}."""
        _reset_cache()

        result = proxy_mod.get_connections()

        assert result == {}
