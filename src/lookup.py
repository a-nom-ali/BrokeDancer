"""Utility to fetch market/token IDs from a Polymarket event slug.

Parses the event page `https://polymarket.com/event/<slug>` and extracts the
market id plus clob token ids (order follows outcomes list).
"""

import json
import re
import logging
from datetime import datetime
from typing import Dict

import httpx

from .utils import retry_with_backoff, validate_market_slug

logger = logging.getLogger(__name__)


@retry_with_backoff(
    max_attempts=3,
    initial_delay=2.0,
    exceptions=(httpx.HTTPError, httpx.TimeoutException, ConnectionError)
)
def fetch_market_from_slug(slug: str) -> Dict[str, str]:
    """
    Fetch market information from Polymarket event slug.

    Args:
        slug: Market slug (e.g., "btc-updown-15m-1765301400")

    Returns:
        Dictionary with market_id, token IDs, and metadata

    Raises:
        ValueError: If slug format is invalid
        RuntimeError: If market data cannot be extracted
        httpx.HTTPError: If HTTP request fails (after retries)
    """
    # Validate slug format
    if not validate_market_slug(slug):
        raise ValueError(f"Invalid market slug format: {slug}")

    # Allow slugs that include query params (e.g., copied from the browser)
    slug = slug.split("?")[0]
    url = f"https://polymarket.com/event/{slug}"

    logger.debug(f"Fetching market data from: {url}")

    try:
        resp = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching market '{slug}': {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching market '{slug}': {e}")
        raise RuntimeError(f"Failed to fetch market data: {e}") from e

    # Extract __NEXT_DATA__ JSON payload
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text, re.DOTALL)
    if not m:
        logger.error(f"__NEXT_DATA__ payload not found for slug: {slug}")
        raise RuntimeError("__NEXT_DATA__ payload not found on page")

    try:
        payload = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse __NEXT_DATA__ JSON: {e}")
        raise RuntimeError(f"Invalid JSON in __NEXT_DATA__: {e}") from e

    queries = payload.get("props", {}).get("pageProps", {}).get("dehydratedState", {}).get("queries", [])
    market = None
    for q in queries:
        data = q.get("state", {}).get("data")
        if isinstance(data, dict) and "markets" in data:
            for mk in data["markets"]:
                if mk.get("slug") == slug:
                    market = mk
                    break
        if market:
            break

    if not market:
        logger.error(f"Market slug '{slug}' not found in dehydrated state")
        raise RuntimeError(f"Market slug '{slug}' not found in dehydrated state")

    clob_tokens = market.get("clobTokenIds") or []
    outcomes = market.get("outcomes") or []
    if len(clob_tokens) != 2 or len(outcomes) != 2:
        logger.error(
            f"Expected binary market with 2 tokens, got {len(clob_tokens)} tokens "
            f"and {len(outcomes)} outcomes"
        )
        raise RuntimeError("Expected binary market with two clob tokens")

    result = {
        "market_id": market.get("id", ""),
        "yes_token_id": clob_tokens[0],
        "no_token_id": clob_tokens[1],
        "outcomes": outcomes,
        "question": market.get("question", ""),
        "start_date": market.get("startDate"),
        "end_date": market.get("endDate"),
    }

    logger.info(f"Successfully fetched market: {result['question']}")
    return result


def next_slug(slug: str) -> str:
    # Increment the trailing epoch-like number by 900 seconds (15m)
    m = re.match(r"(.+-)(\d+)$", slug)
    if not m:
        raise ValueError(f"Slug not in expected format: {slug}")
    prefix, num = m.groups()
    return f"{prefix}{int(num) + 900}"


def parse_iso(dt: str) -> datetime | None:
    if not dt:
        return None
    try:
        return datetime.fromisoformat(dt.replace("Z", "+00:00"))
    except Exception:
        return None


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m src.lookup <slug>")
        sys.exit(1)
    info = fetch_market_from_slug(sys.argv[1])
    print(json.dumps(info, indent=2))