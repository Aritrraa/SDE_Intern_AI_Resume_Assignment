"""
Eligibility module — deterministic hard filter.

A candidate is eligible ONLY when BOTH conditions are met:
  1. Python evidence: Python appears as a genuine skill / project tech / work tech.
  2. AI/Agentic evidence: at least one meaningful AI/LLM/RAG/agentic project,
     framework, or implementation is present.

This filter is intentionally rule-based, not LLM-based.
"""

import logging
import re
from src.config import PYTHON_KEYWORDS, AI_KEYWORDS

logger = logging.getLogger(__name__)


def _find_keyword_matches(text_lower: str, keyword_list: list[str]) -> list[str]:
    """Return all keywords from *keyword_list* that appear in *text_lower*."""
    matches = []
    for kw in keyword_list:
        kw_lower = kw.lower()
        # Use word-boundary regex for short keywords (≤4 chars) to avoid
        # false positives like "rag" matching inside "storage"/"coverage"
        if len(kw_lower) <= 4:
            if re.search(r'\b' + re.escape(kw_lower) + r'\b', text_lower):
                matches.append(kw)
        else:
            if kw_lower in text_lower:
                matches.append(kw)
    return sorted(set(matches))


def check_eligibility(text: str, matched_skills: list[str] | None = None) -> dict:
    """
    Apply the two hard eligibility filters.

    Parameters
    ----------
    text : str
        Full resume text.
    matched_skills : list[str] | None
        Pre-extracted skill list (for the output). If None, we derive it.

    Returns
    -------
    dict with keys:
        eligible: bool
        rejection_reasons: list[str]
        python_evidence: list[str]
        ai_evidence: list[str]
        matched_skills: list[str]
    """
    text_lower = text.lower()

    python_evidence = _find_keyword_matches(text_lower, PYTHON_KEYWORDS)
    ai_evidence = _find_keyword_matches(text_lower, AI_KEYWORDS)

    rejection_reasons: list[str] = []

    has_python = len(python_evidence) > 0
    has_ai = len(ai_evidence) > 0

    if not has_python:
        rejection_reasons.append("No evidence of Python stack")
    if not has_ai:
        rejection_reasons.append("No AI/agentic project evidence")

    eligible = has_python and has_ai

    return {
        "eligible": eligible,
        "rejection_reasons": rejection_reasons,
        "python_evidence": python_evidence,
        "ai_evidence": ai_evidence,
        "matched_skills": matched_skills or (python_evidence + ai_evidence),
    }
