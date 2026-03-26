"""Tests for scout_acquire tool — full pipeline: search, filter, rank, connect, notify."""

import inspect
from unittest.mock import AsyncMock, patch

import mcp.types
import pytest

import server


class TestScoutAcquire:
    def setup_method(self):
        """Reset proxy state before each test."""
        import proxy as proxy_mod

        proxy_mod._connections.clear()
        proxy_mod._urls.clear()

    @pytest.mark.asyncio
    async def test_acquire_connects_top_server(self):
        """Happy path: scout_acquire searches, ranks, connects top server, fires notification."""
        from fastmcp.server.context import Context

        mock_ctx = AsyncMock(spec=Context)

        registry_servers = [
            {"name": "weather-mcp", "description": "Weather tools", "remote_url": "https://weather.example.com/mcp"},
        ]
        ranked_servers = [
            {
                "name": "weather-mcp",
                "description": "Weather tools",
                "remote_url": "https://weather.example.com/mcp",
                "score": 95,
                "reasoning": "Best weather MCP server",
                "ranked": True,
            }
        ]
        connect_result = {
            "status": "connected",
            "name": "weather-mcp",
            "url": "https://weather.example.com/mcp",
        }

        with (
            patch("server.search_registry", AsyncMock(return_value=registry_servers)),
            patch("server.rank_servers", AsyncMock(return_value=ranked_servers)),
            patch("proxy.connect", new_callable=AsyncMock, return_value=connect_result),
        ):
            result = await server.scout_acquire("weather tools", mock_ctx)

        assert result["status"] == "connected"
        assert result["server"] == "weather-mcp"
        assert result["url"] == "https://weather.example.com/mcp"
        assert result["score"] == 95
        assert result["reasoning"] == "Best weather MCP server"

        mock_ctx.send_notification.assert_awaited_once()
        call_args = mock_ctx.send_notification.call_args[0][0]
        assert isinstance(call_args, mcp.types.ToolListChangedNotification)

    @pytest.mark.asyncio
    async def test_acquire_cache_hit_no_notification(self):
        """Cache hit: when top server is already connected, no notification is fired."""
        from fastmcp.server.context import Context

        mock_ctx = AsyncMock(spec=Context)

        registry_servers = [
            {"name": "weather-mcp", "description": "Weather tools", "remote_url": "https://weather.example.com/mcp"},
        ]
        ranked_servers = [
            {
                "name": "weather-mcp",
                "description": "Weather tools",
                "remote_url": "https://weather.example.com/mcp",
                "score": 95,
                "reasoning": "Best weather MCP server",
                "ranked": True,
            }
        ]
        connect_result = {
            "status": "already_connected",
            "name": "weather-mcp",
            "url": "https://weather.example.com/mcp",
        }

        with (
            patch("server.search_registry", AsyncMock(return_value=registry_servers)),
            patch("server.rank_servers", AsyncMock(return_value=ranked_servers)),
            patch("proxy.connect", new_callable=AsyncMock, return_value=connect_result),
        ):
            result = await server.scout_acquire("weather tools", mock_ctx)

        assert result["status"] == "already_connected"
        mock_ctx.send_notification.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_acquire_no_http_servers(self):
        """No HTTP servers: when all registry results are stdio-only, returns no_servers_found."""
        from fastmcp.server.context import Context

        mock_ctx = AsyncMock(spec=Context)

        registry_servers = [
            {"name": "local-mcp", "description": "Local tool", "remote_url": None},
            {"name": "stdio-only", "description": "Another stdio tool", "remote_url": None},
        ]

        with (
            patch("server.search_registry", AsyncMock(return_value=registry_servers)),
        ):
            result = await server.scout_acquire("weather tools", mock_ctx)

        assert result == {"status": "no_servers_found", "context": "weather tools"}
        mock_ctx.send_notification.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_acquire_empty_ranked_list(self):
        """Empty ranked list: when rank_servers returns [], returns no_servers_found."""
        from fastmcp.server.context import Context

        mock_ctx = AsyncMock(spec=Context)

        registry_servers = [
            {"name": "weather-mcp", "description": "Weather tools", "remote_url": "https://weather.example.com/mcp"},
        ]

        with (
            patch("server.search_registry", AsyncMock(return_value=registry_servers)),
            patch("server.rank_servers", AsyncMock(return_value=[])),
        ):
            result = await server.scout_acquire("weather tools", mock_ctx)

        assert result == {"status": "no_servers_found", "context": "weather tools"}
        mock_ctx.send_notification.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_acquire_retries_on_unreachable_server(self):
        """When the top-ranked server is unreachable, acquire tries the next one."""
        from fastmcp.server.context import Context

        mock_ctx = AsyncMock(spec=Context)

        registry_servers = [
            {"name": "broken-mcp", "description": "Down server", "remote_url": "https://broken.example.com/mcp"},
            {"name": "good-mcp", "description": "Working server", "remote_url": "https://good.example.com/mcp"},
        ]
        ranked_servers = [
            {
                "name": "broken-mcp", "description": "Down server",
                "remote_url": "https://broken.example.com/mcp",
                "score": 95, "reasoning": "Best match", "ranked": True,
            },
            {
                "name": "good-mcp", "description": "Working server",
                "remote_url": "https://good.example.com/mcp",
                "score": 80, "reasoning": "Also good", "ranked": True,
            },
        ]

        async def mock_connect(name, url, _app):
            if name == "broken-mcp":
                return {"status": "error", "name": name, "url": url, "message": "Connection refused"}
            return {"status": "connected", "name": name, "url": url}

        with (
            patch("server.search_registry", AsyncMock(return_value=registry_servers)),
            patch("server.rank_servers", AsyncMock(return_value=ranked_servers)),
            patch("proxy.connect", side_effect=mock_connect),
        ):
            result = await server.scout_acquire("some tools", mock_ctx)

        assert result["status"] == "connected"
        assert result["server"] == "good-mcp"
        mock_ctx.send_notification.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_acquire_all_servers_unreachable(self):
        """When all ranked servers are unreachable, returns error with tried list."""
        from fastmcp.server.context import Context

        mock_ctx = AsyncMock(spec=Context)

        registry_servers = [
            {"name": "broken1", "description": "Down", "remote_url": "https://broken1.example.com/mcp"},
            {"name": "broken2", "description": "Also down", "remote_url": "https://broken2.example.com/mcp"},
        ]
        ranked_servers = [
            {
                "name": "broken1", "description": "Down",
                "remote_url": "https://broken1.example.com/mcp",
                "score": 90, "reasoning": "Top", "ranked": True,
            },
            {
                "name": "broken2", "description": "Also down",
                "remote_url": "https://broken2.example.com/mcp",
                "score": 80, "reasoning": "Second", "ranked": True,
            },
        ]

        async def mock_connect(name, url, _app):
            return {"status": "error", "name": name, "url": url, "message": "Unreachable"}

        with (
            patch("server.search_registry", AsyncMock(return_value=registry_servers)),
            patch("server.rank_servers", AsyncMock(return_value=ranked_servers)),
            patch("proxy.connect", side_effect=mock_connect),
        ):
            result = await server.scout_acquire("some tools", mock_ctx)

        assert result["status"] == "error"
        assert result["message"] == "No reachable servers found"
        assert len(result["tried"]) == 2
        mock_ctx.send_notification.assert_not_awaited()

    def test_acquire_signature(self):
        """scout_acquire must have context: str and ctx: Context parameters."""
        from fastmcp.server.context import Context

        sig = inspect.signature(server.scout_acquire)
        params = sig.parameters

        assert "context" in params, "scout_acquire must accept a 'context' parameter"
        assert params["context"].annotation is str, (
            f"'context' parameter must be annotated as str, got {params['context'].annotation}"
        )

        assert "ctx" in params, "scout_acquire must accept a 'ctx' parameter"
        assert params["ctx"].annotation is Context, (
            f"'ctx' parameter must be annotated as Context, got {params['ctx'].annotation}"
        )
