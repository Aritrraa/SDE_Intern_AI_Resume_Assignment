"""
LLM-assisted resume assessment module.

Uses a configurable LLM provider (Google Gemini or OpenAI) to perform
semantic analysis of resume project descriptions. Returns structured,
evidence-backed assessments that augment the deterministic scoring.

Falls back gracefully to deterministic-only scoring when:
- No API key is configured
- The LLM call fails (timeout, rate limit, malformed response)
- The --no-llm flag is passed via CLI
"""

import json
import logging
import re
from typing import Optional

from src.config import (
    LLM_PROVIDER, GOOGLE_API_KEY, OPENAI_API_KEY,
    LLM_MODEL, LLM_TEMPERATURE, LLM_TIMEOUT,
)

logger = logging.getLogger(__name__)

# In-memory cache for the current run
_llm_cache: dict[str, dict] = {}

# ---------------------------------------------------------------------------
# Pydantic-style schema (plain dict validation — no extra dependency needed)
# ---------------------------------------------------------------------------

ASSESSMENT_SCHEMA = {
    "project_summary": str,
    "ai_implementation_evidence": list,
    "python_backend_evidence": list,
    "engineering_strengths": list,
    "concerns": list,
    "project_quality_assessment": str,
    "has_thin_wrapper_indicators": bool,
    "thin_wrapper_reasoning": str,
    "ownership_signals": list,
    "ai_depth_rating": str,  # "strong" | "moderate" | "weak" | "none"
}


def _validate_assessment(data: dict) -> dict:
    """Validate and normalize an LLM assessment against the expected schema."""
    validated = {}
    for key, expected_type in ASSESSMENT_SCHEMA.items():
        val = data.get(key)
        if val is None:
            validated[key] = [] if expected_type is list else ("" if expected_type is str else False)
        elif expected_type is list and isinstance(val, list):
            validated[key] = [str(item) for item in val[:10]]  # cap at 10 items
        elif expected_type is str and isinstance(val, str):
            validated[key] = val[:500]  # cap string length
        elif expected_type is bool:
            validated[key] = bool(val)
        else:
            validated[key] = [] if expected_type is list else ("" if expected_type is str else False)
    return validated


# ---------------------------------------------------------------------------
# LLM prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an expert technical recruiter evaluating resumes for an SDE Intern position 
focused on AI/agentic systems, RAG pipelines, and Python backend development.

Analyze the resume text and return a JSON object with exactly these fields:

{
  "project_summary": "2-3 sentence summary of the candidate's most relevant projects",
  "ai_implementation_evidence": ["list of specific AI/ML/RAG implementations found IN project descriptions, not just skills lists"],
  "python_backend_evidence": ["list of specific Python/backend implementations found in projects"],
  "engineering_strengths": ["list of engineering depth signals: testing, deployment, architecture, etc."],
  "concerns": ["list of concerns: thin wrappers, tutorial-only projects, keyword-only claims, missing details"],
  "project_quality_assessment": "brief assessment of project depth and originality",
  "has_thin_wrapper_indicators": true/false,
  "thin_wrapper_reasoning": "explain why projects appear to be thin wrappers, or say 'No thin wrapper indicators found'",
  "ownership_signals": ["evidence of ownership: 'built from scratch', specific metrics, deployment details"],
  "ai_depth_rating": "strong|moderate|weak|none"
}

Rules:
- Only cite evidence that is explicitly present in the resume text.
- Distinguish between keywords in a skills list vs. keywords used in project descriptions.
- Do NOT invent projects, technologies, or implementation details.
- If evidence is absent, say so clearly — do not fabricate.
- Be concise. Each list item should be one sentence max.
- Return ONLY valid JSON, no markdown fences, no explanation outside the JSON."""


def _build_user_prompt(resume_text: str) -> str:
    """Build the user prompt with truncated resume text."""
    # Limit text to ~3000 chars to stay within token limits
    text = resume_text[:3000]
    return f"Analyze this resume and return the JSON assessment:\n\n{text}"


# ---------------------------------------------------------------------------
# Provider adapters
# ---------------------------------------------------------------------------

def _call_google(resume_text: str) -> Optional[dict]:
    """Call Google Gemini API."""
    try:
        import google.generativeai as genai
    except ImportError:
        logger.warning("google-generativeai not installed. Run: pip install google-generativeai")
        return None

    if not GOOGLE_API_KEY:
        logger.info("No GOOGLE_API_KEY set. Skipping LLM assessment.")
        return None

    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel(
            LLM_MODEL,
            generation_config=genai.GenerationConfig(
                temperature=LLM_TEMPERATURE,
                response_mime_type="application/json",
            ),
        )

        prompt = SYSTEM_PROMPT + "\n\n" + _build_user_prompt(resume_text)
        response = model.generate_content(
            prompt,
            request_options={"timeout": LLM_TIMEOUT},
        )

        return _parse_response(response.text)
    except Exception as e:
        logger.warning("Google Gemini API call failed: %s", e)
        return None


def _call_openai(resume_text: str) -> Optional[dict]:
    """Call OpenAI API."""
    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("openai not installed. Run: pip install openai")
        return None

    if not OPENAI_API_KEY:
        logger.info("No OPENAI_API_KEY set. Skipping LLM assessment.")
        return None

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=LLM_MODEL if "gpt" in LLM_MODEL else "gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(resume_text)},
            ],
            temperature=LLM_TEMPERATURE,
            timeout=LLM_TIMEOUT,
            response_format={"type": "json_object"},
        )
        return _parse_response(response.choices[0].message.content)
    except Exception as e:
        logger.warning("OpenAI API call failed: %s", e)
        return None


def _parse_response(text: str) -> Optional[dict]:
    """Parse and validate the LLM's JSON response."""
    if not text:
        return None

    # Strip markdown code fences if present
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return _validate_assessment(data)
    except json.JSONDecodeError as e:
        logger.warning("LLM response is not valid JSON: %s", e)

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def assess_resume(resume_text: str, candidate_id: str = "") -> Optional[dict]:
    """
    Run LLM-based assessment on a resume.

    Parameters
    ----------
    resume_text : str
        Full resume text.
    candidate_id : str
        Identifier for caching (e.g., filename).

    Returns
    -------
    dict with structured assessment fields, or None if LLM is unavailable/failed.
    """
    # Check cache
    if candidate_id and candidate_id in _llm_cache:
        return _llm_cache[candidate_id]

    # Select provider
    if LLM_PROVIDER == "google":
        result = _call_google(resume_text)
    elif LLM_PROVIDER == "openai":
        result = _call_openai(resume_text)
    else:
        logger.warning("Unknown LLM provider: %s", LLM_PROVIDER)
        result = None

    # Cache result
    if candidate_id and result is not None:
        _llm_cache[candidate_id] = result

    return result


def is_llm_available() -> bool:
    """Check if an LLM provider is configured with an API key."""
    if LLM_PROVIDER == "google" and GOOGLE_API_KEY:
        return True
    if LLM_PROVIDER == "openai" and OPENAI_API_KEY:
        return True
    return False


def clear_cache():
    """Clear the LLM assessment cache."""
    _llm_cache.clear()
