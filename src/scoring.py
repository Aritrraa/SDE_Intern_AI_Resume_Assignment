"""
Scoring module — deterministic 100-point model.

Category breakdown (baseline weights):
    ai_project_depth     40
    python_backend       30
    cloud_fullstack      15
    github               10  (filled by github_enrichment module)
    engineering_depth     5

Project-quality penalties:
    -5 to -15 for thin API wrappers, tutorial-only projects, keyword-only claims.
"""

import re
import logging
from src.config import (
    SCORING_WEIGHTS,
    PYTHON_BACKEND_KEYWORDS,
    CLOUD_DEPLOY_KEYWORDS,
    ENGINEERING_DEPTH_KEYWORDS,
    AI_PROJECT_DEPTH_KEYWORDS,
    THIN_WRAPPER_INDICATORS,
    PROJECT_DEPTH_INDICATORS,
)

logger = logging.getLogger(__name__)


def _count_keyword_hits(text_lower: str, keywords: list[str]) -> tuple[int, list[str]]:
    """Count unique keyword hits and return (count, matched_list)."""
    hits = []
    for kw in keywords:
        kw_lower = kw.lower()
        # Word-boundary matching for short keywords to prevent false positives
        if len(kw_lower) <= 4:
            if re.search(r'\b' + re.escape(kw_lower) + r'\b', text_lower):
                hits.append(kw)
        else:
            if kw_lower in text_lower:
                hits.append(kw)
    unique = sorted(set(hits))
    return len(unique), unique


def _has_project_context(text_lower: str, keyword: str) -> bool:
    """
    Check whether a keyword appears in a project/experience context
    rather than just a skills list.

    Heuristic: the keyword appears within 200 chars of action verbs
    or project-related terms.
    """
    action_indicators = [
        "built", "developed", "implemented", "created", "designed",
        "deployed", "integrated", "engineered", "automated", "optimized",
        "architected", "configured", "maintained", "contributed",
        "used", "using", "utilized", "leveraged",
    ]
    kw_lower = keyword.lower()
    # For short keywords, use word-boundary regex to find positions
    if len(kw_lower) <= 4:
        for m in re.finditer(r'\b' + re.escape(kw_lower) + r'\b', text_lower):
            pos = m.start()
            context_start = max(0, pos - 200)
            context_end = min(len(text_lower), pos + len(kw_lower) + 200)
            context = text_lower[context_start:context_end]
            for action in action_indicators:
                if action in context:
                    return True
    else:
        pos = text_lower.find(kw_lower)
        while pos != -1:
            context_start = max(0, pos - 200)
            context_end = min(len(text_lower), pos + len(kw_lower) + 200)
            context = text_lower[context_start:context_end]
            for action in action_indicators:
                if action in context:
                    return True
            pos = text_lower.find(kw_lower, pos + 1)
    return False


def score_ai_project_depth(text: str, ai_evidence: list[str]) -> dict:
    """
    Score AI/Agentic/RAG project depth (0-40 points).

    Rewards real AI systems: agents, RAG, tools, retrieval, state,
    orchestration, evaluation, and meaningful business logic.
    Discriminates between agentic/RAG depth and surface-level ML.
    """
    max_score = SCORING_WEIGHTS["ai_project_depth"]
    text_lower = text.lower()
    score = 0.0
    evidence: list[str] = []
    penalties: list[str] = []

    hit_count, hits = _count_keyword_hits(text_lower, AI_PROJECT_DEPTH_KEYWORDS)

    # --- Tier 1: Agentic / RAG specific keywords (higher value) ---
    agentic_keywords = [
        "langchain", "langgraph", "llamaindex", "llama_index", "llama index",
        "rag", "retrieval augmented", "retrieval-augmented",
        "vector search", "vector store", "vector database",
        "tool calling", "tool-calling", "function calling",
        "agentic", "multi-agent", "multiagent",
        "orchestration", "state machine",
        "crewai", "autogen", "dspy", "semantic kernel", "haystack",
        "evaluation pipeline", "eval pipeline",
    ]
    agentic_hits = sum(
        1 for kw in agentic_keywords
        if (re.search(r'\b' + re.escape(kw) + r'\b', text_lower) if len(kw) <= 4
            else kw in text_lower)
    )

    # --- Tier 2: General AI/ML keywords (lower value) ---
    general_hits = hit_count - agentic_hits

    # Base keyword score: agentic worth 3 pts each, general worth 1 pt each
    keyword_score = min(agentic_hits * 3, 15) + min(general_hits * 1, 5)
    score += keyword_score

    # Project context bonus (up to 14 points)
    # Keywords used in actual project descriptions score much higher
    context_hits = 0
    for kw in hits:
        if _has_project_context(text_lower, kw):
            context_hits += 1
    context_score = min(context_hits * 2.5, 14)
    score += context_score
    if context_hits > 0:
        evidence.append(f"{context_hits} AI/ML keywords used in project context")

    # Agentic context bonus (up to 6 points) — reward agentic keywords in projects
    agentic_context = 0
    for kw in agentic_keywords:
        kw_lower = kw.lower()
        found = (re.search(r'\b' + re.escape(kw_lower) + r'\b', text_lower)
                 if len(kw_lower) <= 4 else kw_lower in text_lower)
        if found and _has_project_context(text_lower, kw):
            agentic_context += 1
    if agentic_context > 0:
        agentic_bonus = min(agentic_context * 2, 6)
        score += agentic_bonus
        evidence.append(f"Agentic/RAG keywords in project context: {agentic_context}")

    # Depth indicators bonus (up to 5 points)
    depth_count = 0
    for indicator in PROJECT_DEPTH_INDICATORS:
        if indicator.lower() in text_lower:
            depth_count += 1
    depth_score = min(depth_count * 1, 5)
    score += depth_score

    # --- Project-quality penalties ---
    # Penalty for thin API wrappers
    thin_count = 0
    for indicator in THIN_WRAPPER_INDICATORS:
        if indicator.lower() in text_lower:
            thin_count += 1
    if thin_count > 0:
        penalty = min(thin_count * 5, 15)
        score -= penalty
        penalties.append(f"-{penalty} pts: thin wrapper / tutorial indicators ({thin_count} found)")

    # Penalty: if AI keywords appear ONLY in skills section (no project context)
    if hit_count > 0 and context_hits == 0:
        penalty = 10
        score -= penalty
        penalties.append(f"-{penalty} pts: AI keywords appear only in skills list, no project evidence")

    # Penalty for very few AI project depth indicators
    if depth_count <= 1 and hit_count > 2:
        penalty = 5
        score -= penalty
        penalties.append(f"-{penalty} pts: limited project depth despite multiple AI keywords")

    final = max(0, min(round(score), max_score))

    return {
        "score": final,
        "max": max_score,
        "evidence": evidence,
        "matched_keywords": hits,
        "penalties": penalties,
    }


def score_python_backend(text: str, python_evidence: list[str]) -> dict:
    """
    Score Python & Backend Engineering (0-30 points).

    Rewards Python, FastAPI, async programming, PostgreSQL, Redis.
    Prefers evidence in projects/internships over keyword-only skill lists.
    """
    max_score = SCORING_WEIGHTS["python_backend"]
    text_lower = text.lower()
    score = 0.0
    evidence: list[str] = []

    hit_count, hits = _count_keyword_hits(text_lower, PYTHON_BACKEND_KEYWORDS)

    # Keyword score (up to 15)
    keyword_score = min(hit_count * 2.5, 15)
    score += keyword_score

    # Context bonus (up to 10)
    context_hits = 0
    for kw in hits:
        if _has_project_context(text_lower, kw):
            context_hits += 1
    context_score = min(context_hits * 2.5, 10)
    score += context_score
    if context_hits > 0:
        evidence.append(f"{context_hits} Python/backend keywords used in project context")

    # Backend framework bonus (up to 5)
    backend_frameworks = ["fastapi", "django", "flask"]
    fw_used = [fw for fw in backend_frameworks if fw in text_lower]
    if fw_used:
        fw_bonus = min(len(fw_used) * 2.5, 5)
        score += fw_bonus
        evidence.append(f"Backend frameworks: {', '.join(fw_used)}")

    # Penalty: keyword-only with no project context
    if hit_count > 0 and context_hits == 0:
        penalty = 5
        score -= penalty

    final = max(0, min(round(score), max_score))
    return {
        "score": final,
        "max": max_score,
        "evidence": evidence,
        "matched_keywords": hits,
    }


def score_cloud_fullstack(text: str) -> dict:
    """
    Score Cloud/Deployment/Full Stack (0-15 points).

    GCP, Docker, deployment. React/Next.js as supporting signals.
    """
    max_score = SCORING_WEIGHTS["cloud_fullstack"]
    text_lower = text.lower()
    score = 0.0
    evidence: list[str] = []

    hit_count, hits = _count_keyword_hits(text_lower, CLOUD_DEPLOY_KEYWORDS)

    # Keyword score (up to 10)
    keyword_score = min(hit_count * 1.5, 10)
    score += keyword_score

    # Context bonus (up to 5)
    context_hits = 0
    for kw in hits:
        if _has_project_context(text_lower, kw):
            context_hits += 1
    context_score = min(context_hits * 1.5, 5)
    score += context_score
    if context_hits > 0:
        evidence.append(f"Cloud/deploy keywords in project context: {context_hits}")

    final = max(0, min(round(score), max_score))
    return {
        "score": final,
        "max": max_score,
        "evidence": evidence,
        "matched_keywords": hits,
    }


def score_engineering_depth(text: str) -> dict:
    """
    Score Engineering Depth Signals (0-5 points).

    Testing, architecture, caching, queues, observability, concurrency,
    failure handling.
    """
    max_score = SCORING_WEIGHTS["engineering_depth"]
    text_lower = text.lower()
    score = 0.0
    evidence: list[str] = []

    hit_count, hits = _count_keyword_hits(text_lower, ENGINEERING_DEPTH_KEYWORDS)

    # Keyword score (up to 3)
    keyword_score = min(hit_count * 0.5, 3)
    score += keyword_score

    # Context bonus (up to 2)
    context_hits = 0
    for kw in hits:
        if _has_project_context(text_lower, kw):
            context_hits += 1
    context_score = min(context_hits * 0.5, 2)
    score += context_score
    if context_hits > 0:
        evidence.append(f"Engineering depth signals in context: {context_hits}")

    final = max(0, min(round(score), max_score))
    return {
        "score": final,
        "max": max_score,
        "evidence": evidence,
        "matched_keywords": hits,
    }


def compute_total_score(
    text: str,
    ai_evidence: list[str],
    python_evidence: list[str],
    github_score: int = 0,
    github_summary: str = "",
) -> dict:
    """
    Compute the full 100-point score for an eligible candidate.

    Returns a dict with total_score, score_breakdown, evidence, penalties,
    strengths, and concerns.
    """
    ai_result = score_ai_project_depth(text, ai_evidence)
    py_result = score_python_backend(text, python_evidence)
    cloud_result = score_cloud_fullstack(text)
    eng_result = score_engineering_depth(text)

    # Cap GitHub score at 10
    github_capped = max(0, min(github_score, SCORING_WEIGHTS["github"]))

    total = (
        ai_result["score"]
        + py_result["score"]
        + cloud_result["score"]
        + github_capped
        + eng_result["score"]
    )

    # Ensure total is within bounds
    total = max(0, min(total, 100))

    # Build strengths and concerns
    strengths: list[str] = []
    concerns: list[str] = []

    if ai_result["score"] >= 25:
        strengths.append("Strong AI/agentic project depth")
    elif ai_result["score"] >= 15:
        strengths.append("Moderate AI project experience")
    else:
        concerns.append("Limited AI project depth")

    if py_result["score"] >= 20:
        strengths.append("Strong Python/backend engineering")
    elif py_result["score"] >= 10:
        strengths.append("Moderate Python skills")
    else:
        concerns.append("Limited Python/backend evidence")

    if cloud_result["score"] >= 10:
        strengths.append("Good cloud/deployment experience")

    if eng_result["score"] >= 3:
        strengths.append("Engineering depth signals present")

    if github_capped >= 7:
        strengths.append("Active GitHub profile")
    elif github_capped == 0:
        concerns.append("No GitHub activity data")

    # Collect all penalties
    all_penalties = ai_result.get("penalties", [])

    # Build project summary from evidence
    project_evidence = (
        ai_result.get("evidence", []) +
        py_result.get("evidence", []) +
        cloud_result.get("evidence", []) +
        eng_result.get("evidence", [])
    )

    return {
        "total_score": total,
        "score_breakdown": {
            "ai_project_depth": ai_result["score"],
            "python_backend": py_result["score"],
            "cloud_fullstack": cloud_result["score"],
            "github": github_capped,
            "engineering_depth": eng_result["score"],
        },
        "evidence": project_evidence,
        "penalties": all_penalties,
        "strengths": strengths,
        "concerns": concerns,
        "matched_keywords": {
            "ai": ai_result.get("matched_keywords", []),
            "python_backend": py_result.get("matched_keywords", []),
            "cloud": cloud_result.get("matched_keywords", []),
            "engineering": eng_result.get("matched_keywords", []),
        },
    }
