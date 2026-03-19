"""Tests for scout_list_active and scout_disconnect tools in server.py.

Verifies that:
- scout_list_active returns a list of {name, url} dicts for all connected servers
- scout_list_active returns [] when no servers are connected
- scout_list_active is synchronous (not a coroutine function)
- scout_disconnect removes a server and fires ToolListChangedNotification on success
- scout_disconnect for an unknown server returns not_found without firing notification
- scout_disconnect has the correct signature (server_name: str, ctx: Context)
"""
import asyncio
import inspect
import pytest
from unittest.mock import AsyncMock, patch
import mcp.types

import proxy as proxy_mod
import server


def _reset_cache():
    """Clear the proxy module-level cache before each test to avoid state leakage."""
    proxy_mod._connections.clear()
    proxy_mod._urls.clear()


class TestListActive:
    def setup_method(self):
        """Reset proxy state before each test."""
        _reset_cache()

    def test_list_active_returns_connected_servers(self):
        """When two servers are connected, scout_list_active returns them as a list of dicts."""
        with patch("proxy.get_connections", return_value={"srv1": "https://a.io/mcp", "srv2": "https://b.io/mcp"}):
            result = server.scout_list_active()

        assert result == [
            {"name": "srv1", "url": "https://a.io/mcp"},
            {"name": "srv2", "url": "https://b.io/mcp"},
        ]

    def test_list_active_empty(self):
        """When no servers are connected, scout_list_active returns []."""
        with patch("proxy.get_connections", return_value={}):
            result = server.scout_list_active()

        assert result == []

    def test_list_active_is_sync(self):
        """scout_list_active must be a regular function, not a coroutine function."""
        assert not asyncio.iscoroutinefunction(server.scout_list_active), (
            "scout_list_active must NOT be async — no await is needed"
        )


class TestDisconnect:
    def setup_method(self):
        """Reset proxy state before each test."""
        _reset_cache()

    @pytest.mark.asyncio
    async def test_disconnect_success(self):
        """When proxy.disconnect returns status=disconnected, the result is returned
        and ctx.send_notification is awaited once with a ToolListChangedNotification."""
        from fastmcp.server.context import Context

        mock_ctx = AsyncMock(spec=Context)
        disconnect_result = {"status": "disconnected", "name": "srv1"}

        with patch("proxy.disconnect", return_value=disconnect_result):
            result = await server.scout_disconnect(server_name="srv1", ctx=mock_ctx)

        assert result == disconnect_result
        mock_ctx.send_notification.assert_awaited_once()
        call_args = mock_ctx.send_notification.call_args[0][0]
        assert isinstance(call_args, mcp.types.ToolListChangedNotification)

    @pytest.mark.asyncio
    async def test_disconnect_not_found_no_notification(self):
        """When proxy.disconnect returns status=not_found, no notification is fired."""
        from fastmcp.server.context import Context

        mock_ctx = AsyncMock(spec=Context)
        disconnect_result = {"status": "not_found", "name": "unknown"}

        with patch("proxy.disconnect", return_value=disconnect_result):
            result = await server.scout_disconnect(server_name="unknown", ctx=mock_ctx)

        assert result == disconnect_result
        mock_ctx.send_notification.assert_not_awaited()

    def test_disconnect_signature(self):
        """scout_disconnect must accept server_name: str and ctx: Context parameters."""
        from fastmcp.server.context import Context

        sig = inspect.signature(server.scout_disconnect)
        assert "server_name" in sig.parameters, "scout_disconnect must accept a server_name parameter"
        assert "ctx" in sig.parameters, "scout_disconnect must accept a ctx parameter"

        server_name_param = sig.parameters["server_name"]
        assert server_name_param.annotation is str, (
            f"server_name must be annotated as str, got {server_name_param.annotation}"
        )

        ctx_param = sig.parameters["ctx"]
        assert ctx_param.annotation is Context, (
            f"ctx parameter must be annotated as Context, got {ctx_param.annotation}"
        )
