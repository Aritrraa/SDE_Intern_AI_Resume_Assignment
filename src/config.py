"""
Configuration module — all tuneable parameters in one place.

Keeps scoring weights, eligibility keywords, thresholds, and API config
separate from business logic so they can be reviewed and changed easily.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Scoring weights (must sum to 100)
# ---------------------------------------------------------------------------
SCORING_WEIGHTS = {
    "ai_project_depth": 40,
    "python_backend": 30,
    "cloud_fullstack": 15,
    "github": 10,
    "engineering_depth": 5,
}

# ---------------------------------------------------------------------------
# Eligibility keywords (case-insensitive matching)
# ---------------------------------------------------------------------------

# Python evidence — language / frameworks / tools that prove Python usage
PYTHON_KEYWORDS = [
    "python", "django", "flask", "fastapi", "streamlit", "pandas", "numpy",
    "scipy", "matplotlib", "seaborn",
    "scikit-learn", "sklearn", "celery", "sqlalchemy", "pydantic",
    "uvicorn", "gunicorn", "jupyter", "notebook", "conda",
    "asyncio", "aiohttp", "httpx", "boto3", "pytest", "unittest",
]

# AI / Agentic evidence — frameworks, concepts, project types
AI_KEYWORDS = [
    # Frameworks / libraries
    "langchain", "langgraph", "llamaindex", "llama_index", "llama index",
    "google adk", "autogen", "crewai", "crew ai", "semantic kernel",
    "haystack", "dspy",
    # Concepts / project types
    "rag", "retrieval augmented generation", "retrieval-augmented",
    "vector search", "vector database", "vector store", "vector db",
    "embedding", "embeddings", "pinecone", "weaviate", "chroma",
    "chromadb", "qdrant", "faiss", "milvus",
    "tool calling", "tool-calling", "tool use", "function calling",
    "agentic", "agent", "multi-agent", "multiagent",
    "llm", "large language model", "gpt", "openai", "anthropic",
    "claude", "gemini", "mistral", "ollama", "huggingface", "hugging face",
    "transformers", "fine-tuning", "fine tuning", "finetuning",
    "prompt engineering", "prompt template",
    "chatbot", "conversational ai",
    "natural language processing", "nlp",
    "computer vision", "image classification", "object detection",
    "deep learning", "neural network", "cnn", "rnn", "lstm",
    "reinforcement learning",
    "machine learning", "ml model", "ml pipeline",
    "generative ai", "gen ai", "genai",
]

# Scoring sub-keywords for individual categories
PYTHON_BACKEND_KEYWORDS = [
    "python", "fastapi", "django", "flask", "async", "asyncio",
    "postgresql", "postgres", "redis", "celery", "sqlalchemy",
    "rest api", "restful", "graphql", "grpc",
    "uvicorn", "gunicorn", "pydantic", "httpx", "aiohttp",
]

CLOUD_DEPLOY_KEYWORDS = [
    "gcp", "google cloud", "aws", "azure", "docker", "kubernetes",
    "k8s", "terraform", "ci/cd", "cicd", "github actions",
    "jenkins", "vercel", "netlify", "heroku", "railway",
    "cloud run", "cloud functions", "lambda", "ec2", "s3",
    "nginx", "linux", "deployment", "devops",
    "react", "next.js", "nextjs", "vue", "angular", "svelte",
    "full stack", "fullstack", "full-stack",
]

ENGINEERING_DEPTH_KEYWORDS = [
    "testing", "unit test", "pytest", "unittest", "integration test",
    "tdd", "test-driven",
    "architecture", "microservice", "monolith", "clean architecture",
    "caching", "cache", "redis", "memcached",
    "queue", "rabbitmq", "kafka", "celery", "sqs",
    "observability", "monitoring", "logging", "prometheus", "grafana",
    "sentry", "datadog",
    "concurrency", "multithreading", "multiprocessing", "async",
    "failure handling", "retry", "circuit breaker", "error handling",
    "rate limit", "rate limiting",
    "design pattern", "solid", "dependency injection",
    "api gateway", "load balancer",
]

AI_PROJECT_DEPTH_KEYWORDS = [
    # Core agentic / RAG
    "langchain", "langgraph", "llamaindex", "llama_index", "llama index",
    "rag", "retrieval augmented", "retrieval-augmented",
    "vector search", "vector store", "vector database",
    "embedding", "embeddings", "tool calling", "tool-calling",
    "function calling", "agentic", "agent", "multi-agent",
    "orchestration", "state machine", "workflow",
    # Deeper AI
    "fine-tuning", "fine tuning", "finetuning",
    "evaluation pipeline", "eval pipeline",
    "prompt engineering", "prompt template",
    "transformer", "attention mechanism",
    "training pipeline", "model training",
    "deep learning", "neural network",
    "reinforcement learning",
    "computer vision", "nlp", "natural language processing",
    "generative ai", "gen ai",
    # Frameworks
    "pytorch", "tensorflow", "keras", "scikit-learn", "sklearn",
    "huggingface", "hugging face", "openai", "anthropic",
    "gpt", "claude", "gemini", "mistral", "ollama",
    "pinecone", "weaviate", "chroma", "qdrant", "faiss",
    "crewai", "autogen", "dspy", "semantic kernel", "haystack",
]

# ---------------------------------------------------------------------------
# Project-quality penalty keywords (thin wrapper detection)
# ---------------------------------------------------------------------------
THIN_WRAPPER_INDICATORS = [
    "api call", "api wrapper", "simple chatbot", "basic chatbot",
    "tutorial", "course project", "demo project", "hello world",
    "todo app", "to-do app", "weather app",
]

PROJECT_DEPTH_INDICATORS = [
    "state management", "retrieval", "pipeline", "workflow",
    "orchestration", "evaluation", "backend logic", "data processing",
    "database", "authentication", "authorization", "deployment",
    "caching", "queue", "async", "concurrency", "testing",
    "monitoring", "logging", "error handling", "retry",
    "custom", "built from scratch", "end-to-end", "production",
    "scalable", "microservice",
]

# ---------------------------------------------------------------------------
# GitHub API
# ---------------------------------------------------------------------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_API_BASE = "https://api.github.com"
GITHUB_MAX_SCORE = 10  # cap
GITHUB_REQUEST_TIMEOUT = 10  # seconds

# ---------------------------------------------------------------------------
# LLM Assessment
# ---------------------------------------------------------------------------
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "google")  # "google" | "openai"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.0-flash")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))
LLM_MAX_CONCURRENCY = int(os.getenv("LLM_MAX_CONCURRENCY", "5"))

# ---------------------------------------------------------------------------
# File handling
# ---------------------------------------------------------------------------
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}
