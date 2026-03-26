"""Tests for scout_connect tool notification wiring in server.py.

Verifies that:
- ToolListChangedNotification is sent when a new server is connected
- No notification is sent on cache hit (already_connected)
- scout_connect returns the result dict from proxy.connect
- scout_connect accepts a ctx: Context parameter
"""

import inspect
from unittest.mock import AsyncMock, patch

import mcp.types
import pytest

import server


class TestNotification:
    def setup_method(self):
        """Reset proxy state before each test."""
        import proxy as proxy_mod

        proxy_mod._connections.clear()
        proxy_mod._urls.clear()

    @pytest.mark.asyncio
    async def test_list_changed_fires_on_new_connection(self):
        """When proxy.connect returns status=connected, ctx.send_notification is called
        with a ToolListChangedNotification instance."""
        from fastmcp.server.context import Context

        mock_ctx = AsyncMock(spec=Context)
        connect_result = {"status": "connected", "name": "test", "url": "https://example.com/mcp"}

        with patch("proxy.connect", new_callable=AsyncMock, return_value=connect_result):
            await server.scout_connect(
                name="test", url="https://example.com/mcp", ctx=mock_ctx
            )

        mock_ctx.send_notification.assert_awaited_once()
        call_args = mock_ctx.send_notification.call_args[0][0]
        assert isinstance(call_args, mcp.types.ToolListChangedNotification)

    @pytest.mark.asyncio
    async def test_no_notification_on_cache_hit(self):
        """When proxy.connect returns status=already_connected, ctx.send_notification
        must NOT be called."""
        from fastmcp.server.context import Context

        mock_ctx = AsyncMock(spec=Context)
        connect_result = {"status": "already_connected", "name": "test", "url": "https://example.com/mcp"}

        with patch("proxy.connect", new_callable=AsyncMock, return_value=connect_result):
            await server.scout_connect(
                name="test", url="https://example.com/mcp", ctx=mock_ctx
            )

        mock_ctx.send_notification.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_scout_connect_returns_connect_result(self):
        """scout_connect should pass through the dict returned by proxy.connect."""
        from fastmcp.server.context import Context

        mock_ctx = AsyncMock(spec=Context)
        expected = {"status": "connected", "name": "myserver", "url": "https://myserver.io/mcp"}

        with patch("proxy.connect", new_callable=AsyncMock, return_value=expected):
            result = await server.scout_connect(
                name="myserver", url="https://myserver.io/mcp", ctx=mock_ctx
            )

        assert result == expected

    def test_scout_connect_accepts_context_param(self):
        """The scout_connect function signature must include a ctx: Context parameter."""
        from fastmcp.server.context import Context

        sig = inspect.signature(server.scout_connect)
        assert "ctx" in sig.parameters, "scout_connect must accept a ctx parameter"
        param = sig.parameters["ctx"]
        assert param.annotation is Context, (
            f"ctx parameter must be annotated as Context, got {param.annotation}"
        )
