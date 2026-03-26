"""Shared fixtures for Scout MCP tests."""

import pytest
from fastmcp import FastMCP

import proxy as proxy_mod


@pytest.fixture()
def clean_proxy_cache():
    """Reset proxy module-level caches before and after each test."""
    proxy_mod._connections.clear()
    proxy_mod._urls.clear()
    yield
    proxy_mod._connections.clear()
    proxy_mod._urls.clear()


@pytest.fixture()
def fresh_app():
    """Return a fresh FastMCP instance isolated from other tests."""
    return FastMCP("test")
