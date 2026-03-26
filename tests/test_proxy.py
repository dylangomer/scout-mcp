"""Tests for proxy.py — connect, is_connected, disconnect, get_connections."""

from unittest.mock import AsyncMock, MagicMock, patch

import proxy as proxy_mod

URL1 = "https://server1.example.com/mcp"
URL2 = "https://server2.example.com/mcp"


def _mock_reachable():
    """Return a patch that makes ProxyClient.__aenter__/__aexit__ succeed instantly."""
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return patch("proxy.ProxyClient", return_value=mock_client)


def _mock_unreachable(error_msg="Connection refused"):
    """Return a patch that makes ProxyClient.__aenter__ raise."""
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(side_effect=RuntimeError(error_msg))
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return patch("proxy.ProxyClient", return_value=mock_client)


# ---------------------------------------------------------------------------
# TestConnect
# ---------------------------------------------------------------------------


class TestConnect:
    """PRXY-01: connect() registers a ProxyProvider on the FastMCP instance."""

    async def test_connect_adds_provider(self, clean_proxy_cache, fresh_app):
        """connect("myserver", url, app) adds a provider and returns connected status."""
        initial_count = len(fresh_app.providers)

        with _mock_reachable():
            result = await proxy_mod.connect("myserver", URL1, fresh_app)

        assert result == {"status": "connected", "name": "myserver", "url": URL1}
        assert len(fresh_app.providers) == initial_count + 1

    async def test_connect_uses_non_deprecated_import(self):
        """proxy.py must import ProxyProvider from fastmcp.server.providers.proxy."""
        import ast
        import inspect

        source = inspect.getsource(proxy_mod)
        tree = ast.parse(source)

        deprecated_path = "fastmcp.server.proxy"
        canonical_path = "fastmcp.server.providers.proxy"

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert deprecated_path != module, (
                    f"proxy.py uses deprecated import path '{deprecated_path}'. "
                    f"Use '{canonical_path}' instead."
                )

    async def test_connect_binds_url_in_lambda(self, clean_proxy_cache, fresh_app):
        """ProxyProvider factory binds URL at creation time (no lambda closure trap)."""
        with _mock_reachable():
            await proxy_mod.connect("server1", URL1, fresh_app)
            await proxy_mod.connect("server2", URL2, fresh_app)

        assert len(fresh_app.providers) >= 2

        provider1 = proxy_mod._connections["server1"]
        provider2 = proxy_mod._connections["server2"]

        client1 = provider1.client_factory()
        client2 = provider2.client_factory()

        url_attr1 = str(client1.transport.url)
        url_attr2 = str(client2.transport.url)

        assert url_attr1 != url_attr2, (
            f"Lambda closure bug: both providers use the same URL ({url_attr1}). "
            "Use 'lambda u=url: ProxyClient(u)' to bind at creation time."
        )

    async def test_connect_returns_error_on_unreachable(self, clean_proxy_cache, fresh_app):
        """connect() returns error status and does NOT cache when server is unreachable."""
        initial_count = len(fresh_app.providers)

        with _mock_unreachable("Connection refused"):
            result = await proxy_mod.connect("badserver", URL1, fresh_app)

        assert result["status"] == "error"
        assert result["name"] == "badserver"
        assert "Connection refused" in result["message"]
        assert len(fresh_app.providers) == initial_count
        assert not proxy_mod.is_connected("badserver")


# ---------------------------------------------------------------------------
# TestNamespace
# ---------------------------------------------------------------------------


class TestNamespace:
    """PRXY-02: connect() calls app.add_provider with namespace=name."""

    async def test_namespace_applied(self, clean_proxy_cache, fresh_app):
        """connect() passes namespace=name to app.add_provider."""
        calls = []

        original_add_provider = fresh_app.add_provider

        def spy_add_provider(provider, namespace=None, **kwargs):
            calls.append({"provider": provider, "namespace": namespace})
            return original_add_provider(provider, namespace=namespace, **kwargs)

        with _mock_reachable(), patch.object(
            fresh_app, "add_provider", side_effect=spy_add_provider
        ):
            await proxy_mod.connect("myserver", URL1, fresh_app)

        assert len(calls) == 1
        assert calls[0]["namespace"] == "myserver", (
            f"Expected namespace='myserver', got namespace={calls[0]['namespace']!r}"
        )


# ---------------------------------------------------------------------------
# TestCache
# ---------------------------------------------------------------------------


class TestCache:
    """PRXY-04: In-memory cache prevents re-connecting to the same server."""

    async def test_cache_prevents_reconnect(self, clean_proxy_cache, fresh_app):
        """Calling connect() twice with the same name and URL returns already_connected."""
        calls = []

        original_add_provider = fresh_app.add_provider

        def spy_add_provider(provider, namespace=None, **kwargs):
            calls.append(namespace)
            return original_add_provider(provider, namespace=namespace, **kwargs)

        with _mock_reachable(), patch.object(
            fresh_app, "add_provider", side_effect=spy_add_provider
        ):
            result1 = await proxy_mod.connect("myserver", URL1, fresh_app)
            result2 = await proxy_mod.connect("myserver", URL1, fresh_app)

        assert result1["status"] == "connected"
        assert result2 == {"status": "already_connected", "name": "myserver", "url": URL1}
        assert len(calls) == 1, (
            f"add_provider was called {len(calls)} times; expected exactly 1"
        )

    async def test_cache_reconnects_on_different_url(self, clean_proxy_cache, fresh_app):
        """Calling connect() with the same name but a different URL disconnects and reconnects."""
        with _mock_reachable():
            result1 = await proxy_mod.connect("myserver", URL1, fresh_app)
            assert result1["status"] == "connected"

            result2 = await proxy_mod.connect("myserver", URL2, fresh_app)
            assert result2["status"] == "connected"
            assert result2["url"] == URL2
            assert proxy_mod._urls["myserver"] == URL2

    async def test_cache_reconnect_removes_old_provider(self, clean_proxy_cache, fresh_app):
        """Reconnecting to a different URL removes the old provider before adding new one."""
        initial_count = len(fresh_app.providers)

        with _mock_reachable():
            await proxy_mod.connect("myserver", URL1, fresh_app)
            assert len(fresh_app.providers) == initial_count + 1

            await proxy_mod.connect("myserver", URL2, fresh_app)
            # Old provider removed, new provider added — count stays the same
            assert len(fresh_app.providers) == initial_count + 1

    async def test_is_connected_true(self, clean_proxy_cache, fresh_app):
        """is_connected('myserver') returns True after connect('myserver', ...)."""
        with _mock_reachable():
            await proxy_mod.connect("myserver", URL1, fresh_app)

        assert proxy_mod.is_connected("myserver") is True

    async def test_is_connected_false(self, clean_proxy_cache):
        """is_connected('unknown') returns False for a name that was never connected."""
        assert proxy_mod.is_connected("unknown") is False


# ---------------------------------------------------------------------------
# TestDisconnect
# ---------------------------------------------------------------------------


class TestDisconnect:
    """disconnect() removes the provider from app.providers and clears cache."""

    async def test_disconnect_removes_provider(self, clean_proxy_cache, fresh_app):
        """disconnect('myserver', app) removes the provider and clears the cache."""
        initial_count = len(fresh_app.providers)

        with _mock_reachable():
            await proxy_mod.connect("myserver", URL1, fresh_app)
        assert len(fresh_app.providers) == initial_count + 1

        result = proxy_mod.disconnect("myserver", fresh_app)

        assert result == {"status": "disconnected", "name": "myserver"}
        assert len(fresh_app.providers) == initial_count
        assert proxy_mod.is_connected("myserver") is False

    async def test_disconnect_unknown_returns_not_found(self, clean_proxy_cache, fresh_app):
        """disconnect('unknown', app) returns not_found when name is not connected."""
        result = proxy_mod.disconnect("unknown", fresh_app)

        assert result == {"status": "not_found", "name": "unknown"}


# ---------------------------------------------------------------------------
# TestGetConnections
# ---------------------------------------------------------------------------


class TestGetConnections:
    """get_connections() returns a name->url mapping for all active connections."""

    async def test_get_connections_returns_name_url_map(self, clean_proxy_cache, fresh_app):
        """After connecting two servers, get_connections() returns both."""
        with _mock_reachable():
            await proxy_mod.connect("server1", URL1, fresh_app)
            await proxy_mod.connect("server2", URL2, fresh_app)

        result = proxy_mod.get_connections()

        assert result == {"server1": URL1, "server2": URL2}

    async def test_get_connections_empty(self, clean_proxy_cache):
        """Before any connections, get_connections() returns {}."""
        result = proxy_mod.get_connections()

        assert result == {}
