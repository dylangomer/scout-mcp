"""Tests for error handling in scout_find and scout_acquire.

scout_find: errors propagate naturally — FastMCP wraps them as ToolError.
scout_acquire: catches RuntimeError and returns a structured error dict;
    unexpected exceptions propagate to FastMCP.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastmcp.server.context import Context

import server


class TestScoutFindErrorHandling:
    """scout_find lets exceptions propagate (no internal catch)."""

    async def test_registry_unreachable_raises(self):
        """When search_registry raises RuntimeError, it propagates from scout_find."""
        with (
            patch.object(server, "search_registry", AsyncMock(side_effect=RuntimeError("Registry unreachable"))),
            pytest.raises(RuntimeError, match="Registry unreachable"),
        ):
            await server.scout_find("project management tools")

    async def test_unexpected_error_raises(self):
        """When an unexpected exception occurs, it propagates from scout_find."""
        with (
            patch.object(server, "search_registry", AsyncMock(side_effect=ValueError("bad data"))),
            pytest.raises(ValueError, match="bad data"),
        ):
            await server.scout_find("any context")


class TestScoutAcquireErrorHandling:
    """scout_acquire catches RuntimeError; other exceptions propagate."""

    @pytest.mark.asyncio
    async def test_registry_unreachable_returns_error_dict(self):
        """When search_registry raises RuntimeError, scout_acquire returns error dict."""
        mock_ctx = AsyncMock(spec=Context)
        error_msg = "Registry unreachable at https://registry.modelcontextprotocol.io/v0.1/servers"

        with patch.object(server, "search_registry", AsyncMock(side_effect=RuntimeError(error_msg))):
            result = await server.scout_acquire("weather tools", mock_ctx)

        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert result["message"] == error_msg

    @pytest.mark.asyncio
    async def test_notification_not_sent_on_error(self):
        """When search_registry raises RuntimeError, ctx.send_notification is NOT called."""
        mock_ctx = AsyncMock(spec=Context)

        with patch.object(server, "search_registry", AsyncMock(side_effect=RuntimeError("down"))):
            await server.scout_acquire("weather tools", mock_ctx)

        mock_ctx.send_notification.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_unexpected_error_propagates(self):
        """Unexpected exceptions (non-RuntimeError) propagate from scout_acquire."""
        mock_ctx = AsyncMock(spec=Context)

        with (
            patch.object(server, "search_registry", AsyncMock(side_effect=ConnectionError("network down"))),
            pytest.raises(ConnectionError, match="network down"),
        ):
            await server.scout_acquire("any context", mock_ctx)
