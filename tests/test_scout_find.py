"""Tests for scout_find tool — search + filter + rank pipeline with registry retry."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

import server

# ---------------------------------------------------------------------------
# Test data helpers
# ---------------------------------------------------------------------------


def _make_registry_server(name, description, remote_url):
    """Build a server dict in the shape returned by search_registry."""
    return {"name": name, "description": description, "remote_url": remote_url}


def _make_ranked_server(name, description, remote_url, score, reasoning):
    """Build a fully-ranked result as rank_servers would return."""
    return {
        "name": name,
        "description": description,
        "remote_url": remote_url,
        "score": score,
        "reasoning": reasoning,
        "ranked": True,
    }


# 6 servers: 4 with remote_url, 2 without
MOCK_REGISTRY_SERVERS = [
    _make_registry_server("github-mcp", "GitHub integration", "https://github.example.com/mcp"),
    _make_registry_server("slack-mcp", "Slack integration", "https://slack.example.com/mcp"),
    _make_registry_server("local-mcp", "Local stdio tool", None),
    _make_registry_server("jira-mcp", "Jira integration", "https://jira.example.com/mcp"),
    _make_registry_server("linear-mcp", "Linear integration", "https://linear.example.com/mcp"),
    _make_registry_server("stdio-only", "Another stdio server", None),
]

HTTP_ONLY = [s for s in MOCK_REGISTRY_SERVERS if s["remote_url"] is not None]

MOCK_RANKED_RESULTS = [
    _make_ranked_server("jira-mcp", "Jira integration", "https://jira.example.com/mcp", 90, "Best match"),
    _make_ranked_server("linear-mcp", "Linear integration", "https://linear.example.com/mcp", 80, "Good match"),
    _make_ranked_server("github-mcp", "GitHub integration", "https://github.example.com/mcp", 70, "Partial match"),
    _make_ranked_server("slack-mcp", "Slack integration", "https://slack.example.com/mcp", 50, "Weak match"),
]


# ---------------------------------------------------------------------------
# scout_find shape and behavior tests
# ---------------------------------------------------------------------------


class TestScoutFindShape:
    """DISC-03: scout_find returns correctly-shaped results."""

    async def test_scout_find_shape(self):
        """scout_find returns a list of dicts each with required keys."""
        with (
            patch.object(server, "search_registry", AsyncMock(return_value=MOCK_REGISTRY_SERVERS)),
            patch.object(server, "rank_servers", AsyncMock(return_value=MOCK_RANKED_RESULTS)),
        ):
            results = await server.scout_find("project management tools")

        assert isinstance(results, list)
        assert len(results) > 0
        required_keys = {"name", "description", "remote_url", "score", "reasoning", "ranked"}
        for result in results:
            assert required_keys.issubset(result.keys()), (
                f"Result missing keys: {required_keys - result.keys()}"
            )

    async def test_scout_find_sorted_by_score(self):
        """scout_find results are sorted by score descending (highest first)."""
        with (
            patch.object(server, "search_registry", AsyncMock(return_value=MOCK_REGISTRY_SERVERS)),
            patch.object(server, "rank_servers", AsyncMock(return_value=MOCK_RANKED_RESULTS)),
        ):
            results = await server.scout_find("project management")

        scores = [r["score"] for r in results if r["score"] is not None]
        assert scores == sorted(scores, reverse=True), (
            f"Results not sorted by score descending: {scores}"
        )

    async def test_scout_find_max_results(self):
        """When max_results=2, at most 2 results are returned."""
        with (
            patch.object(server, "search_registry", AsyncMock(return_value=MOCK_REGISTRY_SERVERS)),
            patch.object(server, "rank_servers", AsyncMock(return_value=MOCK_RANKED_RESULTS)),
        ):
            results = await server.scout_find("project management", max_results=2)

        assert len(results) <= 2

    async def test_scout_find_default_max_results(self):
        """When max_results is not passed, defaults to 5 — at most 5 results returned."""
        six_ranked = [
            _make_ranked_server(f"server-{i}", f"Server {i}", f"https://s{i}.example.com", 100 - i * 5, "ok")
            for i in range(6)
        ]
        with (
            patch.object(server, "search_registry", AsyncMock(return_value=MOCK_REGISTRY_SERVERS)),
            patch.object(server, "rank_servers", AsyncMock(return_value=six_ranked)),
        ):
            results = await server.scout_find("anything")

        assert len(results) <= 5

    async def test_scout_find_filters_stdio(self):
        """Servers with remote_url=None must not appear in scout_find results."""
        captured_servers = []

        async def capturing_rank(context, servers):
            captured_servers.extend(servers)
            return MOCK_RANKED_RESULTS

        with (
            patch.object(server, "search_registry", AsyncMock(return_value=MOCK_REGISTRY_SERVERS)),
            patch.object(server, "rank_servers", capturing_rank),
        ):
            results = await server.scout_find("any context")

        for s in captured_servers:
            assert s["remote_url"] is not None, (
                f"Server {s['name']} with remote_url=None passed to rank_servers"
            )

        for r in results:
            assert r["remote_url"] is not None


# ---------------------------------------------------------------------------
# search_registry retry tests
# ---------------------------------------------------------------------------


class TestRegistryRetry:
    """Registry retry: one retry on first failure, RuntimeError on second failure."""

    async def test_registry_retry_on_first_failure(self):
        """When first registry call raises HTTPError, second succeeds."""
        registry_json = {
            "servers": [
                {
                    "server": {
                        "name": "test-mcp",
                        "description": "Test server",
                        "remotes": [{"url": "https://test.example.com/mcp"}],
                    }
                }
            ]
        }
        success_resp = MagicMock()
        success_resp.raise_for_status = MagicMock()
        success_resp.json = MagicMock(return_value=registry_json)

        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.HTTPStatusError(
                    "500 Internal Server Error",
                    request=MagicMock(),
                    response=MagicMock(),
                )
            return success_resp

        mock_client_instance = AsyncMock()
        mock_client_instance.get = mock_get
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client_instance):
            result = await server.search_registry("test query")

        assert call_count == 2, f"Expected 2 calls (retry), got {call_count}"
        assert len(result) == 1
        assert result[0]["name"] == "test-mcp"

    async def test_registry_retry_exhausted(self):
        """When both registry attempts fail, RuntimeError is raised."""
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "503 Service Unavailable",
                request=MagicMock(),
                response=MagicMock(),
            )
        )
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("httpx.AsyncClient", return_value=mock_client_instance),
            pytest.raises(RuntimeError, match="Registry unreachable"),
        ):
            await server.search_registry("failing query")
