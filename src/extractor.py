"""
Candidate information extraction — deterministic regex/heuristic approach.

Extracts name, email, phone, GitHub URL, LinkedIn URL, skills, and
basic project information from raw resume text.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_PATTERN = re.compile(r"(?:\+?\d{1,3}[\s\-]?)?\(?\d{3,5}\)?[\s\-]?\d{3,4}[\s\-]?\d{3,4}")
GITHUB_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9\-]+)(?:/[a-zA-Z0-9\-]*)?",
    re.IGNORECASE,
)
LINKEDIN_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?linkedin\.com/in/([a-zA-Z0-9\-]+)",
    re.IGNORECASE,
)


def _extract_email(text: str) -> Optional[str]:
    match = EMAIL_PATTERN.search(text)
    return match.group(0) if match else None


def _extract_name(text: str) -> str:
    """
    Heuristic: Filter out obvious non-name lines. If an email is found, prefer
    a valid line that shares parts of the email prefix. Otherwise, return the
    first valid line.
    """
    valid_lines = []
    
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Skip lines that look like headers/labels rather than names
        lower = line.lower()
        if any(lower.startswith(prefix) for prefix in [
            "resume", "curriculum", "cv", "objective", "summary",
            "phone", "email", "address", "http", "www.",
        ]):
            continue
        # Skip very long lines (probably a paragraph, not a name)
        if len(line) > 60:
            continue
        # Skip very short lines (artifacts, single chars like '/')
        alpha_chars = sum(c.isalpha() for c in line)
        if alpha_chars < 2:
            continue
        # Skip lines that are mostly digits (phone numbers etc.)
        if sum(c.isdigit() for c in line) > len(line) * 0.3:
            continue
        # Skip lines that end with a period (sentence fragments, not names)
        if line.rstrip().endswith('.'):
            continue
        # Skip lines containing a colon (typically labels/fields, not names)
        if ':' in line:
            continue
        # Skip lines containing an @ symbol (emails/social handles)
        if '@' in line:
            continue
        # Skip lines containing common non-name words indicating paragraphs,
        # certifications, or section content rather than a person's name
        non_name_words = [
            "experience", "motivated", "passionate", "proficient",
            "simulation", "certification", "project", "develop",
            "engineer", "collaborate", "contribute", "skills",
            "ability", "knowledge", "seeking", "dedicated",
            "bachelor", "college", "university", "institute", "school",
            "secondary", "technology", "language", "database", "react",
            "english", "tamil", "telugu", "hindi", "visual", "jupyter",
            "collab", "basic", "master", "applications"
        ]
        if any(word in lower for word in non_name_words):
            continue
        # Skip lines with too many words (names rarely exceed 5 words)
        words = line.split()
        if len(words) > 6:
            continue
            
        valid_lines.append(line.strip("| \t\r\n"))
        
    if not valid_lines:
        return "Unknown"
        
    # Prefer a line that matches the email prefix (e.g. jdoe@ -> John Doe)
    email = _extract_email(text)
    if email:
        prefix = email.split('@')[0].lower()
        parts = [p for p in re.split(r'[^a-z]+', prefix) if len(p) > 2]
        for line in valid_lines:
            lower_line = line.lower()
            if any(part in lower_line for part in parts):
                return line

    # Fallback to the first valid line
    return valid_lines[0]




def _extract_phone(text: str) -> Optional[str]:
    match = PHONE_PATTERN.search(text)
    return match.group(0).strip() if match else None


def _extract_github_url(text: str) -> Optional[str]:
    match = GITHUB_PATTERN.search(text)
    if match:
        username = match.group(1)
        # Filter out common false positives
        if username.lower() in {"features", "about", "blog", "topics", "explore", "settings", "login", "signup"}:
            return None
        return f"https://github.com/{username}"
    return None


def _extract_github_username(text: str) -> Optional[str]:
    match = GITHUB_PATTERN.search(text)
    if match:
        username = match.group(1)
        if username.lower() in {"features", "about", "blog", "topics", "explore", "settings", "login", "signup"}:
            return None
        return username
    return None


def _extract_linkedin_url(text: str) -> Optional[str]:
    match = LINKEDIN_PATTERN.search(text)
    if match:
        return f"https://linkedin.com/in/{match.group(1)}"
    return None


def _extract_skills_section(text: str) -> list[str]:
    """
    Try to find a 'Skills' or 'Technical Skills' section and pull skill tokens.
    Falls back to scanning the full text for known keywords.
    """
    from src.config import (
        PYTHON_KEYWORDS, AI_KEYWORDS, PYTHON_BACKEND_KEYWORDS,
        CLOUD_DEPLOY_KEYWORDS, ENGINEERING_DEPTH_KEYWORDS,
    )
    all_keywords = set(
        PYTHON_KEYWORDS + AI_KEYWORDS + PYTHON_BACKEND_KEYWORDS +
        CLOUD_DEPLOY_KEYWORDS + ENGINEERING_DEPTH_KEYWORDS
    )

    text_lower = text.lower()
    found = []
    for kw in all_keywords:
        kw_lower = kw.lower()
        if len(kw_lower) <= 4:
            if re.search(r'\b' + re.escape(kw_lower) + r'\b', text_lower):
                found.append(kw)
        else:
            if kw_lower in text_lower:
                found.append(kw)
    return sorted(set(found))


def _extract_projects(text: str) -> list[str]:
    """
    Heuristic extraction of project titles / descriptions.
    Looks for a 'Projects' section and grabs lines that look like project headers.
    """
    projects: list[str] = []
    lines = text.split("\n")
    in_projects = False

    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()

        # Detect start of projects section
        if re.match(r"^(projects?|personal projects?|academic projects?|key projects?)\s*$", lower):
            in_projects = True
            continue

        # Detect end of projects section (next major heading)
        if in_projects and re.match(
            r"^(education|experience|work experience|skills|technical skills|"
            r"certifications?|awards?|achievements?|publications?|interests?|"
            r"hobbies|references?|summary|objective|contact)\s*$",
            lower,
        ):
            in_projects = False
            continue

        if in_projects and stripped:
            # Project title lines are often short-ish and may contain | or —
            if len(stripped) < 200 and not stripped.startswith("•"):
                # Likely a project title/header
                projects.append(stripped)
            elif stripped.startswith("•") or stripped.startswith("-"):
                # Bullet point — append as project detail
                projects.append(stripped)

    return projects


def extract_candidate_info(text: str, filename: str = "") -> dict:
    """
    Extract structured candidate information from resume text.

    Returns dict with: name, email, phone, github_url, github_username,
    linkedin_url, skills, projects, source_file.
    """
    return {
        "name": _extract_name(text),
        "email": _extract_email(text),
        "phone": _extract_phone(text),
        "github_url": _extract_github_url(text),
        "github_username": _extract_github_username(text),
        "linkedin_url": _extract_linkedin_url(text),
        "skills": _extract_skills_section(text),
        "projects": _extract_projects(text),
        "source_file": filename,
    }
