# AI Resume Screening & Ranking System

An automated pipeline that ingests a folder of resumes, filters candidates against Python/AI requirements, scores relevant candidates based on engineering and AI project depth, enriches scores using public GitHub activity, and returns a ranked shortlist.

## Quick Start

### Prerequisites
- Python 3.10+
- pip

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# (Optional) Configure GitHub token and LLM API keys
cp .env.example .env
# Edit .env and add your API keys (e.g., GOOGLE_API_KEY)
```

### Run CLI

```bash
# Process resumes and generate ranked results
python main.py --input ./resumes --output ./output/results.json

# Run without GitHub enrichment (offline / faster)
python main.py --input ./resumes --output ./output/results.json --no-github

# Run without LLM semantic extraction (fallback to deterministic)
python main.py --input ./resumes --output ./output/results.json --no-llm

# Verbose logging
python main.py --input ./resumes --output ./output/results.json -v
```

### Run Frontend Dashboard

```bash
streamlit run app.py
```

### Run Tests

```bash
python -m pytest tests/ -v
```

## Project Structure

```
project/
├── main.py                  # CLI entry point
├── src/
│   ├── __init__.py
│   ├── config.py            # All tuneable parameters (weights, keywords, thresholds)
│   ├── ingestion.py         # Resume file ingestion (PDF, DOCX, TXT)
│   ├── extractor.py         # Candidate info extraction (name, email, GitHub, skills)
│   ├── eligibility.py       # Hard eligibility filter (Python + AI evidence)
│   ├── scoring.py           # 100-point scoring model with penalties
│   ├── github_enrichment.py # Lightweight GitHub API integration
│   └── pipeline.py          # Pipeline orchestrator
├── tests/
│   ├── __init__.py
│   └── test_pipeline.py     # Unit + integration tests (31 tests)
├── resumes/                 # Input resume directory (supplied dataset)
├── output/                  # Generated results
│   └── results.json
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Pipeline

The system follows the exact pipeline prescribed in the assignment:

1. **Ingest** — Scan input directory for PDF files (DOCX/TXT also supported as bonus). Malformed or unreadable files are logged and skipped without crashing the batch.

2. **Extract** — Parse resume text and extract candidate information (name, email, phone, GitHub URL, skills, projects) using regex/heuristic methods.

3. **Eligibility Filter** — Deterministic hard filter. A candidate is eligible **only** when **both** conditions are satisfied:
   - **Python evidence**: Python or a Python framework/tool appears in the resume
   - **AI/agentic evidence**: At least one meaningful AI/LLM/RAG/agentic framework, project, or concept is present

4. **Score** — Score eligible candidates using the prescribed 100-point model (see below).

5. **GitHub Enrichment** — If a GitHub profile URL is found, query the public GitHub API for recent activity and repository information. Capped at 10 points. Graceful failure handling.

6. **Rank & Output** — Rank eligible candidates by total score (descending), generate JSON with full score breakdowns, evidence, rejection reasons, and batch statistics.

## Scoring Model (100 Points)

| Category | Weight | What is Rewarded |
|---|---|---|
| AI / Agentic / RAG Project Depth | 40 | Real AI systems: agents, RAG, tools, retrieval, state, orchestration, evaluation. Tiered scoring: agentic/RAG keywords worth 3× more than generic ML keywords. Context bonus for keywords used in project descriptions. |
| Python & Backend Engineering | 30 | Python, FastAPI, async, PostgreSQL, Redis. Evidence in projects/internships rewarded over keyword-only skill lists. Backend framework bonus. |
| Cloud / Deployment / Full Stack | 15 | GCP, Docker, deployment, React/Next.js as supporting signals. Context bonus for deployment in project descriptions. |
| GitHub Activity | 10 | Recent public events (0-5 pts) + maintained/relevant repositories (0-5 pts). Missing/private GitHub does not fail screening. |
| Engineering Depth Signals | 5 | Testing, architecture, caching, queues, observability, concurrency, failure handling. |

### Project-Quality Penalties

- **-5 to -15 pts**: Thin API wrappers, tutorial-style projects, demo/course projects with no implementation details
- **-10 pts**: AI keywords appear only in skills list with no project context or evidence of usage
- **-5 pts**: Limited project depth despite multiple AI keyword mentions

These penalties ensure that framework names in a skills section don't receive the same score as demonstrated project implementations.

## Design Decisions

### Filtering Strategy
Eligibility uses a **deterministic keyword-matching approach** rather than LLM-based classification. This ensures:
- Predictable, reproducible results
- No dependency on external API availability
- Testable behavior with clear pass/fail criteria
- No false positives from well-written but irrelevant resumes

Python evidence is separated from AI framework keywords (e.g., TensorFlow/PyTorch are classified as AI evidence, not Python evidence) to ensure a candidate must demonstrate genuine Python language usage.

### Scoring Strategy
The scoring model uses a **tiered, context-aware keyword approach**:

1. **Tiered keywords**: Agentic/RAG-specific keywords (LangChain, RAG, vector search, tool calling) score 3× higher than generic ML keywords (machine learning, neural network). This directly rewards the assignment's emphasis on "agents, RAG, tools, retrieval, state, orchestration."

2. **Context bonus**: Keywords found near action verbs ("built," "developed," "implemented") in project/experience sections score significantly higher than keywords appearing only in skills lists. This implements the assignment's instruction to "prefer evidence showing how [a framework] was used."

3. **Transparent penalties**: Penalties are explicitly documented in the output with point values and reasons, making every score decision auditable.

### LLM Usage
Phase 1 is fully deterministic — no LLM calls. This provides:
- A reliable baseline that works without API keys
- Reproducible results for testing and debugging
- A foundation for optional LLM-enhanced scoring in Phase 2

### GitHub Scoring
GitHub enrichment is implemented as an additive signal (0-10 pts), never a hard requirement:
- **Activity score (0-5)**: Based on public events in the last 90 days
- **Repository score (0-5)**: Based on Python repos, AI-relevant repos, and total maintained repos
- Results are cached within the run to avoid redundant API calls
- Rate limits, timeouts, and API failures are handled gracefully
- When GitHub is unavailable, screening continues with 0 GitHub points

## Phase 2 Implementation

This project implements the Phase 2 requirements:
- **LLM Assessment**: Uses Google Gemini (or OpenAI) to semantically analyze project descriptions, extract evidence, and evaluate project quality (e.g. flagging thin wrappers).
- **Graceful Fallback**: Safely falls back to the deterministic scoring algorithm if an API key is missing or the model fails.
- **Streamlit Frontend**: A lightweight web dashboard to view batch statistics, ranked candidate details (including LLM insights and penalties), and rejection reasons.

## If I Had More Time

1. **Async/concurrent processing**: Process resumes, GitHub API calls, and LLM calls concurrently with bounded parallelism for significant speedup on the 50-resume batch.
2. **Section-aware parsing**: Implement resume section detection (Education, Experience, Projects, Skills) to weight keyword appearances by section, reducing false positives from irrelevant sections.
3. **Confidence scoring**: Add a confidence indicator for each score component, flagging low-confidence decisions for human review when keyword evidence is ambiguous.

## Limitations

- **Name extraction is heuristic**: The first non-trivial line of a resume is assumed to be the candidate's name. This may fail for unusual resume formats.
- **GitHub enrichment requires network access**: Without a `GITHUB_TOKEN`, the public API allows only 60 requests/hour (may not cover all 50 resumes).
- **LLM Token Limits**: Very large resumes are truncated to fit within optimal context windows.
