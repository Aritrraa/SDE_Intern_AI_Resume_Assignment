import json
import os
from datetime import datetime

# Ensure docs directory exists
os.makedirs("docs", exist_ok=True)

# 2. Extract Data from JSON
with open('output/results.json', 'r', encoding='utf-8') as f:
    results = json.load(f)

summary = results['batch_summary']
top_candidates = results['ranked_candidates'][:5]

# 3. Create PDF with FPDF
from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("helvetica", "B", 10)
            self.set_text_color(100, 100, 100)
            self.cell(0, 10, "AI Resume Screening & Ranking System - Assessment Report", 0, 1, "R")
            self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")

    def chapter_title(self, title):
        self.set_font("helvetica", "B", 16)
        self.set_text_color(46, 125, 50) # Dark Green
        self.cell(0, 10, title, 0, 1, "L")
        self.ln(4)

    def chapter_body(self, text):
        text = text.encode('ascii', 'ignore').decode('ascii')
        self.set_font("helvetica", "", 11)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 6, text)
        self.ln(4)
        
    def add_bullet(self, text):
        text = text.encode('ascii', 'ignore').decode('ascii')
        self.set_font("helvetica", "", 11)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 6, f"- {text}")
        self.ln(2)

pdf = PDF()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()

# --- Page 1: Cover & Executive Summary ---
pdf.set_font("helvetica", "B", 24)
pdf.set_text_color(0, 0, 0)
pdf.ln(40)
pdf.cell(0, 15, "AI Resume Screening & Ranking System", 0, 1, "C")
pdf.set_font("helvetica", "I", 16)
pdf.set_text_color(100, 100, 100)
pdf.cell(0, 10, "SDE Intern Coding Assignment - Technical Assessment Report", 0, 1, "C")
pdf.ln(20)

pdf.set_font("helvetica", "", 12)
pdf.cell(0, 10, f"Date: {datetime.now().strftime('%B %d, %Y')}", 0, 1, "C")
pdf.cell(0, 10, "Author: Aritra Das", 0, 1, "C")
pdf.ln(30)

pdf.chapter_title("Executive Summary")
pdf.chapter_body(
    "This report documents the architecture, methodology, and results of the AI Resume Screening & Ranking System. "
    "The system automates the evaluation of software engineering candidate resumes against strict criteria: "
    "demonstrated Python proficiency and substantive AI/RAG/Agentic project experience. "
    "It implements a robust, deterministic pipeline that ingests resumes, extracts critical information, filters candidates based on hard requirements, "
    "scores them against a 100-point rubric, and enriches the data using the GitHub API and LLM-assisted semantic analysis."
)
pdf.chapter_body(
    "Technologies utilized: Python 3.12, PyMuPDF (Ingestion), Regex/Heuristics (Extraction), "
    "GitHub REST API (Enrichment), Google Gemini / OpenAI (LLM Assessment), Streamlit (Frontend Dashboard), and Pytest (Validation)."
)

# --- Page 2: Architecture ---
pdf.add_page()
pdf.chapter_title("Problem, Requirements, and Architecture")
pdf.chapter_body(
    "The core problem requires screening a batch of 50 resumes to reliably identify candidates capable of building "
    "production AI pipelines. It demands a defensible, bias-resistant methodology where mere keyword stuffing does not equate to engineering competence. "
    "The system must process PDFs, rank candidates mathematically, and provide explainable evidence for every score."
)
pdf.chapter_body("The implemented architecture strictly enforces a modular, linear workflow:")

pdf.set_font("helvetica", "B", 10)
pdf.cell(50, 10, "[1. PDF Ingestion]", border=1, align="C")
pdf.cell(10, 10, "->", align="C")
pdf.cell(50, 10, "[2. Text Extraction]", border=1, align="C")
pdf.cell(10, 10, "->", align="C")
pdf.cell(50, 10, "[3. Eligibility Gate]", border=1, align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(5)
pdf.cell(50, 10, "[4. Scoring (100 pts)]", border=1, align="C")
pdf.cell(10, 10, "<-", align="C")
pdf.cell(50, 10, "[5. Enrichment (GH/LLM)]", border=1, align="C")
pdf.cell(10, 10, "<-", align="C")
pdf.cell(50, 10, "[6. JSON Output]", border=1, align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(10)
pdf.ln(10)
pdf.chapter_body(
    "1. Ingestion: PyMuPDF extracts text directly from PDF bytes, handling unreadable files gracefully without crashing the batch.\n"
    "2. Extraction: Heuristic filters strip boilerplate to extract candidate names, emails, and GitHub URLs.\n"
    "3. Eligibility: A hard deterministic gate requiring both Python and AI evidence.\n"
    "4. Scoring: A 100-point evaluator measuring project context rather than just keyword presence.\n"
    "5. GitHub & LLM: Optional enrichment APIs that add qualitative depth and activity signals, designed with strict timeout fallbacks."
)

# --- Page 3: Methodology ---
pdf.add_page()
pdf.chapter_title("Eligibility and Ranking Methodology")
pdf.chapter_body(
    "Eligibility is strictly deterministic. A candidate must demonstrate both genuine Python evidence and meaningful AI/LLM/RAG/agentic evidence. "
    "This gate is not controlled by an LLM to prevent hallucinations from advancing unqualified candidates. "
    "Short acronyms like 'RAG' use word-boundary regular expressions to prevent false positives (e.g., matching inside the word 'storage')."
)

pdf.set_font("helvetica", "B", 12)
pdf.cell(0, 10, "Scoring Weights (100 Points Maximum)", 0, 1)
pdf.add_bullet("AI/Agentic/RAG Project Depth: 40 points")
pdf.add_bullet("Python/Backend Engineering: 30 points")
pdf.add_bullet("Cloud/Deployment/Full Stack: 15 points")
pdf.add_bullet("GitHub Activity (API Enriched): 10 points")
pdf.add_bullet("Engineering Depth (Testing, CI/CD): 5 points")
pdf.ln(5)

pdf.chapter_body(
    "Scoring heavily favors keywords found in contextual proximity to action verbs (e.g., 'built', 'deployed') "
    "over long lists of isolated skills. To combat inflated resumes, a 5-15 point penalty is applied when projects demonstrate 'thin wrapper' characteristics—"
    "such as basic API calls, tutorial-style apps, or when AI keywords only appear in the skills section without project implementation details."
)
pdf.chapter_body(
    "GitHub enrichment acts as a bonus signal. If a profile is private, missing, or the API rate limit is reached, the candidate safely scores 0 in this category "
    "without failing the screening."
)

# --- Page 4: Implementation and Testing ---
pdf.add_page()
pdf.chapter_title("Implementation, Reliability, and Testing")
pdf.chapter_body(
    "The implementation separates configuration (weights/keywords) from business logic. "
    "The Phase 2 LLM assessment integrates via a configurable adapter supporting Google Gemini and OpenAI. "
    "It uses strict JSON-schema prompting to perform semantic extraction, identifying true engineering strengths and confirming thin-wrapper penalties. "
    "Crucially, if the LLM API key is missing or the response times out, the pipeline deterministically falls back to regex-based scoring, guaranteeing reliability."
)
pdf.chapter_body(
    "The system includes a Streamlit dashboard (app.py) that acts as a UI overlay for the core pipeline, ensuring no logic duplication."
)
pdf.set_font("helvetica", "B", 12)
pdf.cell(0, 10, "Test Strategy (53 Passing Tests)", 0, 1)
pdf.chapter_body(
    "The test suite relies on pytest and uses synthetic resume strings to isolate behaviors:"
)
pdf.add_bullet("Eligibility limits: Asserts that Python-only or AI-only resumes fail the hard filter.")
pdf.add_bullet("Keyword boundaries: Prevents substrings from triggering false evidence.")
pdf.add_bullet("Mathematical bounds: Asserts no candidate can exceed category maximums or 100 total points.")
pdf.add_bullet("API Mocks: Simulates GitHub 403 Rate Limits, 404s, and LLM key absences to verify graceful fallback.")

# --- Page 5: Results ---
pdf.add_page()
pdf.chapter_title("Results and Evaluation")
pdf.chapter_body(
    "The pipeline was executed against the provided 50-resume dataset. The actual processed batch metrics are as follows:"
)
pdf.set_font("helvetica", "B", 11)
pdf.cell(40, 8, f"Total Resumes:", border=1); pdf.set_font("helvetica", "", 11); pdf.cell(20, 8, str(summary['total_resumes']), border=1, ln=1)
pdf.set_font("helvetica", "B", 11)
pdf.cell(40, 8, f"Parsed:", border=1); pdf.set_font("helvetica", "", 11); pdf.cell(20, 8, str(summary['successfully_parsed']), border=1, ln=1)
pdf.set_font("helvetica", "B", 11)
pdf.cell(40, 8, f"Eligible:", border=1); pdf.set_font("helvetica", "", 11); pdf.cell(20, 8, str(summary['eligible']), border=1, ln=1)
pdf.set_font("helvetica", "B", 11)
pdf.cell(40, 8, f"Rejected:", border=1); pdf.set_font("helvetica", "", 11); pdf.cell(20, 8, str(summary['rejected']), border=1, ln=1)
pdf.set_font("helvetica", "B", 11)
pdf.cell(40, 8, f"Failed:", border=1); pdf.set_font("helvetica", "", 11); pdf.cell(20, 8, str(summary['failed_unreadable']), border=1, ln=1)
pdf.ln(5)

pdf.set_font("helvetica", "B", 12)
pdf.cell(0, 10, "Top 5 Ranked Candidates", 0, 1)
pdf.set_font("helvetica", "B", 10)
pdf.cell(10, 8, "Rank", 1)
pdf.cell(60, 8, "Name", 1)
pdf.cell(20, 8, "Score", 1)
pdf.cell(90, 8, "Breakdown (AI/Py/Cld/GH/Eng)", 1, 1)

pdf.set_font("helvetica", "", 10)
for c in top_candidates:
    bd = c['score_breakdown']
    breakdown_str = f"{bd['ai_project_depth']}/{bd['python_backend']}/{bd['cloud_fullstack']}/{bd['github']}/{bd['engineering_depth']}"
    pdf.cell(10, 8, str(c['rank']), 1)
    pdf.cell(60, 8, str(c['candidate_name'])[:25], 1)
    pdf.cell(20, 8, str(c['total_score']), 1)
    pdf.cell(90, 8, breakdown_str, 1, 1)
pdf.ln(5)

pdf.chapter_body(
    "The score distribution demonstrates effective separation between candidates with deep, contextualized agentic implementations "
    "and those merely listing generic frameworks."
)

# --- Page 6: Decisions, Limitations & Future ---
pdf.add_page()
pdf.chapter_title("Design Decisions & Limitations")
pdf.chapter_body(
    "Trade-off: Determinism vs Semantic Understanding. A purely LLM-driven pipeline risks inconsistent eligibility judgments "
    "due to non-determinism. By isolating the LLM as an optional enrichment layer (Phase 2), the system retains absolute baseline reliability. "
    "If the LLM flags a 'thin wrapper', it is logged as a qualitative concern rather than silently mutating the quantitative score, maintaining auditability."
)
pdf.set_font("helvetica", "B", 12)
pdf.cell(0, 10, "Known Limitations", 0, 1)
pdf.add_bullet("Name Extraction: Relies on heuristics (rejecting common non-name words and headers). Highly unconventional formats may still produce errors.")
pdf.add_bullet("API Reliance: GitHub restricts unauthenticated IPs to 60 requests per hour. For 50 resumes, a token is highly recommended to avoid partial enrichment.")
pdf.add_bullet("LLM Context Windows: Extremely dense, multi-page PDFs are truncated to ~3000 characters before LLM assessment to prevent token limit errors.")

pdf.set_font("helvetica", "B", 12)
pdf.cell(0, 10, "If I Had More Time (Future Improvements)", 0, 1)
pdf.add_bullet("Async/Concurrent Processing: Parallelizing I/O-bound tasks (GitHub and LLM API requests) to process the batch in seconds rather than minutes.")
pdf.add_bullet("Section-Aware Parsing: Using an ML classifier to segment the resume (Experience, Projects, Education) to isolate skill searches specifically to professional experience.")
pdf.add_bullet("Confidence Scoring: Outputting an algorithmic confidence percentage for each candidate to automatically flag ambiguous resumes for human review.")

pdf.output("docs/AI_Resume_Screening_Assessment_Report.pdf")
print("PDF successfully generated.")
