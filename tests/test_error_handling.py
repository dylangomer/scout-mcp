"""Tests for error handling in scout_find and scout_acquire.

Verifies that RuntimeError from search_registry is caught and returned as a
structured error dict instead of propagating to FastMCP's generic ToolError wrapper.
"""
import pytest
from unittest.mock import AsyncMock, patch
from fastmcp.server.context import Context

import server


class TestScoutFindErrorHandling:
    """PLSH-01: scout_find returns structured error dict on registry failure."""

    @pytest.mark.asyncio
    async def test_registry_unreachable_returns_error_dict(self):
        """When search_registry raises RuntimeError, scout_find returns error dict (not exception)."""
        error_msg = "Registry unreachable at https://registry.modelcontextprotocol.io/v0.1/servers"

        with patch.object(server, "search_registry", AsyncMock(side_effect=RuntimeError(error_msg))):
            result = await server.scout_find("project management tools")

        assert isinstance(result, dict), (
            f"Expected dict, got {type(result).__name__}: {result!r}"
        )
        assert result["status"] == "error", f"Expected status='error', got {result}"
        assert result["message"] == error_msg, (
            f"Expected message={error_msg!r}, got {result.get('message')!r}"
        )

    @pytest.mark.asyncio
    async def test_unexpected_error_returns_error_dict(self):
        """When an unexpected Exception occurs, scout_find returns error dict with prefixed message."""
        with patch.object(server, "search_registry", AsyncMock(side_effect=ValueError("bad data"))):
            result = await server.scout_find("any context")

        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert "Unexpected error during search" in result["message"]
        assert "bad data" in result["message"]


class TestScoutAcquireErrorHandling:
    """PLSH-01: scout_acquire returns structured error dict on registry failure."""

    @pytest.mark.asyncio
    async def test_registry_unreachable_returns_error_dict(self):
        """When search_registry raises RuntimeError, scout_acquire returns error dict (not exception)."""
        mock_ctx = AsyncMock(spec=Context)
        error_msg = "Registry unreachable at https://registry.modelcontextprotocol.io/v0.1/servers"

        with patch.object(server, "search_registry", AsyncMock(side_effect=RuntimeError(error_msg))):
            result = await server.scout_acquire("weather tools", mock_ctx)

        assert isinstance(result, dict), (
            f"Expected dict, got {type(result).__name__}: {result!r}"
        )
        assert result["status"] == "error", f"Expected status='error', got {result}"
        assert result["message"] == error_msg, (
            f"Expected message={error_msg!r}, got {result.get('message')!r}"
        )

    @pytest.mark.asyncio
    async def test_notification_not_sent_on_error(self):
        """When search_registry raises RuntimeError, ctx.send_notification is NOT called."""
        mock_ctx = AsyncMock(spec=Context)
        error_msg = "Registry unreachable at https://registry.modelcontextprotocol.io/v0.1/servers"

        with patch.object(server, "search_registry", AsyncMock(side_effect=RuntimeError(error_msg))):
            await server.scout_acquire("weather tools", mock_ctx)

        mock_ctx.send_notification.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_unexpected_error_returns_error_dict(self):
        """When an unexpected Exception occurs, scout_acquire returns error dict with prefixed message."""
        mock_ctx = AsyncMock(spec=Context)

        with patch.object(server, "search_registry", AsyncMock(side_effect=ConnectionError("network down"))):
            result = await server.scout_acquire("any context", mock_ctx)

        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert "Unexpected error during acquire" in result["message"]
        assert "network down" in result["message"]
