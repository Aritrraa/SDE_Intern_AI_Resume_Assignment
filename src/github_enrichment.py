"""
GitHub enrichment — lightweight public API integration.

Enriches candidate score with up to 10 points based on:
  - Recent activity (0-5 pts): public events / commits in last 90 days
  - Repository quality (0-5 pts): maintained, Python/AI-relevant repos

Handles rate limits, private/missing profiles, and API failures gracefully.
Results are cached within the run to avoid repeated calls.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests

from src.config import GITHUB_TOKEN, GITHUB_API_BASE, GITHUB_MAX_SCORE, GITHUB_REQUEST_TIMEOUT

logger = logging.getLogger(__name__)

# In-memory cache for the current run
_cache: dict[str, dict] = {}


def _get_headers() -> dict:
    """Build request headers, including auth token if available."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers


def _api_get(url: str) -> Optional[dict | list]:
    """Make a GET request to the GitHub API with error handling."""
    try:
        resp = requests.get(url, headers=_get_headers(), timeout=GITHUB_REQUEST_TIMEOUT)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 403:
            logger.warning("GitHub API rate limited: %s", url)
            return None
        elif resp.status_code == 404:
            logger.info("GitHub profile not found: %s", url)
            return None
        else:
            logger.warning("GitHub API returned %d for %s", resp.status_code, url)
            return None
    except requests.exceptions.Timeout:
        logger.warning("GitHub API timeout: %s", url)
        return None
    except requests.exceptions.RequestException as e:
        logger.error("GitHub API error: %s", e)
        return None


def _score_recent_activity(username: str) -> tuple[int, str]:
    """
    Score recent activity (0-5 points).

    Uses the public events API to check for recent activity.
    """
    url = f"{GITHUB_API_BASE}/users/{username}/events/public?per_page=30"
    events = _api_get(url)

    if events is None:
        return 0, "Could not fetch activity data"

    if not isinstance(events, list):
        return 0, "Unexpected API response format"

    # Count events in last 90 days
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    recent_events = 0
    for event in events:
        created = event.get("created_at", "")
        try:
            event_date = datetime.fromisoformat(created.replace("Z", "+00:00"))
            if event_date >= cutoff:
                recent_events += 1
        except (ValueError, TypeError):
            continue

    if recent_events >= 15:
        score = 5
        summary = f"Very active ({recent_events} events in last 90 days)"
    elif recent_events >= 8:
        score = 4
        summary = f"Active ({recent_events} events in last 90 days)"
    elif recent_events >= 4:
        score = 3
        summary = f"Moderately active ({recent_events} events in last 90 days)"
    elif recent_events >= 1:
        score = 2
        summary = f"Some recent activity ({recent_events} events in last 90 days)"
    else:
        score = 0
        summary = "No recent public activity"

    return score, summary


def _score_repositories(username: str) -> tuple[int, str]:
    """
    Score maintained/relevant repositories (0-5 points).

    Checks for Python/AI-related repos and overall repo count.
    """
    url = f"{GITHUB_API_BASE}/users/{username}/repos?per_page=30&sort=updated&direction=desc"
    repos = _api_get(url)

    if repos is None:
        return 0, "Could not fetch repository data"

    if not isinstance(repos, list):
        return 0, "Unexpected API response format"

    python_repos = 0
    ai_keywords = {"ai", "ml", "machine-learning", "deep-learning", "nlp", "rag",
                    "langchain", "llm", "agent", "chatbot", "neural", "transformer"}
    ai_repos = 0
    total_repos = len(repos)

    for repo in repos:
        lang = (repo.get("language") or "").lower()
        name = (repo.get("name") or "").lower()
        desc = (repo.get("description") or "").lower()

        if lang == "python":
            python_repos += 1

        if any(kw in name or kw in desc for kw in ai_keywords):
            ai_repos += 1

    score = 0
    details = []

    # Points for Python repos
    if python_repos >= 5:
        score += 2
        details.append(f"{python_repos} Python repos")
    elif python_repos >= 2:
        score += 1
        details.append(f"{python_repos} Python repos")

    # Points for AI-relevant repos
    if ai_repos >= 3:
        score += 2
        details.append(f"{ai_repos} AI-relevant repos")
    elif ai_repos >= 1:
        score += 1
        details.append(f"{ai_repos} AI-relevant repo(s)")

    # Points for overall maintained repos
    if total_repos >= 10:
        score += 1
        details.append(f"{total_repos} total public repos")

    score = min(score, 5)
    summary = "; ".join(details) if details else "No relevant repositories found"

    return score, summary


def enrich_github(username: str) -> dict:
    """
    Enrich a candidate with GitHub activity data.

    Returns dict with:
        github_score: int (0-10)
        github_summary: str
        activity_score: int
        repo_score: int
        enrichment_status: str ("success" | "failed" | "skipped")
        error: str | None
    """
    # Check cache first
    if username in _cache:
        logger.info("Using cached GitHub data for %s", username)
        return _cache[username]

    if not username:
        result = {
            "github_score": 0,
            "github_summary": "No GitHub profile provided",
            "activity_score": 0,
            "repo_score": 0,
            "enrichment_status": "skipped",
            "error": None,
        }
        return result

    try:
        activity_score, activity_summary = _score_recent_activity(username)
        repo_score, repo_summary = _score_repositories(username)

        total = min(activity_score + repo_score, GITHUB_MAX_SCORE)

        # Determine enrichment status: if both sub-calls returned no data,
        # label as partial_failure rather than success
        both_failed = (
            activity_score == 0 and repo_score == 0
            and ("Could not fetch" in activity_summary or "No recent" in activity_summary)
            and "Could not fetch" in repo_summary
        )
        status = "partial_failure" if both_failed else "success"

        result = {
            "github_score": total,
            "github_summary": f"Activity: {activity_summary}. Repos: {repo_summary}",
            "activity_score": activity_score,
            "repo_score": repo_score,
            "enrichment_status": status,
            "error": None,
        }
    except Exception as e:
        logger.error("GitHub enrichment failed for %s: %s", username, e)
        result = {
            "github_score": 0,
            "github_summary": f"Enrichment failed: {e}",
            "activity_score": 0,
            "repo_score": 0,
            "enrichment_status": "failed",
            "error": str(e),
        }

    # Cache result
    _cache[username] = result
    return result


def clear_cache():
    """Clear the GitHub cache (useful for testing)."""
    _cache.clear()
