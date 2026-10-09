"""
Tests for the AI Resume Screening & Ranking System.

Covers:
  - Eligibility (Python + AI hard filter)
  - Scoring (bounds, weights, penalties)
  - Ranking (order, completeness)
  - Malformed input handling
  - GitHub enrichment (with mocked API)
  - Pipeline integration
"""

import json
import os
import pytest
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Test data: synthetic resume texts
# ---------------------------------------------------------------------------

ELIGIBLE_RESUME = """
John Doe
Email: john@example.com
GitHub: github.com/johndoe
Phone: +91-9876543210

Summary
Experienced Python developer with strong background in AI/ML and backend systems.

Skills
Python, FastAPI, LangChain, Docker, PostgreSQL, Redis, PyTorch, RAG

Work Experience
AI Engineer — TechCorp
Jan 2024 – Present
• Built a retrieval-augmented generation (RAG) pipeline using LangChain and Pinecone
  for semantic document search, processing 10k+ documents daily.
• Developed a multi-agent workflow using LangGraph with state management and tool calling.
• Implemented async FastAPI backend with PostgreSQL and Redis caching.
• Deployed using Docker on GCP Cloud Run with CI/CD via GitHub Actions.
• Designed evaluation pipeline to measure retrieval quality and agent performance.

Projects
AI Document Assistant | Python, LangChain, FastAPI, Pinecone
• Built end-to-end RAG system with custom retrieval pipeline and embedding generation.
• Implemented state management and orchestration for multi-step agent workflows.

Education
B.Tech Computer Science — IIT Delhi
"""

PYTHON_ONLY_RESUME = """
Jane Smith
Email: jane@example.com

Skills
Python, Django, Flask, PostgreSQL, Redis, Docker

Work Experience
Backend Developer — WebCorp
Built REST APIs using Django and Flask. Deployed on AWS with Docker.
Implemented caching with Redis and database optimization.

Education
B.Tech CS — BITS Pilani
"""

AI_ONLY_RESUME = """
Bob Wilson
Email: bob@example.com

Skills
Java, TensorFlow, Deep Learning, Neural Networks, NLP

Work Experience
ML Engineer — DataCo
Built deep learning models using TensorFlow in Java.
Implemented NLP pipeline for text classification.

Education
M.Tech AI — IISc Bangalore
"""

NO_PYTHON_NO_AI_RESUME = """
Alice Brown
Email: alice@example.com

Skills
JavaScript, React, Next.js, Node.js, MongoDB, Express.js

Work Experience
Frontend Developer — DesignCo
Built responsive web applications using React and Next.js.
Implemented REST APIs with Express.js and MongoDB.

Education
B.Tech IT — VIT Vellore
"""

THIN_WRAPPER_RESUME = """
Tom Harris
Email: tom@example.com
GitHub: github.com/tomharris

Skills
Python, OpenAI, GPT, LangChain, Flask

Projects
Simple Chatbot | Python, OpenAI API
• Made a basic chatbot using OpenAI API call with simple prompt.
• Tutorial project from online course.
• Demo project for learning purposes.

Weather App | Python, Flask
• Simple weather app using API wrapper around weather service.
• Todo app with basic CRUD operations.

Education
B.Tech CS — Some University
"""

STRONG_AI_RESUME = """
Priya Sharma
Email: priya@example.com
GitHub: github.com/priyasharma

Summary
AI/ML engineer specializing in agentic AI systems and production ML pipelines.

Skills
Python, FastAPI, LangChain, LangGraph, RAG, Vector Search, Docker, GCP,
PostgreSQL, Redis, PyTorch, Transformers, Pytest

Work Experience
Senior AI Engineer — AIStartup
Jan 2024 – Present
• Architected production RAG pipeline with custom retrieval, embedding generation,
  and evaluation framework using LangChain and Pinecone.
• Built multi-agent orchestration system using LangGraph with state machines,
  tool calling, and error handling for complex workflow automation.
• Developed async FastAPI microservice backend with PostgreSQL, Redis caching,
  and comprehensive testing using pytest.
• Deployed end-to-end system on GCP using Docker and Kubernetes with CI/CD.
• Implemented monitoring with Prometheus and Grafana for observability.

Projects
Agentic Document Processor | Python, LangGraph, FastAPI
• Built stateful agentic workflow with retrieval, tool calling, and evaluation.
• Custom pipeline with data processing, state management, and backend logic.
• Implemented retry logic, circuit breaker, and rate limiting for reliability.

Production ML Pipeline | PyTorch, FastAPI, Docker
• End-to-end ML training and deployment pipeline with fine-tuning.
• Automated evaluation and monitoring in production environment.

Education
M.Tech AI — IIT Bombay
"""


# ---------------------------------------------------------------------------
# Eligibility Tests
# ---------------------------------------------------------------------------

class TestEligibility:
    def test_eligible_candidate(self):
        from src.eligibility import check_eligibility
        result = check_eligibility(ELIGIBLE_RESUME)
        assert result["eligible"] is True
        assert len(result["rejection_reasons"]) == 0
        assert len(result["python_evidence"]) > 0
        assert len(result["ai_evidence"]) > 0

    def test_python_only_rejected(self):
        from src.eligibility import check_eligibility
        result = check_eligibility(PYTHON_ONLY_RESUME)
        assert result["eligible"] is False
        assert "No AI/agentic project evidence" in result["rejection_reasons"]
        assert len(result["python_evidence"]) > 0

    def test_ai_only_rejected(self):
        from src.eligibility import check_eligibility
        result = check_eligibility(AI_ONLY_RESUME)
        assert result["eligible"] is False
        assert "No evidence of Python stack" in result["rejection_reasons"]
        assert len(result["ai_evidence"]) > 0

    def test_no_python_no_ai_rejected(self):
        from src.eligibility import check_eligibility
        result = check_eligibility(NO_PYTHON_NO_AI_RESUME)
        assert result["eligible"] is False
        assert len(result["rejection_reasons"]) == 2

    def test_empty_text(self):
        from src.eligibility import check_eligibility
        result = check_eligibility("")
        assert result["eligible"] is False
        assert len(result["rejection_reasons"]) == 2

    def test_mixed_skills_with_python_and_ai(self):
        """Candidate with JS/React + Python + AI should be eligible."""
        from src.eligibility import check_eligibility
        text = """
        Skills: JavaScript, React, Python, LangChain, RAG, Docker
        Built a RAG pipeline using Python and LangChain.
        Also developed React frontend for the application.
        """
        result = check_eligibility(text)
        assert result["eligible"] is True


# ---------------------------------------------------------------------------
# Scoring Tests
# ---------------------------------------------------------------------------

class TestScoring:
    def test_score_bounds(self):
        """Total score must be between 0 and 100."""
        from src.scoring import compute_total_score
        result = compute_total_score(ELIGIBLE_RESUME, ["langchain", "rag"], ["python", "fastapi"])
        assert 0 <= result["total_score"] <= 100

    def test_score_breakdown_sums_correctly(self):
        """Individual category scores should not exceed their max weights."""
        from src.scoring import compute_total_score
        from src.config import SCORING_WEIGHTS
        result = compute_total_score(STRONG_AI_RESUME, ["langchain", "rag"], ["python", "fastapi"])
        bd = result["score_breakdown"]
        assert bd["ai_project_depth"] <= SCORING_WEIGHTS["ai_project_depth"]
        assert bd["python_backend"] <= SCORING_WEIGHTS["python_backend"]
        assert bd["cloud_fullstack"] <= SCORING_WEIGHTS["cloud_fullstack"]
        assert bd["github"] <= SCORING_WEIGHTS["github"]
        assert bd["engineering_depth"] <= SCORING_WEIGHTS["engineering_depth"]

    def test_strong_candidate_scores_higher(self):
        """A strong AI candidate should score higher than a thin wrapper."""
        from src.scoring import compute_total_score
        strong = compute_total_score(STRONG_AI_RESUME, ["langchain", "rag", "langgraph"], ["python", "fastapi"])
        weak = compute_total_score(THIN_WRAPPER_RESUME, ["openai", "gpt"], ["python"])
        assert strong["total_score"] > weak["total_score"]

    def test_thin_wrapper_penalties_applied(self):
        """Thin wrapper projects should receive penalties."""
        from src.scoring import score_ai_project_depth
        result = score_ai_project_depth(THIN_WRAPPER_RESUME, ["openai", "gpt"])
        assert len(result.get("penalties", [])) > 0

    def test_score_with_github(self):
        """GitHub score should be added to the total."""
        from src.scoring import compute_total_score
        without_gh = compute_total_score(ELIGIBLE_RESUME, ["langchain"], ["python"], github_score=0)
        with_gh = compute_total_score(ELIGIBLE_RESUME, ["langchain"], ["python"], github_score=8)
        assert with_gh["total_score"] > without_gh["total_score"]

    def test_github_score_capped_at_10(self):
        """GitHub contribution must be capped at 10."""
        from src.scoring import compute_total_score
        result = compute_total_score(ELIGIBLE_RESUME, ["langchain"], ["python"], github_score=20)
        assert result["score_breakdown"]["github"] <= 10

    def test_empty_text_score(self):
        """Empty text should produce 0 score without crashing."""
        from src.scoring import compute_total_score
        result = compute_total_score("", [], [])
        assert result["total_score"] == 0

    def test_strengths_and_concerns_present(self):
        """Score result should include strengths and concerns."""
        from src.scoring import compute_total_score
        result = compute_total_score(STRONG_AI_RESUME, ["langchain", "rag"], ["python", "fastapi"])
        assert isinstance(result["strengths"], list)
        assert isinstance(result["concerns"], list)


# ---------------------------------------------------------------------------
# Extractor Tests
# ---------------------------------------------------------------------------

class TestExtractor:
    def test_extract_name(self):
        from src.extractor import extract_candidate_info
        info = extract_candidate_info(ELIGIBLE_RESUME)
        assert info["name"] == "John Doe"

    def test_extract_name_candidate_20(self):
        """Must not extract 'Programming Language: Python' as name."""
        from src.extractor import extract_candidate_info
        text = "Programming Language: Python\nReact Native Basic\nDatabase: SQL\nPRIYA R"
        info = extract_candidate_info(text)
        assert info["name"] not in ("Programming Language: Python", "Database: SQL")

    def test_extract_name_candidate_21(self):
        """Must not extract 'Higher Secondary: Science- PCMB' as name."""
        from src.extractor import extract_candidate_info
        text = "SUMMARY\nSoftware Engineering Job Simulation |\nHigher Secondary: Science- PCMB\nMANOJ KUMAR"
        info = extract_candidate_info(text)
        assert info["name"] not in ("Higher Secondary: Science- PCMB", "Software Engineering Job Simulation |", "SUMMARY")

    def test_extract_email(self):
        from src.extractor import extract_candidate_info
        info = extract_candidate_info(ELIGIBLE_RESUME)
        assert info["email"] == "john@example.com"

    def test_extract_github(self):
        from src.extractor import extract_candidate_info
        info = extract_candidate_info(ELIGIBLE_RESUME)
        assert info["github_url"] == "https://github.com/johndoe"
        assert info["github_username"] == "johndoe"

    def test_extract_no_github(self):
        from src.extractor import extract_candidate_info
        info = extract_candidate_info(PYTHON_ONLY_RESUME)
        assert info["github_url"] is None

    def test_skills_extracted(self):
        from src.extractor import extract_candidate_info
        info = extract_candidate_info(ELIGIBLE_RESUME)
        assert len(info["skills"]) > 0


# ---------------------------------------------------------------------------
# Ingestion Tests
# ---------------------------------------------------------------------------

class TestIngestion:
    def test_nonexistent_directory(self):
        from src.ingestion import ingest_resumes
        with pytest.raises(FileNotFoundError):
            ingest_resumes("/nonexistent/path")

    def test_empty_directory(self, tmp_path):
        from src.ingestion import ingest_resumes
        result = ingest_resumes(str(tmp_path))
        assert len(result) == 0

    def test_malformed_pdf(self, tmp_path):
        """A corrupted PDF should not crash the batch."""
        from src.ingestion import ingest_resumes
        bad_file = tmp_path / "bad.pdf"
        bad_file.write_bytes(b"not a real pdf content")
        result = ingest_resumes(str(tmp_path))
        assert len(result) == 1
        assert result[0]["text"] is None or result[0]["parse_error"] is not None

    def test_unsupported_extension_skipped(self, tmp_path):
        """Files with unsupported extensions should be skipped."""
        from src.ingestion import ingest_resumes
        (tmp_path / "file.xyz").write_text("content")
        result = ingest_resumes(str(tmp_path))
        assert len(result) == 0


# ---------------------------------------------------------------------------
# GitHub Enrichment Tests (mocked)
# ---------------------------------------------------------------------------

class TestGitHubEnrichment:
    def test_no_username(self):
        from src.github_enrichment import enrich_github, clear_cache
        clear_cache()
        result = enrich_github("")
        assert result["github_score"] == 0
        assert result["enrichment_status"] == "skipped"

    @patch("src.github_enrichment.requests.get")
    def test_successful_enrichment(self, mock_get):
        from src.github_enrichment import enrich_github, clear_cache
        clear_cache()

        # Mock events response
        events_response = MagicMock()
        events_response.status_code = 200
        events_response.json.return_value = [
            {"created_at": "2026-09-15T10:00:00Z", "type": "PushEvent"},
            {"created_at": "2026-09-14T10:00:00Z", "type": "PushEvent"},
            {"created_at": "2026-09-13T10:00:00Z", "type": "PushEvent"},
            {"created_at": "2026-09-12T10:00:00Z", "type": "PushEvent"},
            {"created_at": "2026-09-11T10:00:00Z", "type": "PushEvent"},
        ]

        # Mock repos response
        repos_response = MagicMock()
        repos_response.status_code = 200
        repos_response.json.return_value = [
            {"name": "ai-project", "language": "Python", "description": "RAG chatbot"},
            {"name": "web-app", "language": "Python", "description": "Flask app"},
            {"name": "ml-pipeline", "language": "Python", "description": "ML training"},
        ]

        mock_get.side_effect = [events_response, repos_response]

        result = enrich_github("testuser")
        assert result["enrichment_status"] == "success"
        assert 0 <= result["github_score"] <= 10

    @patch("src.github_enrichment.requests.get")
    def test_api_failure_graceful(self, mock_get):
        from src.github_enrichment import enrich_github, clear_cache
        clear_cache()

        mock_get.side_effect = Exception("Network error")
        result = enrich_github("failuser")
        assert result["enrichment_status"] == "failed"
        assert result["github_score"] == 0

    @patch("src.github_enrichment.requests.get")
    def test_rate_limited(self, mock_get):
        from src.github_enrichment import enrich_github, clear_cache
        clear_cache()

        response = MagicMock()
        response.status_code = 403
        mock_get.return_value = response

        result = enrich_github("ratelimited")
        # Should not crash, should return 0 score
        assert result["github_score"] == 0

    @patch("src.github_enrichment.requests.get")
    def test_caching(self, mock_get):
        from src.github_enrichment import enrich_github, clear_cache
        clear_cache()

        response = MagicMock()
        response.status_code = 200
        response.json.return_value = []
        mock_get.return_value = response

        # First call
        enrich_github("cachetest")
        # Second call should use cache
        enrich_github("cachetest")

        # Should only make 2 API calls (events + repos), not 4
        assert mock_get.call_count == 2


# ---------------------------------------------------------------------------
# Ranking Tests
# ---------------------------------------------------------------------------

class TestRanking:
    def test_ranking_order(self):
        """Eligible candidates should be ranked by score descending."""
        from src.pipeline import run_pipeline
        import tempfile, shutil

        # Create temp dir with synthetic resumes as text files
        tmp = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmp, "strong.txt"), "w") as f:
                f.write(STRONG_AI_RESUME)
            with open(os.path.join(tmp, "eligible.txt"), "w") as f:
                f.write(ELIGIBLE_RESUME)
            with open(os.path.join(tmp, "weak.txt"), "w") as f:
                f.write(THIN_WRAPPER_RESUME)

            results = run_pipeline(tmp, enable_github=False)

            ranked = results["ranked_candidates"]
            if len(ranked) >= 2:
                for i in range(len(ranked) - 1):
                    assert ranked[i]["total_score"] >= ranked[i + 1]["total_score"]
        finally:
            shutil.rmtree(tmp)

    def test_all_candidates_accounted(self):
        """Every input file should appear in ranked, rejected, or failed."""
        from src.pipeline import run_pipeline
        import tempfile, shutil

        tmp = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmp, "a.txt"), "w") as f:
                f.write(ELIGIBLE_RESUME)
            with open(os.path.join(tmp, "b.txt"), "w") as f:
                f.write(NO_PYTHON_NO_AI_RESUME)
            with open(os.path.join(tmp, "c.pdf"), "wb") as f:
                f.write(b"corrupted pdf")

            results = run_pipeline(tmp, enable_github=False)
            summary = results["batch_summary"]
            total = summary["eligible"] + summary["rejected"] + summary["failed_unreadable"]
            assert total == summary["total_resumes"]
        finally:
            shutil.rmtree(tmp)


# ---------------------------------------------------------------------------
# Pipeline Integration Test
# ---------------------------------------------------------------------------

class TestPipelineIntegration:
    def test_full_pipeline_with_synthetic_data(self):
        """Run the complete pipeline with synthetic resumes."""
        from src.pipeline import run_pipeline
        import tempfile, shutil

        tmp = tempfile.mkdtemp()
        try:
            # Create various test resumes
            resumes = {
                "strong.txt": STRONG_AI_RESUME,
                "eligible.txt": ELIGIBLE_RESUME,
                "python_only.txt": PYTHON_ONLY_RESUME,
                "ai_only.txt": AI_ONLY_RESUME,
                "no_match.txt": NO_PYTHON_NO_AI_RESUME,
                "thin.txt": THIN_WRAPPER_RESUME,
            }
            for name, content in resumes.items():
                with open(os.path.join(tmp, name), "w") as f:
                    f.write(content)

            results = run_pipeline(tmp, enable_github=False)

            # Verify structure
            assert "ranked_candidates" in results
            assert "rejected_candidates" in results
            assert "failed_files" in results
            assert "batch_summary" in results

            # Verify batch summary
            summary = results["batch_summary"]
            assert summary["total_resumes"] == 6
            assert summary["eligible"] >= 2  # at least strong + eligible
            assert summary["rejected"] >= 2  # at least python_only + no_match

            # Verify eligible candidates have required fields
            for c in results["ranked_candidates"]:
                assert "rank" in c
                assert "candidate_name" in c
                assert "total_score" in c
                assert "score_breakdown" in c
                assert "eligible" in c and c["eligible"] is True
                assert "matched_skills" in c
                assert "strengths" in c
                assert "concerns" in c

            # Verify rejected candidates have reasons
            for c in results["rejected_candidates"]:
                assert "rejection_reasons" in c
                assert len(c["rejection_reasons"]) > 0

            # Verify JSON serializable
            json.dumps(results)
        finally:
            shutil.rmtree(tmp)


# ---------------------------------------------------------------------------
# Keyword Boundary Regression Tests
# ---------------------------------------------------------------------------

class TestKeywordBoundary:
    """Regression tests for word-boundary matching of short keywords."""

    def test_rag_false_positive_storage(self):
        """'rag' must NOT match inside 'storage'."""
        from src.eligibility import _find_keyword_matches
        text = "integrated cloud storage buckets for file uploads"
        matches = _find_keyword_matches(text.lower(), ["rag"])
        assert "rag" not in matches

    def test_rag_false_positive_coverage(self):
        """'rag' must NOT match inside 'coverage'."""
        from src.eligibility import _find_keyword_matches
        text = "achieved 90% test coverage across all modules"
        matches = _find_keyword_matches(text.lower(), ["rag"])
        assert "rag" not in matches

    def test_rag_false_positive_leverage(self):
        """'rag' must NOT match inside 'leverage'."""
        from src.eligibility import _find_keyword_matches
        text = "leveraged Kubernetes for container orchestration"
        matches = _find_keyword_matches(text.lower(), ["rag"])
        assert "rag" not in matches

    def test_rag_false_positive_kharagpur(self):
        """'rag' must NOT match inside 'Kharagpur'."""
        from src.eligibility import _find_keyword_matches
        text = "JAYA NANDI Kharagpur, West Bengal"
        matches = _find_keyword_matches(text.lower(), ["rag"])
        assert "rag" not in matches

    def test_rag_true_positive_standalone(self):
        """'rag' MUST match as a standalone word."""
        from src.eligibility import _find_keyword_matches
        text = "Built a RAG pipeline using LangChain"
        matches = _find_keyword_matches(text.lower(), ["rag"])
        assert "rag" in matches

    def test_rag_true_positive_with_punctuation(self):
        """'rag' MUST match next to punctuation (e.g. 'RAG,' or 'RAG)')."""
        from src.eligibility import _find_keyword_matches
        text = "implemented RAG, vector search, and embeddings"
        matches = _find_keyword_matches(text.lower(), ["rag"])
        assert "rag" in matches

    def test_rag_true_positive_hyphenated_phrase(self):
        """'retrieval-augmented' should match as a longer keyword."""
        from src.eligibility import _find_keyword_matches
        text = "retrieval-augmented generation for document search"
        matches = _find_keyword_matches(text.lower(), ["retrieval-augmented"])
        assert "retrieval-augmented" in matches

    def test_gpt_false_positive(self):
        """'gpt' must NOT match inside unrelated words."""
        from src.eligibility import _find_keyword_matches
        text = "used encrypted storage for security"
        matches = _find_keyword_matches(text.lower(), ["gpt"])
        assert "gpt" not in matches

    def test_gpt_true_positive(self):
        """'gpt' MUST match standalone."""
        from src.eligibility import _find_keyword_matches
        text = "integrated GPT-4 for text generation"
        matches = _find_keyword_matches(text.lower(), ["gpt"])
        assert "gpt" in matches

    def test_nlp_true_positive(self):
        """'nlp' MUST match standalone."""
        from src.eligibility import _find_keyword_matches
        text = "built an NLP pipeline for text classification"
        matches = _find_keyword_matches(text.lower(), ["nlp"])
        assert "nlp" in matches

    def test_scoring_rag_false_positive(self):
        """Scoring _count_keyword_hits must also reject 'rag' in 'storage'."""
        from src.scoring import _count_keyword_hits
        text = "cloud storage and data coverage analysis"
        count, hits = _count_keyword_hits(text.lower(), ["rag"])
        assert count == 0
        assert "rag" not in hits

    def test_scoring_rag_true_positive(self):
        """Scoring _count_keyword_hits must find standalone 'rag'."""
        from src.scoring import _count_keyword_hits
        text = "built a RAG system with vector retrieval"
        count, hits = _count_keyword_hits(text.lower(), ["rag"])
        assert count == 1
        assert "rag" in hits

    def test_context_detection_rag_standalone(self):
        """_has_project_context must find standalone 'rag' near action verbs."""
        from src.scoring import _has_project_context
        text = "built a production RAG pipeline with custom retrieval"
        assert _has_project_context(text.lower(), "rag") is True

    def test_context_detection_rag_inside_storage(self):
        """_has_project_context must NOT find 'rag' inside 'storage'."""
        from src.scoring import _has_project_context
        text = "built a cloud storage system for file uploads"
        assert _has_project_context(text.lower(), "rag") is False

    def test_longer_keywords_still_substring_match(self):
        """Keywords longer than 4 chars should still use substring matching."""
        from src.eligibility import _find_keyword_matches
        text = "used langchain for building the pipeline"
        matches = _find_keyword_matches(text.lower(), ["langchain"])
        assert "langchain" in matches

    def test_eligibility_with_only_false_rag(self):
        """A candidate with only false 'rag' (from 'storage') should NOT get AI evidence."""
        from src.eligibility import check_eligibility
        text = """
        Python developer from Kharagpur.
        Skills: Python, Django, cloud storage, test coverage.
        Built REST APIs with high code coverage.
        """
        result = check_eligibility(text)
        assert result["eligible"] is False
        assert "rag" not in result["ai_evidence"]

    def test_eligibility_with_real_rag(self):
        """A candidate with real standalone 'RAG' MUST get AI evidence."""
        from src.eligibility import check_eligibility
        text = """
        Python developer specializing in AI.
        Built a RAG pipeline using Python and LangChain.
        Deployed vector search with Pinecone.
        """
        result = check_eligibility(text)
        assert result["eligible"] is True

# ---------------------------------------------------------------------------
# LLM Assessment Tests
# ---------------------------------------------------------------------------

class TestLLMAssessment:
    def test_llm_missing_api_key_fallback(self):
        """When no API key is set, assess_resume should return None and not crash."""
        from src.llm_assessment import assess_resume
        # Force clear keys for test
        with patch("src.llm_assessment.GOOGLE_API_KEY", ""), patch("src.llm_assessment.OPENAI_API_KEY", ""):
            result = assess_resume("Some text", candidate_id="test")
            assert result is None

    def test_llm_malformed_json_fallback(self):
        """When LLM returns malformed JSON, assess_resume should return None."""
        from src.llm_assessment import _parse_response
        result = _parse_response("This is not JSON")
        assert result is None

    def test_llm_valid_json_parsing(self):
        """Valid JSON should be parsed and missing fields filled with defaults."""
        from src.llm_assessment import _parse_response
        valid_json = '''
        {
          "project_summary": "Built a RAG pipeline.",
          "has_thin_wrapper_indicators": true
        }
        '''
        result = _parse_response(valid_json)
        assert result is not None
        assert result["project_summary"] == "Built a RAG pipeline."
        assert result["has_thin_wrapper_indicators"] is True
        # Missing fields should be empty lists/strings
        assert result["ai_implementation_evidence"] == []
        assert result["ai_depth_rating"] == ""
