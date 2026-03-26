"""Tests for ranker.py — filter_http_servers and rank_servers with mocked AsyncAnthropic."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic

import ranker

# ---------------------------------------------------------------------------
# Test data helpers
# ---------------------------------------------------------------------------

def _make_server(name, description, remote_url):
    return {"name": name, "description": description, "remote_url": remote_url}


HTTP_SERVER_1 = _make_server("github-mcp", "GitHub integration", "https://github.example.com/mcp")
HTTP_SERVER_2 = _make_server("slack-mcp", "Slack integration", "https://slack.example.com/mcp")
STDIO_SERVER = _make_server("local-mcp", "Local stdio tool", None)

MIXED_SERVERS = [HTTP_SERVER_1, STDIO_SERVER, HTTP_SERVER_2]
HTTP_ONLY_SERVERS = [HTTP_SERVER_1, HTTP_SERVER_2]


# ---------------------------------------------------------------------------
# filter_http_servers tests
# ---------------------------------------------------------------------------

class TestFilterHttpServers:
    """DISC-01: filter_http_servers removes servers with remote_url=None."""

    def test_filter_removes_stdio(self):
        """Given mixed servers, only those with remote_url are returned."""
        result = ranker.filter_http_servers(MIXED_SERVERS)
        assert len(result) == 2
        names = [s["name"] for s in result]
        assert "github-mcp" in names
        assert "slack-mcp" in names
        assert "local-mcp" not in names

    def test_filter_empty_list(self):
        """Given an empty list, returns an empty list."""
        result = ranker.filter_http_servers([])
        assert result == []

    def test_filter_all_stdio(self):
        """Given all stdio servers, returns an empty list."""
        all_stdio = [STDIO_SERVER, _make_server("another-local", "Also local", None)]
        result = ranker.filter_http_servers(all_stdio)
        assert result == []

    def test_filter_preserves_http_servers(self):
        """filter_http_servers does not modify servers that pass the filter."""
        result = ranker.filter_http_servers(HTTP_ONLY_SERVERS)
        assert len(result) == 2
        assert result[0]["remote_url"] is not None
        assert result[1]["remote_url"] is not None


# ---------------------------------------------------------------------------
# rank_servers tests
# ---------------------------------------------------------------------------

def _make_mock_response(json_text: str):
    """Build a mock AsyncAnthropic response whose content[0].text returns json_text."""
    mock_content = MagicMock()
    mock_content.text = json_text
    mock_response = MagicMock()
    mock_response.content = [mock_content]
    return mock_response


class TestRankServers:
    """DISC-02: rank_servers calls Haiku and returns sorted, scored results."""

    async def test_rank_success(self):
        """When Haiku returns valid JSON scores, results are sorted by score descending."""
        valid_json = json.dumps([
            {"index": 1, "score": 60, "reasoning": "Partial match"},
            {"index": 2, "score": 90, "reasoning": "Great match"},
        ])
        mock_create = AsyncMock(return_value=_make_mock_response(valid_json))

        with patch.object(ranker._client.messages, "create", mock_create):
            results = await ranker.rank_servers("I need GitHub integration", HTTP_ONLY_SERVERS)

        assert len(results) == 2
        # Sorted by score descending
        assert results[0]["score"] == 90
        assert results[1]["score"] == 60
        # Each result has required fields
        for r in results:
            assert isinstance(r["score"], int)
            assert isinstance(r["reasoning"], str)
            assert r["ranked"] is True

    async def test_rank_fallback_on_api_error(self):
        """When AsyncAnthropic raises APIError, returns unranked fallback results."""
        mock_create = AsyncMock(
            side_effect=anthropic.RateLimitError(
                message="rate limited",
                response=MagicMock(),
                body=None,
            )
        )

        with patch.object(ranker._client.messages, "create", mock_create):
            results = await ranker.rank_servers("I need GitHub integration", HTTP_ONLY_SERVERS)

        assert len(results) == 2
        for r in results:
            assert r["ranked"] is False
            assert r["score"] is None
            assert r["reasoning"] is None
            assert isinstance(r["fallback_reason"], str)
            assert len(r["fallback_reason"]) > 0

    async def test_rank_fallback_on_malformed_json(self):
        """When Haiku returns non-JSON text, falls back gracefully without raising."""
        malformed = "Sure! Here are the rankings: [invalid json"
        mock_create = AsyncMock(return_value=_make_mock_response(malformed))

        with patch.object(ranker._client.messages, "create", mock_create):
            results = await ranker.rank_servers("I need GitHub integration", HTTP_ONLY_SERVERS)

        assert len(results) == 2
        for r in results:
            assert r["ranked"] is False
            assert r["score"] is None

    async def test_rank_fallback_on_json_missing_fields(self):
        """When Haiku returns JSON missing required fields, falls back to unranked."""
        missing_fields_json = json.dumps([{"wrong_field": 1}])
        mock_create = AsyncMock(return_value=_make_mock_response(missing_fields_json))

        with patch.object(ranker._client.messages, "create", mock_create):
            results = await ranker.rank_servers("I need GitHub integration", HTTP_ONLY_SERVERS)

        assert len(results) == 2
        for r in results:
            assert r["ranked"] is False

    async def test_rank_empty_servers_returns_empty(self):
        """When servers list is empty, returns empty list without calling Haiku."""
        mock_create = AsyncMock()

        with patch.object(ranker._client.messages, "create", mock_create):
            results = await ranker.rank_servers("anything", [])

        assert results == []
        mock_create.assert_not_called()

    async def test_rank_result_preserves_server_fields(self):
        """Ranked results include name, description, and remote_url from source server."""
        valid_json = json.dumps([
            {"index": 1, "score": 85, "reasoning": "Good match"},
        ])
        mock_create = AsyncMock(return_value=_make_mock_response(valid_json))
        single_server = [HTTP_SERVER_1]

        with patch.object(ranker._client.messages, "create", mock_create):
            results = await ranker.rank_servers("GitHub", single_server)

        assert len(results) == 1
        assert results[0]["name"] == HTTP_SERVER_1["name"]
        assert results[0]["description"] == HTTP_SERVER_1["description"]
        assert results[0]["remote_url"] == HTTP_SERVER_1["remote_url"]

    async def test_rank_fallback_result_preserves_server_fields(self):
        """Fallback results include name, description, and remote_url from source server."""
        mock_create = AsyncMock(
            side_effect=anthropic.RateLimitError(
                message="rate limited",
                response=MagicMock(),
                body=None,
            )
        )
        single_server = [HTTP_SERVER_1]

        with patch.object(ranker._client.messages, "create", mock_create):
            results = await ranker.rank_servers("GitHub", single_server)

        assert len(results) == 1
        assert results[0]["name"] == HTTP_SERVER_1["name"]
        assert results[0]["description"] == HTTP_SERVER_1["description"]
        assert results[0]["remote_url"] == HTTP_SERVER_1["remote_url"]
