"""
Ingestion: parses BIS SP 21 PDFs and produces structured chunks.

Strategy (this is your "Innovation" point):
- Detect IS standard codes (e.g., "IS 269", "IS 8112:2013") with regex.
- Each chunk = one standard's summary block, NOT a fixed token window.
  This is critical because BIS standards are atomic units — splitting them
  by 512 tokens shreds the very thing we want to retrieve.
- Falls back to paragraph chunking for sections without explicit IS codes.
"""

import os
import re
import json
from pathlib import Path
from typing import List, Dict
import pdfplumber
from tqdm import tqdm

DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw_pdfs"
CHUNKS_PATH = DATA_DIR / "chunks.json"

# Matches: "IS 269", "IS 269:2015", "IS 269 : 2015", "IS/ISO 9001"
IS_CODE_PATTERN = re.compile(
    r"\b(IS(?:/[A-Z]+)?\s*\d{1,5}(?:\s*[:\-]\s*\d{4})?(?:\s*\(Part\s*\d+\))?)\b",
    re.IGNORECASE,
)


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract all text from a PDF, preserving paragraph breaks."""
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
    return "\n".join(text_parts)


def normalize_is_code(code: str) -> str:
    """'IS  269 : 2015' -> 'IS 269:2015'"""
    code = re.sub(r"\s+", " ", code.strip())
    code = code.replace(" : ", ":").replace(" :", ":").replace(": ", ":")
    return code.upper().replace("IS ", "IS ")


def chunk_by_standards(text: str, source_file: str) -> List[Dict]:
    """
    Split text into chunks where each chunk is anchored to one IS standard.
    Walks the text linearly: every time a new IS code appears, start a new chunk.
    """
    chunks = []
    matches = list(IS_CODE_PATTERN.finditer(text))

    if not matches:
        # Fallback: paragraph chunks of ~500 words
        return _fallback_paragraph_chunks(text, source_file)

    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk_text = text[start:end].strip()

        # Skip tiny chunks (likely TOC entries)
        if len(chunk_text) < 80:
            continue

        # Cap chunks at ~2000 chars to avoid pulling 5 pages into one chunk
        if len(chunk_text) > 2000:
            chunk_text = chunk_text[:2000]

        is_code = normalize_is_code(m.group(1))
        chunks.append({
            "id": f"{source_file}::{i}",
            "is_code": is_code,
            "text": chunk_text,
            "source": source_file,
        })

    return chunks


def _fallback_paragraph_chunks(text: str, source_file: str) -> List[Dict]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if len(p.strip()) > 80]
    return [
        {
            "id": f"{source_file}::para_{i}",
            "is_code": "UNKNOWN",
            "text": p[:2000],
            "source": source_file,
        }
        for i, p in enumerate(paragraphs)
    ]


def build_chunks() -> List[Dict]:
    if not RAW_DIR.exists():
        raise FileNotFoundError(
            f"Put SP 21 PDFs in {RAW_DIR} before running ingestion."
        )

    pdf_files = list(RAW_DIR.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"No PDFs found in {RAW_DIR}")

    all_chunks = []
    for pdf_path in tqdm(pdf_files, desc="Parsing PDFs"):
        text = extract_text_from_pdf(pdf_path)
        chunks = chunk_by_standards(text, pdf_path.name)
        all_chunks.extend(chunks)

    # Deduplicate by IS code, keeping the longest (most informative) chunk
    by_code = {}
    for c in all_chunks:
        key = c["is_code"]
        if key == "UNKNOWN":
            by_code[c["id"]] = c  # keep paragraph chunks individually
        elif key not in by_code or len(c["text"]) > len(by_code[key]["text"]):
            by_code[key] = c

    deduped = list(by_code.values())
    DATA_DIR.mkdir(exist_ok=True)
    with open(CHUNKS_PATH, "w") as f:
        json.dump(deduped, f, indent=2)
    print(f"✅ Built {len(deduped)} chunks → {CHUNKS_PATH}")
    return deduped


if __name__ == "__main__":
    build_chunks()
