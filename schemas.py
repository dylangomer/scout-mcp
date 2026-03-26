"""Shared type definitions for Scout MCP server."""

from typing import NotRequired, TypedDict


class RegistryServer(TypedDict):
    """Server entry as returned by the MCP registry search."""

    name: str
    description: str
    remote_url: str | None


class ScoredServer(TypedDict):
    """Server entry after ranking or fallback.

    On successful ranking: score is an int (0-100), reasoning is a string,
    ranked is True, and fallback_reason is absent.

    On fallback: score and reasoning are None, ranked is False, and
    fallback_reason explains why ranking was unavailable.
    """

    name: str
    description: str
    remote_url: str | None
    score: int | None
    reasoning: str | None
    ranked: bool
    fallback_reason: NotRequired[str]


class ConnectionInfo(TypedDict):
    """Active connection entry returned by scout_list_active."""

    name: str
    url: str
