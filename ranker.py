"""Ranker module — filters HTTP servers and ranks them using Claude Haiku.

This is the intelligence core of Scout:
  1. filter_http_servers removes stdio-only registry entries (remote_url=None).
  2. rank_servers calls Claude Haiku to score servers by relevance (0-100).
  3. On any Haiku failure (network, rate limit, auth, bad JSON), fallback_unranked
     returns results with ranked=False and a fallback_reason — no crash.
"""

import json
import logging
import os

import anthropic

from schemas import RegistryServer, ScoredServer

log = logging.getLogger(__name__)

RANKING_MODEL = os.environ.get("SCOUT_RANKING_MODEL", "claude-haiku-4-5-20251001")
RANKING_MAX_TOKENS = 512

_client = anthropic.AsyncAnthropic()  # uses ANTHROPIC_API_KEY from env


def filter_http_servers(servers: list[RegistryServer]) -> list[RegistryServer]:
    """Remove servers that have no HTTP remote_url (stdio-only entries)."""
    return [s for s in servers if s.get("remote_url") is not None]


def build_prompt(context: str, servers: list[RegistryServer]) -> str:
    """Build the ranking prompt for Haiku."""
    server_list = "\n".join(
        f"{i + 1}. {s['name']}: {s['description']}"
        for i, s in enumerate(servers)
    )
    return (
        f"You are ranking MCP servers for a user.\n"
        f"User needs: {context}\n\n"
        f"Servers:\n{server_list}\n\n"
        f"Return a JSON array, one object per server, in this exact format:\n"
        f'[{{"index": 1, "score": 85, "reasoning": "one sentence"}}, ...]\n'
        f"Score 0-100. Higher = better match. No other text."
    )


def fallback_unranked(servers: list[RegistryServer], reason: str) -> list[ScoredServer]:
    """Return servers without ranking when Haiku is unavailable or returns bad data."""
    return [
        ScoredServer(
            name=s["name"],
            description=s["description"],
            remote_url=s["remote_url"],
            score=None,
            reasoning=None,
            ranked=False,
            fallback_reason=reason,
        )
        for s in servers
    ]


async def rank_servers(context: str, servers: list[RegistryServer]) -> list[ScoredServer]:
    """Rank servers using Claude Haiku. Falls back to unranked on any failure.

    Args:
        context: Natural-language description of what the user needs.
        servers: List of server dicts (must have name, description, remote_url).

    Returns:
        List of server dicts with score (int 0-100), reasoning (str), and ranked=True
        on success; or score=None, reasoning=None, ranked=False, fallback_reason on
        any failure.
    """
    if not servers:
        return []
    try:
        response = await _client.messages.create(
            model=RANKING_MODEL,
            max_tokens=RANKING_MAX_TOKENS,
            messages=[{"role": "user", "content": build_prompt(context, servers)}],
        )
        text = response.content[0].text
        rankings = json.loads(text)
        # Validate structure — every entry must have index, score, reasoning
        scored: list[ScoredServer] = []
        for rank in rankings:
            if not all(k in rank for k in ("index", "score", "reasoning")):
                log.warning("Malformed ranking entry from Haiku: %s", rank)
                return fallback_unranked(servers, "Malformed ranking response")
            idx = rank["index"] - 1  # 1-based → 0-based
            if 0 <= idx < len(servers):
                src = servers[idx]
                scored.append(ScoredServer(
                    name=src["name"],
                    description=src["description"],
                    remote_url=src["remote_url"],
                    score=int(rank["score"]),
                    reasoning=rank["reasoning"],
                    ranked=True,
                ))
        scored.sort(key=lambda s: s["score"], reverse=True)
        return scored
    except anthropic.APIError as e:
        log.warning("Haiku API error during ranking: %s", e)
        return fallback_unranked(servers, str(e))
    except (json.JSONDecodeError, KeyError, IndexError, ValueError, TypeError) as e:
        log.warning("Failed to parse Haiku ranking response: %s", e)
        return fallback_unranked(servers, "Failed to parse ranking response")
