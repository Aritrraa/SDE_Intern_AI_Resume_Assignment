"""
Resume ingestion — read PDF (and optionally DOCX/TXT) files from a directory.

Handles malformed or unreadable files gracefully: logs the error and
continues processing the rest of the batch.
"""

import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def extract_text_from_pdf(filepath: str) -> str:
    """Extract text from a PDF using PyMuPDF (fitz)."""
    import fitz  # PyMuPDF

    text_parts: list[str] = []
    doc = fitz.open(filepath)
    try:
        for page in doc:
            text_parts.append(page.get_text())
    finally:
        doc.close()
    return "\n".join(text_parts)


def extract_text_from_docx(filepath: str) -> str:
    """Extract text from a DOCX file (bonus format)."""
    try:
        from docx import Document
    except ImportError:
        raise ImportError("python-docx is required for DOCX support. Install it with: pip install python-docx")

    doc = Document(filepath)
    return "\n".join(para.text for para in doc.paragraphs)


def extract_text_from_txt(filepath: str) -> str:
    """Extract text from a plain text file."""
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


# Dispatch table
_EXTRACTORS = {
    ".pdf": extract_text_from_pdf,
    ".docx": extract_text_from_docx,
    ".txt": extract_text_from_txt,
}


def extract_text(filepath: str) -> Optional[str]:
    """
    Extract text from a resume file.

    Returns the extracted text string, or None if extraction failed.
    """
    ext = Path(filepath).suffix.lower()
    extractor = _EXTRACTORS.get(ext)
    if extractor is None:
        logger.warning("Unsupported file format: %s", ext)
        return None
    try:
        text = extractor(filepath)
        if not text or not text.strip():
            logger.warning("No text extracted from %s", filepath)
            return None
        return text
    except Exception as e:
        logger.error("Failed to extract text from %s: %s", filepath, e)
        return None


def ingest_resumes(input_dir: str) -> list[dict]:
    """
    Scan *input_dir* for resume files and extract text from each.

    Returns a list of dicts:
        {
            "filename": str,
            "filepath": str,
            "text": str | None,
            "parse_error": str | None,
        }
    """
    from src.config import SUPPORTED_EXTENSIONS

    input_path = Path(input_dir)
    if not input_path.is_dir():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    results: list[dict] = []
    files = sorted(input_path.iterdir())

    for f in files:
        if not f.is_file():
            continue
        if f.suffix.lower() not in SUPPORTED_EXTENSIONS:
            logger.info("Skipping unsupported file: %s", f.name)
            continue

        record: dict = {
            "filename": f.name,
            "filepath": str(f),
            "text": None,
            "parse_error": None,
        }

        try:
            text = extract_text(str(f))
            if text is None:
                record["parse_error"] = "No text could be extracted"
            else:
                record["text"] = text
        except Exception as e:
            record["parse_error"] = str(e)
            logger.error("Ingestion error for %s: %s", f.name, e)

        results.append(record)

    return results
