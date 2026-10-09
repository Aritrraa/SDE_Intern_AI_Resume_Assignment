"""
Pipeline module — orchestrates the full resume screening pipeline.

Steps:
  1. Ingest resumes from input directory
  2. Extract text and candidate info
  3. Apply hard eligibility filters (Python + AI evidence)
  4. Score eligible candidates (40/30/15/10/5 weights)
  5. Enrich with GitHub data when available
  6. Rank and produce final output with batch statistics
"""

import logging
from typing import Optional

from src.ingestion import ingest_resumes
from src.extractor import extract_candidate_info
from src.eligibility import check_eligibility
from src.scoring import compute_total_score
from src.github_enrichment import enrich_github
from src.llm_assessment import assess_resume, is_llm_available

logger = logging.getLogger(__name__)


def _build_project_summary(text: str, ai_evidence: list[str]) -> str:
    """Build a short project summary from resume text and AI evidence."""
    text_lower = text.lower()

    # Look for key project indicators
    indicators = []
    if "rag" in text_lower or "retrieval" in text_lower:
        indicators.append("RAG/retrieval system")
    if "agent" in text_lower or "agentic" in text_lower:
        indicators.append("agentic workflow")
    if "langchain" in text_lower:
        indicators.append("LangChain integration")
    if "langgraph" in text_lower:
        indicators.append("LangGraph state machine")
    if "llamaindex" in text_lower or "llama_index" in text_lower:
        indicators.append("LlamaIndex usage")
    if "fine-tuning" in text_lower or "fine tuning" in text_lower:
        indicators.append("model fine-tuning")
    if "fastapi" in text_lower:
        indicators.append("FastAPI backend")
    if "deep learning" in text_lower or "neural network" in text_lower:
        indicators.append("deep learning model")
    if "computer vision" in text_lower:
        indicators.append("computer vision")
    if "nlp" in text_lower or "natural language" in text_lower:
        indicators.append("NLP application")
    if "chatbot" in text_lower:
        indicators.append("chatbot implementation")
    if "docker" in text_lower:
        indicators.append("containerized deployment")
    if "machine learning" in text_lower or "ml model" in text_lower:
        indicators.append("ML model development")

    if indicators:
        return "Projects include: " + ", ".join(indicators[:5]) + "."
    elif ai_evidence:
        return f"AI/ML keywords present: {', '.join(ai_evidence[:5])}."
    return "No detailed project information extracted."


def run_pipeline(input_dir: str, enable_github: bool = True, enable_llm: bool = False) -> dict:
    """
    Run the full resume screening pipeline.

    Parameters
    ----------
    input_dir : str
        Path to directory containing resume files.
    enable_github : bool
        Whether to attempt GitHub enrichment (default: True).
    enable_llm : bool
        Whether to attempt LLM project assessment (default: False).

    Returns
    -------
    dict with:
        ranked_candidates: list[dict]  — eligible candidates, highest score first
        rejected_candidates: list[dict] — ineligible candidates with reasons
        failed_files: list[dict] — files that could not be parsed
        batch_summary: dict — aggregate statistics
    """
    logger.info("Starting pipeline. Input directory: %s", input_dir)

    # Step 1: Ingest
    raw_resumes = ingest_resumes(input_dir)
    logger.info("Ingested %d files", len(raw_resumes))

    eligible_candidates: list[dict] = []
    rejected_candidates: list[dict] = []
    failed_files: list[dict] = []

    for resume in raw_resumes:
        filename = resume["filename"]

        # Handle parse failures
        if resume["text"] is None:
            failed_files.append({
                "filename": filename,
                "error": resume.get("parse_error", "Unknown error"),
            })
            continue

        text = resume["text"]

        # Step 2: Extract candidate info
        info = extract_candidate_info(text, filename)

        # Step 3: Eligibility check
        elig = check_eligibility(text, info["skills"])

        if not elig["eligible"]:
            rejected_candidates.append({
                "candidate_name": info["name"],
                "source_file": filename,
                "eligible": False,
                "rejection_reasons": elig["rejection_reasons"],
                "matched_skills": elig["matched_skills"],
                "python_evidence": elig["python_evidence"],
                "ai_evidence": elig["ai_evidence"],
            })
            continue

        # Step 4 & 5: GitHub enrichment
        github_data = {"github_score": 0, "github_summary": "No GitHub profile provided",
                       "enrichment_status": "skipped", "error": None}
        if enable_github and info.get("github_username"):
            github_data = enrich_github(info["github_username"])

        # Step 4: Score (Deterministic baseline)
        score_result = compute_total_score(
            text=text,
            ai_evidence=elig["ai_evidence"],
            python_evidence=elig["python_evidence"],
            github_score=github_data["github_score"],
            github_summary=github_data["github_summary"],
        )

        # Build project summary
        project_summary = _build_project_summary(text, elig["ai_evidence"])
        llm_assessment = None

        # LLM Integration
        if enable_llm and is_llm_available():
            llm_result = assess_resume(text, candidate_id=filename)
            if llm_result:
                llm_assessment = llm_result
                
                # Merge LLM insights into the deterministic outputs without overwriting scores
                if llm_result.get("project_summary"):
                    project_summary = llm_result["project_summary"]
                
                score_result["strengths"].extend(
                    [s for s in llm_result.get("engineering_strengths", []) if s not in score_result["strengths"]]
                )
                score_result["concerns"].extend(
                    [c for c in llm_result.get("concerns", []) if c not in score_result["concerns"]]
                )
                
                # The LLM assesses if it's a thin wrapper. If deterministic logic didn't catch it,
                # but the LLM is confident and provided reasoning, we log it as a concern, but we don't
                # strictly subtract points to preserve the deterministic bounds unless explicitly coded.
                if llm_result.get("has_thin_wrapper_indicators"):
                    score_result["concerns"].append("LLM Flag: " + llm_result.get("thin_wrapper_reasoning", "Appears to be a thin wrapper or tutorial project."))

        candidate_result = {
            "candidate_name": info["name"],
            "source_file": filename,
            "email": info["email"],
            "eligible": True,
            "total_score": score_result["total_score"],
            "score_breakdown": score_result["score_breakdown"],
            "matched_skills": info["skills"],
            "project_summary": project_summary,
            "github_url": info["github_url"],
            "github_summary": github_data["github_summary"],
            "github_enrichment_status": github_data["enrichment_status"],
            "strengths": score_result["strengths"],
            "concerns": score_result["concerns"],
            "penalties": score_result["penalties"],
            "evidence": score_result["evidence"],
            "llm_assessment": llm_assessment,
        }

        eligible_candidates.append(candidate_result)

    # Step 6: Rank eligible candidates
    eligible_candidates.sort(key=lambda c: c["total_score"], reverse=True)
    for rank, candidate in enumerate(eligible_candidates, start=1):
        candidate["rank"] = rank

    # Batch summary
    batch_summary = {
        "total_resumes": len(raw_resumes),
        "successfully_parsed": len(raw_resumes) - len(failed_files),
        "eligible": len(eligible_candidates),
        "rejected": len(rejected_candidates),
        "failed_unreadable": len(failed_files),
    }

    logger.info(
        "Pipeline complete. Total: %d, Parsed: %d, Eligible: %d, Rejected: %d, Failed: %d",
        batch_summary["total_resumes"],
        batch_summary["successfully_parsed"],
        batch_summary["eligible"],
        batch_summary["rejected"],
        batch_summary["failed_unreadable"],
    )

    return {
        "ranked_candidates": eligible_candidates,
        "rejected_candidates": rejected_candidates,
        "failed_files": failed_files,
        "batch_summary": batch_summary,
    }
