"""Tests for CONF-01 (API key validation) and CONF-02 (registry URL config)."""
import importlib
import sys
import pytest


async def _run_lifespan(module):
    """Helper to run the lifespan context manager and capture SystemExit."""
    async with module.app_lifespan(None):
        pass


class TestMissingApiKey:
    """CONF-01: Scout must exit with nonzero code if ANTHROPIC_API_KEY is not set."""

    async def test_missing_api_key_prevents_startup(self, monkeypatch):
        """Lifespan raises SystemExit(1) when ANTHROPIC_API_KEY is absent."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        import server
        importlib.reload(server)
        with pytest.raises(SystemExit) as exc_info:
            await _run_lifespan(server)
        assert exc_info.value.code == 1


class TestRegistryUrl:
    """CONF-02: Registry URL must default to live registry and be overridable."""

    def test_registry_url_default(self, monkeypatch):
        """get_registry_url() returns the hardcoded default when env var is absent."""
        monkeypatch.delenv("SCOUT_REGISTRY_URL", raising=False)
        import server
        importlib.reload(server)
        assert server.get_registry_url() == "https://registry.modelcontextprotocol.io/v0.1/servers"

    def test_registry_url_custom(self, monkeypatch):
        """get_registry_url() returns the custom URL when SCOUT_REGISTRY_URL is set."""
        custom_url = "http://localhost:9000/v1/servers"
        monkeypatch.setenv("SCOUT_REGISTRY_URL", custom_url)
        import server
        importlib.reload(server)
        assert server.get_registry_url() == custom_url
